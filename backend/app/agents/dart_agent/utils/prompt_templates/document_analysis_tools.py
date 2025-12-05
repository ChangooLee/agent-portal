def get_document_analysis_tools_description() -> str:
    """
    DocumentAnalysisAgent에서 사용할 수 있는 도구들의 설명을 반환합니다.
    """
    return """
### 📋 문서 분석 도구 (3개)

#### 1. `get_disclosure_list` - 공시 목록 조회
**목적**: 사업보고서, 반기보고서, 분기보고서 등 pblntf_ty="A"로 찾기

**조회 순서**:
1. 8월 조회 (page_no=1) → 데이터 없으면 page_no=2
2. 3월 조회 (page_no=1) → 데이터 없으면 page_no=2  
3. 5월 조회 (page_no=1) → 데이터 없으면 page_no=2
4. 11월 조회 (page_no=1) → 데이터 없으면 page_no=2

**중요**: 원하는 보고서를 찾으면 즉시 멈추고 다음 단계로 진행

#### 2. `get_disclosure_document` - 원본 문서 다운로드
**목적**: 찾은 보고서의 XML 원본 다운로드

#### 3. `search_financial_notes` - 키워드 검색
**목적**: 공시문서에서 특정 내용 검색
**제한**: 최대 5회까지만 검색, 3회 연속 결과 없으면 중단

### 🚨 절대 금지
- 같은 기업의 공시 목록을 2번 이상 조회하지 말 것
- 이미 찾은 보고서를 다시 찾으려고 시도하지 말 것
- 같은 기간, 같은 페이지로 중복 호출하지 말 것

### 💡 사용 예시
```
# 1단계: 보고서 찾기
get_disclosure_list(corp_code="기업코드", bgn_de="조회시작일", end_de="조회종료일", pblntf_ty="A", page_no=1)
# 8월에 없으면 page_no=2, 그래도 없으면 3월로 이동

# 2단계: 문서 다운로드  
get_disclosure_document(rcp_no="공시번호")

# 3단계: 키워드 검색
search_financial_notes(rcp_no="공시번호", search_term="사업의 개요")
```
"""
