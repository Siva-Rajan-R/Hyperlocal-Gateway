from fastapi import Request
from fastapi.responses import JSONResponse
import jwt,os
import httpx
import json
from motor.motor_asyncio import AsyncIOMotorClient
from icecream import ic
from core.constants import SHOPEMP_SERVICE_URL,AUTH_SERVICE_URL
from dotenv import load_dotenv
load_dotenv()

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

# MongoDB Client for checking token revocation
MONGODB_URL=os.getenv("MONGODB_URL")
mongo_client = AsyncIOMotorClient(MONGODB_URL)
db = mongo_client["AuthenticationServiceDb"]


async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Always pass through CORS preflight requests — the browser sends OPTIONS
    # before every cross-origin fetch. Blocking them breaks all API calls.
    if request.method == "OPTIONS":
        return await call_next(request)

    # Bypass authentication for health checks, auth routes, and employee verification routes
    if path.startswith("/health") or path.startswith("/api/auth") or path.startswith("/api/employees/verify"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return create_error_response(401, "Authentication Error", "Missing or invalid authorization header")

    token = auth_header.replace("Bearer ", "")

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
            async with httpx.AsyncClient(timeout=5.0) as client:
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
        # Invalidate cached public key in case auth service updated key pair
        PUBLIC_KEYS_CACHE.pop(version, None)
        return create_error_response(401, "Authentication Error", "Invalid token signature")

    # 4. Check if token was revoked
    if jti:
        try:
            is_revoked = await db.revoked_tokens.find_one({"jti": jti})
            if is_revoked:
                return create_error_response(401, "Authentication Error", "Token has been revoked")
        except Exception as e:
            ic(f"Failed to check token revocation: {e}")
            # We fail secure on DB errors
            return create_error_response(500, "Authentication Error", "Internal authorization database error")

    # 5. Service-based Route Access Control (Navigation Rules)
    service_name = payload.get("service_name")
    user_id = payload.get("sub")
    
    # Extract x-shop-id to verify roles
    x_shop_id = request.headers.get("x-shop-id")
    
    from core.permissions.route_permissions import get_required_permission, ROLE_PERMISSIONS
    required_permission = get_required_permission(request.method, path)
    
    role = payload.get("role")
    
    is_digitalstore_route = (
        path.startswith("/api/digitalstore")
        or path.startswith("/digitalstore")
        or service_name == "digitalstore"
        or request.headers.get("x-origin") == "digitalstore"
    )
    
    if not is_digitalstore_route and x_shop_id and user_id:
        # We need to check the shop-specific role from ShopEmp-Service
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{SHOPEMP_SERVICE_URL}/employees/internal/role/{x_shop_id}/{user_id}")
                if resp.status_code == 200:
                    role = resp.json().get("role")
        except Exception as e:
            ic(f"Failed to fetch role from ShopEmp-Service: {e}")
            
        if not role:
            return create_error_response(403, "Access Denied", "Access denied: Not an authorized employee of this shop")
            
    # Logging with color formatting
    import logging
    logger = logging.getLogger("gateway.auth")

    CYAN = "\033[96m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

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
    
    # Mutate the ASGI scope to append the new header
    headers = list(request.scope["headers"])
    # Strip any client-sent X-USER-INFOS for security
    headers = [h for h in headers if h[0].lower() != b"x-user-infos"]
    headers.append((b"x-user-infos", user_info_json.encode("utf-8")))
    request.scope["headers"] = headers

    return await call_next(request)
