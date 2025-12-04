# 에이전트 모니터링 자동 등록 시스템

> **Status**: ✅ 구현 완료 (2025-12-03)
> **참조**: [docs/AGENT_MONITORING.md](../AGENT_MONITORING.md) - 사용 가이드

## 아키텍처

```
[Agent Endpoint] → [Agent Registry] → [Trace Start]
       ↓                                    ↓
[LLM Call via LiteLLM] ←→ [Child Span with parent_trace_id]
       ↓                                    ↓
[Response] → [Trace End] → [ClickHouse/MariaDB]
       ↓
[Monitoring Dashboard] → [Overview: Agent Usage] + [Agent Detail Tab]
```

## 1. 에이전트 레지스트리 테이블 (MariaDB)

[backend/app/services/agent_registry_service.py](backend/app/services/agent_registry_service.py)

```sql
CREATE TABLE agents (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type ENUM('text2sql', 'langflow', 'flowise', 'autogen', 'custom') NOT NULL,
    project_id VARCHAR(255) DEFAULT 'default-project',
    external_id VARCHAR(255),  -- Langflow flow_id, Flowise chatflow_id
    config JSON,
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    UNIQUE KEY (name, project_id),
    INDEX idx_external (external_id)
);
```

## 2. 에이전트 등록 API

[backend/app/routes/agent_registry.py](backend/app/routes/agent_registry.py)

| Endpoint | Method | 용도 |
|----------|--------|------|
| `/agents/register` | POST | 에이전트 등록 (Langflow/Flowise/Text2SQL 호출) |
| `/agents/{agent_id}` | GET | 에이전트 상세 |
| `/agents` | GET | 에이전트 목록 |
| `/agents/{agent_id}/trace/start` | POST | 트레이스 시작 (trace_id 반환) |
| `/agents/{agent_id}/trace/end` | POST | 트레이스 종료 |

## 3. 에이전트 트레이스 어댑터

[backend/app/services/agent_trace_adapter.py](backend/app/services/agent_trace_adapter.py)

- OTEL Collector로 스팬 전송 (HTTP/gRPC)
- 또는 ClickHouse 직접 삽입
- parent_trace_id로 LLM 호출과 연결

## 4. 각 에이전트별 자동 등록 구현

### 4.1 Text2SQL Agent (LangGraph 기반)

[backend/app/agents/text2sql/](backend/app/agents/text2sql/) - 새로 구현됨

- **state.py**: SqlAgentState TypedDict
- **nodes.py**: 9개 LangGraph 노드 (entry, dialect_resolver, schema_selector, planner, sql_generator, sql_executor, sql_repair, answer_formatter, human_review)
- **graph.py**: StateGraph 구성 + Text2SQLAgent 클래스
- **metrics.py**: OTEL span/metric 헬퍼

```python
from app.agents.text2sql.graph import text2sql_agent

result = await text2sql_agent.run(
    question="최근 주문 10건 보여줘",
    connection_id="conn-abc123",
    trace_id=None  # 자동 생성
)
# result["chosen_sql"], result["trace_id"] 사용
```

### 4.2 Langflow/Flowise

[backend/app/services/langgraph_service.py](backend/app/services/langgraph_service.py)

- `_run_flow()` 실제 API 호출 구현
- Langflow: `POST http://langflow:7860/api/v1/run/{flow_id}`
- Flowise: `POST http://flowise:3000/api/v1/prediction/{chatflow_id}`
- 플로우 실행 전 자동 등록

### 4.3 AutoGen

[backend/app/routes/autogen.py](backend/app/routes/autogen.py) (선택적)

- AutoGen Studio API 연동
- 에이전트 생성 시 자동 등록

## 5. LiteLLM 메타데이터 연결

[backend/app/services/litellm_service.py](backend/app/services/litellm_service.py)

