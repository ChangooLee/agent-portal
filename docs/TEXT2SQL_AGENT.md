# Text-to-SQL Agent 구현 문서

> **Version**: 1.0.0  
> **Last Updated**: 2025-12-03  
> **참조 설계 문서**: [docs/plans/DATA_CLOUD_AGENT.md](./plans/DATA_CLOUD_AGENT.md)

---

## 1. 개요

LangGraph 기반 Plan-and-Execute 패턴의 Text-to-SQL 에이전트입니다.  
자연어 질문을 받아 SQL을 생성하고, 실행 검증 후 최종 결과를 반환합니다.

### 주요 특징

- **Plan-and-Execute 패턴**: Planner가 JSON 플랜 생성 → Executor가 SQL 생성/검증/수정
- **ReAct 루프**: 실행 실패 시 에러 기반 SQL 수정 (최대 2회)
- **Multi-Dialect 지원**: PostgreSQL, MySQL, MariaDB, Oracle, ClickHouse, SAP HANA, Databricks
- **OTEL 통합**: OpenTelemetry 기반 traces/metrics 수집

---

## 2. 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│                    /text2sql/generate                           │
│                    /text2sql/generate/stream                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                          │
│                                                                 │
│  ┌──────────┐   ┌──────────────────┐   ┌────────────────────┐  │
│  │  entry   │ → │ dialect_resolver │ → │  schema_selector   │  │
│  └──────────┘   └──────────────────┘   └────────────────────┘  │
│                                                  │              │
│                                                  ▼              │
│  ┌────────────────┐   ┌────────────────┐   ┌──────────┐       │
│  │ sql_generator  │ ← │    planner     │ ← │          │       │
│  └────────────────┘   └────────────────┘   └──────────┘       │
│         │                                                       │
│         ▼                                                       │
│  ┌────────────────┐                                            │
│  │  sql_executor  │ ─┬─ 성공 ─→ answer_formatter → END        │
│  └────────────────┘  │                                         │
│         ▲            ├─ 실패 & retry < max ─→ sql_repair ──┐  │
│         │            │                                      │  │
│         └────────────┴─ 실패 & retry >= max ─→ human_review │  │
│                                                              │  │
│                      └───────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   LiteLLM    │  │  DataCloud   │  │  OTEL Collector      │  │
│  │  (LLM 호출)  │  │  (DB 스키마) │  │  (traces/metrics)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 파일 구조

```
backend/app/
├── agents/text2sql/
│   ├── __init__.py       # 모듈 진입점
│   ├── state.py          # SqlAgentState TypedDict
│   ├── nodes.py          # 9개 LangGraph 노드 함수
│   ├── graph.py          # StateGraph 구성 + Text2SQLAgent 클래스
│   ├── tools.py          # DB 스키마 조회/SQL 실행 도구
│   ├── prompts.py        # Dialect별 SQL 규칙 + 프롬프트 템플릿
│   └── metrics.py        # OTEL span/metric 헬퍼
├── telemetry/
│   ├── __init__.py
│   └── otel.py           # OpenTelemetry 초기화
└── routes/
    └── text2sql.py       # FastAPI 라우터
```

---

## 4. State 설계

`SqlAgentState`는 LangGraph 노드 간 데이터 전달에 사용되는 TypedDict입니다.

### 주요 필드

