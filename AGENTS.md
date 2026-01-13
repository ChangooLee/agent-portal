# AGENTS.md — Agent Portal Technical Reference

> **Purpose**: Define WHAT the project is and WHERE things are located
> **Audience**: AI agents (Claude, Cursor) working on this codebase
> **Version**: 5.3 (2025-12-11)

---

## 1. Project Overview

### 1.1 What is Agent Portal?

Enterprise AI agent management platform built on Open-WebUI, providing:
- **Unified Chat Interface**: Multi-LLM access via LiteLLM gateway
- **Monitoring Dashboard**: Real-time LLM call observability via OTEL/ClickHouse
- **Data Cloud**: Zero-copy database connectors with Text-to-SQL
- **MCP Gateway**: Model Context Protocol server management via Kong
- **Agent Builders**: Embedded Langflow, Flowise, AutoGen Studio

### 1.2 Critical Development Rule: Common Infrastructure Protection

**⚠️ IMPORTANT**: 사용자의 명시적 요청이 없는 한, 다음 공통 인프라 구성 요소는 수정하지 마세요:

| Component | Location | Purpose | Why Protected |
|-----------|----------|---------|---------------|
| **LiteLLM Gateway** | `config/litellm.yaml`, `docker-compose.yml` (litellm service) | LLM 통합 게이트웨이 | 모든 에이전트와 서비스에서 사용하는 핵심 인프라 |
| **Kong Gateway** | `config/kong.yml`, `docker-compose.yml` (kong service) | API 게이트웨이 | MCP, DataCloud 등 여러 서비스의 라우팅 담당 |
| **MariaDB Schema** | `scripts/init-*.sql` | 애플리케이션 데이터베이스 | 모든 서비스의 데이터 저장소 |
| **ClickHouse Schema** | Monitoring setup | 트레이스 저장소 | 모든 에이전트의 관측 데이터 저장 |
| **OTEL Collector** | `docker-compose.yml` (otel-collector) | 텔레메트리 수집 | 모든 서비스의 관측 파이프라인 |
| **Docker Compose Base** | `docker-compose.yml` | 서비스 오케스트레이션 | 전체 시스템의 기반 인프라 |

**수정 허용 조건**:
- ✅ 사용자가 명시적으로 요청한 경우
- ✅ 버그 수정이 필요한 경우 (하지만 먼저 사용자에게 보고)
- ✅ 새로운 기능 추가가 필요한 경우 (하지만 먼저 사용자에게 확인)

**수정 금지 시나리오**:
- ❌ "작동하지 않아서" 임시로 우회하기 위해 수정
- ❌ 다른 기능 개발 중 "편의상" 수정
- ❌ 테스트를 위해 임시로 수정

**대신 해야 할 것**:
1. 문제 발생 시 원인 분석 후 사용자에게 보고
2. 해결 방안 2-3가지 제시 (우회책 제외)
3. 사용자 승인 후 진행

### 1.3 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | SvelteKit, Tailwind CSS, TypeScript |
| Backend | FastAPI (Python 3.11), httpx |
| LLM Gateway | LiteLLM Proxy |
| API Gateway | Kong |
| Databases | MariaDB (app), ClickHouse (traces), PostgreSQL (LiteLLM) |
| Observability | OTEL Collector, Prometheus |
| Infrastructure | Docker Compose |

---

## 2. Architecture

### 2.1 System Topology

**Single Port Architecture (Port 3009)**

모든 서비스가 단일 포트(3009)를 통해 접근됩니다. BFF가 메인 엔트리 포인트로 동작하며, WebUI Backend와 Kong Gateway를 프록시합니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                      http://localhost:3010                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Backend BFF (port 3009)                       │
│                         FastAPI                                  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│  │   Chat   │ Monitor  │DataCloud │   MCP    │ Gateway  │       │
│  │  /chat   │/monitor  │/datacloud│  /mcp    │/gateway  │       │
│  │/api/webui│          │          │          │          │       │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘       │
└───────┼──────────┼──────────┼──────────┼──────────┼─────────────┘
        │          │          │          │          │
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ WebUI   │ │ LiteLLM │ │ClickHs  │ │ MariaDB │ │  Kong   │
   │:3001/8080│ │  :4000  │ │  :8124  │ │  :3306  │ │  :8000  │
   │(internal)│ │         │ │         │ │         │ │(internal)│
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
        │          │          │          │          │
        │          │          │          │          │
        │          │          ▼          │          ▼
        │          │    ┌─────────┐     │    ┌─────────┐
        │          │    │  OTEL   │     │    │   MCP   │
        │          │    │Collector│     │    │ Servers │
        │          │    │ :4317/8 │     │    └─────────┘
        │          │    └─────────┘     │
        │          │          │         │
        │          │          ▼         │
        │          │    ┌─────────┐     │
        │          │    │ClickHouse│     │
        │          │    │  :8124  │     │
        │          │    └─────────┘     │
        │          │                    │
        └──────────┴────────────────────┘
                    (All via BFF)
