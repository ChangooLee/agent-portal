"""
BaseAgentPortal - Agent Portal용 기본 에이전트 클래스

LiteLLM 기반 LLM 호출, MCP 도구 바인딩, OTEL 트레이싱 통합.
원본 base_agent.py, state_graph_agent.py 참조하여 리팩토링.
"""

import json
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, TypedDict, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage, SystemMessage
from langchain_core.tools import BaseTool

from .mcp_client import MCPHTTPClient, MCPTool, create_langchain_tools, get_opendart_mcp_client
from .metrics import (
    start_dart_span, start_llm_call_span, start_tool_call_span,
    record_counter, record_histogram, get_trace_headers, inject_context_to_carrier
)

logger = logging.getLogger(__name__)


# =============================================================================
# 에이전트 상태 정의
# =============================================================================

class AgentState(TypedDict):
    """에이전트 상태"""
    messages: List[BaseMessage]
    metadata: Dict[str, Any]
    otel_carrier: Optional[Dict[str, str]]


# =============================================================================
# 설정
# =============================================================================

DEFAULT_STEP_TIMEOUT = 120
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_ITERATIONS = 10


# =============================================================================
# LiteLLM 어댑터
# =============================================================================

class LiteLLMAdapter:
    """
    LiteLLM 서비스 어댑터.
    
    Agent Portal의 litellm_service를 사용하여 LLM 호출.
    """
    
    def __init__(self, model: str = "qwen-235b"):
        self.model = model
        self._litellm_service = None
    
    @property
    def litellm_service(self):
        if self._litellm_service is None:
            from app.services.litellm_service import litellm_service
            self._litellm_service = litellm_service
        return self._litellm_service
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        trace_headers: Optional[Dict[str, str]] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        LLM 채팅 호출.
        
        Args:
            messages: 메시지 리스트
            tools: 사용 가능한 도구 정의
            trace_headers: OTEL trace context
            temperature: 온도
            max_tokens: 최대 토큰
            metadata: 추가 메타데이터
            
        Returns:
            LLM 응답
        """
        kwargs = {
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        if metadata:
            kwargs["metadata"] = metadata
        
        return await self.litellm_service.chat_completion_sync(
            model=self.model,
            messages=messages,
            trace_headers=trace_headers,
            **kwargs
        )


# =============================================================================
# 기본 에이전트 클래스
# =============================================================================

class DartBaseAgent(ABC):
    """
    Agent Portal용 DART 에이전트 기본 클래스.
    
    LiteLLM 기반 LLM 호출, MCP 도구 바인딩, OTEL 트레이싱 통합.
    """
    
    def __init__(
        self,
        agent_name: str,
        model: str = "qwen-235b",
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        step_timeout: int = DEFAULT_STEP_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES
    ):
        """
        Args:
            agent_name: 에이전트 이름 (예: "financial_agent")
            model: LLM 모델명
            max_iterations: 최대 반복 횟수
            step_timeout: 단계 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        self.agent_name = agent_name
        self.model = model
        self.max_iterations = max_iterations
        self.step_timeout = step_timeout
        self.max_retries = max_retries
        
        self.llm = LiteLLMAdapter(model)
        self.mcp_client: Optional[MCPHTTPClient] = None
        self.filtered_tools: List[BaseTool] = []
        self._initialized = False
    
    async def initialize(self):
        """에이전트 초기화 (MCP 연결 + 도구 로드)"""
        if self._initialized:
            return
        
        logger.info(f"{self.agent_name} 초기화 시작")
        
        try:
            # MCP 클라이언트 획득 (싱글톤)
            self.mcp_client = await get_opendart_mcp_client()
            
            # 도구 필터링
            all_tools = self.mcp_client.get_tools()
            filtered = await self._filter_tools(all_tools)
            
            # LangChain 도구로 변환
            self.filtered_tools = create_langchain_tools(
                self.mcp_client,
                name_filter=lambda n: any(t.name == n for t in filtered)
            )
            
            self._initialized = True
            logger.info(f"{self.agent_name} 초기화 완료: {len(self.filtered_tools)}개 도구")
            
        except Exception as e:
            logger.error(f"{self.agent_name} 초기화 실패: {e}")
            raise
    
    @abstractmethod
    async def _filter_tools(self, tools: List[MCPTool]) -> List[MCPTool]:
        """
        도구 필터링 (하위 클래스에서 구현).
        
        Args:
            tools: 전체 MCP 도구 목록
            
        Returns:
            필터링된 도구 목록
        """
        pass
    
    @abstractmethod
    def _create_system_prompt(self) -> str:
        """시스템 프롬프트 생성 (하위 클래스에서 구현)."""
        pass
    
    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        """LLM에 전달할 도구 스키마 생성"""
        tools_schema = []
        
        for tool in self.filtered_tools:
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.args_schema.schema() if hasattr(tool, 'args_schema') else {}
                }
            }
            tools_schema.append(schema)
        
        return tools_schema
    
    async def _execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        parent_carrier: Optional[Dict[str, str]] = None
    ) -> str:
        """
        도구 실행.
        
        Args:
            tool_name: 도구 이름
            arguments: 도구 인자
            parent_carrier: 부모 OTEL context
            
        Returns:
            도구 실행 결과 (문자열)
        """
        with start_tool_call_span(tool_name, arguments, parent_carrier) as (span, record):
            try:
                # LangChain 도구에서 찾기
                tool = next((t for t in self.filtered_tools if t.name == tool_name), None)
                
                if tool is None:
                    # MCP 직접 호출
                    if self.mcp_client:
                        result = await self.mcp_client.call_tool(tool_name, arguments)
                        if result.error:
                            record(None, result.error)
                            return f"Error: {result.error}"
                        record(result.result)
                        return json.dumps(result.result, ensure_ascii=False) if isinstance(result.result, (dict, list)) else str(result.result)
                    else:
                        record(None, f"Tool not found: {tool_name}")
                        return f"Error: Tool not found: {tool_name}"
                
                # LangChain 도구 실행
                result = await tool._arun(**arguments)
                record(result)
                return result
                
            except Exception as e:
                logger.error(f"Tool execution failed: {tool_name} - {e}")
                record(None, str(e))
                return f"Error: {str(e)}"
    
    async def run(
        self,
        question: str,
        session_id: Optional[str] = None,
        parent_carrier: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        에이전트 실행.
        
        Args:
            question: 사용자 질문
            session_id: 세션 ID (선택)
            parent_carrier: 부모 OTEL context
            
        Returns:
            실행 결과 {"answer": str, "tool_calls": list, "tokens": dict}
        """
        await self.initialize()
        
        span_name = f"dart.{self.agent_name}"
        
        with start_dart_span(span_name, {"question_length": len(question)}, parent_carrier) as span:
            # 현재 span의 context를 carrier에 저장
            current_carrier = {}
            inject_context_to_carrier(current_carrier)
            
            start_time = time.time()
            
            messages = [
                {"role": "system", "content": self._create_system_prompt()},
                {"role": "user", "content": question}
            ]
            
            tools_schema = self._get_tools_schema()
            tool_calls_log = []
            total_tokens = {"prompt": 0, "completion": 0, "total": 0}
            
            iteration = 0
            final_answer = ""
            
            while iteration < self.max_iterations:
                iteration += 1
                
                # LLM 호출
                with start_llm_call_span(self.agent_name, self.model, messages, current_carrier) as (llm_span, record_llm):
                    try:
                        response = await self.llm.chat(
                            messages=messages,
                            tools=tools_schema if tools_schema else None,
                            trace_headers=get_trace_headers(),
                            metadata={
                                "agent_id": self.agent_name,
                                "session_id": session_id,
                                "iteration": iteration
                            }
                        )
                        record_llm(response)
                        
                        # 토큰 누적
                        usage = response.get("usage", {})
                        total_tokens["prompt"] += usage.get("prompt_tokens", 0)
                        total_tokens["completion"] += usage.get("completion_tokens", 0)
                        total_tokens["total"] += usage.get("total_tokens", 0)
                        
                    except Exception as e:
                        logger.error(f"LLM call failed: {e}")
                        if hasattr(span, 'set_attribute'):
                            span.set_attribute("error", str(e))
                        raise
                
                # 응답 처리
                choice = response.get("choices", [{}])[0]
                message = choice.get("message", {})
                finish_reason = choice.get("finish_reason", "")
                
                # Tool calls 처리
                tool_calls = message.get("tool_calls", [])
                
                if tool_calls:
                    # AI 메시지 추가
                    messages.append({
                        "role": "assistant",
                        "content": message.get("content", ""),
                        "tool_calls": tool_calls
                    })
                    
                    # 도구 실행
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        tool_name = func.get("name", "")
                        tool_args_str = func.get("arguments", "{}")
                        tool_id = tc.get("id", "")
                        
                        try:
                            tool_args = json.loads(tool_args_str)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        logger.info(f"Executing tool: {tool_name}")
                        
                        result = await self._execute_tool(tool_name, tool_args, current_carrier)
                        
                        tool_calls_log.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result[:500] if len(result) > 500 else result
                        })
                        
                        # Tool message 추가
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result
                        })
                    
                else:
                    # 최종 응답
                    final_answer = message.get("content", "")
                    break
            
            # 메트릭 기록
            latency_ms = (time.time() - start_time) * 1000
            record_histogram(f"dart_{self.agent_name}_latency_ms", latency_ms, {"model": self.model})
            record_counter(f"dart_{self.agent_name}_requests_total", {"model": self.model})
            
            if hasattr(span, 'set_attribute'):
                span.set_attribute("answer_length", len(final_answer))
                span.set_attribute("tool_calls_count", len(tool_calls_log))
                span.set_attribute("iterations", iteration)
                span.set_attribute("total_tokens", total_tokens["total"])
            
            return {
                "answer": final_answer,
                "tool_calls": tool_calls_log,
                "tokens": total_tokens,
                "iterations": iteration,
                "latency_ms": latency_ms
            }
    
    async def run_stream(
        self,
        question: str,
        session_id: Optional[str] = None,
        parent_carrier: Optional[Dict[str, str]] = None
    ):
        """
        에이전트 실행 (스트리밍).
        
        각 단계마다 이벤트를 yield.
        
        Args:
            question: 사용자 질문
            session_id: 세션 ID
            parent_carrier: 부모 OTEL context
            
        Yields:
            Dict[str, Any]: 스트림 이벤트
        """
        await self.initialize()
        
        span_name = f"dart.{self.agent_name}"
        
        with start_dart_span(span_name, {"question_length": len(question)}, parent_carrier) as span:
            current_carrier = {}
            inject_context_to_carrier(current_carrier)
            
            start_time = time.time()
            
            yield {"event": "start", "agent": self.agent_name}
            
            messages = [
                {"role": "system", "content": self._create_system_prompt()},
                {"role": "user", "content": question}
            ]
            
            tools_schema = self._get_tools_schema()
            tool_calls_log = []
            total_tokens = {"prompt": 0, "completion": 0, "total": 0}
            
            iteration = 0
            final_answer = ""
            
            while iteration < self.max_iterations:
                iteration += 1
                
                yield {"event": "iteration", "iteration": iteration}
                
                # LLM 호출
                with start_llm_call_span(self.agent_name, self.model, messages, current_carrier) as (llm_span, record_llm):
                    try:
                        response = await self.llm.chat(
                            messages=messages,
                            tools=tools_schema if tools_schema else None,
                            trace_headers=get_trace_headers(),
                            metadata={
                                "agent_id": self.agent_name,
                                "session_id": session_id,
                                "iteration": iteration
                            }
                        )
                        record_llm(response)
                        
                        usage = response.get("usage", {})
                        total_tokens["prompt"] += usage.get("prompt_tokens", 0)
                        total_tokens["completion"] += usage.get("completion_tokens", 0)
                        total_tokens["total"] += usage.get("total_tokens", 0)
                        
                    except Exception as e:
                        yield {"event": "error", "error": str(e)}
                        raise
                
                choice = response.get("choices", [{}])[0]
                message = choice.get("message", {})
                tool_calls = message.get("tool_calls", [])
                
                if tool_calls:
                    messages.append({
                        "role": "assistant",
                        "content": message.get("content", ""),
                        "tool_calls": tool_calls
                    })
                    
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        tool_name = func.get("name", "")
                        tool_args_str = func.get("arguments", "{}")
                        tool_id = tc.get("id", "")
                        
                        try:
                            tool_args = json.loads(tool_args_str)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        yield {"event": "tool_start", "tool": tool_name, "args": tool_args}
                        
                        result = await self._execute_tool(tool_name, tool_args, current_carrier)
                        
                        tool_calls_log.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result[:500] if len(result) > 500 else result
                        })
                        
                        yield {"event": "tool_end", "tool": tool_name, "result": result[:200]}
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": result
                        })
                    
                else:
                    final_answer = message.get("content", "")
                    yield {"event": "answer", "content": final_answer}
                    break
            
            latency_ms = (time.time() - start_time) * 1000
            
            yield {
                "event": "done",
                "answer": final_answer,
                "tool_calls": tool_calls_log,
                "tokens": total_tokens,
                "iterations": iteration,
                "latency_ms": latency_ms
            }


