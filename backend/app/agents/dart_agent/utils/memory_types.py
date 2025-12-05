"""
memory_types.py
DART 멀티에이전트 시스템의 메모리 관리를 위한 데이터 구조 정의
"""

from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from datetime import datetime
from enum import Enum


# =============================================================================
# 🧠 메모리 관리용 열거형
# =============================================================================

class MemoryType(Enum):
    """메모리 타입"""
    CONVERSATION = "conversation"
    ANALYSIS_RESULT = "analysis_result"
    USER_PREFERENCE = "user_preference"
    CONTEXT_MEMORY = "context_memory"
    TOKEN_USAGE = "token_usage"


class MessagePriority(Enum):
    """메시지 중요도"""
    CRITICAL = 1.0      # 도구 호출/결과
    HIGH = 0.8          # 분석 관련 메시지
    MEDIUM = 0.5        # 일반 메시지
    LOW = 0.2           # 부가 정보


# =============================================================================
# 🧠 메모리 관리용 State 구조
# =============================================================================

class MemoryState(TypedDict):
    """메모리 관리를 위한 확장된 State"""
    # 기본 메시지
    messages: List[BaseMessage]
    
    # 메모리 관리
    conversation_summary: Optional[str]  # 대화 요약
    analysis_cache: Dict[str, Any]  # 분석 결과 캐시
    user_preferences: Dict[str, Any]  # 사용자 선호도
    context_memory: Dict[str, Any]  # 컨텍스트 메모리
    
    # 토큰 관리
    token_usage: Dict[str, int]  # 에이전트별 토큰 사용량
    context_priority: Dict[str, float]  # 컨텍스트 중요도
    
    # 메타데이터
    thread_id: str
    session_id: str
    last_updated: datetime
    memory_version: int


class DartAnalysisState(MemoryState):
    """DART 분석을 위한 특화된 State"""
    # 기존 AnalysisContext 필드들
    corp_code: str
    corp_name: str
    user_question: str
    scope: str
    domain: str
    depth: str
    
    # 분석 결과
    agent_results: List[Dict[str, Any]]
    integrated_analysis: Optional[str]
    
    # 메모리 관리
    previous_analyses: List[Dict[str, Any]]  # 이전 분석 결과들
    company_metadata: Dict[str, Any]  # 기업별 메타데이터
    analysis_patterns: Dict[str, Any]  # 분석 패턴


# =============================================================================
# 🧠 메모리 관리용 데이터 클래스
# =============================================================================

class MemoryEntry:
    """메모리 엔트리"""
    def __init__(self, key: str, value: Any, memory_type: MemoryType, 
                 priority: float = 0.5, created_at: datetime = None):
        self.key = key
        self.value = value
        self.memory_type = memory_type
        self.priority = priority
        self.created_at = created_at or datetime.now()
        self.last_accessed = datetime.now()
        self.access_count = 0
    
    def access(self):
        """메모리 접근 기록"""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "key": self.key,
            "value": self.value,
            "memory_type": self.memory_type.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count
        }


class TokenUsage:
    """토큰 사용량 추적"""
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.total_tokens = 0
        self.message_tokens = 0
        self.tool_tokens = 0
        self.response_tokens = 0
        self.last_updated = datetime.now()
    
    def add_usage(self, message_tokens: int = 0, tool_tokens: int = 0, 
                  response_tokens: int = 0):
        """토큰 사용량 추가"""
        self.message_tokens += message_tokens
        self.tool_tokens += tool_tokens
        self.response_tokens += response_tokens
        self.total_tokens = self.message_tokens + self.tool_tokens + self.response_tokens
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "agent_type": self.agent_type,
            "total_tokens": self.total_tokens,
            "message_tokens": self.message_tokens,
            "tool_tokens": self.tool_tokens,
            "response_tokens": self.response_tokens,
            "last_updated": self.last_updated.isoformat()
        }


class AnalysisCache:
    """분석 결과 캐시"""
    def __init__(self, corp_code: str, analysis_type: str):
        self.corp_code = corp_code
        self.analysis_type = analysis_type
        self.results = {}
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.hit_count = 0
    
    def get(self, key: str) -> Any:
        """캐시에서 값 조회"""
        self.last_accessed = datetime.now()
        if key in self.results:
            self.hit_count += 1
            return self.results[key]
        return None
    
    def set(self, key: str, value: Any):
        """캐시에 값 저장"""
        self.results[key] = value
        self.last_accessed = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "corp_code": self.corp_code,
            "analysis_type": self.analysis_type,
            "results": self.results,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "hit_count": self.hit_count
        }


# =============================================================================
# 🧠 메모리 관리 설정
# =============================================================================

class MemoryConfig:
    """메모리 관리 설정"""
    
    # 에이전트별 토큰 제한
    TOKEN_LIMITS = {
        "master": 10000,      # 마스터 에이전트
        "financial": 15000,   # 재무 분석
        "governance": 10000,  # 지배구조 분석
        "document": 20000,    # 문서 분석 (가장 많은 토큰 필요)
        "capital_change": 8000,
        "debt_funding": 8000,
        "business_structure": 8000,
        "overseas_business": 8000,
        "legal_risk": 8000,
        "executive_audit": 8000,
        "others": 8000        # 기타 에이전트들
    }
    
    # 메모리 정리 설정
    MAX_CACHE_SIZE = 1000     # 최대 캐시 크기
    MAX_ANALYSIS_HISTORY = 50  # 최대 분석 히스토리
    CACHE_TTL_HOURS = 24      # 캐시 TTL (시간)
    
    # 토큰 관리 설정
    MAX_TOTAL_TOKENS = 65000  # 전체 최대 토큰
    TOKEN_BUFFER = 5000       # 토큰 버퍼
    
    @classmethod
    def get_token_limit(cls, agent_type: str) -> int:
        """에이전트 타입별 토큰 제한 조회"""
        return cls.TOKEN_LIMITS.get(agent_type.lower(), cls.TOKEN_LIMITS["others"])
    
    @classmethod
    def is_token_within_limit(cls, agent_type: str, current_tokens: int) -> bool:
        """토큰 사용량이 제한 내에 있는지 확인"""
        limit = cls.get_token_limit(agent_type)
        return current_tokens <= limit