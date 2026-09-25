from fastapi import Request
from fastapi.responses import JSONResponse
import jwt
import os
import httpx
import json
import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from icecream import ic
from core.constants import SHOPEMP_SERVICE_URL, AUTH_SERVICE_URL
from core.utils.http_client import get_http_client
from core.permissions.route_permissions import get_required_permission, ROLE_PERMISSIONS
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("gateway.auth")

CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def create_error_response(status_code: int, msg: str, description: str):
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": {
                "msg": msg,
                "status_code": status_code,
                "success": False,
                "status_type": "error",
                "title": msg,
                "description": description
            }
        }
    )

# In-memory public key cache: version -> public_key_pem
PUBLIC_KEYS_CACHE = {}

# In-memory TTL caches for roles and validated tokens
USER_ROLE_CACHE = {}  # (shop_id, user_id) -> (role, expire_time)
VALID_JTI_CACHE = {}  # jti -> expire_time
SHOP_SUB_CACHE = {}   # shop_id -> (is_expired, expire_time)
ROLE_CACHE_TTL = 60.0  # seconds
JTI_CACHE_TTL = 60.0   # seconds
SUB_CACHE_TTL = 10.0   # seconds

# MongoDB Client for checking token revocation & subscription
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
mongo_client = AsyncIOMotorClient(MONGODB_URL)
db = mongo_client["AuthenticationServiceDb"]


async def is_shop_subscription_expired(shop_id: str) -> bool:
    mock_expired = (os.getenv("MOCK_SUBSCRIPTION_EXPIRED", "false").lower() in ("true", "1", "yes")) or (os.getenv("MOCK_TRIAL_EXPIRED", "false").lower() in ("true", "1", "yes"))
    if mock_expired:
        return True
    if not shop_id or shop_id == "string":
        return False
    now = time.time()
    cached = SHOP_SUB_CACHE.get(shop_id)
    if cached and now < cached[1]:
        return cached[0]
    try:
        sub_doc = await mongo_client["ShopEmpServiceDb"]["shop_subscriptions"].find_one({"shop_id": shop_id})
        is_exp = bool(sub_doc and (sub_doc.get("is_expired") or sub_doc.get("status") == "expired"))
        SHOP_SUB_CACHE[shop_id] = (is_exp, now + SUB_CACHE_TTL)
        return is_exp
    except Exception as e:
        ic(f"Error checking subscription status: {e}")
        return False


