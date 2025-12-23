---
name: dart-master-agent
description: DART 멀티에이전트 시스템의 마스터 조정자 - 전체 워크플로우 관리, 의도 분류 결과 기반 하위 에이전트 실행, 최종 결과 통합
---

# Dart Master Agent

DART 멀티에이전트 시스템의 마스터 조정자입니다. 전체 워크플로우를 관리하고, IntentClassifierAgent의 분류 결과를 기반으로 하위 에이전트를 실행하며, 최종 결과를 통합합니다.

## 역할

- 전체 분석 워크플로우 조정
- IntentClassifierAgent를 통한 의도 분류 및 에이전트 선택
- 단일/복수 기업 분석 분기 처리
- 전문 에이전트 실행 및 결과 수집
- LLM 기반 최종 결과 통합 및 리포트 생성

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/dart_master_agent.py`

## 클래스 구조

```python
class DartMasterAgent(DartBaseAgent):
    """DART 멀티에이전트 시스템의 마스터 조정자"""
    
    def __init__(self, model: str = "qwen-235b"):
        # DartBaseAgent 초기화
        # 하위 에이전트 저장소 초기화
        # 메시지 생성기 초기화
    
    async def coordinate_analysis_stream(
        self, 
        user_question: str, 
        thread_id: Optional[str] = None, 
        user_email: Optional[str] = None
    ):
        # 스트리밍 분석 조정
        # IntentClassifierAgent 호출
        # 전문 에이전트 실행
        # 결과 통합
```

## 주요 메서드

### `coordinate_analysis_stream()`

전체 분석 워크플로우를 스트리밍으로 조정합니다:

1. **시작 응답 생성**: `_generate_start_response()` - LLM을 사용한 친근한 시작 메시지
2. **질문 유형 분류**: `_classify_question_type()` - greeting/agent_intro/analysis 분류
3. **의도 분류**: IntentClassifierAgent의 `classify_intent_and_select_agents()` 호출
4. **단일/복수 기업 분기**: `_handle_multi_company_analysis()` 또는 단일 기업 분석
5. **전문 에이전트 실행**: `_execute_sub_agents_for_data_collection()`
6. **결과 통합**: `_integrate_agent_results()` 또는 `_integrate_multi_company_results()`

### `_execute_sub_agents_for_data_collection()`

선택된 전문 에이전트들을 순차 실행하고 결과를 수집합니다:

- 각 에이전트의 `analyze_[domain]_data()` 메서드 직접 호출
- 스트리밍 지원
- AgentResult 수집

### `_integrate_agent_results()`

단일 기업 분석 결과를 LLM으로 통합합니다:

- 수집된 데이터 정리
- 의도 기반 데이터 필터링
- LLM 분석 프롬프트 구성
- 최종 리포트 생성

### `_integrate_multi_company_results()`

복수 기업 분석 결과를 LLM으로 비교 분석합니다:

- 기업별 데이터 정리
- 비교 분석 프롬프트 구성
- LLM 비교 분석 리포트 생성
- Fallback 로직 (LLM 실패 시 수집 데이터로 직접 리포트 생성)

## 사용 도구

마스터 에이전트는 기본 도구 3개만 사용합니다:

- `get_corporation_code_by_name`: 기업명으로 고유번호 조회
- `get_corporation_info`: 기업 기본정보 조회
- `get_disclosure_list`: 공시 목록 조회

## 코드 패턴

### BaseAgent 상속

```python
from app.agents.dart_agent.base import DartBaseAgent

class DartMasterAgent(DartBaseAgent):
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="DartMasterAgent",
            model=model,
            max_iterations=15
        )
```

### 하위 에이전트 등록

```python
def register_sub_agent(self, agent_name: str, agent: BaseAgent):
    """하위 에이전트 등록"""
    self.sub_agents[agent_name] = agent

def register_intent_classifier(self, classifier):
    """의도 분류기 등록"""
    self.intent_classifier = classifier