| 카테고리 | 필드 | 타입 | 설명 |
|---------|------|-----|------|
| **입력** | `question` | `str` | 사용자의 자연어 질문 |
| | `connection_id` | `str` | DB 연결 식별자 |
| **Dialect** | `dialect` | `Literal[...]` | DB 방언 (postgres, mysql, ...) |
| | `dialect_rules` | `str` | SQL 규칙 문자열 |
| **스키마** | `schema_summary` | `str` | 스키마 요약 문자열 |
| | `schema_graph` | `dict` | 테이블/관계 JSON |
| **플랜** | `plan` | `dict` | Planner 출력 JSON |
| **SQL** | `candidate_sql` | `list[str]` | SQL 후보 리스트 |
| | `chosen_sql` | `str` | 최종 선택 SQL |
| | `sql_reasoning` | `str` | LLM reasoning |
| **실행** | `execution_result` | `list[dict]` | 실행 결과 |
| | `execution_error` | `str` | 에러 메시지 |
| **재시도** | `retry_count` | `int` | 현재 재시도 횟수 |
| | `max_retries` | `int` | 최대 재시도 횟수 |
| **Human Review** | `needs_human_review` | `bool` | 사람 검토 필요 여부 |
| **출력** | `answer_summary` | `str` | 자연어 요약 |
| **OTEL** | `trace_id` | `str` | 트레이스 ID |
| | `metrics_tags` | `dict` | 메트릭 태그 |

---

## 5. 노드 설계

### 노드 목록

| # | 노드 | 책임 | OTEL Span |
|---|------|-----|-----------|
| 1 | `entry_node` | 초기 state 구성, 기본값 설정 | `text2sql.entry` |
| 2 | `dialect_resolver` | connection_id → dialect 매핑 | `text2sql.dialect_resolver` |
| 3 | `schema_selector` | 스키마 메타데이터 조회 | `text2sql.schema_selector` |
| 4 | `planner_node` | JSON 플랜 생성 (SQL 없이) | `text2sql.planner` |
| 5 | `sql_generator_node` | SQL 후보 생성 | `text2sql.generator` |
| 6 | `sql_executor_node` | SQL 실행 검증 | `text2sql.executor` |
| 7 | `sql_repair_node` | 에러 기반 SQL 수정 | `text2sql.repair` |
| 8 | `answer_formatter_node` | 최종 응답 생성 | `text2sql.answer_formatter` |
| 9 | `human_review_node` | Human-in-the-loop 처리 | `text2sql.human_review` |

### 그래프 흐름

```
entry → dialect_resolver → schema_selector → planner → sql_generator → sql_executor
                                                                           │
                            ┌──────────────────────────────────────────────┤
                            │                                              │
                            ▼                                              ▼
                     [execution_error?]                              [success]
                            │                                              │
           ┌────────────────┴────────────────┐                            ▼
           │                                 │                      answer_formatter
           ▼                                 ▼                             │
    [retry < max?]                    [retry >= max]                      ▼
           │                                 │                           END
           ▼                                 ▼
       sql_repair                      human_review
           │                                 │
           └──────→ sql_executor             ▼
                                            END
```

---

## 6. Dialect 지원

| Dialect | LIMIT 문법 | 식별자 인용 | 특이사항 |
|---------|-----------|------------|---------|
| PostgreSQL | `LIMIT n` | `"identifier"` | ANSI SQL 스타일 |
| MySQL/MariaDB | `LIMIT n` | `` `identifier` `` | 백틱 사용 |
| Oracle | `FETCH FIRST n ROWS ONLY` | `"identifier"` | LIMIT 사용 금지 |
| ClickHouse | `LIMIT n` | 백틱 또는 더블쿼트 | 집계 최적화 |
| SAP HANA | `LIMIT n` | `"identifier"` | 표준 SQL |
| Databricks | `LIMIT n` | 백틱 | Spark SQL 기반 |

---

## 7. API 엔드포인트

### POST /text2sql/generate

SQL 생성 (동기 방식)

**Request:**
```json
{
  "connection_id": "conn-abc123",
  "question": "최근 주문 10건을 보여줘",
  "max_retries": 2
}
```

**Response:**
```json
{
  "success": true,
  "sql": "SELECT * FROM orders ORDER BY created_at DESC LIMIT 10",
  "reasoning": "...",
  "answer_summary": "최근 주문 10건을 조회하는 쿼리입니다.",
  "dialect": "postgres",
  "execution_result": [...],
  "trace_id": "uuid-xxx",
  "needs_human_review": false
}
```

### POST /text2sql/generate/stream

SQL 생성 (SSE 스트리밍)

