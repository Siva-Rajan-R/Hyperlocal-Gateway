from fastapi import APIRouter, Request, Response
import httpx
from api.middlewares.rate_limit import limiter
from core.utils.service_url import get_service_url
from icecream import ic

router = APIRouter()

@router.api_route(
    "/{service_path:path}",
    methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"],
)

@limiter.limit("15/minute")
async def proxy(service_path: str, request: Request):
    base_url = get_service_url(service_path=service_path)
    url = f"{base_url}/{service_path}"

    excluded_headers = {"host", "content-length", "connection"}

    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in excluded_headers
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.query_params,
            content=await request.body()
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )