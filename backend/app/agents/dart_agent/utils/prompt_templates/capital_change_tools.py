def get_capital_change_tools_description() -> str:
    """
    CapitalChangeAgent에서 사용할 수 있는 도구들의 설명을 반환합니다.
    """
    return """
### 📈 주식 현황 도구 (3개)
- `get_stock_increase_decrease`: 증자/감자 현황 조회
- `get_stock_total`: 주식 총수 현황 조회
- `get_treasury_stock`: 자기주식 현황 조회

### 💼 자기주식 관리 도구 (4개)
- `get_treasury_stock_acquisition`: 자기주식 취득 결정 조회
- `get_treasury_stock_disposal`: 자기주식 처분 결정 조회
- `get_treasury_stock_trust_contract`: 자기주식 신탁계약 체결 결정 조회
- `get_treasury_stock_trust_termination`: 자기주식 신탁계약 해지 결정 조회

### 📊 자본 증감 도구 (4개)
- `get_paid_in_capital_increase`: 유상증자 결정 조회
- `get_free_capital_increase`: 무상증자 결정 조회
- `get_paid_free_capital_increase`: 유무상증자 결정 조회
- `get_capital_reduction`: 감자 결정 조회

### 📋 주요 파라미터
- `corp_code`: 기업고유번호 (8자리)
- `bsns_year`: 사업연도 (YYYY 형식)
- `reprt_code`: 보고서코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)
"""
