"""
DART Single Agent - MCP 85개 도구 연결 단일 에이전트

Claude Opus 4.5를 사용하여 MCP 도구들을 직접 호출하는 ReAct 패턴 에이전트.
멀티에이전트 시스템 없이 단일 LLM이 모든 도구를 직접 활용.
"""

import json
import logging
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator, Type

from pydantic import BaseModel, Field, create_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI

from app.agents.dart_agent.mcp_client import get_opendart_mcp_client, MCPTool
from app.agents.dart_agent.utils.prompt_templates import PromptBuilder
from app.agents.dart_agent.message_refiner import MessageRefiner
from app.agents.dart_agent.metrics import inject_context_to_carrier, start_dart_span

# traceparent 헤더 생성 함수
def _get_traceparent_headers() -> Dict[str, str]:
    """현재 context에서 traceparent 헤더 생성"""
    try:
        from opentelemetry.propagate import inject
        carrier = {}
        inject(carrier)
        return carrier
    except Exception:
        return {}

logger = logging.getLogger(__name__)


def _record_otel_event(event_name: str, data: dict, carrier: dict = None):
    """간단한 이벤트 로깅 (OTEL 대체)"""
    logger.info(f"[OTEL Event] {event_name}: {data}")


def _get_current_span_carrier() -> dict:
    """현재 span carrier 반환"""
    carrier = {}
    try:
        inject_context_to_carrier(carrier)
    except Exception:
        pass
    return carrier


def _create_args_schema(input_schema: Dict[str, Any], tool_name: str) -> Type[BaseModel]:
    """
    MCP input_schema에서 Pydantic 모델 동적 생성
    
    Args:
        input_schema: MCP 도구의 input_schema
        tool_name: 도구 이름
        
    Returns:
        동적으로 생성된 Pydantic 모델 클래스
    """
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    
    fields = {}
    for prop_name, prop_info in properties.items():
        # ctx 파라미터는 제외 (내부 사용)
        if prop_name == "ctx":
            continue
        
        prop_type = prop_info.get("type", "string")
        description = prop_info.get("description", "")
        default = prop_info.get("default", ...)
        
        # 타입 매핑
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        python_type = type_map.get(prop_type, str)
        
        # 필수 여부에 따라 기본값 설정
        if prop_name in required:
            fields[prop_name] = (python_type, Field(description=description))
        else:
            # 기본값이 ... 이면 Optional로 처리
            if default is ...:
                default = None
            fields[prop_name] = (Optional[python_type], Field(default=default, description=description))
    
    # 동적 모델 생성
    model_name = f"{tool_name.replace('-', '_').title().replace('_', '')}Args"
    return create_model(model_name, **fields)


