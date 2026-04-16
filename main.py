from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.routers.proxy import router
from api.middlewares.auth import auth_middleware
from api.middlewares.rate_limit import limiter, rate_limit_exceeded_handler

app = FastAPI(title="API Gateway")

app.middleware("http")(auth_middleware)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Routes
app.include_router(router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
