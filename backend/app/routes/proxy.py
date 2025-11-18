from fastapi import APIRouter, Request
from fastapi.responses import Response
import httpx

router = APIRouter(prefix="/proxy", tags=["proxy"])

@router.api_route("/langflow/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_langflow(path: str, request: Request) -> Response:
    """
    Langflow 리버스 프록시
    - X-Frame-Options 제거
    - CORS 헤더 추가
    - CSP frame-ancestors 'self' 설정
    """
    # Langflow 내부 포트는 7860 (docker-compose에서 7861:7860으로 매핑)
    langflow_url = f"http://langflow:7860/{path}"
    
    # 요청 헤더 복사 (host 제거)
    headers = dict(request.headers)
    headers.pop("host", None)
    
    # 요청 본문
    body = await request.body()
    
    # OPTIONS 요청 처리 (CORS preflight)
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "access-control-allow-headers": "*",
            }
        )
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.request(
                method=request.method,
                url=langflow_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
        
        # 응답 헤더 수정
        response_headers = dict(response.headers)
        
        # X-Frame-Options 제거 (iframe 허용)
        response_headers.pop("x-frame-options", None)
        
        # CSP 헤더 수정 (frame-ancestors 'self' 허용)
        if "content-security-policy" in response_headers:
            csp = response_headers["content-security-policy"]
            # frame-ancestors 지시어가 있으면 수정, 없으면 추가
            if "frame-ancestors" in csp:
                csp = csp.replace("frame-ancestors 'none'", "frame-ancestors 'self'")
            else:
                csp += "; frame-ancestors 'self'"
            response_headers["content-security-policy"] = csp
        else:
            response_headers["content-security-policy"] = "frame-ancestors 'self'"
        
        # CORS 헤더 추가
        response_headers["access-control-allow-origin"] = "*"
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get("content-type")
        )
    except httpx.TimeoutException:
        return Response(
            content="Langflow service timeout",
            status_code=504,
            media_type="text/plain"
        )
    except Exception as e:
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )


@router.api_route("/flowise/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_flowise(path: str, request: Request) -> Response:
    """
    Flowise 리버스 프록시 (향후 확장)
    """
    flowise_url = f"http://flowise:3000/{path}"
    
    headers = dict(request.headers)
    headers.pop("host", None)
    body = await request.body()
    
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "access-control-allow-headers": "*",
            }
        )
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.request(
                method=request.method,
                url=flowise_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
        
        response_headers = dict(response.headers)
        response_headers.pop("x-frame-options", None)
        response_headers["content-security-policy"] = "frame-ancestors 'self'"
        response_headers["access-control-allow-origin"] = "*"
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get("content-type")
        )
    except Exception as e:
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )


@router.api_route("/autogen/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_autogen(path: str, request: Request) -> Response:
    """
    AutoGen Studio 리버스 프록시 (향후 확장)
    """
    autogen_url = f"http://autogen-studio:5050/{path}"
    
    headers = dict(request.headers)
    headers.pop("host", None)
    body = await request.body()
    
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "access-control-allow-headers": "*",
            }
        )
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.request(
                method=request.method,
                url=autogen_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
        
        response_headers = dict(response.headers)
        response_headers.pop("x-frame-options", None)
        response_headers["content-security-policy"] = "frame-ancestors 'self'"
        response_headers["access-control-allow-origin"] = "*"
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get("content-type")
        )
    except Exception as e:
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )

