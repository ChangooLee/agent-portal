"""Embed proxy routes for observability tools"""
from fastapi import APIRouter, Request, Response, HTTPException, status, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from typing import Optional
import httpx
from app.config import get_settings
from app.middleware.rbac import get_current_user_role, require_admin_role, security

router = APIRouter()
settings = get_settings()


async def proxy_request(
    internal_url: str,
    path: str,
    request: Request,
    user_info: dict
) -> Response:
    """
    Proxy request to internal service with header rewriting for iframe embedding.
    """
    require_admin_role(user_info)
    
    # Build target URL
    target_url = f"{internal_url}{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    # Prepare headers (remove host, add forwarding headers)
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ["host", "content-length"]
    }
    
    # Prepare request body
    body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Forward request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=True
            )
            
            # Prepare response headers
            response_headers = dict(response.headers)
            
            # Remove headers that block iframe embedding
            headers_to_remove = [
                "x-frame-options",
                "content-security-policy",
                "frame-ancestors"
            ]
            for header in headers_to_remove:
                response_headers.pop(header, None)
            
            # Set permissive frame policy for embedding
            response_headers["X-Frame-Options"] = "SAMEORIGIN"
            
            # Remove content-length for streaming if needed
            if "content-length" in response_headers:
                # Keep it for non-streaming responses
                pass
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response_headers.get("content-type")
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Upstream service timeout"
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upstream service unavailable"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Proxy error: {str(e)}"
        )


@router.api_route(
    "/embed/helicone/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False
)
async def proxy_helicone(
    path: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)
):
    """Proxy requests to Helicone"""
    if not settings.OBSERVABILITY_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Observability disabled"
        )
    
    # Get user role (simplified - integrate with actual auth)
    user_info = {"role": "admin"}  # Placeholder - integrate with Open-WebUI auth
    
    return await proxy_request(
        settings.HELICONE_INTERNAL_URL,
        f"/{path}" if not path.startswith("/") else path,
        request,
        user_info
    )


@router.api_route(
    "/embed/langfuse/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False
)
async def proxy_langfuse(
    path: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)
):
    """Proxy requests to Langfuse"""
    if not settings.OBSERVABILITY_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Observability disabled"
        )
    
    # Get user role (simplified - integrate with actual auth)
    user_info = {"role": "admin"}  # Placeholder - integrate with Open-WebUI auth
    
    return await proxy_request(
        settings.LANGFUSE_INTERNAL_URL,
        f"/{path}" if not path.startswith("/") else path,
        request,
        user_info
    )


@router.api_route(
    "/embed/security/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False
)
async def proxy_security(
    path: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)
):
    """Proxy requests to Security Metrics (SigNoz/OpenObserve)"""
    if not settings.OBSERVABILITY_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Observability disabled"
        )
    
    # Get user role (simplified - integrate with actual auth)
    user_info = {"role": "admin"}  # Placeholder - integrate with Open-WebUI auth
    
    # TODO: Set actual security metrics URL when implemented
    security_url = "http://signoz:3301"  # Placeholder
    return await proxy_request(
        security_url,
        f"/{path}" if not path.startswith("/") else path,
        request,
        user_info
    )

