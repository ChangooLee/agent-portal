def get_legal_compliance_tools_description() -> str:
    """
    LegalComplianceAgent에서 사용할 수 있는 도구들의 설명을 반환합니다.
    """
    return """
### 🚨 경영위기 도구 (4개)
- `get_bankruptcy`: 부도 발생 사실 조회
- `get_business_suspension`: 영업정지 사실 조회
- `get_rehabilitation`: 회생절차 개시신청 사실 조회
- `get_dissolution`: 해산사유 발생 사실 조회

### 🏦 채권관리 도구 (2개)
- `get_creditor_management`: 채권은행 관리절차 개시 사실 조회
- `get_creditor_management_termination`: 채권은행 관리절차 종료 사실 조회

### ⚖️ 법적분쟁 도구 (1개)
- `get_lawsuit`: 소송 제기 사실 조회
"""
