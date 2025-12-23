"""
MCP Management API

MCP 서버 등록, 조회, 수정, 삭제, 연결 테스트 API 엔드포인트.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.requests import Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx

from app.services.mcp_service import mcp_service
from app.services.kong_service import kong_service


# MCP 라우터: /mcp/*와 /api/mcp/* 모두 처리
# Single Port Architecture에서 Vite 프록시가 /api/mcp/*를 /mcp/*로 리라이트하지만,
# 직접 /api/mcp/*로 접근하는 경우도 처리하기 위해 두 개의 라우터를 생성
router = APIRouter(prefix="/mcp", tags=["mcp"])
api_router = APIRouter(prefix="/api/mcp", tags=["mcp"])


# ==================== Request/Response 모델 ====================

class MCPServerCreate(BaseModel):
    """MCP 서버 생성 요청.
    
    모든 MCP 서버는 Kong Gateway를 통해 서비스됩니다.
    Kong Gateway 연동은 필수이며, API Key 인증과 Rate Limiting이 자동 적용됩니다.
    """
    name: str = Field(..., min_length=1, max_length=255, description="서버 이름")
    endpoint_url: str = Field(..., description="MCP 서버 엔드포인트 URL")
    description: Optional[str] = Field(None, description="서버 설명")
    transport_type: str = Field("streamable_http", description="전송 타입 (streamable_http, sse, stdio)")
    auth_type: str = Field("none", description="인증 타입 (none, api_key, bearer)")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="인증 설정")


class MCPServerGitHubCreate(BaseModel):
    """GitHub에서 stdio MCP 서버 생성 요청."""
    name: str = Field(..., min_length=1, max_length=255, description="서버 이름")
    github_url: str = Field(..., description="GitHub 저장소 URL")
    description: Optional[str] = Field(None, description="서버 설명")
    config: Dict[str, Any] = Field(..., description="서버 설정 (command, env 등)")


class MCPServerUpdate(BaseModel):
    """MCP 서버 수정 요청."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="서버 이름")
    endpoint_url: Optional[str] = Field(None, description="MCP 서버 엔드포인트 URL")
    description: Optional[str] = Field(None, description="서버 설명")
    transport_type: Optional[str] = Field(None, description="전송 타입")
    auth_type: Optional[str] = Field(None, description="인증 타입")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="인증 설정")
    enabled: Optional[bool] = Field(None, description="활성화 여부")


class MCPServerGitHubCreate(BaseModel):
    """GitHub에서 stdio MCP 서버 생성 요청."""
    name: str = Field(..., min_length=1, max_length=255, description="서버 이름")
    github_url: str = Field(..., description="GitHub 저장소 URL")
    description: Optional[str] = Field(None, description="서버 설명")
    config: Dict[str, Any] = Field(..., description="서버 설정 (command, env 등)")


class MCPToolInfo(BaseModel):
    """MCP 도구 정보."""
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None


class MCPServerResponse(BaseModel):
    """MCP 서버 응답.
    
    Kong Gateway 관련 정보는 보안상 사용자에게 노출하지 않습니다.
    """
    id: str
    name: str
    description: Optional[str]
    endpoint_url: str
    transport_type: str
    auth_type: str
    auth_config: Optional[Dict[str, Any]]
    enabled: bool
    last_health_check: Optional[datetime]
    health_status: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MCPServerListResponse(BaseModel):
    """MCP 서버 목록 응답."""
    servers: List[MCPServerResponse]
    total: int
    page: int
    size: int


class MCPToolResponse(BaseModel):
    """MCP 도구 응답."""
    id: str
    server_id: str
    tool_name: str
    tool_description: Optional[str]
    input_schema: Optional[Dict[str, Any]]
    discovered_at: datetime
    updated_at: datetime


class MCPTestResult(BaseModel):
    """MCP 연결 테스트 결과."""
    success: bool
    message: str
    tools: Optional[List[MCPToolInfo]] = None
    latency_ms: Optional[int] = None


class MCPPermissionCreate(BaseModel):
    """MCP 권한 부여 요청."""
    permission_type: str = Field(..., description="권한 타입 (user 또는 group)")
    target_id: str = Field(..., description="대상 ID (user_id 또는 group_id)")


class MCPPermissionResponse(BaseModel):
    """MCP 권한 응답."""
    id: str
    server_id: str
    permission_type: str
    target_id: str
    granted_by: Optional[str]
    granted_at: datetime


# ==================== API 엔드포인트 ====================

@router.get("/servers", response_model=MCPServerListResponse)
@api_router.get("/servers", response_model=MCPServerListResponse)
async def list_mcp_servers(
    enabled_only: bool = Query(False, description="활성화된 서버만 조회"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기")
):
    """MCP 서버 목록 조회.
    
    Args:
        enabled_only: 활성화된 서버만 조회
        page: 페이지 번호
        size: 페이지 크기
        
    Returns:
        서버 목록 및 페이지네이션 정보
    """
    result = await mcp_service.list_servers(
        enabled_only=enabled_only,
        page=page,
        size=size
    )
    return result


@router.post("/servers", response_model=MCPServerResponse)
@api_router.post("/servers", response_model=MCPServerResponse)
async def create_mcp_server(request: MCPServerCreate):
    """MCP 서버 등록.
    
    모든 MCP 서버는 Kong Gateway를 통해 서비스됩니다.
    API Key 인증과 Rate Limiting이 자동으로 적용됩니다.
    
    Args:
        request: 서버 생성 요청
        
    Returns:
        생성된 서버 정보 (Kong API Key 포함)
    """
    server = await mcp_service.create_server(
        name=request.name,
        endpoint_url=request.endpoint_url,
        description=request.description,
        transport_type=request.transport_type,
        auth_type=request.auth_type,
        auth_config=request.auth_config
    )
    return server


@router.post("/servers/github", response_model=MCPServerResponse)
@api_router.post("/servers/github", response_model=MCPServerResponse)
async def create_mcp_server_from_github(request: MCPServerGitHubCreate):
    """GitHub에서 코드를 pull 받아 stdio MCP 서버 등록.
    
    Args:
        request: GitHub 등록 요청
        
    Returns:
        생성된 서버 정보
    """
    server = await mcp_service.create_stdio_server(
        name=request.name,
        github_url=request.github_url,
        config=request.config,
        description=request.description
    )
    return server


@router.get("/servers/{server_id}", response_model=MCPServerResponse)
@api_router.get("/servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(server_id: str):
    """MCP 서버 상세 조회.
    
    Args:
        server_id: 서버 ID
        
    Returns:
        서버 정보
    """
    server = await mcp_service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


@router.put("/servers/{server_id}", response_model=MCPServerResponse)
@api_router.put("/servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(server_id: str, request: MCPServerUpdate):
    """MCP 서버 수정.
    
    Args:
        server_id: 서버 ID
        request: 서버 수정 요청
        
    Returns:
        수정된 서버 정보
    """
    server = await mcp_service.update_server(
        server_id=server_id,
        name=request.name,
        description=request.description,
        endpoint_url=request.endpoint_url,
        transport_type=request.transport_type,
        auth_type=request.auth_type,
        auth_config=request.auth_config,
        enabled=request.enabled
    )
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


@router.delete("/servers/{server_id}")
@api_router.delete("/servers/{server_id}")
async def delete_mcp_server(server_id: str):
    """MCP 서버 삭제.
    
    Args:
        server_id: 서버 ID
        
    Returns:
        삭제 결과
    """
    success = await mcp_service.delete_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return {"success": True, "message": "MCP server deleted"}


@router.post("/servers/{server_id}/test", response_model=MCPTestResult)
@api_router.post("/servers/{server_id}/test", response_model=MCPTestResult)
async def test_mcp_server(server_id: str):
    """MCP 서버 연결 테스트.
    
    MCP 서버에 연결하여 도구 목록을 가져오고 헬스 상태를 업데이트합니다.
    Streamable HTTP와 SSE 두 가지 전송 방식을 모두 지원합니다.
    
    Args:
        server_id: 서버 ID
        
    Returns:
        테스트 결과
    """
    server = await mcp_service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    import time
    import json
    start_time = time.time()
    
    transport_type = server.get('transport_type', 'streamable_http')
    
    try:
        if transport_type == 'sse':
            # SSE 방식: GET /sse → session_id 획득 → POST /messages/?session_id=...
            return await _test_mcp_server_sse(server, server_id, start_time)
        else:
            # Streamable HTTP 방식: POST /mcp with mcp-session-id header
            return await _test_mcp_server_streamable_http(server, server_id, start_time)
    
    except httpx.TimeoutException:
        await mcp_service.update_health_status(server_id, "unhealthy")
        return MCPTestResult(
            success=False,
            message="Connection timeout"
        )
    except httpx.HTTPStatusError as e:
        await mcp_service.update_health_status(server_id, "unhealthy")
        return MCPTestResult(
            success=False,
            message=f"HTTP error: {e.response.status_code}"
        )
    except Exception as e:
        await mcp_service.update_health_status(server_id, "unhealthy")
        return MCPTestResult(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


async def _test_mcp_server_streamable_http(server: dict, server_id: str, start_time: float) -> MCPTestResult:
    """Streamable HTTP 방식 MCP 서버 테스트.
    
    Args:
        server: 서버 정보
        server_id: 서버 ID
        start_time: 시작 시간
        
    Returns:
        테스트 결과
    """
    import time
    import json
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # 1. Initialize 요청
        init_payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agent-portal", "version": "1.0"}
            },
            "id": 1
        }
        
        response = await client.post(
            server['endpoint_url'],
            json=init_payload,
            headers=headers
        )
        response.raise_for_status()
        
        # 세션 ID 추출
        session_id = response.headers.get('mcp-session-id')
        
        # SSE 응답 파싱
        response_text = response.text
        init_result = _parse_sse_response(response_text)
        
        if not init_result or 'result' not in init_result:
            try:
                init_result = response.json()
            except:
                pass
        
        server_info = init_result.get('result', {}).get('serverInfo', {}) if init_result else {}
        server_name = server_info.get('name', 'Unknown')
        server_version = server_info.get('version', 'Unknown')
        
        # 2. initialized 알림 전송
        if session_id:
            init_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            notify_headers = headers.copy()
            notify_headers['mcp-session-id'] = session_id
            await client.post(
                server['endpoint_url'],
                json=init_notification,
                headers=notify_headers
            )
        
        # 3. tools/list 요청
        tools_payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        
        tools_headers = headers.copy()
        if session_id:
            tools_headers['mcp-session-id'] = session_id
        
        tools_response = await client.post(
            server['endpoint_url'],
            json=tools_payload,
            headers=tools_headers
        )
        
        tools = []
        if tools_response.status_code == 200:
            tools_result = _parse_sse_response(tools_response.text)
            if not tools_result:
                try:
                    tools_result = tools_response.json()
                except:
                    pass
            
            if tools_result and 'result' in tools_result:
                tool_list = tools_result['result'].get('tools', [])
                for tool in tool_list:
                    tools.append(MCPToolInfo(
                        name=tool.get('name', ''),
                        description=tool.get('description'),
                        input_schema=tool.get('inputSchema')
                    ))
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 도구 목록 동기화
        if tools:
            await mcp_service.sync_server_tools(
                server_id,
                [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools]
            )
        
        # 헬스 상태 업데이트
        await mcp_service.update_health_status(server_id, "healthy")
        
        return MCPTestResult(
            success=True,
            message=f"Connected to {server_name} v{server_version}. Found {len(tools)} tools.",
            tools=tools,
            latency_ms=latency_ms
        )


async def _test_mcp_server_sse(server: dict, server_id: str, start_time: float) -> MCPTestResult:
    """SSE 방식 MCP 서버 테스트.
    
    SSE 방식은 다음과 같이 동작합니다:
    1. GET /sse → SSE 연결, endpoint 이벤트에서 messages URL과 session_id 획득
    2. POST /messages/?session_id=... → JSON-RPC 메시지 전송 (응답은 "Accepted")
    3. SSE 스트림에서 실제 JSON-RPC 응답 수신
    
    Args:
        server: 서버 정보
        server_id: 서버 ID
        start_time: 시작 시간
        
    Returns:
        테스트 결과
    """
    import time
    import json
    import asyncio
    from urllib.parse import urljoin, urlparse
    
    sse_url = server['endpoint_url']
    base_url = sse_url.rsplit('/', 1)[0] + '/'  # /sse 제거하고 base URL 추출
    
    messages_endpoint = None
    server_name = "Unknown"
    server_version = "Unknown"
    tools = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. SSE 연결하여 messages endpoint 획득 및 메시지 수신
        async with client.stream("GET", sse_url, headers={"Accept": "text/event-stream"}, timeout=30.0) as sse_response:
            sse_response.raise_for_status()
            
            line_buffer = ""
            init_sent = False
            init_received = False
            tools_sent = False
            tools_received = False
            
            async for chunk in sse_response.aiter_bytes():
                line_buffer += chunk.decode('utf-8')
                
                # 라인 단위로 파싱
                while '\n' in line_buffer:
                    line, line_buffer = line_buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    if line.startswith('data: '):
                        data_str = line[6:]
                        
                        # 1단계: messages endpoint 획득
                        if not messages_endpoint and '/messages/' in data_str:
                            messages_endpoint = urljoin(base_url, data_str)
                            
                            # Initialize 요청 전송 (별도 클라이언트로)
                            async with httpx.AsyncClient(timeout=10.0) as msg_client:
                                init_payload = {
                                    "jsonrpc": "2.0",
                                    "method": "initialize",
                                    "params": {
                                        "protocolVersion": "2024-11-05",
                                        "capabilities": {},
                                        "clientInfo": {"name": "agent-portal", "version": "1.0"}
                                    },
                                    "id": 1
                                }
                                await msg_client.post(messages_endpoint, json=init_payload, headers={"Content-Type": "application/json"})
                                init_sent = True
                            continue
                        
                        # JSON-RPC 응답 파싱
                        if '"jsonrpc"' in data_str:
                            try:
                                data = json.loads(data_str)
                                
                                # 2단계: initialize 응답 처리
                                if data.get('id') == 1 and 'result' in data and not init_received:
                                    server_info = data['result'].get('serverInfo', {})
                                    server_name = server_info.get('name', 'Unknown')
                                    server_version = server_info.get('version', 'Unknown')
                                    init_received = True
                                    
                                    # initialized 알림 및 tools/list 요청 전송
                                    async with httpx.AsyncClient(timeout=10.0) as msg_client:
                                        # initialized 알림
                                        init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
                                        await msg_client.post(messages_endpoint, json=init_notification, headers={"Content-Type": "application/json"})
                                        
                                        # tools/list 요청
                                        tools_payload = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2}
                                        await msg_client.post(messages_endpoint, json=tools_payload, headers={"Content-Type": "application/json"})
                                        tools_sent = True
                                    continue
                                
                                # 3단계: tools/list 응답 처리
                                if data.get('id') == 2 and 'result' in data and not tools_received:
                                    tool_list = data['result'].get('tools', [])
                                    for tool in tool_list:
                                        tools.append(MCPToolInfo(
                                            name=tool.get('name', ''),
                                            description=tool.get('description'),
                                            input_schema=tool.get('inputSchema')
                                        ))
                                    tools_received = True
                                    break  # 모든 작업 완료
                                    
                            except json.JSONDecodeError:
                                continue
                
                if tools_received:
                    break
    
    if not messages_endpoint:
        await mcp_service.update_health_status(server_id, "unhealthy")
        return MCPTestResult(
            success=False,
            message="Failed to get messages endpoint from SSE"
        )
    
    if not tools_received:
        await mcp_service.update_health_status(server_id, "unhealthy")
        return MCPTestResult(
            success=False,
            message="Failed to receive tools list from SSE"
        )
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # 도구 목록 동기화
    if tools:
        await mcp_service.sync_server_tools(
            server_id,
            [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools]
        )
    
    # 헬스 상태 업데이트
    await mcp_service.update_health_status(server_id, "healthy")
    
    return MCPTestResult(
        success=True,
        message=f"Connected to {server_name} v{server_version}. Found {len(tools)} tools.",
        tools=tools,
        latency_ms=latency_ms
    )


def _parse_sse_response(response_text: str) -> Optional[Dict[str, Any]]:
    """SSE 응답에서 JSON 데이터 추출.
    
    Args:
        response_text: SSE 응답 텍스트
        
    Returns:
        파싱된 JSON 또는 None
    """
    import json
    for line in response_text.split('\n'):
        if line.startswith('data: '):
            try:
                return json.loads(line[6:])
            except json.JSONDecodeError:
                continue
    return None


@router.get("/servers/{server_id}/tools", response_model=List[MCPToolResponse])
@api_router.get("/servers/{server_id}/tools", response_model=List[MCPToolResponse])
async def get_mcp_server_tools(server_id: str):
    """MCP 서버의 도구 목록 조회.
    
    Args:
        server_id: 서버 ID
        
    Returns:
        도구 목록
    """
    server = await mcp_service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    tools = await mcp_service.get_server_tools(server_id)
    return tools


# ==================== 권한 관리 API ====================

@router.get("/servers/{server_id}/permissions", response_model=List[MCPPermissionResponse])
@api_router.get("/servers/{server_id}/permissions", response_model=List[MCPPermissionResponse])
async def get_mcp_server_permissions(server_id: str):
    """MCP 서버의 권한 목록 조회.
    
    Args:
        server_id: 서버 ID
        
    Returns:
        권한 목록
    """
    server = await mcp_service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    permissions = await mcp_service.get_server_permissions(server_id)
    return permissions


@router.post("/servers/{server_id}/permissions", response_model=MCPPermissionResponse)
@api_router.post("/servers/{server_id}/permissions", response_model=MCPPermissionResponse)
async def grant_mcp_permission(server_id: str, request: MCPPermissionCreate):
    """MCP 서버 접근 권한 부여.
    
    Args:
        server_id: 서버 ID
        request: 권한 부여 요청
        
    Returns:
        생성된 권한 정보
    """
    permission = await mcp_service.grant_permission(
        server_id=server_id,
        permission_type=request.permission_type,
        target_id=request.target_id,
        granted_by=None  # TODO: 현재 사용자 ID 추가
    )
    return permission


@router.delete("/servers/{server_id}/permissions/{permission_id}")
@api_router.delete("/servers/{server_id}/permissions/{permission_id}")
async def revoke_mcp_permission(server_id: str, permission_id: str):
    """MCP 서버 접근 권한 회수.
    
    Args:
        server_id: 서버 ID
        permission_id: 권한 ID
        
    Returns:
        삭제 결과
    """
    server = await mcp_service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    await mcp_service.revoke_permission(permission_id)
    return {"success": True, "message": "Permission revoked"}


# ==================== stdio 프로세스 관리 API ====================

@router.post("/servers/{server_id}/start")
@api_router.post("/servers/{server_id}/start")
async def start_stdio_process(server_id: str):
    """stdio MCP 서버 프로세스 시작.
    
    Args:
        server_id: 서버 ID
        
    Returns:
        시작 결과
    """
    success = await mcp_service.start_stdio_process(server_id)
    return {"success": success, "message": "Process started" if success else "Failed to start process"}


@router.post("/servers/{server_id}/stop")
@api_router.post("/servers/{server_id}/stop")
async def stop_stdio_process(server_id: str):
    """stdio MCP 서버 프로세스 중지.
    
    Args:
        server_id: 서버 ID
        
    Returns:
        중지 결과
    """
    success = await mcp_service.stop_stdio_process(server_id)
    return {"success": success, "message": "Process stopped" if success else "Failed to stop process"}


@router.post("/servers/{server_id}/restart")
@api_router.post("/servers/{server_id}/restart")
async def restart_stdio_process(server_id: str):
    """stdio MCP 서버 프로세스 재시작.
    
    Args:
        server_id: 서버 ID
        
    Returns:
        재시작 결과
    """
    success = await mcp_service.restart_stdio_process(server_id)
    return {"success": success, "message": "Process restarted" if success else "Failed to restart process"}


@router.get("/servers/{server_id}/status")
@api_router.get("/servers/{server_id}/status")
async def get_stdio_process_status(server_id: str):
    """stdio MCP 서버 프로세스 상태 조회.
    
    Args:
        server_id: 서버 ID
        
    Returns:
        프로세스 상태 정보
    """
    status = await mcp_service.get_stdio_process_status(server_id)
    return status


@router.get("/servers/{server_id}/logs")
@api_router.get("/servers/{server_id}/logs")
async def get_stdio_process_logs(
    server_id: str,
    lines: Optional[int] = Query(None, ge=1, le=10000, description="조회할 로그 라인 수")
):
    """stdio MCP 서버 프로세스 로그 조회.
    
    Args:
        server_id: 서버 ID
        lines: 조회할 로그 라인 수 (None이면 전체)
        
    Returns:
        로그 라인 리스트
    """
    logs = await mcp_service.get_stdio_process_logs(server_id, lines)
    return {"logs": logs, "count": len(logs)}


# ==================== HTTP Adapter 엔드포인트 ====================

@router.api_route("/adapters/{server_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def mcp_adapter_proxy(server_id: str, path: str, request: Request):
    """stdio MCP 어댑터 프록시.
    
    stdio MCP 서버를 HTTP로 래핑하여 Kong Gateway를 통해 접근할 수 있도록 합니다.
    
    Args:
        server_id: 서버 ID
        path: 요청 경로
        request: FastAPI 요청
        
    Returns:
        MCP 서버 응답
    """
    from app.mcp.http_adapter import http_adapter
    
    # 서버 정보 조회
    server = await mcp_service._get_server_internal(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    if server.get('transport_type') != 'stdio':
        raise HTTPException(status_code=400, detail="Not a stdio MCP server")
    
    # 어댑터로 요청 전달
    command = server.get('command')
    local_path = server.get('local_path')
    env_vars = server.get('env_vars')
    
    if not command:
        raise HTTPException(status_code=500, detail="command not found")
    
    # Parse env_vars
    env = {}
    if env_vars:
        if isinstance(env_vars, str):
            import json
            env = json.loads(env_vars)
        else:
            env = env_vars
    
    return await http_adapter.handle_request(
        server_id=server_id,
        request=request,
        command=command,
        cwd=local_path,
        env=env
    )


# Kong 관련 엔드포인트는 내부 관리용으로만 사용 (사용자에게 노출하지 않음)

