# Perplexica 프록시 본문 전송 문제 - 질문

## 문제 상황

FastAPI BFF에서 Perplexica Next.js 백엔드로 SSE 스트리밍 요청을 프록시할 때, 요청 본문 앞에 예상치 못한 문자가 추가되어 JSON 파싱 에러가 발생합니다.

## 기술 스택

- **프록시 서버**: FastAPI (Python 3.11) + aiohttp 3.13.3
- **대상 서버**: Next.js (Node.js) API Route (`/api/chat`)
- **통신 방식**: SSE (Server-Sent Events) 스트리밍
- **요청 본문**: JSON (Content-Type: application/json)

## 증상

### 1. 프록시에서 보내는 본문
```python
# 프록시 코드 (backend/app/routes/proxy.py)
json_body_str = json.dumps(request_json, ensure_ascii=False)  # 319 chars
json_body_bytes = json_body_str.encode('utf-8')  # 319 bytes

# 헤더 설정
clean_headers['Content-Type'] = 'application/json; charset=utf-8'
clean_headers['Content-Length'] = str(len(json_body_bytes))  # '319'
clean_headers.pop('transfer-encoding', None)
clean_headers.pop('Transfer-Encoding', None)

# aiohttp로 전송
async with session.post(
    perplexica_url,
    data=json_body_bytes,  # bytes 전달
    headers=clean_headers,
    chunked=False  # Content-Length 사용 시 chunked 인코딩 비활성화
) as response:
    ...
```

**프록시 로그 확인**:
```
[PROXY] JSON body length: 319 chars, 319 bytes
[PROXY] Content-Length header set to: 319
[PROXY] JSON body (first 300): {"message": {"messageId": "test", "chatId": "test", "content": "test"}, "optimizationMode": "balanced", "sources": ["web"], "history": [], "files": [], "chatModel": {"providerId": "openai", "key": "qwen2.5-7b-instruct"}, "embeddingModel": {"providerId": "openai", "key": "nomic-embed-text"}, "systemI
```

### 2. Perplexica 백엔드가 받은 본문
**Perplexica 로그**:
```
Body text length: 319
Body text (first 500): 13f
{"message": {"messageId": "test", "chatId": "test", "content": "test"}, "optimizationMode": "balanced", "sources": ["web"], "history": [], "files": [], "chatModel": {"providerId": "openai", "key": "qwen2.5-7b-instruct"}, "embeddingModel": {"providerId": "openai", "key": "nomic-embed-text"}, "systemInstructions": 
```

**에러 메시지**:
```
SyntaxError: Unexpected non-whitespace character after JSON at position 2 (line 1 column 3)
```

### 3. 문제 분석
- 본문 앞에 `13f` 문자가 추가됨
- `13f`는 16진수로 319 (0x13f)를 의미
- 이것은 Content-Length 값 (319)의 16진수 표현으로 보임
- aiohttp가 본문을 전송할 때 Content-Length를 본문 앞에 추가하는 것으로 추정

## 시도한 해결 방법

### 1. `data` 파라미터 사용
```python
async with session.post(
    perplexica_url,
    data=json_body_bytes,  # bytes 직접 전달
    headers=clean_headers,
    chunked=False
) as response:
```

**결과**: `13f` 문자가 여전히 추가됨

### 2. `json` 파라미터 사용
```python
async with session.post(
    perplexica_url,
    json=request_json,  # dict 전달, aiohttp가 자동 직렬화
    headers=clean_headers,
    chunked=False
) as response:
```

**결과**: 동일한 문제 발생

### 3. Content-Length 헤더 제거
```python
clean_headers.pop('Content-Length', None)
# aiohttp가 자동으로 계산하도록 함
```

**결과**: 동일한 문제 발생

### 4. `chunked=True`로 변경
```python
async with session.post(
    perplexica_url,
    data=json_body_bytes,
    headers=clean_headers,
    chunked=True  # Transfer-Encoding: chunked 사용
) as response:
```

**결과**: 동일한 문제 발생

## 현재 코드 구조

