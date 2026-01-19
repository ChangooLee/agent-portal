"""
LangGraph StateGraph for Legislation Agent

계층적 작업 분해를 위한 그래프 구성:
entry -> planner -> search_laws -> get_details -> analyze -> verify -> answer_formatter -> END

트레이스 구조:
- 단일 TraceId로 모든 노드가 연결됨
- Parent-Child 관계로 트리 형태 트레이스 생성
- LLM 호출도 같은 TraceId 하에 연결
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager

from langgraph.graph import StateGraph, END

from .state import LegislationAgentState, create_initial_state
from .nodes import (
    entry_node,
    planner_node,
    search_laws_node,
    get_details_node,
    analyze_node,
    verify_node,
    answer_formatter_node
)
from .metrics import start_legislation_span, inject_context_to_carrier

logger = logging.getLogger(__name__)


def route_after_verify(state: LegislationAgentState) -> str:
    """
    verify 이후 조건부 라우팅.
    
    - verification_passed == True → answer_formatter (성공)
    - retry_count < max_retries → analyze (재시도)
    - else → answer_formatter (실패해도 응답 생성)
    """
    if state.get("verification_passed", False):
        return "answer_formatter"
    elif state.get("retry_count", 0) < state.get("max_retries", 2):
        # 재시도: analyze 노드로 다시
        state["retry_count"] = state.get("retry_count", 0) + 1
        return "analyze"
    else:
        # 최대 재시도 초과: 그래도 응답 생성
        return "answer_formatter"


def route_after_planner(state: LegislationAgentState) -> str:
    """
    planner 이후 조건부 라우팅.
    
    required_tasks에 따라 다음 노드 결정.
    """
    required_tasks = state.get("required_tasks", [])
    
    if "search_laws" in required_tasks:
        return "search_laws"
    elif "get_details" in required_tasks:
        return "get_details"
    else:
        # 기본: 법령 검색
        return "search_laws"


def build_legislation_graph() -> StateGraph:
    """
    법률 에이전트 LangGraph 구성.
    
    노드 흐름:
    entry -> planner -> (search_laws -> get_details) -> analyze 
          -> verify -> (answer_formatter | analyze 재시도 | answer_formatter)
          -> END
    
    Returns:
        컴파일된 LangGraph 앱
    """
    # StateGraph 생성
    graph = StateGraph(LegislationAgentState)
    
    # ========== 노드 등록 ==========
    graph.add_node("entry", entry_node)
    graph.add_node("planner", planner_node)
    graph.add_node("search_laws", search_laws_node)
    graph.add_node("get_details", get_details_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("verify", verify_node)
    graph.add_node("answer_formatter", answer_formatter_node)
    
    # ========== 엣지 연결 ==========
    
    # 시작점 설정
    graph.set_entry_point("entry")
    
    # 직선 경로 엣지
    graph.add_edge("entry", "planner")
    
    # planner 이후 조건부 엣지
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "search_laws": "search_laws",
            "get_details": "get_details"
        }
    )
    
    # search_laws 이후 get_details로
    graph.add_edge("search_laws", "get_details")
    
    # get_details 이후 analyze로
    graph.add_edge("get_details", "analyze")
    
    # analyze 이후 verify로
    graph.add_edge("analyze", "verify")
    
    # verify 이후 조건부 엣지
    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "answer_formatter": "answer_formatter",
            "analyze": "analyze"  # 재시도
        }
    )
    
    # 종료 노드
    graph.add_edge("answer_formatter", END)
    
    logger.info("Legislation graph built successfully")
    
    return graph.compile()


class LegislationGraphAgent:
    """
    법률 에이전트 LangGraph 래퍼 클래스.
    
    사용 예:
        agent = LegislationGraphAgent()
        result = await agent.run(
            question="민법 제1조의 내용은?",
            session_id="session-123"
        )
    """
    
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.graph = build_legislation_graph()
        logger.info(f"LegislationGraphAgent initialized (max_retries={max_retries})")
    
    async def run(
        self,
        question: str,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> LegislationAgentState:
        """
        Agent 실행 (트리 형태 트레이스 지원).
        
        Root span을 생성하고 모든 노드가 이 span의 하위에 연결됨.
        
        Args:
            question: 사용자의 자연어 질문
            session_id: 세션 ID
            trace_id: 상위 레이어의 trace_id
            
        Returns:
            최종 LegislationAgentState
        """
        # 초기 state 생성
        initial_state = create_initial_state(
            question=question,
            session_id=session_id,
            trace_id=trace_id,
            max_retries=self.max_retries
        )
        
        logger.info(f"Running Legislation agent: question='{question[:50]}...', session_id={session_id}")
        
        # Root span 생성하고 그 안에서 그래프 실행
        try:
            from .metrics import _get_tracer
            tracer = _get_tracer()
            
            # Agent ID와 Name 설정 (모니터링을 위해 필수)
            attrs = {
                "service.name": "agent-legislation",
                "component": "legislation",
                "span.kind": "server",
                "question_length": len(question),
                "session_id": session_id or "unknown"
            }
            
            # agent.id와 agent.name 추가 (모니터링 쿼리에서 사용)
            if agent_id:
                attrs["agent.id"] = agent_id
            else:
                attrs["agent.id"] = "legislation-agent"  # 기본값
                
            if agent_name:
                attrs["agent.name"] = agent_name
            else:
                attrs["agent.name"] = "Legislation Agent"  # 기본값
            
            # GenAI 표준 속성 추가 (모니터링 화면에서 인식)
            attrs["gen_ai.agent.id"] = attrs["agent.id"]
            attrs["gen_ai.agent.name"] = attrs["agent.name"]
            attrs["gen_ai.agent.type"] = "legislation"
            
            with tracer.start_as_current_span(
                "gen_ai.session",  # GenAI 표준: root agent session
                attributes=attrs
            ) as root_span:
                # External trace_id가 있으면 속성으로 저장
                if trace_id:
                    root_span.set_attribute("app.external_trace_id", trace_id)
                
                # Root span context를 state에 저장 (각 노드가 child로 연결)
                carrier = {}
                inject_context_to_carrier(carrier)
                initial_state["otel_carrier"] = carrier
                
                # 그래프 실행
                final_state = await self.graph.ainvoke(initial_state)
                
                # 결과 속성 추가
                root_span.set_attribute("has_answer", bool(final_state.get("final_answer")))
                root_span.set_attribute("verification_passed", final_state.get("verification_passed", False))
                root_span.set_attribute("tool_calls_count", len(final_state.get("tool_calls", [])))
                root_span.set_attribute("total_tokens", final_state.get("total_tokens", 0))
                
        except ImportError:
            # OTEL 없으면 그냥 실행
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            logger.warning(f"Root span creation failed, running without tracing: {e}")
            final_state = await self.graph.ainvoke(initial_state)
        
        logger.info(f"Legislation agent completed: answer_length={len(final_state.get('final_answer', ''))}")
        
        return final_state
    
    async def run_stream(
        self,
        question: str,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ):
        """
        Agent 실행 (스트리밍).
        
        각 노드 실행 후 중간 상태를 yield.
        
        Args:
            question: 사용자의 자연어 질문
            session_id: 세션 ID
            trace_id: 상위 레이어의 trace_id
            
        Yields:
            (node_name, state) 튜플
        """
        initial_state = create_initial_state(
            question=question,
            session_id=session_id,
            trace_id=trace_id,
            max_retries=self.max_retries
        )
        
        logger.info(f"Running Legislation agent (streaming): question='{question[:50]}...'")
        
        # Root span 생성하고 그 안에서 그래프 실행
        try:
            from .metrics import _get_tracer, inject_context_to_carrier
            tracer = _get_tracer()
            
            # Agent ID와 Name 설정 (모니터링을 위해 필수)
            attrs = {
                "service.name": "agent-legislation",
                "component": "legislation",
                "span.kind": "server",
                "question_length": len(question),
                "session_id": session_id or "unknown"
            }
            
            # agent.id와 agent.name 추가 (모니터링 쿼리에서 사용)
            if agent_id:
                attrs["agent.id"] = agent_id
            else:
                attrs["agent.id"] = "legislation-agent"  # 기본값
                
            if agent_name:
                attrs["agent.name"] = agent_name
            else:
                attrs["agent.name"] = "Legislation Agent"  # 기본값
            
            # GenAI 표준 속성 추가 (모니터링 화면에서 인식)
            attrs["gen_ai.agent.id"] = attrs["agent.id"]
            attrs["gen_ai.agent.name"] = attrs["agent.name"]
            attrs["gen_ai.agent.type"] = "legislation"
            
            with tracer.start_as_current_span(
                "gen_ai.session",  # GenAI 표준: root agent session
                attributes=attrs
            ) as root_span:
                # External trace_id가 있으면 속성으로 저장
                if trace_id:
                    root_span.set_attribute("app.external_trace_id", trace_id)
                
                # Root span context를 state에 저장 (각 노드가 child로 연결)
                carrier = {}
                inject_context_to_carrier(carrier)
                initial_state["otel_carrier"] = carrier
                
                # LangGraph astream은 {node_name: state_dict} 형태의 딕셔너리 반환
                async for event in self.graph.astream(initial_state):
                    # event는 {node_name: state} 딕셔너리
                    for node_name, state in event.items():
                        logger.debug(f"Node '{node_name}' completed")
                        yield node_name, state
                        
        except ImportError:
            # OTEL 없으면 그냥 실행
            async for event in self.graph.astream(initial_state):
                for node_name, state in event.items():
                    logger.debug(f"Node '{node_name}' completed")
                    yield node_name, state
        except Exception as e:
            logger.warning(f"Root span creation failed, running without tracing: {e}")
            async for event in self.graph.astream(initial_state):
                for node_name, state in event.items():
                    logger.debug(f"Node '{node_name}' completed")
                    yield node_name, state


# Singleton instance
legislation_graph_agent = LegislationGraphAgent()
