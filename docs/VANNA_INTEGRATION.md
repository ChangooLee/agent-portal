# Vanna AI Text-to-SQL Integration

> **Version**: 1.0.0 (2025-11-28)  
> **Purpose**: Document Vanna AI integration for natural language to SQL conversion

---

## Overview

Agent Portal integrates [Vanna AI](https://github.com/vanna-ai/vanna) as a Git submodule to provide intelligent Text-to-SQL capabilities. This integration uses LiteLLM as the backend LLM provider, enabling the use of any LLM model supported by LiteLLM (OpenRouter, OpenAI, Anthropic, etc.).

### Key Features

- **Schema-aware SQL Generation**: Automatically learns database schema for accurate SQL generation
- **Business Term Integration**: Supports custom business terminology mapping
- **SSE Streaming**: Real-time streaming of SQL generation progress
- **Multi-Database Support**: Works with MariaDB, PostgreSQL, ClickHouse
- **LiteLLM Backend**: Leverages existing LiteLLM infrastructure for model flexibility

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Frontend (SvelteKit)                       │
│                    /admin/datacloud/+page.svelte                │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/SSE
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend BFF (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ /vanna/      │  │ VannaAgent   │  │ LiteLLMVannaService  │  │
│  │ generate_sql │──│ Service      │──│ (Vanna LlmService)   │  │
│  │ chat_sse     │  │              │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LiteLLM Proxy (:4000)                        │
│                  (OpenRouter, OpenAI, etc.)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
agent-portal/
├── libs/
│   └── vanna/                 # Git submodule
│       └── src/vanna/
│           ├── core/          # Core interfaces (LlmService, Agent)
│           ├── integrations/  # DB integrations
│           └── servers/       # FastAPI/Flask servers
│
├── backend/app/
│   ├── services/
│   │   ├── vanna_llm_service.py   # LiteLLM adapter for Vanna
│   │   ├── vanna_agent_service.py # Agent management per connection
│   │   └── datacloud_service.py   # Calls Vanna for Text-to-SQL
│   └── routes/
│       └── vanna.py               # Vanna API endpoints
│
└── webui/
    └── vite.config.ts             # Proxy: /api/vanna → backend
```

---

## API Endpoints

### Generate SQL (Non-Streaming)

```http
POST /vanna/generate_sql
Content-Type: application/json

{
  "connection_id": "uuid",
  "question": "Show me top 10 customers by revenue"
}
```

**Response:**
```json
{
  "success": true,
  "sql": "SELECT customer_name, SUM(revenue) as total_revenue FROM customers GROUP BY customer_name ORDER BY total_revenue DESC LIMIT 10",
  "model": "gpt-4o-mini",
  "tokens_used": 150,
  "execution_time_ms": 1234
}
```

### Generate SQL (SSE Streaming)

```http
POST /vanna/chat_sse
Content-Type: application/json

{
  "connection_id": "uuid",
  "question": "Show me top 10 customers by revenue"
}
```

**Response (Server-Sent Events):**
```
data: {"type": "start", "data": {"message": "Generating SQL..."}}

data: {"type": "content", "data": {"delta": "SELECT"}}

data: {"type": "content", "data": {"delta": " customer_name"}}

data: {"type": "complete", "data": {"sql": "SELECT ...", "finish_reason": "stop"}}

data: [DONE]
```

### Train Agent

```http
POST /vanna/train
Content-Type: application/json

{
  "connection_id": "uuid",
  "refresh_schema": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Agent trained with 15 tables and 20 business terms",
  "tables_count": 15,
  "terms_count": 20
}
```

### Invalidate Cache

```http
DELETE /vanna/cache/{connection_id}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEXT_TO_SQL_MODEL` | `gpt-4o-mini` | LLM model for SQL generation |
| `LITELLM_HOST` | `http://litellm:4000` | LiteLLM proxy URL |
| `LITELLM_MASTER_KEY` | - | LiteLLM API key |

### Docker Configuration

The Vanna submodule is mounted read-only in the backend container:

```yaml
# docker-compose.yml
backend:
  volumes:
    - ./libs/vanna:/app/libs/vanna:ro
```

---

## Usage in Data Cloud UI

The Text-to-SQL feature is available in the Data Cloud admin page:

1. Navigate to `/admin/datacloud`
2. Select a database connection
3. Enter a natural language question
4. Click "SQL 생성" to generate SQL
5. Review and execute the generated SQL

---

## Testing

### Manual Testing

1. **Backend API Test:**
```bash
# Health check
curl http://localhost:8000/vanna/health

# Generate SQL
curl -X POST http://localhost:8000/vanna/generate_sql \
  -H "Content-Type: application/json" \
  -d '{"connection_id": "YOUR_CONNECTION_ID", "question": "Show all tables"}'
```

2. **Frontend Test:**
- Login to Agent Portal
- Navigate to Data Cloud → Select a connection
- Use the Text-to-SQL input

### Automated Tests

```bash
# Run pytest (when available)
cd backend
pytest tests/test_vanna.py -v
```

---

## Troubleshooting

### Common Issues

**1. "Agent not initialized" Error**
- Cause: Schema not loaded for the connection
- Fix: Call `/vanna/train` endpoint first, or use `refresh_schema: true`

**2. LLM API Timeout**
- Cause: LiteLLM proxy not responding
- Fix: Check LiteLLM status: `curl http://localhost:4000/health`

**3. Empty SQL Generated**
- Cause: Model didn't understand the question
- Fix: Check schema is properly loaded, refine the question

**4. Import Errors**
- Cause: Vanna submodule not mounted
- Fix: Verify `libs/vanna` exists and is mounted in Docker

---

## Development Notes

### Extending LLM Support

To add a new LLM provider, modify `vanna_llm_service.py`:

```python
class CustomLlmService(LlmService):
    async def send_request(self, request: LlmRequest) -> LlmResponse:
        # Custom implementation
        pass
```

### Adding Business Terms

Business terms are loaded from the `db_business_terms` table:

```sql
INSERT INTO db_business_terms 
(connection_id, technical_name, business_name, description)
VALUES 
('uuid', 'cust_id', '고객번호', '고유 고객 식별자');
```

---

## References

- [Vanna AI GitHub](https://github.com/vanna-ai/vanna)
- [Vanna Documentation](https://vanna.ai/docs/)
- [LiteLLM Documentation](https://docs.litellm.ai/)

---

**Last Updated**: 2025-11-28

