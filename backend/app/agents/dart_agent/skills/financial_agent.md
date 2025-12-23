---
name: financial-agent
description: 재무 데이터 수집 및 분석 전문 에이전트 - 재무 건전성, 수익성, 유동성, 재무제표 분석
---

# Financial Agent

재무 데이터 수집 및 분석 전문 에이전트입니다. 재무 건전성, 수익성, 유동성, 재무제표 분석을 담당합니다.

## 역할

- 재무제표 데이터 수집 및 분석
- 재무지표 계산 및 해석
- 수익성, 안정성, 성장성, 활동성 지표 분석
- 재무 리스크 평가

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/financial_agent.py`
- **도구 설명**: `app/agents/dart_agent/utils/prompt_templates/financial_tools.py`

## 사용 도구 (8개)

### 기업 식별 및 기본 정보 (3개)
- `get_corporation_code_by_name`: 기업명으로 고유번호 조회
- `get_corporation_info`: 기업 기본정보 조회
- `get_disclosure_list`: 공시 목록 조회

### 재무제표 데이터 (3개)
- `get_single_acnt`: 단일회사 재무제표 계정 조회
- `get_multi_acnt`: 다중회사 재무제표 계정 조회
- `get_single_acc`: 단일회사 계정과목 조회

### 재무지표 데이터 (2개)
- `get_single_index`: 단일회사 재무지표 조회
- `get_multi_index`: 다중회사 재무지표 조회

## 클래스 구조

```python
class FinancialAgent(DartBaseAgent):
    """재무 데이터 수집 및 분석 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        # DartBaseAgent 초기화
        # PromptBuilder 초기화
        # MessageRefiner 초기화
    
    async def analyze_financial_data(
        self, 
        context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        # 재무 데이터 분석
        # 스트리밍 지원
```

## 주요 메서드

### `analyze_financial_data()`

재무 데이터 분석 메인 함수입니다:

1. **분석 시작**: 진행 상황 스트리밍
2. **LLM 기반 도구 선택**: LangGraph agent_executor를 통한 도구 선택
3. **도구 호출**: 재무제표 및 재무지표 도구 호출
4. **데이터 수집**: 도구 결과 수집 및 저장
5. **결과 반환**: AgentResult 생성 및 반환

## 코드 패턴

### BaseAgent 상속

```python
from app.agents.dart_agent.base import DartBaseAgent
from app.agents.dart_agent.dart_types import AnalysisContext, AgentResult

class FinancialAgent(DartBaseAgent):
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="FinancialAgent",
            model=model,
            max_iterations=10
        )
        self.agent_domain = "financial"
```

### 도구 필터링

```python
async def _filter_tools_for_agent(self, tools):
    """재무 분석에서 사용할 도구 필터링"""
    target_tools = {
        "get_corporation_code_by_name",
        "get_corporation_info",
        "get_disclosure_list",
        "get_single_acnt",
        "get_multi_acnt",
        "get_single_acc",
        "get_single_index",
        "get_multi_index",
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
async def analyze_financial_data(
    self, 
    context: AnalysisContext
) -> AsyncGenerator[Dict[str, Any], AgentResult]:
    # 시작 메시지
    yield {
        "type": "progress",
        "content": f"{context.corp_name}의 재무 데이터를 수집하겠습니다...",
    }
    
    # LangGraph 에이전트 실행
    async for chunk in self.agent_executor.astream(
        {"messages": [("human", analysis_prompt)]},
        config={"configurable": {"thread_id": f"financial_{context.corp_code}_{int(time.time())}"}},
    ):
        if "agent" in chunk:
            # LLM 응답 스트리밍
            yield {"type": "progress", "content": "..."}
        elif "tools" in chunk:
            # 도구 호출 및 결과
            yield {"type": "tool_call", "tool_name": "...", "tool_args": {...}}
            yield {"type": "tool_result", "content": "...", "tool_name": "..."}
    
    # 최종 결과
    agent_result = AgentResult(
        agent_name=self.agent_name,
        analysis_type="financial_analysis",
        risk_level=RiskLevel.LOW,
        key_findings=[...],
        supporting_data={...},
        execution_time=time.time() - start_time,
    )
    yield agent_result
```

## 프롬프트 구조

FinancialAgent는 `PromptBuilder`를 사용하여 프롬프트를 생성합니다:

1. **BasePromptTemplate**: 핵심 원칙, 기업 정보, 경고, 작업 지시사항
2. **DomainSpecificTemplates**: 재무 분석 특화 지침
3. **financial_tools.py**: 재무 도구 상세 설명

## 개선 가이드라인

### 도구 호출 최적화

- 필요한 도구만 호출 (중복 호출 방지)
- 여러 기업 비교 시 `get_multi_acnt`, `get_multi_index` 사용
- 단일 기업 분석 시 `get_single_acnt`, `get_single_index` 사용

### 데이터 검증

```python
# 도구 결과 검증
if not result or len(result) == 0:
    log_step("재무 데이터 수집", "WARNING", "데이터가 없습니다.")
    # 재호출 또는 다른 도구 시도
```

### 에러 처리

```python
try:
    result = await tool.ainvoke(params)
except Exception as e:
    log_step("도구 호출", "ERROR", f"{tool_name} 호출 실패: {str(e)}")
    yield {"type": "error", "content": f"재무 데이터 수집 중 오류: {str(e)}"}
```

## 주의사항

1. **도구 선택**: LLM이 적절한 도구를 선택하도록 명확한 프롬프트 제공
2. **무한 루프 방지**: 도구 호출 제한 설정 (`max_tool_calls`)
3. **데이터 품질**: 수집된 데이터가 유효한지 검증
4. **스트리밍 일관성**: 모든 중간 과정을 스트리밍으로 전달

## 관련 파일

- `dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/utils/prompt_templates/financial_tools.py`: 재무 도구 설명
- `app/agents/dart_agent/utils/prompt_templates/prompt_builder.py`: 프롬프트 빌더

