# CLAUDE.md — Quick Reference

> Minimal cheat sheet for Agent Portal. See `AGENTS.md` for details.

---

## Project

Enterprise AI agent platform: Chat UI + LLM Gateway + Monitoring + Data Cloud + MCP Gateway

---

## Services

| Service | Port | Health |
|---------|------|--------|
| backend | 8000 | http://localhost:8000/docs |
| webui | 3001 | http://localhost:3001 |
| litellm | 4000 | http://localhost:4000/health |
| kong | 8002 | http://localhost:8002/status |
| clickhouse | 8124 | http://localhost:8124/ping |
| mariadb | 3306 | - |

---

## Quick Commands

```bash
# Health check
./scripts/health-check.sh

# Logs
docker compose logs <service> --tail=50 -f

# Rebuild
docker compose build --no-cache <service>
docker compose up -d <service>

# MariaDB
docker compose exec mariadb mariadb -uroot -prootpass agent_portal

# ClickHouse
docker compose exec monitoring-clickhouse clickhouse-client
```

---

## Key Locations

| What | Where |
|------|-------|
| Backend routes | `backend/app/routes/` |
| Backend services | `backend/app/services/` |
| Admin pages | `webui/src/routes/(app)/admin/` |
| AI rules | `.cursor/rules/*.mdc` |
| Vite proxy | `webui/vite.config.ts` |

---

## Critical Gotchas

1. **ClickHouse project_id**: `ResourceAttributes['project_id']` (NOT direct column)
2. **Frontend API**: Use `/api/*` proxy (NOT `http://localhost:8000`)
3. **Duration**: Nanoseconds in ClickHouse, divide by 1000000 for ms
4. **Container rebuild**: Use `--no-cache` after code changes

---

## Documentation

- `.cursorrules` — AI behavioral guidelines
- `AGENTS.md` — Full technical reference
- `.cursor/rules/` — Domain-specific rules

---

**Last Updated**: 2025-11-28
