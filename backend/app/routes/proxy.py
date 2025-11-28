from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import Response, StreamingResponse
from typing import Optional
import httpx
import time
import json

from app.services.mcp_service import mcp_service
from app.services.webui_auth_service import webui_auth_service

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


# ==================== MCP 프록시 ====================

@router.api_route("/mcp/{server_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_mcp(
    server_id: str, 
    path: str, 
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Response:
    """
    MCP 서버 리버스 프록시
    
    등록된 MCP 서버로 요청을 전달하고 호출 로그를 기록합니다.
    Kong Gateway를 통해 API Key 인증과 Rate Limiting이 적용됩니다.
    사용자는 권한이 있어야만 MCP 서버에 접근할 수 있습니다.
    
    Args:
        server_id: MCP 서버 ID
        path: MCP 서버 경로
        request: FastAPI 요청
        authorization: WebUI 인증 토큰
        
    Returns:
        MCP 서버 응답
    """
    # MCP 서버 조회
    server = await mcp_service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    if not server.get('enabled'):
        raise HTTPException(status_code=403, detail="MCP server is disabled")
    
    # 권한 체크 (Authorization 헤더에서 토큰 추출)
    user_id = None
    group_ids = []
    is_admin = False
    
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            user_info = await webui_auth_service.get_current_user_info(token)
            if user_info:
                user_id = user_info.get('id')
                group_ids = user_info.get('group_ids', [])
                is_admin = user_info.get('role') == 'admin'
        except:
            pass  # 인증 실패 시 권한 체크 진행
    
    # 관리자가 아닌 경우 권한 체크
    if not is_admin:
        if not user_id:
            raise HTTPException(
                status_code=401, 
                detail="Authentication required to access MCP server"
            )
        
        has_permission = await mcp_service.check_user_permission(
            server_id=server_id,
            user_id=user_id,
            group_ids=group_ids
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403, 
                detail="You don't have permission to access this MCP server"
            )
    
    # 요청 헤더 복사 (host 제거)
    headers = dict(request.headers)
    headers.pop("host", None)
    
    # MCP 서버 인증 설정 적용
    if server.get('auth_type') == 'api_key' and server.get('auth_config'):
        api_key = server['auth_config'].get('api_key')
        header_name = server['auth_config'].get('header_name', 'X-API-Key')
        if api_key:
            headers[header_name] = api_key
    elif server.get('auth_type') == 'bearer' and server.get('auth_config'):
        token = server['auth_config'].get('token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
    
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
    
    # MCP 서버 URL 구성
    mcp_url = f"{server['endpoint_url'].rstrip('/')}/{path}"
    
    start_time = time.time()
    status = "success"
    error_message = None
    response_payload = None
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=request.method,
                url=mcp_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 응답 헤더 수정
        response_headers = dict(response.headers)
        response_headers.pop("x-frame-options", None)
        response_headers["content-security-policy"] = "frame-ancestors 'self'"
        response_headers["access-control-allow-origin"] = "*"
        
        # 응답 페이로드 저장 (로깅용)
        try:
            response_payload = response.json()
        except:
            response_payload = {"raw": response.text[:1000]}  # 최대 1000자
        
        # 호출 로그 기록
        await mcp_service.log_call(
            server_id=server_id,
            tool_name=path.split('/')[0] if path else "unknown",
            request_payload={"path": path, "method": request.method},
            response_payload=response_payload,
            status="success" if response.status_code < 400 else "error",
            latency_ms=latency_ms
        )
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=response_headers,
            media_type=response.headers.get("content-type")
        )
        
    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        await mcp_service.log_call(
            server_id=server_id,
            tool_name=path.split('/')[0] if path else "unknown",
            request_payload={"path": path, "method": request.method},
            status="timeout",
            error_message="Request timeout",
            latency_ms=latency_ms
        )
        return Response(
            content="MCP server timeout",
            status_code=504,
            media_type="text/plain"
        )
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        await mcp_service.log_call(
            server_id=server_id,
            tool_name=path.split('/')[0] if path else "unknown",
            request_payload={"path": path, "method": request.method},
            status="error",
            error_message=str(e),
            latency_ms=latency_ms
        )
        return Response(
            content=f"MCP proxy error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )


@router.get("/mcp/{server_id}/sse")
async def proxy_mcp_sse(server_id: str, request: Request):
    """
    MCP SSE 스트림 프록시
    
    SSE 타입 MCP 서버의 이벤트 스트림을 프록시합니다.
    
    Args:
        server_id: MCP 서버 ID
        request: FastAPI 요청
        
    Returns:
        SSE 스트림
    """
    # MCP 서버 조회
    server = await mcp_service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    if not server.get('enabled'):
        raise HTTPException(status_code=403, detail="MCP server is disabled")
    
    if server.get('transport_type') != 'sse':
        raise HTTPException(status_code=400, detail="This endpoint is only for SSE transport type")
    
    # 요청 헤더 복사
    headers = dict(request.headers)
    headers.pop("host", None)
    
    # MCP 서버 인증 설정 적용
    if server.get('auth_type') == 'api_key' and server.get('auth_config'):
        api_key = server['auth_config'].get('api_key')
        header_name = server['auth_config'].get('header_name', 'X-API-Key')
        if api_key:
            headers[header_name] = api_key
    elif server.get('auth_type') == 'bearer' and server.get('auth_config'):
        token = server['auth_config'].get('token')
        if token:
            headers['Authorization'] = f"Bearer {token}"
    
    async def event_generator():
        """SSE 이벤트 스트림 생성기."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET",
                server['endpoint_url'],
                headers=headers
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