```python
async def chat_completion_sync(self, model, messages, metadata=None, **kwargs):
    payload = {
        "model": model,
        "messages": messages,
        "metadata": {
            "agent_id": metadata.get("agent_id") if metadata else None,
            "parent_trace_id": metadata.get("parent_trace_id") if metadata else None,
            **metadata or {}
        },
        **kwargs
    }
```

LiteLLM의 OTEL 콜백이 metadata를 SpanAttributes에 저장하여 에이전트 트레이스와 연결.

## 6. 모니터링 어댑터 개선

[backend/app/services/monitoring_adapter.py](backend/app/services/monitoring_adapter.py)

```python
async def get_agent_detail_stats(self, agent_id: str, ...):
    """개별 에이전트 상세 통계"""
    query = f"""
    SELECT ...
    FROM otel_traces
    WHERE SpanAttributes['metadata.agent_id'] = '{agent_id}'
    """
```

## 7. 모니터링 UI

### 7.1 Agent Usage 섹션

[webui/src/routes/(app)/admin/monitoring/+page.svelte](webui/src/routes/(app)/admin/monitoring/+page.svelte)

- 테이블에 "상세" 버튼 → 에이전트 상세 페이지로 이동

### 7.2 에이전트 상세 탭

[webui/src/routes/(app)/admin/monitoring/agents/[agent_id]/+page.svelte](webui/src/routes/(app)/admin/monitoring/agents/[agent_id]/+page.svelte)

- 개별 에이전트 메트릭 (호출수, 비용, 에러율)
- 해당 에이전트의 트레이스 목록
- 시간별 사용량 차트
- 하위 LLM 호출 연결 표시

## 8. 구현 완료 항목

| # | 항목 | 상태 |
|---|------|------|
| 1 | DB 스키마 생성 (`agents` 테이블) | ✅ |
| 2 | `agent_registry_service.py` 구현 | ✅ |
| 3 | `agent_trace_adapter.py` 구현 (OTEL 연동) | ✅ |
| 4 | `agent_registry.py` API 라우터 구현 | ✅ |
| 5 | Text2SQL Agent 구현 (LangGraph 기반) | ✅ |
| 6 | `langgraph_service.py` 수정 (실제 API 호출 + 자동 등록) | ✅ |
| 7 | `litellm_service.py` 수정 (metadata 전달) | ✅ |
| 8 | `monitoring_adapter.py` 수정 (agent_id 기반 쿼리) | ✅ |
| 9 | UI: Agent Usage 테이블에 상세 링크 추가 | ✅ |
| 10 | UI: 에이전트 상세 페이지 구현 | ✅ |

## 9. 문서

### 9.1 생성된 문서

| 문서 | 내용 |
|------|------|
| [docs/AGENT_MONITORING.md](../AGENT_MONITORING.md) | 에이전트 모니터링 설정 가이드, API 사용법 |
| [docs/AGENT_INTEGRATION_GUIDE.md](../AGENT_INTEGRATION_GUIDE.md) | Langflow/Flowise/AutoGen 연동 가이드 |
| [docs/TEXT2SQL_AGENT.md](../TEXT2SQL_AGENT.md) | Text2SQL Agent 구현 문서 |

### 9.2 업데이트된 문서

| 문서 | 업데이트 내용 |
|------|-------------|
| [AGENTS.md](../../AGENTS.md) | 에이전트 모니터링 아키텍처, API 레퍼런스 추가 |
| [docs/plans/DATA_CLOUD_AGENT.md](DATA_CLOUD_AGENT.md) | Text2SQL Agent 상세 설계 |

## 10. 테스트 체크리스트

- [x] 에이전트 자동 등록 동작 확인
- [x] 트레이스 시작/종료 ClickHouse 저장 확인
- [x] LLM 호출에 parent_trace_id 연결 확인
- [x] Agent Usage 통계 정확성 확인
- [x] 에이전트 상세 페이지 데이터 표시 확인
- [x] 에러 케이스 (에이전트 실패 시) 트레이스 기록 확인

---

**Last Updated**: 2025-12-03
