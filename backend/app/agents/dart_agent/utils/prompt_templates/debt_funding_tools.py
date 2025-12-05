def get_debt_funding_tools_description() -> str:
    """
    DebtFundingAgent에서 사용할 수 있는 도구들의 설명을 반환합니다.
    """
    return """
### 💰 채무증권 발행 분석 도구 (6개)
- `get_debt`: 채무증권 발행 및 매출 내역
- `get_debt_securities_issued`: 채무증권 발행 실적
- `get_convertible_bond`: 전환사채 발행 결정
- `get_bond_with_warrant`: 신주인수권부사채 발행 결정
- `get_exchangeable_bond`: 교환사채 발행 결정
- `get_write_down_bond`: 상각형 조건부자본증권 발행 결정

### 📈 미상환 잔액 분석 도구 (5개)
- `get_commercial_paper_outstanding`: 기업어음 미상환 잔액
- `get_short_term_bond_outstanding`: 단기사채 미상환 잔액
- `get_corporate_bond_outstanding`: 회사채 미상환 잔액
- `get_hybrid_securities_outstanding`: 신종자본증권 미상환 잔액
- `get_conditional_capital_securities_outstanding`: 조건부자본증권 미상환 잔액

### 💼 자금 사용 및 기타 분석 도구 (4개)
- `get_public_capital_usage`: 공모자금 사용내역
- `get_private_capital_usage`: 사모자금 사용내역
- `get_equity`: 지분증권 발행 및 매출 내역
- `get_depository_receipt`: 예탁증권 발행 내역

### 📋 주요 파라미터
- `corp_code`: 기업고유번호 (8자리)
- `bsns_year`: 사업연도 (YYYY 형식)
- `reprt_code`: 보고서코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)
"""
