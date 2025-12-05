def get_executive_audit_tools_description() -> str:
    """
    ExecutiveAuditAgent에서 사용할 수 있는 도구들의 설명을 반환합니다.
    """
    return """
### 💰 임원보수 도구 (6개)
- `get_individual_compensation`: 개별임원보수 조회
- `get_total_compensation`: 총임원보수 조회
- `get_individual_compensation_amount`: 개별임원보수금액 조회
- `get_unregistered_exec_compensation`: 미등기임원보수 조회
- `get_executive_compensation_approved`: 임원보수승인 조회
- `get_executive_compensation_by_type`: 임원보수유형별 조회

### 🔍 감사 관련 도구 (3개)
- `get_accounting_auditor_opinion`: 회계감사인의견 조회
- `get_audit_service_contract`: 감사서비스계약 조회
- `get_non_audit_service_contract`: 비감사서비스계약 조회

### 📋 주요 파라미터
- `corp_code`: 기업고유번호 (8자리)
- `bsns_year`: 사업연도 (YYYY 형식)
- `reprt_code`: 보고서코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)
"""