class DartSingleAgent:
    """
    DART 단일 에이전트 - MCP 도구 직접 연결
    
    Claude Opus 4.5를 사용하여 ReAct 패턴으로 동작.
    모든 MCP 도구(85개)를 LangChain Tool로 래핑하여 사용.
    """
    
    def __init__(self, model: str = "claude-opus-4.5"):
        self.model_name = model
        self.prompt_builder = PromptBuilder()
        self.message_refiner = MessageRefiner()
        self.max_iterations = 30  # 복잡한 분석을 위해 증가
        self.llm = None
        self.tools: List[BaseTool] = []
        self.mcp_client = None
        self._initialized = False
    
    async def _ensure_mcp_initialized(self):
        """MCP 클라이언트 초기화"""
        if self.mcp_client is not None:
            return
        
        # MCP 클라이언트 초기화
        self.mcp_client = await get_opendart_mcp_client()
        await self.mcp_client.connect()
        
        # MCP 도구들을 LangChain Tool로 래핑
        mcp_tools = self.mcp_client.get_tools()
        self.tools = await self._wrap_mcp_tools(mcp_tools)
        logger.info(f"MCP 초기화 완료: {len(self.tools)}개 도구 로드")

    def _create_llm_with_tracing(self) -> ChatOpenAI:
        """traceparent 헤더를 포함한 LLM 인스턴스 생성 (root span 내에서 호출)"""
        litellm_api_key = os.environ.get("LITELLM_MASTER_KEY", "sk-1234")
        trace_headers = _get_traceparent_headers()
        
        logger.debug(f"LLM 생성 (traceparent: {trace_headers.get('traceparent', 'none')})")
        
        return ChatOpenAI(
            model=self.model_name,
            base_url="http://litellm:4000/v1",
            api_key=litellm_api_key,
            default_headers=trace_headers,  # traceparent 전달
            temperature=0.1,
            max_tokens=16384,
            timeout=600,
        )
    
    async def _wrap_mcp_tools(self, mcp_tools: List[MCPTool]) -> List[BaseTool]:
        """MCP 도구들을 LangChain Tool로 래핑 (스키마 포함)"""
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
            
            # 클로저를 위한 도구 이름 및 mcp_client 캡처
            def make_coroutine(captured_tool_name, captured_mcp_client):
                async def coro(**kwargs) -> str:
                    """MCP 도구 호출 래퍼"""
                    # ctx 파라미터 제거
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
                "func": lambda **kwargs: None,  # 동기 함수 (사용 안함)
                "coroutine": make_coroutine(tool_name, self.mcp_client),
                "name": tool_name,
                "description": mcp_tool.description or f"MCP tool: {tool_name}",
            }
            
            if args_schema:
                tool_kwargs["args_schema"] = args_schema
            
            lc_tool = StructuredTool.from_function(**tool_kwargs)
            langchain_tools.append(lc_tool)
        
        return langchain_tools
    
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성 - 모든 도메인 통합"""
        # 현재 시스템 일자 기준으로 최신 데이터 조회 안내
        current_date = datetime.now()
        current_year = current_date.year
        current_date_str = current_date.strftime("%Y년 %m월 %d일")
        
        return f"""당신은 DART(전자공시시스템) 기업 공시 분석 전문가입니다.
사용자의 질문을 분석하고, 제공된 MCP 도구들을 활용하여 정확한 정보를 조회하고 분석합니다.

## 현재 시스템 일자

**오늘 날짜: {current_date_str}**

이 날짜를 기준으로 가장 최신 데이터를 조회하세요.
- 최신 연도: {current_year}년 또는 {current_year - 1}년
- 공시 조회 시 bgn_de/end_de는 최근 1년 이내로 설정
- 재무제표 조회 시 bsns_year는 {current_year - 1}년 또는 {current_year}년 사용

## 핵심 원칙

1. **정확한 데이터 우선**: 추측하지 말고 반드시 도구를 사용하여 실제 데이터를 조회하세요.
2. **단계적 분석**: 복잡한 질문은 여러 단계로 나누어 처리하세요.
3. **체계적 응답**: 조회한 데이터를 바탕으로 명확하고 구조화된 분석을 제공하세요.
4. **최신 데이터**: 오늘 날짜({current_date_str}) 기준 가장 최신 데이터를 우선 조회하세요.

## 주요 워크플로우

1. **기업 식별**: 먼저 기업명으로 corp_code를 조회합니다 (get_corporation_code_by_name)
2. **기업 정보 확인**: 기업 기본 정보를 조회합니다 (get_corporation_info)
3. **공시 조회**: 해당 기업의 최근 공시 목록을 확인합니다 (get_disclosure_list)
4. **상세 분석**: 필요한 재무/공시 데이터를 조회합니다
   - 재무제표: get_single_acnt, get_multi_acnt
   - 재무지표: get_single_index, get_financial_indicators
   - 주주정보: get_major_shareholder, get_minority_shareholder
   - 임원정보: get_executive_info, get_individual_compensation
   - 지배구조: get_board_of_directors, get_audit_committee
