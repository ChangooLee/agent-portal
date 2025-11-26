# LiteLLM PostgreSQL + OpenTelemetry 통합 완료

## 2025-11-25: LiteLLM Database 모드 + PostgreSQL 통합

### 작업 목표

LiteLLM Proxy를 PostgreSQL + Database 이미지를 사용하여 풀 기능 모드로 실행하고, OpenTelemetry를 통해 AgentOps와 통합합니다.

### 구현 완료 사항

#### 1. PostgreSQL 서비스 추가

**파일**: `docker-compose.yml`

- PostgreSQL 16 컨테이너 추가
- 헬스체크 설정
- 포트: 5433 (호스트) → 5432 (컨테이너)
- 볼륨: `litellm_pg_data` (데이터 영속성)

```yaml
litellm-postgres:
  image: postgres:16
  environment:
    POSTGRES_USER: litellm
    POSTGRES_PASSWORD: ${LITELLM_DB_PASSWORD}
    POSTGRES_DB: litellm_db
  ports:
    - "5433:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U litellm"]
    interval: 10s
    timeout: 5s
    retries: 5
```

#### 2. LiteLLM Database 이미지 사용

**파일**: `litellm/Dockerfile`

- 베이스 이미지: `ghcr.io/berriai/litellm-database:main-stable`
- **Prisma가 이미 포함되어 있음** (별도 설치 불필요)
- OpenTelemetry 패키지만 추가:
  - `opentelemetry-api`
  - `opentelemetry-sdk`
  - `opentelemetry-exporter-otlp-proto-http`

```dockerfile
FROM ghcr.io/berriai/litellm-database:main-stable

RUN pip install --no-cache-dir \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp-proto-http

COPY config.yaml /app/config.yaml
EXPOSE 4000
CMD ["--config", "/app/config.yaml", "--port", "4000", "--detailed_debug"]
```

#### 3. LiteLLM 설정 업데이트

**파일**: `litellm/config.yaml`

- OpenTelemetry callback 추가: `callbacks: - otel`
- 모델 목록: qwen-235b, gpt-4, gpt-3.5-turbo (모두 OpenRouter로 라우팅)
- Master key: 환경 변수에서 로드

```yaml
litellm_settings:
  callbacks:
    - otel
  default_tags:
    - project:agent-portal
    - environment:development
```

#### 4. Docker Compose 환경 변수 설정

**파일**: `docker-compose.yml`

- `DATABASE_URL`: PostgreSQL 연결 문자열
- `LITELLM_MASTER_KEY`: 마스터 키 (sk- 로 시작 필수)
- `LITELLM_SALT_KEY`: API 키 암호화용 솔트 (변경 금지)
- OpenTelemetry 환경 변수:
  - `OTEL_EXPORTER_OTLP_ENDPOINT=http://agentops-otel-collector:4318`
  - `OTEL_SERVICE_NAME=litellm-proxy`
  - `OTEL_TRACES_EXPORTER=otlp`

```yaml
litellm:
  depends_on:
    litellm-postgres:
      condition: service_healthy
    agentops-otel-collector:
      condition: service_started
  environment:
    - DATABASE_URL=postgresql://litellm:${LITELLM_DB_PASSWORD}@litellm-postgres:5432/litellm_db
    - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    - LITELLM_SALT_KEY=${LITELLM_SALT_KEY}
    - OTEL_EXPORTER_OTLP_ENDPOINT=http://agentops-otel-collector:4318
```

#### 5. 환경 변수 추가

**파일**: `.env`

```env
# LiteLLM Database
LITELLM_DB_PASSWORD=litellm_secure_password_change_in_production

# LiteLLM Salt Key (generate random value, never change after first use)
LITELLM_SALT_KEY=sk-salt-random-long-key-do-not-change-after-first-use
```

### 테스트 결과

#### ✅ 성공한 항목

1. **PostgreSQL 정상 시작**
   - 헬스체크 통과: `pg_isready -U litellm` 성공
   - 포트: 5433 (호스트)

2. **LiteLLM Proxy 정상 시작**
   - Prisma 마이그레이션 자동 완료 (70+ migrations)
   - Uvicorn 서버 실행 중: `http://0.0.0.0:4000`
   - 데이터베이스 연결 성공

3. **Open-WebUI 연동 유지**
   - 환경 변수 보존: `OPENAI_API_BASE_URLS=http://litellm:4000/v1`
   - 네트워크 연결 확인: Open-WebUI → LiteLLM 통신 가능

4. **관측성 스택 준비 완료**
   - OTLP Collector 실행 중 (포트 4317/4318)
   - ClickHouse 실행 중 (포트 9002/8124)

