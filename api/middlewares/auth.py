from fastapi import Request, HTTPException
import jwt


JWT_SECRET=""
async def auth_middleware(request: Request, call_next):
    # if request.url.path.startswith("/health"):
    #     return await call_next(request)

    # token = request.headers.get("Authorization")
    # if not token:
    #     raise HTTPException(status_code=401, detail="Missing token")

    # try:
    #     jwt.decode(token.replace("Bearer ", ""), JWT_SECRET, algorithms=["HS256"])
    # except Exception:
    #     raise HTTPException(status_code=401, detail="Invalid token")

    return await call_next(request)
