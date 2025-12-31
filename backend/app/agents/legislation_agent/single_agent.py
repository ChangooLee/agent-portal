"""
Legislation Single Agent - 법률 정보 분석 에이전트

한국 법률 정보를 검색하고 분석하는 에이전트.
mcp-kr-legislation MCP 서버 활용.
"""

import logging
from datetime import datetime

from app.agents.common.base_single_agent import BaseSingleAgent
from app.agents.legislation_agent.metrics import set_active_service

logger = logging.getLogger(__name__)


# 도구 표시명 매핑
TOOL_DISPLAY_NAMES = {
    # 법령 검색 도구
    "search_laws": "법령 검색",
    "search_law_by_name": "법령명으로 검색",
    "get_law_detail": "법령 상세 조회",
    "get_law_articles": "법령 조문 조회",
    "get_law_history": "법령 연혁 조회",
    
    # 판례 검색 도구
    "search_precedents": "판례 검색",
    "get_precedent_detail": "판례 상세 조회",
    
    # 법령해석 도구
    "search_legal_interpretations": "법령해석 검색",
    "get_interpretation_detail": "법령해석 상세 조회",
    
    # 행정규칙 도구
    "search_administrative_rules": "행정규칙 검색",
    
    # 조약 도구
    "search_treaties": "조약 검색",
    
    # 분석 도구
    "analyze_related_laws": "관련 법령 분석",
    "compare_law_versions": "법령 버전 비교",
}


class LegislationSingleAgent(BaseSingleAgent):
    """
    법률 정보 분석 Single Agent
    
    한국 법률 정보를 검색하고 분석합니다.
    mcp-kr-legislation MCP 서버 활용.
    """
    
    MCP_SERVER_NAME = "mcp-kr-legislation"
    SERVICE_NAME = "agent-legislation"
    AGENT_DISPLAY_NAME = "법률 정보 분석 에이전트"
    
    def __init__(self, model: str = "claude-opus-4.5"):
        super().__init__(model)
        set_active_service(self.SERVICE_NAME)
    
    def _get_tool_display_name(self, tool_name: str) -> str:
        """도구 표시명 반환"""
        return TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
    
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        current_date = datetime.now()
        current_date_str = current_date.strftime("%Y년 %m월 %d일")
        
        return f"""당신은 한국 법률 정보 분석 전문가입니다.
사용자의 질문을 분석하고, 제공된 MCP 도구들을 활용하여 정확한 법률 정보를 조회하고 분석합니다.

## 현재 시스템 일자

**오늘 날짜: {current_date_str}**

## 핵심 원칙

1. **정확한 데이터 우선**: 추측하지 말고 반드시 도구를 사용하여 실제 법률 정보를 조회하세요.
2. **최신 법령 확인**: 법률은 자주 개정되므로 현행 법령인지 확인하세요.
3. **조문 정확성**: 법령 조문을 인용할 때는 정확한 조항 번호와 내용을 제시하세요.
4. **관련 법령 안내**: 하나의 법률 질문에도 관련 법령이 여러 개일 수 있음을 고려하세요.

## 주요 워크플로우

### 법령 검색
1. 법령명 검색 (search_law_by_name 또는 search_laws)
2. 법령 상세 조회 (get_law_detail)
3. 조문 조회 (get_law_articles)

### 판례 검색
1. 키워드로 판례 검색 (search_precedents)
2. 판례 상세 조회 (get_precedent_detail)

### 법령 연혁 확인
1. 법령 검색
2. 연혁 조회 (get_law_history)
3. 필요시 버전 비교 (compare_law_versions)

### 관련 법령 분석
1. 특정 주제의 법령 검색
2. 관련 법령 분석 (analyze_related_laws)

## 도구 사용 시 주의사항

- **법령구분**: 헌법, 법률, 대통령령, 총리령, 부령 등
- **시행상태**: 현행, 폐지, 미시행 등 확인 필요
- **검색어**: 정확한 법령명이나 관련 키워드 사용

## 응답 형식

분석 결과는 마크다운 형식으로 제공하세요:

### 1. 요약
핵심 법률 정보를 간결하게 정리

### 2. 관련 법령
- 법령명, 조문번호
- 주요 내용 요약

### 3. 적용 사례 (해당시)
- 관련 판례
- 법령해석 사례

### 4. 주의사항
- 법률 정보의 한계
- 전문가 상담 권고

## 주의사항

- 법률 정보는 참고용이며, 구체적인 법률 문제는 변호사 등 법률 전문가와 상담하세요.
- 법령은 수시로 개정되므로 반드시 최신 법령을 확인하세요.
- 제공된 정보는 일반적인 법률 정보이며, 개별 사안에 대한 법률 조언이 아닙니다."""