### 프록시 함수 (FastAPI)
```python
@router.api_route("/perplexica/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_perplexica_api(path: str, request: Request) -> Response:
    perplexica_url = f"http://perplexica:3000/api/{path}"
    
    # 요청 본문 읽기
    body = await request.body()
    request_json = json.loads(body)
    
    # SSE 스트리밍 처리
    if path == "chat" and request.method == "POST":
        async def event_generator():
            timeout = ClientTimeout(total=None, connect=30, sock_read=None)
            connector = aiohttp.TCPConnector(
                limit=100,
                enable_cleanup_closed=True,
                force_close=False
            )
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            ) as session:
                # 헤더 정리
                clean_headers = {}
                safe_headers = ['accept', 'accept-language', 'user-agent', 'origin', 'referer']
                for key, value in request.headers.items():
                    key_lower = key.lower()
                    if key_lower in safe_headers:
                        clean_headers[key] = value
                
                clean_headers['Accept'] = 'text/event-stream, application/json, */*'
                
                # JSON 본문 직렬화
                json_body_str = json.dumps(request_json, ensure_ascii=False)
                json_body_bytes = json_body_str.encode('utf-8')
                
                # Content-Type과 Content-Length 설정
                clean_headers['Content-Type'] = 'application/json; charset=utf-8'
                clean_headers['Content-Length'] = str(len(json_body_bytes))
                clean_headers.pop('transfer-encoding', None)
                clean_headers.pop('Transfer-Encoding', None)
                
                # aiohttp로 전송
                async with session.post(
                    perplexica_url,
                    data=json_body_bytes,
                    headers=clean_headers,
                    params=dict(request.query_params) if request.query_params else None,
                    chunked=False
                ) as response:
                    # 청크 단위로 스트리밍
                    async for chunk in response.content.iter_any():
                        if chunk:
                            yield chunk
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )
```

### Perplexica 백엔드 (Next.js)
```typescript
// perplexica/src/app/api/chat/route.ts
export const POST = async (req: Request) => {
  try {
    // 문서 9.6절 방법 1: req.json() 대신 req.text() 사용 후 수동 파싱
    const bodyText = await req.text();
    let reqBody: Body;
    try {
      reqBody = JSON.parse(bodyText) as Body;
    } catch (parseError) {
      console.error('JSON parse error:', parseError);
      console.error('Body text length:', bodyText.length);
      console.error('Body text (first 500):', bodyText.substring(0, 500));
      console.error('Body text (last 200):', bodyText.substring(Math.max(0, bodyText.length - 200)));
      throw parseError;
    }
    // ... 나머지 처리
  }
}
```

## 질문

1. **왜 aiohttp가 본문 앞에 `13f` (Content-Length의 16진수)를 추가하는가?**
   - 이것은 aiohttp의 버그인가, 아니면 설정 문제인가?
   - `chunked=False`와 명시적 `Content-Length` 설정이 충돌하는가?

2. **aiohttp로 bytes 본문을 전송할 때 올바른 방법은 무엇인가?**
   - `data=json_body_bytes` vs `json=request_json`
   - Content-Length를 명시적으로 설정해야 하는가?
   - `chunked=False`가 올바른 설정인가?

3. **Next.js의 `req.text()`가 본문을 읽을 때 추가 문자를 포함하는 이유는 무엇인가?**
   - 이것은 Next.js의 문제인가, 아니면 프록시에서 보낸 본문의 문제인가?

4. **대안적인 해결 방법은 무엇인가?**
   - httpx로 다시 전환? (이전에 `httpx.StreamClosed` 에러 발생)
   - 다른 HTTP 클라이언트 라이브러리 사용?
   - 프록시 구조 자체를 변경?

## 환경 정보

- **Python**: 3.11
- **FastAPI**: 0.109.0
- **aiohttp**: 3.13.3
- **Next.js**: 14.x (Perplexica 백엔드)
- **Docker**: 컨테이너 간 통신 (BFF → Perplexica)

## 추가 정보

- 프록시는 Docker 네트워크 내에서 `http://perplexica:3000`로 요청 전송
- 직접 curl로 Perplexica에 요청하면 정상 동작 (프록시 없이)
- 프록시를 통한 요청에서만 `13f` 문자가 추가됨

## 참고 문서

- `docs/PERPLEXICA_STREAMING_ISSUE.md`: 전체 이슈 문서
- `backend/app/routes/proxy.py`: 프록시 구현 코드

