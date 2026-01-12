# 친화적 메시지 변환 위치 정리

프로젝트에서 기술적 메시지를 사용자 친화적 메시지로 변환하는 부분들을 정리합니다.

## 1. 백엔드 (Backend)

### 1.1 `base_single_agent.py` - finish_reason 변환 (현재 미사용)

**위치**: `backend/app/agents/common/base_single_agent.py`

**메서드**: `_get_finish_reason_message()`

**기능**: finish_reason을 친화적 메시지로 변환

**상태**: ⚠️ **현재 미사용** (LLM 원본 응답을 그대로 표시하도록 수정됨)

```python
def _get_finish_reason_message(self, finish_reason: str) -> str:
    finish_reason_messages = {
        "stop": "✅ 응답 완료",
        "tool_call": "🔧 도구 호출 필요",
        "tool_calls": "🔧 도구 호출 필요",
        "length": "⚠️ 길이 제한 도달",
        "content_filter": "⚠️ 콘텐츠 필터링",
        "function_call": "🔧 함수 호출",
        "max_tokens": "⚠️ 최대 토큰 도달"
    }
    return finish_reason_messages.get(finish_reason, f"⏳ 처리 중 ({finish_reason})")
```

**참고**: 현재는 LLM의 실제 응답 내용(`response.content`)을 그대로 표시하도록 변경됨.

---

### 1.2 `message_refiner.py` - 기술적 메시지 정제

**위치**: `backend/app/agents/dart_agent/message_refiner.py`

**클래스**: `MessageRefiner`

**기능**: 기술적 메시지를 사용자 친화적으로 변환

**주요 메서드**:
- `refine(technical_message, message_type)`: 기술적 메시지를 친화적으로 변환
- `_refine_tool_call_message(message)`: 도구 호출 메시지 정제
- `_refine_progress_message(message)`: 진행 상황 메시지 정제
- `get_action_message(tool_name)`: 도구 호출 액션 메시지 반환

**매핑 예시**:
```python
self.tool_name_mapping = {
    "get_corporation_code_by_name": "기업 코드 조회",
    "get_corporation_info": "기업 정보 조회",
    "get_disclosure_list": "공시 목록 조회",
    # ... 200개 이상의 도구 매핑
}

self.tool_action_messages = {
    "get_corporation_code_by_name": "기업 코드를 조회하고 있습니다",
    "get_corporation_info": "기업 정보를 조회하고 있습니다",
    # ... 많은 액션 메시지
}
```

**사용 위치**: DART 에이전트의 Multi Agent 시스템에서 사용

---

### 1.3 `message_generator.py` - 액션별 메시지 생성

**위치**: `backend/app/agents/dart_agent/utils/message_generator.py`

**클래스**: `MessageGenerator`

**기능**: 경량 LLM을 사용한 사용자 친화적 메시지 생성

**정적 매핑**:
```python
ACTION_MESSAGES = {
    "intent_classification_start": "질문을 분석하고 있습니다...",
    "intent_classification_complete": "질문 분석이 완료되었습니다.",
    "agent_selection_start": "분석에 필요한 에이전트를 선택하고 있습니다...",
    "data_collection": "데이터를 수집하고 있습니다...",
    "financial_analysis": "재무 데이터를 분석하고 있습니다...",
    # ... 기타 액션 메시지
}
```

**동적 생성**: LLM을 사용하여 컨텍스트 기반 메시지 생성 (LLM 없으면 정적 메시지 사용)

---

### 1.4 `dart_master_agent.py` - 마스터 에이전트 메시지

**위치**: `backend/app/agents/dart_agent/dart_master_agent.py`

**기능**: 마스터 에이전트의 진행 상황 메시지

**매핑**:
```python
actions = {
    "single_agent_analysis": f"{context.get('corp_name', '기업')} 분석 진행 중...",
    "multi_agent_analysis": f"{context.get('corp_name', '기업')}에 대해 다중 분석 진행 중...",
    "additional_analysis": f"{context.get('corp_name', '기업')}에 대한 추가 분석 진행 중...",
    "result_integration": "결과 통합 중...",
}
```

---

## 2. 프론트엔드 (Frontend)

### 2.1 DART 에이전트 화면

**위치**: `webui/src/routes/(app)/dart/+page.svelte`

