# Monitoring Setup Guide

## Overview

Agent Portal의 모니터링은 **LiteLLM + OTEL + ClickHouse** 스택으로 구성됩니다.

```
LiteLLM (LLM Gateway)
  └─> OTEL Callback (트레이스 생성)
        └─> OTEL Collector (4317/4318)
              └─> ClickHouse (otel_2.otel_traces)
                    ↑
Backend BFF → ClickHouse 쿼리
  └─> 모니터링 화면 (Agent/LLM Call/All 탭)
```

---

## Architecture

### 1. LiteLLM → OTEL → ClickHouse

LiteLLM은 OTEL 콜백을 통해 모든 LLM 호출을 트레이스로 기록합니다.

**설정** (`config/litellm.yaml`):
```yaml
litellm_settings:
  success_callback: ["otel"]
  failure_callback: ["otel"]

environment_variables:
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4318"
  OTEL_SERVICE_NAME: "litellm-proxy"
```

**트레이스 데이터**:
- TraceId, SpanId, SpanName
- ServiceName (litellm-proxy, agent-text2sql 등)
- Duration (나노초 단위)
- Token Usage (prompt_tokens, completion_tokens)
- Cost (USD)
- Status Code (OK/ERROR)

### 2. ClickHouse 스키마

**데이터베이스**: `otel_2`
**테이블**: `otel_traces`

```sql
-- 주요 컬럼
TraceId             String
SpanId              String
SpanName            String
ServiceName         LowCardinality(String)
Duration            Int64  -- 나노초 (ms로 변환: Duration / 1000000)
Timestamp           DateTime64(9)
StatusCode          LowCardinality(String)
ResourceAttributes  Map(LowCardinality(String), String)
SpanAttributes      Map(LowCardinality(String), String)

-- project_id 접근 방식 (Map 내부)
ResourceAttributes['project_id']
```

### 3. Backend BFF → ClickHouse

`backend/app/services/monitoring_adapter.py`에서 ClickHouse를 직접 쿼리합니다.

```python
# 트레이스 조회 예시
SELECT 
    TraceId as trace_id,
    SpanName as span_name,
    ServiceName as service_name,
    Duration / 1000000 as duration_ms,
    ResourceAttributes['project_id'] as project_id
FROM otel_2.otel_traces
WHERE ResourceAttributes['project_id'] = '{project_id}'
ORDER BY Timestamp DESC
LIMIT 100
```

---

## Quick Start

### 1. 환경 변수 설정

```bash
# .env 파일
# ClickHouse
CLICKHOUSE_HOST=monitoring-clickhouse
CLICKHOUSE_HTTP_PORT=8123
CLICKHOUSE_DATABASE=otel_2
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password

# Default Project
DEFAULT_PROJECT_ID=8c59e361-3727-418c-bc68-086b69f7598b
```

### 2. 서비스 시작

```bash
# 모니터링 스택 시작
docker compose up -d otel-collector monitoring-clickhouse

# LiteLLM 시작
docker compose up -d litellm

# Backend 시작
docker compose up -d backend webui
```

### 3. 상태 확인

```bash
# ClickHouse 연결 확인
curl http://localhost:8124/ping

# 트레이스 확인
curl "http://localhost:8124/?query=SELECT+count()+FROM+otel_2.otel_traces"

# LiteLLM 헬스 체크
curl http://localhost:4000/health
```

### 4. UI 접속

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Monitoring Dashboard** | http://localhost:3009/admin/monitoring | Overview/Analytics/Traces/Replay |
| **LiteLLM Admin** | http://localhost:4000/ui | 모델 관리, 사용량 확인 |
| **Prometheus** | http://localhost:9090 | 메트릭 쿼리 |

---

## Monitoring Dashboard

### Overview 탭

| 메트릭 | 설명 |
|--------|------|
| Total Cost | 전체 비용 (USD) |
| LLM Calls | LiteLLM 호출 수 |
| Agent Calls | 에이전트 실행 수 |
| Avg Latency | 평균 응답 시간 |
| Fail Rate | 에러 비율 |

### Analytics 탭

- **Cost Trend**: 일별 비용 추이
- **Token Usage**: 토큰 사용량 차트
- **Agent Flow Graph**: 에이전트 실행 흐름

### Traces 탭

**서브탭**:
| 탭 | 필터 | 용도 |
|---|---|---|
| 🤖 Agent | text2sql, analyze, generate, execute 등 | 에이전트 워크플로우 |
| 💬 LLM Call | litellm, chat_completion, prompt_tokens > 0 | LLM API 호출 |
| 📋 All | 필터 없음 | 전체 트레이스 |

---

## Troubleshooting

### 문제 1: 트레이스가 보이지 않음

**증상**: Traces 탭이 비어 있음

**원인**: LLM 요청이 없거나 OTEL 설정 오류

**해결**:
```bash
# 1. LiteLLM 테스트 요청
curl -X POST "http://localhost:4000/v1/chat/completions" \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-235b",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'

# 2. ClickHouse에서 트레이스 확인
curl "http://localhost:8124/?query=SELECT+count()+FROM+otel_2.otel_traces"

# 3. OTEL Collector 로그 확인
docker compose logs otel-collector --tail=50
```

### 문제 2: ClickHouse 연결 실패

**증상**: 모니터링 화면에 에러 표시

**해결**:
```bash
# 1. ClickHouse 상태 확인
docker compose ps monitoring-clickhouse
curl http://localhost:8124/ping

# 2. 재시작
docker compose restart monitoring-clickhouse

# 3. 테이블 존재 확인
docker compose exec monitoring-clickhouse clickhouse-client \
  --query "SHOW TABLES FROM otel_2"
```

### 문제 3: Duration이 너무 큼

**원인**: Duration은 나노초 단위로 저장됨

**해결**: 밀리초로 변환
```sql
SELECT Duration / 1000000 as duration_ms FROM otel_2.otel_traces
```

### 문제 4: project_id 필터링 안됨

**원인**: project_id는 직접 컬럼이 아니라 Map 내부에 있음

**해결**:
```sql
-- ❌ WRONG
WHERE project_id = 'xxx'

-- ✅ CORRECT
WHERE ResourceAttributes['project_id'] = 'xxx'
```

---

## Performance Tuning

### ClickHouse Retention

```sql
-- 30일 이상 된 트레이스 삭제
ALTER TABLE otel_2.otel_traces DELETE 
WHERE Timestamp < now() - INTERVAL 30 DAY
```

### OTEL Collector Batch

```yaml
# config/otel-collector-config.yaml
processors:
  batch:
    timeout: 5s
    send_batch_size: 512
```

---

## Production Checklist

- [ ] ClickHouse 비밀번호 변경 (default/password)
- [ ] ClickHouse retention 정책 설정
- [ ] OTEL Collector 리소스 제한 설정
- [ ] Backend 연결 타임아웃 설정 (30초)
- [ ] 모니터링 API 인증 추가

---

## References

- [LiteLLM OpenTelemetry Docs](https://docs.litellm.ai/docs/proxy/logging)
- [OTEL Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)
- [ClickHouse SQL Reference](https://clickhouse.com/docs/en/sql-reference)

---

**Last Updated**: 2025-12-05