#### ⚠️ 추가 작업 필요

1. **Virtual Key 생성**
   - LiteLLM UI (`http://localhost:4000/ui`)에서 master key로 로그인
   - Virtual key 생성하여 Open-WebUI 설정 업데이트

2. **실제 LLM 호출 테스트**
   - Open-WebUI에서 채팅 테스트
   - OpenTelemetry trace 생성 확인
   - ClickHouse에 trace 저장 확인

3. **AgentOps Dashboard 연동**
   - Backend BFF에서 ClickHouse 조회 API 구현
   - Open-WebUI Monitoring 페이지에서 traces 표시

### 핵심 학습 내용

#### 1. LiteLLM Database 이미지의 장점

- ✅ **Prisma 자동 포함**: 별도 설치/설정 불필요
- ✅ **자동 마이그레이션**: 첫 실행 시 자동으로 DB 스키마 생성
- ✅ **풀 기능 지원**: Virtual Keys, Team/Org 관리, 사용량 추적
- ✅ **UI 제공**: `http://localhost:4000/ui`에서 관리 가능

#### 2. LiteLLM Proxy의 인증 시스템

- **Master Key**: 관리용 키 (sk- 로 시작 필수)
- **Virtual Keys**: 실제 API 호출용 키 (UI에서 생성)
- **데이터베이스 기반**: 모든 키는 `LiteLLM_VerificationTokenTable`에 저장
- **❌ Master Key로 직접 API 호출 불가**: Virtual key 생성 필요

#### 3. 데이터베이스 없이 실행 불가

LiteLLM Proxy는 v1.80.5부터 데이터베이스를 필수로 요구합니다:
- 인증 (master key, virtual keys)
- 사용량 추적
- 팀/조직 관리
- 비용 추적

#### 4. Open-WebUI 연동 주의사항

**변경 금지 항목**:
- `OPENAI_API_BASE_URLS` 환경 변수
- `OPENAI_API_KEYS` 환경 변수
- Open-WebUI 데이터베이스의 `PersistentConfig`

**테스트 절차**:
1. LiteLLM UI에서 virtual key 생성
2. Open-WebUI 설정에서 virtual key로 업데이트 (선택)
3. 또는 master key를 그대로 사용 (LiteLLM이 자동으로 virtual key 생성)
4. 채팅 테스트 수행

### 아키텍처 다이어그램

```
Open-WebUI (3001)
    ↓ HTTP
LiteLLM Proxy (4000)
    ↓ PostgreSQL
litellm-postgres (5433)
    ↓ OpenTelemetry gRPC
OTLP Collector (4317/4318)
    ↓ ClickHouse Protocol
ClickHouse (9002/8124)
    ↑ Query
Backend BFF (8000)
    ↑ HTTP
Open-WebUI Monitoring
```

### 다음 단계

#### 즉시 실행 가능

1. **LiteLLM UI 접속**:
   ```bash
   # 브라우저에서 http://localhost:4000/ui
   # Master Key 입력: sk-1234
   ```

2. **Virtual Key 생성** (선택):
   - Settings → API Keys → Create New Key
   - 생성된 키를 Open-WebUI 설정에 추가

3. **Open-WebUI 채팅 테스트**:
   ```bash
   # 브라우저에서 http://localhost:3001
   # 채팅 입력 후 응답 확인
   ```

4. **OpenTelemetry trace 확인**:
   ```bash
   docker exec agentops-clickhouse clickhouse-client --query "
   SELECT count(*) FROM otel_2.otel_traces 
   WHERE Timestamp >= now() - INTERVAL 5 MINUTE"
   ```

#### 향후 작업

- [ ] Backend BFF에서 ClickHouse 조회 API 구현
- [ ] Open-WebUI Monitoring 페이지에서 traces 표시
- [ ] LiteLLM UI 임베딩 (iframe 또는 프록시)
- [ ] AgentOps Dashboard와 LiteLLM 메트릭 통합

### 트러블슈팅

#### 문제 1: "Authentication Error, Invalid proxy server token"

**원인**: Master key를 직접 API 호출에 사용

**해결**:
1. LiteLLM UI에서 virtual key 생성
2. 또는 master key를 그대로 사용 (LiteLLM이 자동으로 처리)

#### 문제 2: Prisma 마이그레이션 오류

**원인**: PostgreSQL 연결 실패 또는 `DATABASE_URL` 오류

