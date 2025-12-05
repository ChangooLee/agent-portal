"""
MCP HTTP Client for OpenDart MCP Server (Streamable HTTP)

Agent Portal용 MCP 클라이언트 - JSON-RPC 2.0 프로토콜 over HTTP.
원본 fastmcp.Client (stdio)를 HTTP Streamable로 리팩토링.

참조: /Users/lchangoo/Workspace/agent-platform/connection/mcp_direct_client.py
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import uuid

import httpx
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)


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
        timeout: float = 120.0,
        max_retries: int = 3
    ):
        """
        Args:
            endpoint: MCP 서버 URL (예: http://121.141.60.219:8089/mcp)
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._connected = False
        self._tools: List[MCPTool] = []
        self._http_client: Optional[httpx.AsyncClient] = None
        
    async def connect(self) -> bool:
        """MCP 서버에 연결하고 도구 목록을 조회"""
        logger.info(f"Connecting to MCP server: {self.endpoint}")
        
        try:
            # HTTP 클라이언트 생성
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"}
            )
            
            # 도구 목록 조회
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
        logger.info("Disconnected from MCP server")
    
    async def _load_tools(self):
        """도구 목록 조회 (tools/list)"""
        response = await self._send_rpc("tools/list", {})
        
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
        
        for attempt in range(self.max_retries):
            try:
                response = await self._http_client.post(
                    self.endpoint,
                    json=rpc_request
                )
                response.raise_for_status()
                
                result = response.json()
                
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
        도구 호출 (tools/call).
        
        Args:
            tool_name: 도구 이름
            arguments: 도구 인자
            
        Returns:
            MCPToolCall 결과
        """
        logger.info(f"Calling MCP tool: {tool_name}")
        logger.debug(f"Tool arguments: {json.dumps(arguments, ensure_ascii=False)[:200]}")
        
        try:
            result = await self._send_rpc(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": arguments
                }
            )
            
            # content 필드에서 실제 결과 추출
            content = result.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                first_content = content[0]
                if isinstance(first_content, dict):
                    # text 형식
                    if first_content.get("type") == "text":
                        text_result = first_content.get("text", "")
                        # JSON 파싱 시도
                        try:
                            parsed = json.loads(text_result)
                            return MCPToolCall(name=tool_name, result=parsed)
                        except json.JSONDecodeError:
                            return MCPToolCall(name=tool_name, result=text_result)
            
            return MCPToolCall(name=tool_name, result=result)
            
        except Exception as e:
            logger.error(f"Tool call failed: {tool_name} - {e}")
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
    
    # LangChain Tool 클래스 정의
    class MCPLangChainTool(BaseTool):
        name: str = tool.name
        description: str = tool.description or f"MCP tool: {tool.name}"
        args_schema: type = ArgsSchema
        
        _mcp_client: MCPHTTPClient = mcp_client
        
        def _run(self, **kwargs) -> str:
            """동기 실행 (비권장)"""
            import asyncio
            return asyncio.run(self._arun(**kwargs))
        
        async def _arun(self, **kwargs) -> str:
            """비동기 실행"""
            result = await self._mcp_client.call_tool(self.name, kwargs)
            if result.error:
                return f"Error: {result.error}"
            return json.dumps(result.result, ensure_ascii=False) if isinstance(result.result, (dict, list)) else str(result.result)
    
    return MCPLangChainTool()


def create_langchain_tools(
    mcp_client: MCPHTTPClient,
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

_opendart_client: Optional[MCPHTTPClient] = None


async def get_opendart_mcp_client() -> MCPHTTPClient:
    """
    OpenDart MCP 클라이언트 싱글톤 반환.
    
    환경변수에서 MCP 엔드포인트를 읽거나 기본값 사용.
    """
    global _opendart_client
    
    if _opendart_client is None or not _opendart_client.is_connected:
        import os
        endpoint = os.getenv("OPENDART_MCP_ENDPOINT", "http://121.141.60.219:8089/mcp")
        
        _opendart_client = MCPHTTPClient(endpoint)
        await _opendart_client.connect()
    
    return _opendart_client


async def close_opendart_mcp_client():
    """OpenDart MCP 클라이언트 종료"""
    global _opendart_client
    if _opendart_client:
        await _opendart_client.disconnect()
        _opendart_client = None


