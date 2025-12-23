---
name: document-analysis-agent
description: 문서 기반 심층 분석 전문 에이전트 - 사업보고서, 반기보고서, 분기보고서의 원본 문서를 파싱하고 검색하는 기능
---

# Document Analysis Agent

문서 기반 심층 분석 전문 에이전트입니다. 사업보고서, 반기보고서, 분기보고서의 원본 문서를 파싱하고 검색하는 기능을 제공합니다.

## 역할

- 공시 문서 다운로드 및 파싱
- 재무제표 주석 자동 추출 및 캐싱
- 키워드 기반 문서 검색
- 문서 기반 심층 분석

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/document_analysis_agent.py`
- **도구 설명**: `app/agents/dart_agent/utils/prompt_templates/document_analysis_tools.py`

## 사용 도구 (3개)

### 문서 분석 도구 (3개)
- `get_disclosure_list`: 공시 목록 조회 (적절한 보고서 찾기)
- `get_disclosure_document`: 공시서류 원본 다운로드 및 재무제표 주석 자동 추출
- `search_financial_notes`: 공시문서 상세내용 키워드 기반 검색

## 클래스 구조

```python
class DocumentAnalysisAgent(DartBaseAgent):
    """문서 기반 심층 분석 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="DocumentAnalysisAgent",
            model=model,
            max_iterations=10
        )
    
    async def analyze_document_data(
        self, 
        context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        # 문서 기반 심층 분석
        # 스트리밍 지원
```

## 주요 메서드

### `analyze_document_data()`

문서 기반 심층 분석 메인 함수입니다:

1. **분석 시작**: 진행 상황 스트리밍
2. **문서 분석 워크플로우**: 보고서 식별 → 문서 다운로드 → 데이터 추출 → 키워드 검색
3. **LLM 기반 도구 선택**: LangGraph agent_executor를 통한 도구 선택
4. **도구 호출**: 공시 목록 조회, 문서 다운로드, 키워드 검색
5. **결과 반환**: AgentResult 생성 및 반환

## 캐시 활용

DocumentAnalysisAgent는 MCP 도구를 통해 간접적으로 파일 시스템 캐시를 활용합니다:

### `get_disclosure_document` 도구의 캐시

- **XML 파일 저장**: `disclosure_{rcp_no}.xml`
- **재무제표 주석 캐시**: `disclosure_cache/financial_notes_{rcp_no}/`
- **캐시 구조**:
  - `consolidated_notes/`: 연결재무제표 주석
  - `separate_notes/`: 재무제표 주석
  - `business_content/`: 사업의 내용
  - `company_overview/`: 회사의 개요

### `search_financial_notes` 도구의 캐시 활용

- 캐시 디렉토리에서 직접 검색
- XML 다운로드 및 추출 과정 생략
- 빠른 검색 성능

자세한 내용은 [document_analysis_agent_cache.md](../../document_analysis_agent_cache.md) 참조.

## 코드 패턴

### BaseAgent 상속

```python
from app.agents.dart_agent.base import DartBaseAgent

class DocumentAnalysisAgent(DartBaseAgent):
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="DocumentAnalysisAgent",
            model=model,
            max_iterations=10
        )
        self.agent_domain = "document_analysis"
```

### 도구 필터링

```python
async def _filter_tools_for_agent(self, tools):
    """문서 분석에서 사용할 도구 필터링"""
    target_tools = {
        "get_disclosure_list",
        "get_disclosure_document",
        "search_financial_notes",
    }
    
    filtered_tools = []
    for tool in tools:
        if getattr(tool, "name", "") in target_tools:
            filtered_tools.append(tool)
    
    return filtered_tools
```

### 스트리밍 분석

```python
@observe()
async def analyze_document_data(
    self, 
    context: AnalysisContext
) -> AsyncGenerator[Dict[str, Any], AgentResult]:
    # 시작 메시지
    yield {
        "type": "progress",
        "content": f"{context.corp_name}의 문서 기반 심층 분석을 시작하겠습니다...",
    }
    
    # 문서 분석 워크플로우 시작
    yield {
        "type": "progress",
        "content": "문서 분석 워크플로우를 시작합니다: 1) 보고서 식별 → 2) 문서 다운로드 → 3) 데이터 추출 → 4) 키워드 검색",
    }
    
    # LangGraph 에이전트 실행
    async for chunk in self.agent_executor.astream(...):
        # 스트리밍 처리
        ...
    
    # 최종 결과
    agent_result = AgentResult(...)
    yield agent_result
```

## 문서 분석 워크플로우

1. **보고서 식별**: `get_disclosure_list`로 적절한 보고서 찾기
   - 8월 조회 → 3월 조회 → 5월 조회 → 11월 조회 순서
   - 원하는 보고서를 찾으면 즉시 멈추고 다음 단계로 진행

2. **문서 다운로드**: `get_disclosure_document`로 원본 문서 다운로드
   - XML 파일 다운로드 및 저장
   - 재무제표 주석 자동 추출 및 캐싱

3. **데이터 추출**: 재무제표 주석이 자동으로 추출되어 캐시에 저장됨

4. **키워드 검색**: `search_financial_notes`로 특정 내용 검색
   - 최대 5회까지만 검색
   - 3회 연속 결과 없으면 중단

## 개선 가이드라인

### 캐시 활용 최적화

- 동일 문서 재검색 시 캐시 활용
- 캐시 무효화 조건 확인
- 불필요한 재다운로드 방지

### 검색 최적화

- 검색 키워드를 구체적으로 지정
- 검색 횟수 제한 (최대 5회)
- 연속 실패 시 중단

### 에러 처리

```python
try:
    result = await tool.ainvoke(params)
except Exception as e:
    log_step("문서 분석", "ERROR", f"{tool_name} 호출 실패: {str(e)}")
    yield {"type": "error", "content": f"문서 분석 중 오류가 발생했습니다: {str(e)}"}
```

## 주의사항

1. **중복 호출 방지**: 같은 기업의 공시 목록을 2번 이상 조회하지 말 것
2. **보고서 선택**: 이미 찾은 보고서를 다시 찾으려고 시도하지 말 것
3. **검색 제한**: 최대 5회까지만 검색, 3회 연속 결과 없으면 중단
4. **캐시 활용**: `get_disclosure_document`를 먼저 실행하여 캐시 생성 후 `search_financial_notes` 사용

## 관련 파일

- `dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/utils/prompt_templates/document_analysis_tools.py`: 문서 분석 도구 설명
- `document_analysis_agent_cache.md`: 캐시 활용 상세 가이드

