"""
FinancialAgent 도구 설명
"""


def get_financial_tools_description() -> str:
    """재무 분석 도구 설명"""
    return """### 📊 기업 식별 및 기본 정보 (3개)
- `get_corporation_code_by_name`: 기업명으로 고유번호 조회
- `get_corporation_info`: 기업 기본정보 조회
- `get_disclosure_list`: 공시 목록 조회

### 📈 재무제표 데이터 (3개)
- `get_single_acnt`: 단일회사 재무제표 계정 조회
- `get_multi_acnt`: 다중회사 재무제표 계정 조회
- `get_single_acc`: 단일회사 계정과목 조회

### 📊 재무지표 데이터 (2개)
- `get_single_index`: 단일회사 재무지표 조회
- `get_multi_index`: 다중회사 재무지표 조회

### 💡 도구 사용 가이드
- **기업 식별**: 먼저 `get_corporation_code_by_name`으로 정확한 기업코드 확인
- **기본 정보**: `get_corporation_info`로 기업 개요 파악
- **재무제표**: `get_single_acnt` 또는 `get_multi_acnt`로 손익계산서, 재무상태표 등 조회
- **재무지표**: `get_single_index` 또는 `get_multi_index`로 수익성, 안정성, 성장성 지표 조회
- **공시 정보**: `get_disclosure_list`로 최신 공시 현황 확인

### 📋 주요 파라미터
- `corp_code`: 기업고유번호 (8자리)
- `bsns_year`: 사업연도 (YYYY 형식)
- `reprt_code`: 보고서코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)
- `fs_div`: 재무제표구분 (CFS: 연결재무제표, OFS: 별도재무제표)"""
