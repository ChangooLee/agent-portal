# OpenTelemetry Gen AI Metrics Specification

> **Purpose**: Agent Portal의 OTEL Gen AI 표준 매트릭 정의 및 구현 현황
> **Reference**: [OpenTelemetry Gen AI Semantic Conventions v1.38.0](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
> **Last Updated**: 2025-12-23

---

## 1. Overview

Agent Portal은 OpenTelemetry Gen AI 시맨틱 컨벤션을 기반으로 LLM 호출, 에이전트 실행, 도구 호출을 모니터링합니다.

### 1.1 데이터 흐름

```
Agent/LLM 호출
  └─> OTEL Instrumentation (속성 기록)
        └─> OTEL Collector (4317/4318)
              └─> ClickHouse (otel_2.otel_traces)
                    ↑
Backend BFF → ClickHouse 쿼리 → 모니터링 UI
```

---

## 2. 표준 Span 유형

### 2.1 Gen AI 표준 Span Names

| Span Name | 유형 | 설명 | 구현 상태 |
|-----------|------|------|----------|
| `gen_ai.session` | Root | 에이전트 세션 루트 span | ✅ 구현됨 |
| `gen_ai.content.completion` | LLM | LLM 완성 호출 | ⚠️ LiteLLM 대체 |
| `gen_ai.tool.call` | Tool | 도구 호출 | ✅ 구현됨 |
| `gen_ai.agent.*` | Agent | 에이전트 작업 | ✅ 구현됨 |

### 2.2 레거시 Span Names (호환성 유지)

| Span Name | 유형 | 설명 | 마이그레이션 |
|-----------|------|------|-------------|
| `litellm_request` | LLM | LiteLLM 프록시 요청 | 유지 (LiteLLM 제공) |
| `raw_gen_ai_request` | LLM | OpenRouter 원시 요청 | 유지 (비용 정보 포함) |
| `dart.llm_call.*` | LLM | DART 에이전트 LLM 호출 | → `gen_ai.content.completion` |
| `dart.tool_call.*` | Tool | DART 에이전트 도구 호출 | → `gen_ai.tool.call` |

---

## 3. 표준 속성 (Attributes)

### 3.1 Gen AI 공통 속성

| 속성 | 타입 | 필수 | 설명 | 구현 상태 |
|------|------|------|------|----------|
| `gen_ai.operation.name` | string | Required | 작업 이름 (chat, embeddings 등) | ⚠️ 부분 구현 |
| `gen_ai.provider.name` | string | Required | 제공자 (openai, anthropic 등) | ⚠️ 부분 구현 |
| `gen_ai.request.model` | string | Required | 요청 모델명 | ✅ 구현됨 |
| `gen_ai.response.model` | string | Recommended | 응답 모델명 | ✅ 구현됨 |
| `gen_ai.agent.id` | string | Recommended | 에이전트 ID | ✅ 구현됨 |
| `gen_ai.agent.name` | string | Recommended | 에이전트 이름 | ✅ 구현됨 |

### 3.2 토큰 사용량 속성

| 속성 | 타입 | 설명 | 구현 상태 |
|------|------|------|----------|
| `gen_ai.usage.input_tokens` | int | 입력 토큰 수 | ⚠️ LiteLLM 대체 |
| `gen_ai.usage.output_tokens` | int | 출력 토큰 수 | ⚠️ LiteLLM 대체 |
| `gen_ai.token.type` | string | 토큰 유형 (input/output) | ❌ 미구현 |

**현재 LiteLLM/OpenRouter 속성** (호환성 유지):

| 속성 | 타입 | 설명 |
|------|------|------|
| `llm.openrouter.usage` | string (JSON) | OpenRouter 응답 사용량 |
| `llm.usage.total_tokens` | int | 총 토큰 수 |
| `llm.usage.prompt_tokens` | int | 프롬프트 토큰 수 |
| `llm.usage.completion_tokens` | int | 완성 토큰 수 |

### 3.3 도구 호출 속성

| 속성 | 타입 | 설명 | 구현 상태 |
|------|------|------|----------|
| `gen_ai.tool.name` | string | 도구 이름 | ✅ 구현됨 |
| `gen_ai.tool.call.id` | string | 도구 호출 ID | ⚠️ 부분 구현 |
| `tool.arguments` | string | 도구 인자 (JSON) | ✅ 구현됨 |
| `tool.result` | string | 도구 결과 | ✅ 구현됨 |
| `tool.latency_ms` | float | 도구 지연 시간 | ✅ 구현됨 |
| `tool.success` | boolean | 성공 여부 | ✅ 구현됨 |

---

## 4. 표준 메트릭

### 4.1 Client Metrics (gen_ai.client.*)

| 메트릭 | 유형 | 단위 | 설명 | 구현 상태 |
|--------|------|------|------|----------|
| `gen_ai.client.token.usage` | Histogram | {token} | 토큰 사용량 | ⚠️ Span 속성으로 대체 |
| `gen_ai.client.operation.duration` | Histogram | s | 작업 시간 | ✅ Duration으로 구현 |

### 4.2 Server Metrics (gen_ai.server.*)

| 메트릭 | 유형 | 단위 | 설명 | 구현 상태 |
|--------|------|------|------|----------|
| `gen_ai.server.request.duration` | Histogram | s | 요청 처리 시간 | ✅ Duration으로 구현 |
| `gen_ai.server.time_per_output_token` | Histogram | s | 출력 토큰당 시간 | ❌ 미구현 |
| `gen_ai.server.time_to_first_token` | Histogram | s | 첫 토큰까지 시간 | ❌ 미구현 |

---

## 5. 비용 추적

### 5.1 비용 데이터 소스

OpenTelemetry Gen AI 표준에는 비용 속성이 정의되어 있지 않습니다. Agent Portal은 다음 소스에서 비용을 추출합니다:

| 우선순위 | 소스 | 속성/필드 | 설명 |
|---------|------|----------|------|
| 1 | OpenRouter | `llm.openrouter.usage.cost` | OpenRouter 응답 내 비용 |
| 2 | LiteLLM | `metadata.usage_object.cost` | LiteLLM 메타데이터 |
| 3 | 토큰 계산 | (tokens * pricing) | 폴백 계산 |

### 5.2 비용 추출 SQL

```sql
-- ClickHouse에서 비용 추출
sum(
    greatest(
        -- 1순위: OpenRouter usage 필드
        toFloat64OrZero(extractAll(
            SpanAttributes['llm.openrouter.usage'], 
            '\'cost\': ([0-9.]+)'
        )[1]),
        -- 2순위: metadata.usage_object
        toFloat64OrZero(extractAll(
            SpanAttributes['metadata.usage_object'], 
            'cost.: ([0-9.eE-]+)'
        )[1]),
        -- 3순위: 토큰 기반 계산
        (toUInt64OrZero(SpanAttributes['llm.usage.total_tokens']) * pricing)
    )
) as total_cost
```

### 5.3 제안: 표준 비용 속성 추가

향후 에이전트에서 다음 속성을 직접 기록하는 것을 권장합니다:

```python
# 제안 속성
gen_ai.usage.cost = 0.25  # USD
gen_ai.usage.cost_currency = "USD"
```

---

## 6. 현재 구현 vs 표준

### 6.1 구현 현황 요약

| 카테고리 | 표준 | 구현 | 격차 |
|---------|------|------|------|
| Span Names | gen_ai.* | gen_ai.session, gen_ai.tool.call | ⚠️ LLM span은 LiteLLM 제공 |
| 토큰 속성 | gen_ai.usage.* | llm.openrouter.usage | ⚠️ 표준 속성 미사용 |
| 비용 | (표준 없음) | llm.openrouter.usage.cost | ✅ 커스텀 구현 |
| 도구 호출 | gen_ai.tool.* | tool.* | ⚠️ 접두사 차이 |

### 6.2 마이그레이션 계획

**Phase 1 (현재)**: 레거시 호환성 유지
- LiteLLM/OpenRouter 속성 그대로 사용
- 모니터링 어댑터에서 다중 소스 지원

**Phase 2 (향후)**: 표준 속성 추가
- 에이전트에서 `gen_ai.usage.*` 속성 직접 기록
- 레거시 속성은 폴백으로 유지

**Phase 3 (장기)**: 표준 전환 완료
- `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` 활성화
- 레거시 속성 제거

---

## 7. 모니터링 대시보드 매핑

### 7.1 Overview 탭

| 표시 항목 | 데이터 소스 | ClickHouse 쿼리 |
|----------|------------|-----------------|
| Total Cost | llm.openrouter.usage.cost | `extractAll(llm.openrouter.usage, 'cost')` |
| LLM Calls | SpanName 필터 | `COUNT(DISTINCT TraceId)` |
| Agent Calls | ServiceName 필터 | `COUNT(DISTINCT TraceId)` |
| Avg Latency | Duration | `AVG(Duration) / 1000000` |
| Fail Rate | StatusCode | `COUNT(ERROR) / COUNT(*)` |

### 7.2 Traces 탭

| 서브탭 | 필터 조건 |
|--------|----------|
| Agent | `gen_ai.session`, `gen_ai.tool.call`, `text2sql`, `agent` |
| LLM Call | `litellm_request`, `raw_gen_ai_request`, `tokens > 0` |
| All | 모든 트레이스 |

---

## 8. ClickHouse 스키마

### 8.1 주요 컬럼

```sql
-- otel_2.otel_traces
TraceId             String
SpanId              String
ParentSpanId        String
SpanName            String
ServiceName         LowCardinality(String)
Duration            Int64  -- 나노초
Timestamp           DateTime64(9)
StatusCode          LowCardinality(String)
ResourceAttributes  Map(LowCardinality(String), String)
SpanAttributes      Map(LowCardinality(String), String)
```

### 8.2 표준 속성 저장 위치

| 속성 | 저장 위치 |
|------|----------|
| `gen_ai.request.model` | `SpanAttributes['gen_ai.request.model']` |
| `gen_ai.agent.id` | `SpanAttributes['gen_ai.agent.id']` |
| `project_id` | `ResourceAttributes['project_id']` |

---

## 9. 참조 문서

- [OpenTelemetry Gen AI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [Gen AI Metrics](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/)
- [Gen AI Agent Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)
- [Gen AI Model Spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/)
- [LiteLLM OpenTelemetry Docs](https://docs.litellm.ai/docs/proxy/logging)

---

## 10. Appendix: 현재 수집 매트릭 전체 목록

### 10.1 LiteLLM 제공 속성

```
SpanAttributes:
- gen_ai.completion.0.content
- gen_ai.completion.0.finish_reason
- gen_ai.completion.0.role
- gen_ai.prompt.*.content
- gen_ai.prompt.*.role
- llm.request.functions.*.name
- llm.request.functions.*.description
- llm.openrouter.usage (JSON: prompt_tokens, completion_tokens, total_tokens, cost)
- llm.openrouter.model
- llm.openrouter.provider
```

### 10.2 에이전트 커스텀 속성

```
SpanAttributes:
- gen_ai.agent.id
- gen_ai.agent.name
- gen_ai.request.model
- session.id
- tool.name
- tool.arguments
- tool.result
- tool.latency_ms
- tool.success
- tool.error
```

### 10.3 리소스 속성

```
ResourceAttributes:
- project_id
- service.name
- service.version
```

---

**Version**: 1.0
**Status**: Draft
**Author**: Agent Portal Team

