# Langfuse 설정 가이드

> **Langfuse**: LLM 애플리케이션을 위한 오픈소스 관측성 플랫폼 (LLM Tracing & Observability)

## 개요

Langfuse는 **멀티 프로젝트 + SDK 인증 구조**로 설계되어 있어, 최소한 **"어느 프로젝트에 기록할지"를 구분해 줄 식별자**가 필요합니다.

## 설정 절차

### 1. Langfuse 접속 및 계정 생성

```bash
# Langfuse UI 접속
http://localhost:3003
```

- 최초 접속 시 **관리자 계정 생성** (이메일/비밀번호)
- 로그인 후 조직(Organization) 자동 생성됨

### 2. 프로젝트 생성

- 대시보드에서 **"Create New Project"** 클릭
- 프로젝트 이름 입력 (예: `Agent Portal - Development`)
- 프로젝트 ID는 자동 생성됨 (예: `clxxxxxx...`)

### 3. API 키 발급

- 프로젝트 선택 → **Settings > API Keys** 이동
- **Create New Secret Key** 클릭
- **Public Key**와 **Secret Key** 복사

### 4. `.env` 파일 업데이트

프로젝트 루트의 `.env` 파일에 다음 내용을 추가하세요:

```bash
# Langfuse API Keys
LANGFUSE_PUBLIC_KEY=pk-lf-9735e125-fd80-49f4-a4b0-820834dbf97b
LANGFUSE_SECRET_KEY=sk-lf-9487be38-8a0e-454f-b1c4-0bbb4ea8bb1a
LANGFUSE_HOST=http://langfuse:3000  # 컨테이너 내부 통신
LANGFUSE_PROJECT_NAME=agent-portal-dev  # 프로젝트 식별자
LANGFUSE_DATABASE_URL=postgresql://postgres:postgres@langfuse-db:5432/postgres
```

**⚠️ 보안 주의사항**:
- `.env` 파일은 절대 Git에 커밋하지 마세요 (이미 `.gitignore`에 포함됨)
- API 키는 안전하게 보관하세요

### 5. LiteLLM 컨테이너 재빌드 및 재시작

Langfuse 패키지를 LiteLLM에 설치하기 위해 재빌드가 필요합니다:

```bash
# LiteLLM 컨테이너 재빌드 (langfuse 패키지 포함)
docker-compose build --no-cache litellm

# 전체 스택 재시작
docker-compose up -d
```

### 6. 확인

- Langfuse UI 접속: http://localhost:3003
- 프로젝트 대시보드에서 트레이스 확인
- Chat API 호출 시 자동으로 LLM 호출 기록됨

**테스트 방법**:
```bash
# Chat API 호출 테스트
curl -X POST http://localhost:3001/api/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "model": "qwen-235b",
    "stream": true
  }'

# Langfuse UI에서 Traces 탭 확인
# → 방금 호출한 LLM 요청이 기록되어 있어야 함
```

## 멀티 프로젝트 환경 설정

Langfuse는 하나의 인스턴스에서 여러 프로젝트를 지원합니다. 각 프로젝트별로 데이터를 구분하려면:

### 방법 1: 환경 변수로 기본 프로젝트 설정

```bash
# .env
LANGFUSE_PROJECT_NAME=agent-portal-dev  # 프로젝트 이름 (태그용)
```

### 방법 2: LiteLLM config.yaml에서 태그로 구분

```yaml
# litellm/config.yaml
litellm_settings:
  success_callback: ["langfuse"]
  langfuse_public_key: os.environ/LANGFUSE_PUBLIC_KEY
  langfuse_secret_key: os.environ/LANGFUSE_SECRET_KEY
  langfuse_host: http://langfuse:3000
  # 프로젝트 식별 태그 추가
  default_tags:
    - project:agent-portal
    - environment:development
```

### 방법 3: SDK 호출 시 명시적 지정

```python
from langfuse import Langfuse
import os

langfuse = Langfuse(
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    host=os.environ["LANGFUSE_HOST"]
)

# 트레이스 생성 시 프로젝트 메타데이터 추가
trace = langfuse.trace(
    name="agent_execution",
    metadata={
        "project": "agent-portal",
        "environment": "development",
        "component": "langflow"
    }
)
```

## 프로젝트별 API 키 관리

개발/스테이징/프로덕션 환경별로 별도 프로젝트를 생성하고, 각각의 API 키를 사용하는 것을 권장합니다:

```bash
# .env.development
LANGFUSE_PROJECT_NAME=agent-portal-dev
LANGFUSE_PUBLIC_KEY=pk-lf-dev-...
LANGFUSE_SECRET_KEY=sk-lf-dev-...

# .env.staging
LANGFUSE_PROJECT_NAME=agent-portal-staging
LANGFUSE_PUBLIC_KEY=pk-lf-staging-...
LANGFUSE_SECRET_KEY=sk-lf-staging-...

# .env.production
LANGFUSE_PROJECT_NAME=agent-portal-prod
LANGFUSE_PUBLIC_KEY=pk-lf-prod-...
LANGFUSE_SECRET_KEY=sk-lf-prod-...
```

## Langfuse 대시보드 활용

### 1. Traces 뷰

- 모든 LLM 호출 기록 확인
- 프롬프트, 응답, 토큰 수, 비용, 레이턴시 확인
- 필터링: 모델, 날짜, 사용자, 태그 등

### 2. Sessions 뷰

- 사용자별/대화별 세션 추적
- 여러 트레이스를 하나의 세션으로 그룹화

### 3. Users 뷰

- 사용자별 사용량 분석
- 비용 추적 및 리포팅

### 4. Prompts 뷰

- 프롬프트 템플릿 관리
- A/B 테스트 및 버전 관리
- 프로덕션 프롬프트 배포

### 5. Playground

- 프롬프트 실시간 테스트
- 모델 비교 (GPT-4 vs Claude vs Qwen 등)
- 응답 품질 평가

## 트러블슈팅

### 트레이스가 기록되지 않을 때

1. **Langfuse 서비스 상태 확인**:
   ```bash
   docker-compose ps langfuse
   docker-compose logs langfuse
   ```

2. **LiteLLM 로그 확인**:
   ```bash
   docker-compose logs litellm | grep -i langfuse
   ```

3. **API 키 확인**:
   ```bash
   # .env 파일의 키가 올바른지 확인
   docker-compose exec litellm env | grep LANGFUSE
   ```

4. **네트워크 연결 확인**:
   ```bash
   # LiteLLM에서 Langfuse로 연결 테스트
   docker-compose exec litellm curl http://langfuse:3000/api/public/health
   ```

### "Module 'langfuse' not found" 오류

LiteLLM 컨테이너를 재빌드하세요:

```bash
docker-compose build --no-cache litellm
docker-compose up -d litellm
```

### 프로젝트가 구분되지 않을 때

`litellm/config.yaml`에서 `default_tags`를 확인하고, 각 트레이스에 프로젝트 태그가 포함되었는지 Langfuse UI에서 확인하세요.

## 관련 문서

- [Langfuse 공식 문서](https://langfuse.com/docs)
- [LiteLLM Langfuse Integration](https://docs.litellm.ai/docs/observability/langfuse_integration)
- [Agent Portal README.md](../../README.md)

## 다음 단계

- [AgentOps 설정](./AGENTOPS_SETUP.md) - 에이전트 실행 모니터링
- [Helicone 설정](./HELICONE_SETUP.md) - LLM 프록시 및 비용 추적