async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Always pass through CORS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)

    # Bypass authentication for health checks, auth routes, and employee verification routes
    if path.startswith("/health") or path.startswith("/api/auth") or "/verify" in path or "/internal/" in path:
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
    else:
        token = (
            request.query_params.get("token")
            or request.query_params.get("auth_token")
            or request.query_params.get("access_token")
        )

    if not token:
        return create_error_response(401, "Authentication Error", "Missing or invalid authorization header")

    try:
        # 1. Decode token without signature verification to extract version
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        version = unverified_payload.get("version", "1")
        jti = unverified_payload.get("jti")
    except Exception as e:
        ic(f"Unverified decode failed: {e}")
        return create_error_response(401, "Authentication Error", "Invalid token format")

    # 2. Get public key for version (with in-memory cache)
    global PUBLIC_KEYS_CACHE
    if version not in PUBLIC_KEYS_CACHE:
        try:
            client = get_http_client()
            resp = await client.get(f"{AUTH_SERVICE_URL}/auth/keys/{version}")
            if resp.status_code == 200:
                raw_key = resp.json()["public_key"]
                if isinstance(raw_key, str):
                    raw_key = "\n".join(line.strip() for line in raw_key.strip().splitlines())
                PUBLIC_KEYS_CACHE[version] = raw_key
            else:
                return create_error_response(401, "Authentication Error", f"Failed to fetch public key for version {version}")
        except Exception as e:
            ic(f"Error fetching public key: {e}")
            return create_error_response(500, "Authentication Error", "Authentication Service is currently unavailable")

    public_key = PUBLIC_KEYS_CACHE[version]

    # 3. Verify signature and expiration
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256", "HS256"])
    except jwt.ExpiredSignatureError:
        return create_error_response(401, "Authentication Error", "Token has expired")
    except jwt.PyJWTError as e:
        ic(f"Token verification failed: {e}")
        PUBLIC_KEYS_CACHE.pop(version, None)
        return create_error_response(401, "Authentication Error", "Invalid token signature")

    # 4. Check if token was revoked (with 60s fast-path caching)
    now = time.time()
    if jti:
        if jti not in VALID_JTI_CACHE or now >= VALID_JTI_CACHE[jti]:
            try:
                is_revoked = await db.revoked_tokens.find_one({"jti": jti})
                if is_revoked:
                    VALID_JTI_CACHE.pop(jti, None)
                    return create_error_response(401, "Authentication Error", "Token has been revoked")
                VALID_JTI_CACHE[jti] = now + JTI_CACHE_TTL
            except Exception as e:
                ic(f"Failed to check token revocation: {e}")
                return create_error_response(500, "Authentication Error", "Internal authorization database error")

    # 5. Service-based Route Access Control (Navigation Rules)
    service_name = payload.get("service_name")
    user_id = payload.get("sub")
    x_shop_id = request.headers.get("x-shop-id") or request.query_params.get("shop_id")
    required_permission = get_required_permission(request.method, path)
    role = payload.get("role")

    is_digitalstore_route = (
        path.startswith("/api/digitalstore")
        or path.startswith("/digitalstore")
        or service_name == "digitalstore"
        or request.headers.get("x-origin") == "digitalstore"
    )

    # 5.1 SUBSCRIPTION EXPIRATION LOCKOUT (Hard backend check)
    is_exempt_route = (
        path.startswith("/health")
        or path.startswith("/api/auth")
        or "/subscriptions" in path
        or "/shops" in path
        or "/verify" in path
        or "/internal/" in path
    )

    if not is_exempt_route and not is_digitalstore_route:
        if await is_shop_subscription_expired(x_shop_id):
            logger.warning(f"{RED}[SUBSCRIPTION LOCKED]{RESET} {CYAN}{request.method} {path}{RESET} | Shop: {x_shop_id} is EXPIRED. Request rejected.")
            return create_error_response(
                403,
                "Subscription Expired",
                "Your subscription has ended. All operations and data views for this workspace are locked until renewed."
            )

    if not is_digitalstore_route and x_shop_id and user_id:
        cache_key = (x_shop_id, user_id)
        cached = USER_ROLE_CACHE.get(cache_key)
        if cached and now < cached[1]:
            role = cached[0]
        else:
            try:
                client = get_http_client()
                resp = await client.get(f"{SHOPEMP_SERVICE_URL}/employees/internal/role/{x_shop_id}/{user_id}")
                if resp.status_code == 200:
                    role = resp.json().get("role")
                    USER_ROLE_CACHE[cache_key] = (role, now + ROLE_CACHE_TTL)
            except Exception as e:
                ic(f"Failed to fetch role from ShopEmp-Service: {e}")

        if not role:
            return create_error_response(403, "Access Denied", "Access denied: Not an authorized employee of this shop")

    if required_permission and not is_digitalstore_route:
        if not role:
            logger.warning(f"{RED}[AUTH] ✖ ACCESS DENIED:{RESET} {CYAN}{request.method} {path}{RESET} | User: {user_id} | Role: {YELLOW}NONE{RESET} | Required Permission: {required_permission}")
            return create_error_response(403, "Access Denied", "Access denied: Role could not be determined")
        allowed_actions = ROLE_PERMISSIONS.get(role, set())
        if required_permission not in allowed_actions:
            logger.warning(f"{RED}[AUTH] ✖ ACCESS DENIED:{RESET} {CYAN}{request.method} {path}{RESET} | User: {user_id} | Role: {YELLOW}{role}{RESET} | Missing Permission: {required_permission}")
            return create_error_response(403, "Access Denied", f"Access denied: Role '{role}' does not have '{required_permission}' permission")
        logger.info(f"{GREEN}[AUTH] ✔ ACCESS ALLOWED:{RESET} {CYAN}{request.method} {path}{RESET} | User: {user_id} | Role: {YELLOW}{role}{RESET} | Granted Permission: {required_permission}")
    else:
        logger.info(f"{GREEN}[AUTH] ✔ ACCESS ALLOWED (Unrestricted Route):{RESET} {CYAN}{request.method} {path}{RESET} | User: {user_id} | Role: {YELLOW}{role or 'PUBLIC'}{RESET}")

    # 6. Forward Decoded Token User Info as JSON in X-USER-INFOS header
    user_info = {
        "user_id": user_id,
        "email": payload.get("email"),
        "mobilenumber": payload.get("mobilenumber"),
        "role": role,
        "service_name": service_name
    }
    user_info_json = json.dumps(user_info)

    headers = list(request.scope["headers"])
    headers = [h for h in headers if h[0].lower() != b"x-user-infos"]
    headers.append((b"x-user-infos", user_info_json.encode("utf-8")))
    request.scope["headers"] = headers

    return await call_next(request)
