# Langfuse 설정 가이드

## 1. Langfuse 웹 UI 접속

브라우저에서 다음 URL로 접속:
```
http://localhost:3003
```

## 2. 계정 생성

1. **Sign Up** 클릭
2. 이메일과 비밀번호로 계정 생성
   - 로컬 환경이므로 실제 이메일 확인은 필요 없음
   - 예시: `admin@localhost`, 비밀번호: `admin123`

## 3. 프로젝트 생성

1. 로그인 후 **New Project** 클릭
2. 프로젝트 이름: `Agent Portal`
3. **Create** 클릭

## 4. API 키 생성

1. 프로젝트 대시보드에서 **Settings** 클릭
2. **API Keys** 탭 선택
3. **Create new API key** 클릭
4. 키 이름: `LiteLLM Gateway`
5. **Create** 클릭
6. 생성된 키 복사:
   - **Public Key**: `pk-lf-...`
   - **Secret Key**: `sk-lf-...`

## 5. .env 파일에 키 추가

`.env` 파일을 열고 다음 변수 추가:

```bash
# Langfuse (Observability)
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGFUSE_HOST=http://langfuse:3000
```

**주의**: 실제 생성한 키로 `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` 부분을 교체하세요.

## 6. LiteLLM 재시작

LiteLLM 서비스를 재시작하여 Langfuse 콜백을 활성화:

```bash
docker-compose restart litellm
```

## 7. 동작 확인

### 7.1 LiteLLM 로그 확인
```bash
docker-compose logs -f litellm
```

정상 연동 시 다음과 같은 로그 확인:
```
Langfuse initialized with host: http://langfuse:3000
```

### 7.2 테스트 요청
```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-235b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

### 7.3 Langfuse 대시보드 확인
1. http://localhost:3003 접속
2. **Traces** 메뉴 클릭
3. 방금 전송한 요청이 트레이스로 기록되었는지 확인

성공 시 다음 정보가 표시됨:
- 요청 시간
- 모델명 (`openrouter/qwen/qwen3-235b-a22b-2507`)
- 입력/출력 메시지
- 토큰 사용량
- 비용 (모델별 가격 정보 기반)
- 레이턴시

## 트러블슈팅

### Langfuse 연결 실패
```
Error: Could not connect to Langfuse
```

**해결**:
1. Langfuse 서비스 상태 확인: `docker-compose ps langfuse`
2. Langfuse 로그 확인: `docker-compose logs langfuse`
3. API 키 확인: .env 파일의 `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`

### 트레이스가 기록되지 않음

**확인 사항**:
1. LiteLLM `success_callback` 설정 확인: `litellm/config.yaml`
2. LiteLLM 로그에서 Langfuse 초기화 메시지 확인
3. Langfuse 프로젝트 ID 확인 (기본 프로젝트 사용 중인지)

## 다음 단계

Langfuse 설정 완료 후:
1. ✅ Backend BFF에서 Langfuse 통합 테스트
2. ✅ Chat API → LiteLLM → OpenRouter → Langfuse E2E 테스트
3. ✅ Monitoring 대시보드에서 실제 데이터 확인
4. ✅ AgentOps SDK 통합 (에이전트 실행 모니터링)

