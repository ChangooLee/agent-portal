"""FastAPI BFF Application"""
import logging
import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.responses import Response
from starlette.requests import Request
import httpx
import websockets
from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routes with explicit error handling
try:
    from app.routes import embed, kong_admin, chat, observability, news
    logger.info("✅ Old routes imported successfully")
except Exception as e:
    logger.error(f"❌ Old routes import failed: {e}")
    raise

try:
    from app.routes import proxy, agents, monitoring, projects, teams, mcp, gateway, datacloud, llm, agent_registry, text2sql, dart, webui_proxy
    from app.routes import realestate, health as health_route, legislation, slides  # New MCP agents + Slide Studio
    logger.info("✅ New routes (proxy, agents, monitoring, projects, teams, mcp, gateway, datacloud, llm, agent_registry, text2sql, dart, webui_proxy, realestate, health, legislation, slides) imported successfully")
except Exception as e:
    logger.error(f"❌ New routes import failed: {e}")
    import traceback
    traceback.print_exc()
    raise

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Agent Portal Backend for Frontend (BFF) - Chat, Observability, and Admin Tools",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Private Network Access middleware (Chrome's CORS policy for localhost from external IP)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class PrivateNetworkAccessMiddleware(BaseHTTPMiddleware):
    """Add Access-Control-Allow-Private-Network header for Chrome's Private Network Access policy."""
    async def dispatch(self, request: StarletteRequest, call_next):
        # Handle preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response

app.add_middleware(PrivateNetworkAccessMiddleware)

# 개발 환경에서 캐시 완전 비활성화 미들웨어
class NoCacheMiddleware(BaseHTTPMiddleware):
    """개발 환경에서 모든 캐시 헤더 제거 (응답 헤더만 수정)"""
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        
        # 개발 환경에서만 캐시 헤더 제거
        env = os.getenv("ENVIRONMENT", "local")
        is_dev = (env in ["local", "development", "docker"] or 
                  settings.ENVIRONMENT in ["local", "development", "docker"])
        
        if is_dev:
            # 응답 헤더에서 캐시 관련 헤더 제거 (MutableHeaders는 pop이 없으므로 del 사용)
            cache_headers = ["etag", "last-modified", "cache-control", "expires", "age"]
            for header in cache_headers:
                if header in response.headers:
                    del response.headers[header]
            # 강제로 no-cache 설정
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response

app.add_middleware(NoCacheMiddleware)

# ExceptionGroup 처리 미들웨어 (Python 3.11+)
import httpx

class ExceptionGroupMiddleware(BaseHTTPMiddleware):
    """ExceptionGroup을 안전하게 처리하는 미들웨어"""
    async def dispatch(self, request: StarletteRequest, call_next):
        try:
            return await call_next(request)
        except (httpx.StreamClosed, httpx.StreamError) as e:
            # httpx 스트림 에러는 정상 종료로 처리
            logger = logging.getLogger(__name__)
            logger.debug(f"Stream closed in middleware: {str(e)}")
            from starlette.responses import Response
            return Response(
                content="",
                status_code=200,
                media_type="text/plain"
            )
        except BaseExceptionGroup as eg:
            # ExceptionGroup 내부의 예외들을 개별적으로 처리
            logger = logging.getLogger(__name__)
            
            # 모든 예외 분석
            has_critical = False
            has_connection_error = False
            has_cancelled = False
            has_stream_closed = False
            other_exceptions = []
            
            for exc in eg.exceptions:
                if isinstance(exc, GeneratorExit):
                    has_critical = True
                    has_cancelled = True
                elif isinstance(exc, asyncio.CancelledError):
                    has_critical = True
                    has_cancelled = True
                elif isinstance(exc, (ConnectionError, BrokenPipeError, OSError)):
                    has_connection_error = True
                    has_critical = True
                elif isinstance(exc, (httpx.StreamClosed, httpx.StreamError)):
                    has_stream_closed = True
                    has_critical = True
                else:
                    other_exceptions.append(exc)
            
            # 정상적인 클라이언트 연결 종료는 DEBUG 레벨로 로깅
            if has_critical and (has_connection_error or has_cancelled or has_stream_closed) and not other_exceptions:
                logger.debug(f"Client connection closed normally: {len(eg.exceptions)} exceptions")
                from starlette.responses import Response
                return Response(
                    content="",
                    status_code=200,
                    media_type="text/plain"
                )
            elif has_critical and not other_exceptions:
                # 클라이언트 연결 종료이지만 다른 예외는 없음
                logger.debug(f"Stream cancelled or connection closed: {len(eg.exceptions)} exceptions")
                from starlette.responses import Response
                return Response(
                    content="",
                    status_code=200,
                    media_type="text/plain"
                )
            else:
                # 실제 에러가 포함된 경우만 WARNING 레벨로 로깅
                logger.warning(f"ExceptionGroup with unexpected errors: {len(eg.exceptions)} exceptions, {len(other_exceptions)} non-connection errors", exc_info=True)
                from starlette.responses import Response
                return Response(
                    content="Internal server error",
                    status_code=500,
                    media_type="text/plain"
                )

