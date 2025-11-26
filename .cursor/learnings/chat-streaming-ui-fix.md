# Chat Streaming UI 문제 해결

## 날짜
2025-11-19

## 문제 상황

### 증상
- Chat API는 정상적으로 SSE 스트리밍 응답 반환
- 브라우저에서 `200 OK` 응답 확인
- 하지만 UI에서 스켈레톤 로딩만 표시되고 실제 텍스트가 렌더링되지 않음

### 근본 원인

**스트리밍 응답 처리 로직 누락**:
- `generateOpenAIChatCompletion`이 SSE 응답 시 `Response` 객체 반환
- `Chat.svelte`의 `sendPromptSocket` 함수에서 `res.body` 처리 로직 누락
- 기존 코드는 `res.error`와 `res.task_id`만 체크

### API 응답 확인 (정상)

**Network 탭 확인**:
```
Status: 200 OK
Content-Type: text/event-stream; charset=utf-8

data: {"id":"gen-...","choices":[{"index":0,"delta":{"content":"Hello"}}]}
data: {"id":"gen-...","choices":[{"index":0,"delta":{"content":"!"}}]}
...
data: [DONE]
```

## 해결 방법

### 수정 파일
`webui/src/lib/components/chat/Chat.svelte` (Line 1671-1742)

### 수정 전

```javascript
if (res) {
    if (res.error) {
        await handleOpenAIError(res.error, responseMessage);
    } else {
        if (taskIds) {
            taskIds.push(res.task_id);
        } else {
            taskIds = [res.task_id];
        }
    }
}
```

### 수정 후

```javascript
if (res) {
    // ⚠️ CRITICAL: 스트리밍 응답 처리 (res.body가 있으면 SSE 응답)
    if (res.ok && res.body) {
        // SSE 스트리밍 응답 처리
        try {
            const textStream = await createOpenAITextStream(res.body, $settings.splitLargeChunks);
            for await (const update of textStream) {
                const { value, done, sources, selectedModelId, error, usage } = update;
                
                if (error) {
                    await handleOpenAIError(error, responseMessage);
                    break;
                }
                
                if (done) {
                    break;
                }
                
                if (sources) {
                    responseMessage.sources = sources;
                    history.messages[responseMessageId] = responseMessage;
                    continue;
                }
                
                if (selectedModelId) {
                    responseMessage.selectedModelId = selectedModelId;
                    history.messages[responseMessageId] = responseMessage;
                    continue;
                }
                
                if (usage) {
                    responseMessage.usage = usage;
                    history.messages[responseMessageId] = responseMessage;
                    continue;
                }
                
                if (responseMessage.content == '' && value == '\n') {
                    continue;
                } else {
                    responseMessage.content += value;
                    history.messages[responseMessageId] = responseMessage;
                }
                
                if (autoScroll) {
                    scrollToBottom();
                }
            }
            
            responseMessage.done = true;
            history.messages[responseMessageId] = responseMessage;
            
            await saveChatHandler(_chatId, _history);
        } catch (error) {
            console.error('Streaming error:', error);
            await handleOpenAIError({ message: error.toString() }, responseMessage);
        }
    } else if (res.error) {
        // 에러 응답 처리
        await handleOpenAIError(res.error, responseMessage);
    } else if (res.task_id) {
        // 비스트리밍 응답 처리 (task_id 기반)
        if (taskIds) {
            taskIds.push(res.task_id);
        } else {
            taskIds = [res.task_id];
        }
    }
}
```

## 핵심 원칙

### SSE 스트리밍 응답 처리 (Chat.svelte)

1. **`res.ok && res.body` 체크**:
   - SSE 응답인지 확인
   - `Response` 객체의 `body`가 있으면 스트리밍

2. **`createOpenAITextStream` 사용**:
   - `res.body`를 SSE 파서에 전달
   - `for await` 루프로 스트리밍 처리

3. **`responseMessage.content` 업데이트**:
   - 각 `value`를 누적하여 `responseMessage.content`에 추가
   - `history.messages[responseMessageId]` 업데이트로 UI 반영

4. **`responseMessage.done = true` 설정**:
   - 스트리밍 완료 시 메시지 완료 상태로 변경
   - `saveChatHandler` 호출로 채팅 저장

## 관련 수정 이력

### 1. `generateOpenAIChatCompletion` 수정
- **파일**: `webui/src/lib/apis/openai/index.ts`
- **변경**: SSE 응답 시 `Response` 객체 직접 반환
- **이유**: 프론트엔드에서 `res.body`로 스트리밍 처리

### 2. Open-WebUI 백엔드 수정
- **파일**: `webui/backend/open_webui/routers/openai.py`
- **변경 1**: `data=payload` → `json=payload` (JSON 전송)
- **변경 2**: `json.dumps(payload)` 제거 (이중 인코딩 방지)
- **변경 3**: 헤더 대소문자 확인 (aiohttp는 소문자로 저장)

### 3. Chat.svelte 스트리밍 처리 추가 (이번 수정)
- **파일**: `webui/src/lib/components/chat/Chat.svelte`
- **변경**: `res.body` 처리 로직 추가
- **이유**: SSE 응답을 UI에 렌더링

## 테스트 방법

### 1. 브라우저 하드 새로고침
```
Mac: Cmd + Shift + R
Windows: Ctrl + Shift + R
```

### 2. 새 채팅 시작
1. http://localhost:3001 접속
2. 모델 선택: `qwen-235b`
3. 메시지 전송

### 3. 확인 사항
- ✅ 실시간 스트리밍 응답 (토큰 단위로 출력)
- ✅ 스켈레톤 로딩 → 실제 텍스트로 전환
- ✅ 자동 스크롤
- ✅ 응답 완료 후 채팅 저장

## 예방 체크리스트

### Chat 컴포넌트 수정 시
- [ ] `generateOpenAIChatCompletion` 호출 후 `res.body` 처리 확인
- [ ] `createOpenAITextStream`으로 SSE 파싱
- [ ] `responseMessage.content` 누적 업데이트
- [ ] `responseMessage.done = true` 설정
- [ ] `saveChatHandler` 호출로 채팅 저장

### API 클라이언트 수정 시
- [ ] SSE 응답 시 `Response` 객체 직접 반환
- [ ] JSON 응답 시 `res.json()` 파싱 후 반환
- [ ] `Content-Type` 헤더 확인 (대소문자 무관)

## 참고 자료

- `webui/src/lib/apis/streaming/index.ts`: `createOpenAITextStream` 구현
- `webui/src/lib/components/chat/Chat.svelte`: 채팅 UI 로직
- `webui/backend/open_webui/routers/openai.py`: Open-WebUI 백엔드

