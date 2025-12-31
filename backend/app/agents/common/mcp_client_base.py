"""
MCP Client Base - 범용 MCP 클라이언트

여러 에이전트에서 공통으로 사용하는 MCP 클라이언트 베이스 클래스.
DART 에이전트의 MCPStdioClientWrapper를 일반화.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


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


class MCPClientBase:
    """
    범용 MCP stdio 클라이언트 래퍼.
    
    서버 ID로 MCP 서버에 연결하고 도구를 호출합니다.
    
    Example:
        client = MCPClientBase(server_id="xxx", service_name="agent-realestate")
        await client.connect()
        tools = client.get_tools()
        result = await client.call_tool("search_apartments", {"region": "강남구"})
    """
    
    def __init__(
        self,
        server_id: str,
        service_name: str = "agent-mcp",
        timeout: float = 600.0,
        max_retries: int = 3
    ):
        """
        Args:
            server_id: MCP 서버 ID
            service_name: 서비스 이름 (OTEL 트레이싱용)
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        self.server_id = server_id
        self.service_name = service_name
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._connected = False
        self._tools: List[MCPTool] = []
        self._stdio_client = None
        self._server_info: Optional[Dict[str, Any]] = None
    
    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._connected
    
    async def connect(self) -> bool:
        """MCP 서버에 연결하고 도구 목록을 조회"""
        from app.mcp.stdio_client import MCPStdioClient
        from app.mcp.process_manager import process_manager
        from app.services.mcp_service import mcp_service
        
        logger.info(f"[{self.service_name}] Connecting to MCP server: {self.server_id}")
        
        try:
            # MCP 서비스에서 서버 정보 가져오기
            self._server_info = await mcp_service._get_server_internal(self.server_id)
            
            if not self._server_info:
                raise RuntimeError(f"MCP server {self.server_id} not found")
            
            # stdio 서버인지 확인
            transport_type = self._server_info.get('transport_type')
            if transport_type != 'stdio':
                raise RuntimeError(f"MCP server {self.server_id} is not stdio type (got {transport_type})")
            
            # 프로세스 확인
            existing_process = process_manager.get_process(self.server_id)
            if existing_process is None or existing_process.returncode is not None:
                # 프로세스가 없거나 종료됨 - 시작 필요
                logger.info(f"[{self.service_name}] Starting MCP server process: {self.server_id}")
                await mcp_service.start_stdio_process(self.server_id)
                
                # 프로세스가 등록될 때까지 대기 (최대 5초)
                max_wait = 5.0
                wait_interval = 0.2
                waited = 0.0
                while waited < max_wait:
                    existing_process = process_manager.get_process(self.server_id)
                    if existing_process is not None and existing_process.returncode is None:
                        logger.info(f"[{self.service_name}] Process registered (PID: {existing_process.pid})")
                        break
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                else:
                    raise RuntimeError(f"Failed to start MCP server process: {self.server_id}")
            else:
                logger.info(f"[{self.service_name}] Process already running (PID: {existing_process.pid})")
            
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
            
            # 기존 프로세스 다시 확인
            existing_process = process_manager.get_process(self.server_id)
            if existing_process is None:
                raise RuntimeError(f"Process {self.server_id} not found in process_manager")
            
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
            logger.info(f"[{self.service_name}] Connected: {len(self._tools)} tools loaded")
            return True
            
        except Exception as e:
            logger.error(f"[{self.service_name}] Failed to connect: {e}", exc_info=True)
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
        """도구 필터링"""
        tools = self.get_tools()
        if name_filter:
            return [t for t in tools if name_filter(t.name)]
        return tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPToolCall:
        """도구 호출"""
        from app.mcp.process_manager import process_manager
        
        if not self._connected or not self._stdio_client:
            raise RuntimeError("Not connected to MCP server")
        
        start_time = datetime.now()
        
        try:
            # 연결 상태 확인 및 재연결
            if not self._stdio_client.is_connected():
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
            
            # 도구 호출
            result = await self._stdio_client.call_tool(tool_name, arguments)
            
            # 결과가 리스트인 경우 처리
            if isinstance(result, list):
                result_text = ""
                for item in result:
                    if hasattr(item, 'text'):
                        text_val = item.text
                        if isinstance(text_val, bytes):
                            text_val = text_val.decode('utf-8', errors='replace')
                        result_text += text_val
                    elif isinstance(item, str):
                        result_text += item
                    elif isinstance(item, dict):
                        if 'text' in item:
                            text_val = item['text']
                            if isinstance(text_val, bytes):
                                text_val = text_val.decode('utf-8', errors='replace')
                            result_text += text_val
                        else:
                            result_text += json.dumps(item, ensure_ascii=False)
                    elif isinstance(item, bytes):
                        result_text += item.decode('utf-8', errors='replace')
                    else:
                        result_text += str(item)
                
                result = result_text if result_text else json.dumps(result, ensure_ascii=False, default=str)
            elif isinstance(result, bytes):
                result = result.decode('utf-8', errors='replace')
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.debug(f"[{self.service_name}] Tool {tool_name} completed in {latency_ms:.1f}ms")
            
            return MCPToolCall(
                name=tool_name,
                result=result,
                error=None
            )
        except Exception as e:
            logger.error(f"[{self.service_name}] Failed to call tool {tool_name}: {e}", exc_info=True)
            return MCPToolCall(
                name=tool_name,
                result=None,
                error=str(e)
            )
    
    async def disconnect(self) -> None:
        """연결 종료"""
        self._connected = False
        self._stdio_client = None
        logger.info(f"[{self.service_name}] Disconnected from MCP server: {self.server_id}")


async def create_mcp_client(
    server_name: str,
    service_name: str = "agent-mcp"
) -> MCPClientBase:
    """
    서버 이름으로 MCP 클라이언트 생성
    
    Args:
        server_name: MCP 서버 이름 (예: "mcp-kr-realestate")
        service_name: 서비스 이름 (OTEL 트레이싱용)
    
    Returns:
        연결된 MCP 클라이언트
    """
    from app.services.mcp_service import mcp_service
    
    # 서버 이름으로 ID 조회
    servers = await mcp_service.list_servers()
    server_id = None
    for server in servers.get("servers", []):
        if server.get("name") == server_name:
            server_id = server.get("id")
            break
    
    if not server_id:
        raise RuntimeError(f"MCP server not found: {server_name}")
    
    client = MCPClientBase(server_id=server_id, service_name=service_name)
    await client.connect()
    return client