app.add_middleware(ExceptionGroupMiddleware)

# ExceptionGroup 전용 exception handler (Starlette 에러 미들웨어보다 우선)
from fastapi import Request as FastAPIRequest
from fastapi.responses import Response as FastAPIResponse

# BaseExceptionGroup은 Exception의 서브클래스가 아니므로 exception handler에 등록 불가
# ExceptionGroup을 사용하거나 미들웨어에서만 처리
# 미들웨어(ExceptionGroupMiddleware)에서 이미 처리하므로 exception handler는 불필요

# Include routers
# BFF 라우터를 먼저 등록 (우선순위 높음)
# /mcp, /datacloud, /gateway 등은 BFF에서 직접 처리
app.include_router(embed.router)
app.include_router(kong_admin.router)
app.include_router(chat.router)
app.include_router(observability.router)
app.include_router(news.router)
app.include_router(proxy.router)  # /proxy/* - BFF에서 직접 처리
app.include_router(proxy.api_router)  # /api/perplexica/* - Vite 프록시를 통한 요청 처리
app.include_router(agents.router)
app.include_router(monitoring.router)
app.include_router(projects.router)
app.include_router(teams.router)
# BFF 직접 처리 라우터들 (우선순위 높음)
# /api/* 경로는 BFF에서 직접 처리하므로, webui_proxy.api_router보다 먼저 등록되어야 함
app.include_router(mcp.router)  # /mcp/* - BFF에서 직접 처리
app.include_router(mcp.api_router)  # /api/mcp/* - Vite 프록시를 통한 요청 처리
app.include_router(gateway.router)  # /gateway/* - BFF에서 직접 처리
app.include_router(gateway.api_router)  # /api/gateway/* - Vite 프록시를 통한 요청 처리
app.include_router(datacloud.router)  # /datacloud/* - BFF에서 직접 처리
app.include_router(datacloud.api_router)  # /api/datacloud/* - Vite 프록시를 통한 요청 처리
app.include_router(llm.router)  # /llm/* - BFF에서 직접 처리
app.include_router(llm.api_router)  # /api/llm/* - Vite 프록시를 통한 요청 처리
app.include_router(text2sql.router)  # /text2sql/* - BFF에서 직접 처리
app.include_router(text2sql.api_router)  # /api/text2sql/* - Vite 프록시를 통한 요청 처리
app.include_router(agent_registry.router)
app.include_router(dart.router)  # /dart/* - DART 기업공시분석 에이전트
app.include_router(dart.api_router)  # /api/dart/* - Vite 프록시를 통한 요청 처리

# New MCP Agents - 부동산, 건강, 법률
app.include_router(realestate.router)  # /realestate/* - 부동산 분석 에이전트
app.include_router(realestate.api_router)  # /api/realestate/* - Vite 프록시를 통한 요청 처리
app.include_router(health_route.router)  # /health-agent/* - 건강/의료 분석 에이전트
app.include_router(health_route.api_router)  # /api/health-agent/* - Vite 프록시를 통한 요청 처리
app.include_router(legislation.router)  # /legislation/* - 법률 정보 분석 에이전트
app.include_router(legislation.api_router)  # /api/legislation/* - Vite 프록시를 통한 요청 처리
app.include_router(slides.router)  # /slides/* - Slide Studio
app.include_router(slides.api_router)  # /api/slides/* - Vite 프록시를 통한 요청 처리

# WebUI Backend 프록시는 마지막에 등록 (catch-all)
# /api/* 경로 중 BFF에서 처리하지 않는 것만 WebUI Backend로 프록시
app.include_router(webui_proxy.api_router)  # /api/* 직접 프록시 (catch-all)
app.include_router(webui_proxy.router)  # /api/webui/* 프록시

