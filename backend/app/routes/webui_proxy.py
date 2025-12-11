"""
WebUI Backend Proxy Router

WebUI Backend (Open-WebUI Python) 프록시 라우터.
모든 WebUI Backend 요청을 BFF를 통해 프록시합니다.
"""
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import Response, StreamingResponse
from typing import Optional
import httpx
import os

# WebUI Backend 프록시 라우터
# /api/* 경로를 WebUI Backend로 프록시 (우선순위를 위해 /api/webui와 /api를 모두 처리)
router = APIRouter(prefix="/api/webui", tags=["webui-proxy"])
api_router = APIRouter(prefix="/api", tags=["webui-proxy"])

# WebUI Backend URL (Docker 내부 네트워크)
WEBUI_BACKEND_URL = os.getenv("WEBUI_BACKEND_URL", "http://webui:8080")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_webui_backend(
    path: str,
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Response:
    """
    WebUI Backend 프록시
    
    WebUI Backend (Open-WebUI Python)의 모든 요청을 프록시합니다.
    인증 토큰과 헤더를 그대로 전달합니다.
    
    Args:
        path: WebUI Backend 경로
        request: FastAPI 요청 객체
        authorization: Authorization 헤더 (Bearer token)
        
    Returns:
        WebUI Backend 응답
    """
    # WebUI Backend URL 구성
    # path가 이미 /api/로 시작하면 그대로 사용, 아니면 /api/를 추가
    if path.startswith("/api/"):
        # 이미 /api/로 시작하면 그대로 사용
        pass
    elif path.startswith("/"):
        # /로 시작하지만 /api/가 아니면 /api를 앞에 추가
        path = f"/api{path}"
    else:
        # /로 시작하지 않으면 /api/를 앞에 추가
        path = f"/api/{path}"
    
    target_url = f"{WEBUI_BACKEND_URL}{path}"
    
    # Query parameters 추가
    if request.query_params:
        target_url += f"?{request.query_params}"
    
    # 요청 헤더 복사 (host 제거)
    # request.headers는 Starlette Headers 객체이므로 직접 dict 변환 시 문제 발생 가능
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ["host", "content-length"]:
            headers[key] = value
    
    # Authorization 헤더 유지
    if authorization:
        headers["authorization"] = authorization
    
    # 요청 본문
    body = await request.body()
    
    # OPTIONS 요청 처리 (CORS preflight)
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
                "access-control-allow-headers": "*",
                "access-control-allow-credentials": "true",
            }
        )
    
    try:
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            # WebSocket 업그레이드 요청 처리
            if "upgrade" in headers.get("connection", "").lower() and headers.get("upgrade", "").lower() == "websocket":
                # WebSocket은 별도 처리 필요 (현재는 HTTP만 지원)
                raise HTTPException(status_code=501, detail="WebSocket proxy not yet implemented")
            
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            # 응답 헤더 복사
            response_headers = dict(response.headers)
            
            # CORS 헤더 추가
            response_headers["access-control-allow-origin"] = "*"
            response_headers["access-control-allow-credentials"] = "true"
            
            # Streaming response 처리
            if response.headers.get("content-type", "").startswith("text/event-stream"):
                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk
                
                return StreamingResponse(
                    generate(),
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type")
                )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="WebUI Backend timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WebUI Backend connection failed")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"WebUI Backend error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")


# WebUI Backend의 특정 경로들을 직접 프록시
@router.api_route("/openai/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_openai(path: str, request: Request) -> Response:
    """OpenAI API 프록시"""
    return await proxy_webui_backend(f"openai/{path}", request)


@router.api_route("/ollama/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_ollama(path: str, request: Request) -> Response:
    """Ollama API 프록시"""
    return await proxy_webui_backend(f"ollama/{path}", request)


@router.get("/health")
async def proxy_health(request: Request) -> Response:
    """WebUI Backend health check 프록시"""
    return await proxy_webui_backend("health", request)


# /api/v1/* 경로를 명시적으로 처리 (우선순위 최고 - catch-all보다 먼저)
@api_router.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_api_v1(
    path: str,
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Response:
    """
    /api/v1/* 경로를 WebUI Backend로 프록시
    
    /api/v1/auths/signin, /api/v1/chats 등 모든 /api/v1/* 경로를 처리합니다.
    """
    # WebUI Backend URL 구성
    target_path = f"/api/v1/{path}"
    target_url = f"{WEBUI_BACKEND_URL}{target_path}"
    
    # Query parameters 추가
    if request.query_params:
        target_url += f"?{request.query_params}"
    
    # 요청 헤더 복사
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ["host", "content-length"]:
            headers[key] = value
    
    # Authorization 헤더 유지
    if authorization:
        headers["authorization"] = authorization
    
    # 요청 본문
    body = await request.body()
    
    # OPTIONS 요청 처리 (CORS preflight)
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
                "access-control-allow-headers": "*",
                "access-control-allow-credentials": "true",
            }
        )
    
    try:
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            # 응답 헤더 복사
            response_headers = dict(response.headers)
            
            # CORS 헤더 추가
            response_headers["access-control-allow-origin"] = "*"
            response_headers["access-control-allow-credentials"] = "true"
            
            # Streaming response 처리
            if response.headers.get("content-type", "").startswith("text/event-stream"):
                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk
                
                return StreamingResponse(
                    generate(),
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type")
                )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="WebUI Backend timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WebUI Backend connection failed")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"WebUI Backend error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")


