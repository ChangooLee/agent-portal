# Agent Monitoring Guide

> **Version**: 1.0.0 (2025-12-01)
> **Purpose**: 에이전트 모니터링 시스템 설정 및 사용 가이드

---

## 1. Overview

Agent Portal은 다양한 AI 에이전트(Vanna, Langflow, Flowise, AutoGen)를 통합 모니터링합니다.

### 1.1 주요 기능

- **자동 에이전트 등록**: 첫 실행 시 자동으로 에이전트 레지스트리에 등록
- **트레이스 추적**: 에이전트 실행의 시작과 종료를 추적
- **LLM 호출 연결**: 에이전트 트레이스와 하위 LLM 호출을 연결
- **통합 대시보드**: 모니터링 화면에서 모든 에이전트 통계 조회

### 1.2 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Execution                             │
│  (Vanna Text-to-SQL, Langflow Flow, Flowise Chatflow, etc.)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Registry Service                        │
│              (MariaDB: agents table)                             │
│  - Auto-registration on first run                                │
│  - Stores agent metadata (name, type, external_id)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Trace Adapter                           │
│  - Start trace → returns trace_id                                │
│  - End trace → saves to ClickHouse                               │
│  - Provides parent_trace_id for LLM calls                       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌───────────────────────┐             ┌───────────────────────┐
│     ClickHouse        │             │       LiteLLM         │
│   (otel_2.otel_traces)│◄────────────│  (OTEL Callback)      │
│                       │   metadata  │  - agent_id           │
│ SpanAttributes:       │   includes  │  - parent_trace_id    │
│ - metadata.agent_id   │             │                       │
│ - metadata.agent_name │             │                       │
└───────────────────────┘             └───────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Monitoring Dashboard                          │
│  - Agent Usage Overview                                          │
│  - Agent Detail Page (/admin/monitoring/agents/{agent_id})      │
│  - Trace linkage                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema

### 2.1 agents Table (MariaDB)

```sql
CREATE TABLE agents (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type ENUM('vanna', 'langflow', 'flowise', 'autogen', 'custom') NOT NULL,
    project_id VARCHAR(255) NOT NULL DEFAULT 'default-project',
    external_id VARCHAR(255),
    description TEXT,
    config JSON,
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP NULL,
    UNIQUE KEY uk_name_project (name, project_id),
    INDEX idx_type (type),
    INDEX idx_project (project_id),
    INDEX idx_external (external_id),
    INDEX idx_status (status)
);
```

### 2.2 ClickHouse SpanAttributes

에이전트 트레이스는 다음 속성을 포함합니다:

| Attribute | Description |
|-----------|-------------|
| `metadata.agent_id` | 에이전트 UUID |
| `metadata.agent_name` | 에이전트 이름 |
| `metadata.parent_trace_id` | 상위 트레이스 ID (LLM 호출 연결용) |
| `agent.type` | 에이전트 유형 (vanna, langflow, flowise, autogen) |
| `agent.inputs` | 입력 데이터 (JSON) |
| `agent.outputs` | 출력 데이터 (JSON) |

---

## 3. API Reference

### 3.1 Agent Registry API

**Register Agent**
```http
POST /agents/register
Content-Type: application/json

{
    "name": "vanna-abc12345",
    "type": "vanna",
    "project_id": "default-project",
    "external_id": "connection-uuid",
    "description": "Text-to-SQL agent for ClickHouse"
}
```

**List Agents**
```http
GET /agents?project_id=default-project&type=vanna&limit=100
```

**Get Agent Detail**
```http
GET /agents/{agent_id}
```

**Start Trace**
```http
POST /agents/{agent_id}/trace/start
Content-Type: application/json

{
    "inputs": {"question": "Show all users"},
    "tags": ["production"]
}

Response:
{
    "trace_id": "abc123...",
    "agent_id": "...",
    "agent_name": "vanna-abc12345"
}
```

**End Trace**
```http
POST /agents/{agent_id}/trace/end
Content-Type: application/json

{
    "trace_id": "abc123...",
    "outputs": {"sql": "SELECT * FROM users LIMIT 100"},
    "cost": 0.001,
    "tokens": 150
}
```

