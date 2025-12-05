def get_governance_tools_description() -> str:
    """
    GovernanceAgent에서 사용할 수 있는 도구들의 설명을 반환합니다.
    """
    return """
### 📈 주주구조 분석 도구 (4개)
- `get_major_shareholder`: 최대주주 및 특수관계인 지분 현황
- `get_major_shareholder_changes`: 최대주주 지분 변동 내역
- `get_minority_shareholder`: 소액주주 현황  
- `get_major_holder_changes`: 5% 이상 주주의 지분 변동 내역

### 👥 임원 및 거래 분석 도구 (4개)
- `get_executive_trading`: 임원 및 주요주주의 주식 거래 내역
- `get_executive_info`: 임원 현황
- `get_employee_info`: 직원 현황
- `get_outside_director_status`: 사외이사 현황

### 📋 주요 파라미터
- `corp_code`: 기업고유번호 (8자리)
- `bsns_year`: 사업연도 (YYYY 형식)
- `reprt_code`: 보고서코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)
"""