# Debug: 라우터 등록 확인
import logging
logger = logging.getLogger(__name__)
logger.info(f"Total routes registered: {len(app.routes)}")
monitoring_routes = [r for r in app.routes if hasattr(r, 'path') and 'monitoring' in r.path.lower()]
logger.info(f"Monitoring routes: {len(monitoring_routes)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }


# Root endpoint removed - handled by catch_all route
# In development, catch_all proxies to Vite Dev Server
# In production, catch_all serves static files

# Static files serving (for production builds)
# In development, Vite Dev Server handles static files via WebUI container
# In production, WebUI Backend serves static files
# Note: This catch-all route must be registered AFTER all other routes
WEBUI_BUILD_DIR = os.getenv("WEBUI_BUILD_DIR", "/app/webui/build")
WEBUI_DEV_SERVER = os.getenv("WEBUI_DEV_SERVER", "http://webui:3001")

# WebSocket 프록시 (Vite HMR) - 비활성화
# Single Port Architecture에서 BFF를 통한 WebSocket 프록시가 복잡하므로,
# Vite HMR은 폴링 모드로 작동하도록 설정했습니다.
# 폴링 모드는 HTTP 요청을 통해 파일 변경을 감지하므로 WebSocket이 필요 없습니다.
# 
# 주석 처리된 코드는 나중에 WebSocket 프록시가 필요할 때 참고용으로 남겨둡니다.
#
# @app.websocket("/")
# @app.websocket("/@vite/client")
# async def websocket_proxy_vite(websocket: WebSocket):
#     """WebSocket 프록시 for Vite HMR - 현재 비활성화 (폴링 모드 사용)"""
#     pass


# Socket.IO WebSocket 프록시
@app.websocket("/ws/socket.io/{path:path}")
async def websocket_proxy_socketio(websocket: WebSocket, path: str):
    """
    WebSocket 프록시 for Socket.IO
    
    Socket.IO WebSocket 연결을 WebUI Backend로 프록시합니다.
    """
    await websocket.accept()
    
    # WebUI Backend WebSocket URL
    query_string = websocket.url.query
    socketio_ws_url = f"ws://webui:8080/ws/socket.io/{path}{'?' + query_string if query_string else ''}"
    
    try:
        # WebUI Backend로 WebSocket 연결
        async with websockets.connect(socketio_ws_url) as backend_ws:
            # 연결 상태 추적
            client_closed = asyncio.Event()
            backend_closed = asyncio.Event()
            
            # 양방향 메시지 전달
            async def client_to_backend():
                try:
                    while not client_closed.is_set() and not backend_closed.is_set():
                        # FastAPI WebSocket은 receive()를 사용하여 메시지 타입을 확인
                        message = await websocket.receive()
                        if "text" in message:
                            await backend_ws.send(message["text"])
                        elif "bytes" in message:
                            await backend_ws.send(message["bytes"])
                except WebSocketDisconnect:
                    logger.info("Client disconnected from Socket.IO WebSocket proxy")
                    client_closed.set()
                except Exception as e:
                    logger.error(f"Error in client_to_backend: {e}")
                    client_closed.set()
            
            async def backend_to_client():
                try:
                    while not client_closed.is_set() and not backend_closed.is_set():
                        data = await backend_ws.recv()
                        # WebSocket이 닫혔는지 확인
                        if client_closed.is_set():
                            break
                        if isinstance(data, str):
                            try:
                                await websocket.send_text(data)
                            except (RuntimeError, ConnectionError) as e:
                                logger.info(f"WebSocket already closed, stopping backend_to_client: {e}")
                                break
                        else:
                            try:
                                await websocket.send_bytes(data)
                            except (RuntimeError, ConnectionError) as e:
                                logger.info(f"WebSocket already closed, stopping backend_to_client: {e}")
                                break
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebUI Backend disconnected from Socket.IO WebSocket proxy")
                    backend_closed.set()
                except Exception as e:
                    logger.error(f"Error in backend_to_client: {e}")
                    backend_closed.set()
            
            # 양방향 전달을 병렬로 실행
            await asyncio.gather(
                client_to_backend(),
                backend_to_client(),
                return_exceptions=True
            )
    except Exception as e:
        logger.error(f"Socket.IO WebSocket proxy error: {e}")
        try:
            await websocket.close(code=1011, reason=f"Socket.IO WebSocket proxy error: {str(e)}")
        except:
            pass


@app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def catch_all(path: str, request: Request):
    """
    Catch-all route for static files and SPA routing.
    
    - API routes are handled by specific routers above
    - Static files: In production, serve from build directory
    - In development, proxy to Vite Dev Server
    - WebSocket upgrade requests are handled by websocket_proxy above
    """
    # path가 비어있으면 request.url.path에서 추출
    if not path:
        path = request.url.path.lstrip("/")
    
    # Skip API routes and health check (already handled by routers)
    if path.startswith("api/") or path == "health":
        return Response(status_code=404)
    
    # In development, proxy to Vite Dev Server (including root path)
    # Treat "docker", "local", "development" as development environments
    env = os.getenv("ENVIRONMENT", "local")
    is_dev = (env in ["local", "development", "docker"] or 
              settings.ENVIRONMENT in ["local", "development", "docker"])
    if is_dev:
        try:
            # Vite 가상 모듈 경로 처리 (@id, @fs, @vite 등)
            # request.url.path를 직접 사용하여 원본 경로 가져오기 (URL 인코딩된 상태 유지)
            # FastAPI의 path 파라미터는 URL 디코딩을 수행하므로, request.url.path를 사용
            target_path = request.url.path
            
            # 디버깅: Vite 가상 모듈 경로 로깅
            if "@id" in target_path or "@fs" in target_path or "@vite" in target_path:
                logger.info(f"Vite virtual module path: {target_path} (decoded path: {path})")
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # 개발 환경에서는 캐시 헤더 완전 제거하여 304 방지
                request_headers = {}
                # 필수 헤더만 복사 (캐시 관련 헤더 제외)
                for key, value in request.headers.items():
                    key_lower = key.lower()
                    # 캐시 검증 헤더 완전 제거
                    if key_lower not in ["if-none-match", "if-modified-since", "if-match", "if-range"]:
                        request_headers[key] = value
                
                # User-Agent는 유지 (일부 서버에서 필요)
                if "user-agent" not in request_headers:
                    request_headers["User-Agent"] = request.headers.get("User-Agent", "Mozilla/5.0")
                
                # 브라우저 캐시 우회: 타임스탬프 쿼리 파라미터 추가
                # 단, Vite 가상 모듈 경로(@id, @fs, @vite 등)는 타임스탬프를 추가하지 않음
                import time
                params = dict(request.query_params)
                # Vite 가상 모듈 경로나 Vite 클라이언트 파일은 타임스탬프를 추가하지 않음
                is_vite_virtual = "@id" in target_path or "@fs" in target_path or "@vite" in target_path
                is_vite_client = "/node_modules/vite/" in target_path or "/@vite/client" in target_path
                if not is_vite_virtual and not is_vite_client and "_t" not in params and "t" not in params:
                    params["_t"] = str(int(time.time() * 1000))
                
                try:
                    response = await client.get(
                        f"{WEBUI_DEV_SERVER}{target_path}",
                        headers=request_headers,
                        params=params
                    )
                except httpx.TimeoutException:
                    logger.error(f"Vite Dev Server timeout: {target_path}")
                    return Response(status_code=504, content="Gateway Timeout")
                except httpx.ConnectError:
                    logger.error(f"Vite Dev Server connection failed: {WEBUI_DEV_SERVER}")
                    return Response(status_code=503, content="Service Unavailable")
                
                # 응답 헤더에서 캐시 관련 헤더 완전 제거 및 no-cache 설정
                response_headers = {}
                for key, value in response.headers.items():
                    key_lower = key.lower()
                    # 캐시 관련 헤더 완전 제거
                    if key_lower not in ["etag", "last-modified", "cache-control", "expires", "pragma", "age"]:
                        response_headers[key] = value
                
                # 개발 환경에서는 항상 no-cache (모든 캐시 비활성화)
                response_headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
                response_headers["Pragma"] = "no-cache"
                response_headers["Expires"] = "0"
                response_headers["X-Content-Type-Options"] = "nosniff"
                
                # 304 응답을 200으로 강제 변환 (개발 환경에서는 항상 최신 파일 제공)
                status_code = response.status_code
                if status_code == 304:
                    # 304인 경우 실제 파일을 다시 가져오기 위해 캐시 헤더 없이 재요청
                    logger.debug(f"Received 304 for {target_path}, forcing 200")
                    try:
                        # 304인 경우 타임스탬프를 업데이트하여 재요청
                        fresh_params = dict(params)
                        fresh_params["_t"] = str(int(time.time() * 1000))
                        fresh_response = await client.get(
                            f"{WEBUI_DEV_SERVER}{target_path}",
                            headers={k: v for k, v in request_headers.items() if k.lower() not in ["if-none-match", "if-modified-since"]},
                            params=fresh_params
                        )
                        status_code = 200
                        content = fresh_response.content
                        # Content-Type 유지
                        if "content-type" not in response_headers:
                            response_headers["Content-Type"] = fresh_response.headers.get("content-type", "text/html")
                    except Exception as e:
                        logger.warning(f"Failed to fetch fresh content for 304: {e}")
                        status_code = 200
                        content = response.content
                else:
                    content = response.content
                
                return Response(
                    content=content,
                    status_code=status_code,
                    headers=response_headers,
                    media_type=response_headers.get("Content-Type", response.headers.get("content-type", "text/html"))
                )
        except Exception as e:
            logger.error(f"Catch-all proxy error: {e}")
            # If Vite Dev Server is not available, return 404
            return Response(status_code=404)
    else:
        # In production, serve from build directory
        if os.path.exists(WEBUI_BUILD_DIR):
            file_path = os.path.join(WEBUI_BUILD_DIR, path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            # SPA fallback: serve index.html for non-file paths
            index_path = os.path.join(WEBUI_BUILD_DIR, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
        
        return Response(status_code=404)

