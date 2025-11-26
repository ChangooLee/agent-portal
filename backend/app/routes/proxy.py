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


@router.api_route("/agentops-dashboard/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_agentops_dashboard(path: str, request: Request) -> Response:
    """
    AgentOps Dashboard 리버스 프록시
    
    서비스 계정 세션 쿠키를 자동으로 주입하여 인증된 요청을 전달합니다.
    이를 통해 iframe 내에서도 AgentOps Dashboard가 정상 동작합니다.
    """
    from app.services.agentops_session_service import agentops_session_service
    
    agentops_dashboard_url = f"http://host.docker.internal:3006/{path}"
    
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
        # 서비스 계정 세션 쿠키 획득
        session_cookie = await agentops_session_service.get_session_cookie()
        if session_cookie:
            # 기존 쿠키와 병합
            existing_cookie = headers.get("cookie", "")
            if existing_cookie:
                headers["cookie"] = f"{existing_cookie}; {session_cookie}"
            else:
                headers["cookie"] = session_cookie
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.request(
                method=request.method,
                url=agentops_dashboard_url,
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


@router.api_route("/agentops-api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_agentops_api(path: str, request: Request) -> Response:
    """
    AgentOps API 리버스 프록시
    
    서비스 계정 세션 쿠키를 자동으로 주입하여 인증된 요청을 전달합니다.
    Dashboard에서 API 호출 시 사용됩니다.
    """
    from app.services.agentops_session_service import agentops_session_service
    
    agentops_api_url = f"http://host.docker.internal:8003/{path}"
    
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
                "access-control-allow-credentials": "true",
            }
        )
    
    try:
        # 서비스 계정 세션 쿠키 획득
        session_cookie = await agentops_session_service.get_session_cookie()
        if session_cookie:
            # 기존 쿠키와 병합
            existing_cookie = headers.get("cookie", "")
            if existing_cookie:
                headers["cookie"] = f"{existing_cookie}; {session_cookie}"
            else:
                headers["cookie"] = session_cookie
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.request(
                method=request.method,
                url=agentops_api_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
        
        response_headers = dict(response.headers)
        response_headers.pop("x-frame-options", None)
        response_headers["access-control-allow-origin"] = "*"
        response_headers["access-control-allow-credentials"] = "true"
        
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


@router.api_route("/grafana/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_grafana(path: str, request: Request) -> Response:
    """
    Grafana 리버스 프록시 (Monitoring Dashboard)
    - X-Frame-Options 제거 (iframe 허용)
    - CORS 헤더 추가
    - CSP frame-ancestors 'self' 설정
    """
    # Grafana 내부 포트는 3000 (docker-compose에서 3005:3000으로 매핑)
    grafana_url = f"http://grafana:3000/{path}"
    
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
                url=grafana_url,
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
            content="Grafana service timeout",
            status_code=504,
            media_type="text/plain"
        )
    except Exception as e:
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )


@router.api_route("/langfuse/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_langfuse(path: str, request: Request) -> Response:
    """
    Langfuse 리버스 프록시 (Agent Quality Management)
    - X-Frame-Options 제거 (iframe 허용)
    - CORS 헤더 추가
    - CSP frame-ancestors 'self' 설정
    """
    # Langfuse 내부 포트는 3000 (docker-compose에서 3003:3000으로 매핑)
    langfuse_url = f"http://langfuse:3000/{path}"
    
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
                url=langfuse_url,
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
            content="Langfuse service timeout",
            status_code=504,
            media_type="text/plain"
        )
    except Exception as e:
        return Response(
            content=f"Proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )

