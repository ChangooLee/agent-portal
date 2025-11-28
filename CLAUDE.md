# CLAUDE.md — Agent Portal Quick Reference

> **Purpose**: Quick reference for AI agents working on Agent Portal

---

## Philosophy

### "Shoot and Forget" — Result-Oriented Delegation
- Provide clear context and goals to AI
- Evaluate by final PR quality, not process
- Human intervenes only at PR review stage

---

## Project Structure

```
agent-portal/
├── backend/                    # FastAPI BFF (port 8000)
│   ├── app/routes/            # API endpoints
│   ├── app/services/          # Business logic
│   └── app/middleware/        # RBAC, auth
│
├── webui/                      # Open-WebUI fork (port 3001)
│   └── src/routes/(app)/admin/ # Admin pages
│
├── config/                     # litellm.yaml, kong.yml
├── docker-compose.yml          # Service orchestration
└── docs/                       # Documentation
```

---

## Key Services

| Service | Port | Status |
|---------|------|--------|
| Backend BFF | 8000 | ✅ Running |
| Open-WebUI | 3001 | ✅ Running |
| LiteLLM | 4000 | ✅ Running |
| ClickHouse | 8124 | ✅ Running |
| Kong Gateway | 8002 | ✅ Running |
| MariaDB | 3306 | ✅ Running |

---

## Architecture

### Monitoring Pipeline
```
LiteLLM → OTEL Collector → ClickHouse → Backend BFF → Frontend
```

### Data Cloud
```
MariaDB/PostgreSQL/ClickHouse → SQLAlchemy → Backend BFF → Frontend
```

### MCP Gateway
```
MCP Servers → Kong Gateway → Backend Registry → Frontend Admin
```

---

## Quick Commands

### Backend
```bash
# Rebuild and restart
docker-compose build --no-cache backend && docker-compose up -d backend

# Check logs
docker-compose logs backend --tail=50

# Test API
curl http://localhost:8000/api/monitoring/metrics?...
```

### Frontend
```bash
# Dev server
cd webui && npm run dev

# Check browser at http://localhost:3001
```

### Database
```bash
# MariaDB
docker-compose exec mariadb mariadb -uroot -prootpass agent_portal

# ClickHouse
docker-compose exec monitoring-clickhouse clickhouse-client
```

---

## Rules Reference

See `.cursor/rules/` for detailed guides:
- `backend-api.mdc` — FastAPI patterns
- `ui-development.mdc` — Svelte/Tailwind patterns
- `admin-screens.mdc` — Admin UI patterns
- `monitoring-development.mdc` — ClickHouse queries
- `datacloud-development.mdc` — Database connector
- `mcp-gateway.mdc` — MCP server management

---

## Common Gotchas

1. **ClickHouse project_id**: Use `ResourceAttributes['project_id']`, NOT direct column
2. **Frontend API calls**: Use `/api/*` proxy, NOT `http://localhost:8000/*`
3. **Duration units**: ClickHouse stores nanoseconds, convert to ms: `Duration / 1000000`
4. **Container changes**: Rebuild with `--no-cache` after code changes

---

**Last Updated**: 2025-11-28
