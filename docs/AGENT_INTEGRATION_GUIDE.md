# Agent Integration Guide

> **Version**: 1.0.0 (2025-12-01)
> **Purpose**: Langflow, Flowise, AutoGen 통합 가이드

---

## 1. Overview

Agent Portal은 다음 에이전트 빌더를 지원합니다:

| 에이전트 | 유형 | 포트 | 상태 |
|---------|------|------|------|
| Vanna AI | Text-to-SQL | - (내장) | 활성 |
| Langflow | Visual Flow Builder | 7860 | 선택적 |
| Flowise | Chatflow Builder | 3000 | 선택적 |
| AutoGen Studio | Multi-Agent | 8000 | 선택적 |

---

## 2. Langflow Integration

### 2.1 Prerequisites

```yaml
# docker-compose.yml에 추가
services:
  langflow:
    image: langflowai/langflow:latest
    ports:
      - "7860:7860"
    environment:
      - LANGFLOW_DATABASE_URL=sqlite:///./langflow.db
    volumes:
      - langflow_data:/app/langflow
```

### 2.2 Auto-Registration

Langflow 플로우 실행 시 자동으로 에이전트가 등록됩니다:

```python
from app.services.langgraph_service import langgraph_service

result = await langgraph_service.execute_langflow(
    flow_id="uuid-of-flow",
    inputs={"input_value": "Hello, world!"},
    tags=["production"]
)

# result:
# {
#     "success": True,
#     "result": {"output": "..."},
#     "trace_id": "...",
#     "agent_id": "...",
#     "execution_time_ms": 1234
# }
```

### 2.3 Sync Flows to Registry

```python
# 모든 Langflow 플로우를 에이전트 레지스트리에 동기화
registered = await langgraph_service.sync_langflow_flows()
print(f"Synced {len(registered)} flows")
```

### 2.4 API Endpoint

```http
POST /api/agents/langflow/{flow_id}/run
Content-Type: application/json

{
    "input_value": "Hello",
    "tweaks": {}
}
```

---

## 3. Flowise Integration

### 3.1 Prerequisites

```yaml
# docker-compose.yml에 추가
services:
  flowise:
    image: flowiseai/flowise:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_PATH=/root/.flowise
    volumes:
      - flowise_data:/root/.flowise
```

### 3.2 Auto-Registration

```python
from app.services.langgraph_service import langgraph_service

result = await langgraph_service.execute_flowise(
    chatflow_id="uuid-of-chatflow",
    question="What is AI?",
    history=[],
    tags=["production"]
)
```

### 3.3 Sync Chatflows

```python
registered = await langgraph_service.sync_flowise_chatflows()
```

---

## 4. AutoGen Integration

### 4.1 Prerequisites

```yaml
# docker-compose.yml에 추가
services:
  autogen-api:
    build: ./autogen
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

### 4.2 Execution

```python
from app.services.langgraph_service import langgraph_service

result = await langgraph_service.execute_autogen(
    agent_id="uuid-of-agent",
    task="Analyze this data and provide insights",
    context={"data": [...]}
)
```

---

## 5. Custom Agent Integration

### 5.1 Register Agent

```python
from app.services.agent_registry_service import agent_registry, AgentType

agent = await agent_registry.register_or_get(
    name="my-custom-agent",
    agent_type=AgentType.CUSTOM,
    project_id="default-project",
    external_id="external-system-id",
    description="Custom agent for specific tasks",
    config={
        "model": "gpt-4",
        "temperature": 0.7
    }
)
```

### 5.2 Start/End Trace

```python
from app.services.agent_trace_adapter import agent_trace_adapter

# Start
trace_id = await agent_trace_adapter.start_trace(
    agent_id=agent['id'],
    agent_name=agent['name'],
    agent_type='custom',
    project_id='default-project',
    inputs={"task": "Do something"},
    tags=["production"]
)

# Execute your logic...

# End (success)
await agent_trace_adapter.end_trace(
    trace_id=trace_id,
    outputs={"result": "Success"},
    cost=0.01,
    tokens=500
)

# End (error)
await agent_trace_adapter.end_trace(
    trace_id=trace_id,
    error="Something went wrong"
)
```

### 5.3 LLM Calls with Agent Context

LLM 호출 시 metadata에 agent 정보를 포함하면 트레이스가 연결됩니다:

```python
from app.services.litellm_service import litellm_service

response = await litellm_service.chat_completion_sync(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    metadata={
        "agent_id": agent['id'],
        "agent_name": agent['name'],
        "parent_trace_id": trace_id
    }
)
```

---

## 6. Monitoring

### 6.1 Agent Usage Dashboard

`/admin/monitoring` > Overview > Agent Usage:
- 에이전트별 호출 수, 토큰, 비용, 에러율
- "Details" 클릭으로 상세 페이지 이동

### 6.2 Agent Detail Page

`/admin/monitoring/agents/{agent_id}`:
- 총 트레이스, 토큰, 비용, 성공률
- 레이턴시 통계 (Avg/P50/P95)
- 최근 트레이스 목록
- 시간별 호출 트렌드

### 6.3 API Queries

```bash
# 에이전트 목록
curl "http://localhost:8000/agents?project_id=default-project"

# 에이전트 사용량 통계
curl "http://localhost:8000/monitoring/agents/usage?project_id=default-project&start_time=2025-01-01T00:00:00Z&end_time=2025-01-02T00:00:00Z"

# 에이전트 상세 통계
curl "http://localhost:8000/monitoring/agents/{agent_id}/detail?start_time=...&end_time=..."
```

---

## 7. Troubleshooting

### 7.1 Langflow Connection Failed

```bash
# Langflow 컨테이너 상태 확인
docker compose ps langflow

# Langflow API 테스트
curl http://localhost:7860/api/v1/flows/
```

### 7.2 Flowise Connection Failed

```bash
# Flowise 상태 확인
docker compose ps flowise

# Flowise API 테스트
curl http://localhost:3000/api/v1/chatflows
```

### 7.3 Agent Not Appearing in Monitoring

1. 에이전트가 등록되었는지 확인:
```bash
docker exec agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal \
  -e "SELECT * FROM agents ORDER BY created_at DESC LIMIT 5;"
```

2. 트레이스가 ClickHouse에 저장되었는지 확인:
```bash
docker exec monitoring-clickhouse clickhouse-client \
  --query "SELECT count() FROM otel_2.otel_traces WHERE SpanAttributes['metadata.agent_id'] != ''"
```

---

## 8. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGFLOW_URL` | `http://langflow:7860` | Langflow API URL |
| `FLOWISE_URL` | `http://flowise:3000` | Flowise API URL |
| `AUTOGEN_URL` | `http://autogen-api:8000` | AutoGen API URL |
| `DEFAULT_PROJECT_ID` | `default-project` | 기본 프로젝트 ID |

---

**Last Updated**: 2025-12-01

