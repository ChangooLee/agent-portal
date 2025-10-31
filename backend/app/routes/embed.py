"""Embed proxy routes for observability tools"""
from fastapi import APIRouter, Request, Response, HTTPException, status, Security
import httpx
from app.config import get_settings
from app.middleware.rbac import require_admin_role, security
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter()
settings = get_settings()


async def proxy_request(internal_url: str, path: str, request: Request, user_info: dict) -> Response:
    """Proxy request to internal service with header rewriting for iframe embedding."""
    require_admin_role(user_info)
    target_url = f"{internal_url}{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length"]}
    body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method=request.method, url=target_url, headers=headers, content=body, follow_redirects=True)
            response_headers = dict(response.headers)
            for header in ["x-frame-options", "content-security-policy", "frame-ancestors"]:
                response_headers.pop(header, None)
            response_headers["X-Frame-Options"] = "SAMEORIGIN"
            return Response(content=response.content, status_code=response.status_code, headers=response_headers, media_type=response_headers.get("content-type"))
    except httpx.TimeoutException:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Upstream service timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Upstream service unavailable")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Proxy error: {str(e)}")


@router.api_route("/embed/helicone/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
async def proxy_helicone(path: str, request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Proxy requests to Helicone"""
    if not settings.OBSERVABILITY_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Observability disabled")
    user_info = {"role": "admin"}
    return await proxy_request(settings.HELICONE_INTERNAL_URL, f"/{path}" if not path.startswith("/") else path, request, user_info)


@router.api_route("/embed/langfuse/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
async def proxy_langfuse(path: str, request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Proxy requests to Langfuse"""
    if not settings.OBSERVABILITY_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Observability disabled")
    user_info = {"role": "admin"}
    return await proxy_request(settings.LANGFUSE_INTERNAL_URL, f"/{path}" if not path.startswith("/") else path, request, user_info)


@router.api_route("/embed/security/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
async def proxy_security(path: str, request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Proxy requests to Security Metrics"""
    if not settings.OBSERVABILITY_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Observability disabled")
    user_info = {"role": "admin"}
    security_url = "http://signoz:3301"
    return await proxy_request(security_url, f"/{path}" if not path.startswith("/") else path, request, user_info)
