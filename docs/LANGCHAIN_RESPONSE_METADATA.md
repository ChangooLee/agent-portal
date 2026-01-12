# LangChain Response Metadata 가이드

## 개요

LangChain의 `AIMessage` 객체는 `response_metadata` 속성을 통해 LLM 응답과 함께 다양한 메타데이터를 제공합니다. 이 메타데이터는 **provider(OpenAI, Anthropic 등)에 따라 다른 구조**를 가집니다.

## Provider별 Response Metadata 구조

### 1. OpenAI 기반 (ChatOpenAI)

OpenAI API를 사용하는 경우 (`ChatOpenAI`), `response_metadata`는 다음과 같은 구조를 가집니다:

```python
{
    "token_usage": {
        "completion_tokens": 88,
        "prompt_tokens": 16,
        "total_tokens": 104,
        "completion_tokens_details": {
            "accepted_prediction_tokens": 0,
            "audio_tokens": 0,
            "reasoning_tokens": 0,
            "rejected_prediction_tokens": 0
        },
        "prompt_tokens_details": {
            "audio_tokens": 0,
            "cached_tokens": 0
        }
    },
    "model_name": "gpt-4o-mini-2024-07-18",
    "system_fingerprint": "fp_34a54ae93c",
    "id": "chatcmpl-ByN1Qkvqb5fAGKKzXXxZ3rBlnqkWs",
    "service_tier": "default",
    "finish_reason": "stop",  # 또는 "tool_call", "length", "content_filter", "function_call", "max_tokens"
    "logprobs": None
}
```

**주요 필드**:
- `token_usage`: 토큰 사용량 정보
  - `completion_tokens`: 응답에 사용된 토큰 수
  - `prompt_tokens`: 프롬프트에 사용된 토큰 수
  - `total_tokens`: 전체 토큰 수
- `model_name`: 사용된 모델 이름
- `finish_reason`: 응답 종료 이유
  - `"stop"`: 정상 종료
  - `"tool_call"`: 도구 호출 필요
  - `"length"`: 길이 제한 도달
  - `"content_filter"`: 콘텐츠 필터링
  - `"function_call"`: 함수 호출
  - `"max_tokens"`: 최대 토큰 도달
- `system_fingerprint`: 시스템 지문
- `id`: 응답 ID
- `service_tier`: 서비스 티어
- `logprobs`: 로그 확률 정보 (선택적)

### 2. Anthropic 기반

Anthropic API를 사용하는 경우, `response_metadata`는 다음과 같은 구조를 가집니다:

```python
{
    "model": "claude-3-5-sonnet-20241022",
    "usage": {
        "input_tokens": 100,
        "output_tokens": 200
    },
    "stop_reason": "end_turn"  # 또는 "max_tokens", "stop_sequence"
}
```

**주요 필드**:
- `model`: 사용된 모델 이름
- `usage`: 토큰 사용량 정보
  - `input_tokens`: 입력 토큰 수
  - `output_tokens`: 출력 토큰 수
- `stop_reason`: 응답 종료 이유
  - `"end_turn"`: 정상 종료
  - `"max_tokens"`: 최대 토큰 도달
  - `"stop_sequence"`: 중지 시퀀스 도달

## 코드베이스에서의 사용 예시

### langflow 예시

```python
# langflow/src/backend/base/langflow/base/models/model.py
if message.response_metadata:
    response_metadata = message.response_metadata
    
    # OpenAI 형식 확인
    openai_keys = ["token_usage", "model_name", "finish_reason"]
    inner_openai_keys = ["completion_tokens", "prompt_tokens", "total_tokens"]
    
    if all(key in response_metadata for key in openai_keys):
        token_usage = response_metadata["token_usage"]
        finish_reason = response_metadata["finish_reason"]
    
    # Anthropic 형식 확인
    anthropic_keys = ["model", "usage", "stop_reason"]
    inner_anthropic_keys = ["input_tokens", "output_tokens"]
    
    if all(key in response_metadata for key in anthropic_keys):
        usage = response_metadata["usage"]
        stop_reason = response_metadata["stop_reason"]
```

