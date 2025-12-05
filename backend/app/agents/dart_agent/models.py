"""
DART 에이전트 공통 모델 정의
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AnalysisContext:
    """분석 컨텍스트 정보"""

    user_question: str
    corporation_name: Optional[str] = None
    corporation_code: Optional[str] = None
    analysis_type: Optional[str] = None
    thread_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ToolExecutionResult:
    """도구 실행 결과"""

    tool_name: str
    parameters: Dict[str, Any]
    result: Any
    success: bool
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: Optional[datetime] = None


@dataclass
class AgentResult:
    """에이전트 분석 결과"""

    agent_name: str
    analysis_type: str
    success: bool
    data: Dict[str, Any]
    tools_used: List[str]
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MultiAgentResult:
    """멀티에이전트 시스템 전체 결과"""

    question: str
    agents_involved: List[str]
    tools_used: List[str]
    results: Dict[str, AgentResult]
    overall_analysis: str
    success: bool
    execution_time: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CorporationInfo:
    """기업 기본 정보"""

    name: str
    code: str
    representative: Optional[str] = None
    industry: Optional[str] = None
    listing_status: Optional[str] = None
    establishment_date: Optional[str] = None
    fiscal_year_end: Optional[str] = None
    auditor: Optional[str] = None


@dataclass
class FinancialData:
    """재무 데이터"""

    period: str
    account_name: str
    value: Union[int, float, str]
    unit: Optional[str] = None
    change_rate: Optional[float] = None
    previous_value: Optional[Union[int, float, str]] = None


@dataclass
class DisclosureInfo:
    """공시 정보"""

    rcept_no: str
    corp_name: str
    stock_code: str
    report_nm: str
    rcept_dt: str
    rcept_person: str
    url: Optional[str] = None
    content: Optional[str] = None


@dataclass
class ShareholderInfo:
    """주주 정보"""

    name: str
    shares: int
    percentage: float
    change: Optional[int] = None
    change_percentage: Optional[float] = None
    category: Optional[str] = None  # 'major', 'executive', 'other'


@dataclass
class ExecutiveInfo:
    """임원 정보"""

    name: str
    position: str
    shares: Optional[int] = None
    percentage: Optional[float] = None
    appointment_date: Optional[str] = None
    compensation: Optional[int] = None


@dataclass
class AnalysisSummary:
    """분석 요약"""

    key_findings: List[str]
    risk_factors: List[str]
    opportunities: List[str]
    recommendations: List[str]
    confidence_level: float  # 0.0 ~ 1.0
    data_quality: str  # 'high', 'medium', 'low'
    limitations: List[str]