5. **공시 문서 분석**: 필요시 원본 문서 조회 (get_disclosure_document)
6. **종합 분석**: 조회된 데이터를 바탕으로 분석 결과를 제공합니다

## 도구 사용 시 주의사항

- **corp_code**: 8자리 숫자 문자열 (예: "00126256"). get_corporation_code_by_name으로 조회
- **bsns_year**: 4자리 연도 문자열 (예: "2024")
- **reprt_code**: 보고서 코드
  - 11011: 사업보고서 (연간)
  - 11012: 반기보고서
  - 11013: 1분기보고서
  - 11014: 3분기보고서
- **fs_div**: 재무제표 구분
  - OFS: 개별재무제표
  - CFS: 연결재무제표 (권장)
- **rcp_no**: 공시 접수번호 (14자리). get_disclosure_list에서 조회
- **idx_cl_code**: 지표분류코드
  - M210000: 수익성지표
  - M220000: 안정성지표
  - M230000: 성장성지표
  - M240000: 활동성지표

## 복수 기업 비교 분석

여러 기업을 비교 분석할 때:
1. 각 기업의 corp_code를 먼저 모두 조회
2. 동일한 기준(연도, 보고서 유형)으로 데이터 수집
3. 표 형식으로 비교 정리
4. 차이점과 시사점 분석

## 응답 형식

분석 결과는 마크다운 형식으로 제공하세요:

### 1. 요약
핵심 발견사항을 간결하게 정리

### 2. 상세 분석
데이터 기반의 상세 분석 (표, 수치 포함)

### 3. 시사점
투자자/이해관계자 관점에서의 의미

### 4. 참고 자료
조회한 공시 정보 (공시명, 접수번호, 날짜)"""
    
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
        
        # Root span 생성 (gen_ai.session) - 모든 하위 호출이 같은 TraceId 공유
        with start_dart_span("gen_ai.session", {
            "gen_ai.agent.id": "dart-single-agent",
            "gen_ai.agent.name": "DART Single Agent",
            "gen_ai.request.model": self.model_name,
            "session.id": session_id,
        }) as root_span:
            # 현재 span의 context를 carrier에 저장 (하위 호출에 전달용)
            parent_carrier = _get_current_span_carrier()
            
            _record_otel_event("single_agent_start", {
                "question": question,
                "session_id": session_id,
                "model": self.model_name
            }, parent_carrier)
            
            try:
                # MCP 초기화
                await self._ensure_mcp_initialized()
                
                # LLM 생성 (root span 내에서 생성하여 traceparent 포함)
                llm = self._create_llm_with_tracing()
                
                yield {
                    "event": "start",
                    "agent": "DartSingleAgent",
                    "model": self.model_name,
                    "tools_count": len(self.tools)
                }
                
                # 메시지 구성
                messages = [SystemMessage(content=self._build_system_prompt())]
                
                # 이전 대화 기록 추가
                if conversation_history:
                    for msg in conversation_history:
                        if msg.get("role") == "user":
                            messages.append(HumanMessage(content=msg.get("content", "")))
                        elif msg.get("role") == "assistant":
                            messages.append(AIMessage(content=msg.get("content", "")))
                
                # 현재 질문 추가
                messages.append(HumanMessage(content=question))
                
                yield {
                    "event": "thinking",
                    "content": "질문을 분석하고 있습니다..."
                }
                
                # ReAct 루프
                iteration = 0
                final_response = ""
                total_tool_calls = 0
                
                while iteration < self.max_iterations:
                    iteration += 1
                    
                    # LLM 호출 (도구 바인딩)
                    llm_with_tools = llm.bind_tools(self.tools)
                    
                    try:
                        response = await llm_with_tools.ainvoke(messages)
                    except Exception as e:
                        logger.error(f"LLM 호출 실패: {e}")
                        _record_otel_event("llm_error", {"error": str(e), "iteration": iteration}, parent_carrier)
                        yield {
                            "event": "error",
                            "error": f"LLM 호출 실패: {str(e)}"
                        }
                        break
                    
                    # 도구 호출이 있는 경우
                    if response.tool_calls:
                        messages.append(response)
                        
                        for tool_call in response.tool_calls:
                            tool_name = tool_call.get("name")
                            tool_args = tool_call.get("args", {})
                            tool_id = tool_call.get("id", f"call_{iteration}_{total_tool_calls}")
                            
                            total_tool_calls += 1
                            
                            # 도구 호출 시작 이벤트
                            display_name = self.message_refiner.refine(tool_name, "tool_call")
                            action_message = self.message_refiner.get_action_message(tool_name)
                            
                            yield {
                                "event": "tool_start",
                                "tool": tool_name,
                                "display_name": display_name,
                                "action_message": action_message,
                                "args": tool_args,
                                "iteration": iteration
                            }
                            
                            # 도구 실행
                            tool_start = time.time()
                            try:
                                # ctx 파라미터 제거
                                clean_args = {k: v for k, v in tool_args.items() if k != "ctx"}
                                result = await self.mcp_client.call_tool(tool_name, clean_args)
                                tool_result = result.result if result.result else json.dumps({"error": result.error})
                            except Exception as e:
                                tool_result = json.dumps({"error": str(e)})
                                logger.error(f"도구 호출 실패: {tool_name}, 에러: {e}")
                            
                            tool_latency = (time.time() - tool_start) * 1000
                            
                            # 도구 완료 이벤트
                            is_success = "error" not in str(tool_result).lower()[:100]
                            yield {
                                "event": "tool_result",
                                "agent_name": "DartSingleAgent",
                                "tool": tool_name,
                                "display_name": display_name,
                                "latency_ms": tool_latency,
                                "success": is_success
                            }
                            
                            # 메시지에 도구 결과 추가 (너무 길면 자르기)
                            truncated_result = tool_result
                            if isinstance(tool_result, str) and len(tool_result) > 50000:
                                truncated_result = tool_result[:50000] + "\n...[결과가 너무 길어 일부 생략됨]"
                            
                            messages.append(ToolMessage(
                                content=truncated_result,
                                tool_call_id=tool_id
                            ))
                    
                    else:
                        # 도구 호출 없음 = 최종 응답
                        final_response = response.content
                        break
                
                # 최종 응답 스트리밍
                if final_response:
                    # 청크 단위로 스트리밍
                    chunk_size = 100
                    for i in range(0, len(final_response), chunk_size):
                        chunk = final_response[i:i+chunk_size]
                        yield {
                            "event": "content",
                            "content": chunk
                        }
                    
                    yield {
                        "event": "analysis",
                        "content": final_response
                    }
                
                # 완료
                total_latency = (time.time() - start_time) * 1000
                
                _record_otel_event("single_agent_complete", {
                    "total_latency_ms": total_latency,
                    "iterations": iteration,
                    "tool_calls": total_tool_calls
                }, parent_carrier)
                
                yield {
                    "event": "complete",
                    "total_latency_ms": total_latency,
                    "iterations": iteration,
                    "tool_calls": total_tool_calls
                }
                
            except Exception as e:
                logger.error(f"DartSingleAgent 오류: {e}", exc_info=True)
                _record_otel_event("single_agent_error", {"error": str(e)}, parent_carrier)
                yield {
                    "event": "error",
                    "error": str(e)
                }
                yield {
                    "event": "complete",
                    "total_latency_ms": (time.time() - start_time) * 1000,
                    "error": str(e)
                }


# 싱글톤
_single_agent: Optional[DartSingleAgent] = None


def get_dart_single_agent(model: str = "claude-opus-4.5") -> DartSingleAgent:
    """DART 단일 에이전트 싱글톤 반환"""
    global _single_agent
    if _single_agent is None:
        _single_agent = DartSingleAgent(model=model)
    return _single_agent