### 3.2 Monitoring API

**Agent Usage Stats**
```http
GET /monitoring/agents/usage?project_id=default-project&start_time=2025-01-01T00:00:00Z&end_time=2025-01-02T00:00:00Z
```

**Agent Detail Stats**
```http
GET /monitoring/agents/{agent_id}/detail?start_time=...&end_time=...
```

---

## 4. Integration Guide

### 4.1 Vanna Agent (Automatic)

Vanna Agent는 `generate_sql` 호출 시 자동으로:
1. 에이전트 등록 (`vanna-{connection_id[:8]}`)
2. 트레이스 시작
3. SQL 생성 (LiteLLM 호출 with metadata)
4. 트레이스 종료

```python
# vanna_agent_service.py에서 자동 처리
result = await vanna_agent_service.generate_sql(
    connection_id="...",
    question="Show all users"
)
# result.metadata에 agent_id, trace_id 포함
```

### 4.2 Langflow/Flowise Integration

```python
from app.services.langgraph_service import langgraph_service

# Langflow 플로우 실행 (자동 등록 + 트레이스)
result = await langgraph_service.execute_langflow(
    flow_id="langflow-uuid",
    inputs={"input_value": "Hello"},
    tags=["production"]
)
```

### 4.3 Custom Agent

```python
from app.services.agent_registry_service import agent_registry, AgentType
from app.services.agent_trace_adapter import agent_trace_adapter

# 1. 에이전트 등록
agent = await agent_registry.register_or_get(
    name="my-custom-agent",
    agent_type=AgentType.CUSTOM,
    description="Custom agent for special tasks"
)

# 2. 트레이스 시작
trace_id = await agent_trace_adapter.start_trace(
    agent_id=agent['id'],
    agent_name=agent['name'],
    agent_type='custom',
    inputs={"task": "Do something"}
)

# 3. 작업 수행 (LLM 호출 시 metadata에 trace_id 포함)
# ...

# 4. 트레이스 종료
await agent_trace_adapter.end_trace(
    trace_id=trace_id,
    outputs={"result": "Done"},
    tokens=100,
    cost=0.001
)
```

---

## 5. Monitoring Dashboard

### 5.1 Agent Usage Section

모니터링 > Overview > Agent Usage 섹션에서:
- 에이전트별 호출 수, 토큰, 비용, 레이턴시, 에러율 확인
- "Details" 버튼으로 상세 페이지 이동

### 5.2 Agent Detail Page

`/admin/monitoring/agents/{agent_id}` 에서:
- 총 트레이스 수, 토큰, 비용, 성공률
- 평균/P50/P95 레이턴시
- 최근 50개 트레이스 목록
- 시간별 호출 트렌드

---

## 6. Troubleshooting

### 6.1 에이전트가 등록되지 않음

```bash
# MariaDB agents 테이블 확인
docker exec agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal \
  -e "SELECT * FROM agents ORDER BY created_at DESC LIMIT 5;"
```

### 6.2 트레이스가 ClickHouse에 저장되지 않음

```bash
# ClickHouse 트레이스 확인
docker exec monitoring-clickhouse clickhouse-client \
  --query "SELECT count() FROM otel_2.otel_traces WHERE SpanAttributes['metadata.agent_id'] != ''"
```

### 6.3 Agent Usage가 0으로 표시됨

1. 프로젝트 ID 확인 (기본: `default-project`)
2. 시간 범위 확인 (마지막 24시간)
3. WebSocket 연결 확인 (브라우저 콘솔)

---

## 7. Best Practices

1. **의미있는 에이전트 이름 사용**
   - 좋음: `vanna-clickhouse-prod`, `langflow-customer-support`
   - 나쁨: `agent-1`, `test`

2. **트레이스 태그 활용**
   - `["production"]`, `["staging"]`, `["test"]`
   - 필터링 및 분석에 유용

3. **에러 메시지 포함**
   - `end_trace` 시 `error` 파라미터로 에러 상세 기록

---

**Last Updated**: 2025-12-01

