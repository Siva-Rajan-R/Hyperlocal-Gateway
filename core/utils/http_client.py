import httpx
from typing import Optional

_http_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        limits = httpx.Limits(
            max_keepalive_connections=100,
            max_connections=300,
            keepalive_expiry=60.0
        )
        timeout = httpx.Timeout(120.0, connect=10.0)
        _http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
    return _http_client

async def close_http_client():
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
