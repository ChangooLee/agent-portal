# AGENTS.md — AI Agent Guide

> **Purpose**: Guide for AI agents (Claude Code, Cursor AI) to understand and work on Agent Portal  
> **Reference**: [Claude Code Usage Guide](https://news.hada.io/topic?id=24099)

---

## Project Overview

Agent Portal is an enterprise AI agent management platform built on Open-WebUI, integrating:
- **LiteLLM**: Multi-LLM gateway
- **Monitoring**: ClickHouse-based observability (OTEL traces)
- **Data Cloud**: Zero-copy database connectors
- **MCP Gateway**: Model Context Protocol server management
- **Agent Builders**: Langflow, Flowise, AutoGen Studio

---

## Directory Structure

```
agent-portal/
├── backend/                    # FastAPI BFF (port 8000)
│   ├── app/
│   │   ├── routes/            # API endpoints
│   │   │   ├── chat.py        # Chat API
│   │   │   ├── monitoring.py  # Monitoring API
│   │   │   ├── datacloud.py   # Data Cloud API
│   │   │   ├── mcp.py         # MCP API
│   │   │   └── gateway.py     # Gateway API
│   │   ├── services/          # Business logic
│   │   │   ├── litellm_service.py
│   │   │   ├── monitoring_adapter.py
│   │   │   ├── datacloud_service.py
│   │   │   └── mcp_registry.py
│   │   └── main.py            # FastAPI app
│   └── requirements.txt
│
├── webui/                      # Open-WebUI (port 3001)
│   └── src/routes/(app)/admin/
│       ├── monitoring/        # Monitoring dashboard
│       ├── datacloud/         # Data Cloud management
│       ├── mcp/               # MCP server management
│       └── gateway/           # Gateway overview
│
├── config/
│   ├── litellm.yaml           # LiteLLM configuration
│   └── kong.yml               # Kong Gateway configuration
│
├── docker-compose.yml          # Service orchestration
└── docs/                       # Documentation
```

---

## Service Status

| Service | Port | Role | Status |
|---------|------|------|--------|
| Backend BFF | 8000 | FastAPI gateway | ✅ |
| Open-WebUI | 3001 | Portal UI | ✅ |
| LiteLLM | 4000 | LLM proxy | ✅ |
| OTEL Collector | 4317/4318 | Trace collection | ✅ |
| ClickHouse | 8124 | Trace storage | ✅ |
| Kong | 8002 | API Gateway | ✅ |
| MariaDB | 3306 | App database | ✅ |
| Langflow | 7861 | Agent builder | ✅ |
| Flowise | 3002 | Agent builder | ✅ |
| AutoGen Studio | 5050 | Agent builder | ✅ |

---

## Development Stages

### Stage 1: Infrastructure ✅ Complete
- Kong Gateway setup
- Docker Compose orchestration

### Stage 2: Core APIs ✅ Complete
- Chat API (`/chat/stream`, `/chat/completions`)
- Observability API (`/observability/*`)
- Monitoring API (ClickHouse integration)
- LiteLLM → OTEL → ClickHouse pipeline

### Stage 3: Agent Builders ✅ Complete
- Langflow/Flowise/AutoGen Studio embedding
- Reverse proxy implementation

### Stage 4: Data Cloud ✅ Complete
- Zero-copy database connector
- Schema reflection
- Query execution
- Text-to-SQL via LiteLLM
- Business terminology management
- Permission management

### Stage 5: MCP Gateway ✅ Complete
- MCP server registration
- Tool discovery
- Kong integration

---

## API Patterns

### Service Layer (Singleton)

```python
# backend/app/services/example_service.py
class ExampleService:
    def __init__(self):
        self.base_url = "http://service:8080"
    
    async def get_data(self, id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/{id}")
            response.raise_for_status()
            return response.json()

example_service = ExampleService()  # Singleton
```

### Router Pattern

```python
# backend/app/routes/example.py
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/example", tags=["example"])

@router.get("/{id}")
async def get_example(id: str):
    try:
        return await example_service.get_data(id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Error Handling

```python
try:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
except httpx.TimeoutException:
    raise HTTPException(status_code=504, detail="Timeout")
except httpx.HTTPStatusError as e:
    raise HTTPException(status_code=e.response.status_code, detail=str(e))
```

---

## ClickHouse Queries

### Important: project_id Location

```sql
-- ❌ WRONG: project_id is NOT a direct column
SELECT * FROM otel_traces WHERE project_id = '...'

-- ✅ CORRECT: project_id is in ResourceAttributes map
SELECT * FROM otel_traces WHERE ResourceAttributes['project_id'] = '...'
```

### Duration Conversion

```sql
-- Duration is stored in nanoseconds, convert to milliseconds
SELECT Duration / 1000000 as duration_ms FROM otel_traces
```

### Example Query

```python
query = f"""
SELECT 
    TraceId as trace_id,
    SpanName as span_name,
    Duration / 1000000 as duration_ms,
    ResourceAttributes['project_id'] as project_id
FROM otel_2.otel_traces
WHERE ResourceAttributes['project_id'] = '{project_id}'
    AND Timestamp >= '{start_time}'
ORDER BY Timestamp DESC
"""
```

---

## Frontend Patterns

### API Proxy

```typescript
// ❌ WRONG: Direct backend call
fetch('http://localhost:8000/api/...')

// ✅ CORRECT: Use Vite proxy
fetch('/api/...')
```

### Glassmorphism Card

```svelte
<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl 
            border border-white/20 dark:border-gray-700/20 shadow-sm p-6">
  <!-- Content -->
</div>
```

### Modal Pattern

```svelte
{#if showModal}
<div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50">
  <div class="bg-white dark:bg-gray-800 rounded-2xl max-w-2xl mx-auto mt-20">
    <!-- Modal content -->
  </div>
</div>
{/if}
```

---

## Common Troubleshooting

### Container Not Updated
```bash
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Router Not Registered
1. Check import in `main.py`
2. Verify `app.include_router()` call
3. Check container file: `docker-compose exec backend cat /app/app/main.py`

### CORS Error
- Use `/api/*` proxy in frontend, not direct `localhost:8000` calls
- Check `webui/vite.config.ts` for proxy rules

### ClickHouse Query Fails
- Check column exists: `DESCRIBE otel_2.otel_traces`
- Use `ResourceAttributes['key']` for map access
- Check database name: `otel_2` not `otel`

---

## Task Completion Checklist

- [ ] Code written
- [ ] Service restarted (if backend)
- [ ] API tested with curl
- [ ] Browser tested (if frontend)
- [ ] Console errors checked
- [ ] Documentation updated (if significant)

---

**Last Updated**: 2025-11-28  
**Version**: 3.0 (English, optimized)
