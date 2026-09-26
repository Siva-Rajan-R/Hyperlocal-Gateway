import httpx
from typing import Optional

_http_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        limits = httpx.Limits(
            max_keepalive_connections=200,
            max_connections=500,
            keepalive_expiry=120.0
        )
        # Fast connect timeout (2.0s) for same-server internal requests, generous read timeout (60.0s)
        timeout = httpx.Timeout(60.0, connect=2.0)
        _http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
    return _http_client

async def close_http_client():
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
