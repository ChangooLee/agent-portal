from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import Response, StreamingResponse
from typing import Optional
import httpx
import time
import json
import logging
import asyncio

from app.services.mcp_service import mcp_service
from app.services.webui_auth_service import webui_auth_service

router = APIRouter(prefix="/proxy", tags=["proxy"])
api_router = APIRouter(prefix="/api/perplexica", tags=["perplexica-proxy"])

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


@router.api_route("/perplexica/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_perplexica_api(path: str, request: Request) -> Response:
    """
    Perplexica API 리버스 프록시
    - httpx + Queue 기반 SSE 스트리밍 지원
    - CORS 헤더 추가
    """
    perplexica_url = f"http://perplexica:3000/api/{path}"
    logger = logging.getLogger(__name__)
    
    # 요청 본문 읽기
    body = await request.body()
    
    # OPTIONS 요청 처리 (CORS preflight)
    if request.method == "OPTIONS":
        return Response(
            content="",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            }
        )
    
    # SSE 스트리밍 처리 (POST /api/chat)
    if path == "chat" and request.method == "POST":
        # JSON 본문 파싱 및 검증
        request_json = None
        if body:
            try:
                request_json = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"[PROXY] Invalid JSON in request body: {e}")
                return Response(
                    content=json.dumps({"error": f"Invalid JSON: {str(e)}"}),
                    status_code=400,
                    media_type="application/json",
                    headers={"Access-Control-Allow-Origin": "*"}
                )
        
        if not request_json:
            logger.error("[PROXY] Empty request body")
            return Response(
                content=json.dumps({"error": "Empty request body"}),
                status_code=400,
                media_type="application/json",
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Queue 기반 스트리밍
        queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue()
        stream_error: Optional[Exception] = None
        
        async def fetch_stream():
            """백그라운드 태스크: 스트림을 읽어 큐에 넣음"""
            nonlocal stream_error
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST",
                        perplexica_url,
                        json=request_json,  # httpx가 자동으로 처리
                        headers={"Accept": "text/event-stream"}
                    ) as response:
                        logger.debug(f"[PROXY] Perplexica response status: {response.status_code}")
                        
                        if response.status_code >= 400:
                            error_body = await response.aread()
                            error_msg = json.dumps({
                                "type": "error",
                                "data": f"Perplexica error {response.status_code}: {error_body.decode()[:200]}"
                            }) + "\n"
                            await queue.put(error_msg.encode('utf-8'))
                            return
                        
                        async for chunk in response.aiter_bytes():
                            await queue.put(chunk)
                            
            except asyncio.CancelledError:
                logger.debug("[PROXY] Stream fetch cancelled")
            except Exception as e:
                logger.error(f"[PROXY] Stream fetch error: {e}", exc_info=True)
                stream_error = e
            finally:
                await queue.put(None)  # 종료 신호
        
        # 백그라운드 태스크 시작
        fetch_task = asyncio.create_task(fetch_stream())
        
        async def event_generator():
            """제너레이터: 큐에서 읽어 클라이언트로 전달"""
            try:
                while True:
                    try:
                        chunk = await asyncio.wait_for(queue.get(), timeout=120.0)
                    except asyncio.TimeoutError:
                        if fetch_task.done():
                            break
                        continue
                    
                    if chunk is None:
                        break
                    
                    yield chunk
                    
            except asyncio.CancelledError:
                logger.debug("[PROXY] Event generator cancelled")
            except GeneratorExit:
                logger.debug("[PROXY] Generator exited")
            finally:
                if not fetch_task.done():
                    fetch_task.cancel()
                    try:
                        await fetch_task
                    except asyncio.CancelledError:
                        pass
                
                # 에러가 있었다면 마지막에 에러 메시지 전송
                if stream_error:
                    error_msg = json.dumps({"type": "error", "data": f"Proxy error: {str(stream_error)}"}) + "\n"
                    yield error_msg.encode('utf-8')
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    # 비스트리밍 요청 처리 (GET, 기타 경로)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=request.method,
                url=perplexica_url,
                json=json.loads(body) if body and request.method != "GET" else None,
                params=dict(request.query_params) if request.query_params else None
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "content-type": response.headers.get("content-type", "application/json")
                }
            )
    except httpx.HTTPStatusError as e:
        logger.error(f"[PROXY] Perplexica proxy HTTP error: {e}")
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=e.response.status_code,
            media_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except httpx.RequestError as e:
        logger.error(f"[PROXY] Perplexica proxy request error: {e}")
        return Response(
            content=json.dumps({"error": f"Bad Gateway: {str(e)}"}),
            status_code=502,
            media_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        logger.error(f"[PROXY] Unexpected Perplexica proxy error: {e}", exc_info=True)
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500,
            media_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except (ConnectionError, BrokenPipeError, OSError) as e:
        # 클라이언트 연결 종료는 정상적인 상황일 수 있음
        logger = logging.getLogger(__name__)
        logger.debug(f"Client connection closed: {str(e)}")
        return Response(
            content="",
            status_code=200,
            media_type="text/plain"
        )
    except BaseExceptionGroup as eg:
        # Python 3.11+ ExceptionGroup 처리
        logger = logging.getLogger(__name__)
        logger.debug(f"ExceptionGroup in proxy: {len(eg.exceptions)} exceptions")
        # ExceptionGroup 내부의 예외들을 개별적으로 처리
        has_critical = False
        for exc in eg.exceptions:
            if isinstance(exc, (GeneratorExit, asyncio.CancelledError)):
                has_critical = True
                break
            elif isinstance(exc, (ConnectionError, BrokenPipeError, OSError)):
                logger.debug(f"Connection error in ExceptionGroup: {str(exc)}")
        
        if has_critical:
            # GeneratorExit나 CancelledError가 있으면 조용히 처리
            return Response(
                content="",
                status_code=200,
                media_type="text/plain"
            )
        else:
            # 기타 예외는 로그 남기고 에러 응답
            logger.warning(f"Unhandled exceptions in ExceptionGroup: {eg}")
            return Response(
                content="Proxy error: Multiple exceptions occurred",
                status_code=500,
                media_type="text/plain"
            )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Proxy error: {str(e)}", exc_info=True)
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
    
    # Kong Gateway를 통해 MCP 서버 호출
    from app.config import get_settings
    settings = get_settings()
    
    # Kong에 등록된 경우 Kong을 통해 호출, 아니면 직접 호출 (fallback)
    kong_service_id = server.get('kong_service_id')
    kong_api_key = server.get('kong_api_key')
    
    if kong_service_id and kong_api_key:
        # Kong Gateway를 통해 호출
        kong_proxy_url = settings.KONG_PROXY_URL
        mcp_url = f"{kong_proxy_url}/mcp/{server_id}/{path}"
        # Kong API Key 인증 추가
        headers['X-API-Key'] = kong_api_key
    else:
        # Kong에 등록되지 않은 경우 직접 호출 (fallback)
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


# API Router for /api/perplexica/* paths (Vite proxy bypass)
@api_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_perplexica_api_via_api(path: str, request: Request) -> Response:
    """
    Perplexica API 리버스 프록시 (via /api/perplexica/*)
    - /api/perplexica/* 경로를 /proxy/perplexica/api/*로 리라이트
    """
    logger = logging.getLogger(__name__)
    print(f"[PROXY-API] ===== Request received via /api/perplexica: {request.method} {path} =====")
    logger.info(f"[PROXY-API] Request received via /api/perplexica: {request.method} {path}")
    # 기존 proxy_perplexica_api 함수를 재사용
    return await proxy_perplexica_api(path, request)