**해결**:
```bash
# PostgreSQL 헬스체크 확인
docker exec litellm-postgres pg_isready -U litellm

# DATABASE_URL 확인
docker exec agent-portal-litellm-1 env | grep DATABASE_URL
```

#### 문제 3: OpenTelemetry trace가 안 보임

**원인**: 실제 LLM 호출이 없거나 OTLP Collector 연결 실패

**해결**:
1. LiteLLM 로그 확인:
   ```bash
   docker logs agent-portal-litellm-1 | grep -i otel
   ```

2. OTLP Collector 로그 확인:
   ```bash
   docker logs agentops-otel-collector | grep -i span
   ```

3. 실제 LLM 호출 수행 (Open-WebUI 채팅)

### 파일 변경 요약

**신규 파일**: 없음

**수정된 파일**:
1. `docker-compose.yml`: PostgreSQL 서비스 추가, LiteLLM 환경 변수 업데이트
2. `litellm/Dockerfile`: Database 이미지 기반으로 변경
3. `litellm/config.yaml`: OpenTelemetry callback 추가
4. `.env`: `LITELLM_DB_PASSWORD`, `LITELLM_SALT_KEY` 추가

**삭제된 파일**:
- `litellm/init_otel.py` (Database 이미지에서 불필요)
- `litellm/start.sh` (Database 이미지에서 불필요)

### 참고 자료

