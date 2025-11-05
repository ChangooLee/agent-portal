"""Kong Admin UI (Konga) proxy route"""
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import StreamingResponse
import httpx
from app.config import get_settings
from app.middleware.rbac import get_current_user_role, require_admin_role, security
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter()
settings = get_settings()


@router.api_route(
    "/embed/kong-admin/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False
)
async def proxy_kong_admin(
    path: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)
):
    """
    Proxy requests to Konga (Kong Admin UI).
    Only accessible by admin users via BFF proxy.
    """
    # Get user role (simplified - integrate with actual auth)
    # TODO: Integrate with Open-WebUI authentication system
    user_info = {"role": "admin"}  # Placeholder
    
    # Require admin role
    require_admin_role(user_info)
    
    # Build target URL
    if not path or path == "":
        path = "/"
    elif not path.startswith("/"):
        path = f"/{path}"
    
    target_url = f"{settings.KONG_ADMIN_INTERNAL_URL}{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    # Prepare headers (remove host, add forwarding headers)
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ["host", "content-length", "authorization"]
    }
    
    # Prepare request body
    body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Forward request to Konga
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )
            
            # Prepare response headers
            response_headers = dict(response.headers)
            
            # Remove headers that block iframe embedding
            headers_to_remove = [
                "x-frame-options",
                "content-security-policy",
                "frame-ancestors",
            ]
            for header in headers_to_remove:
                response_headers.pop(header, None)
            
            # Set permissive frame policy for embedding
            response_headers["X-Frame-Options"] = "SAMEORIGIN"
            
            # Handle cookies - make them HttpOnly and SameSite=Lax for security
            if "set-cookie" in response_headers:
                # Note: This is a simplified approach. For production,
                # you may need to parse and rewrite cookie attributes
                cookies = response_headers.get("set-cookie", "")
                # In production, parse cookies and add HttpOnly; SameSite=Lax
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response_headers.get("content-type", "text/html")
            )
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Konga service timeout"
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Konga service unavailable. Please ensure Konga is running."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Proxy error: {str(e)}"
        )


