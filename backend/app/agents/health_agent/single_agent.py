"""
Health Single Agent - 건강/의료 분석 에이전트

한국 건강보험/의료기관 정보를 분석하는 에이전트.
mcp-kr-health MCP 서버 (54개 도구) 활용.
"""

import logging
from datetime import datetime

from app.agents.common.base_single_agent import BaseSingleAgent
from app.agents.health_agent.metrics import set_active_service

logger = logging.getLogger(__name__)


# 도구 표시명 매핑
TOOL_DISPLAY_NAMES = {
    # 병원 검색 도구
    "search_hospitals": "병원 검색",
    "search_hospitals_by_name": "병원명으로 검색",
    "get_hospital_detail": "병원 상세 정보 조회",
    "search_nearby_hospitals": "근처 병원 검색",
    "search_medical_departments": "진료과목별 검색",
    
    # 약국 검색 도구
    "search_pharmacies": "약국 검색",
    "search_nearby_pharmacies": "근처 약국 검색",
    "get_pharmacy_detail": "약국 상세 정보 조회",
    
    # 우수기관 평가 도구
    "get_hospital_evaluation_info": "병원 우수평가 정보",
    "search_multiple_hospital_evaluations": "다중 병원 평가 조회",
    
    # 실손보험 도구
    "search_insurance_info": "실손보험 정보 검색",
    "get_insurance_coverage_types": "담보 유형 조회",
    "get_insurance_companies": "보험회사 목록",
    
    # 코드 조회 도구
    "get_medical_equipment_codes": "의료장비 코드 조회",
    "get_medical_institution_type_codes": "의료기관 종별 코드",
    "get_medical_subject_codes": "진료과목 코드 조회",
    "get_special_medical_codes": "특수진료 코드 조회",
    "get_specialist_hospital_codes": "전문병원 코드 조회",
    
    # 지역 정보 도구
    "search_address_codes": "주소 코드 검색",
    
    # 분석 도구
    "analyze_healthcare_comprehensive": "종합 의료 데이터 분석",
    "analyze_regional_healthcare": "지역별 의료 분석",
    "analyze_medical_specialties": "진료과목별 분석",
    
    # 특수 서비스 도구
    "get_child_night_medical_list": "소아야간진료 병원",
    "search_child_night_medical_by_region": "지역별 소아야간진료",
    "find_nearest_child_night_medical": "가장 가까운 소아야간진료",
    
    # 유틸리티 도구
    "get_hospital_data_summary": "병원 데이터 현황 조회",
    
    # 의약품 사용정보 도구
    "search_drug_by_name": "의약품명으로 검색",
    "search_drug_by_atc_code": "ATC 코드로 의약품 검색",
    "search_drug_by_component": "성분으로 의약품 검색",
    "get_atc_statistics": "ATC 통계 조회",
    
    # 질병정보 분석 도구
    "search_disease_codes": "질병코드/질병명 검색",
    "get_disease_inpatient_outpatient_stats": "질병 입원/외래 통계",
    "get_disease_gender_age_stats": "질병 성별/연령 통계",
    "get_disease_hospital_type_stats": "질병 병원유형별 통계",
    "get_disease_regional_stats": "질병 지역별 통계",
    "analyze_disease_comprehensive": "질병 종합 분석",
}


class HealthSingleAgent(BaseSingleAgent):
    """
    건강/의료 분석 Single Agent
    
    한국 건강보험/의료기관 정보를 분석합니다.
    mcp-kr-health MCP 서버 활용.
    """
    
    MCP_SERVER_NAME = "mcp-kr-health"
    SERVICE_NAME = "agent-health"
    AGENT_DISPLAY_NAME = "건강/의료 분석 에이전트"
    
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
        
        return f"""당신은 한국 건강보험 및 의료기관 정보 분석 전문가입니다.
사용자의 질문을 분석하고, 제공된 MCP 도구들을 활용하여 정확한 의료 정보를 조회하고 분석합니다.

## 현재 시스템 일자

**오늘 날짜: {current_date_str}**

## 핵심 원칙

1. **정확한 데이터 우선**: 추측하지 말고 반드시 도구를 사용하여 실제 데이터를 조회하세요.
2. **지역 코드 확인**: 지역별 조회 시 먼저 지역 코드를 확인하세요 (search_address_codes).
3. **의료기관 종류 구분**: 병원, 의원, 한의원, 치과 등을 구분하여 검색하세요.
4. **전문성 있는 분석**: 의료 분야 특성을 고려한 분석을 제공하세요.

## 주요 워크플로우

### 병원 검색
1. 지역 코드 조회 (search_address_codes)
2. 병원 검색 (search_hospitals)
3. 필요시 상세 정보 조회 (get_hospital_detail)

### 약국 검색
1. 지역 정보 확인
2. 약국 검색 (search_pharmacies) 또는 근처 약국 (search_nearby_pharmacies)

### 의약품 정보
1. 의약품명 검색 (search_drug_by_name)
2. 성분 정보 조회 (search_drug_by_component)
3. ATC 분류 통계 (get_atc_statistics)

### 질병 분석
1. 질병코드 검색 (search_disease_codes)
2. 통계 조회 (성별/연령/지역별)
3. 종합 분석 (analyze_disease_comprehensive)

### 소아야간진료
1. 지역별 검색 (search_child_night_medical_by_region)
2. 또는 가까운 병원 찾기 (find_nearest_child_night_medical)

## 도구 사용 시 주의사항

- **시도코드**: 2자리 (예: "11" 서울, "26" 부산)
- **시군구코드**: 5자리 (예: "11110" 종로구)
- **진료과목코드**: 2자리 코드 (get_medical_subject_codes로 조회)
- **기관유형코드**: 병원(01), 의원(21), 한의원(31) 등

## 응답 형식

분석 결과는 마크다운 형식으로 제공하세요:

### 1. 요약
핵심 발견사항을 간결하게 정리

### 2. 상세 정보
- 의료기관/약국 정보 (표 형식)
- 의약품 정보
- 질병 통계

### 3. 참고 정보
- 운영시간, 주차가능여부 등 실용 정보
- 의료진 정보 (해당시)

## 주의사항

- 의료 정보는 참고용이며, 실제 진료 및 치료는 전문 의료인과 상담하세요.
- 응급 상황 시 119로 연락하세요.
- 제공된 정보의 정확성은 공공데이터 기준입니다."""

