# LiteLLM 단일 게이트웨이 설정 가이드

**작성일**: 2025-11-19  
**버전**: 1.0  
**담당자**: Agent Portal 개발팀

## 목차

1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [설정 방법](#설정-방법)
4. [사용 가능한 모델](#사용-가능한-모델)
5. [각 컴포넌트 연동](#각-컴포넌트-연동)
6. [트러블슈팅](#트러블슈팅)

---

## 개요

LiteLLM은 Agent Portal의 **단일 LLM 게이트웨이**로, 모든 컴포넌트(Open-WebUI, Langflow, Flowise, LangGraph, Backend BFF)가 OpenAI 호환 방식으로 LLM을 사용할 수 있도록 합니다.

### 핵심 장점

- **단일 설정**: `litellm/config.yaml` 한 곳에서 모든 LLM 모델 관리
- **비용/지연 정책 중앙화**: 라우팅, 폴백, 쿼터, 태깅 일원화
- **관측/모니터링 단일화**: OTEL → ClickHouse로 모든 LLM 호출 추적
- **보안 관점**: Kong을 통한 키 인증, 레이트리밋, mTLS, 감사 로그 중앙화 (선택)

---

## 아키텍처

```
[Langflow]   [Flowise]   [LangGraph]   [Open-WebUI]   [Backend BFF]
     \           |              |               |              /
      \__________|______________|_______________|_____________/
                        (OpenAI 호환)
                   base_url = http://litellm:4000/v1
                       api_key = LITELLM_MASTER_KEY
                   model = 공통 별칭(qwen-235b, gpt-4, ...)
                                 |
                            [LiteLLM]
         ┌──────────────┬───────────────┬───────────────┐
         │OpenRouter    │ vLLM(로컬)    │ Ollama(로컬)  │ ...
         └──────────────┴───────────────┴───────────────┘
```

---

## 설정 방법

### 1. LiteLLM 설정 파일

**위치**: `litellm/config.yaml`

```yaml
# 모델 카탈로그 (별칭 = model_name)
model_list:
  # Primary: OpenRouter (Qwen 235B)
  - model_name: qwen-235b
    litellm_params:
      model: openrouter/qwen/qwen3-235b-a22b-2507
      api_base: https://openrouter.ai/api/v1
      api_key: os.environ/OPENROUTER_API_KEY
  
  # Alias for compatibility
  - model_name: gpt-4
    litellm_params:
      model: openrouter/qwen/qwen3-235b-a22b-2507
      api_base: https://openrouter.ai/api/v1
      api_key: os.environ/OPENROUTER_API_KEY
  
  - model_name: gpt-3.5-turbo
    litellm_params:
      model: openrouter/qwen/qwen3-235b-a22b-2507
      api_base: https://openrouter.ai/api/v1
      api_key: os.environ/OPENROUTER_API_KEY

# General settings
general_settings:
  set_verbose: true
  master_key: os.environ/LITELLM_MASTER_KEY

# Observability: OTEL integration (ClickHouse 기반 모니터링)
litellm_settings:
  callbacks: ["otel"]
  success_callback: ["otel"]
  failure_callback: ["otel"]
```

### 2. 환경 변수 설정

**위치**: `.env`

```bash
# LiteLLM
LITELLM_MASTER_KEY=sk-1234  # 로컬 테스트용

# OpenRouter
OPENROUTER_API_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL_NAME=qwen/qwen3-235b-a22b-2507
```

### 3. Docker Compose 설정

**위치**: `docker-compose.yml`

```yaml
litellm:
  build: ./litellm
  ports:
    - "4000:4000"
  env_file: .env
  environment:
    - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
```

---

## 사용 가능한 모델

| 모델 별칭 | 실제 모델 | 용도 |
|----------|----------|------|
| `qwen-235b` | openrouter/qwen/qwen3-235b-a22b-2507 | 기본 모델 |
| `gpt-4` | openrouter/qwen/qwen3-235b-a22b-2507 | 호환성 별칭 |
| `gpt-3.5-turbo` | openrouter/qwen/qwen3-235b-a22b-2507 | 호환성 별칭 |

**헬스체크**:
```bash
curl http://localhost:4000/health -H "Authorization: Bearer sk-1234" | jq .
```

**모델 목록 조회**:
```bash
curl http://localhost:4000/v1/models -H "Authorization: Bearer sk-1234" | jq '.data[] | {id, created}'
```

---

## 각 컴포넌트 연동

### 1. Open-WebUI

**설정 위치**: `docker-compose.yml`의 `webui` 서비스

```yaml
webui:
  environment:
    - ENABLE_OPENAI_API=true
    - OPENAI_API_BASE_URLS=http://litellm:4000/v1
    - OPENAI_API_KEYS=${LITELLM_MASTER_KEY}
  depends_on:
    - litellm
```

**UI 설정**:
1. `http://localhost:3001/admin/settings` 접속
2. Connections > OpenAI API 활성화
3. Base URL: `http://litellm:4000/v1`
4. API Key: `.env`의 `LITELLM_MASTER_KEY`
5. 사용 가능 모델: `qwen-235b`, `gpt-4`, `gpt-3.5-turbo`

### 2. Backend BFF

**LiteLLM 서비스 클라이언트**: `backend/app/services/litellm_service.py`

```python
from app.services.litellm_service import litellm_service

# 비동기 chat completion
response = await litellm_service.chat_completion_sync(
    model="qwen-235b",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.7
)

# 스트리밍
async for line in litellm_service.chat_completion(
    model="qwen-235b",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
):
    print(line)
```

**Chat API**: `backend/app/routes/chat.py`

```bash
# 비스트리밍
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "gpt-4",
    "stream": false
  }' | jq .

# 스트리밍
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "gpt-4",
    "stream": true
  }'
```

### 3. Langflow

**설정 위치**: `docker-compose.yml`의 `langflow` 서비스

```yaml
langflow:
  environment:
    - LANGFLOW_DEFAULT_OPENAI_BASE_URL=http://litellm:4000/v1
    - LANGFLOW_DEFAULT_OPENAI_API_KEY=${LITELLM_MASTER_KEY}
  depends_on:
    - litellm
```

**사용 방법**:
1. Langflow UI에서 LLM 노드 추가
2. **OpenAI Compatible** 선택
3. Base URL: `http://litellm:4000/v1`
4. API Key: `LITELLM_MASTER_KEY`
5. Model: `qwen-235b` or `gpt-4`

### 4. Flowise

**설정 위치**: `docker-compose.yml`의 `flowise` 서비스

```yaml
flowise:
  environment:
    - OPENAI_API_BASE=http://litellm:4000/v1
    - OPENAI_API_KEY=${LITELLM_MASTER_KEY}
  depends_on:
    - litellm
```

**사용 방법**:
1. Flowise UI에서 Credentials 추가
2. **OpenAI Compatible** 선택
3. Base URL/API Key/Model 별칭 입력

---

## 트러블슈팅

### 문제 1: "Authentication Error, No api key passed in."

**원인**: API 키 헤더 누락

**해결**:
```bash
# ❌ 잘못된 호출
curl http://localhost:4000/health

# ✅ 올바른 호출
curl http://localhost:4000/health -H "Authorization: Bearer sk-1234"
```

### 문제 2: Backend에서 "Failed to connect to LiteLLM"

**원인**: Backend와 LiteLLM 간 네트워크 연결 실패

**해결**:
1. LiteLLM 컨테이너 상태 확인:
   ```bash
   docker-compose ps litellm
   ```
2. LiteLLM 로그 확인:
   ```bash
   docker-compose logs litellm
   ```
3. `backend/app/config.py`에서 `LITELLM_HOST` 확인:
   ```python
   LITELLM_HOST: str = "http://litellm:4000"
   ```

### 문제 3: Docker 빌드 캐시 이슈

**원인**: LiteLLM 설정 파일 변경 후 캐시로 인해 반영되지 않음

**해결**:
```bash
docker-compose build --no-cache litellm
docker-compose up -d litellm
```

---

## 모델 별칭 규약

| 외부 | 내부 | 설명 |
|------|------|------|
| `gpt-4`, `sonnet-35`, `gemini-1.5-pro` | - | 외부 API 별칭 |
| `llama3-70b`, `qwen2.5-32b-ollama`, `mixtral-8x7b-vllm` | - | 내부 로컬 모델 별칭 |
| - | **변경 금지** | 플로우/그래프 재배포 최소화 |

---

## 참고 자료

- [LiteLLM 공식 문서](https://docs.litellm.ai/)
- [OpenRouter API 문서](https://openrouter.ai/docs)

---

**마지막 업데이트**: 2025-11-19  
**버전**: 1.0

