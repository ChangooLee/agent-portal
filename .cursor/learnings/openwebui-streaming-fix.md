# Open-WebUI 스트리밍 응답 JSON 파싱 에러 해결

## 2025-11-19: "data: {"id"... is not valid JSON" 에러 완전 해결

### 문제 상황

**에러 메시지** (브라우저 콘솔):
```
SyntaxError: Unexpected token 'd', "data: {"id"... is not valid JSON
```

**발생 위치**: 채팅 화면 (`http://localhost:3001/c/{chat_id}`)

**증상**:
- API는 200 OK 응답 (정상)
- `content-type: text/event-stream` 헤더 정상
- LiteLLM을 통한 OpenRouter 호출 성공
- 하지만 프론트엔드에서 JSON 파싱 에러 발생

### 근본 원인

**문제 코드** (`webui/src/lib/apis/openai/index.ts`):

```typescript
// ❌ 잘못된 코드 (스트리밍 응답도 JSON으로 파싱 시도)
export const generateOpenAIChatCompletion = async (
    token: string = '',
    body: object,
    url: string = `${WEBUI_BASE_URL}/api`
) => {
    const res = await fetch(`${url}/chat/completions`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    })
        .then(async (res) => {
            if (!res.ok) throw await res.json();
            return res.json();  // ❌ SSE 응답도 JSON으로 파싱 시도
        });
    
    return res;
};
```

**문제점**:
1. `stream=true`로 요청 → 백엔드가 `text/event-stream` 응답
2. 프론트엔드가 `res.json()`을 호출하여 SSE 텍스트 전체를 JSON으로 파싱 시도
3. SSE 텍스트 형식: `data: {"id":"...","choices":[...]}\n\n`
4. `JSON.parse("data: {"id":...")`  → SyntaxError!

**올바른 처리 방법**:
- SSE 응답: `Response` 객체를 그대로 반환 → `res.body`를 `createOpenAITextStream()`으로 전달
- JSON 응답: `res.json()`으로 파싱 후 반환

### 해결 방법

**수정 코드** (`webui/src/lib/apis/openai/index.ts`):

```typescript
// ✅ 올바른 코드 (스트리밍 응답과 JSON 응답 구분)
export const generateOpenAIChatCompletion = async (
    token: string = '',
    body: object,
    url: string = `${WEBUI_BASE_URL}/api`
) => {
    let error = null;

    const res = await fetch(`${url}/chat/completions`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
    }).catch((err) => {
        error = `${err?.detail ?? err}`;
        return null;
    });

    // ⚠️ CRITICAL: 스트리밍 응답 (text/event-stream)은 Response 객체 그대로 반환
    // 프론트엔드에서 res.body를 createOpenAITextStream()으로 전달
    if (res && res.ok) {
        const contentType = res.headers.get('content-type') || res.headers.get('Content-Type') || '';
        if (contentType.includes('text/event-stream')) {
            return res; // ✅ SSE: Response 객체 반환
        }
    }

    // 비스트리밍 응답: JSON 파싱
    const data = await res?.json().catch((err) => {
        error = `Failed to parse response: ${err}`;
        return null;
    });

    if (!res || !res.ok) {
        error = data?.detail || 'Request failed';
    }

    if (error) {
        throw error;
    }

    return data;
};
```

**핵심 변경 사항**:
1. **`content-type` 헤더 확인**: `text/event-stream` 포함 시 Response 객체 그대로 반환
2. **대소문자 호환**: `res.headers.get('content-type')` + `res.headers.get('Content-Type')` 둘 다 확인
3. **JSON 응답만 파싱**: SSE가 아닐 때만 `res.json()` 호출

### Chat.svelte에서 사용 방법

**스트리밍 응답 처리** (`webui/src/lib/components/chat/Chat.svelte`):

```typescript
const res = await generateOpenAIChatCompletion(
    localStorage.token,
    {
        stream: true,  // 스트리밍 요청
        model: model.id,
        messages: messages,
        ...
    }
);

// res는 Response 객체 (stream=true일 때)
if (res && res.ok && res.body) {
    const textStream = await createOpenAITextStream(res.body, $settings.splitLargeChunks);
    for await (const update of textStream) {
        const { value, done, error } = update;
        // ... SSE 이벤트 처리
    }
}
```

