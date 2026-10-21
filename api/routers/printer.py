import socket
import base64
import asyncio
import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("gateway.printer")

router = APIRouter(prefix="/printer", tags=["Printer Bridge"])

class NetworkPrintRequest(BaseModel):
    host: str
    port: int = 9100
    data_base64: str | None = None
    timeout: float = 4.0

class NetworkPingRequest(BaseModel):
    host: str
    port: int = 9100
    timeout: float = 3.0

def _clean_host_and_port(raw_host: str, raw_port: int) -> tuple[str, int]:
    clean = raw_host.replace("http://", "").replace("https://", "").strip()
    if "/" in clean:
        clean = clean.split("/")[0]
    if ":" in clean:
        parts = clean.split(":")
        clean = parts[0]
        try:
            raw_port = int(parts[1])
        except Exception:
            pass
    return clean, raw_port

def _send_tcp_job(host: str, port: int, payload: bytes, timeout: float):
    clean_host, clean_port = _clean_host_and_port(host, port)
    logger.info(f"Opening TCP socket to {clean_host}:{clean_port} (timeout={timeout}s)")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect((clean_host, clean_port))
        if payload:
            sock.sendall(payload)

@router.post("/network-print")
async def network_print(req: NetworkPrintRequest):
    if not req.host or not req.host.strip():
        return {"success": False, "message": "Host or IP address is required."}

    clean_host, clean_port = _clean_host_and_port(req.host, req.port)
    payload = b""
    if req.data_base64:
        try:
            payload = base64.b64decode(req.data_base64)
        except Exception as e:
            logger.error(f"Base64 decode error: {e}")
            return {"success": False, "message": f"Invalid print data payload: {e}"}

    try:
        await asyncio.to_thread(_send_tcp_job, clean_host, clean_port, payload, req.timeout)
        return {
            "success": True,
            "message": f"Sent print job to Network Printer at {clean_host}:{clean_port}",
        }
    except socket.timeout:
        logger.warning(f"Connection timeout reaching {clean_host}:{clean_port}")
        return {
            "success": False,
            "message": f"Connection timed out reaching {clean_host}:{clean_port}. Please verify printer host/IP, port, and power.",
        }
    except ConnectionRefusedError:
        logger.warning(f"Connection refused by {clean_host}:{clean_port}")
        return {
            "success": False,
            "message": f"Connection refused by {clean_host}:{clean_port}. Check that the printer or emulator is running and listening on port {clean_port}.",
        }
    except Exception as e:
        logger.error(f"Network print error: {e}")
        return {
            "success": False,
            "message": f"Could not print to {clean_host}:{clean_port} ({str(e)})",
        }

@router.post("/network-ping")
async def network_ping(req: NetworkPingRequest):
    if not req.host or not req.host.strip():
        return {"success": False, "message": "Host or IP address is required."}

    clean_host, clean_port = _clean_host_and_port(req.host, req.port)
    try:
        await asyncio.to_thread(_send_tcp_job, clean_host, clean_port, b"", req.timeout)
        return {
            "success": True,
            "message": f"Network printer at {clean_host}:{clean_port} is online and reachable!",
        }
    except socket.timeout:
        return {
            "success": False,
            "message": f"Connection timed out reaching {clean_host}:{clean_port}.",
        }
    except ConnectionRefusedError:
        return {
            "success": False,
            "message": f"Connection refused at {clean_host}:{clean_port}. Port {clean_port} is closed.",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to reach {clean_host}:{clean_port} ({str(e)})",
        }
