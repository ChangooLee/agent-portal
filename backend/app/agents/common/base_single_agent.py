"""
Base Single Agent - 범용 MCP 기반 Single Agent

DART Single Agent 패턴을 일반화한 베이스 클래스.
각 도메인별 에이전트가 상속하여 사용.
"""

import json
import logging
import time
import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator, Type

from pydantic import BaseModel, Field, create_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI

from app.agents.common.mcp_client_base import MCPClientBase, MCPTool, create_mcp_client


# OTEL 트레이싱 헬퍼
_service_tracers = {}

def _get_tracer_for_agent(service_name: str):
    """에이전트별 tracer 획득"""
    global _service_tracers
    
    if service_name in _service_tracers:
        return _service_tracers[service_name]
    
    try:
        from app.telemetry.otel import get_tracer_for_service
        tracer = get_tracer_for_service(service_name, f"{service_name}-tracer")
        _service_tracers[service_name] = tracer
        return tracer
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to get tracer for {service_name}: {e}")
        return None


@contextmanager
def _start_agent_span(service_name: str, span_name: str, attributes: Dict[str, Any] = None):
    """에이전트용 span 시작"""
    tracer = _get_tracer_for_agent(service_name)
    
    if tracer is None:
        yield None
        return
    
    span_attrs = {
        "service.name": service_name,
        "agent.type": service_name,
    }
    if attributes:
        span_attrs.update(attributes)
    
    try:
        with tracer.start_as_current_span(span_name, attributes=span_attrs) as span:
            yield span
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to create span: {e}")
        yield None


logger = logging.getLogger(__name__)


def _create_args_schema(input_schema: Dict[str, Any], tool_name: str) -> Type[BaseModel]:
    """MCP input_schema에서 Pydantic 모델 동적 생성"""
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    
    fields = {}
    for prop_name, prop_info in properties.items():
        if prop_name == "ctx":
            continue
        
        prop_type = prop_info.get("type", "string")
        description = prop_info.get("description", "")
        default = prop_info.get("default", ...)
        
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        python_type = type_map.get(prop_type, str)
        
        if prop_name in required:
            fields[prop_name] = (python_type, Field(description=description))
        else:
            if default is ...:
                default = None
            fields[prop_name] = (Optional[python_type], Field(default=default, description=description))
    
    model_name = f"{tool_name.replace('-', '_').title().replace('_', '')}Args"
    return create_model(model_name, **fields)


