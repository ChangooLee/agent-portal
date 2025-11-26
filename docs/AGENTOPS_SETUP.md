# AgentOps Self-Hosting Setup Guide

## Overview

Agent Portal은 **AgentOps self-hosted 인스턴스**를 사용하여 완전히 폐쇄망 환경에서 LLM 호출 모니터링을 수행합니다.

```
LiteLLM → (AgentOps SDK/콜백) → AgentOps API → AgentOps Dashboard
                                      ↓
                                 ClickHouse (메트릭 저장)
                                      ↓
                                 Supabase (인증/DB)
```

## Architecture

### 서비스 구성

| 서비스 | 포트 | 역할 | 의존성 |
|--------|------|------|--------|
| **AgentOps API** | 8003 | LLM 호출 데이터 수집 API | Supabase, ClickHouse |
| **AgentOps Dashboard** | 3006 | 웹 대시보드 (API 키 발급) | AgentOps API |
| **Supabase** | 54321 | 인증 및 메타데이터 DB | PostgreSQL |
| **ClickHouse** | 9000 | 메트릭 데이터 저장소 | - |

### 데이터 흐름

1. **LiteLLM** → AgentOps SDK로 LLM 호출 데이터 전송
2. **AgentOps API** → ClickHouse에 메트릭 저장
3. **AgentOps Dashboard** → API를 통해 데이터 조회 및 시각화
4. **Admin** → Dashboard에서 API 키 생성/관리

---

## Quick Start (Automated Setup - 권장)

### 자동 스크립트로 API 키 생성 및 설정

가장 빠르고 간편한 방법입니다. 스크립트가 다음을 자동으로 수행합니다:
1. AgentOps 사용자 생성
2. 자동 생성된 API 키 추출
3. `.env` 파일에 API 키 추가
4. LiteLLM 재시작

```bash
# 스크립트 실행
./scripts/setup-agentops-apikey.sh
```

**출력 예시**:
```
🔐 AgentOps API Key 자동 설정
================================
1️⃣  사용자 생성 중...
✅ 사용자 생성 성공

2️⃣  API 키 추출 중...
✅ API 키 추출 성공: 12345678-1234-1234-1234-123456789abc

3️⃣  .env 파일 업데이트 중...
✅ AGENTOPS_API_KEY 추가 완료

4️⃣  LiteLLM 재시작 중...
✅ LiteLLM 재시작 완료

🎉 AgentOps API Key 설정 완료!
   Email: admin@agent-portal.local
   API Key: 12345678-1234-1234-1234-123456789abc

📋 다음 단계:
   1. AgentOps Dashboard 접속: http://localhost:3006
   2. 위 이메일/비밀번호로 로그인
   3. LiteLLM 테스트: curl http://localhost:4000/chat/completions ...
```

**생성된 계정 정보**:
- Email: `admin@agent-portal.local`
- Password: `agentops-admin-password`

