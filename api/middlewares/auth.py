from fastapi import Request
from fastapi.responses import JSONResponse
import jwt
import httpx
import json
from motor.motor_asyncio import AsyncIOMotorClient
from icecream import ic

# In-memory public key cache: version -> public_key_pem
PUBLIC_KEYS_CACHE = {}

# MongoDB Client for checking token revocation
mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
db = mongo_client["AuthenticationServiceDb"]

AUTH_SERVICE_URL="http://127.0.0.1:8010"

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
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing or invalid authorization header"}
        )

    token = auth_header.replace("Bearer ", "")

    try:
        # 1. Decode token without signature verification to extract version
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        version = unverified_payload.get("version", "1")
        jti = unverified_payload.get("jti")
    except Exception as e:
        ic(f"Unverified decode failed: {e}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid token format"}
        )

    # 2. Get public key for version (with in-memory cache)
    global PUBLIC_KEYS_CACHE
    if version not in PUBLIC_KEYS_CACHE:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{AUTH_SERVICE_URL}/auth/keys/{version}")
                if resp.status_code == 200:
                    PUBLIC_KEYS_CACHE[version] = resp.json()["public_key"]
                else:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": f"Failed to fetch public key for version {version}"}
                    )
        except Exception as e:
            ic(f"Error fetching public key: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Authentication Service is currently unavailable"}
            )

    public_key = PUBLIC_KEYS_CACHE[version]

    # 3. Verify signature and expiration
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token has expired"})
    except jwt.PyJWTError as e:
        ic(f"Token verification failed: {e}")
        return JSONResponse(status_code=401, content={"detail": "Invalid token signature"})

    # 4. Check if token was revoked
    if jti:
        try:
            is_revoked = await db.revoked_tokens.find_one({"jti": jti})
            if is_revoked:
                return JSONResponse(status_code=401, content={"detail": "Token has been revoked"})
        except Exception as e:
            ic(f"Failed to check token revocation: {e}")
            # We fail secure on DB errors
            return JSONResponse(status_code=500, content={"detail": "Internal authorization database error"})

    # 5. Service-based Route Access Control (Navigation Rules)
    service_name = payload.get("service_name")
    
    # if service_name == "HYPERLOCAL-INVENTORY":
    #     # HYPERLOCAL-INVENTORY cannot access /api/digitalstore
    #     if path.startswith("/api/digitalstore") or path.startswith("/digitalstore"):
    #         return JSONResponse(
    #             status_code=403,
    #             content={"detail": "Access forbidden: HYPERLOCAL-INVENTORY cannot access digital store routes"}
    #         )
    # elif service_name == "HYPERLOCAL-APP":
    #     # HYPERLOCAL-APP can only access /api/digitalstore
    #     if not (path.startswith("/api/digitalstore") or path.startswith("/digitalstore")):
    #         return JSONResponse(
    #             status_code=403,
    #             content={"detail": "Access forbidden: HYPERLOCAL-APP can only access digital store routes"}
    #         )

    # 6. Forward Decoded Token User Info as JSON in X-USER-INFOS header
    user_info = {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "mobilenumber": payload.get("mobilenumber"),
        "role": payload.get("role"),
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
