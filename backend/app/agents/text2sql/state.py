"""
SqlAgentState - Text-to-SQL Agent State Definition

참조: docs/plans/DATA_CLOUD_AGENT.md 섹션 3. State 설계

LangGraph StateGraph의 state로 사용되는 TypedDict.
Plan-and-Execute 패턴에 필요한 모든 필드를 정의.
"""

from typing import TypedDict, List, Optional, Literal, Dict, Any


# Supported SQL dialects
Dialect = Literal[
    "postgres",
    "mysql", 
    "mariadb",
    "oracle",
    "clickhouse",
    "hana",
    "databricks",
    "generic"
]


class SqlAgentState(TypedDict):
    """
    Text-to-SQL Agent의 전체 상태.
    
    LangGraph StateGraph에서 노드 간 데이터 전달에 사용.
    각 노드는 이 State를 입력/출력으로 사용.
    """
    
    # ========== 입력 필드 ==========
    
    # 사용자의 자연어 질문 (한국어/영어 혼합 가능)
    question: str
    
    # Data Cloud에서 사용하는 DB 연결 식별자
    connection_id: str
    
    # ========== Dialect 관련 ==========
    
    # dialect_resolver 노드에서 채우는 값
    # SQLAlchemy engine.dialect.name 기반으로 매핑
    dialect: Optional[Dialect]
    
    # dialect에 따른 SQL 규칙 문자열 (프롬프트에 포함)
    dialect_rules: Optional[str]
    
    # ========== 스키마 관련 ==========
    
    # Planner/Generator에게 넘겨줄 스키마 요약 문자열
    # (테이블 목록, 컬럼, PK/FK, 코멘트, 샘플 컬럼 등)
    schema_summary: Optional[str]
    
    # (선택) 테이블/관계 정보를 JSON 그래프 형태로 보존
    # {"tables": [...], "relations": [...]} 구조
    schema_graph: Optional[Dict[str, Any]]
    
    # ========== Plan (Planner 출력) ==========
    
    # Planner LLM이 만든 JSON 플랜
    # 예: {"tables": [...], "joins": [...], "filters": [...], 
    #      "aggregations": [...], "group_by": [...], "order_by": [...], "limit": 100}
    plan: Optional[Dict[str, Any]]
    
    # ========== SQL 생성 관련 ==========
    
    # SqlGenerator가 쌓아가는 SQL 후보 리스트
    candidate_sql: List[str]
    
    # 최종적으로 채택된 SQL
    chosen_sql: Optional[str]
    
    # SQL 생성 시 LLM의 reasoning 텍스트 (디버깅용)
    sql_reasoning: Optional[str]
    
    # ========== 실행 결과 ==========
    
    # (선택) 실행 후 결과
    # 최소한 row_count 정도만 저장, 실제 데이터는 상위 서비스에서 관리
    execution_result: Optional[List[Dict[str, Any]]]
    
    # SQL 실행 중 마지막 에러 메시지 (있다면)
    execution_error: Optional[str]
    
    # ========== 재시도 관련 ==========
    
    # SQL 수정 재시도 횟수
    retry_count: int
    
    # 설정값 (예: 1 또는 2)
    max_retries: int
    
    # ========== Human-in-the-loop ==========
    
    # Human-in-the-loop 단계로 보내야 하는지 여부
    needs_human_review: bool
    
    # Human review가 필요한 이유
    human_review_reason: Optional[str]
    
    # ========== 최종 출력 ==========
    
    # 결과를 바탕으로 만든 자연어 요약
    answer_summary: Optional[str]
    
    # ========== OTEL 관련 (관측성) ==========
    
    # 상위 HTTP/API 레이어에서 들어온 trace_id
    # OTEL tracer와 연동할 때 span attribute로 같이 사용
    trace_id: Optional[str]
    
    # metrics 공통 태그
    # 예: {"service": "agent-portal", "component": "text2sql", "dialect": "postgres"}
    metrics_tags: Optional[Dict[str, str]]
    
    # 그래프 실행 시작 시간 (latency 측정용)
    start_time: Optional[float]
    
    # OTEL Context (span간 parent-child 연결용)
    # 직렬화된 trace context 정보
    otel_carrier: Optional[Dict[str, str]]
    
    # Entry 노드의 context (다른 모든 노드가 entry의 child가 되도록)
    entry_carrier: Optional[Dict[str, str]]
    
    # ========== 토큰 및 비용 추적 ==========
    
    # 사용된 LLM 모델명
    llm_model: Optional[str]
    
    # 누적 토큰 사용량
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int


def create_initial_state(
    question: str,
    connection_id: str,
    trace_id: Optional[str] = None,
    max_retries: int = 2
) -> SqlAgentState:
    """
    초기 State 생성 헬퍼 함수.
    
    Args:
        question: 사용자의 자연어 질문
        connection_id: DB 연결 식별자
        trace_id: 상위 레이어에서 전달된 trace_id
        max_retries: SQL 수정 최대 재시도 횟수
        
    Returns:
        초기화된 SqlAgentState
    """
    import time
    
    return SqlAgentState(
        # 입력
        question=question,
        connection_id=connection_id,
        
        # Dialect
        dialect=None,
        dialect_rules=None,
        
        # 스키마
        schema_summary=None,
        schema_graph=None,
        
        # Plan
        plan=None,
        
        # SQL
        candidate_sql=[],
        chosen_sql=None,
        sql_reasoning=None,
        
        # 실행
        execution_result=None,
        execution_error=None,
        
        # 재시도
        retry_count=0,
        max_retries=max_retries,
        
        # Human review
        needs_human_review=False,
        human_review_reason=None,
        
        # 출력
        answer_summary=None,
        
        # OTEL
        trace_id=trace_id,
        metrics_tags={
            "service": "agent-portal",
            "component": "text2sql",
            "phase": "entry"
        },
        start_time=time.time(),
        otel_carrier=None,  # graph.py에서 root span 생성 시 설정
        entry_carrier=None,  # entry_node에서 설정, 다른 노드들의 parent로 사용
        
        # 토큰 추적
        llm_model=None,
        total_prompt_tokens=0,
        total_completion_tokens=0,
        total_tokens=0
    )

