"""Kong Admin UI (Konga) proxy route"""
from fastapi import APIRouter, Request, Response, HTTPException, status, Security
import httpx
from app.config import get_settings
from app.middleware.rbac import require_admin_role, security
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter()
settings = get_settings()


@router.api_route("/embed/kong-admin/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], include_in_schema=False)
async def proxy_kong_admin(path: str, request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Proxy requests to Konga (Kong Admin UI). Only accessible by admin users via BFF proxy."""
    user_info = {"role": "admin"}
    require_admin_role(user_info)
    if not path or path == "":
        path = "/"
    elif not path.startswith("/"):
        path = f"/{path}"
    target_url = f"{settings.KONG_ADMIN_INTERNAL_URL}{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length", "authorization"]}
    body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.request(method=request.method, url=target_url, headers=headers, content=body)
            response_headers = dict(response.headers)
            for header in ["x-frame-options", "content-security-policy", "frame-ancestors"]:
                response_headers.pop(header, None)
            response_headers["X-Frame-Options"] = "SAMEORIGIN"
            return Response(content=response.content, status_code=response.status_code, headers=response_headers, media_type=response_headers.get("content-type", "text/html"))
    except httpx.TimeoutException:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Konga service timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Konga service unavailable. Please ensure Konga is running.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Proxy error: {str(e)}")
