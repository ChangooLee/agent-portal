# Open-WebUI + LiteLLM 통합 학습 내용

## 2025-11-19: Open-WebUI에서 LiteLLM 연동 시 JSON 파싱 오류 해결

### 문제 상황

**증상**:
- 프론트엔드에서 `SyntaxError: Unexpected token 'd', "data: {"id"... is not valid JSON` 에러 발생
- Open-WebUI 채팅 화면에서 LiteLLM을 통한 응답 실패
- 백엔드 로그에서는 200 OK 응답

**근본 원인**:
- `webui/backend/open_webui/routers/openai.py` (line 703)에서 `data=payload` 사용
- aiohttp에서 `data` 파라미터에 딕셔너리를 전달하면 form-data로 인코딩됨
- LiteLLM은 JSON 요청을 기대하므로 파싱 오류 발생

### 해결 방법

**문제 1: `data=payload` → `json=payload` 변경**:

수정 전:
```python
r = await session.request(
    method="POST",
    url=f"{url}/chat/completions",
    data=payload,  # ❌ form-data로 인코딩됨
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        ...
    },
)
```

수정 후:
```python
r = await session.request(
    method="POST",
    url=f"{url}/chat/completions",
    json=payload,  # ✅ JSON으로 직렬화됨
    headers={
        "Authorization": f"Bearer {key}",
        # Content-Type은 자동 설정됨
        ...
    },
)
```

**문제 2: `payload = json.dumps(payload)` 제거**:

수정 전 (line 688):
```python
payload = json.dumps(payload)  # ❌ 딕셔너리 → 문자열 변환

r = await session.request(
    method="POST",
    url=f"{url}/chat/completions",
    json=payload,  # ❌ 문자열을 json 파라미터에 전달
    ...
)
```

수정 후:
```python
# Note: payload remains as dict for aiohttp's json parameter
# ✅ 딕셔너리 상태 유지

r = await session.request(
    method="POST",
    url=f"{url}/chat/completions",
    json=payload,  # ✅ 딕셔너리를 json 파라미터에 전달
    ...
)
```

**문제 3: aiohttp 헤더 대소문자 구분 (스트리밍 응답 감지 실패)**:

수정 전 (line 728):
```python
# Check if response is SSE
if "text/event-stream" in r.headers.get("Content-Type", ""):
    # ❌ aiohttp는 헤더를 소문자로 저장 (content-type)
    streaming = True
    return StreamingResponse(...)
else:
    # ✅ 스트리밍 응답인데도 else 블록으로 감
    response = await r.json()  # SSE를 JSON으로 파싱 시도 → 실패
    # 또는
    response = await r.text()  # SSE 텍스트 전체를 문자열로 반환
    return response  # 프론트엔드가 SSE 텍스트를 JSON.parse() 시도 → 에러!
```

수정 후:
```python
# Check if response is SSE (case-insensitive header check)
content_type = r.headers.get("content-type", "") or r.headers.get("Content-Type", "")
# ✅ 대소문자 모두 확인
if "text/event-stream" in content_type:
    streaming = True
    return StreamingResponse(
        r.content,  # ✅ SSE 스트림을 그대로 전달
        status_code=r.status,
        headers=dict(r.headers),
        ...
    )
```

### 핵심 원칙

1. **aiohttp JSON 전송**:
   - `data` 파라미터: raw bytes 또는 form-data
   - `json` 파라미터: 자동 JSON 직렬화 + Content-Type 설정
   - **LLM API 호출 시 항상 `json` 파라미터 사용**
   - **`json` 파라미터에는 딕셔너리 전달 (문자열 X)**

2. **aiohttp 헤더 대소문자 구분**:
   - aiohttp는 HTTP 헤더를 **소문자로 저장** (`content-type`, `content-length` 등)
   - `r.headers.get("Content-Type")` → ❌ 빈 문자열 반환
   - `r.headers.get("content-type")` → ✅ 정상 반환
   - **권장**: 대소문자 모두 확인 (`r.headers.get("content-type", "") or r.headers.get("Content-Type", "")`)

3. **Open-WebUI 데이터베이스 설정**:
   - SQLite 데이터베이스: `/app/backend/data/webui.db`
   - `config` 테이블에 JSON 형식으로 설정 저장
   - `openai.enable = true`, `openai.api_base_urls`, `openai.api_keys` 필드

4. **LiteLLM 연동 체크리스트**:
   - [ ] LiteLLM `config.yaml`에 모델 카탈로그 정의
   - [ ] Open-WebUI 데이터베이스에 LiteLLM 연결 정보 삽입
   - [ ] aiohttp 요청에 `json` 파라미터 사용 (딕셔너리 전달)
   - [ ] `json.dumps()` 사용하지 않기 (aiohttp가 자동 처리)
   - [ ] Authorization 헤더에 `LITELLM_MASTER_KEY` 설정
   - [ ] 스트리밍 응답 감지: `content-type` 헤더 확인 (소문자)

### 예방

**Open-WebUI 커스터마이징 시**:
- 외부 LLM API 호출 시 항상 `json` 파라미터 사용
- `data` 파라미터는 파일 업로드/form-data 전용
- Content-Type 헤더 수동 설정 불필요 (aiohttp가 자동 처리)

**테스트 방법**:
```bash
# Open-WebUI 프론트엔드에서 채팅 테스트
1. http://localhost:3000 접속
2. 새 채팅 시작
3. 모델 선택: qwen-235b, gpt-4, gpt-3.5-turbo
4. "Hello, test!" 메시지 전송
5. 응답 확인
```

### 참고 파일

- `webui/backend/open_webui/routers/openai.py` (line 700-726)
- `scripts/setup-openwebui-litellm.sh` (데이터베이스 설정 자동화)
- `litellm/config.yaml` (모델 카탈로그)

---

**학습 시점**: 2025-11-19  
**해결 시간**: 15분  
**재사용 가능성**: ⭐⭐⭐⭐⭐ (Open-WebUI + 외부 LLM API 통합 시 필수)

