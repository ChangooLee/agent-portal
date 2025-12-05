"""
dart_types.py
DART 멀티에이전트 시스템의 공통 데이터 구조 정의
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


# =============================================================================
# 🎯 분석 분류 열거형
# =============================================================================


class AnalysisScope(Enum):
    """분석 범위"""

    SINGLE_COMPANY = "single_company"
    MULTI_COMPANY = "multi_company"
    INDUSTRY_ANALYSIS = "industry_analysis"
    COMPREHENSIVE_RISK = "comprehensive_risk"


class AnalysisDomain(Enum):
    """분석 영역"""

    FINANCIAL = "financial"
    GOVERNANCE = "governance"
    BUSINESS = "business"
    BUSINESS_STRUCTURE = "business_structure"
    CAPITAL_CHANGE = "capital_change"
    DEBT_FUNDING = "debt_funding"
    OVERSEAS_BUSINESS = "overseas_business"
    LEGAL_RISK = "legal_risk"
    EXECUTIVE_AUDIT = "executive_audit"
    DOCUMENT_ANALYSIS = "document_analysis"
    MIXED = "mixed"


class AnalysisDepth(Enum):
    """분석 깊이"""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class RiskLevel(Enum):
    """리스크 수준"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# 📊 데이터 구조 클래스
# =============================================================================


@dataclass
class AnalysisContext:
    """분석 컨텍스트 - 에이전트 간 공유되는 기본 정보"""

    corp_code: str
    corp_name: str
    user_question: str
    scope: AnalysisScope
    domain: AnalysisDomain
    depth: AnalysisDepth
    thread_id: str = ""
    intent_reasoning: str = ""
    analysis_reasoning: str = ""
    additional_reasoning: str = ""
    collected_data: Dict[str, Any] = None
    risk_indicators: List[str] = None
    cross_references: Dict[str, Any] = None

    def __post_init__(self):
        if self.collected_data is None:
            self.collected_data = {}
        if self.risk_indicators is None:
            self.risk_indicators = []
        if self.cross_references is None:
            self.cross_references = {}


@dataclass
class AgentResult:
    """에이전트 분석 결과 표준 구조"""

    agent_name: str
    analysis_type: str
    risk_level: RiskLevel
    key_findings: List[str]
    supporting_data: Dict[str, Any]
    recommendations: List[str]
    execution_time: float
    tools_used: List[str]
    created_at: datetime = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class IntentClassificationResult:
    """의도 분류 결과"""

    scope: AnalysisScope
    domain: AnalysisDomain
    depth: AnalysisDepth
    required_agents: List[str] = None  # 기존 호환성
    recommended_agents: List[str] = None  # 새로운 필드
    reasoning: str = ""
    verification_message: Optional[str] = None  # 기업 정보 확인 메시지
    corp_info: Optional[Dict[str, Any]] = None  # 기업 정보 (IntentClassifierAgent가 식별한 결과)
    # 동적 분석 깊이 관련 필드
    needs_deep_analysis: bool = False  # 깊은 분석이 필요한지 여부
    analysis_reasoning: str = ""  # 분석 깊이 판단 근거
    recent_disclosures: List[Dict[str, Any]] = None  # 최근 공시 정보

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "scope": (self.scope.value if hasattr(self.scope, "value") else str(self.scope)),
            "domain": (self.domain.value if hasattr(self.domain, "value") else str(self.domain)),
            "depth": (self.depth.value if hasattr(self.depth, "value") else str(self.depth)),
            "required_agents": self.required_agents or [],
            "recommended_agents": self.recommended_agents or [],
            "reasoning": self.reasoning,
            "verification_message": self.verification_message,
            "corp_info": self.corp_info or {},
            "needs_deep_analysis": self.needs_deep_analysis,
            "analysis_reasoning": self.analysis_reasoning,
            "recent_disclosures": self.recent_disclosures or [],
        }


@dataclass
class ToolExecutionResult:
    """도구 실행 결과"""

    tool_name: str
    success: bool
    result: Any
    error_message: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0


# =============================================================================
# 🔧 유틸리티 함수
# =============================================================================


def create_analysis_context(
    corp_code: str,
    corp_name: str,
    user_question: str,
    classification: IntentClassificationResult,
    thread_id: str = "",
) -> AnalysisContext:
    """분석 컨텍스트 생성 헬퍼 함수"""
    return AnalysisContext(
        corp_code=corp_code,
        corp_name=corp_name,
        user_question=user_question,
        scope=classification.scope,
        domain=classification.domain,
        depth=classification.depth,
        thread_id=thread_id,
        intent_reasoning=classification.reasoning,
        analysis_reasoning=classification.analysis_reasoning,
    )


def merge_agent_results(results: List[AgentResult]) -> Dict[str, Any]:
    """여러 에이전트 결과를 통합"""
    merged = {
        "overall_risk_level": RiskLevel.LOW,
        "key_findings": [],
        "recommendations": [],
        "supporting_data": {},
        "agents_involved": [],
        "total_tools_used": [],
        "average_confidence": 0.0,
    }

    if not results:
        return merged

    # 최고 리스크 수준 결정
    risk_levels = [result.risk_level for result in results]
    if RiskLevel.CRITICAL in risk_levels:
        merged["overall_risk_level"] = RiskLevel.CRITICAL
    elif RiskLevel.HIGH in risk_levels:
        merged["overall_risk_level"] = RiskLevel.HIGH
    elif RiskLevel.MEDIUM in risk_levels:
        merged["overall_risk_level"] = RiskLevel.MEDIUM

    # 결과 통합
    for result in results:
        merged["key_findings"].extend(result.key_findings)
        merged["recommendations"].extend(result.recommendations)
        merged["supporting_data"][result.agent_name] = result.supporting_data
        merged["agents_involved"].append(result.agent_name)
        merged["total_tools_used"].extend(result.tools_used)

    return merged