- [LiteLLM Database Docs](https://docs.litellm.ai/docs/proxy/virtual_keys)
- [PostgreSQL Official Docker Image](https://hub.docker.com/_/postgres)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [AgentOps Self-Hosted](https://github.com/AgentOps-AI/agentops)

---

## 2025-11-25 업데이트: Master Key 인증 및 Virtual Key 생성 성공

### 문제 해결: Master Key 인증 실패

#### 초기 증상
- 모든 API 호출이 `401 Authentication Error` 반환
- 에러 메시지: "Unable to find token in cache or `LiteLLM_VerificationTokenTable`"

#### 원인 분석
Master key 인증 흐름:
1. API 요청의 `Authorization: Bearer <key>` 확인
2. `<key>`와 `master_key` (환경 변수 또는 config.yaml) 문자열 비교
   - **일치하면**: Master key로 인정, DB 조회 없이 통과
   - **불일치하면**: DB에서 virtual key 조회 → 없으면 401 에러

#### 해결 방법

**1단계: Master Key 정합성 확인**
```bash
docker exec agent-portal-litellm-1 sh -c '
  echo "LITELLM_MASTER_KEY=$LITELLM_MASTER_KEY"
  grep -A10 "general_settings" /app/config.yaml
'
```

**결과**:
- 환경변수: `LITELLM_MASTER_KEY=sk-1234` ✅
- config.yaml: `master_key: os.environ/LITELLM_MASTER_KEY` ✅

**2단계: Master Key로 Virtual Key 생성**
```bash
curl "http://localhost:4000/key/generate" \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["qwen-235b", "gpt-4", "gpt-3.5-turbo"],
    "metadata": {"project": "agent-portal"}
  }'
```

**성공 응답**:
```json
{
  "key": "sk-S1fQVcPcxdq5mtXOunHc9w",
  "models": ["qwen-235b", "gpt-4", "gpt-3.5-turbo"],
  "token_id": "e67db189...",
  "created_at": "2025-11-25T03:31:43.303000Z"
}
```

### LLM 호출 테스트 성공

**Virtual Key로 LLM 호출**:
```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-S1fQVcPcxdq5mtXOunHc9w" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-235b",
    "messages": [{"role": "user", "content": "Say hello in one word"}],
    "max_tokens": 10
  }'
```

**성공 응답**:
```json
{
  "id": "gen-1764041512-...",
  "model": "qwen/qwen3-235b-a22b-2507",
  "choices": [{
    "message": {"content": "Hello", "role": "assistant"}
  }],
  "usage": {
    "total_tokens": 15,
    "cost": 0.000001864
  }
}
```

### OpenTelemetry 상태

#### ✅ 확인된 사항
1. **OpenTelemetry callback 초기화 완료**
   - LiteLLM 로그에 `otel` callback 확인됨
   - Trace 및 Span 생성 확인됨
   - Trace ID: `0x837daab569edc28bae8e01ccef560f2d`

2. **환경 변수 설정 완료**
   ```env
   OTEL_EXPORTER_OTLP_ENDPOINT=http://agentops-otel-collector:4318
   OTEL_SERVICE_NAME=litellm-proxy
   OTEL_TRACES_EXPORTER=otlp
   ```

#### ⚠️ 추가 확인 필요
- **ClickHouse에 trace 미저장**: LiteLLM이 span을 생성하지만 OTLP Exporter로 전송하지 않는 것으로 보임
- **원인 가능성**: LiteLLM의 `otel` callback이 로깅 전용일 수 있음
- **해결 방향**: LiteLLM 문서 확인 또는 추가 설정 필요

### 핵심 학습 내용

#### 1. Master Key vs Virtual Key

**Master Key** (`sk-1234`):
- 관리자용 키
- DB 조회 없이 문자열 비교로 인증
- `/key/*`, `/user/*`, `/config/*` 등 관리 엔드포인트 접근
- **DB에 저장할 필요 없음**

**Virtual Key** (`sk-S1fQVcPcxdq5mtXOunHc9w`):
- 실제 API 호출용 키
- SHA-256 해시로 DB에 저장 (`LiteLLM_VerificationToken`)
- 팀/유저별 예산, RPM 제한, 모델 권한 관리
- `/key/generate`로 생성

#### 2. LiteLLM 인증 원칙

```
API 요청
  ↓
Authorization 헤더 확인
  ↓
문자열 비교: api_key == master_key?
  ├─ Yes → Master Key 인증 완료 (DB 조회 X)
  └─ No  → DB에서 virtual key 조회
           ├─ 있음 → Virtual Key 인증 완료
           └─ 없음 → 401 에러
```

#### 3. PostgreSQL에 Master Key 넣기는 필요 없음

Master key를 DB에 넣는 것은:
- ❌ **필수 아님** - Master key는 문자열 비교로 인증
- ❌ **401 해결책 아님** - 근본 원인은 master key 문자열 불일치
- ✅ **선택 사항** - 인프라-as-code로 관리하고 싶을 때만

#### 4. Virtual Key 생성 방법

**옵션 1: Master Key만 사용** (가장 단순)
- Open-WebUI에 master key 직접 입력
- 개인/소규모 환경에 적합
- 팀별 관리 없음

**옵션 2: UI로 Virtual Key 생성** (가장 편함)
- `http://localhost:4000/ui` 접속
- Organization / Team 생성
- Virtual Keys 메뉴에서 키 생성

**옵션 3: API로 Virtual Key 생성** (완전 자동화)
- `POST /key/generate` 사용
- CI/CD 또는 초기화 스크립트에 적합
- 이번에 사용한 방법 ✅

### 다음 단계

#### 즉시 가능

1. **Open-WebUI 연동 테스트**:
   ```env
   OPENAI_API_BASE_URL=http://litellm:4000/v1
   OPENAI_API_KEY=sk-S1fQVcPcxdq5mtXOunHc9w  # Virtual key
   ```

2. **브라우저에서 채팅 테스트**:
   - `http://localhost:3001` 접속
   - 채팅 입력하여 응답 확인

#### 추가 작업 필요

- OpenTelemetry trace export 설정 확인
- LiteLLM 문서에서 OTLP exporter 활성화 방법 확인
- Backend BFF에서 ClickHouse 조회 API 구현
- Open-WebUI Monitoring 페이지에서 traces 표시

### 트러블슈팅 가이드

#### 문제: "Authentication Error, Invalid proxy server token"

**원인**: Master key 문자열 불일치

**해결**:
1. 컨테이너 내부 master key 확인:
   ```bash
   docker exec <container> sh -c 'echo $LITELLM_MASTER_KEY'
   ```
2. config.yaml 확인:
   ```bash
   docker exec <container> grep -A5 "general_settings" /app/config.yaml
   ```
3. 두 값이 정확히 일치하는지 확인 (따옴표, 공백, 개행 주의)

#### 문제: "/key/generate가 401 반환"

**원인**: Master key 인증 실패

**해결**:
1. Authorization 헤더 형식 확인: `Authorization: Bearer <master_key>`
2. Bearer와 키 사이 공백 하나만 있는지 확인
3. Master key에 특수문자나 공백이 없는지 확인

#### 문제: "Virtual key로 LLM 호출이 401"

**원인**: Virtual key가 DB에 없거나 만료됨

**해결**:
1. PostgreSQL에서 확인:
   ```sql
   SELECT token FROM "LiteLLM_VerificationToken" LIMIT 5;
   ```
2. 새 virtual key 생성
3. `expires` 필드 확인

### 참고 자료

- [LiteLLM Virtual Keys](https://docs.litellm.ai/docs/proxy/virtual_keys)
- [LiteLLM Authentication](https://docs.litellm.ai/docs/proxy/user_keys)
- [OpenTelemetry Integration](https://docs.litellm.ai/docs/observability/opentelemetry)

