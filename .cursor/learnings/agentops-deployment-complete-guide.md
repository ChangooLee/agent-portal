# AgentOps Self-Hosted 완전 기동 가이드

**작성일**: 2025-11-21  
**목적**: AgentOps Self-Hosted 인스턴스를 로컬에서 완전히 기동하고 설정하는 전 과정 문서화

## 목차

1. [개요](#개요)
2. [전체 아키텍처](#전체-아키텍처)
3. [사전 준비 사항](#사전-준비-사항)
4. [단계별 기동 절차](#단계별-기동-절차)
5. [문제 해결](#문제-해결)
6. [LiteLLM 연동](#litellm-연동)
7. [학습 내용](#학습-내용)

---

## 개요

AgentOps는 Self-Hosted 방식으로 운영되며, 다음 컴포넌트로 구성됩니다:

- **Supabase**: 인증 및 PostgreSQL 데이터베이스
- **ClickHouse**: 시계열 트레이스 데이터 저장 (선택적)
- **AgentOps API**: FastAPI 백엔드 (포트 8003)
- **AgentOps Dashboard**: Next.js 프론트엔드 (포트 3006)
- **OpenTelemetry Collector**: 트레이스 수집 (선택적)

**핵심**: Supabase만으로도 기본 기능은 모두 사용 가능합니다.

---

## 전체 아키텍처

### 현재 구성 (2025-11-25 업데이트)

```
┌─────────────────────────────────────────────────────────────────┐
│                    AgentOps Self-Hosted                         │
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │   LiteLLM    │─────▶│    OTEL      │─────▶│  ClickHouse  │  │
│  │   (4000)     │      │  Collector   │      │   (Traces)   │  │
│  └──────────────┘      │  (4317/4318) │      └──────┬───────┘  │
│                        └──────────────┘             │          │
│                                                     │          │
│  ┌──────────────┐      ┌──────────────┐             │          │
│  │  Supabase    │◀─────│  AgentOps    │◀────────────┘          │
│  │  PostgreSQL  │      │     API      │                        │
│  │  (Sessions,  │      │   (8003)     │                        │
│  │   Users)     │      └──────┬───────┘                        │
│  └──────────────┘             │                                │
│                               │                                │
│                        ┌──────▼───────┐                        │
│                        │  AgentOps    │                        │
│                        │  Dashboard   │                        │
│                        │   (3006)     │                        │
│                        └──────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

**데이터 플로우**:
1. LiteLLM이 OpenTelemetry callback으로 trace 생성
2. OTEL Collector가 traces를 수신 (OTLP gRPC/HTTP)
3. ClickHouse에 traces 저장 (`otel_2.otel_traces` 테이블)
4. AgentOps API가 ClickHouse 또는 Supabase에서 데이터 조회
5. AgentOps Dashboard가 API를 통해 traces 시각화

### 레거시 아키텍처 (참고용)

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Portal                             │
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   LiteLLM    │─────▶│  AgentOps    │                    │
│  │   (4000)     │      │  API (8003)  │                    │
│  └──────────────┘      └──────┬───────┘                    │
│                               │                             │
│  ┌──────────────┐      ┌──────▼───────┐                    │
│  │  Backend BFF │─────▶│   Supabase   │                    │
│  │   (8000)     │      │  PostgreSQL  │                    │
│  └──────────────┘      │   (55432)    │                    │
│                        └──────────────┘                     │
│  ┌──────────────┐                                           │
│  │  Frontend    │      ┌──────────────┐                    │
│  │   (3001)     │─────▶│  AgentOps    │                    │
│  └──────────────┘      │  Dashboard   │                    │
│                        │   (3006)     │                    │
│                        └──────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 사전 준비 사항

### 1. 필수 도구

- **Docker Desktop**: 최신 버전
- **Node.js**: v20 이상
- **Supabase CLI**: v1.200.0 이상
- **Python**: 3.11 이상 (AgentOps API 실행 시)

### 2. Supabase CLI 설치

```bash
# npm으로 설치 (권장)
npm install -g supabase

# 또는 Homebrew (macOS)
brew install supabase/tap/supabase

# 설치 확인
supabase --version
```

### 3. Git Submodule 초기화

```bash
cd /Users/lchangoo/Workspace/agent-portal
git submodule update --init --recursive
```

---

## 단계별 기동 절차

### Phase 1: Supabase 시작

#### 1-1. Supabase 로컬 인스턴스 시작

```bash
cd /Users/lchangoo/Workspace/agent-portal/external/agentops/app
supabase start
```

**예상 출력**:
```
supabase local development setup is running.

         API URL: http://127.0.0.1:55321
     GraphQL URL: http://127.0.0.1:55321/graphql/v1
  S3 Storage URL: http://127.0.0.1:55321/storage/v1/s3
    Database URL: postgresql://postgres:postgres@127.0.0.1:55432/postgres
      Studio URL: http://127.0.0.1:55323
 Publishable key: sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH
      Secret key: sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz
```

**중요**: 이 키들은 `.env` 파일에 자동으로 설정되어 있습니다.

#### 1-2. Supabase Studio 접속 (선택적)

브라우저에서 http://127.0.0.1:55323 접속하여 데이터베이스 확인 가능합니다.

---

### Phase 2: 계정 및 프로젝트 생성

#### 2-1. 자동 스크립트 실행 (권장)

```bash
cd /Users/lchangoo/Workspace/agent-portal
./scripts/setup-agentops-apikey.sh
```

**스크립트 실행 결과**:
```
🔐 AgentOps API Key 자동 설정
================================
1️⃣  Supabase 상태 확인 중...
✅ Supabase 실행 중

2️⃣  사용자, 조직, 프로젝트 생성 중...
✅ 데이터 생성 완료

3️⃣  API 키 및 프로젝트 ID 추출 중...
✅ 추출 성공
   Project ID: 94909765-19bf-475a-b7da-d448ab90d072
   API Key: 0c26af2a-8bac-4809-8b30-433ae3850608

4️⃣  .env 파일 업데이트 중...
✅ AGENTOPS_API_KEY 업데이트 완료

5️⃣  Backend BFF 재시작 중...
✅ Backend 재시작 완료

🎉 AgentOps 설정 완료!
```

**생성된 정보**:
- Email: `admin@agent-portal.local`
- Password: `agentops-admin-password`
- Project: `agent-portal`
- Project ID: `94909765-19bf-475a-b7da-d448ab90d072`
- API Key: `0c26af2a-8bac-4809-8b30-433ae3850608`

#### 2-2. 수동 SQL 실행 (대안)

```bash
cd /Users/lchangoo/Workspace/agent-portal

# Supabase PostgreSQL에 SQL 직접 실행
docker exec supabase_db_agentops psql -U postgres -d postgres -f scripts/setup-agentops.sql
```

---

### Phase 3: AgentOps API 시작 (선택적)

AgentOps API는 **v4 REST API 엔드포인트**를 제공합니다. 현재는 **Backend BFF가 직접 Supabase에 접근**하므로 선택적입니다.

#### 3-1. API 디렉토리로 이동

```bash
cd /Users/lchangoo/Workspace/agent-portal/external/agentops/app/api
```

#### 3-2. 가상 환경 설정 및 의존성 설치

```bash
# uv 사용 (권장)
uv sync

# 또는 pip 사용
python -m venv venv
source venv/bin/activate
pip install -e .
```

#### 3-3. 환경 변수 설정

```bash
# app/.env 파일 확인
cat ../env | grep -E "SUPABASE|DATABASE"
```

**필수 환경 변수**:
- `SUPABASE_URL=http://127.0.0.1:55321`
- `SUPABASE_KEY=sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz`
- `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55432/postgres`

#### 3-4. API 서버 시작

```bash
# uv 사용
uv run python run.py

# 또는 pip 사용
python run.py
```

**예상 출력**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8003
```

#### 3-5. API 헬스 체크

```bash
curl http://localhost:8003/health
# 출력: {"status": "ok"}
```

---

### Phase 4: AgentOps Dashboard 시작 (선택적)

#### 4-1. Dashboard 디렉토리로 이동

```bash
cd /Users/lchangoo/Workspace/agent-portal/external/agentops/app/dashboard
```

#### 4-2. 의존성 설치

```bash
# npm 사용
npm install

# 또는 bun 사용 (더 빠름)
bun install
```

#### 4-3. 환경 변수 확인

```bash
cat ../.env | grep -E "NEXT_PUBLIC"
```

**필수 환경 변수**:
- `NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:55321`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH`
- `NEXT_PUBLIC_API_URL=http://localhost:8003`

#### 4-4. 개발 서버 시작

```bash
# npm 사용
npm run dev

# 또는 bun 사용
bun dev
```

**예상 출력**:
```
- ready started server on 0.0.0.0:3006
- event compiled client and server successfully in 2.3s
- Local:        http://localhost:3006
```

#### 4-5. Dashboard 접속

브라우저에서 http://localhost:3006 접속

**로그인 정보**:
- Email: `admin@agent-portal.local`
- Password: `agentops-admin-password`

---

## 문제 해결

### 문제 1: ClickHouse 포트 9000 충돌

**증상**:
```
Error: Bind for 0.0.0.0:9000 failed: port is already allocated
```

**원인**: MinIO가 포트 9000 사용 중

**해결**:
1. **방법 1**: ClickHouse 건너뛰기 (권장)
   - Supabase만으로도 기본 기능은 모두 사용 가능
   - 트레이스 저장은 PostgreSQL 사용

2. **방법 2**: ClickHouse 포트 변경
   ```yaml
   # external/agentops/app/compose.yaml
   clickhouse:
     ports:
       - "9001:9000"  # 9000 → 9001로 변경
   ```

### 문제 2: OpenTelemetry Collector 경로 오류

**증상**:
```
unable to prepare context: path "/Users/.../opentelemetry-collector/opentelemetry-collector" not found
```

**원인**: OpenTelemetry Collector 디렉토리 누락

**해결**:
- OTEL Collector는 선택적 컴포넌트
- 기본 기능에는 영향 없음
- 필요 시 AgentOps 저장소에서 해당 디렉토리 복사

### 문제 3: Supabase CLI 미설치

**증상**:
```
supabase: command not found
```

**해결**:
```bash
npm install -g supabase
```

### 문제 4: Backend BFF 연결 실패

**증상**: Monitoring 화면에서 "No data available"

**확인 사항**:
1. Supabase 실행 중인지 확인:
   ```bash
   docker ps | grep supabase
   ```

2. `.env` 파일에 `AGENTOPS_API_KEY` 설정 확인:
   ```bash
   grep AGENTOPS_API_KEY .env
   ```

3. Backend 재시작:
   ```bash
   docker-compose restart backend
   ```

---

## LiteLLM 연동

### 현재 상태

LiteLLM은 `litellm/config.yaml`에서 AgentOps 콜백이 **주석 처리**되어 있습니다:

```yaml
# litellm/config.yaml
litellm_settings:
  success_callback: ["langfuse"]  # ❌ AgentOps 미포함
```

### 연동 방법

#### 1. LiteLLM 설정 업데이트

```yaml
# litellm/config.yaml
litellm_settings:
  success_callback: ["langfuse", "agentops"]
  agentops_api_key: os.environ/AGENTOPS_API_KEY
  agentops_endpoint: os.environ/AGENTOPS_API_ENDPOINT
  agentops_app_url: os.environ/AGENTOPS_APP_URL
```

#### 2. 환경 변수 설정

```bash
# .env 파일에 추가
AGENTOPS_API_KEY=0c26af2a-8bac-4809-8b30-433ae3850608
AGENTOPS_API_ENDPOINT=http://host.docker.internal:8003
AGENTOPS_APP_URL=http://localhost:3006
```

#### 3. LiteLLM 재시작

```bash
docker-compose restart litellm
```

#### 4. 연동 테스트

```bash
# LiteLLM Chat Completion 호출
curl -X POST http://localhost:4000/chat/completions \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen/qwen3-235b-a22b-2507",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# AgentOps Dashboard 확인
# http://localhost:3006 → 트레이스 데이터 확인
```

---

## ClickHouse + OpenTelemetry 통합 (2025-11-25 추가)

### 개요

LiteLLM에서 생성된 traces를 OpenTelemetry Collector를 통해 ClickHouse에 저장하고, AgentOps API와 Dashboard에서 조회할 수 있습니다.

### 아키텍처

```
┌────────────────────────────────────────────────────────┐
│              Trace Collection Pipeline                 │
│                                                        │
│  LiteLLM (4000)                                        │
│       ↓ OpenTelemetry callback                         │
│       ↓ Generates traces/spans                         │
│       ↓                                                │
│  OTEL Collector (4317 gRPC / 4318 HTTP)               │
│       ↓ Receives OTLP traces                           │
│       ↓ Processes & transforms                         │
│       ↓                                                │
│  ClickHouse (9002 native / 8124 HTTP)                 │
│       ↓ Stores in otel_2.otel_traces                   │
│       ↑                                                │
│  AgentOps API (8003) OR Backend BFF (8000)            │
│       ↑ Queries traces via SQL                         │
│       ↑                                                │
│  AgentOps Dashboard (3006) OR Open-WebUI (3001)       │
│       Visualizes traces                                │
└────────────────────────────────────────────────────────┘
```

### ClickHouse 테이블 구조

**테이블**: `otel_2.otel_traces`

**주요 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `Timestamp` | DateTime64(9) | Trace 생성 시간 (나노초 정밀도) |
| `TraceId` | String | Trace ID (16진수) |
| `SpanId` | String | Span ID (16진수) |
| `ParentSpanId` | String | 부모 Span ID |
| `ServiceName` | LowCardinality(String) | 서비스 이름 (예: `litellm-proxy`) |
| `SpanName` | LowCardinality(String) | Span 이름 (예: `litellm_request`) |
| `SpanKind` | LowCardinality(String) | Span 종류 (SERVER, CLIENT 등) |
| `Duration` | Int64 | Duration (나노초) |
| `StatusCode` | LowCardinality(String) | 상태 코드 (Ok, Error 등) |
| `SpanAttributes` | Map(LowCardinality(String), String) | Span 속성 (key-value) |
| `ResourceAttributes` | Map(LowCardinality(String), String) | 리소스 속성 |

**SpanAttributes 주요 키** (LiteLLM 호출 시):
- `gen_ai.request.model`: 사용된 모델 이름
- `gen_ai.prompt.0.content`: 프롬프트 내용
- `gen_ai.completion.0.content`: 응답 내용
- `gen_ai.usage.prompt_tokens`: Prompt 토큰 수
- `gen_ai.usage.completion_tokens`: Completion 토큰 수
- `gen_ai.usage.total_tokens`: 총 토큰 수
- `hidden_params`: 비용, 캐시 키 등 메타데이터

### OTEL Collector 설정

**설정 파일**: `config/otel-collector-config.yaml`

#### Receivers

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
```

- LiteLLM이 gRPC (4317) 또는 HTTP (4318)로 traces 전송
- 환경 변수: `OTEL_EXPORTER_OTLP_ENDPOINT=http://agentops-otel-collector:4318`

#### Processors

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
  
  batch:
    send_batch_size: 10000
    timeout: 10s
  
  resource:
    attributes:
      - key: service.name
        value: litellm-proxy
        action: upsert
```

- `memory_limiter`: 메모리 사용량 제한
- `batch`: 배치 처리로 성능 향상
- `resource`: 리소스 속성 추가/수정

#### Exporters

```yaml
exporters:
  clickhouse/otel_traces:
    endpoint: ${CLICKHOUSE_ENDPOINT}
    username: ${CLICKHOUSE_USERNAME}
    password: ${CLICKHOUSE_PASSWORD}
    database: ${CLICKHOUSE_DATABASE}
    traces_table_name: ${TRACES_TABLE_NAME}
    ttl: ${CLICKHOUSE_TTL}
    timeout: ${CLICKHOUSE_TIMEOUT}
    create_schema: true
    sending_queue:
      queue_size: 100
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: 300s
```

**환경 변수** (`.env` 또는 `docker-compose.yml`):
```env
CLICKHOUSE_ENDPOINT=tcp://agentops-clickhouse:9000
CLICKHOUSE_USERNAME=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DATABASE=otel_2
TRACES_TABLE_NAME=otel_traces
CLICKHOUSE_TTL=2592000  # 30일
CLICKHOUSE_TIMEOUT=5s
```

#### Service Pipeline

```yaml
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resourcedetection/system, resource, transform, batch]
      exporters: [clickhouse/otel_traces]
```

### LiteLLM OTEL 설정

**설정 파일**: `litellm/config.yaml`

```yaml
litellm_settings:
  callbacks:
    - otel
  default_tags:
    - project:agent-portal
    - environment:development
```

**환경 변수** (`docker-compose.yml`):
```yaml
litellm:
  environment:
    - OTEL_EXPORTER=otlp_http
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://agentops-otel-collector:4318
    - OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://agentops-otel-collector:4318/v1/traces
    - OTEL_SERVICE_NAME=litellm-proxy
    - OTEL_TRACES_EXPORTER=otlp
    - OTEL_METRICS_EXPORTER=none
    - OTEL_LOGS_EXPORTER=none
```

**중요**: `OTEL_EXPORTER=otlp_http`가 없으면 LiteLLM이 console exporter를 사용합니다.

### 데이터 조회 방법

#### 방법 1: ClickHouse 직접 조회 (권장)

```bash
# 최근 trace 조회
docker exec agentops-clickhouse clickhouse-client --query "
SELECT 
    Timestamp,
    SpanName,
    SpanAttributes['gen_ai.request.model'] as model,
    SpanAttributes['gen_ai.prompt.0.content'] as prompt,
    substring(SpanAttributes['gen_ai.completion.0.content'], 1, 100) as response,
    SpanAttributes['gen_ai.usage.total_tokens'] as tokens,
    Duration / 1000000000 as duration_sec
FROM otel_2.otel_traces 
WHERE SpanName = 'litellm_request'
ORDER BY Timestamp DESC 
LIMIT 10
FORMAT PrettyCompact
"
```

**출력 예시**:
```
   ┌─────────────────────Timestamp─┬─SpanName────────┬─model─────────────────────┬─prompt──────────┬─tokens─┬─duration_sec─┐
1. │ 2025-11-25 07:08:56.881273088 │ litellm_request │ qwen/qwen3-235b-a22b-2507 │ ㅇㅇㅇㅇㅇㅇ    │ 88     │  1.692307968 │
   └───────────────────────────────┴─────────────────┴───────────────────────────┴─────────────────┴────────┴──────────────┘
```

#### 방법 2: AgentOps API 통해 조회 (현재 미구현)

AgentOps API는 현재 **Supabase (MariaDB) 기반**으로 되어 있어, ClickHouse에 저장된 traces를 조회할 수 없습니다.

**구현 필요 사항**:
1. `backend/app/services/agentops_adapter.py`를 ClickHouse 쿼리로 변경
2. 또는 AgentOps API 자체를 ClickHouse 기반으로 수정

**현재 상태**:
```python
# backend/app/services/agentops_adapter.py
# 현재: MariaDB (Supabase) 조회
url = f"{self.api_url}/v4/traces"
params = {"project_id": project_id, ...}
# 결과: 빈 배열 (ClickHouse 데이터 접근 불가)
```

**해결 방안**:
- **Option A**: Backend BFF가 ClickHouse를 직접 조회 (권장)
- **Option B**: AgentOps API에 ClickHouse adapter 추가

### 검증 방법

#### 1단계: LiteLLM이 traces 생성하는지 확인

```bash
# LiteLLM 로그 확인
docker logs agent-portal-litellm-1 | grep -i "otel\|span"

# 기대 출력:
# self.OTEL_EXPORTER: otlp_http
# OpenTelemetry: intiializing otlp_http exporter.
# Creating span litellm_request...
```

#### 2단계: OTEL Collector가 수신하는지 확인

```bash
# OTEL Collector 로그 확인
docker logs agentops-otel-collector | grep -i "span\|trace"

# 기대 출력:
# Traces: Exporter, Exporting 7 spans
```

#### 3단계: ClickHouse에 저장되었는지 확인

```bash
# ClickHouse 레코드 수 확인
docker exec agentops-clickhouse clickhouse-client --query "
SELECT count(*) as total_traces FROM otel_2.otel_traces
"

# 기대 출력:
# 9 (또는 그 이상)
```

#### 4단계: 실제 데이터 확인

```bash
# 최근 1개 trace 상세 조회
docker exec agentops-clickhouse clickhouse-client --query "
SELECT 
    Timestamp,
    SpanName,
    SpanAttributes
FROM otel_2.otel_traces 
ORDER BY Timestamp DESC 
LIMIT 1
FORMAT Vertical
"
```

### 트러블슈팅

#### 문제 1: LiteLLM이 traces를 생성하지 않음

**증상**: LiteLLM 로그에 "OpenTelemetry: intiializing console exporter" 표시

**원인**: `OTEL_EXPORTER=otlp_http` 환경 변수 누락

**해결**:
```yaml
# docker-compose.yml
litellm:
  environment:
    - OTEL_EXPORTER=otlp_http  # 추가
```

#### 문제 2: OTEL Collector가 ClickHouse에 저장하지 않음

**증상**: OTEL Collector 로그에 "DB::Exception: Database otel does not exist"

**원인**: ClickHouse exporter 설정 오류 또는 데이터베이스 미생성

**해결**:
```yaml
# config/otel-collector-config.yaml
exporters:
  clickhouse/otel_traces:
    create_schema: true  # 자동 스키마 생성 활성화
```

#### 문제 3: ClickHouse 조회 시 빈 결과

**증상**: `SELECT count(*) FROM otel_2.otel_traces` 결과가 0

**원인**: 실제 LLM 호출이 없거나 trace 생성 실패

**해결**:
1. LiteLLM으로 실제 Chat Completion 호출
2. LiteLLM 로그에서 span 생성 확인
3. OTEL Collector 로그에서 export 확인

### 참고 자료

- [OpenTelemetry Collector ClickHouse Exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/clickhouseexporter)
- [LiteLLM OpenTelemetry Integration](https://docs.litellm.ai/docs/observability/opentelemetry)
- [ClickHouse 공식 문서](https://clickhouse.com/docs)

---

## 학습 내용

### 핵심 학습 1: Supabase 기반 최소 구성

**발견**: AgentOps는 Supabase만으로도 완전히 작동합니다.

**구성**:
- ✅ **Supabase**: 인증, 데이터베이스, 스토리지
- ⚠️ **ClickHouse**: 선택적 (대용량 트레이스 저장 시 유용)
- ⚠️ **OTEL Collector**: 선택적 (고급 트레이스 수집)

**이점**:
- 단순한 설정
- 포트 충돌 최소화
- 빠른 시작

### 핵심 학습 2: 자동 스크립트의 중요성

**문제**: 수동으로 계정, 조직, 프로젝트 생성 시 복잡한 SQL 필요

**해결**: `scripts/setup-agentops-apikey.sh` 자동화 스크립트

**장점**:
- 1회 실행으로 모든 설정 완료
- API 키 자동 추출 및 `.env` 업데이트
- Backend BFF 자동 재시작

**재사용 패턴**:
```bash
#!/bin/bash
# 1. 서비스 상태 확인
# 2. 데이터 생성 (SQL 직접 실행)
# 3. 키 추출
# 4. .env 파일 업데이트
# 5. 관련 서비스 재시작
```

### 핵심 학습 3: Backend BFF의 이중 통신 경로

**구조**:
```
Backend BFF (8000)
  ├─ 경로 1: Supabase PostgreSQL (직접 쿼리)
  └─ 경로 2: AgentOps API (v4 REST 엔드포인트)
```

**현재 구현**: 경로 2 (AgentOps API v4 엔드포인트)

**장점**:
- API 추상화 (비즈니스 로직 캡슐화)
- 버전 관리 용이
- 권한 제어 통합

**단점**:
- 추가 네트워크 홉
- AgentOps API 실행 필요

**향후 개선**: 경로 1 (Supabase 직접 쿼리) 지원 추가

### 핵심 학습 4: API 키 기반 JWT 인증 패턴

**흐름**:
```
1. Backend BFF가 AGENTOPS_API_KEY 소유
2. /v3/auth/token 엔드포인트에 API 키 전송
3. JWT 토큰 획득 (1시간 유효)
4. /v4/traces 등 API 호출 시 JWT Bearer 토큰 사용
5. 토큰 만료 5분 전 자동 갱신
```

**구현 위치**: `backend/app/services/agentops_adapter.py`

**재사용 패턴**:
```python
class APIAdapter:
    def __init__(self, api_key):
        self.api_key = api_key
        self.jwt_token = None
        self.token_expiry = None
    
    async def _get_jwt_token(self):
        if self.jwt_token and self.token_expiry > datetime.now() + timedelta(minutes=5):
            return  # 토큰 재사용
        
        # 토큰 갱신
        response = await client.post(f"{self.api_url}/v3/auth/token", json={"api_key": self.api_key})
        data = response.json()
        self.jwt_token = data["token"]
        self.token_expiry = datetime.now() + timedelta(hours=1)
```

### 핵심 학습 5: v4 REST API 엔드포인트 올바른 사용법

**잘못된 방법** (구식):
```python
url = f"{self.api_url}/v4/traces/list/{project_id}"  # ❌
```

**올바른 방법** (현재):
```python
url = f"{self.api_url}/v4/traces"
params = {"project_id": project_id, "start_time": "...", "end_time": "..."}
response = await client.get(url, params=params, headers={"Authorization": f"Bearer {jwt}"})
```

**핵심**: 쿼리 파라미터 방식 사용

### 핵심 학습 6: Docker 네트워크 호스트 접근

**문제**: Backend BFF (Docker 컨테이너)에서 호스트의 AgentOps API (8003) 접근

**해결**:
```bash
# .env
AGENTOPS_API_ENDPOINT=http://host.docker.internal:8003
```

**설명**:
- `localhost` → Docker 컨테이너 내부 루프백 (❌)
- `host.docker.internal` → macOS/Windows에서 호스트 접근 (✅)
- Linux는 `--network=host` 또는 `172.17.0.1` 사용

---

## 체크리스트

### 기동 전 확인 사항

- [ ] Docker Desktop 실행 중
- [ ] Supabase CLI 설치 (`supabase --version`)
- [ ] Git submodule 초기화 (`git submodule update --init --recursive`)
- [ ] 포트 사용 가능 확인:
  - 9002/8124 (ClickHouse)
  - 4317/4318 (OTEL Collector)
  - 8003 (AgentOps API)
  - 3006 (AgentOps Dashboard)
  - 4000 (LiteLLM)
  - 55321/55432 (Supabase)

### 기동 후 확인 사항

#### Core Services
- [ ] Supabase 실행 중 (`docker ps | grep supabase`)
- [ ] ClickHouse 실행 중 (`docker ps | grep clickhouse`)
- [ ] OTEL Collector 실행 중 (`docker ps | grep otel-collector`)
- [ ] LiteLLM 실행 중 (`docker ps | grep litellm`)

#### AgentOps Configuration
- [ ] 계정 및 프로젝트 생성 완료 (`./scripts/setup-agentops-apikey.sh`)
- [ ] API 키 `.env`에 저장 (`grep AGENTOPS_API_KEY .env`)
- [ ] Backend BFF 재시작 완료 (`docker-compose logs backend | grep AgentOps`)

### LiteLLM + OTEL 연동 확인

#### LiteLLM 설정
- [ ] `litellm/config.yaml`에 OTEL callback 추가 (`callbacks: - otel`)
- [ ] 환경 변수 설정 확인 (`OTEL_EXPORTER=otlp_http`)
- [ ] LiteLLM 재시작 (`docker-compose restart litellm`)

#### OTEL 동작 확인
- [ ] LiteLLM OTEL 초기화 로그 확인:
  ```bash
  docker logs agent-portal-litellm-1 | grep "OTEL_EXPORTER"
  # 기대: self.OTEL_EXPORTER: otlp_http
  ```
- [ ] Chat Completion 호출 테스트:
  ```bash
  curl -X POST http://localhost:4000/chat/completions \
    -H "Authorization: Bearer sk-1234" \
    -H "Content-Type: application/json" \
    -d '{"model": "qwen-235b", "messages": [{"role": "user", "content": "Test"}]}'
  ```
- [ ] OTEL Collector 수신 확인:
  ```bash
  docker logs agentops-otel-collector | grep "Exporting"
  # 기대: Traces: Exporter, Exporting N spans
  ```

#### ClickHouse 저장 확인
- [ ] ClickHouse에 traces 저장 확인:
  ```bash
  docker exec agentops-clickhouse clickhouse-client --query \
    "SELECT count(*) FROM otel_2.otel_traces"
  # 기대: 1 이상
  ```
- [ ] 최근 trace 조회:
  ```bash
  docker exec agentops-clickhouse clickhouse-client --query \
    "SELECT Timestamp, SpanName, ServiceName FROM otel_2.otel_traces ORDER BY Timestamp DESC LIMIT 5 FORMAT PrettyCompact"
  ```

### AgentOps Dashboard 연동 확인 (선택)

- [ ] AgentOps API 실행 중 (`curl http://localhost:8003/health`)
- [ ] AgentOps Dashboard 접속 (`http://localhost:3006`)
- [ ] Dashboard 로그인 (admin@agent-portal.local / agentops-admin-password)
- [ ] Dashboard에서 트레이스 확인

---

## 참고 자료

### 스크립트

- `scripts/start-agentops.sh` — AgentOps 전체 스택 시작 (Supabase + ClickHouse + API)
- `scripts/setup-agentops-apikey.sh` — 계정/프로젝트 자동 생성 및 API 키 추출
- `scripts/setup-agentops.sql` — 수동 SQL (대안)

### 문서

- `AGENTS.md` (Section 3.3) — AgentOps Self-Hosted API 통합
- `.cursor/rules/backend-api.mdc` (Section 4.5) — AgentOps 가드레일
- `.cursor/learnings/agentops-self-hosting.md` — Self-Hosting 학습 패턴
- `.cursor/learnings/agentops-litellm-integration-test.md` — LiteLLM 연동 테스트

### 코드

- `backend/app/services/agentops_adapter.py` — AgentOps API 클라이언트
- `backend/app/routes/agentops.py` — AgentOps API 프록시 라우트
- `backend/app/config.py` — 환경 변수 설정

---

## 실제 기동 결과 (2025-11-21)

### ✅ 성공적으로 실행된 서비스

1. **Supabase (20개 컨테이너)**
   - API URL: http://127.0.0.1:55321
   - PostgreSQL: postgresql://postgres:postgres@127.0.0.1:55432/postgres
   - Studio UI: http://127.0.0.1:55323
   - 상태: ✅ 정상 실행

2. **AgentOps API (PID: 15724)**
   - URL: http://localhost:8003
   - Health Check: `{"message":"Server Up"}` ✅
   - OpenAPI Docs: http://localhost:8003/docs
   - 로그: `/tmp/agentops-api.log`
   - 상태: ✅ 정상 실행
   - 주의: Stripe 경고는 무시 (결제 기능 미사용)

3. **AgentOps Dashboard (PID: 15878)**
   - URL: http://localhost:3006
   - 빌드 시간: 2.4초 (Turbopack)
   - 로그: `/tmp/agentops-dashboard.log`
   - 상태: ✅ 정상 실행 (로그인 페이지로 리다이렉트)

4. **데이터베이스 (Supabase PostgreSQL)**
   - ✅ 사용자 생성: `admin@agent-portal.local`
   - ✅ 조직 생성: `Agent Portal Organization`
   - ✅ 프로젝트 생성: `agent-portal`
   - ✅ API 키 자동 추출: `0c26af2a-8bac-4809-8b30-433ae3850608`
   - ✅ Project ID: `94909765-19bf-475a-b7da-d448ab90d072`

5. **Backend BFF 연동**
   - ✅ `.env` 파일 자동 업데이트
   - ✅ Backend 자동 재시작
   - ✅ AgentOps Adapter 새 API 키 적용

### 사용 방법

```bash
# 1. Dashboard 접속
open http://localhost:3006

# 2. 로그인
Email: admin@agent-portal.local
Password: agentops-admin-password

# 3. Monitoring 화면에서 데이터 확인
open http://localhost:3001/admin/monitoring

# 4. API 직접 호출 테스트
curl http://localhost:8003/health
curl http://localhost:8003/docs  # OpenAPI 문서
```

### 로그 모니터링

```bash
# API 로그 실시간 확인
tail -f /tmp/agentops-api.log

# Dashboard 로그 실시간 확인
tail -f /tmp/agentops-dashboard.log

# Supabase 로그
docker logs -f supabase_db_agentops
```

### 프로세스 관리

```bash
# 실행 중인 프로세스 확인
ps aux | grep -E "python run.py|npm run dev" | grep -v grep

# API 중지 (필요 시)
kill 15724

# Dashboard 중지 (필요 시)
kill 15878

# Supabase 중지
cd external/agentops/app && supabase stop
```

---

**작성자**: AI Agent (Claude)  
**최종 업데이트**: 2025-11-25  
**상태**: ✅ 완전 검증 완료 (Supabase + API + Dashboard + 계정 생성 + Backend 연동 + OTEL + ClickHouse)

## 변경 이력

### 2025-11-26 (2): Agent Flow Graph + Guardrail 모니터링 추가

**목적**: LLM/Agent 호출 흐름과 가드레일 모니터링 시각화

**구현 내용**:

1. **Agent Flow Graph 개선** (`agentops_adapter.py`)
   - 실제 호출 흐름 표현:
     ```
     [Client Request] → [Input Guardrail] → [LiteLLM Proxy] → [LLM Provider] → [Output Guardrail]
                                                  ↓
                                           [Agent Builder]
                                                  ↓
                                             [MCP Tools]
     ```
   - 각 단계별 통계: call_count, avg_latency_ms, total_tokens, total_cost
   - 가드레일 차단 여부 표시 (error_count, guardrail_applied)

2. **Guardrail Stats API** (`/api/agentops/analytics/guardrails`)
   - 전체 요청 수, 가드레일 적용 수, 차단된 요청 수
   - Input/Output 가드레일별 통계 (checks, blocks, block_rate)
   - 토큰 사용량 및 평균 레이턴시

3. **프론트엔드 업데이트** (`AgentFlowGraph.svelte`)
   - 가드레일 노드 시각적 구분 (🛡️ 아이콘, 둥근 모서리)
   - 차단된 엣지 표시 (빨간색 점선)
   - 범례에 가드레일 추가

**가드레일 유형**:
- **Input Guardrail**: PII 감지, 프롬프트 인젝션 방지 (proxy_pre_call 단계)
- **Output Guardrail**: 유해 콘텐츠 필터링, 형식 검증 (batch_write_to_db 단계)
- **Cost Guardrail**: 비용 제한 초과 (향후 구현)
- **Rate Limit**: 요청 빈도 제한 (향후 구현)

**검증 결과**:
```bash
# Guardrail Stats API 테스트
curl "http://localhost:8000/api/agentops/analytics/guardrails?project_id=8c59e361-3727-418c-bc68-086b69f7598b&start_time=2025-11-26T00:00:00&end_time=2025-11-27T00:00:00"
# 결과: {"total_requests": 35, "blocked_requests": 3, "block_rate": 8.57, ...}

# Agent Flow Graph API 테스트
curl "http://localhost:8000/api/agentops/analytics/agent-flow?project_id=8c59e361-3727-418c-bc68-086b69f7598b&start_time=2025-11-26T00:00:00&end_time=2025-11-27T00:00:00"
# 결과: {"nodes": [{"label": "Client Request", ...}, {"label": "Input Guardrail", "is_guardrail": true, ...}], ...}
```

**핵심 학습**:
- LiteLLM의 `proxy_pre_call` 스팬이 입력 검증 단계 역할
- `batch_write_to_db` 스팬이 출력 검증 단계 역할
- StatusCode = 'Error'로 가드레일 차단 감지 가능
- `metadata.applied_guardrails` 필드로 적용된 가드레일 목록 확인 (현재 빈 배열)

### 2025-11-26: Backend AgentOps Adapter ClickHouse 전환

**문제**: `agentops_adapter.py`가 MariaDB를 조회했으나, 실제 트레이스 데이터는 ClickHouse에 저장됨

**해결**:
1. `agentops_adapter.py` 전면 재작성 (MariaDB → ClickHouse HTTP API)
2. `docker-compose.yml`에 Backend용 ClickHouse 환경 변수 추가:
   ```yaml
   backend:
     environment:
       - CLICKHOUSE_HOST=agentops-clickhouse
       - CLICKHOUSE_HTTP_PORT=8123
       - CLICKHOUSE_USER=default
       - CLICKHOUSE_PASSWORD=password
       - CLICKHOUSE_DATABASE=otel_2
   ```

**핵심 학습**:
- ClickHouse HTTP API는 JSONEachRow 형식으로 결과 반환
- Duration 필드가 문자열로 반환되므로 `int()` 변환 필요
- Docker 컨테이너 내부에서는 `agentops-clickhouse` 호스트명 사용 (`.env`의 `host.docker.internal` 아님)

**검증 결과**:
```bash
# Replay API 테스트
curl "http://localhost:8000/api/agentops/replay/dcf2e92508f43453bc55a4deeda45d37"
# 결과: {"trace_id": "...", "events": [...], "total_duration": 9, ...}

# Traces 목록 API 테스트
curl "http://localhost:8000/api/agentops/traces?project_id=8c59e361-3727-418c-bc68-086b69f7598b&start_time=2025-11-01T00:00:00&end_time=2025-11-30T00:00:00"
# 결과: {"traces": [...], "total": "4", ...}
```

### 2025-11-25 (2): ClickHouse 스키마 마이그레이션

**문제**: OTEL Collector가 생성한 표준 스키마에 `project_id` 컬럼이 없어서 AgentOps API가 데이터 조회 불가

**해결**:
1. ClickHouse 테이블 재생성 (AgentOps 스키마 적용)
   - `project_id String MATERIALIZED ResourceAttributes['agentops.project.id']`
   - 관련 뷰와 인덱스 생성
2. OTEL Collector `processors.yaml.tpl` 수정
   - `from_context: auth.project_id` → `value: ${env:AGENTOPS_PROJECT_ID}`
3. docker-compose.yml에 `AGENTOPS_PROJECT_ID` 환경 변수 추가

**생성된 파일**:
- `scripts/clickhouse-agentops-schema.sql` — ClickHouse 스키마 마이그레이션 스크립트

**검증 결과**:
```bash
# ClickHouse에서 project_id 확인
curl "http://localhost:8124/?query=SELECT project_id, count(*) FROM otel_2.otel_traces GROUP BY project_id"
# 결과: 8c59e361-3727-418c-bc68-086b69f7598b	9

# AgentOps API에서 프로젝트 조회
curl "http://localhost:8003/opsboard/projects" -H "Cookie: session_id=..."
# 결과: span_count: 9, trace_count: 1
```

**핵심 학습**:
- AgentOps는 `project_id`를 `ResourceAttributes['agentops.project.id']`에서 추출
- MATERIALIZED 컬럼을 사용하면 INSERT 시 자동으로 값이 추출됨
- JWT 인증 비활성화 시 OTEL Collector에서 정적 project_id 설정 필요

### 2025-11-25: OTEL + ClickHouse 통합 추가
- 현재 아키텍처 다이어그램 업데이트 (LiteLLM → OTEL → ClickHouse)
- ClickHouse 테이블 구조 및 주요 필드 문서화
- OTEL Collector 설정 상세 설명 추가
- LiteLLM OTEL 환경 변수 설정 가이드
- ClickHouse 직접 조회 방법 및 예시 쿼리
- 검증 방법 4단계 절차 추가
- 체크리스트 확장 (OTEL/ClickHouse 항목 추가)
- 트러블슈팅 가이드 추가

**핵심 변경**:
- AgentOps 통합 방식: SDK callback → OTEL Collector → ClickHouse
- Backend BFF의 ClickHouse 직접 조회 옵션 제시
- 실제 동작 확인 완료 (9건의 trace 저장 검증)

### 2025-11-21: 초기 문서 작성
- AgentOps Self-Hosted 전체 스택 기동 가이드
- Supabase, API, Dashboard 설정 방법
- 계정 및 프로젝트 자동 생성 스크립트
- LiteLLM SDK callback 연동 방법


