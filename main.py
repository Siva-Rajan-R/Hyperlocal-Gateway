from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.routers.proxy import router
from api.middlewares.auth import auth_middleware
from api.middlewares.rate_limit import limiter, rate_limit_exceeded_handler

app = FastAPI(title="API Gateway")

# ✅ 1. CORS FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 2. Rate limit
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ✅ 3. Auth middleware AFTER CORS
app.middleware("http")(auth_middleware)

# Routes
app.include_router(router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}