class BaseSingleAgent(ABC):
    """
    범용 MCP 기반 Single Agent 베이스 클래스
    
    Claude Opus 4.5를 사용하여 ReAct 패턴으로 동작.
    각 도메인별 에이전트가 상속하여 사용.
    """
    
    # 서브클래스에서 오버라이드
    MCP_SERVER_NAME: str = ""  # MCP 서버 이름
    SERVICE_NAME: str = "agent-base"  # OTEL 서비스 이름
    AGENT_DISPLAY_NAME: str = "Base Agent"  # 화면 표시명
    
    def __init__(self, model: str = "claude-opus-4.5"):
        self.model_name = model
        self.max_iterations = 30
        self.llm = None
        self.tools: List[BaseTool] = []
        self.mcp_client: Optional[MCPClientBase] = None
        self._initialized = False
    
    async def _ensure_mcp_initialized(self):
        """MCP 클라이언트 초기화"""
        if self.mcp_client is not None:
            return
        
        # MCP 클라이언트 초기화
        self.mcp_client = await create_mcp_client(
            server_name=self.MCP_SERVER_NAME,
            service_name=self.SERVICE_NAME
        )
        
        # MCP 도구들을 LangChain Tool로 래핑
        mcp_tools = self.mcp_client.get_tools()
        self.tools = await self._wrap_mcp_tools(mcp_tools)
        logger.info(f"[{self.SERVICE_NAME}] MCP 초기화 완료: {len(self.tools)}개 도구 로드")
    
    def _create_llm(self) -> ChatOpenAI:
        """LLM 인스턴스 생성"""
        litellm_api_key = os.environ.get("LITELLM_MASTER_KEY", "sk-1234")
        
        return ChatOpenAI(
            model=self.model_name,
            base_url="http://litellm:4000/v1",
            api_key=litellm_api_key,
            temperature=0.1,
            max_tokens=16384,
            timeout=600,
        )
    
    async def _wrap_mcp_tools(self, mcp_tools: List[MCPTool]) -> List[BaseTool]:
        """MCP 도구들을 LangChain Tool로 래핑"""
        langchain_tools = []
        
        for mcp_tool in mcp_tools:
            tool_name = mcp_tool.name
            input_schema = mcp_tool.input_schema
            
            # args_schema 동적 생성
            try:
                args_schema = _create_args_schema(input_schema, tool_name)
            except Exception as e:
                logger.warning(f"도구 {tool_name}의 args_schema 생성 실패: {e}")
                args_schema = None
            
            # 클로저를 위한 캡처
            def make_coroutine(captured_tool_name, captured_mcp_client):
                async def coro(**kwargs) -> str:
                    kwargs.pop("ctx", None)
                    try:
                        result = await captured_mcp_client.call_tool(captured_tool_name, kwargs)
                        if result.error:
                            return json.dumps({"error": result.error}, ensure_ascii=False)
                        return result.result if isinstance(result.result, str) else json.dumps(result.result, ensure_ascii=False)
                    except Exception as e:
                        return json.dumps({"error": str(e)}, ensure_ascii=False)
                return coro
            
            # StructuredTool 생성
            tool_kwargs = {
                "func": lambda **kwargs: None,
                "coroutine": make_coroutine(tool_name, self.mcp_client),
                "name": tool_name,
                "description": mcp_tool.description or f"MCP tool: {tool_name}",
            }
            
            if args_schema:
                tool_kwargs["args_schema"] = args_schema
            
            lc_tool = StructuredTool.from_function(**tool_kwargs)
            langchain_tools.append(lc_tool)
        
        return langchain_tools
    
    @abstractmethod
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성 - 서브클래스에서 구현"""
        pass
    
    def _get_tool_display_name(self, tool_name: str) -> str:
        """도구 표시명 반환 - 서브클래스에서 오버라이드 가능"""
        return tool_name
    
    async def analyze_stream(
        self,
        question: str,
        session_id: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        스트리밍 분석 실행
        
        Args:
            question: 사용자 질문
            session_id: 세션 ID
            conversation_history: 이전 대화 기록
            
        Yields:
            SSE 이벤트 딕셔너리
        """
        start_time = time.time()
        
        logger.info(f"[{self.SERVICE_NAME}] Starting analysis: {question[:50]}...")
        
        # OTEL Root Span 생성
        with _start_agent_span(
            self.SERVICE_NAME,
            f"gen_ai.session.{self.SERVICE_NAME}",
            {
                "gen_ai.agent.id": self.SERVICE_NAME,
                "gen_ai.agent.name": self.AGENT_DISPLAY_NAME,
                "gen_ai.request.model": self.model_name,
                "gen_ai.user_query": question[:200],
                "session.id": session_id or "",
            }
        ) as root_span:
            try:
                # MCP 초기화
                await self._ensure_mcp_initialized()
                
                # Start 이벤트
                yield {
                    "event": "start",
                    "message": f"{self.AGENT_DISPLAY_NAME}가 질문을 분석합니다...",
                    "agent": self.SERVICE_NAME
                }
                
                # LLM 생성 (매 호출시 새로 생성 - 트레이스 연결)
                self.llm = self._create_llm()
                
                # 시스템 프롬프트
                system_prompt = self._build_system_prompt()
                
                # 메시지 구성
                messages = [SystemMessage(content=system_prompt)]
                
                # 대화 히스토리 추가
                if conversation_history:
                    for msg in conversation_history[-10:]:  # 최근 10개
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        if role == "user":
                            messages.append(HumanMessage(content=content))
                        elif role == "assistant":
                            messages.append(AIMessage(content=content))
                
                # 현재 질문 추가
                messages.append(HumanMessage(content=question))
                
                # LLM + Tools 바인딩
                llm_with_tools = self.llm.bind_tools(self.tools)
                
                # ReAct 루프
                iteration = 0
                final_response = ""
                
                while iteration < self.max_iterations:
                    iteration += 1
                    logger.debug(f"[{self.SERVICE_NAME}] Iteration {iteration}")
                    
                    # Tool call span
                    with _start_agent_span(
                        self.SERVICE_NAME,
                        f"gen_ai.iteration.{iteration}",
                        {"iteration": iteration}
                    ):
                        yield {
                            "event": "iteration",
                            "iteration": iteration,
                            "max_iterations": self.max_iterations
                        }
                        
                        # LLM 호출
                        response = await llm_with_tools.ainvoke(messages)
                        
                        # 도구 호출이 있는 경우
                        if response.tool_calls:
                            messages.append(response)
                            
                            for tool_call in response.tool_calls:
                                tool_name = tool_call["name"]
                                tool_args = tool_call["args"]
                                tool_call_id = tool_call.get("id", f"call_{iteration}")
                                
                                display_name = self._get_tool_display_name(tool_name)
                                
                                yield {
                                    "event": "tool_start",
                                    "tool": tool_name,
                                    "display_name": display_name,
                                    "args": tool_args
                                }
                                
                                # Tool execution span
                                with _start_agent_span(
                                    self.SERVICE_NAME,
                                    f"gen_ai.tool.{tool_name}",
                                    {"tool.name": tool_name, "tool.args": json.dumps(tool_args, ensure_ascii=False)[:500]}
                                ):
                                    # 도구 실행
                                    tool_result = None
                                    for tool in self.tools:
                                        if tool.name == tool_name:
                                            try:
                                                tool_result = await tool.ainvoke(tool_args)
                                            except Exception as e:
                                                tool_result = json.dumps({"error": str(e)}, ensure_ascii=False)
                                            break
                                    
                                    if tool_result is None:
                                        tool_result = json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
                                
                                yield {
                                    "event": "tool_result",
                                    "tool": tool_name,
                                    "display_name": display_name,
                                    "success": "error" not in str(tool_result).lower()
                                }
                                
                                # ToolMessage 추가
                                messages.append(ToolMessage(
                                    content=tool_result if isinstance(tool_result, str) else json.dumps(tool_result, ensure_ascii=False),
                                    tool_call_id=tool_call_id
                                ))
                        else:
                            # 도구 호출이 없으면 최종 응답
                            final_response = response.content
                            break
                
                # 최종 응답 스트리밍
                if final_response:
                    yield {
                        "event": "content",
                        "content": final_response
                    }
                
                elapsed_time = time.time() - start_time
                
                # Span에 결과 기록
                if root_span:
                    root_span.set_attribute("gen_ai.response.latency_ms", elapsed_time * 1000)
                    root_span.set_attribute("gen_ai.response.iterations", iteration)
                
                yield {
                    "event": "complete",
                    "elapsed_time": elapsed_time,
                    "iterations": iteration
                }
                
                logger.info(f"[{self.SERVICE_NAME}] Analysis completed in {elapsed_time:.2f}s ({iteration} iterations)")
                
            except Exception as e:
                logger.error(f"[{self.SERVICE_NAME}] Analysis failed: {e}", exc_info=True)
                if root_span:
                    root_span.set_attribute("error", True)
                    root_span.set_attribute("error.message", str(e))
                yield {
                    "event": "error",
                    "message": f"분석 중 오류가 발생했습니다: {str(e)}"
                }

