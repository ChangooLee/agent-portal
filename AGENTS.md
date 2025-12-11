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

### 1.2 Tech Stack

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
│                      http://localhost:3009                       │
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
| backend | 3009 | 3009 | agent-portal-backend-1 | http://localhost:3009/health | FastAPI BFF (Main Entry Point) |
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

### 9.3 Testing

```bash
# Test backend API (Single Port Architecture)
curl http://localhost:3009/health
curl http://localhost:3009/docs

# Test frontend
curl http://localhost:3009

# Test LiteLLM
curl http://localhost:4000/health
```

---

## 11. Testing and Validation

### 10.1 Test Scripts

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

### 10.2 Test Scenarios

핵심 네트워크 경로별 테스트 케이스:

1. **기본 연결 테스트**: Browser → WebUI Frontend (3009)
   - `GET http://localhost:3009/` → 200 OK
   - HTML 응답, 정적 파일 로드 확인

2. **WebUI Backend 프록시**: Browser → BFF (3009) → WebUI Backend (8080)
   - `GET http://localhost:3009/api/webui/health`
   - `POST http://localhost:3009/api/webui/v1/chat`
   - 인증 토큰 전달 확인

3. **BFF 직접 API**: Browser → BFF (3009)
   - `GET http://localhost:3009/health`
   - `GET http://localhost:3009/monitoring/traces`
   - `GET http://localhost:3009/mcp/servers`

4. **Kong Gateway 통합**: Browser → BFF (3009) → Kong (8000) → MCP Server
   - MCP 서버 등록 → Kong에 서비스/라우트 생성 확인
   - `GET http://localhost:3009/api/mcp/servers/{id}/tools` → Kong 경유 MCP 호출
   - API Key 인증 확인
   - Rate Limiting 동작 확인

5. **DataCloud Kong 통합**: Browser → BFF (3009) → Kong (8000) → Database
   - DB 연결 생성 → Kong에 서비스/라우트 생성 확인
   - `POST http://localhost:3009/api/datacloud/connections/{id}/query` → Kong 경유 DB 쿼리
   - 연결 정보 암호화 확인

6. **WebSocket 연결**: Browser → BFF (3009) → WebUI Backend (8080)
   - WebSocket 연결 수립
   - 실시간 메시지 전송/수신
   - 연결 유지 및 재연결

자세한 테스트 절차는 [docs/TESTING.md](./docs/TESTING.md)를 참조하세요.

### 10.3 Network Path Verification

**단일 포트 구조 검증**:

- 모든 요청이 포트 3009를 통해 접근되는지 확인
- BFF가 WebUI Backend를 올바르게 프록시하는지 확인
- BFF가 Kong Gateway를 올바르게 경유하는지 확인
- 내부 네트워크 서비스 간 통신이 정상인지 확인

**검증 명령어**:
```bash
# External access (Port 3009)
curl http://localhost:3009/health

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
| WebUI Frontend | ✅ | `http://localhost:3009/` → Vite Dev Server (3001, internal) |
| WebUI Backend | ✅ | `http://localhost:3009/api/v1/*` → WebUI Backend (8080, internal) |
| BFF 직접 API | ✅ | `http://localhost:3009/health`, `/monitoring/*`, `/chat/*` 등 |
| MCP Gateway | ✅ | `http://localhost:3009/api/mcp/*` → BFF → Kong → MCP Servers |
| DataCloud | ✅ | `http://localhost:3009/api/datacloud/*` → BFF → Kong → Databases |
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

**Last Updated**: 2025-12-09
**Version**: 5.2 (Single Port Architecture + Testing)