# /api/v1/* 경로를 명시적으로 처리 (우선순위 최고 - catch-all보다 먼저)
@api_router.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_api_v1(
    path: str,
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Response:
    """
    /api/v1/* 경로를 WebUI Backend로 프록시
    
    /api/v1/auths/signin, /api/v1/chats 등 모든 /api/v1/* 경로를 처리합니다.
    """
    # WebUI Backend URL 구성
    target_path = f"/api/v1/{path}"
    target_url = f"{WEBUI_BACKEND_URL}{target_path}"
    
    # Query parameters 추가
    if request.query_params:
        target_url += f"?{request.query_params}"
    
    # 요청 헤더 복사
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ["host", "content-length"]:
            headers[key] = value
    
    # Authorization 헤더 유지
    if authorization:
        headers["authorization"] = authorization
    
    # 요청 본문
    body = await request.body()
    
    # OPTIONS 요청 처리 (CORS preflight)
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
                "access-control-allow-headers": "*",
                "access-control-allow-credentials": "true",
            }
        )
    
    try:
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            # 응답 헤더 복사
            response_headers = dict(response.headers)
            
            # CORS 헤더 추가
            response_headers["access-control-allow-origin"] = "*"
            response_headers["access-control-allow-credentials"] = "true"
            
            # Streaming response 처리
            if response.headers.get("content-type", "").startswith("text/event-stream"):
                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk
                
                return StreamingResponse(
                    generate(),
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type")
                )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="WebUI Backend timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WebUI Backend connection failed")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"WebUI Backend error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")


# /api/config 직접 처리 (Vite 프록시가 리라이트하지 않는 경우 대비)
@api_router.get("/config")
async def proxy_config(request: Request) -> Response:
    """WebUI Backend /api/config 직접 프록시"""
    # proxy_webui_backend는 router의 라우트이므로 직접 호출 불가
    # 대신 내부 로직을 직접 구현
    target_url = f"{WEBUI_BACKEND_URL}/api/config"
    if request.query_params:
        target_url += f"?{request.query_params}"
    
    # 헤더를 올바르게 처리 (dict 변환 시 문제 방지)
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ["host", "content-length"]:
            headers[key] = value
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(target_url, headers=headers, params=request.query_params)
            response_headers = dict(response.headers)
            response_headers["access-control-allow-origin"] = "*"
            response_headers["access-control-allow-credentials"] = "true"
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="WebUI Backend timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WebUI Backend connection failed")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"WebUI Backend error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")


# /api/* 경로를 WebUI Backend로 프록시 (catch-all)
# 단, /api/mcp/*, /api/datacloud/*, /api/gateway/*, /api/monitoring/* 등은 제외
# 이들은 BFF의 다른 라우터에서 처리됩니다.
@api_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_api_catchall(
    path: str,
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> Response:
    """
    /api/* 경로를 WebUI Backend로 프록시 (catch-all)
    
    /api/v1/*, /api/models, /api/ollama, /api/openai 등 모든 /api/* 경로를 처리합니다.
    단, /api/mcp/*, /api/datacloud/*, /api/gateway/*, /api/monitoring/* 등은 제외됩니다.
    """
    # BFF에서 직접 처리하는 경로는 제외
    excluded_paths = ["mcp", "datacloud", "gateway", "monitoring", "projects", "teams", "agents", "news", "llm", "text2sql", "dart", "embed", "proxy"]
    path_parts = path.split("/")
    if path_parts and path_parts[0] in excluded_paths:
        # BFF의 다른 라우터에서 처리해야 하는 경로는 404 반환
        raise HTTPException(status_code=404, detail=f"Path /api/{path} should be handled by BFF router, not WebUI Backend proxy")
    
    # WebUI Backend URL 구성
    # path는 이미 /api/로 시작하지 않으므로 /api/를 추가
    if path.startswith("/"):
        target_path = f"/api{path}"
    else:
        target_path = f"/api/{path}"
    
    target_url = f"{WEBUI_BACKEND_URL}{target_path}"
    
    # Query parameters 추가
    if request.query_params:
        target_url += f"?{request.query_params}"
    
    # 요청 헤더 복사
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ["host", "content-length"]:
            headers[key] = value
    
    # Authorization 헤더 유지
    if authorization:
        headers["authorization"] = authorization
    
    # 요청 본문
    body = await request.body()
    
    # OPTIONS 요청 처리 (CORS preflight)
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
                "access-control-allow-headers": "*",
                "access-control-allow-credentials": "true",
            }
        )
    
    try:
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            # 응답 헤더 복사
            response_headers = dict(response.headers)
            
            # CORS 헤더 추가
            response_headers["access-control-allow-origin"] = "*"
            response_headers["access-control-allow-credentials"] = "true"
            
            # Streaming response 처리
            if response.headers.get("content-type", "").startswith("text/event-stream"):
                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk
                
                return StreamingResponse(
                    generate(),
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type")
                )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="WebUI Backend timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="WebUI Backend connection failed")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"WebUI Backend error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

