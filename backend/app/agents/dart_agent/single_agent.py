"""
DART Single Agent - MCP 85개 도구 연결 단일 에이전트

Claude Opus 4.5를 사용하여 MCP 도구들을 직접 호출하는 단순한 ReAct 패턴 에이전트.
멀티에이전트 시스템 없이 단일 LLM이 모든 도구를 직접 활용.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional, AsyncGenerator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI

from app.agents.dart_agent.mcp_client import get_opendart_mcp_client, MCPTool
from app.agents.dart_agent.utils.prompt_templates import PromptBuilder
from app.agents.dart_agent.message_refiner import MessageRefiner

logger = logging.getLogger(__name__)


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
        self.max_iterations = 20
        self.llm = None
        self.tools: List[BaseTool] = []
        self.mcp_client = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """에이전트 초기화 (MCP 클라이언트, LLM, 도구)"""
        if self._initialized:
            return
        
        # MCP 클라이언트 초기화
        self.mcp_client = await get_opendart_mcp_client()
        await self.mcp_client.connect()
        
        # LLM 초기화 (LiteLLM 프록시 사용)
        import os
        litellm_api_key = os.environ.get("LITELLM_MASTER_KEY", "sk-1234")
        self.llm = ChatOpenAI(
            model=self.model_name,
            base_url="http://litellm:4000/v1",
            api_key=litellm_api_key,  # LiteLLM master key
            temperature=0.1,
            max_tokens=8192,
            timeout=600,  # 10분 타임아웃
        )
        
        # MCP 도구들을 LangChain Tool로 래핑
        mcp_tools = self.mcp_client.get_tools()
        self.tools = await self._wrap_mcp_tools(mcp_tools)
        
        logger.info(f"DartSingleAgent 초기화 완료: {len(self.tools)}개 도구 로드")
        self._initialized = True
    
    async def _wrap_mcp_tools(self, mcp_tools: List[MCPTool]) -> List[BaseTool]:
        """MCP 도구들을 LangChain Tool로 래핑"""
        langchain_tools = []
        
        for mcp_tool in mcp_tools:
            # 클로저를 위한 도구 이름 캡처
            tool_name = mcp_tool.name
            
            async def _call_mcp_tool(tool_name=tool_name, **kwargs) -> str:
                """MCP 도구 호출 래퍼"""
                try:
                    result = await self.mcp_client.call_tool(tool_name, kwargs)
                    if result.error:
                        return json.dumps({"error": result.error}, ensure_ascii=False)
                    return result.result if isinstance(result.result, str) else json.dumps(result.result, ensure_ascii=False)
                except Exception as e:
                    return json.dumps({"error": str(e)}, ensure_ascii=False)
            
            # StructuredTool 생성 - 클로저를 사용하여 tool_name 캡처
            def make_coroutine(captured_tool_name):
                async def coro(**kwargs):
                    return await _call_mcp_tool(tool_name=captured_tool_name, **kwargs)
                return coro
            
            lc_tool = StructuredTool.from_function(
                func=lambda **kwargs: None,  # 동기 함수 (사용 안함)
                coroutine=make_coroutine(tool_name),
                name=tool_name,
                description=mcp_tool.description or f"MCP tool: {tool_name}",
            )
            langchain_tools.append(lc_tool)
        
        return langchain_tools
    
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성 - 모든 도메인 통합"""
        base_prompt = """당신은 DART(전자공시시스템) 기업 공시 분석 전문가입니다.

사용자의 질문을 분석하고, 제공된 MCP 도구들을 활용하여 정확한 정보를 조회하고 분석합니다.

## 핵심 원칙

1. **정확한 데이터 우선**: 추측하지 말고 반드시 도구를 사용하여 실제 데이터를 조회하세요.
2. **단계적 분석**: 복잡한 질문은 여러 단계로 나누어 처리하세요.
3. **체계적 응답**: 조회한 데이터를 바탕으로 명확하고 구조화된 분석을 제공하세요.

## 주요 워크플로우

1. **기업 식별**: 먼저 기업명으로 corp_code를 조회합니다 (get_corporation_code_by_name)
2. **공시 조회**: 해당 기업의 최근 공시 목록을 확인합니다 (search_disclosure_list)
3. **상세 분석**: 필요한 재무/공시 데이터를 조회합니다 (get_single_acnt, get_financial_indicators 등)
4. **종합 분석**: 조회된 데이터를 바탕으로 분석 결과를 제공합니다

## 도구 사용 시 주의사항

- corp_code는 8자리 숫자 문자열입니다 (예: "00126256")
- 연도(bsns_year)는 4자리 문자열입니다 (예: "2024")
- 보고서 코드: 11011(사업보고서), 11012(반기보고서), 11013(1분기보고서), 11014(3분기보고서)
- 재무제표 구분: OFS(개별), CFS(연결)

## 응답 형식

분석 결과는 다음 형식으로 제공하세요:
1. 요약: 핵심 발견사항
2. 상세 분석: 데이터 기반 분석
3. 시사점: 투자자/이해관계자 관점의 의미"""
        
        return base_prompt
    
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
        
        try:
            # 초기화
            await self._ensure_initialized()
            
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
            
            while iteration < self.max_iterations:
                iteration += 1
                
                # LLM 호출 (도구 바인딩)
                llm_with_tools = self.llm.bind_tools(self.tools)
                
                try:
                    response = await llm_with_tools.ainvoke(messages)
                except Exception as e:
                    logger.error(f"LLM 호출 실패: {e}")
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
                        tool_id = tool_call.get("id", f"call_{iteration}")
                        
                        # 도구 호출 시작 이벤트
                        display_name = self.message_refiner.refine(tool_name, "tool_call")
                        action_message = self.message_refiner.get_action_message(tool_name)
                        
                        yield {
                            "event": "tool_start",
                            "tool": tool_name,
                            "display_name": display_name,
                            "action_message": action_message,
                            "args": tool_args
                        }
                        
                        # 도구 실행
                        tool_start = time.time()
                        try:
                            result = await self.mcp_client.call_tool(tool_name, tool_args)
                            tool_result = result.result if result.result else json.dumps({"error": result.error})
                        except Exception as e:
                            tool_result = json.dumps({"error": str(e)})
                        
                        tool_latency = (time.time() - tool_start) * 1000
                        
                        # 도구 완료 이벤트
                        yield {
                            "event": "tool_result",
                            "agent_name": "DartSingleAgent",
                            "tool": tool_name,
                            "display_name": display_name,
                            "latency_ms": tool_latency,
                            "success": "error" not in tool_result.lower() if isinstance(tool_result, str) else True
                        }
                        
                        # 메시지에 도구 결과 추가
                        messages.append(ToolMessage(
                            content=tool_result[:10000] if len(tool_result) > 10000 else tool_result,
                            tool_call_id=tool_id
                        ))
                
                else:
                    # 도구 호출 없음 = 최종 응답
                    final_response = response.content
                    break
            
            # 최종 응답
            if final_response:
                yield {
                    "event": "analysis",
                    "content": final_response
                }
            
            # 완료
            total_latency = (time.time() - start_time) * 1000
            yield {
                "event": "complete",
                "total_latency_ms": total_latency,
                "iterations": iteration
            }
            
        except Exception as e:
            logger.error(f"DartSingleAgent 오류: {e}", exc_info=True)
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

