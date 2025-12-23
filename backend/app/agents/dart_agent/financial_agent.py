"""
financial_agent.py
재무 데이터 수집 및 분석 전문 에이전트
"""

import time
import re
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from langchain_core.messages import ToolMessage, SystemMessage, HumanMessage

# Agent Portal imports
from .base import DartBaseAgent, LiteLLMAdapter
from .dart_types import (
    AnalysisContext,
    AgentResult,
    RiskLevel,
    AnalysisScope,
    AnalysisDomain,
    AnalysisDepth,
)
from .message_refiner import MessageRefiner
from .mcp_client import MCPTool, get_opendart_mcp_client
from .metrics import observe, record_counter
from .utils.prompt_templates import PromptBuilder

logger = logging.getLogger(__name__)

def log_step(step_name: str, status: str, message: str):
    """로깅 헬퍼 함수 (agent-platform 호환)"""
    logger.info(f"[{step_name}] {status}: {message}")

def log_agent_flow(agent_name: str, action: str, step: int, message: str):
    """에이전트 플로우 로깅 (agent-platform 호환)"""
    logger.info(f"[{agent_name}] Step {step} - {action}: {message}")

# observe 데코레이터는 metrics.py에서 import


class FinancialAgent(DartBaseAgent):
    """재무 데이터 수집 및 분석 전문 에이전트 (Agent Portal 마이그레이션)"""

    def __init__(self, model: str = "qwen-235b"):
        """FinancialAgent 초기화 (Agent Portal 구조)"""
        super().__init__(
            agent_name="FinancialAgent",
            model=model,
            max_iterations=10
        )

        self.agent_domain = "financial"
        self.message_refiner = MessageRefiner()
        self.prompt_builder = PromptBuilder()
        
        log_step("FinancialAgent 초기화", "SUCCESS", "재무 분석 에이전트 설정 완료")

    async def _filter_tools(self, tools: List[MCPTool]) -> List[MCPTool]:
        """재무 분석에서 사용할 도구 필터링"""
        target_tools = {
            "get_corporation_code_by_name",
            "get_corporation_info",
            "get_disclosure_list",
            "get_single_acnt",
            "get_multi_acnt",
            "get_single_acc",
            "get_single_index",
            "get_multi_index",
        }
        filtered = [t for t in tools if t.name in target_tools]
        log_step("도구 필터링 완료", "SUCCESS", f"Financial 도구: {len(filtered)}개")
        return filtered
    
    # _create_system_prompt()는 base.py에서 자동으로 prompt_builder를 사용하도록 구현됨

    def _create_analysis_prompt(self, context: AnalysisContext) -> str:
        """User Request Prompt 생성 - context 기반"""
        return self._create_user_request(context)

    @observe()
    async def analyze_financial_data(
        self, context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        """재무 데이터 분석 메인 함수 - LLM 기반 도구 선택 + 스트리밍"""
        logger.info(f"[FinancialAgent.analyze_financial_data] 함수 호출됨 - observe 데코레이터 테스트")
        start_time = time.time()
        
        try:
                # 1번 yield: 분석 시작
                yield {
                    "type": "progress",
                    "content": f"{context.corp_name}의 재무 데이터를 수집하겠습니다...",
                }

                log_agent_flow(
                    "FinancialAgent",
                    "재무 분석 시작",
                    0,
                    f"기업: {context.corp_name}, 질문: {context.user_question[:100]}...",
                )

                # BaseAgent 초기화 확인
                if not self._initialized:
                    yield {"type": "progress", "content": "에이전트를 초기화하고 있습니다..."}
                    await self.initialize()

                # 2번 yield: LLM 기반 도구 선택 시작

                # 분석 프롬프트 생성
                analysis_prompt = self._create_analysis_prompt(context)

                # LangGraph 에이전트 스트리밍 실행
                final_response = ""
                tools_used = []
                collected_data = {}

                # ★ 루프 바로 위에 추가: 호출 정보를 잠시 보관
                pending_calls = {}  # tool_call_id -> {"display_name": str, "args": dict, "t0": float}

                # User request prompt 생성
                user_prompt = self._create_analysis_prompt(context)
                
                async for chunk in self.agent_executor_stream(
                    {"messages": [("human", user_prompt)]},
                    config={
                        "configurable": {
                            "thread_id": f"financial_{context.corp_code}_{int(time.time())}"
                        }
                    },
                ):
                    # LangGraph 실행 과정을 실시간으로 처리
                    if "agent" in chunk:
                        # LLM의 응답 (도구 선택 이유 포함)
                        agent_messages = chunk["agent"]["messages"]
                        if agent_messages:
                            agent_message = agent_messages[-1]  # 가장 최근 메시지

                            if hasattr(agent_message, "content") and agent_message.content:
                                # LLM의 사고 과정 스트리밍 (기존 유지)
                                content = agent_message.content.strip()
                                if content:
                                    yield {
                                        "type": "progress",
                                        "content": f"재무 분석 에이전트 분석: {content}...",
                                    }
                                    if final_response:
                                        final_response += "\n" + content
                                    else:
                                        final_response = content

                            # (핵심) 도구 호출은 "출력 안 하고" 저장만 한다
                            if hasattr(agent_message, "tool_calls") and agent_message.tool_calls:
                                for tool_call in agent_message.tool_calls:
                                    tool_name = tool_call.get("name", "알 수 없는 도구")
                                    tool_args = tool_call.get("args", {}) or {}
                                    tool_args = self._process_tool_args(tool_args)

                                    # 페어링용 call_id 확보
                                    tc_id = (
                                        tool_call.get("id")
                                        or tool_call.get("tool_call_id")
                                        or f"{tool_name}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"
                                    )

                                    display_name = self.message_refiner.refine(tool_name)
                                    # 호출 로그는 지금 내보내지 않음! (병렬이라 순서 깨지므로)
                                    pending_calls[tc_id] = {
                                        "display_name": display_name,
                                        "args": tool_args,
                                        "t0": time.perf_counter(),
                                    }

                    elif "tools" in chunk:
                        # 도구 실행 결과 처리
                        tool_messages = chunk["tools"]["messages"]
                        for tool_message in tool_messages:
                            tool_name = getattr(tool_message, "name", None)
                            # 응답에 달린 tool_call_id로 pending과 매칭
                            tc_id = getattr(tool_message, "tool_call_id", None)
                            # None 값 필터링: tool_name이 None이면 pending_calls에서 역추적
                            if not tool_name:
                                if tc_id and tc_id in pending_calls:
                                    tool_name = pending_calls[tc_id].get("name", "도구")
                                else:
                                    tool_name = "도구"
                            tools_used.append(tool_name)
                            if tc_id and tc_id in pending_calls:
                                info = pending_calls.pop(tc_id)
                                display_name = info["display_name"]
                                tool_args = info["args"]

                                # 사용자 친화적 액션 메시지 (정적 매핑, 즉시 반환)
                                action_msg = self.message_refiner.get_action_message(tool_name)
                                yield {"type": "progress", "content": action_msg}

                                yield {
                                    "type": "tool_call",
                                    "tool_name": display_name,
                                    "tool_args": tool_args,
                                }
                            else:
                                # 매칭 실패 시 기존 방식으로 이름만 정제
                                display_name = self.message_refiner.refine(tool_name)

                            # 이어서 '응답 로그' 출력
                            if hasattr(tool_message, "content"):
                                extracted_text = self._extract_text_from_content(tool_message.content)
                                collected_data[tool_name] = extracted_text

                                yield {
                                    "type": "tool_result",
                                    "agent_name": self.agent_name,
                                    "content": extracted_text,
                                    "tool_name": display_name,
                                }

                # 🔥 AgentResult에 LLM의 실제 분석 결과를 담아서 반환
                agent_result = AgentResult(
                    agent_name=self.agent_name,
                    analysis_type="financial_streaming_analysis",
                    risk_level=RiskLevel.LOW,
                    key_findings=[final_response] if final_response else ["재무 데이터 분석 완료"],
                    supporting_data={
                        "llm_response": final_response,
                        "raw_financial_data": collected_data,
                        "execution_time": time.time() - start_time,
                    },
                    recommendations=[],
                    execution_time=time.time() - start_time,
                    tools_used=list(set(tools_used)),
                )
                
                # 최종 결과 yield (observe 데코레이터가 자동으로 span에 기록)
                logger.info(f"[FinancialAgent] Yielding AgentResult: agent_name={agent_result.agent_name}, key_findings_len={len(agent_result.key_findings) if agent_result.key_findings else 0}")
                yield agent_result
                return
                
        except Exception as e:
            log_step("재무 분석 오류", "ERROR", f"분석 중 오류 발생: {str(e)}")
            import traceback

            log_step("재무 분석 오류", "ERROR", f"스택 트레이스: {traceback.format_exc()}")

            # 에러 yield
            yield {"type": "error", "content": f"재무 분석 중 오류가 발생했습니다: {str(e)}"}

            agent_result = AgentResult(
                agent_name=self.agent_name,
                analysis_type="error",
                risk_level=RiskLevel.HIGH,
                key_findings=[f"분석 오류: {str(e)}"],
                supporting_data={"error": str(e)},
                recommendations=["시스템 상태 확인 필요"],
                execution_time=time.time() - start_time,
                tools_used=[],
            )

            yield agent_result
            return

    def _extract_text_from_content(self, content) -> str:
        """다양한 content 타입에서 텍스트 추출"""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # TextContent 리스트 처리
            texts = []
            for item in content:
                if hasattr(item, "text"):
                    texts.append(item.text)
                elif hasattr(item, "content"):
                    texts.append(str(item.content))
                else:
                    texts.append(str(item))
            return "".join(texts)
        elif hasattr(content, "text"):
            # 단일 TextContent 객체
            return content.text
        else:
            return str(content)

    def _setup_agent(self):
        """에이전트 설정"""
        try:
            log_step(f"{self.agent_name} 에이전트 설정", "START", "create_agent 생성 중...")
                        
            # 도메인별 프롬프트를 문자열로 직접 전달
            domain_prompt = self._create_domain_prompt()
            
            # create_agent로 에이전트 생성 (prompt에 문자열 직접 전달)
            self.agent = create_agent(
                model=self.llm_with_tools,
                tools=self.filtered_tools,
                prompt=SystemMessage(content=domain_prompt),
                checkpointer=self.checkpointer
            )
            
            log_step(f"{self.agent_name} 에이전트 설정", "SUCCESS", "create_agent 생성 완료")
            
        except Exception as e:
            log_step(f"{self.agent_name} 에이전트 설정", "FAIL", f"에이전트 설정 실패: {e}")
            raise
