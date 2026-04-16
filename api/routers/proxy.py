from fastapi import APIRouter, Request, Response
import httpx
from api.middlewares.rate_limit import limiter
from core.utils.service_url import get_service_url
from icecream import ic

router = APIRouter()

@router.api_route(
    "/{service_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
@limiter.limit("10/minute")
async def proxy(
    service_path: str,
    request: Request,
):
    base_url = get_service_url(service_path=service_path)

    url = f"{base_url}/{service_path}"
    ic(url)

    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=dict(request.headers),
            params=request.query_params,
            content=await request.body()
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )