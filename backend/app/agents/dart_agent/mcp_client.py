"""
MCP Client for OpenDart MCP Server (stdio)

Agent Portal용 MCP 클라이언트 - stdio 방식으로 MCP 서버와 통신.
기존 HTTP Streamable 방식을 stdio로 변경.

참조: /Users/lchangoo/Workspace/agent-platform/connection/mcp_direct_client.py
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import uuid
from datetime import datetime

import httpx
from pydantic import BaseModel, Field, create_model

# OTEL 기록 함수
from app.agents.dart_agent.metrics import start_tool_call_span

logger = logging.getLogger(__name__)

# stdio MCP 클라이언트 import
from app.mcp.stdio_client import MCPStdioClient
from app.mcp.process_manager import process_manager
from app.mcp.http_adapter import http_adapter


# =============================================================================
# MCP 도구 정의
# =============================================================================

@dataclass
class MCPTool:
    """MCP 도구 정보"""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)


class MCPToolCall(BaseModel):
    """MCP 도구 호출 결과"""
    name: str
    result: Any
    error: Optional[str] = None


# =============================================================================
# MCP HTTP 클라이언트
# =============================================================================

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


# =============================================================================
# MCP stdio 클라이언트 래퍼
# =============================================================================

class MCPStdioClientWrapper:
    """
    OpenDart MCP stdio 클라이언트 래퍼.
    
    MCPHTTPClient와 동일한 인터페이스를 제공하지만 stdio 방식으로 통신.
    
    Example:
        client = MCPStdioClientWrapper(server_id="xxx")
        await client.connect()
        tools = client.get_tools()
        result = await client.call_tool("search_disclosure", {"company": "삼성전자"})
    """
    
    def __init__(
        self,
        server_id: str,
        timeout: float = 600.0,  # 10분 - 복잡한 도구 호출 지원
        max_retries: int = 3
    ):
        """
        Args:
            server_id: MCP 서버 ID
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        self.server_id = server_id
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._connected = False
        self._tools: List[MCPTool] = []
        self._stdio_client: Optional[MCPStdioClient] = None
        self._server_info: Optional[Dict[str, Any]] = None
        
        # MCPHTTPClient 호환성을 위한 속성
        self.endpoint = f"stdio://{server_id}"
        self.kong_api_key = None
    
    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected
    
    async def connect(self) -> bool:
        """MCP 서버에 연결하고 도구 목록을 조회"""
        logger.info(f"Connecting to MCP server via stdio: {self.server_id}")
        
        try:
            # MCP 서비스에서 서버 정보 가져오기
            from app.services.mcp_service import mcp_service
            self._server_info = await mcp_service._get_server_internal(self.server_id)
            
            if not self._server_info:
                raise RuntimeError(f"MCP server {self.server_id} not found")
            
            # stdio 서버인지 확인
            transport_type = self._server_info.get('transport_type')
            if transport_type != 'stdio':
                raise RuntimeError(f"MCP server {self.server_id} is not stdio type (got {transport_type})")
            
            # process_manager에서 프로세스 확인 (DB 상태보다 실제 프로세스 상태가 우선)
            existing_process = process_manager.get_process(self.server_id)
            if existing_process is None or existing_process.returncode is not None:
                # process_manager에 프로세스가 없거나 종료됨 - 시작 필요
                logger.info(f"Starting MCP server process: {self.server_id}")
                await mcp_service.start_stdio_process(self.server_id)
                # 프로세스가 process_manager에 등록될 때까지 대기 (최대 5초)
                max_wait = 5.0
                wait_interval = 0.2
                waited = 0.0
                while waited < max_wait:
                    existing_process = process_manager.get_process(self.server_id)
                    if existing_process is not None and existing_process.returncode is None:
                        logger.info(f"Process {self.server_id} registered in process_manager (PID: {existing_process.pid})")
                        break
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                else:
                    # 프로세스가 등록되지 않음
                    logger.warning(f"Process {self.server_id} not found in process_manager after {max_wait}s")
                    raise RuntimeError(f"Failed to start MCP server process: {self.server_id}")
            else:
                logger.info(f"Process {self.server_id} already running in process_manager (PID: {existing_process.pid})")
            
            # stdio 클라이언트 생성
            self._stdio_client = MCPStdioClient(self.server_id)
            
            # 서버 정보에서 command, cwd, env 가져오기
            command = self._server_info.get('command')
            local_path = self._server_info.get('local_path')
            env_vars = self._server_info.get('env_vars')
            
            if not command:
                raise RuntimeError(f"MCP server {self.server_id} has no command")
            
            # env_vars 파싱
            env = {}
            if env_vars:
                if isinstance(env_vars, str):
                    env = json.loads(env_vars)
                else:
                    env = env_vars
            
            # 기존 프로세스 가져오기 (다시 확인)
            existing_process = process_manager.get_process(self.server_id)
            if existing_process is None:
                raise RuntimeError(f"Process {self.server_id} not found in process_manager after start attempt")
            else:
                logger.info(f"Found existing process for {self.server_id} (PID: {existing_process.pid}, returncode: {existing_process.returncode})")
            
            # 연결
            tools = await self._stdio_client.connect(
                command=command,
                cwd=local_path,
                env=env,
                reuse_existing_process=True,
                existing_process=existing_process
            )
            
            # 도구 목록 변환
            self._tools = []
            for tool in tools:
                self._tools.append(MCPTool(
                    name=tool.name,
                    description=tool.description or '',
                    input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                ))
            
            self._connected = True
            logger.info(f"Connected to MCP server via stdio: {len(self._tools)} tools loaded")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server via stdio: {e}", exc_info=True)
            self._connected = False
            raise
    
    def get_tools(self) -> List[MCPTool]:
        """도구 목록 반환"""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")
        return self._tools
    
    @property
    def tool_count(self) -> int:
        """도구 수"""
        return len(self._tools) if self._connected else 0
    
    def filter_tools(self, name_filter: Optional[Callable[[str], bool]] = None) -> List[MCPTool]:
        """도구 필터링 (MCPHTTPClient 호환성)"""
        tools = self.get_tools()
        if name_filter:
            return [t for t in tools if name_filter(t.name)]
        return tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolCall:
        """도구 호출 (OTEL 자동 기록)"""
        if not self._connected or not self._stdio_client:
            raise RuntimeError("Not connected to MCP server")
        
        start_time = datetime.now()
        
        # OTEL span으로 도구 호출 기록
        with start_tool_call_span(tool_name, arguments) as (span, record_result):
            try:
                # stdio 클라이언트를 통해 도구 호출
                # MCPStdioClient는 call_tool 메서드를 사용
                if not self._stdio_client.is_connected():
                    # 재연결
                    command = self._server_info.get('command')
                    local_path = self._server_info.get('local_path')
                    env_vars = self._server_info.get('env_vars')
                    env = {}
                    if env_vars:
                        if isinstance(env_vars, str):
                            env = json.loads(env_vars)
                        else:
                            env = env_vars
                    
                    existing_process = process_manager.get_process(self.server_id)
                    await self._stdio_client.connect(
                        command=command,
                        cwd=local_path,
                        env=env,
                        reuse_existing_process=True,
                        existing_process=existing_process
                    )
                
                # call_tool 메서드 사용
                result = await self._stdio_client.call_tool(tool_name, arguments)
                
                # 결과가 리스트인 경우 처리 (MCP SDK는 content 리스트 반환)
                # agent-platform 패턴: content 리스트에서 text 추출
                if isinstance(result, list):
                    # TextContent 객체들을 문자열로 변환
                    result_text = ""
                    for item in result:
                        if hasattr(item, 'text'):
                            # MCP SDK TextContent 객체
                            text_val = item.text
                            if isinstance(text_val, bytes):
                                text_val = text_val.decode('utf-8', errors='replace')
                            result_text += text_val
                        elif isinstance(item, str):
                            result_text += item
                        elif isinstance(item, dict):
                            # {"type": "text", "text": "..."} 형식
                            if 'text' in item:
                                text_val = item['text']
                                if isinstance(text_val, bytes):
                                    text_val = text_val.decode('utf-8', errors='replace')
                                result_text += text_val
                            elif 'content' in item:
                                result_text += str(item['content'])
                            else:
                                # 전체 dict를 JSON으로 변환
                                result_text += json.dumps(item, ensure_ascii=False)
                        elif isinstance(item, bytes):
                            # bytes 직접 처리
                            result_text += item.decode('utf-8', errors='replace')
                        else:
                            result_text += str(item)
                    
                    # 빈 문자열이면 JSON으로 변환
                    result = result_text if result_text else json.dumps(result, ensure_ascii=False, default=str)
                elif isinstance(result, bytes):
                    # bytes 직접 반환된 경우
                    result = result.decode('utf-8', errors='replace')
                
                # OTEL에 결과 기록
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                record_result({"result": str(result)[:500], "latency_ms": latency_ms})
                
                return MCPToolCall(
                    name=tool_name,
                    result=result,
                    error=None
                )
            except Exception as e:
                logger.error(f"Failed to call tool {tool_name}: {e}", exc_info=True)
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                record_result({"error": str(e), "latency_ms": latency_ms})
                return MCPToolCall(
                    name=tool_name,
                    result=None,
                    error=str(e)
                )
    
    async def disconnect(self) -> None:
        """연결 종료"""
        # stdio 클라이언트는 프로세스를 종료하지 않음 (process_manager가 관리)
        self._connected = False
        self._stdio_client = None
        logger.info(f"Disconnected from MCP server: {self.server_id}")


# =============================================================================
# MCP HTTP 클라이언트 (레거시)
# =============================================================================

class MCPHTTPClient:
    """
    OpenDart MCP Streamable HTTP 클라이언트.
    
    JSON-RPC 2.0 프로토콜 over HTTP를 사용하여 MCP 서버와 통신.
    
    Example:
        client = MCPHTTPClient("http://121.141.60.219:8089/mcp")
        await client.connect()
        tools = client.get_tools()
        result = await client.call_tool("search_disclosure", {"company": "삼성전자"})
    """
    
    def __init__(
        self,
        endpoint: str,
        timeout: float = 600.0,  # 10분 - 복잡한 도구 호출 지원
        max_retries: int = 3,
        kong_api_key: Optional[str] = None
    ):
        """
        Args:
            endpoint: MCP 서버 URL (예: http://121.141.60.219:8089/mcp 또는 http://kong:8000/mcp/{server_id})
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
            kong_api_key: Kong Gateway API Key (Kong을 통한 접근 시 필요)
        """
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.kong_api_key = kong_api_key
        
        self._connected = False
        self._tools: List[MCPTool] = []
        self._http_client: Optional[httpx.AsyncClient] = None
        self._session_id: Optional[str] = None
        
    async def connect(self) -> bool:
        """MCP 서버에 연결하고 도구 목록을 조회"""
        logger.info(f"Connecting to MCP server: {self.endpoint}")
        
        try:
            # HTTP 클라이언트 생성
            # MCP 서버는 application/json과 text/event-stream 둘 다를 Accept해야 함
            # httpx.AsyncClient의 기본 헤더는 설정하지 않고, 각 요청마다 명시적으로 헤더 전달
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout)
            )
            
            # #region agent log
            try:
                log_entry = {
                    "location": "mcp_client.py:89",
                    "message": "Creating HTTP client for MCP",
                    "data": {
                        "endpoint": self.endpoint,
                        "headers": {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
                    },
                    "timestamp": int(__import__("time").time() * 1000),
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "B"
                }
                with open("/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except:
                pass
            # #endregion
            
            # 1. Initialize 요청으로 세션 ID 획득
            await self._initialize()
            
            # 2. Initialized 알림 전송
            await self._send_initialized()
            
            # 3. 도구 목록 조회
            await self._load_tools()
            
            self._connected = True
            logger.info(f"Connected to MCP server: {len(self._tools)} tools loaded")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """연결 종료"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False
        self._tools = []
        self._session_id = None
        logger.info("Disconnected from MCP server")
    
    async def _initialize(self):
        """MCP 서버 초기화 및 세션 ID 획득"""
        if not self._http_client:
            raise RuntimeError("MCP client not connected")
        
        init_payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "agent-portal-dart", "version": "1.0"}
            },
            "id": 1
        }
        
        # #region agent log
        try:
            log_entry = {
                "location": "mcp_client.py:_initialize",
                "message": "Sending initialize request",
                "data": {"endpoint": self.endpoint},
                "timestamp": int(__import__("time").time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B"
            }
            with open("/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except:
            pass
        # #endregion
        
        # #region agent log
        try:
            import time
            log_entry = {
                "location": "mcp_client.py:_initialize:177",
                "message": "Sending initialize POST request",
                "data": {
                    "endpoint": self.endpoint,
                    "payload_method": init_payload.get("method"),
                    "client_headers": dict(self._http_client.headers) if hasattr(self._http_client, 'headers') else {}
                },
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B"
            }
            log_path = "/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as log_err:
            logger.debug(f"Debug log write failed: {log_err}")
        # #endregion
        
        # Accept 헤더를 명시적으로 전달
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # Kong API Key가 있으면 헤더에 추가
        if self.kong_api_key:
            headers["X-API-Key"] = self.kong_api_key
            logger.debug(f"Added X-API-Key header (first 20): {self.kong_api_key[:20]}...")
        
        # #region agent log
        try:
            import time
            log_entry = {
                "location": "mcp_client.py:_initialize:220",
                "message": "About to send POST request",
                "data": {
                    "endpoint": self.endpoint,
                    "headers": headers,
                    "payload_method": init_payload.get("method")
                },
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B"
            }
            log_path = "/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as log_err:
            logger.debug(f"Debug log write failed: {log_err}")
        # #endregion
        
        response = await self._http_client.post(
            self.endpoint,
            json=init_payload,
            headers=headers
        )
        
        # #region agent log
        try:
            import time
            log_entry = {
                "location": "mcp_client.py:_initialize:210",
                "message": "Initialize response received",
                "data": {
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers),
                    "has_session_id": 'mcp-session-id' in response.headers,
                    "response_text_preview": response.text[:200] if hasattr(response, 'text') else None
                },
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B"
            }
            log_path = "/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as log_err:
            logger.debug(f"Debug log write failed: {log_err}")
        # #endregion
        
        response.raise_for_status()
        
        # 세션 ID 추출
        self._session_id = response.headers.get('mcp-session-id')
        
        # SSE 응답 파싱 (text/event-stream 형식)
        response_text = response.text
        init_result = _parse_sse_response(response_text)
        
        # SSE 파싱 실패 시 일반 JSON으로 시도
        if not init_result or 'result' not in init_result:
            try:
                init_result = response.json()
            except:
                pass
        
        # #region agent log
        try:
            import time
            log_entry = {
                "location": "mcp_client.py:_initialize:245",
                "message": "Initialize response received",
                "data": {
                    "status_code": response.status_code,
                    "session_id": self._session_id,
                    "content_type": response.headers.get('content-type'),
                    "has_init_result": init_result is not None,
                    "response_text_preview": response_text[:200] if response_text else None
                },
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B"
            }
            log_path = "/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as log_err:
            logger.debug(f"Debug log write failed: {log_err}")
        # #endregion
        
        if not self._session_id:
            raise RuntimeError("Failed to get session ID from MCP server")
        
        logger.debug(f"MCP session ID: {self._session_id}")
    
    async def _send_initialized(self):
        """Initialized 알림 전송"""
        if not self._http_client or not self._session_id:
            raise RuntimeError("MCP client not initialized")
        
        init_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": self._session_id
        }
        
        # Kong API Key가 있으면 헤더에 추가
        if self.kong_api_key:
            headers["X-API-Key"] = self.kong_api_key
        
        # #region agent log
        try:
            import time
            log_entry = {
                "location": "mcp_client.py:_send_initialized",
                "message": "Sending initialized notification",
                "data": {"session_id": self._session_id},
                "timestamp": int(time.time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B"
            }
            log_path = "/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as log_err:
            logger.debug(f"Debug log write failed: {log_err}")
        # #endregion
        
        response = await self._http_client.post(
            self.endpoint,
            json=init_notification,
            headers=headers
        )
        response.raise_for_status()
        
        logger.debug("Initialized notification sent")
    
    async def _load_tools(self):
        """도구 목록 조회 (tools/list)"""
        response = await self._send_rpc("tools/list", {})
        
        # response가 dict가 아닌 경우 처리
        if not isinstance(response, dict):
            response = {}
        
        tools_data = response.get("tools", [])
        self._tools = []
        
        for tool_data in tools_data:
            tool = MCPTool(
                name=tool_data.get("name", "unknown"),
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {})
            )
            self._tools.append(tool)
            
        logger.debug(f"Loaded {len(self._tools)} tools from MCP server")
    
    async def _send_rpc(
        self,
        method: str,
        params: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        JSON-RPC 2.0 요청 전송.
        
        Args:
            method: RPC 메서드 (예: "tools/list", "tools/call")
            params: 메서드 파라미터
            request_id: 요청 ID (없으면 자동 생성)
            
        Returns:
            RPC 응답의 result 필드
        """
        if not self._http_client:
            raise RuntimeError("MCP client not connected")
        
        request_id = request_id or str(uuid.uuid4())
        
        rpc_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        logger.debug(f"Sending RPC request: method={method}, id={request_id}")
        
        # 세션 ID가 있으면 헤더에 추가
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        
        # Kong API Key가 있으면 헤더에 추가
        if self.kong_api_key:
            headers["X-API-Key"] = self.kong_api_key
        
        for attempt in range(self.max_retries):
            try:
                # #region agent log
                try:
                    log_entry = {
                        "location": "mcp_client.py:162",
                        "message": "Sending RPC request",
                        "data": {
                            "endpoint": self.endpoint,
                            "method": method,
                            "request_id": request_id,
                            "attempt": attempt + 1,
                            "has_session_id": bool(self._session_id)
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B"
                    }
                    with open("/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log", "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                except:
                    pass
                # #endregion
                
                response = await self._http_client.post(
                    self.endpoint,
                    json=rpc_request,
                    headers=headers
                )
                
                # #region agent log
                try:
                    log_entry = {
                        "location": "mcp_client.py:180",
                        "message": "RPC response received",
                        "data": {
                            "status_code": response.status_code,
                            "headers": dict(response.headers),
                            "content_type": response.headers.get("content-type", ""),
                            "content_length": len(response.content) if hasattr(response, 'content') else 0
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B"
                    }
                    with open("/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log", "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                except:
                    pass
                # #endregion
                
                response.raise_for_status()
                
                # SSE 응답 파싱
                response_text = response.text
                result = _parse_sse_response(response_text)
                
                # SSE 파싱 실패 시 일반 JSON으로 시도
                if not result:
                    try:
                        result = response.json()
                    except:
                        result = {}
                
                if "error" in result:
                    error = result["error"]
                    raise RuntimeError(f"RPC error: {error.get('message', error)}")
                
                return result.get("result", {})
                
            except httpx.TimeoutException:
                logger.warning(f"RPC timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                
            except httpx.HTTPStatusError as e:
                logger.error(f"RPC HTTP error: {e.response.status_code}")
                
                # #region agent log
                try:
                    error_text = e.response.text[:500] if hasattr(e.response, 'text') else str(e)
                    log_entry = {
                        "location": "mcp_client.py:183",
                        "message": "RPC HTTP error",
                        "data": {
                            "status_code": e.response.status_code,
                            "endpoint": self.endpoint,
                            "method": method,
                            "error_text": error_text,
                            "response_headers": dict(e.response.headers) if hasattr(e.response, 'headers') else {}
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B"
                    }
                    with open("/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log", "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                except:
                    pass
                # #endregion
                
                raise
    
    def get_tools(self) -> List[MCPTool]:
        """조회된 도구 목록 반환"""
        return self._tools
    
    def get_tool_by_name(self, name: str) -> Optional[MCPTool]:
        """이름으로 도구 검색"""
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None
    
    def filter_tools(self, name_filter: Optional[Callable[[str], bool]] = None) -> List[MCPTool]:
        """
        도구 필터링.
        
        Args:
            name_filter: 도구 이름 필터 함수 (True면 포함)
            
        Returns:
            필터링된 도구 목록
        """
        if name_filter is None:
            return self._tools
        return [t for t in self._tools if name_filter(t.name)]
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> MCPToolCall:
        """
        도구 호출 (tools/call) - OTEL 자동 기록.
        
        Args:
            tool_name: 도구 이름
            arguments: 도구 인자
            
        Returns:
            MCPToolCall 결과
        """
        logger.info(f"Calling MCP tool: {tool_name}")
        logger.debug(f"Tool arguments: {json.dumps(arguments, ensure_ascii=False)[:200]}")
        
        start_time = datetime.now()
        
        # OTEL span으로 도구 호출 기록
        with start_tool_call_span(tool_name, arguments) as (span, record_result):
            try:
                result = await self._send_rpc(
                    "tools/call",
                    {
                        "name": tool_name,
                        "arguments": arguments
                    }
                )

                # MCP servers may return tool-level errors as a successful JSON-RPC result,
                # e.g. {"result": {"content": [...], "isError": true}}
                if isinstance(result, dict) and result.get("isError") is True:
                    content = result.get("content", [])
                    error_msg = "Tool error"
                    if content and isinstance(content, list) and isinstance(content[0], dict):
                        if content[0].get("type") == "text":
                            error_msg = content[0].get("text", "Tool error")
                    else:
                        error_msg = str(result)
                    latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                    record_result({"error": error_msg, "latency_ms": latency_ms})
                    return MCPToolCall(name=tool_name, result=None, error=error_msg)
                
                # content 필드에서 실제 결과 추출
                content = result.get("content", [])
                if content and isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict):
                        # text 형식
                        if first_content.get("type") == "text":
                            text_result = first_content.get("text", "")
                            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                            record_result({"result": text_result[:500], "latency_ms": latency_ms})
                            # JSON 파싱 시도
                            try:
                                parsed = json.loads(text_result)
                                return MCPToolCall(name=tool_name, result=parsed)
                            except json.JSONDecodeError:
                                return MCPToolCall(name=tool_name, result=text_result)
                
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                record_result({"result": str(result)[:500], "latency_ms": latency_ms})
                return MCPToolCall(name=tool_name, result=result)
                
            except Exception as e:
                logger.error(f"Tool call failed: {tool_name} - {e}")
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                record_result({"error": str(e), "latency_ms": latency_ms})
                return MCPToolCall(name=tool_name, result=None, error=str(e))
    
    @property
    def is_connected(self) -> bool:
        """연결 상태"""
        return self._connected
    
    @property
    def tool_count(self) -> int:
        """도구 수"""
        return len(self._tools)


# =============================================================================
# LangChain BaseTool 래퍼
# =============================================================================

def create_langchain_tool(
    mcp_client: MCPHTTPClient,
    tool: MCPTool
) -> "BaseTool":
    """
    MCP 도구를 LangChain BaseTool로 래핑.
    
    원본 참조: mcp_direct_client.py:_convert_to_langchain_tools()
    """
    from langchain_core.tools import BaseTool
    
    # 입력 스키마에서 Pydantic 모델 생성
    properties = tool.input_schema.get("properties", {})
    required = tool.input_schema.get("required", [])
    
    # 동적 Pydantic 모델 생성
    fields = {}
    for prop_name, prop_schema in properties.items():
        field_type = str  # 기본 타입
        prop_type = prop_schema.get("type", "string")
        if prop_type == "integer":
            field_type = int
        elif prop_type == "number":
            field_type = float
        elif prop_type == "boolean":
            field_type = bool
        elif prop_type == "array":
            field_type = list
        elif prop_type == "object":
            field_type = dict
        
        # Optional 처리
        if prop_name in required:
            fields[prop_name] = (field_type, Field(description=prop_schema.get("description", "")))
        else:
            fields[prop_name] = (Optional[field_type], Field(default=None, description=prop_schema.get("description", "")))
    
    # 동적 ArgsSchema 모델 생성
    ArgsSchema = create_model(
        f"{tool.name}Args",
        **fields
    )
    
    # IMPORTANT:
    # Do NOT store mcp_client on the Tool as a pydantic/model field (or class attr).
    # Pydantic/LangChain may deepcopy/serialize tool objects, which can traverse into
    # httpx internals (RLock) and crash with: "cannot pickle '_thread.RLock' object".
    # Reference agent-platform pattern: closure-based wrapper (no client field on the tool).

    async def _tool_wrapper(**kwargs) -> str:
        result = await mcp_client.call_tool(tool.name, kwargs)
        if result.error:
            return f"Error: {result.error}"
        return (
            json.dumps(result.result, ensure_ascii=False)
            if isinstance(result.result, (dict, list))
            else str(result.result)
        )

    class MCPLangChainTool(BaseTool):
        name: str = tool.name
        description: str = tool.description or f"MCP tool: {tool.name}"
        args_schema: type = ArgsSchema

        def _run(self, **kwargs) -> str:
            """Sync run (discouraged)."""
            import asyncio
            return asyncio.run(self._arun(**kwargs))

        async def _arun(self, **kwargs) -> str:
            return await _tool_wrapper(**kwargs)

    return MCPLangChainTool()


def create_langchain_tools(
    mcp_client: MCPStdioClientWrapper,
    name_filter: Optional[Callable[[str], bool]] = None
) -> List["BaseTool"]:
    """
    MCP 도구들을 LangChain BaseTool 목록으로 변환.
    
    Args:
        mcp_client: MCP 클라이언트
        name_filter: 도구 이름 필터 함수
        
    Returns:
        LangChain BaseTool 목록
    """
    tools = mcp_client.filter_tools(name_filter)
    return [create_langchain_tool(mcp_client, t) for t in tools]


# =============================================================================
# 싱글톤 인스턴스 (OpenDart MCP 전용)
# =============================================================================

_opendart_client: Optional[MCPStdioClientWrapper] = None

# 싱글톤 클라이언트 초기화 플래그 (Kong 정보 변경 시 재연결)
_opendart_client_endpoint: Optional[str] = None
_opendart_client_kong_key: Optional[str] = None


async def get_opendart_mcp_client() -> MCPStdioClientWrapper:
    """
    OpenDart MCP 클라이언트 싱글톤 반환 (stdio 방식).
    
    /build/mcp에 등록된 OpenDART MCP 서버를 stdio 방식으로 사용합니다.
    """
    global _opendart_client, _opendart_client_endpoint, _opendart_client_kong_key
    
    # 함수 시작 로그
    print(f"[DEBUG] get_opendart_mcp_client() called")
    logger.info("get_opendart_mcp_client() called")
    
    # 연결이 끊어진 경우 또는 클라이언트가 없는 경우 재연결
    should_reconnect = (
        _opendart_client is None or 
        (hasattr(_opendart_client, '_connected') and not _opendart_client._connected)
    )
    
    # 로그 출력 (항상 실행)
    print(f"[DEBUG] get_opendart_mcp_client called: should_reconnect={should_reconnect}, client_exists={_opendart_client is not None}")
    logger.info(f"get_opendart_mcp_client called: should_reconnect={should_reconnect}, client_exists={_opendart_client is not None}, is_connected={_opendart_client._connected if _opendart_client and hasattr(_opendart_client, '_connected') else 'N/A'}, endpoint={_opendart_client.endpoint if _opendart_client else 'N/A'}, has_kong_key={hasattr(_opendart_client, 'kong_api_key') and bool(_opendart_client.kong_api_key) if _opendart_client else 'N/A'}")
    
    if should_reconnect:
        print(f"[DEBUG] Initializing OpenDART MCP client (reconnect required)")
        logger.info("Initializing OpenDART MCP client (reconnect required)")
        # MCP 서비스에서 등록된 OpenDART 서버 찾기
        from app.services.mcp_service import mcp_service
        
        # #region agent log
        try:
            log_entry = {
                "location": "mcp_client.py:get_opendart_mcp_client",
                "message": "Looking for registered OpenDART MCP server",
                "data": {},
                "timestamp": int(__import__("time").time() * 1000),
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "G"
            }
            with open("/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except:
            pass
        # #endregion
        
        # 활성화된 서버 목록 조회 (Kong 정보 포함)
        try:
            # Kong 정보를 포함한 서버 정보 조회를 위해 직접 DB 쿼리
            # 또는 _get_server_internal을 사용할 수 있지만, 여기서는 list_servers 결과를 사용
            servers_result = await mcp_service.list_servers(enabled_only=True, page=1, size=100)
            servers = servers_result.get('servers', [])
            
            logger.info(f"Found {len(servers)} enabled MCP servers")
            
            # OpenDART 서버 찾기 (이름에 "opendart" 또는 "dart" 포함)
            opendart_server = None
            opendart_server_id = None
            logger.info(f"Searching for OpenDART server in {len(servers)} servers")
            for server in servers:
                name_lower = server.get('name', '').lower()
                logger.debug(f"Checking server: {server.get('name')} (lower: {name_lower})")
                if 'opendart' in name_lower or ('dart' in name_lower and 'opendart' in name_lower):
                    opendart_server_id = server.get('id')
                    logger.info(f"Found OpenDART server: {server.get('name')} (ID: {opendart_server_id})")
                    break
            
            if not opendart_server_id:
                logger.warning(f"OpenDART server ID not found after searching {len(servers)} servers")
            
            # Kong 정보를 포함한 서버 정보 조회 (내부 메서드 사용)
            opendart_server = None
            if opendart_server_id:
                logger.info(f"Fetching OpenDART server internal info (ID: {opendart_server_id})")
                opendart_server = await mcp_service._get_server_internal(opendart_server_id)
                if not opendart_server:
                    logger.warning(f"OpenDART server not found in internal query (ID: {opendart_server_id})")
                else:
                    logger.info(f"Retrieved OpenDART server with Kong info: kong_service_id={opendart_server.get('kong_service_id')}, has_api_key={bool(opendart_server.get('kong_api_key'))}")
            
            # #region agent log
            try:
                import time
                log_entry = {
                    "location": "mcp_client.py:get_opendart_mcp_client:820",
                    "message": "OpenDART server search result",
                    "data": {
                        "total_servers": len(servers),
                        "server_names": [s.get('name') for s in servers],
                        "found": opendart_server is not None,
                        "server_id": opendart_server_id if opendart_server_id else None,
                        "server_name": opendart_server.get('name') if opendart_server else None,
                        "server_endpoint": opendart_server.get('endpoint_url') if opendart_server else None,
                        "kong_service_id": opendart_server.get('kong_service_id') if opendart_server else None,
                        "kong_api_key_exists": bool(opendart_server.get('kong_api_key')) if opendart_server else False
                    },
                    "timestamp": int(time.time() * 1000),
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "G"
                }
                log_path = "/Users/lchangoo/Workspace/agent-portal/.cursor/debug.log"
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception as log_err:
                logger.debug(f"Debug log write failed: {log_err}")
            # #endregion
            
            if not opendart_server:
                raise RuntimeError(f"OpenDART MCP server not found in registered servers (checked {len(servers)} servers)")
            
            # stdio 방식으로 클라이언트 생성
            server_id = opendart_server.get('id')
            if not server_id:
                raise RuntimeError(f"OpenDART MCP server '{opendart_server.get('name')}' has no id")
            
            # transport_type 확인
            transport_type = opendart_server.get('transport_type')
            if transport_type != 'stdio':
                raise RuntimeError(f"OpenDART MCP server '{opendart_server.get('name')}' is not stdio type (got {transport_type})")
            
            logger.info(f"Using stdio client for OpenDART MCP server: {opendart_server.get('name')} (server_id: {server_id})")
            
            # 기존 클라이언트가 있으면 종료
            if _opendart_client:
                await _opendart_client.disconnect()
            
            # stdio 클라이언트 생성
            _opendart_client = MCPStdioClientWrapper(server_id)
            _opendart_client_endpoint = f"stdio://{server_id}"
            _opendart_client_kong_key = None
            
            await _opendart_client.connect()
        except Exception as e:
            logger.error(f"Failed to get registered MCP servers: {e}")
            import os
            endpoint = os.getenv("OPENDART_MCP_ENDPOINT", "http://121.141.60.219:8089/mcp")
            logger.warning(f"Using fallback endpoint due to error: {endpoint}")
            
            # 기존 클라이언트가 있으면 종료
            if _opendart_client:
                await _opendart_client.disconnect()
            
            _opendart_client = MCPHTTPClient(endpoint)
            _opendart_client_endpoint = endpoint
            _opendart_client_kong_key = None
            await _opendart_client.connect()
    
    return _opendart_client


async def close_opendart_mcp_client():
    """OpenDart MCP 클라이언트 종료"""
    global _opendart_client
    if _opendart_client:
        await _opendart_client.disconnect()
        _opendart_client = None


