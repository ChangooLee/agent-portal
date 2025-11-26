# ClickHouse AgentOps 스키마 마이그레이션

**작성일**: 2025-11-25  
**목적**: OTEL Collector 표준 스키마를 AgentOps 호환 스키마로 마이그레이션

---

## 문제 상황

### 증상
```
DB::Exception: Unknown expression or function identifier project_id in scope 
SELECT any(project_id) AS project_id_, count() AS span_count...
```

### 원인
- OTEL Collector가 생성한 표준 스키마에는 `project_id` 컬럼이 없음
- AgentOps API는 `project_id`로 트레이스를 필터링
- 스키마 불일치로 인해 쿼리 실패

---

## 해결 방법

### 1. ClickHouse 테이블 재생성

**핵심**: `project_id`를 MATERIALIZED 컬럼으로 정의

```sql
CREATE TABLE otel_2.otel_traces (
    Timestamp DateTime64(9) CODEC(Delta(8), ZSTD(1)),
    -- project_id는 ResourceAttributes에서 자동 추출
    project_id String MATERIALIZED ResourceAttributes['agentops.project.id'],
    TraceId String CODEC(ZSTD(1)),
    SpanId String CODEC(ZSTD(1)),
    ParentSpanId String CODEC(ZSTD(1)),
    -- ... 나머지 컬럼 ...
    INDEX idx_project_id project_id TYPE bloom_filter(0.001) GRANULARITY 16
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(Timestamp)
ORDER BY (project_id, Timestamp)
SETTINGS index_granularity = 8192;
```

**스크립트 위치**: `scripts/clickhouse-agentops-schema.sql`

### 2. OTEL Collector 설정 수정

**파일**: `external/agentops/app/opentelemetry-collector/config/processors.yaml.tpl`

**변경 전** (JWT 인증 필요):
```yaml
processors:
  resource:
    attributes:
      - key: agentops.project.id
        action: upsert
        from_context: auth.project_id  # JWT에서 추출
```

**변경 후** (정적 project_id):
```yaml
processors:
  resource:
    attributes:
      - key: agentops.project.id
        action: upsert
        value: ${env:AGENTOPS_PROJECT_ID}  # 환경 변수에서 추출
```

### 3. docker-compose.yml 환경 변수 추가

```yaml
agentops-otel-collector:
  environment:
    # ... 기존 환경 변수 ...
    - AGENTOPS_PROJECT_ID=${AGENTOPS_PROJECT_ID:-8c59e361-3727-418c-bc68-086b69f7598b}
```

---

## 마이그레이션 절차

### 1. 기존 테이블 삭제

```bash
curl -s "http://localhost:8124/" -H "X-ClickHouse-User: default" -H "X-ClickHouse-Key: password" \
  --data "DROP VIEW IF EXISTS otel_2.otel_traces_trace_id_ts_mv"
curl -s "http://localhost:8124/" -H "X-ClickHouse-User: default" -H "X-ClickHouse-Key: password" \
  --data "DROP VIEW IF EXISTS otel_2.otel_traces_project_idx"
curl -s "http://localhost:8124/" -H "X-ClickHouse-User: default" -H "X-ClickHouse-Key: password" \
  --data "DROP TABLE IF EXISTS otel_2.otel_traces_trace_id_ts"
curl -s "http://localhost:8124/" -H "X-ClickHouse-User: default" -H "X-ClickHouse-Key: password" \
  --data "DROP TABLE IF EXISTS otel_2.otel_traces"
```

### 2. AgentOps 스키마로 테이블 생성

```bash
# scripts/clickhouse-agentops-schema.sql 각 쿼리를 개별 실행
# (ClickHouse HTTP 인터페이스는 한 번에 하나의 쿼리만 실행 가능)
```

### 3. OTEL Collector 재빌드

```bash
docker-compose build --no-cache agentops-otel-collector
docker-compose up -d agentops-otel-collector
```

### 4. 검증

```bash
# 테이블 스키마 확인
curl -s "http://localhost:8124/?query=DESCRIBE%20otel_2.otel_traces" \
  -H "X-ClickHouse-User: default" \
  -H "X-ClickHouse-Key: password"

# LiteLLM 호출 테스트
curl -X POST "http://localhost:4000/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "Test"}]}'

# ClickHouse에서 project_id 확인
curl -s "http://localhost:8124/?query=SELECT%20project_id%2C%20count(*)%20FROM%20otel_2.otel_traces%20GROUP%20BY%20project_id" \
  -H "X-ClickHouse-User: default" \
  -H "X-ClickHouse-Key: password"
```

---

## 핵심 학습

### 1. MATERIALIZED 컬럼
- INSERT 시 자동으로 값이 추출됨
- SELECT 시 일반 컬럼처럼 사용 가능
- 저장 공간 절약 (원본 데이터에서 추출)

### 2. ResourceAttributes 구조
- OTEL 표준: Map(LowCardinality(String), String)
- AgentOps project_id: `ResourceAttributes['agentops.project.id']`

### 3. OTEL Collector 인증 모드
- **JWT 모드**: `from_context: auth.project_id` (AgentOps SDK 사용 시)
- **정적 모드**: `value: ${env:AGENTOPS_PROJECT_ID}` (LiteLLM 직접 연동 시)

---

## 관련 파일

- `scripts/clickhouse-agentops-schema.sql` — 스키마 마이그레이션 스크립트
- `external/agentops/app/opentelemetry-collector/config/processors.yaml.tpl` — OTEL Collector 프로세서 설정
- `external/agentops/app/api/agentops/exporter/models.py` — AgentOps 스키마 정의 (참조)
- `docker-compose.yml` — AGENTOPS_PROJECT_ID 환경 변수

---

**작성자**: AI Agent (Claude)  
**상태**: ✅ 검증 완료