**함수**: `transformProgressMessage()`

**기능**: 기술적 이벤트 이름을 친화적 메시지로 변환

**매핑**:
```typescript
const technicalToFriendly: Record<string, string> = {
    'intent_classification_start': '🔍 질문 분석 중...',
    'intent_classification_complete': '✅ 질문 분석 완료',
    'mcp_call_start': '🔧 데이터 조회 중...',
    'mcp_call_complete': '✅ 데이터 조회 완료',
    'llm_call_start': '🤖 AI 분석 중...',
    'llm_call_complete': '✅ AI 분석 완료',
    'tool_call_start': '🔧 도구 실행 중...',
    'tool_call_complete': '✅ 도구 실행 완료',
    'mcp_start': '🔧 MCP 도구 호출 중...',
    'mcp_complete': '✅ MCP 도구 호출 완료'
};
```

**패턴 감지**: `_start`, `_complete`, `_end` 패턴이 포함되면 "⏳ 처리 중..."으로 변환

---

### 2.2 건강/의료 에이전트 화면

**위치**: `webui/src/routes/(app)/health-agent/+page.svelte`

**함수**: `transformProgressMessage()`

**매핑**:
```typescript
const technicalToFriendly: Record<string, string> = {
    'mcp_call_start': '🔧 데이터 조회 중...',
    'mcp_call_complete': '✅ 데이터 조회 완료',
    'llm_call_start': '🤖 AI 분석 중...',
    'llm_call_complete': '✅ AI 분석 완료',
    'tool_call_start': '🔧 도구 실행 중...',
    'tool_call_complete': '✅ 도구 실행 완료'
};
```

---

### 2.3 부동산 에이전트 화면

**위치**: `webui/src/routes/(app)/realestate/+page.svelte`

**함수**: `transformProgressMessage()`

**매핑**: 건강/의료 에이전트와 동일

---

### 2.4 법률 에이전트 화면

**위치**: `webui/src/routes/(app)/legislation/+page.svelte`

**함수**: `transformProgressMessage()`

**매핑**: 건강/의료 에이전트와 동일

---

## 3. 개선 권장 사항

### 3.1 중복 제거

현재 프론트엔드의 4개 에이전트 화면에서 동일한 `transformProgressMessage()` 로직이 중복되어 있습니다.

**개선 방안**:
- 공통 유틸리티 함수로 추출: `webui/src/lib/utils/message-transformer.ts`
- 모든 에이전트 화면에서 공통 함수 사용

### 3.2 finish_reason 메시지 처리

현재 `_get_finish_reason_message()`는 정의되어 있지만 사용되지 않습니다 (LLM 원본 응답을 그대로 표시하도록 변경됨).

**확인 필요**:
- LLM 원본 응답이 항상 사용자 친화적인지 확인
- 필요시 finish_reason 기반 메시지 변환 재활성화 검토

### 3.3 백엔드-프론트엔드 일관성

백엔드의 `MessageRefiner`와 프론트엔드의 `transformProgressMessage()`가 서로 다른 매핑을 사용하고 있습니다.

**개선 방안**:
- 백엔드에서 친화적 메시지로 변환하여 전달
- 프론트엔드는 변환된 메시지를 그대로 표시

---

## 4. 요약

| 위치 | 기능 | 상태 |
|------|------|------|
| `base_single_agent.py` | finish_reason → 친화적 메시지 | ⚠️ 미사용 |
| `message_refiner.py` | 기술적 메시지 → 친화적 메시지 | ✅ 사용 중 (DART Multi Agent) |
| `message_generator.py` | 액션 → 친화적 메시지 | ✅ 사용 중 (DART Multi Agent) |
| `dart_master_agent.py` | 마스터 에이전트 메시지 | ✅ 사용 중 |
| `dart/+page.svelte` | 기술적 이벤트 → 친화적 메시지 | ✅ 사용 중 |
| `health-agent/+page.svelte` | 기술적 이벤트 → 친화적 메시지 | ✅ 사용 중 |
| `realestate/+page.svelte` | 기술적 이벤트 → 친화적 메시지 | ✅ 사용 중 |
| `legislation/+page.svelte` | 기술적 이벤트 → 친화적 메시지 | ✅ 사용 중 |

---

**Last Updated**: 2025-01-02

