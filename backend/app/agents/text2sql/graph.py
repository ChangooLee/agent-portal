"""
LangGraph StateGraph for Text-to-SQL Agent

참조: docs/plans/DATA_CLOUD_AGENT.md 섹션 5, 7

Plan-and-Execute 패턴 + 짧은 ReAct 루프(sql_repair ↔ sql_executor)

트레이스 구조:
- 단일 TraceId로 모든 노드가 연결됨
- Parent-Child 관계로 트리 형태 트레이스 생성
- LLM 호출도 같은 TraceId 하에 연결
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager

from langgraph.graph import StateGraph, END

from .state import SqlAgentState, create_initial_state
from .nodes import (
    entry_node,
    dialect_resolver,
    schema_selector,
    planner_node,
    sql_generator_node,
    sql_executor_node,
    sql_repair_node,
    answer_formatter_node,
    human_review_node
)
from .metrics import start_agent_span, inject_context_to_carrier

logger = logging.getLogger(__name__)


def route_after_executor(state: SqlAgentState) -> str:
    """
    sql_executor 이후 조건부 라우팅.
    
    - execution_error is None → answer_formatter (성공)
    - retry_count < max_retries → sql_repair (재시도)
    - else → human_review (사람 검토 필요)
    """
    if state.get("execution_error") is None:
        return "answer_formatter"
    elif state.get("retry_count", 0) < state.get("max_retries", 2):
        return "sql_repair"
    else:
        return "human_review"


def build_text2sql_graph() -> StateGraph:
    """
    Text-to-SQL Agent LangGraph 구성.
    
    노드 흐름:
    entry -> dialect_resolver -> schema_selector -> planner 
          -> sql_generator -> sql_executor 
          -> (answer_formatter | sql_repair -> sql_executor | human_review)
          -> END
    
    Returns:
        컴파일된 LangGraph 앱
    """
    # StateGraph 생성
    graph = StateGraph(SqlAgentState)
    
    # ========== 노드 등록 ==========
    graph.add_node("entry", entry_node)
    graph.add_node("dialect_resolver", dialect_resolver)
    graph.add_node("schema_selector", schema_selector)
    graph.add_node("planner", planner_node)
    graph.add_node("sql_generator", sql_generator_node)
    graph.add_node("sql_executor", sql_executor_node)
    graph.add_node("sql_repair", sql_repair_node)
    graph.add_node("answer_formatter", answer_formatter_node)
    graph.add_node("human_review", human_review_node)
    
    # ========== 엣지 연결 ==========
    
    # 시작점 설정
    graph.set_entry_point("entry")
    
    # 직선 경로 엣지
    graph.add_edge("entry", "dialect_resolver")
    graph.add_edge("dialect_resolver", "schema_selector")
    graph.add_edge("schema_selector", "planner")
    graph.add_edge("planner", "sql_generator")
    graph.add_edge("sql_generator", "sql_executor")
    
    # sql_executor 이후 조건부 엣지
    graph.add_conditional_edges(
        "sql_executor",
        route_after_executor,
        {
            "answer_formatter": "answer_formatter",
            "sql_repair": "sql_repair",
            "human_review": "human_review"
        }
    )
    
    # sql_repair는 다시 sql_executor로
    graph.add_edge("sql_repair", "sql_executor")
    
    # 종료 노드
    graph.add_edge("answer_formatter", END)
    graph.add_edge("human_review", END)
    
    logger.info("Text-to-SQL graph built successfully")
    
    return graph.compile()


class Text2SQLAgent:
    """
    Text-to-SQL Agent 래퍼 클래스.
    
    사용 예:
        agent = Text2SQLAgent()
        result = await agent.run(
            question="최근 주문 10건을 보여줘",
            connection_id="conn-123"
        )
    """
    
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.graph = build_text2sql_graph()
        logger.info(f"Text2SQLAgent initialized (max_retries={max_retries})")
    
    async def run(
        self,
        question: str,
        connection_id: str,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> SqlAgentState:
        """
        Agent 실행 (트리 형태 트레이스 지원).
        
        Root span을 생성하고 모든 노드가 이 span의 하위에 연결됨.
        
        Args:
            question: 사용자의 자연어 질문
            connection_id: DB 연결 식별자
            trace_id: 상위 레이어의 trace_id
            
        Returns:
            최종 SqlAgentState
        """
        # 초기 state 생성
        initial_state = create_initial_state(
            question=question,
            connection_id=connection_id,
            trace_id=trace_id,
            max_retries=self.max_retries
        )
        
        logger.info(f"Running Text2SQL agent: question='{question[:50]}...', connection_id={connection_id}")
        
        # Root span 생성하고 그 안에서 그래프 실행
        try:
            from .metrics import _get_tracer
            tracer = _get_tracer()
            
            # Agent ID와 Name 설정 (모니터링을 위해 필수)
            attrs = {
                "service.name": "agent-text2sql",
                "component": "text2sql",
                "span.kind": "server",
                "question_length": len(question),
                "connection_id": connection_id
            }
            
            # agent.id와 agent.name 추가 (모니터링 쿼리에서 사용)
            if agent_id:
                attrs["agent.id"] = agent_id
            else:
                attrs["agent.id"] = "text2sql-agent"  # 기본값
                
            if agent_name:
                attrs["agent.name"] = agent_name
            else:
                attrs["agent.name"] = "Text-to-SQL Agent"  # 기본값
            
            with tracer.start_as_current_span(
                "text2sql.agent",
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
                root_span.set_attribute("sql_generated", bool(final_state.get("chosen_sql")))
                root_span.set_attribute("success", final_state.get("execution_error") is None)
                if final_state.get("dialect"):
                    root_span.set_attribute("dialect", final_state["dialect"])
                
        except ImportError:
            # OTEL 없으면 그냥 실행
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            logger.warning(f"Root span creation failed, running without tracing: {e}")
            final_state = await self.graph.ainvoke(initial_state)
        
        logger.info(f"Text2SQL agent completed: sql={final_state.get('chosen_sql', '')[:50]}...")
        
        return final_state
    
    async def run_stream(
        self,
        question: str,
        connection_id: str,
        trace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None
    ):
        """
        Agent 실행 (스트리밍).
        
        각 노드 실행 후 중간 상태를 yield.
        
        Args:
            question: 사용자의 자연어 질문
            connection_id: DB 연결 식별자
            trace_id: 상위 레이어의 trace_id
            
        Yields:
            (node_name, state) 튜플
        """
        initial_state = create_initial_state(
            question=question,
            connection_id=connection_id,
            trace_id=trace_id,
            max_retries=self.max_retries
        )
        
        logger.info(f"Running Text2SQL agent (streaming): question='{question[:50]}...'")
        
        # LangGraph astream은 {node_name: state_dict} 형태의 딕셔너리 반환
        async for event in self.graph.astream(initial_state):
            # event는 {node_name: state} 딕셔너리
            for node_name, state in event.items():
                logger.debug(f"Node '{node_name}' completed")
                yield node_name, state


# Singleton instance
text2sql_agent = Text2SQLAgent()

