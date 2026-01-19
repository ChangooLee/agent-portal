"""
LegislationAgentState - 법률 에이전트 State 정의

LangGraph StateGraph의 state로 사용되는 TypedDict.
계층적 작업 분해에 필요한 모든 필드를 정의.
"""

from typing import TypedDict, List, Optional, Dict, Any, Literal


# 작업 타입
TaskType = Literal[
    "search_laws",      # 법령 검색
    "get_details",      # 상세 정보 조회
    "search_precedents", # 판례 검색
    "analyze_related",   # 관련 법령 분석
    "compare_versions"   # 법령 버전 비교
]


class LegislationAgentState(TypedDict):
    """
    법률 에이전트의 전체 상태.
    
    LangGraph StateGraph에서 노드 간 데이터 전달에 사용.
    """
    
    # ========== 입력 필드 ==========
    
    # 사용자의 자연어 질문
    question: str
    
    # 세션 ID
    session_id: Optional[str]
    
    # ========== 계획 관련 ==========
    
    # Planner가 생성한 작업 계획
    plan: Optional[Dict[str, Any]]
    
    # 필요한 작업 타입 목록
    required_tasks: List[TaskType]
    
    # ========== 법령 검색 결과 ==========
    
    # 검색된 법령 목록
    law_search_results: List[Dict[str, Any]]
    
    # 선택된 법령 ID/이름
    selected_law_id: Optional[str]
    selected_law_name: Optional[str]
    
    # ========== 상세 정보 ==========
    
    # 법령 상세 정보
    law_detail: Optional[Dict[str, Any]]
    
    # 법령 조문 목록
    law_articles: List[Dict[str, Any]]
    
    # 법령 연혁
    law_history: Optional[Dict[str, Any]]
    
    # ========== 판례 정보 ==========
    
    # 검색된 판례 목록
    precedent_results: List[Dict[str, Any]]
    
    # 선택된 판례 상세 정보
    precedent_detail: Optional[Dict[str, Any]]
    
    # ========== 분석 결과 ==========
    
    # LLM이 생성한 분석 결과
    analysis_result: Optional[str]
    
    # 분석에 사용된 근거 (법령, 판례 등)
    analysis_evidence: List[Dict[str, Any]]
    
    # ========== 검증 관련 ==========
    
    # 검증 결과
    verification_result: Optional[Dict[str, Any]]
    
    # 검증 실패 시 재시도 횟수
    retry_count: int
    
    # 최대 재시도 횟수
    max_retries: int
    
    # 검증 통과 여부
    verification_passed: bool
    
    # ========== 최종 출력 ==========
    
    # 최종 응답
    final_answer: Optional[str]
    
    # 사용된 도구 목록
    tool_calls: List[Dict[str, Any]]
    
    # ========== OTEL 관련 ==========
    
    # 상위 HTTP/API 레이어에서 들어온 trace_id
    trace_id: Optional[str]
    
    # OTEL Context (span간 parent-child 연결용)
    otel_carrier: Optional[Dict[str, str]]
    
    # Entry 노드의 context
    entry_carrier: Optional[Dict[str, str]]
    
    # ========== 토큰 및 비용 추적 ==========
    
    # 사용된 LLM 모델명
    llm_model: Optional[str]
    
    # 누적 토큰 사용량
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    
    # ========== 실행 시간 ==========
    
    # 그래프 실행 시작 시간
    start_time: Optional[float]


def create_initial_state(
    question: str,
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    max_retries: int = 2
) -> LegislationAgentState:
    """
    초기 State 생성 헬퍼 함수.
    
    Args:
        question: 사용자의 자연어 질문
        session_id: 세션 ID
        trace_id: 상위 레이어에서 전달된 trace_id
        max_retries: 검증 실패 시 최대 재시도 횟수
        
    Returns:
        초기화된 LegislationAgentState
    """
    import time
    
    return LegislationAgentState(
        # 입력
        question=question,
        session_id=session_id or trace_id,
        
        # 계획
        plan=None,
        required_tasks=[],
        
        # 법령 검색
        law_search_results=[],
        selected_law_id=None,
        selected_law_name=None,
        
        # 상세 정보
        law_detail=None,
        law_articles=[],
        law_history=None,
        
        # 판례
        precedent_results=[],
        precedent_detail=None,
        
        # 분석
        analysis_result=None,
        analysis_evidence=[],
        
        # 검증
        verification_result=None,
        retry_count=0,
        max_retries=max_retries,
        verification_passed=False,
        
        # 출력
        final_answer=None,
        tool_calls=[],
        
        # OTEL
        trace_id=trace_id,
        otel_carrier=None,
        entry_carrier=None,
        
        # 토큰 추적
        llm_model=None,
        total_prompt_tokens=0,
        total_completion_tokens=0,
        total_tokens=0,
        
        # 실행 시간
        start_time=time.time()
    )
