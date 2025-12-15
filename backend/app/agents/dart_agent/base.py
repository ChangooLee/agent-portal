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

# LangChain 1.0 create_agent
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

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
    
    async def ainvoke(
        self,
        input: Any,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        LangChain 호환 ainvoke 메서드.
        
        Args:
            input: 입력 (문자열 또는 메시지 리스트)
            config: 설정
            
        Returns:
            LLM 응답 (content 속성을 가진 객체)
        """
        # 입력을 메시지 형식으로 변환
        if isinstance(input, str):
            messages = [{"role": "user", "content": input}]
        elif isinstance(input, list):
            messages = []
            for item in input:
                if hasattr(item, 'content'):
                    role = getattr(item, 'type', 'user')
                    if role == 'human':
                        role = 'user'
                    elif role == 'ai':
                        role = 'assistant'
                    messages.append({"role": role, "content": item.content})
                elif isinstance(item, dict):
                    messages.append(item)
                else:
                    messages.append({"role": "user", "content": str(item)})
        else:
            messages = [{"role": "user", "content": str(input)}]
        
        # 채팅 호출
        response = await self.chat(messages, **kwargs)
        
        # LangChain AIMessage 스타일로 반환
        class AIMessageLike:
            def __init__(self, content: str):
                self.content = content
                self.type = "ai"
        
        # 응답에서 content 추출
        content = ""
        if isinstance(response, dict):
            if "choices" in response:
                content = response["choices"][0].get("message", {}).get("content", "")
            elif "content" in response:
                content = response["content"]
            elif "message" in response:
                content = response["message"].get("content", "")
        elif hasattr(response, 'content'):
            content = response.content
        else:
            content = str(response)
        
        return AIMessageLike(content)


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
        self.agent_executor = None  # LangChain 1.0 create_agent 결과
        self.checkpointer = None  # 체크포인터
    
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
            
            # LangChain 도구로 변환 (pickle 오류 등 예외 발생 가능)
            try:
                self.filtered_tools = create_langchain_tools(
                    self.mcp_client,
                    name_filter=lambda n: any(t.name == n for t in filtered)
                )
            except Exception as tools_error:
                logger.error(f"{self.agent_name} LangChain 도구 변환 실패: {tools_error}", exc_info=True)
                # 도구 변환 실패 시 빈 리스트로 설정하고 계속 진행
                self.filtered_tools = []
                logger.warning(f"{self.agent_name} 도구 없이 계속 진행합니다")
            
            # LangChain 1.0 create_agent로 agent_executor 생성
            try:
                self.checkpointer = MemorySaver()
                system_prompt = self._create_system_prompt()
                
                # create_agent는 모델명 또는 BaseChatModel을 받음
                # LiteLLM 모델명 사용 (예: "qwen-235b")
                self.agent_executor = create_agent(
                    model=self.model,
                    tools=self.filtered_tools if self.filtered_tools else None,
                    system_prompt=system_prompt,
                    checkpointer=self.checkpointer,
                    name=self.agent_name
                )
                logger.info(f"{self.agent_name} create_agent 완료")
            except Exception as agent_error:
                logger.warning(f"{self.agent_name} create_agent 실패 (fallback 사용): {agent_error}")
                # create_agent 실패 시에도 계속 진행 (기존 run() 메서드 사용 가능)
                self.agent_executor = None
            
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
    
    def _create_user_request(self, context: Any) -> str:
        """실행 시 User Request 생성 - 동적 context 포함 (agent-platform 호환)."""
        # PromptBuilder가 있으면 사용
        if hasattr(self, 'prompt_builder') and hasattr(self, 'agent_domain'):
            tools_info = self._get_tools_description()
            return self.prompt_builder.build_user_request_prompt(
                context=context,
                domain=self.agent_domain,
                tools_info=tools_info
            )
        
        # PromptBuilder가 없으면 기본 포맷 사용
        if hasattr(context, 'user_question') and hasattr(context, 'corp_name') and hasattr(context, 'corp_code'):
            return f"""사용자 질문: {context.user_question}
기업명: {context.corp_name}
기업코드: {context.corp_code}
분석 유형: {getattr(context.scope, 'value', str(context.scope)) if hasattr(context, 'scope') else '일반'}

위 기업에 대해 분석하여 답변해주세요."""
        else:
            return str(context)
    
    def _get_tools_description(self) -> str:
        """도구 설명 문자열 생성 (agent-platform 호환)."""
        if hasattr(self, 'filtered_tools') and self.filtered_tools:
            tools_info = []
            for tool in self.filtered_tools:
                tool_name = getattr(tool, 'name', 'Unknown')
                tool_desc = getattr(tool, 'description', 'No description')
                tools_info.append(f"- {tool_name}: {tool_desc}")
            return "\n".join(tools_info)
        return "사용 가능한 도구가 없습니다."
    
    def _process_tool_args(self, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        도구 인자 전처리.
        
        JSON 문자열 파싱, 빈 값 제거 등을 수행합니다.
        
        Args:
            tool_args: 원본 도구 인자
            
        Returns:
            전처리된 도구 인자
        """
        if not tool_args:
            return {}
        
        processed = {}
        for key, value in tool_args.items():
            # 빈 값 제거
            if value is None or value == "" or value == []:
                continue
            
            # JSON 문자열 파싱 시도
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, (dict, list)):
                        value = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
            
            processed[key] = value
        
        return processed
    
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
                # Some MCP servers expose a "ctx" argument in their tool schema.
                # When we call tools directly (tool._arun / MCPHTTPClient.call_tool),
                # Pydantic default injection may not run, so ensure ctx is present.
                # NOTE: We always set it to None (never a string) unless explicitly provided.
                try:
                    if self.mcp_client and "ctx" not in arguments:
                        mcp_tool = self.mcp_client.get_tool_by_name(tool_name)
                        if mcp_tool and isinstance(mcp_tool.input_schema, dict):
                            props = mcp_tool.input_schema.get("properties", {}) or {}
                            if isinstance(props, dict) and "ctx" in props:
                                arguments = {**arguments, "ctx": None}
                except Exception:
                    # Do not fail tool execution due to ctx-injection logic
                    pass

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
        # 초기화를 generator 시작 전에 처리 (예외 발생 시 generator가 시작되지 않도록)
        try:
            await self.initialize()
        except Exception as init_error:
            logger.error(f"Agent initialization failed in run_stream: {init_error}", exc_info=True)
            # 초기화 실패 시 에러 이벤트를 yield하고 generator 종료
            try:
                yield {"event": "error", "error": f"에이전트 초기화 실패: {str(init_error)}"}
            except Exception as yield_error:
                logger.error(f"Failed to yield initialization error event: {yield_error}")
            try:
                yield {
                    "event": "done",
                    "answer": "",
                    "tool_calls": [],
                    "tokens": {"prompt": 0, "completion": 0, "total": 0},
                    "iterations": 0,
                    "latency_ms": 0,
                    "error": str(init_error)
                }
            except Exception as yield_error:
                logger.error(f"Failed to yield done event after initialization error: {yield_error}")
            # generator 종료 (예외를 전파하지 않음)
            return
        
        # 초기화 성공 후 generator 시작
        try:
            
            span_name = f"dart.{self.agent_name}"
            
            # start_dart_span() 호출도 안전하게 처리 (pickle 오류 등 예외 발생 가능)
            # 참고 프로젝트 패턴: 예외 발생 시에도 계속 진행
            try:
                span_context = start_dart_span(span_name, {"question_length": len(question)}, parent_carrier)
            except Exception as span_error:
                logger.warning(f"Failed to create span {span_name}: {span_error}")
                # span 생성 실패해도 계속 진행 (no-op context manager 사용)
                from contextlib import nullcontext
                span_context = nullcontext()
            
            # span context 사용 (예외 발생해도 계속 진행)
            with span_context:
                current_carrier = {}
                try:
                    inject_context_to_carrier(current_carrier)
                except Exception:
                    pass  # context injection 실패해도 계속 진행
                
                start_time = time.time()
                
                try:
                    yield {"event": "start", "agent": self.agent_name}
                except Exception as yield_error:
                    logger.error(f"Failed to yield start event: {yield_error}")
                    # yield 실패 시에도 계속 진행
                
                try:
                    messages = [
                        {"role": "system", "content": self._create_system_prompt()},
                        {"role": "user", "content": question}
                    ]
                    
                    tools_schema = self._get_tools_schema()
                except Exception as setup_error:
                    logger.error(f"Failed to setup messages/tools in run_stream: {setup_error}")
                    try:
                        yield {"event": "error", "error": f"에이전트 설정 실패: {str(setup_error)}"}
                    except Exception as yield_error:
                        logger.error(f"Failed to yield setup error event: {yield_error}")
                    try:
                        yield {
                            "event": "done",
                            "answer": "",
                            "tool_calls": [],
                            "tokens": {"prompt": 0, "completion": 0, "total": 0},
                            "iterations": 0,
                            "latency_ms": 0,
                            "error": str(setup_error)
                        }
                    except Exception as yield_error:
                        logger.error(f"Failed to yield done event after setup error: {yield_error}")
                    return
                tool_calls_log = []
                total_tokens = {"prompt": 0, "completion": 0, "total": 0}
                
                iteration = 0
                final_answer = ""
                
                while iteration < self.max_iterations:
                    iteration += 1
                    
                    try:
                        yield {"event": "iteration", "iteration": iteration}
                    except Exception as yield_error:
                        logger.error(f"Failed to yield iteration event: {yield_error}")
                        # yield 실패 시 루프 종료
                        break
                    
                    # LLM 호출
                    try:
                        with start_llm_call_span(self.agent_name, self.model, messages, current_carrier) as (llm_span, record_llm):
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
                        logger.error(f"LLM call failed in run_stream: {e}")
                        try:
                            yield {"event": "error", "error": f"LLM 호출 실패: {str(e)}"}
                        except Exception as yield_error:
                            logger.error(f"Failed to yield error event: {yield_error}")
                        # 에러 이벤트를 yield한 후 종료
                        try:
                            yield {
                                "event": "done",
                                "answer": final_answer,
                                "tool_calls": tool_calls_log,
                                "tokens": total_tokens,
                                "iterations": iteration,
                                "latency_ms": (time.time() - start_time) * 1000,
                                "error": str(e)
                            }
                        except Exception as yield_error:
                            logger.error(f"Failed to yield done event: {yield_error}")
                        return
                    
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
                            
                            try:
                                yield {"event": "tool_start", "tool": tool_name, "args": tool_args}
                            except Exception as yield_error:
                                logger.error(f"Failed to yield tool_start event: {yield_error}")
                                # yield 실패 시에도 계속 진행
                            
                            try:
                                result = await self._execute_tool(tool_name, tool_args, current_carrier)
                                
                                tool_calls_log.append({
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "result": result[:500] if len(result) > 500 else result
                                })
                                
                                try:
                                    yield {"event": "tool_end", "tool": tool_name, "result": result[:200]}
                                except Exception as yield_error:
                                    logger.error(f"Failed to yield tool_end event: {yield_error}")
                                
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "content": result
                                })
                            except Exception as e:
                                logger.error(f"Tool execution failed in run_stream: {tool_name} - {e}")
                                error_result = f"Error: {str(e)}"
                                tool_calls_log.append({
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "result": error_result,
                                    "error": True
                                })
                                try:
                                    yield {"event": "tool_error", "tool": tool_name, "error": str(e)}
                                except Exception as yield_error:
                                    logger.error(f"Failed to yield tool_error event: {yield_error}")
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "content": error_result
                                })
                        
                    else:
                        final_answer = message.get("content", "")
                        try:
                            yield {"event": "answer", "content": final_answer}
                        except Exception as yield_error:
                            logger.error(f"Failed to yield answer event: {yield_error}")
                        break
                
                latency_ms = (time.time() - start_time) * 1000
                
                try:
                    yield {
                        "event": "done",
                        "answer": final_answer,
                        "tool_calls": tool_calls_log,
                        "tokens": total_tokens,
                        "iterations": iteration,
                        "latency_ms": latency_ms
                    }
                except Exception as yield_error:
                    logger.error(f"Failed to yield done event: {yield_error}")
        except Exception as e:
            # 최상위 예외 처리: generator가 정상적으로 종료되도록 보장
            logger.error(f"Unexpected error in run_stream: {e}", exc_info=True)
            try:
                yield {"event": "error", "error": f"예기치 않은 오류: {str(e)}"}
            except Exception as yield_error:
                logger.error(f"Failed to yield error event in exception handler: {yield_error}")
            try:
                yield {
                    "event": "done",
                    "answer": "",
                    "tool_calls": [],
                    "tokens": {"prompt": 0, "completion": 0, "total": 0},
                    "iterations": 0,
                    "latency_ms": 0,
                    "error": str(e)
                }
            except Exception as yield_error:
                logger.error(f"Failed to yield done event in exception handler: {yield_error}")
    
    async def agent_executor_stream(
        self,
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ):
        """
        agent_executor.astream() 래퍼 메서드.
        
        agent_executor가 없으면 기존 run_stream()으로 fallback하고
        LangGraph 스타일 청크로 변환.
        
        Args:
            input_data: {"messages": [...]} 형태의 입력
            config: LangGraph config
            
        Yields:
            LangGraph 스타일 청크
        """
        await self.initialize()
        
        if self.agent_executor is not None:
            # agent_executor가 있으면 직접 사용
            async for chunk in self.agent_executor.astream(input_data, config or {}):
                yield chunk
        else:
            # agent_executor가 없으면 기존 run_stream()으로 fallback
            messages = input_data.get("messages", [])
            question = ""
            
            for msg in messages:
                if isinstance(msg, tuple) and len(msg) == 2:
                    role, content = msg
                    if role == "human":
                        question = content
                        break
                elif hasattr(msg, 'content'):
                    question = msg.content
                    break
                elif isinstance(msg, str):
                    question = msg
                    break
            
            if not question:
                yield {"agent": {"messages": [AIMessage(content="질문을 찾을 수 없습니다.")]}}
                return
            
            thread_id = None
            if config and "configurable" in config:
                thread_id = config["configurable"].get("thread_id")
            
            # run_stream()으로 실행하고 LangGraph 스타일로 변환
            async for event in self.run_stream(question, thread_id):
                event_type = event.get("event", "")
                
                if event_type == "answer":
                    # 최종 응답
                    yield {"agent": {"messages": [AIMessage(content=event.get("content", ""))]}}
                    
                elif event_type == "tool_start":
                    # 도구 호출 시작 (tool_calls로 변환)
                    tool_name = event.get("tool", "")
                    tool_args = event.get("args", {})
                    import uuid as uuid_mod
                    tool_call = {
                        "id": f"call_{uuid_mod.uuid4().hex[:8]}",
                        "name": tool_name,
                        "args": tool_args
                    }
                    yield {"agent": {"messages": [AIMessage(content="", tool_calls=[tool_call])]}}
                    
                elif event_type == "tool_end":
                    # 도구 결과
                    tool_name = event.get("tool", "")
                    result = event.get("result", "")
                    yield {"tools": {"messages": [ToolMessage(content=str(result), tool_call_id=f"call_{tool_name}")]}}
                    
                elif event_type == "done":
                    # 완료
                    answer = event.get("answer", "")
                    if answer:
                        yield {"agent": {"messages": [AIMessage(content=answer)]}}
                        
                elif event_type == "error":
                    error_msg = event.get("error", "오류 발생")
                    yield {"agent": {"messages": [AIMessage(content=f"오류: {error_msg}")]}}
    
    async def process_chat_request_stream(
        self,
        message: str,
        thread_id: Optional[str] = None
    ):
        """
        agent-platform 호환 스트리밍 채팅 요청 처리.
        
        LangChain 1.0 create_agent 기반 agent_executor.astream() 사용.
        
        Args:
            message: 사용자 메시지
            thread_id: 세션 ID (선택)
            
        Yields:
            Dict[str, Any]: 스트림 이벤트
        """
        try:
            await self.initialize()
            
            if self.agent_executor is None:
                # agent_executor가 없으면 기존 run_stream() 사용
                logger.warning(f"{self.agent_name}: agent_executor 없음, run_stream() fallback")
                async for event in self.run_stream(message, thread_id):
                    # 이벤트 형식 변환
                    if event.get("event") == "answer":
                        yield {"type": "agent_response", "content": event.get("content", "")}
                    elif event.get("event") == "done":
                        yield {"type": "agent_response", "content": event.get("answer", "")}
                    elif event.get("event") == "error":
                        yield {"type": "error", "content": event.get("error", "")}
                return
            
            # LangChain 1.0 스트리밍 처리
            import uuid
            config = {
                "recursion_limit": max(100, 2 * self.max_iterations + 1),
                "configurable": {"thread_id": thread_id or f"default_{uuid.uuid4().hex[:8]}"}
            }
            
            messages = [HumanMessage(content=message)]
            final_response = ""
            tools_used = []
            
            async for chunk in self.agent_executor.astream(
                {"messages": messages}, config
            ):
                try:
                    # Content Blocks 지원 (LangChain 1.0)
                    if hasattr(chunk, "content_blocks") and chunk.content_blocks:
                        for block in chunk.content_blocks:
                            if block.type == "text":
                                final_response += block.text
                                yield {
                                    "type": "agent_response",
                                    "content": block.text,
                                    "metadata": getattr(block, "metadata", {})
                                }
                    # 기존 content 속성 지원
                    elif hasattr(chunk, "content") and chunk.content:
                        final_response += chunk.content
                        yield {
                            "type": "agent_response",
                            "content": chunk.content,
                            "metadata": getattr(chunk, "metadata", {})
                        }
                    # 딕셔너리 형태의 청크
                    elif isinstance(chunk, dict):
                        if "messages" in chunk:
                            for msg in chunk["messages"]:
                                if hasattr(msg, "content") and msg.content:
                                    final_response += msg.content
                                    yield {
                                        "type": "agent_response",
                                        "content": msg.content
                                    }
                except Exception as chunk_error:
                    logger.warning(f"청크 처리 중 오류: {chunk_error}")
                    continue
            
            logger.info(f"{self.agent_name} 스트리밍 완료: {len(final_response)}자")
            
        except ImportError as ie:
            logger.error(f"Langchain import error: {ie}")
            yield {"type": "error", "content": f"LangChain 의존성 오류: {str(ie)}"}
        except Exception as e:
            logger.error(f"process_chat_request_stream error: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}