**비스트리밍 응답 처리**:

```typescript
const res = await generateOpenAIChatCompletion(
    localStorage.token,
    {
        stream: false,  // 비스트리밍 요청
        model: model.id,
        messages: messages,
        ...
    }
);

// res는 파싱된 JSON 객체 (stream=false일 때)
console.log(res.choices[0].message.content);
```

### 테스트 결과

**브라우저에서 확인**:
1. http://localhost:3001 접속
2. 새 채팅 시작
3. 메시지 전송: "Hello, test!"
4. ✅ 실시간 스트리밍 응답 정상 표시
5. ✅ JSON 파싱 에러 없음
6. ✅ 브라우저 콘솔에 에러 없음

**API 응답 헤더**:
```
HTTP/1.1 200 OK
content-type: text/event-stream; charset=utf-8
x-litellm-version: 1.80.0
x-litellm-model-api-base: https://openrouter.ai/api/v1/chat/completions
```

**SSE 응답 샘플**:
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1732008282,"model":"qwen-235b","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1732008282,"model":"qwen-235b","choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}

data: [DONE]
```

### 핵심 원칙

1. **SSE vs JSON 응답 구분**:
   - SSE: `Response` 객체 반환 → `res.body`를 스트림 파서로 전달
   - JSON: 파싱된 객체 반환 → 직접 사용

2. **Content-Type 헤더 확인**:
   - `text/event-stream`: SSE 응답
   - `application/json`: JSON 응답
   - 대소문자 둘 다 확인 (aiohttp 호환성)

3. **에러 핸들링**:
   - `fetch()` 실패: 네트워크 에러
   - `res.ok === false`: HTTP 에러 (4xx, 5xx)
   - `res.json()` 실패: JSON 파싱 에러
   - SSE 파싱 에러: `createOpenAITextStream()` 내부 처리

4. **프론트엔드 스트리밍 처리 흐름**:
   ```
   fetch() → Response 객체
             ↓
   res.body (ReadableStream)
             ↓
   createOpenAITextStream() → EventSourceParserStream
             ↓
   AsyncGenerator<TextStreamUpdate>
             ↓
   for await (const update of textStream)
   ```

### 예방

**API 함수 작성 시 체크리스트**:
- [ ] SSE 응답과 JSON 응답을 구분하여 처리
- [ ] `content-type` 헤더 확인 (대소문자 무관)
- [ ] SSE 응답: `Response` 객체 반환 (파싱 X)
- [ ] JSON 응답: `res.json()` 호출 후 파싱된 객체 반환
- [ ] 에러 핸들링 3단계 (fetch, HTTP status, JSON parse)

**디버깅 팁**:
```typescript
// 브라우저 콘솔에서 응답 타입 확인
const res = await fetch('/api/chat/completions', {...});
console.log('Content-Type:', res.headers.get('content-type'));
console.log('Response:', res);

// SSE 응답 확인
if (res.body) {
    const reader = res.body.getReader();
    const { value, done } = await reader.read();
    console.log('First chunk:', new TextDecoder().decode(value));
}
```

### 관련 파일

- `webui/src/lib/apis/openai/index.ts` - OpenAI API 호출 함수 (수정됨)
- `webui/src/lib/apis/streaming/index.ts` - SSE 파싱 로직
- `webui/src/lib/components/chat/Chat.svelte` - 채팅 컴포넌트 (스트리밍 처리)
- `webui/backend/open_webui/routers/openai.py` - Open-WebUI 백엔드 (SSE 응답 전달)
- `.cursor/learnings/openwebui-litellm-integration.md` - LiteLLM 연동 학습 내용

---

**학습 시점**: 2025-11-19  
**해결 시간**: 45분  
**재사용 가능성**: ⭐⭐⭐⭐⭐ (모든 SSE 기반 스트리밍 API 필수)

