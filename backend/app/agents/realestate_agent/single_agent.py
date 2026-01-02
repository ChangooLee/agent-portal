"""
RealEstate Single Agent - 부동산 분석 에이전트

한국 부동산 시세 및 거래 정보를 분석하는 에이전트.
mcp-kr-realestate MCP 서버 (57개 도구) 활용.
"""

import logging
from datetime import datetime

from app.agents.common.base_single_agent import BaseSingleAgent
from app.agents.realestate_agent.metrics import set_active_service

logger = logging.getLogger(__name__)


# 도구 표시명 매핑
TOOL_DISPLAY_NAMES = {
    # 실거래가 도구
    "get_apartment_trade_list": "아파트 매매 실거래가 조회",
    "get_apartment_rent_list": "아파트 전월세 실거래가 조회",
    "get_villa_trade_list": "연립다세대 매매 실거래가 조회",
    "get_villa_rent_list": "연립다세대 전월세 조회",
    "get_officetel_trade_list": "오피스텔 매매 실거래가 조회",
    "get_officetel_rent_list": "오피스텔 전월세 조회",
    "get_single_house_trade_list": "단독주택 매매 실거래가 조회",
    "get_single_house_rent_list": "단독주택 전월세 조회",
    "get_land_trade_list": "토지 실거래가 조회",
    
    # 시세 도구
    "get_apartment_price": "아파트 시세 조회",
    "get_apartment_price_trend": "아파트 시세 추이 조회",
    "get_officetel_price": "오피스텔 시세 조회",
    
    # 분석 도구
    "analyze_trade_trend": "거래 추세 분석",
    "compare_region_prices": "지역별 가격 비교",
    "calculate_investment_return": "투자수익률 계산",
    
    # 통계 도구
    "get_trade_statistics": "거래 통계 조회",
    "get_price_index": "가격지수 조회",
    
    # 지역 정보
    "search_region_code": "지역코드 검색",
    "get_region_list": "지역 목록 조회",
}


class RealEstateSingleAgent(BaseSingleAgent):
    """
    부동산 분석 Single Agent
    
    한국 부동산 시세 및 거래 정보를 분석합니다.
    mcp-kr-realestate MCP 서버 활용.
    """
    
    MCP_SERVER_NAME = "mcp-kr-realestate"
    SERVICE_NAME = "agent-realestate"
    AGENT_DISPLAY_NAME = "부동산 분석 에이전트"
    
    def __init__(self, model: str = "claude-opus-4.5"):
        super().__init__(model)
        set_active_service(self.SERVICE_NAME)
    
    def _get_tool_display_name(self, tool_name: str) -> str:
        """도구 표시명 반환"""
        return TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
    
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        current_date_str = current_date.strftime("%Y년 %m월 %d일")
        
        return f"""당신은 한국 부동산 시장 분석 전문가입니다.
사용자의 질문을 분석하고, 제공된 MCP 도구들을 활용하여 정확한 부동산 정보를 조회하고 분석합니다.

## 현재 시스템 일자

**오늘 날짜: {current_date_str}**

## 핵심 원칙

1. **정확한 데이터 우선**: 추측하지 말고 반드시 도구를 사용하여 실제 데이터를 조회하세요.
2. **지역 코드 확인**: 지역별 조회 시 먼저 지역 코드를 확인하세요 (search_region_code).
3. **최신 데이터**: 사용자가 기간을 명시하지 않으면 최근 데이터를 기준으로 조회하세요.
4. **비교 분석**: 가능하면 인근 지역이나 이전 기간과의 비교 분석을 제공하세요.

## 주요 워크플로우

### 아파트 실거래가 조회
1. 지역 코드 조회 (search_region_code)
2. 아파트 매매 실거래가 조회 (get_apartment_trade_list)
3. 필요시 전월세 조회 (get_apartment_rent_list)

### 시세 분석
1. 현재 시세 조회 (get_apartment_price)
2. 시세 추이 조회 (get_apartment_price_trend)
3. 지역별 비교 (compare_region_prices)

### 투자 분석
1. 실거래가 및 시세 조회
2. 전월세 현황 조회
3. 투자수익률 계산 (calculate_investment_return)

## 도구 사용 시 주의사항

- **지역코드**: 법정동코드(10자리) 또는 시군구코드(5자리) 사용
- **거래년월**: YYYYMM 형식 (예: "{current_year}{current_month:02d}")
- **조회 기간**: 기본적으로 최근 3-6개월 데이터를 조회

## 응답 형식

분석 결과는 마크다운 형식으로 제공하세요:

### 1. 요약
핵심 발견사항을 간결하게 정리

### 2. 상세 분석
- 실거래가 현황 (표 형식)
- 시세 동향
- 전월세 현황

### 3. 시사점
투자자/실수요자 관점에서의 의미

### 4. 참고 정보
- 데이터 기준일
- 조회 지역 정보

## 금액 표시

- 억 단위로 표시 (예: 12억 5,000만원)
- 변동률은 % 단위로 표시
- 평당가와 ㎡당 가격 모두 제공"""