### 우리 프로젝트에서의 사용

```python
# backend/app/agents/common/base_single_agent.py
response_metadata = getattr(response, "response_metadata", {})

# 토큰 사용량 추출
token_usage = response_metadata.get("token_usage", {}) or {}

# finish_reason 추출 (OpenAI 형식)
finish_reason = response_metadata.get("finish_reason", "")

# finish_reason이 없으면 tool_calls 유무로 추론
if not finish_reason:
    if hasattr(response, "tool_calls") and response.tool_calls:
        finish_reason = "tool_call"
    else:
        finish_reason = "stop"
```

## 주의사항

1. **Provider에 따라 다른 필드명**: OpenAI는 `finish_reason`, Anthropic은 `stop_reason`을 사용합니다.
2. **토큰 사용량 필드명**: OpenAI는 `token_usage`, Anthropic은 `usage`를 사용합니다.
3. **항상 존재하지 않음**: `response_metadata`는 항상 존재하지 않을 수 있으므로, `getattr()` 또는 `.get()` 메서드를 사용하여 안전하게 접근해야 합니다.
4. **finish_reason이 없는 경우**: 일부 provider나 모델에서는 `finish_reason`이 제공되지 않을 수 있습니다. 이 경우 `tool_calls` 유무로 추론할 수 있습니다.

## 우리 프로젝트의 구현

### Provider 독립적 finish_reason 추출

`backend/app/agents/common/base_single_agent.py`에서 Provider에 관계없이 일관되게 처리합니다:

```python
def _extract_finish_reason(self, response: Any, response_metadata: Dict[str, Any]) -> str:
    """
    Provider에 관계없이 finish_reason 추출
    - OpenAI: finish_reason 직접 사용
    - Anthropic: stop_reason을 OpenAI 형식으로 변환
    - 없으면: tool_calls 유무로 추론
    """
    # 1. OpenAI 형식 확인
    finish_reason = response_metadata.get("finish_reason", "")
    
    # 2. Anthropic 형식 확인 및 변환
    if not finish_reason:
        stop_reason = response_metadata.get("stop_reason", "")
        if stop_reason:
            stop_reason_map = {
                "end_turn": "stop",
                "max_tokens": "length",
                "stop_sequence": "stop"
            }
            finish_reason = stop_reason_map.get(stop_reason, "stop")
    
    # 3. 추론 (tool_calls 유무)
    if not finish_reason:
        if hasattr(response, "tool_calls") and response.tool_calls:
            finish_reason = "tool_call"
        else:
            finish_reason = "stop"
    
    return finish_reason
```

### 사용자 친화적 메시지 변환

```python
def _get_finish_reason_message(self, finish_reason: str) -> str:
    """finish_reason을 사용자 친화적 메시지로 변환"""
    finish_reason_messages = {
        "stop": "✅ 응답 완료",
        "tool_call": "🔧 도구 호출 필요",
        "length": "⚠️ 길이 제한 도달",
        "content_filter": "⚠️ 콘텐츠 필터링",
        "function_call": "🔧 함수 호출",
        "max_tokens": "⚠️ 최대 토큰 도달"
    }
    return finish_reason_messages.get(finish_reason, f"⏳ 처리 중 ({finish_reason})")
```

### 프론트엔드 표시

모든 에이전트 화면에서 백엔드에서 변환된 친화적 메시지를 그대로 표시합니다:

```typescript
case 'progress':
    // finish_reason이 있으면 백엔드에서 이미 친화적 메시지로 변환되어 있음
    const progressMsg = data.message || data.content || '분석 진행 중...';
    currentToolCall = transformProgressMessage(progressMsg);
    break;
```

## 참고 자료

- [LangChain AIMessage 문서](https://python.langchain.com/docs/modules/model_io/chat/messages/)
- [OpenAI API 응답 구조](https://platform.openai.com/docs/api-reference/chat/object)
- [Anthropic API 응답 구조](https://docs.anthropic.com/claude/reference/messages-post)