**Request:** 동일

**Response (SSE):**
```
data: {"event": "start", "data": {"trace_id": "..."}}
data: {"event": "node_complete", "node": "entry", "data": {...}}
data: {"event": "node_complete", "node": "dialect_resolver", "data": {...}}
...
data: {"event": "done", "data": {"success": true, "sql": "..."}}
```

### GET /text2sql/health

헬스체크

**Response:**
```json
{"status": "ok", "service": "text2sql"}
```

---

## 8. OTEL 메트릭

### Counters

| 메트릭 | 설명 |
|-------|------|
| `text2sql_requests_total` | 총 요청 수 |
| `text2sql_dialect_resolved_total` | Dialect 해석 성공/실패 |
| `text2sql_planning_errors_total` | 플래닝 에러 |
| `text2sql_generation_errors_total` | SQL 생성 에러 |
| `text2sql_execution_errors_total` | SQL 실행 에러 |
| `text2sql_requests_success_total` | 성공 요청 |
| `text2sql_retries_total` | 재시도 횟수 |
| `text2sql_answer_built_total` | 응답 생성 완료 |
| `text2sql_human_review_total` | Human review 필요 |

### Histograms

| 메트릭 | 설명 |
|-------|------|
| `text2sql_schema_fetch_latency_ms` | 스키마 조회 지연 |
| `text2sql_planning_latency_ms` | 플래닝 지연 |
| `text2sql_generation_latency_ms` | SQL 생성 지연 |
| `text2sql_execution_latency_ms` | SQL 실행 지연 |
| `text2sql_repair_latency_ms` | SQL 수정 지연 |
| `text2sql_total_latency_ms` | 전체 지연 |
| `text2sql_candidate_count` | SQL 후보 수 |
| `text2sql_execution_row_count` | 실행 결과 행 수 |

---

## 9. 환경 변수

| 변수 | 기본값 | 설명 |
|-----|--------|------|
| `TEXT2SQL_MODEL_PRIMARY` | `qwen-235b` | 기본 LLM 모델 |
| `TEXT2SQL_MAX_RETRIES` | `2` | 최대 재시도 횟수 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4317` | OTLP 엔드포인트 |
| `DEFAULT_PROJECT_ID` | `default-project` | 기본 프로젝트 ID |

---

## 10. 사용 예시

### Python (직접 호출)

```python
from app.agents.text2sql.graph import text2sql_agent

# 동기 실행
result = await text2sql_agent.run(
    question="최근 주문 10건을 보여줘",
    connection_id="conn-abc123"
)

print(result["chosen_sql"])
# SELECT * FROM orders ORDER BY created_at DESC LIMIT 10
```

### curl (API 호출)

```bash
curl -X POST http://localhost:8000/text2sql/generate \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": "conn-abc123",
    "question": "최근 주문 10건을 보여줘"
  }'
```

---

## 11. 마이그레이션 가이드 (Vanna → Text2SQL)

### API 변경점

| 기존 (Vanna) | 신규 (Text2SQL) |
|-------------|-----------------|
| `POST /vanna/generate_sql` | `POST /text2sql/generate` |
| `POST /vanna/chat_sse` | `POST /text2sql/generate/stream` |

### 코드 변경점

```python
# 기존 (Vanna)
from app.services.vanna_agent_service import vanna_agent_service
result = await vanna_agent_service.generate_sql(...)

# 신규 (Text2SQL)
from app.agents.text2sql.graph import text2sql_agent
result = await text2sql_agent.run(...)
```

### 응답 형식 변경

```python
# 기존
result.sql, result.success, result.error

# 신규
result["chosen_sql"], result.get("execution_error") is None, result.get("execution_error")
```

---

## 12. 관련 문서

- [설계 계획서](./plans/DATA_CLOUD_AGENT.md)
- [AGENTS.md](../AGENTS.md) - 프로젝트 구조
- [Data Cloud 개발 가이드](./plans/DATA_CLOUD_DEVELOPMENT.md)