```

### 2.2 Data Flows

**WebUI Frontend Flow**:
```
Browser → BFF (3009) → Vite Dev Server (3001, internal) or Static Files
```

**WebUI Backend Flow**:
```
Browser → BFF (3009) → WebUI Backend (8080, internal)
```

**Monitoring Pipeline**:
```
LiteLLM → OTEL Collector → ClickHouse → Backend BFF (3009) → Frontend
```

**Data Cloud Pipeline**:
```
Browser → BFF (3009) → Kong (8000, internal) → Databases
```

**MCP Gateway Pipeline**:
```
Browser → BFF (3009) → Kong (8000, internal) → MCP Servers
```

---

## 3. Service Catalog

### 3.1 Core Services

| Service | External Port | Internal Port | Container | Health Check | Purpose |
|---------|--------------|---------------|-----------|--------------|---------|
| backend | 3009 | 3009 | agent-portal-backend-1 | http://localhost:3010/health | FastAPI BFF (Main Entry Point) |
| webui | - | 3001 (Vite), 8080 (Backend) | agent-portal-webui-1 | Via BFF proxy | Portal UI (SvelteKit + Open-WebUI) |
| litellm | 4000 | 4000 | agent-portal-litellm-1 | http://localhost:4000/health | LLM Proxy |
| kong | 8004 | 8000 (Proxy), 8001 (Admin) | agent-portal-kong-1 | http://localhost:8004/status | API Gateway (Internal only) |
| mariadb | 3306 | 3306 | agent-portal-mariadb-1 | - | App Database |
| clickhouse | 8124 | 8123 | monitoring-clickhouse | http://localhost:8124/ping | Trace Storage |

### 3.2 Support Services

| Service | Port | Container | Purpose |
|---------|------|-----------|---------|
| redis | 6379 | agent-portal-redis-1 | Cache |
| prometheus | 9090 | agent-portal-prometheus-1 | Metrics |
| chromadb | 8001 | agent-portal-chromadb-1 | Vector DB |
| minio | 9000/9001 | agent-portal-minio-1 | Object Storage |
| otel-collector | 4317/4318 | monitoring-otel-collector | Trace Collection |

### 3.3 Database Connections

**MariaDB (App Data)** — Used by Backend BFF:
```bash
docker compose exec mariadb mariadb -uroot -prootpass agent_portal
```

> **Note**: WebUI (Open-WebUI) uses SQLite by default. Data is stored in `webui_data` Docker volume.

**ClickHouse (Traces)**:
```bash
docker compose exec monitoring-clickhouse clickhouse-client
# Or HTTP: curl http://localhost:8124/?query=SELECT%201
```

**PostgreSQL (LiteLLM)**:
```bash
docker compose exec litellm-postgres psql -U litellm -d litellm_db
```

---

## 4. Directory Structure

### 4.1 Project Layout

```
agent-portal/
├── backend/                    # FastAPI BFF
│   ├── app/
│   │   ├── main.py            # App entry, router registration
│   │   ├── routes/            # API endpoints
│   │   │   ├── chat.py        # /chat/*
│   │   │   ├── monitoring.py  # /monitoring/*
│   │   │   ├── datacloud.py   # /datacloud/*
│   │   │   ├── mcp.py         # /mcp/*
│   │   │   └── gateway.py     # /gateway/*
│   │   ├── services/          # Business logic (singletons)
│   │   │   ├── litellm_service.py
│   │   │   ├── monitoring_adapter.py
│   │   │   ├── datacloud_service.py
│   │   │   └── mcp_registry.py
│   ├── agents/text2sql/           # LangGraph Text-to-SQL Agent
│   │   │   ├── state.py          # Agent state definition
│   │   │   ├── nodes.py          # LangGraph nodes (9 nodes)
│   │   │   ├── graph.py          # StateGraph configuration
│   │   │   ├── tools.py          # DB tools
│   │   │   ├── prompts.py        # Dialect-specific prompts
│   │   │   └── metrics.py        # OTEL metrics
│   │   └── middleware/        # RBAC, auth
│   └── requirements.txt
│
├── webui/                      # Open-WebUI fork (SvelteKit)
│   ├── src/
│   │   ├── routes/
│   │   │   └── (app)/
│   │   │       ├── +page.svelte       # Chat page
│   │   │       ├── build/              # Build menu pages
│   │   │       │   ├── agents/        # Agent development
│   │   │       │   ├── llm/           # LLM model management
│   │   │       │   ├── mcp/           # MCP server management
│   │   │       │   ├── datacloud/     # Data Cloud management
│   │   │       │   ├── guardrails/    # Guardrails configuration
│   │   │       │   └── evaluations/   # Model evaluations
│   │   │       ├── operate/            # Operate menu pages
│   │   │       │   ├── monitoring/    # Monitoring dashboard
│   │   │       │   ├── gateway/       # Gateway overview
│   │   │       │   ├── users/         # User management
│   │   │       │   └── settings/      # System settings
│   │   │       └── projects/          # Project management
│   │   └── lib/
│   │       ├── components/    # Shared components
│   │       └── monitoring/    # Monitoring-specific components
│   ├── vite.config.ts         # Proxy configuration
│   └── .skills/               # AI reference files
│       └── ui-summary.json    # Quick route/pattern lookup
│
├── libs/
│   └── (empty)                # Reserved for future external libraries
│
├── config/
│   ├── litellm.yaml           # LiteLLM model configuration
│   ├── kong.yml               # Kong Gateway configuration
│   └── prometheus.yml         # Prometheus scrape config
│
├── scripts/
│   ├── health-check.sh        # Service status check
│   └── pre-build.sh           # Pre-build state save
│
├── .cursor/
│   ├── rules/                 # Domain-specific AI rules
│   │   ├── backend-api.mdc
│   │   ├── ui-development.mdc
│   │   ├── admin-screens.mdc
│   │   ├── monitoring-development.mdc
│   │   ├── datacloud-development.mdc
│   │   └── mcp-gateway.mdc
│   ├── state/                 # Service state tracking
│   │   └── services.json
│   └── learnings/             # AI learning records
│
├── docker-compose.yml         # Base orchestration
├── docker-compose.dev.yml     # Development overrides
├── docker-compose.prod.yml    # Production overrides
│
├── .cursorrules               # AI behavioral guidelines
├── AGENTS.md                  # This file (technical reference)
└── CLAUDE.md                  # Quick reference
```

### 4.2 Where to Add New Features

| Feature Type | Location |
|--------------|----------|
| New API endpoint | `backend/app/routes/<domain>.py` |
| New service logic | `backend/app/services/<name>_service.py` |
| New Build page | `webui/src/routes/(app)/build/<name>/+page.svelte` |
| New Operate page | `webui/src/routes/(app)/operate/<name>/+page.svelte` |
| New shared component | `webui/src/lib/components/<Name>.svelte` |
| New AI rule | `.cursor/rules/<domain>.mdc` |

---

## 5. Menu Structure

### 5.1 Navigation Structure

Agent Portal uses a three-tier navigation structure:

- **Use**: User-facing features (Chat, Agents, Data Cloud, etc.)
- **Build**: Development and configuration tools
- **Operate**: Operations and administration

### 5.2 Build Menu

| Menu Item | Path | Description |
|-----------|------|-------------|
| Agents | `/build/agents` | Agent development |
| Workflows | `/build/workflows` | Workflow builder |
| LLM | `/build/llm` | LLM model management |
| MCP | `/build/mcp` | MCP server management |
| Data Cloud | `/build/datacloud` | Database connections |
| Knowledge | `/build/knowledge` | Knowledge base |
| Guardrails | `/build/guardrails` | Safety configuration |
| Evaluations | `/build/evaluations` | Model evaluations |

### 5.3 Operate Menu

| Menu Item | Path | Description |
|-----------|------|-------------|
| Monitoring | `/operate/monitoring` | Monitoring dashboard |
| Gateway | `/operate/gateway` | API Gateway overview |
| 사용자관리 | `/operate/users` | User management |
| 설정 | `/operate/settings` | System settings |

### 5.4 Legacy Path Redirects

For backward compatibility, old `/admin/*` paths automatically redirect to new paths:

- `/admin/llm` → `/build/llm`
- `/admin/mcp` → `/build/mcp`
- `/admin/datacloud` → `/build/datacloud`
- `/admin/guardrails` → `/build/guardrails`
- `/admin/evaluations` → `/build/evaluations`
- `/admin/monitoring` → `/operate/monitoring`
- `/admin/gateway` → `/operate/gateway`
- `/admin/users` → `/operate/users`
- `/admin/settings` → `/operate/settings`

---

## 6. API Reference

### 5.1 Backend Routes

| Prefix | Router | Purpose |
|--------|--------|---------|
| `/chat` | chat.py | LLM chat completions |
| `/monitoring` | monitoring.py | Trace queries, metrics, agent stats |
| `/datacloud` | datacloud.py | Database connections, queries |
| `/text2sql` | text2sql.py | LangGraph Text-to-SQL Agent (SSE streaming) |
| `/mcp` | mcp.py | MCP server management |
| `/gateway` | gateway.py | Kong/service overview |
| `/projects` | projects.py | Project management |
| `/agents` | agent_registry.py | Agent registry and tracing |

### 5.2 Frontend Proxy Rules

```typescript
// webui/vite.config.ts
'/api/monitoring': → 'http://localhost:8000/monitoring'
'/api/datacloud':  → 'http://localhost:8000/datacloud'
'/api/text2sql':   → 'http://localhost:8000/text2sql'
'/api/mcp':        → 'http://localhost:8000/mcp'
'/api/gateway':    → 'http://localhost:8000/gateway'
'/api/projects':   → 'http://localhost:8000/projects'
```

### 5.3 Common Request Patterns

**GET with query params**:
```typescript
const response = await fetch('/api/monitoring/traces?project_id=xxx&limit=100');
```

**POST with JSON body**:
```typescript
const response = await fetch('/api/datacloud/connections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: 'conn1', host: 'localhost', ... })
});
```

---

## 7. Domain Knowledge

### 6.1 ClickHouse Specifics

**Database**: `otel_2` (NOT `otel`)

**Table**: `otel_traces`

**Critical**: `project_id` is in `ResourceAttributes` map, NOT a direct column:
```sql
-- ❌ WRONG
SELECT * FROM otel_traces WHERE project_id = 'xxx'

-- ✅ CORRECT
SELECT * FROM otel_traces WHERE ResourceAttributes['project_id'] = 'xxx'
```

**Duration**: Stored in nanoseconds, convert to milliseconds:
```sql
SELECT Duration / 1000000 as duration_ms FROM otel_traces
```

**Common Query**:
```sql
SELECT 
    TraceId as trace_id,
    SpanName as span_name,
    Duration / 1000000 as duration_ms,
    ResourceAttributes['project_id'] as project_id
FROM otel_2.otel_traces
WHERE ResourceAttributes['project_id'] = '{project_id}'
    AND Timestamp >= '{start_time}'
ORDER BY Timestamp DESC
LIMIT 100
```

### 6.2 Kong Gateway

**Admin API**: http://localhost:8001
**Proxy**: http://localhost:8002

**Service Registration Pattern**:
```python
# Create service
POST /services { name, url }

# Create route
POST /services/{service}/routes { paths: ['/path'] }

# Add plugins
POST /services/{service}/plugins { name: 'key-auth' }
```

### 6.3 Data Cloud

**Supported Databases**: MariaDB, PostgreSQL, ClickHouse

**Connection Storage**: MariaDB `agent_portal.db_connections` (encrypted)

**Schema Reflection**: SQLAlchemy `inspect()` for zero-copy metadata

**Text-to-SQL**: Uses LiteLLM with schema context as system prompt

---

## 8. Code Patterns

### 7.1 Backend Service (Singleton)

```python
# backend/app/services/example_service.py
from typing import Dict, Any
import httpx
from fastapi import HTTPException

class ExampleService:
    def __init__(self):
        self.base_url = "http://service:8080"
    
    async def get_data(self, id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/data/{id}")
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="External API timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))

# Singleton instance at module level
example_service = ExampleService()
```

### 7.2 Backend Router

```python
# backend/app/routes/example.py
from fastapi import APIRouter, HTTPException
from ..services.example_service import example_service

router = APIRouter(prefix="/example", tags=["example"])

@router.get("/{id}")
async def get_example(id: str):
    try:
        return await example_service.get_data(id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 7.3 Frontend Admin Page

```svelte
<!-- webui/src/routes/(app)/admin/example/+page.svelte -->
<script lang="ts">
    import { onMount } from 'svelte';
    
    let data = [];
    let loading = true;
    let error = '';
    
    onMount(async () => {
        try {
            const response = await fetch('/api/example');
            if (!response.ok) throw new Error('Failed to fetch');
            data = await response.json();
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    });
</script>

<div class="p-6">
    <!-- Hero section -->
    <div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm 
                rounded-2xl border border-white/20 dark:border-gray-700/20 
                shadow-sm p-6 mb-6">
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            Example Page
        </h1>
    </div>
    
    <!-- Content -->
    {#if loading}
        <p>Loading...</p>
    {:else if error}
        <p class="text-red-500">{error}</p>
    {:else}
        <!-- Render data -->
    {/if}
</div>
```

### 7.4 Glassmorphism Card

```svelte
<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl 
            border border-white/20 dark:border-gray-700/20 shadow-sm p-6">
    <!-- Card content -->
</div>
```

### 7.5 Modal

```svelte
{#if showModal}
<div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 
            flex items-center justify-center p-4">
    <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl 
                max-w-2xl w-full max-h-[90vh] overflow-hidden">
        <!-- Header -->
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 class="text-lg font-semibold">Title</h2>
        </div>
        
        <!-- Content -->
        <div class="p-6">...</div>
        
        <!-- Footer -->
        <div class="px-6 py-4 border-t flex justify-end gap-3">
            <button on:click={() => showModal = false}>Cancel</button>
            <button class="bg-primary text-white">Save</button>
        </div>
    </div>
</div>
{/if}
```

---

## 9. Troubleshooting

### 8.1 Service Not Starting

```bash
# Check status
docker compose ps

# Check logs
docker compose logs <service> --tail=100

# Force recreate
docker compose up -d --force-recreate <service>

# Full rebuild
docker compose build --no-cache <service>
docker compose up -d <service>
```

### 8.2 Port Conflict

```bash
# Find what's using the port
lsof -i :8000

# Kill process
kill -9 <PID>
```

### 8.3 Database Connection Failed

**MariaDB**:
```bash
docker compose ps mariadb
docker compose exec mariadb mariadb -uroot -prootpass -e "SELECT 1;"
docker compose logs mariadb --tail=50
```

**ClickHouse**:
```bash
curl http://localhost:8124/ping
docker compose logs monitoring-clickhouse --tail=50
```

### 8.4 API Returns 404

1. Check router registration in `backend/app/main.py`
2. Verify endpoint path matches request
3. Rebuild container if code changed:
   ```bash
   docker compose build --no-cache backend
   docker compose up -d backend
   ```

### 8.5 CORS Error in Frontend

```typescript
// ❌ WRONG: Direct call
fetch('http://localhost:8000/api/...')

// ✅ CORRECT: Use Vite proxy
fetch('/api/...')
```

Check proxy config in `webui/vite.config.ts`

### 8.6 ClickHouse Query Returns Empty

1. Check database name is `otel_2` not `otel`
2. Check `project_id` access: `ResourceAttributes['project_id']`
3. Check timestamp format and range

---

## 10. Quick Commands

### 9.1 Development

```bash
# Health check all services
./scripts/health-check.sh

# View logs
docker compose logs <service> --tail=50 -f

# Rebuild service
docker compose build --no-cache <service>
docker compose up -d <service>

# Shell into container
docker compose exec <service> /bin/sh
```

### 9.2 Database

```bash
# MariaDB shell
docker compose exec mariadb mariadb -uroot -prootpass agent_portal

# ClickHouse shell
docker compose exec monitoring-clickhouse clickhouse-client

# ClickHouse HTTP query
curl "http://localhost:8124/?query=SELECT+count()+FROM+otel_2.otel_traces"
```

### 9.3 WebUI Database Backup and Restore

**WebUI SQLite Database** (`webui/backend/data/webui.db`):
```bash
# 백업
./scripts/backup-webui-db.sh

# 백업 (커스텀 디렉토리)
./scripts/backup-webui-db.sh /path/to/backup/dir

# 복구
./scripts/restore-webui-db.sh ./backups/webui.db.YYYYMMDD_HHMMSS.backup

# 사용자 확인
docker compose exec webui python3 -c "import sqlite3; conn = sqlite3.connect('/app/backend/data/webui.db'); cursor = conn.cursor(); cursor.execute('SELECT email, name, role FROM user'); [print(f'{row[0]} - {row[1]} ({row[2]})') for row in cursor.fetchall()]; conn.close()"
```

**주의사항**:
- `git clean -fdx` 실행 시 `webui/backend/data/` 디렉토리가 삭제될 수 있음
- `.gitignore`에 `webui/backend/data/*`가 포함되어 있어야 함
- 정기적인 백업 권장

### 9.4 Environment File (.env) Protection

**`.env` 파일 보호** (민감 정보 포함 - API 키, 비밀번호 등):
```bash
# git clean 실행 전 백업
./scripts/protect-env.sh

# git clean 실행
git clean -fdx

# git clean 실행 후 복구
./scripts/restore-env.sh
```

**주의사항**:
- `git clean -fdx` 실행 시 `-x` 옵션으로 `.gitignore`에 포함된 파일도 삭제됨
- `.env` 파일은 `.gitignore`에 포함되어 있어 `git clean -fdx` 실행 시 삭제될 수 있음
- **반드시** `git clean -fdx` 실행 전에 `./scripts/protect-env.sh` 실행 필요
- 백업 파일은 `.env.backup.protected`로 저장되며, `.gitignore`에 포함되어 있음

### 9.5 Testing

```bash
# Test backend API (Single Port Architecture)
curl http://localhost:3010/health
curl http://localhost:3010/docs

# Test frontend
curl http://localhost:3010

# Test LiteLLM
curl http://localhost:4000/health
```

---

## 11. Testing and Validation

### 11.0 Browser Testing (MANDATORY for UI/Frontend Changes)

**⚠️ CRITICAL**: 화면 변경, UI 수정, 프론트엔드 기능 변경 후에는 **반드시 브라우저에서 직접 테스트**해야 합니다.

**When to Use Browser Testing**:
- ✅ SvelteKit 페이지/컴포넌트 수정
- ✅ 네비게이션 메뉴 변경
- ✅ UI 레이아웃/스타일 변경
- ✅ 사용자 인터랙션 기능 추가/수정
- ✅ API 통합 프론트엔드 변경
- ✅ 라우팅/URL 파라미터 변경

**Browser Testing Tools** (MCP Browser Extension):
- `browser_navigate`: 페이지 이동 (`http://localhost:3010/...`)
- `browser_snapshot`: 현재 화면 상태 확인
- `browser_click`: 버튼/링크 클릭
- `browser_type`: 텍스트 입력
- `browser_wait_for`: 로딩 대기
- `browser_console_messages`: 콘솔 오류 확인
- `browser_take_screenshot`: 시각적 확인

**Required Testing Steps**:
1. **페이지 로드 확인**:
   ```typescript
   browser_navigate({ url: "http://localhost:3010/use/perplexica" })
   browser_wait_for({ time: 5 })  // 로딩 대기
   browser_snapshot()  // 화면 상태 확인
   ```

2. **기능 동작 테스트**:
   ```typescript
   browser_click({ element: "검색 버튼", ref: "e128" })
   browser_type({ element: "입력창", ref: "e111", text: "테스트 쿼리" })
   browser_wait_for({ time: 10 })  // 응답 대기
   browser_snapshot()  // 결과 확인
   ```

3. **오류 확인**:
   ```typescript
   browser_console_messages()  // 콘솔 오류 확인
   ```

4. **시각적 확인**:
   ```typescript
   browser_take_screenshot({ filename: "test-result.png" })
   ```

**Testing Checklist**:
- [ ] 페이지가 정상적으로 로드됨
- [ ] 주요 UI 요소가 표시됨
- [ ] 사용자 인터랙션(클릭, 입력)이 정상 동작
- [ ] 콘솔에 오류가 없음
- [ ] 레이아웃이 의도한 대로 표시됨
- [ ] 다크/라이트 모드 모두 정상 동작 (해당 시)
- [ ] 반응형 디자인 정상 동작 (해당 시)

**Completion Criteria**:
- 브라우저에서 직접 테스트 완료 후에만 작업 완료 표시
- 테스트 결과를 사용자에게 보고 (성공/실패, 발견된 문제)

### 11.1 Test Scripts

**기동 및 기본 테스트**:
```bash
./scripts/start-and-test.sh
```
- Docker Compose 서비스 기동
- 서비스 헬스 체크 대기 (최대 120초)
- 기본 연결 테스트 자동 실행
- 실패 시 로그 출력 및 종료

**회귀 테스트**:
```bash
./scripts/regression-test.sh
```
- 모든 핵심 경로 테스트 실행
- 테스트 결과 리포트 생성 (JSON)
- 실패한 테스트 상세 로그
- 테스트 실행 시간 측정

**네트워크 경로 검증**:
```bash
./scripts/verify-network-paths.sh
```
- 각 네트워크 경로별 연결 확인
- 응답 시간 측정
- 에러율 통계
- 네트워크 토폴로지 검증

### 11.2 Test Scenarios

핵심 네트워크 경로별 테스트 케이스:

1. **기본 연결 테스트**: Browser → WebUI Frontend (3009)
   - `GET http://localhost:3010/` → 200 OK
   - HTML 응답, 정적 파일 로드 확인

2. **WebUI Backend 프록시**: Browser → BFF (3009) → WebUI Backend (8080)
   - `GET http://localhost:3010/api/webui/health`
   - `POST http://localhost:3010/api/webui/v1/chat`
   - 인증 토큰 전달 확인

3. **BFF 직접 API**: Browser → BFF (3009)
   - `GET http://localhost:3010/health`
   - `GET http://localhost:3010/monitoring/traces`
   - `GET http://localhost:3010/mcp/servers`

4. **Kong Gateway 통합**: Browser → BFF (3009) → Kong (8000) → MCP Server
   - MCP 서버 등록 → Kong에 서비스/라우트 생성 확인
   - `GET http://localhost:3010/api/mcp/servers/{id}/tools` → Kong 경유 MCP 호출
   - API Key 인증 확인
   - Rate Limiting 동작 확인

5. **DataCloud Kong 통합**: Browser → BFF (3009) → Kong (8000) → Database
   - DB 연결 생성 → Kong에 서비스/라우트 생성 확인
   - `POST http://localhost:3010/api/datacloud/connections/{id}/query` → Kong 경유 DB 쿼리
   - 연결 정보 암호화 확인

6. **WebSocket 연결**: Browser → BFF (3009) → WebUI Backend (8080)
   - WebSocket 연결 수립
   - 실시간 메시지 전송/수신
   - 연결 유지 및 재연결

자세한 테스트 절차는 [docs/TESTING.md](./docs/TESTING.md)를 참조하세요.

### 11.3 Network Path Verification

**단일 포트 구조 검증**:

- 모든 요청이 포트 3009를 통해 접근되는지 확인
- BFF가 WebUI Backend를 올바르게 프록시하는지 확인
- BFF가 Kong Gateway를 올바르게 경유하는지 확인
- 내부 네트워크 서비스 간 통신이 정상인지 확인

**검증 명령어**:
```bash
# External access (Port 3009)
curl http://localhost:3010/health

# Internal network verification
docker compose exec backend curl http://webui:8080/health
docker compose exec backend curl http://kong:8000/status
```

---

## 12. Architecture Integrity Rules (CRITICAL)

### 10.1 No Bypass Policy

**아키텍처 우회 금지**: 문제 발생 시 우회하지 말고 근본 원인을 해결해야 합니다.

### 10.2 Prohibited Bypass Patterns

| Category | ❌ Prohibited | ✅ Required |
|----------|--------------|-------------|
| **Environment** | Docker 대신 npm/python 직접 실행 | Docker Compose로만 기동 |
| **Port Conflict** | docker-compose.yml 포트 변경 | 충돌 프로세스 종료 |
| **Network** | localhost로 우회 | Docker 내부 네트워크명 사용 |
| **Configuration** | YAML로 우회 (DB 관리 안될 때) | 근본 원인 분석 |
| **Failure** | 이전 방식으로 롤백 | 실패 원인 분석 및 보고 |

### 10.3 Service Network Names

Docker 내부에서 서비스 간 통신 시 반드시 아래 네트워크명 사용:

```yaml
# ✅ Correct (Docker internal)
LITELLM_HOST: http://litellm:4000
CLICKHOUSE_HOST: monitoring-clickhouse:8123
DATABASE_URL: mariadb:3306

# ❌ Wrong (localhost bypass)
LITELLM_HOST: http://localhost:4000
CLICKHOUSE_HOST: localhost:8124
```

### 10.4 When Issues Occur

```
1. 우회하지 않고 원인 분석
2. 분석 결과를 사용자에게 명확히 보고
3. 해결 방안 2-3가지 제시 (우회책 제외)
4. 사용자 승인 후 진행
5. 해결 불가 시 아키텍처 재검토 요청
```

### 10.5 Current Architecture Decisions

| Component | Decision | Status |
|-----------|----------|--------|
| LLM Gateway | LiteLLM + PostgreSQL (DB 기반 모델 관리) | 🔧 암호화 문제 조사 중 |
| Observability | OTEL → ClickHouse | ✅ 정상 |
| App Database | MariaDB | ✅ 정상 |
| API Gateway | Kong + Konga | ✅ 정상 |

---

## 13. Single Port Architecture Implementation Status

### 11.1 Implementation Summary

**Status**: ✅ **완료** (2025-12-09)

모든 서비스가 단일 포트(3009)를 통해 접근 가능하도록 구현 완료:

| 경로 | 상태 | 설명 |
|------|------|------|
| WebUI Frontend | ✅ | `http://localhost:3010/` → Vite Dev Server (3001, internal) |
| WebUI Backend | ✅ | `http://localhost:3010/api/v1/*` → WebUI Backend (8080, internal) |
| BFF 직접 API | ✅ | `http://localhost:3010/health`, `/monitoring/*`, `/chat/*` 등 |
| MCP Gateway | ✅ | `http://localhost:3010/api/mcp/*` → BFF → Kong → MCP Servers |
| DataCloud | ✅ | `http://localhost:3010/api/datacloud/*` → BFF → Kong → Databases |
| Kong Gateway | ✅ | 내부 네트워크(`kong:8000`)로만 접근, BFF를 통해서만 외부 노출 |

### 11.2 Router Configuration

**BFF 라우터 등록 순서** (`backend/app/main.py`):

```python
# 1. BFF 직접 처리 라우터들 (우선순위 높음)
app.include_router(mcp.router)  # /mcp/*
app.include_router(mcp.api_router)  # /api/mcp/* (Vite 프록시용)
app.include_router(datacloud.router)  # /datacloud/*
app.include_router(datacloud.api_router)  # /api/datacloud/* (Vite 프록시용)

# 2. WebUI Backend 프록시 (catch-all, 마지막)
app.include_router(webui_proxy.api_router)  # /api/* 직접 프록시
app.include_router(webui_proxy.router)  # /api/webui/* 프록시
```

**중요**: `/api/mcp/*`와 `/api/datacloud/*`는 BFF에서 직접 처리하므로, `webui_proxy.api_router`보다 먼저 등록되어야 합니다.

### 11.3 Test Results (2025-12-09)

**포트 3009를 통한 모든 경로 검증**:

```
✅ WebUI Frontend (Root): HTTP 200
✅ WebUI Backend API (/api/v1/auths/signin): HTTP 400 (정상 - 인증 실패이지만 경로 작동)
✅ BFF 직접 API (/health): HTTP 200
✅ MCP API (/api/mcp/servers): HTTP 200
✅ DataCloud API (/api/datacloud/connections): HTTP 200
⚠️ Monitoring API (/monitoring/traces): HTTP 404 (프로젝트 ID 필요, 경로는 정상)
```

**브라우저 테스트**:
- ✅ 로그인 (`lchangoo@gmail.com`): 성공
- ✅ MCP 서버 목록: 정상 로드 (2개 서버 표시)
- ✅ DataCloud 연결 목록: 정상 로드 (4개 연결 표시)

### 11.4 Known Issues

1. **Vite HMR WebSocket**: 현재 비활성화됨 (연속 리프레시 문제 해결을 위해)
   - 해결책: `webui/vite.config.ts`에서 `hmr: false` 설정
   - 향후 개선: WebSocket 프록시 안정화 후 재활성화

2. **Monitoring API 404**: 프로젝트 ID가 없을 때 404 반환 (정상 동작)

---

## 14. Future Development Epics

아래는 Agent Portal의 향후 개발 로드맵입니다. 각 에픽은 실제 구현 가능한 수준으로 기술 스택, 구현 위치, 핵심 사항을 정의합니다.

### 14.1 Agent-to-UI 테스트 자동화 (ai2ui)

**목표**: 에이전트가 실제 UI를 조작하고, 기대 결과를 검증하며, 전 과정을 텔레메트리로 기록하여 재현 가능한 테스트와 운영 관측을 연결합니다.

**기술 스택**:
- Playwright (브라우저 자동화)
- OpenTelemetry Python SDK (트레이싱)
- MinIO (아티팩트 저장)

**구현 위치**:
```
backend/app/agents/ai2ui/
├── driver.py              # Playwright 기반 UI Driver
├── actions.py             # UI Action DSL (Click, Type, Wait, Assert, Snapshot)
├── assertions.py          # 검증 로직
├── otel_integration.py    # OTEL span 수집
└── artifact_storage.py    # 스크린샷/비디오/DOM 스냅샷 저장

backend/app/routes/ai2ui.py  # API 엔드포인트
webui/src/routes/(app)/operate/ai2ui/  # 테스트 리포트 화면
```

**핵심 구현 사항**:
- [ ] UI Driver DSL 정의 (Click, Type, Wait, Assert, Snapshot)
- [ ] 스텝 단위 span 수집 (action_id, selector, screenshot_ref, latency, error_type)
- [ ] 세션 단위 trace 수집 (OpenTelemetry)
- [ ] 증거 아티팩트 저장 (스크린샷, DOM 스냅샷, 네트워크 로그, 비디오)
- [ ] 실패 시 자동 재시도 및 대체 경로 탐색
- [ ] UI 테스트 런 리포트 화면 (성공/실패, 재시도, 아티팩트 링크)

**완료 기준**:
- 대표 시나리오 3개(로그인/검색/CRUD)에서 재현 가능한 실패 리포트 생성
- 운영 장애 케이스 1개를 테스트로 재현하고 원인 span으로 추적

**참조 문서**: [docs/references/A2UI_PROTOCOL.md](./docs/references/A2UI_PROTOCOL.md), [docs/guides/AI2UI_TESTING_GUIDE.md](./docs/guides/AI2UI_TESTING_GUIDE.md)

---

### 14.2 모델 자동 라우팅 에이전트

**목표**: 작업별로 현재 시점 최적의 모델을 자동 선택하고, 선택 근거(가격/컨텍스트/툴 지원/지연/성공률)를 기록합니다.

**기술 스택**:
- OpenRouter Models API (모델 메타데이터)
- httpx (비동기 HTTP 클라이언트)
- Redis (캐싱)

**구현 위치**:
```
backend/app/services/model_routing_service.py  # 라우팅 로직
backend/app/routes/model_routing.py            # API 엔드포인트
config/model_routing_policy.yaml               # 라우팅 정책

webui/src/routes/(app)/operate/model-routing/  # 라우팅 대시보드
```

**핵심 구현 사항**:
- [ ] OpenRouter Models API로 모델 메타데이터 수집/캐시 (컨텍스트 길이, 가격, 지원 파라미터)
- [ ] 리더보드/랭킹 신호 + 내부 운영 신호(에러율/지연/비용) 합성 스코어링
- [ ] 라우팅 정책: task_type → required_capabilities → candidate_models → score → pick
- [ ] 폴백 정책: 선택 모델 실패 시 provider/model fallback
- [ ] 라우팅 로그: "왜 이 모델을 골랐는지" 설명 가능한 근거 필드
- [ ] 라우팅 대시보드: 비용/지연/성공률 추세 시각화

**완료 기준**:
- 3개 작업 유형에서 수동 선택 대비 비용/성공률/지연 중 1개 이상 유의미 개선
- 모델 선택 결과 재현 가능 (동일 정책/신호면 동일 선택)

**참조 문서**: [docs/references/MODEL_LEADERBOARDS.md](./docs/references/MODEL_LEADERBOARDS.md), [docs/guides/MODEL_ROUTING_GUIDE.md](./docs/guides/MODEL_ROUTING_GUIDE.md)

---

### 14.3 고급 Tool-Use LangGraph 패턴

**목표**: Plan → Tool Select → Execute → Validate → Retry/Repair → Human 승인까지 운영 가능한 루프를 LangGraph로 표준화합니다.

**기술 스택**:
- LangGraph (상태 기반 워크플로우)
- LangChain (LLM 통합)
- OpenTelemetry (트레이싱)

**구현 위치**:
```
backend/app/agents/graph_templates/advanced_tool_use/
├── __init__.py
├── state.py           # 상태 정의
├── nodes/
│   ├── plan.py        # 계획 노드
│   ├── tool_select.py # 도구 선택 노드
│   ├── execute.py     # 실행 노드
│   ├── validate.py    # 검증 노드
│   └── repair.py      # 복구 노드
├── graph.py           # StateGraph 설정
├── error_taxonomy.py  # 에러 분류
└── circuit_breaker.py # 회로 차단기
```

**핵심 구현 사항**:
- [ ] 핵심 루프 그래프 노드 분해 (계획/도구선택/실행/검증/복구)
- [ ] LangGraph interrupt 패턴 (승인/추가 입력 대기)
- [ ] Tool error taxonomy: 입력 스키마 오류 / 권한 오류 / 외부 장애 / 결과 불충분
- [ ] Retry policy 및 회로 차단기 (반복 실패 시 중단, 다른 경로로 전환)
- [ ] 검증 노드 표준 (도구 결과의 완결성/일관성/근거 여부 확인)
- [ ] Human-in-the-loop 승인 UI (티켓/코멘트 기반)

**완료 기준**:
- 대표 MCP 도구 2종 이상에서 "실패→자기복구→성공" 데모
- 승인 필요 케이스에서 interrupt로 안전 중단 후 재개 성공

**참조 문서**: [docs/references/SCALING_AGENT_SYSTEMS.md](./docs/references/SCALING_AGENT_SYSTEMS.md)

---

### 14.4 Data Cloud 시멘틱 레이어

**목표**: RAG/툴/대시보드가 같은 정의의 엔터티·지표·용어를 공유하도록 시멘틱/메트릭 표준을 구축합니다.

**기술 스택**:
- dbt/cube 개념 참고 (시멘틱 레이어)
- SQLAlchemy (메타데이터 관리)
- YAML (정의 파일)

**구현 위치**:
```
backend/app/datacloud/semantic/
├── entities/              # 비즈니스 엔터티 정의 (customer.yaml, product.yaml 등)
├── metrics/               # KPI/메트릭 정의 (revenue.yaml, churn_rate.yaml 등)
├── glossary/              # 용어 사전
└── lineage/               # 라인리지 정보

backend/app/services/semantic_layer_service.py  # 시멘틱 레이어 서비스
```

**핵심 구현 사항**:
- [ ] 비즈니스 엔터티(고객/상품/공시 등) + KPI/메트릭(정의/식/기간/집계) 카탈로그화
- [ ] 모델/지표 정의를 코드(YAML)로 관리
- [ ] RAG 메타데이터에 시멘틱 키 연결 (문서/테이블/툴 결과가 다루는 엔터티/지표)
- [ ] 정책/거버넌스 결합 (권한·라인리지: 누가 어떤 지표를 볼 수 있는가)
- [ ] "동일 질문→RAG/툴/대시보드 결과의 의미 일치" 검증 시나리오

**완료 기준**:
- 대표 지표 5개에 대해 정의/식/출처/라인리지/권한이 한 곳에서 조회 가능
- 에이전트가 "지표 정의"를 근거로 응답에 포함

---

### 14.5 AI Native Stack 매핑 체계

**목표**: AI Native Stack(10개 레이어/Capability 카탈로그)을 체크리스트로 삼아, agent-portal 코드/컴포넌트 매핑과 GAP을 자동으로 드러내는 체계를 만듭니다.

**기술 스택**:
- Python (매핑 스크립트)
- YAML/JSON (매핑 테이블)
- Markdown (문서 생성)

**구현 위치**:
```
docs/AI_NATIVE_STACK_MAPPING.md       # 매핑 문서
docs/references/AI_NATIVE_STACK.md    # 원본 스택 테이블

scripts/generate-stack-mapping.py     # 자동 생성 스크립트
config/stack_mapping.yaml             # 매핑 정의
```

**핵심 구현 사항**:
- [ ] AI Native Stack Layer → (repo path / service / route / config / owner) 매핑 테이블 생성
- [ ] 각 레이어별 "필수 Capability 최소셋" 정의 후 커버리지 산정(있음/부분/없음)
- [ ] Gap이 곧 "다음 스프린트 백로그"로 내려오게 자동화
- [ ] README.md에 Service Map / Port Map / Feature Map / API Reference 섹션 추가
- [ ] PR 템플릿에 "AI Native Stack 영향 레이어 체크" 포함

**완료 기준**:
- AI Native Stack 기준으로 "없음(미구현) Capability"가 자동 목록화
- PR 템플릿에 레이어 체크 포함

**참조 문서**: [docs/references/AI_NATIVE_STACK.md](./docs/references/AI_NATIVE_STACK.md), [docs/guides/AI_NATIVE_STACK_MAPPING_GUIDE.md](./docs/guides/AI_NATIVE_STACK_MAPPING_GUIDE.md)

---

### 14.6 MCP 자동 유지보수 체계

**목표**: MCP 서버들을 "분석→수정→테스트→릴리즈"까지 자동으로 운영하기 위해 AGENTS.md + skill 문서를 표준으로 정착시킵니다.

**기술 스택**:
- MCP SDK (스펙 검증)
- pytest (자동 테스트)
- GitHub Actions (CI 파이프라인)

**구현 위치**:
```
scripts/mcp-self-check/
├── schema_validator.py    # 스키마 검증
├── doc_quality.py         # 문서 품질 체크
├── sample_caller.py       # 샘플 호출 테스트
└── regression_suite.py    # 회귀 테스트

backend/app/services/mcp_validator.py  # MCP 검증 서비스
.github/workflows/mcp-check.yml        # CI 워크플로우
```

**핵심 구현 사항**:
- [ ] MCP 스펙/툴 스키마 표준 준수 체크 (도구명/설명/입출력/에러 계약)
- [ ] repo 루트에 AGENTS.md(에이전트용 작업 규칙) 배치 + 스킬 문서(작업 단위 표준)
- [ ] 자동 점검 파이프라인: 도구 등록 누락/설명 품질/샘플 호출/회귀 테스트를 CI로 고정
- [ ] MCP 서버별 "self-check" 스위트 (간단 호출/스키마 검증)

**완료 기준**:
- MCP 3개 이상에서 "에이전트가 스스로 문서/스키마/테스트를 갱신"하는 PR 생성

---

### 14.7 고위험 도메인 에이전트 라인업

**목표**: 법률/의료/건강/투자/부동산/공시 등 고위험 도메인별로 "규칙 기반 안전장치 + 증거 기반 응답 + 승인 흐름"을 기본 탑재합니다.

**기술 스택**:
- LangGraph (워크플로우)
- OPA (정책 엔진)
- OpenTelemetry (감사 로깅)

**구현 위치**:
```
backend/app/agents/domain_specific/
├── legal/                 # 법률 도메인
├── medical/               # 의료 도메인
├── finance/               # 투자/금융 도메인
├── real_estate/           # 부동산 도메인
└── disclosure/            # 공시 도메인 (기존 DART Agent 확장)

backend/app/policies/
├── legal_policy.rego      # OPA 정책 파일
├── medical_policy.rego
└── finance_policy.rego
```

**핵심 구현 사항**:
- [ ] 도메인별 안전 정책: 금지/주의/승인 필요 범위 명확화
- [ ] 근거 우선: 출처/근거/계산 과정/불확실성을 구조화해 기록
- [ ] 리스크 프레임워크 정렬: NIST AI RMF/OWASP LLM Top 10 체크리스트화
- [ ] 도메인별 에이전트 템플릿 (프롬프트/가드/출력 포맷/로그 스키마)
- [ ] 감사 가능한 "근거 번들" (RAG 출처 + tool 결과 + 판단 로그)

**완료 기준**:
- 1개 도메인에서 "승인 필요 케이스"가 실제로 멈추고, 승인 후에만 실행

---

### 14.8 비용 인지형 에이전트 프레임워크

**목표**: 에이전트가 "언제 도구를 쓸지 / 언제 요약·근사로 갈지"를 예산 정책으로 내재화합니다.

**기술 스택**:
- OpenRouter pricing API (비용 정보)
- Redis (예산 상태 추적)
- OpenTelemetry (비용 이벤트 로깅)

**구현 위치**:
```
backend/app/services/budget_manager.py         # 예산 관리 서비스
backend/app/middleware/budget_middleware.py    # 예산 미들웨어
config/budget_policy.yaml                      # 예산 정책 정의

webui/src/routes/(app)/operate/budget/         # 비용 대시보드
```

**핵심 구현 사항**:
- [ ] 모델/툴 비용 추정: OpenRouter 모델 메타의 pricing/context를 근거로 사전 계산
- [ ] Budget Policy: (Hard cap / Soft cap / Grace) + 초과 시 행동(요약/샘플링/질문 되돌림)
- [ ] 예산-관측 연동: "예산 초과로 전략 변경" 이벤트를 OTEL로 기록
- [ ] 비용 대시보드: 작업유형별 평균 비용, 절감 효과 시각화

**완료 기준**:
- 동일 태스크에서 "예산 모드 ON" 시 비용 안정화 + 품질 저하 허용 범위 내

**참조 문서**: [docs/references/SCALING_AGENT_SYSTEMS.md](./docs/references/SCALING_AGENT_SYSTEMS.md), [docs/guides/BUDGET_AWARE_AGENTS.md](./docs/guides/BUDGET_AWARE_AGENTS.md)

---

### 14.9 Agent Builder 강화

**목표**: n8n/crewai 같은 제품의 좋은 UX/패턴은 흡수하되, 상용 배포 가능한 형태로 자체 구현합니다.

**기술 스택**:
- SvelteKit (UI)
- LangGraph (실행 엔진)
- Svelte Flow (노드 기반 편집기)

**구현 위치**:
```
webui/src/routes/(app)/build/agents/builder/
├── +page.svelte           # 메인 빌더 페이지
├── components/
│   ├── NodeEditor.svelte  # 노드 편집기
│   ├── NodePalette.svelte # 노드 팔레트
│   ├── ExecutionLog.svelte # 실행 로그
│   └── VariableBinding.svelte # 변수 바인딩
└── stores/
    └── graphStore.ts      # 그래프 상태 관리

backend/app/routes/agent_builder.py    # API 엔드포인트
backend/app/services/agent_builder_service.py  # 빌더 서비스
```

**핵심 구현 사항**:
- [ ] Builder UX: 노드 기반 플로우 편집 (Drag&Drop)
- [ ] 실행 로그 표시
- [ ] 변수 바인딩 UI
- [ ] 승인 노드 (Human-in-the-loop)
- [ ] 템플릿 마켓 구조 (내부 배포용)
- [ ] 라이선스 리스크 회피: 코드 재사용 대신 패턴/UX 참고→재구현 원칙

**완료 기준**:
- 간단 플로우 2개 + 멀티에이전트 플로우 1개를 Builder로 구성→실행까지 성공

**참조 문서**: [docs/references/A2UI_PROTOCOL.md](./docs/references/A2UI_PROTOCOL.md)

---

### 14.10 메모리 관리 강화

**목표**: 세션 메모리/장기 메모리를 분리하고, 저장·조회·만료·권한을 정책화하며, 평가/관측과 연결합니다.

**기술 스택**:
- LangGraph Memory (세션 메모리)
- Redis/PostgreSQL (장기 메모리)
- YAML (정책 정의)

**구현 위치**:
```
backend/app/services/memory_manager.py    # 메모리 관리 서비스
backend/app/agents/memory_policy.yaml     # 메모리 정책 정의

config/memory_schema.yaml                 # 메모리 스키마 정의
```

**핵심 구현 사항**:
- [ ] 세션 메모리: thread_id 단위 상태 지속 (LangGraph 체크포인터)
- [ ] 장기 메모리: 액션 아이템/사용자 선호/도메인 사실 같은 제한된 스키마로만 저장
- [ ] 만료/삭제/권한: TTL, scope(팀/프로젝트/개인), 민감도 등급
- [ ] HIL 연계: 기억 저장/수정은 기본적으로 사용자 승인 옵션 제공
- [ ] 메모리 이벤트 관측: 저장/조회/히트율/오답 유발 케이스

**완료 기준**:
- "기억 때문에 틀린 답"을 역추적할 수 있고, 삭제/교정이 즉시 반영

---

### 14.11 보안 강화

**목표**: 정책을 "권고"가 아니라 강제로 집행(enforcement)하고, 도구/데이터 경계에서 접근제어·감사를 기본값으로 둡니다.

**기술 스택**:
- OPA (Open Policy Agent) - 정책 엔진
- OpenTelemetry (감사 추적)
- Vault (비밀 관리)

**구현 위치**:
```
backend/app/middleware/policy_gateway.py  # 정책 게이트웨이
backend/app/policies/
├── tool_access.rego       # 도구 접근 정책
├── data_access.rego       # 데이터 접근 정책
└── action_control.rego    # 행위 통제 정책

docs/SECURITY.md                          # 보안 정책 문서
```

**핵심 구현 사항**:
- [ ] Policy-as-code: OPA로 ABAC/행위 통제 (툴 호출 허용/차단/승인 필요)
- [ ] OWASP LLM Top 10 기반 위협모델 체크 (프롬프트 인젝션, 데이터 유출, 과권한 등)
- [ ] 감사 추적: 모든 tool call에 (who/why/what/inputs/outputs) 서명 가능한 로그 + OTEL 연동
- [ ] 공급망/비밀관리: 모델/도구/컨테이너/시크릿 경로 고정 및 점검
- [ ] 도구 호출 게이트(Policy Gateway) 모듈

**완료 기준**:
- 금지 정책 위반 요청이 "항상" 차단되고, 차단 근거가 로그로 남음
- 승인 흐름이 필요한 액션은 무조건 interrupt로 멈춤

---

**Last Updated**: 2025-12-23
**Version**: 5.3 (Future Development Epics)