이제 [LiteLLM 연동 확인](#litellm-연동-확인) 섹션으로 이동하여 테스트를 진행하세요.

---

## Manual Setup (Optional - 수동 설정)

자동 스크립트를 사용하지 않고 수동으로 설정하려면 아래 단계를 따르세요.

### 1. 환경 변수 설정

`.env` 파일에 다음 추가:

```bash
# AgentOps Self-Hosted Configuration
AGENTOPS_API_KEY=              # 비워두고, 대시보드에서 생성 후 입력
AGENTOPS_API_ENDPOINT=http://agentops-api:8003
AGENTOPS_APP_URL=http://localhost:3006
AGENTOPS_EXPORTER_ENDPOINT=http://otel-collector:4318/v1/traces

# Supabase (AgentOps 인증/DB)
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_HOST=supabase-db
SUPABASE_PORT=5432
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=your-super-secret-and-long-postgres-password
SUPABASE_MAX_POOL_SIZE=10
SUPABASE_SSLMODE=disable

# ClickHouse (AgentOps 메트릭 저장)
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DATABASE=agentops
CLICKHOUSE_SECURE=false

# JWT Secret (AgentOps API)
JWT_SECRET_KEY=your-jwt-secret-key-change-this-in-production
```

### 2. AgentOps 서비스 시작

```bash
# AgentOps 및 의존성 서비스 시작
docker-compose up -d supabase clickhouse agentops-api agentops-dashboard

# 로그 확인
docker-compose logs -f agentops-api agentops-dashboard
```

### 3. 대시보드 접속 및 계정 생성

1. 브라우저에서 **http://localhost:3006** 접속
2. **Sign Up**으로 계정 생성 (첫 계정이 관리자)
3. 로그인 완료

### 4. API 키 발급

#### 4-1. 대시보드에서 API 키 생성

1. 대시보드 우측 상단 **프로필 아이콘** 클릭
2. **Settings** 또는 **API Keys** 메뉴 선택
3. **Create API Key** / **New API Key** 버튼 클릭
4. API 키 정보 입력:
   - **Name**: `internal-prod` (또는 원하는 이름)
   - **Role**: Full access (기본값)
   - **Expiration**: None (또는 충분히 긴 기간)
5. 생성된 키를 **복사** (한 번만 표시됨!)

#### 4-2. 발급받은 키를 .env에 추가

```bash
# .env 파일 수정
AGENTOPS_API_KEY=ao-xxx-your-generated-key-xxx
```

#### 4-3. LiteLLM 재시작

```bash
# LiteLLM 재시작하여 API 키 적용
docker-compose restart litellm
```

---

## LiteLLM 연동 확인

### 5. 테스트 요청 전송

```bash
# LiteLLM에 테스트 요청
curl -X POST http://localhost:4000/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-1234" \
  -d '{
    "model": "qwen-235b",
    "messages": [{"role": "user", "content": "Hello, AgentOps test"}],
    "max_tokens": 20
  }'
```

### 6. AgentOps 대시보드에서 확인

1. **http://localhost:3006** 접속
2. 좌측 사이드바에서 **Sessions** 또는 **Traces** 메뉴 클릭
3. 방금 전송한 요청이 표시되는지 확인

---

## Troubleshooting

### API 키가 작동하지 않음

**증상**: LiteLLM 로그에 `401 Unauthorized` 에러

**해결**:
1. `.env`에서 `AGENTOPS_API_KEY`가 올바른지 확인
2. AgentOps API 엔드포인트가 올바른지 확인:
   ```bash
   curl http://localhost:8003/health
   ```
3. LiteLLM 재시작:
   ```bash
   docker-compose restart litellm
   ```

### Dashboard에 데이터가 표시되지 않음

**증상**: 대시보드는 열리지만 데이터가 비어있음

**해결**:
1. ClickHouse가 정상 실행 중인지 확인:
   ```bash
   docker-compose logs clickhouse
   ```
2. AgentOps API 로그 확인:
   ```bash
   docker-compose logs agentops-api
   ```
3. OTEL Collector가 실행 중인지 확인:
   ```bash
   docker-compose ps otel-collector
   ```

### Supabase 연결 오류

**증상**: 대시보드에서 로그인 불가

**해결**:
1. Supabase 서비스 상태 확인:
   ```bash
   docker-compose logs supabase
   ```
2. `.env`에서 Supabase 설정 확인
3. Supabase 재시작:
   ```bash
   docker-compose restart supabase
   ```

---

## Production 배포 시 고려사항

### 1. 보안

- **JWT_SECRET_KEY**: 랜덤 문자열로 변경 필수
- **Supabase 패스워드**: 강력한 패스워드로 변경
- **ClickHouse 패스워드**: 패스워드 설정 권장

### 2. 스토리지

ClickHouse 데이터 영속화:

```yaml
volumes:
  clickhouse_data:
    driver: local

services:
  clickhouse:
    volumes:
      - clickhouse_data:/var/lib/clickhouse
```

### 3. 네트워크

완전 폐쇄망 환경:

```bash
# 외부 인터넷 연결 차단
docker network create --internal agentops-internal

# docker-compose.yml에 네트워크 추가
networks:
  default:
    name: agentops-internal
    external: false
```

---

## Reference

- [AgentOps GitHub](https://github.com/AgentOps-AI/agentops)
- [AgentOps Self-Hosting Guide](https://github.com/AgentOps-AI/agentops/tree/main/app)
- [LiteLLM + AgentOps Integration](https://docs.litellm.ai/docs/observability/agentops_integration)

---

## 다음 단계

AgentOps 설정이 완료되면 다음 단계로 진행하세요:

1. **Langflow → LangGraph 변환** (Phase 1-B)
2. **LangGraph 실행 시 AgentOps 자동 추적**
3. **모니터링 대시보드에서 실시간 데이터 확인**

자세한 내용은 [MONITORING_SETUP.md](./MONITORING_SETUP.md)를 참조하세요.