```

### 스트리밍 조정

```python
async def coordinate_analysis_stream(
    self, 
    user_question: str, 
    thread_id: Optional[str] = None, 
    user_email: Optional[str] = None
):
    # 시작 응답
    start_response = await self._generate_start_response(user_question)
    yield {"type": "start", "content": start_response}
    
    # 의도 분류
    async for response in self.intent_classifier.classify_intent_and_select_agents(
        user_question, {}
    ):
        if isinstance(response, IntentClassificationResult):
            classification_result = response
        else:
            yield response
    
    # 전문 에이전트 실행
    async for response in self._execute_sub_agents_for_data_collection(
        context, selected_agents, thread_id=thread_id
    ):
        yield response
    
    # 결과 통합
    final_result = await self._integrate_agent_results(...)
    yield {"type": "content", "content": final_result["response"]}
    yield {"type": "end"}
```

### 복수 기업 분석

```python
async def _handle_multi_company_analysis(
    self,
    user_question: str,
    corp_info_list: List[Dict],
    selected_agents: List[str],
    classification: Any,
    thread_id: Optional[str] = None,
):
    all_results = []
    company_results = {}
    
    # 각 기업별 순차 분석
    for i, corp_info in enumerate(corp_info_list):
        context = create_analysis_context(...)
        
        # async generator이므로 async for로 순회
        agent_results_for_company = []
        async for response in self._execute_sub_agents_for_data_collection(
            context, selected_agents, thread_id=thread_id
        ):
            if response.get("type") == "agent_results":
                agent_results_for_company.extend(response.get("results", []))
        
        company_results[company_name] = {
            "corp_info": corp_info,
            "agent_results": agent_results_for_company,
        }
    
    # 복수 기업 통합 분석
    final_result = await self._integrate_multi_company_results(
        user_question, company_results, classification
    )
    
    return final_result
```

## 개선 가이드라인

### LLM 응답 검증

LLM이 빈 응답을 반환할 수 있으므로 Fallback 로직이 필요합니다:

```python
if not integrated_response or len(integrated_response.strip()) < 50:
    log_step("LLM 응답 검증", "WARNING", "LLM 응답이 비어있음, fallback 사용")
    # 에이전트 결과에서 직접 리포트 생성
    formatted_insights = self._format_agent_insights(agent_insights)
    integrated_response = f"""# 📊 {corp_name} {user_question}

## 📋 분석 요약

{formatted_insights}

## 📌 참고사항

LLM 응답이 비어있어 수집된 데이터를 직접 제공합니다.
"""
```

### Async Generator 처리

`_execute_sub_agents_for_data_collection`은 async generator이므로 `async for`로 순회해야 합니다:

```python
# 올바른 사용
agent_results = []
async for response in self._execute_sub_agents_for_data_collection(...):
    if response.get("type") == "agent_results":
        agent_results = response.get("results", [])
        break

# 잘못된 사용 (await로 직접 호출하면 안 됨)
agent_results = await self._execute_sub_agents_for_data_collection(...)  # ❌
```

### 스트리밍 일관성

모든 중간 메시지를 yield하여 사용자가 진행 상황을 확인할 수 있도록 합니다:

```python
yield {"type": "progress", "content": "분석을 시작합니다..."}
yield {"type": "progress", "content": "데이터를 수집하고 있습니다..."}
yield {"type": "tool_call", "tool_name": "...", "tool_args": {...}}
yield {"type": "tool_result", "content": "...", "tool_name": "..."}
yield {"type": "content", "content": "최종 분석 리포트"}
yield {"type": "end"}
```

## 주의사항

1. **의도 분류기 필수**: IntentClassifierAgent가 등록되지 않으면 에러 반환
2. **복수 기업 처리**: async generator를 올바르게 순회해야 함
3. **LLM Fallback**: LLM 응답이 비어있을 때 대체 리포트 생성 필요
4. **스트리밍 순서**: 모든 청크를 순서대로 yield하여 클라이언트가 올바르게 처리할 수 있도록 함

## 관련 파일

- `app/agents/dart_agent/dart_agent.py`: 메인 에이전트
- `app/agents/dart_agent/intent_classifier_agent.py`: 의도 분류 에이전트
- `app/agents/dart_agent/dart_types.py`: 공통 데이터 구조
- `app/agents/dart_agent/utils/prompt_templates/`: 프롬프트 템플릿

