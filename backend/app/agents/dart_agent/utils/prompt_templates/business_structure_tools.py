def get_business_structure_tools_description() -> str:
    """
    BusinessStructureAgent에서 사용할 수 있는 도구들의 설명을 반환합니다.
    """
    return """
### 사업양수도 (2개)
- `get_business_acquisition`: 영업양수 결정 조회
- `get_business_transfer`: 영업양도 결정 조회

### 합병분할 (6개)
- `get_merger`: 회사합병 결정 조회
- `get_division`: 회사분할 결정 조회
- `get_division_merger`: 분할합병 결정 조회
- `get_stock_exchange`: 주식교환/이전 결정 조회
- `get_merger_report`: 합병 증권신고서 조회
- `get_stock_exchange_report`: 주식교환/이전 증권신고서 조회
- `get_division_report`: 분할 증권신고서 조회

### 자산거래 (9개)
- `get_other_corp_stock_acquisition`: 타법인 주식 양수 결정 조회
- `get_other_corp_stock_transfer`: 타법인 주식 양도 결정 조회
- `get_stock_related_bond_acquisition`: 주권 관련 사채권 양수 결정 조회
- `get_stock_related_bond_transfer`: 주권 관련 사채권 양도 결정 조회
- `get_tangible_asset_acquisition`: 유형자산 양수 결정 조회
- `get_tangible_asset_transfer`: 유형자산 양도 결정 조회
- `get_asset_transfer`: 자산양수도 및 풋백옵션 계약 조회
- `get_investment_in_other_corp`: 타법인 출자 현황 조회
"""
