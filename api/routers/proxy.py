from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
from starlette.requests import ClientDisconnect
import httpx
import websockets
import asyncio
import logging
from api.middlewares.rate_limit import limiter
from core.utils.service_url import get_service_url
from core.utils.http_client import get_http_client
from icecream import ic

logger = logging.getLogger("gateway.proxy")
router = APIRouter()

@router.websocket("/{service_path:path}")
async def websocket_proxy(websocket: WebSocket, service_path: str):
    await websocket.accept()
    try:
        base_url = get_service_url(service_path=service_path)
    except Exception as e:
        logger.error(f"WebSocket service resolution error for '{service_path}': {e}")
        await websocket.close(code=1011, reason="Service not found")
        return

    ws_base_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
    query_string = websocket.scope.get("query_string", b"").decode("utf-8")
    target_url = f"{ws_base_url}/{service_path}"
    if query_string:
        target_url = f"{target_url}?{query_string}"

    try:
        async with websockets.connect(target_url) as target_ws:
            async def client_to_target():
                try:
                    while True:
                        data = await websocket.receive()
                        if "text" in data and data["text"] is not None:
                            await target_ws.send(data["text"])
                        elif "bytes" in data and data["bytes"] is not None:
                            await target_ws.send(data["bytes"])
                except WebSocketDisconnect:
                    await target_ws.close()
                except Exception:
                    pass

            async def target_to_client():
                try:
                    async for message in target_ws:
                        if isinstance(message, str):
                            await websocket.send_text(message)
                        else:
                            await websocket.send_bytes(message)
                except Exception:
                    pass

            done, pending = await asyncio.wait(
                [asyncio.create_task(client_to_target()), asyncio.create_task(target_to_client())],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
    except Exception as e:
        logger.error(f"WebSocket proxy error connecting to {target_url}: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass

@router.api_route(
    "/{service_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
@limiter.limit("1000/minute")
async def proxy(service_path: str, request: Request):
    try:
        base_url = get_service_url(service_path=service_path)
    except Exception as e:
        return Response(status_code=404, content=f"Service Not Found: {str(e)}")

    url = f"{base_url}/{service_path}"

    excluded_headers = {"host", "content-length", "connection"}
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in excluded_headers
    }

    try:
        req_body = await request.body()
    except ClientDisconnect:
        logger.warning(f"Client disconnected before request body was received: {request.method} {request.url.path}")
        return Response(status_code=499, content="Client Closed Request")

    client = get_http_client()
    try:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.query_params,
            content=req_body,
        )
    except httpx.ConnectTimeout:
        logger.error(f"Connect timeout forwarding to {url}")
        return Response(status_code=504, content="Gateway Timeout: Upstream connection timeout")
    except httpx.ReadTimeout:
        logger.error(f"Read timeout forwarding to {url}")
        return Response(status_code=504, content="Gateway Timeout: Upstream read timeout")
    except httpx.RequestError as e:
        logger.error(f"Proxy request error forwarding to {url}: {e}")
        return Response(status_code=502, content=f"Bad Gateway: Unable to reach upstream service ({e})")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )
