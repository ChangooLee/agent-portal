"""
LangGraph Nodes for Legislation Agent

계층적 작업 분해를 위한 노드 구현:
1. entry_node - 초기 state 구성
2. planner_node - 질문 분석 및 작업 계획
3. search_laws_node - 법령 검색
4. get_details_node - 상세 정보 조회
5. analyze_node - 분석 수행
6. verify_node - 결과 검증
7. answer_formatter_node - 최종 응답 생성
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .state import LegislationAgentState
from .metrics import (
    start_legislation_span,
    inject_context_to_carrier,
    record_tool_call
)
from app.agents.common.mcp_client_base import create_mcp_client

logger = logging.getLogger(__name__)

# MCP 서버 이름
MCP_SERVER_NAME = "mcp-kr-legislation"
SERVICE_NAME = "agent-legislation"


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """텍스트에서 JSON 추출"""
    try:
        # JSON 코드 블록 찾기
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        return json.loads(text)
    except Exception:
        try:
            return json.loads(text)
        except Exception:
            return None


# ========== 1. Entry Node ==========

async def entry_node(state: LegislationAgentState) -> LegislationAgentState:
    """
    초기 state 구성 및 기본값 설정.
    
    OTEL:
    - span: "legislation.entry" (parent: root span)
    """
    with start_legislation_span("legislation.entry", {
        "question_length": len(state.get("question", "")),
        "session_id": state.get("session_id", "unknown")
    }, parent_carrier=state.get("otel_carrier")):
        # 기본값 설정
        if state.get("retry_count") is None:
            state["retry_count"] = 0
        if state.get("max_retries") is None:
            state["max_retries"] = int(os.getenv("LEGISLATION_MAX_RETRIES", "2"))
        if state.get("start_time") is None:
            state["start_time"] = time.time()
        if state.get("law_search_results") is None:
            state["law_search_results"] = []
        if state.get("law_articles") is None:
            state["law_articles"] = []
        if state.get("precedent_results") is None:
            state["precedent_results"] = []
        if state.get("tool_calls") is None:
            state["tool_calls"] = []
        if state.get("analysis_evidence") is None:
            state["analysis_evidence"] = []
        
        # Entry carrier 설정 (다른 노드들의 parent)
        entry_carrier = {}
        inject_context_to_carrier(entry_carrier)
        state["entry_carrier"] = entry_carrier
        
        logger.info(f"Entry node: question='{state['question'][:50]}...', session_id={state.get('session_id')}")
        
        return state


# ========== 2. Planner Node ==========

async def planner_node(state: LegislationAgentState) -> LegislationAgentState:
    """
    질문 분석 및 작업 계획 수립.
    
    책임:
    - 사용자 질문 분석
    - 필요한 작업 타입 결정 (법령 검색, 판례 검색, 상세 조회 등)
    - 작업 순서 계획
    
    OTEL:
    - span: "legislation.planner"
    - LLM 호출도 같은 TraceId로 연결
    """
    with start_legislation_span("legislation.planner", {
        "question": state["question"][:100]
    }, parent_carrier=state.get("otel_carrier")) as span:
        start_time = time.time()
        
        try:
            from app.services.litellm_service import litellm_service
            
            # 프롬프트 구성
            system_prompt = """당신은 법률 정보 분석 전문가입니다.
사용자의 질문을 분석하여 필요한 작업을 계획하세요.

사용 가능한 작업 타입:
1. search_laws: 법령 검색 (법령명, 키워드로 검색)
2. get_details: 법령 상세 정보 조회 (법령 ID 필요)
3. search_precedents: 판례 검색 (키워드로 검색)
4. analyze_related: 관련 법령 분석
5. compare_versions: 법령 버전 비교

다음 JSON 형식으로 응답하세요:
{
    "required_tasks": ["search_laws", "get_details"],
    "reasoning": "질문 분석 및 작업 선택 이유",
    "search_keywords": ["검색 키워드1", "검색 키워드2"],
    "needs_precedents": true/false,
    "needs_analysis": true/false
}"""
            
            user_prompt = f"""사용자 질문: {state['question']}

위 질문을 분석하여 필요한 작업을 계획하세요."""
            
            # LLM 호출
            model = os.getenv("LEGISLATION_MODEL", "claude-opus-4.5")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Get trace headers for context propagation
            trace_headers = {}
            if state.get("otel_carrier"):
                # Convert otel_carrier to trace headers (traceparent, tracestate)
                trace_headers = state.get("otel_carrier", {})
            
            response = await litellm_service.chat_completion_sync(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=1000,
                trace_headers=trace_headers,
                metadata={
                    "agent_id": "legislation",
                    "node": "planner",
                    "trace_id": state.get("trace_id")
                }
            )
            
            # 응답 파싱
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            plan = _extract_json(content)
            
            if plan:
                state["plan"] = plan
                state["required_tasks"] = plan.get("required_tasks", ["search_laws"])
            else:
                # 기본값: 법령 검색
                state["plan"] = {"required_tasks": ["search_laws"], "reasoning": "기본 작업 계획"}
                state["required_tasks"] = ["search_laws"]
            
            # 토큰 사용량 집계
            usage = response.get("usage", {})
            state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
            state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
            state["total_tokens"] = state.get("total_tokens", 0) + usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            state["llm_model"] = model
            
            logger.info(f"Plan created: {json.dumps(state['plan'])[:100]}...")
            
            return state
            
        except Exception as e:
            logger.error(f"Planner error: {e}")
            # 기본값으로 계속 진행
            state["plan"] = {"required_tasks": ["search_laws"], "reasoning": "기본 작업 계획"}
            state["required_tasks"] = ["search_laws"]
            return state


# ========== 3. Search Laws Node ==========

async def search_laws_node(state: LegislationAgentState) -> LegislationAgentState:
    """
    법령 검색 (MCP 도구 사용).
    
    책임:
    - MCP 도구를 사용하여 법령 검색
    - 검색 결과를 state에 저장
    
    OTEL:
    - span: "legislation.search_laws"
    - MCP 도구 호출도 같은 TraceId로 연결
    """
    with start_legislation_span("legislation.search_laws", {
        "has_plan": bool(state.get("plan"))
    }, parent_carrier=state.get("otel_carrier")) as span:
        start_time = time.time()
        
        try:
            # MCP 클라이언트 생성
            mcp_client = await create_mcp_client(
                server_name=MCP_SERVER_NAME,
                service_name=SERVICE_NAME
            )
            await mcp_client.connect()
            
            # 계획에서 검색 키워드 추출
            plan = state.get("plan", {})
            search_keywords = plan.get("search_keywords", [])
            
            if not search_keywords:
                # 질문에서 키워드 추출 (간단한 방법)
                question = state["question"]
                # 법령명 패턴 찾기 (예: "민법", "형법" 등)
                keywords = [question[:50]]  # 임시로 질문의 일부 사용
            
            # 법령 검색 도구 호출
            # 실제 MCP 도구: search_law (정밀 검색), search_law_unified (통합 검색)
            # 법령명을 모를 때는 search_law_unified 사용
            tool_name = "search_law_unified"  # 통합 검색 도구 사용
            tool_args = {
                "query": search_keywords[0] if search_keywords else state["question"][:50],
                "target": "law"  # 법령만 검색
            }
            
            tool_start = time.time()
            result = await mcp_client.call_tool(tool_name, tool_args)
            tool_latency = (time.time() - tool_start) * 1000
            
            # 도구 호출 기록
            record_tool_call(tool_name, tool_args, result.result, tool_latency)
            state["tool_calls"].append({
                "tool": tool_name,
                "args": tool_args,
                "success": result.error is None,
                "latency_ms": tool_latency
            })
            
            if result.error:
                logger.error(f"법령 검색 실패: {result.error}")
                state["law_search_results"] = []
            else:
                # 결과 파싱
                search_results = []
                if isinstance(result.result, str):
                    try:
                        parsed = json.loads(result.result)
                        if isinstance(parsed, list):
                            search_results = parsed
                        elif isinstance(parsed, dict):
                            # 단일 결과인 경우
                            search_results = [parsed]
                        else:
                            search_results = [{"raw": result.result}]
                    except:
                        # JSON 파싱 실패 시 문자열을 그대로 저장
                        search_results = [{"raw": result.result}]
                else:
                    search_results = result.result if isinstance(result.result, list) else [result.result]
                
                state["law_search_results"] = search_results
                
                # 첫 번째 결과를 선택 (나중에 개선 가능)
                if search_results and len(search_results) > 0:
                    first_result = search_results[0]
                    
                    # MCP 도구 응답 형식에 맞게 필드 추출
                    # 실제 MCP 응답 형식: {"법령명": "...", "법령일련번호": "...", ...}
                    state["selected_law_id"] = (
                        first_result.get("법령일련번호") or 
                        first_result.get("MST") or 
                        first_result.get("mst") or
                        first_result.get("id") or 
                        first_result.get("law_id")
                    )
                    state["selected_law_name"] = (
                        first_result.get("법령명") or
                        first_result.get("name") or 
                        first_result.get("law_name")
                    )
                    
                    logger.info(f"선택된 법령: ID={state['selected_law_id']}, Name={state['selected_law_name']}")
            
            logger.info(f"법령 검색 완료: {len(state['law_search_results'])}개 결과")
            
            return state
            
        except Exception as e:
            logger.error(f"Search laws error: {e}")
            state["law_search_results"] = []
            return state


# ========== 4. Get Details Node ==========

async def get_details_node(state: LegislationAgentState) -> LegislationAgentState:
    """
    법령 상세 정보 조회 (MCP 도구 사용).
    
    책임:
    - 선택된 법령의 상세 정보 조회
    - 조문, 연혁 등 추가 정보 조회
    
    OTEL:
    - span: "legislation.get_details"
    """
    with start_legislation_span("legislation.get_details", {
        "has_law_id": bool(state.get("selected_law_id"))
    }, parent_carrier=state.get("otel_carrier")) as span:
        try:
            if not state.get("selected_law_id") and not state.get("selected_law_name"):
                logger.warning("법령 ID/이름이 없어 상세 정보 조회 건너뜀")
                return state
            
            # MCP 클라이언트 생성
            mcp_client = await create_mcp_client(
                server_name=MCP_SERVER_NAME,
                service_name=SERVICE_NAME
            )
            await mcp_client.connect()
            
            # 법령 상세 정보 조회
            # MCP 도구: get_law_summary (요약), get_law_detail (상세)
            # 우선순위: MST(법령일련번호) > 법령명
            if state.get("selected_law_id"):
                # MST(법령일련번호)가 있으면 get_law_summary 사용
                tool_name = "get_law_summary"
                tool_args = {"law_id": str(state["selected_law_id"])}
            elif state.get("selected_law_name"):
                # 법령명이 있으면 get_law_summary 사용 (정확한 법령명만)
                law_name = state["selected_law_name"]
                # 검색 결과 전체가 아닌 실제 법령명만 추출
                if isinstance(law_name, str) and len(law_name) > 100:
                    # 검색 결과 전체가 전달된 경우, 첫 번째 결과에서 법령명 추출
                    if state.get("law_search_results"):
                        first_result = state["law_search_results"][0]
                        law_name = (
                            first_result.get("법령명") or
                            first_result.get("name") or 
                            first_result.get("law_name") or
                            "민법"  # 기본값
                        )
                tool_name = "get_law_summary"
                tool_args = {"law_name": law_name}
            else:
                # 둘 다 없으면 건너뜀
                logger.warning("법령 ID/이름이 없어 상세 정보 조회 건너뜀")
                return state
            
            tool_start = time.time()
            result = await mcp_client.call_tool(tool_name, tool_args)
            tool_latency = (time.time() - tool_start) * 1000
            
            record_tool_call(tool_name, tool_args, result.result, tool_latency)
            state["tool_calls"].append({
                "tool": tool_name,
                "args": tool_args,
                "success": result.error is None,
                "latency_ms": tool_latency
            })
            
            if not result.error:
                if isinstance(result.result, str):
                    try:
                        state["law_detail"] = json.loads(result.result)
                    except:
                        state["law_detail"] = {"raw": result.result}
                else:
                    state["law_detail"] = result.result
                
                # 조문 조회 (MST가 있는 경우)
                # MCP 도구: search_law_articles (mst 필요)
                if state.get("selected_law_id") and state["law_detail"]:
                    # law_detail에서 MST 추출 시도
                    mst = None
                    if isinstance(state["law_detail"], dict):
                        mst = state["law_detail"].get("MST") or state["law_detail"].get("mst") or state["law_detail"].get("법령일련번호")
                    
                    if mst:
                        try:
                            articles_result = await mcp_client.call_tool("search_law_articles", {
                                "mst": mst
                            })
                            if not articles_result.error:
                                if isinstance(articles_result.result, str):
                                    try:
                                        state["law_articles"] = json.loads(articles_result.result)
                                    except:
                                        state["law_articles"] = []
                                else:
                                    state["law_articles"] = articles_result.result if isinstance(articles_result.result, list) else [articles_result.result]
                        except Exception as e:
                            logger.warning(f"조문 조회 실패: {e}")
            
            logger.info(f"법령 상세 정보 조회 완료")
            
            return state
            
        except Exception as e:
            logger.error(f"Get details error: {e}")
            return state


# ========== 5. Analyze Node ==========

async def analyze_node(state: LegislationAgentState) -> LegislationAgentState:
    """
    분석 수행 (LLM 사용).
    
    책임:
    - 수집된 법령 정보를 바탕으로 분석 수행
    - 사용자 질문에 대한 답변 생성
    
    OTEL:
    - span: "legislation.analyze"
    """
    with start_legislation_span("legislation.analyze", {
        "has_law_detail": bool(state.get("law_detail")),
        "has_precedents": bool(state.get("precedent_results"))
    }, parent_carrier=state.get("otel_carrier")) as span:
        start_time = time.time()
        
        try:
            from app.services.litellm_service import litellm_service
            
            # 분석용 프롬프트 구성
            system_prompt = """당신은 한국 법률 정보 분석 전문가입니다.
수집된 법령 정보를 바탕으로 사용자의 질문에 정확하고 상세하게 답변하세요.

## 핵심 원칙
1. 정확한 법령 조문 인용
2. 관련 판례가 있으면 함께 제시
3. 법률 정보의 한계 명시
4. 전문가 상담 권고

## 응답 형식
마크다운 형식으로 구조화된 답변을 제공하세요:
- 요약
- 관련 법령
- 적용 사례 (판례 등)
- 주의사항"""
            
            # 컨텍스트 구성
            context_parts = []
            
            if state.get("law_detail"):
                context_parts.append(f"### 법령 상세 정보\n{json.dumps(state['law_detail'], ensure_ascii=False, indent=2)[:2000]}")
            
            if state.get("law_articles"):
                context_parts.append(f"### 법령 조문\n{json.dumps(state['law_articles'], ensure_ascii=False, indent=2)[:2000]}")
            
            if state.get("precedent_results"):
                context_parts.append(f"### 관련 판례\n{json.dumps(state['precedent_results'], ensure_ascii=False, indent=2)[:2000]}")
            
            context = "\n\n".join(context_parts) if context_parts else "법령 정보 없음"
            
            user_prompt = f"""사용자 질문: {state['question']}

수집된 법령 정보:
{context}

위 정보를 바탕으로 사용자의 질문에 답변하세요."""
            
            # LLM 호출
            model = os.getenv("LEGISLATION_MODEL", "claude-opus-4.5")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Get trace headers for context propagation
            trace_headers = {}
            if state.get("otel_carrier"):
                # Convert otel_carrier to trace headers (traceparent, tracestate)
                trace_headers = state.get("otel_carrier", {})
            
            response = await litellm_service.chat_completion_sync(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=4000,
                trace_headers=trace_headers,
                metadata={
                    "agent_id": "legislation",
                    "node": "analyze",
                    "trace_id": state.get("trace_id")
                }
            )
            
            # 응답 저장
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            state["analysis_result"] = content
            
            # 근거 저장
            state["analysis_evidence"] = []
            if state.get("law_detail"):
                state["analysis_evidence"].append({"type": "law_detail", "data": state["law_detail"]})
            if state.get("law_articles"):
                state["analysis_evidence"].append({"type": "law_articles", "data": state["law_articles"]})
            if state.get("precedent_results"):
                state["analysis_evidence"].append({"type": "precedents", "data": state["precedent_results"]})
            
            # 토큰 사용량 집계
            usage = response.get("usage", {})
            state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
            state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
            state["total_tokens"] = state.get("total_tokens", 0) + usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            
            logger.info(f"분석 완료: {len(content)}자")
            
            return state
            
        except Exception as e:
            logger.error(f"Analyze error: {e}")
            state["analysis_result"] = f"분석 중 오류가 발생했습니다: {str(e)}"
            return state


# ========== 6. Verify Node ==========

async def verify_node(state: LegislationAgentState) -> LegislationAgentState:
    """
    결과 검증.
    
    책임:
    - 분석 결과의 완전성 검증
    - 필수 정보 포함 여부 확인
    
    OTEL:
    - span: "legislation.verify"
    """
    with start_legislation_span("legislation.verify", {}, parent_carrier=state.get("otel_carrier")) as span:
        try:
            verification_result = {
                "passed": False,
                "checks": []
            }
            
            # 검증 체크리스트
            checks = []
            
            # 1. 분석 결과 존재 여부
            has_analysis = bool(state.get("analysis_result"))
            checks.append({
                "check": "analysis_result_exists",
                "passed": has_analysis,
                "message": "분석 결과가 생성되었습니다" if has_analysis else "분석 결과가 없습니다"
            })
            
            # 2. 법령 정보 존재 여부
            has_law_info = bool(state.get("law_detail") or state.get("law_search_results"))
            checks.append({
                "check": "law_info_exists",
                "passed": has_law_info,
                "message": "법령 정보가 수집되었습니다" if has_law_info else "법령 정보가 없습니다"
            })
            
            # 3. 분석 결과 길이 확인
            analysis_length = len(state.get("analysis_result", ""))
            has_sufficient_length = analysis_length > 100
            checks.append({
                "check": "analysis_length_sufficient",
                "passed": has_sufficient_length,
                "message": f"분석 결과 길이: {analysis_length}자" if has_sufficient_length else "분석 결과가 너무 짧습니다"
            })
            
            verification_result["checks"] = checks
            verification_result["passed"] = all(check["passed"] for check in checks)
            
            state["verification_result"] = verification_result
            state["verification_passed"] = verification_result["passed"]
            
            logger.info(f"검증 완료: {'통과' if verification_result['passed'] else '실패'}")
            
            return state
            
        except Exception as e:
            logger.error(f"Verify error: {e}")
            state["verification_result"] = {"passed": False, "error": str(e)}
            state["verification_passed"] = False
            return state


# ========== 7. Answer Formatter Node ==========

async def answer_formatter_node(state: LegislationAgentState) -> LegislationAgentState:
    """
    최종 응답 생성.
    
    책임:
    - 분석 결과를 최종 응답 형식으로 포맷팅
    - 사용된 도구 정보 포함
    
    OTEL:
    - span: "legislation.answer_formatter"
    """
    with start_legislation_span("legislation.answer_formatter", {}, parent_carrier=state.get("otel_carrier")) as span:
        try:
            # 분석 결과를 최종 응답으로 사용
            analysis_result = state.get("analysis_result", "")
            
            # 추가 정보 추가 (선택적)
            if state.get("law_detail"):
                law_name = state["law_detail"].get("name") or state.get("selected_law_name", "")
                if law_name:
                    analysis_result = f"## 관련 법령: {law_name}\n\n{analysis_result}"
            
            # 주의사항 추가
            disclaimer = "\n\n---\n\n**주의사항**: 법률 정보는 참고용이며, 구체적인 법률 문제는 변호사 등 법률 전문가와 상담하세요."
            analysis_result += disclaimer
            
            state["final_answer"] = analysis_result
            
            # 실행 시간 계산
            if state.get("start_time"):
                elapsed_time = time.time() - state["start_time"]
                logger.info(f"법률 에이전트 실행 완료: {elapsed_time:.2f}초, 토큰: {state.get('total_tokens', 0)}")
            
            return state
            
        except Exception as e:
            logger.error(f"Answer formatter error: {e}")
            state["final_answer"] = state.get("analysis_result", "응답 생성 중 오류가 발생했습니다.")
            return state
