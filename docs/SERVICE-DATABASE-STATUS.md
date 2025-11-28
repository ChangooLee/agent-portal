# Agent Portal 서비스 및 데이터베이스 상태 문서

> **Last Updated**: 2025-11-28
> **Purpose**: 로컬 개발 환경의 서비스 및 DB 상태 기록

---

## 1. 서비스 현황

### 1.1 실행 중인 서비스 (15개)

| 서비스 | 컨테이너명 | 포트 | 상태 | 용도 |
|--------|-----------|------|------|------|
| webui | agent-portal-webui-1 | 3005:3001, 3000:8080 | Running | Portal UI (SvelteKit) |
| backend | agent-portal-backend-1 | 8000:8000 | Running | FastAPI BFF |
| mariadb | agent-portal-mariadb-1 | 3306:3306 | Running | App Database |
| redis | agent-portal-redis-1 | 6379:6379 | Running | Cache |
| chromadb | agent-portal-chromadb-1 | 8005:8000 | Running | Vector DB |
| minio | agent-portal-minio-1 | 9003:9000, 9004:9001 | Running | Object Storage |
| kong | agent-portal-kong-1 | 8004:8000, 8444:8443 | Running (healthy) | API Gateway |
| kong-db | agent-portal-kong-db-1 | - | Running (healthy) | Kong PostgreSQL |
| konga | agent-portal-konga-1 | 1337:1337 | Running | Kong Admin UI |
| konga-db | agent-portal-konga-db-1 | - | Running (healthy) | Konga PostgreSQL |
| litellm | agent-portal-litellm-1 | 4000:4000 | Running | LLM Gateway (external) |
| prometheus | agent-portal-prometheus-1 | 9092:9090 | Running | Metrics |
| clickhouse | monitoring-clickhouse | 8124:8123, 9002:9000 | Running | OTEL Traces (external) |
| otel-collector | monitoring-otel-collector | 4319:4317, 4320:4318 | Running | Trace Collection (external) |
| litellm-postgres | litellm-postgres | 5433:5432 | Running (healthy) | LiteLLM PostgreSQL (external) |

### 1.2 외부 서비스 (별도 docker-compose로 실행)

| 서비스 | 포트 | 호스트 접근 방식 |
|--------|------|-----------------|
| LiteLLM | 4000 | `host.docker.internal:4000` |
| OTEL Collector | 4317/4318 | `host.docker.internal:4317` (gRPC) |
| ClickHouse | 8124 | `host.docker.internal:8124` |

---

## 2. 데이터베이스 상세

### 2.1 MariaDB (agent_portal)

**연결 정보**:
```
Host: mariadb (Docker) / localhost:3306 (Local)
User: root
Password: rootpass (env: MARIADB_ROOT_PASSWORD)
Database: agent_portal
```

**테이블 목록 (43개)**:

| 테이블 | 용도 | 스키마 초기화 |
|--------|------|--------------|
| `projects` | 프로젝트 관리 | `scripts/init-project-schema.sql` |
| `teams` | 팀 관리 | `scripts/init-project-schema.sql` |
| `team_members` | 팀-사용자 매핑 | `scripts/init-project-schema.sql` |
| `team_projects` | 팀-프로젝트 매핑 | `scripts/init-project-schema.sql` |
| `mcp_servers` | MCP 서버 등록 | `scripts/init-mcp-schema.sql` |
| `mcp_server_tools` | MCP 서버 도구 | `scripts/init-mcp-schema.sql` |
| `mcp_server_projects` | MCP-프로젝트 매핑 | `scripts/init-mcp-schema.sql` |
| `mcp_server_permissions` | MCP 권한 | `scripts/init-mcp-schema.sql` |
| `mcp_call_logs` | MCP 호출 로그 | `scripts/init-mcp-schema.sql` |
| `db_connections` | Data Cloud 연결 | `scripts/init-datacloud-schema.sql` |
| `db_schema_cache` | 스키마 캐시 | `scripts/init-datacloud-schema.sql` |
| `db_table_cache` | 테이블 캐시 | `scripts/init-datacloud-schema.sql` |
| `db_business_terms` | 비즈니스 용어 | `scripts/init-datacloud-schema.sql` |
| `db_connection_permissions` | DB 연결 권한 | `scripts/init-datacloud-schema.sql` |
| `db_query_logs` | 쿼리 로그 | `scripts/init-datacloud-schema.sql` |
| `llm_calls` | LLM 호출 로그 | Backend 자동 생성 |
| `otel_traces` | OTEL 트레이스 (미사용) | - |
| `trace_summaries` | 트레이스 요약 (미사용) | - |
| `user`, `auth`, `chat`, `file`, ... | WebUI 테이블 (SQLite 마이그레이션) | - |

**스키마 초기화 방법**:
```bash
# 전체 스키마 초기화
docker exec -i agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal < scripts/init-project-schema.sql
docker exec -i agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal < scripts/init-mcp-schema.sql
docker exec -i agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal < scripts/init-datacloud-schema.sql
```

### 2.2 WebUI SQLite

**연결 정보**:
```
Path: /app/backend/data/webui.db (컨테이너 내)
Volume: webui_data (로컬: ./webui/backend/data/)
```

**테이블 목록**:
- `user`, `auth`, `chat`, `chatidtag`, `config`
- `document`, `file`, `function`, `group`
- `memory`, `model`, `prompt`, `tag`, `tool`
- `alembic_version`, `migratehistory`

**스키마 생성**: Open-WebUI 자동 생성 (Peewee ORM + Alembic 마이그레이션)

### 2.3 ClickHouse (otel_2)

**연결 정보**:
```
Host: monitoring-clickhouse (Docker) / host.docker.internal:8124 (dev)
User: default
Password: password
Database: otel_2
```

**테이블 목록**:
- `otel_traces` - OTEL 트레이스 저장 (메인)
- `otel_logs` - OTEL 로그
- `otel_metrics_*` - OTEL 메트릭

**주요 컬럼** (`otel_traces`):
```sql
TraceId, SpanId, SpanName, ServiceName, Duration, Timestamp, StatusCode
ResourceAttributes['project_id']  -- project_id 접근 방식
SpanAttributes['llm.usage.total_tokens']
```

**스키마 생성**: OTEL Collector 자동 생성

### 2.4 LiteLLM PostgreSQL (litellm_db)

**연결 정보**:
```
Host: litellm-postgres (Docker) / localhost:5433 (Local)
User: litellm
Password: litellm_secure_password
Database: litellm_db
```

**테이블 목록 (36개)**: Prisma 자동 생성
- `LiteLLM_UserTable`, `LiteLLM_TeamTable`, `LiteLLM_SpendLogs`
- `LiteLLM_ModelTable`, `LiteLLM_VerificationToken`, etc.

### 2.5 Kong PostgreSQL

**연결 정보**:
```
Host: kong-db (Docker)
User: kong
Password: kongpass
Database: kong
```

**스키마 생성**: `kong-migrations` 서비스가 자동 실행 (`kong migrations bootstrap`)

### 2.7 Konga PostgreSQL

**연결 정보**:
```
Host: konga-db (Docker)
User: konga
Password: kongapass
Database: konga
```

**스키마 생성**: Konga 자동 생성 (Sails.js)

---

## 3. 데이터 볼륨

| 볼륨 | 컨테이너 경로 | 용도 |
|------|--------------|------|
| `agent-portal_mariadb` | `/var/lib/mysql` | MariaDB 데이터 |
| `agent-portal_webui_data` | `/app/backend/data` | WebUI SQLite |
| `agent-portal_redis` | `/data` | Redis 데이터 |
| `agent-portal_minio` | `/data` | MinIO 오브젝트 |
| `agent-portal_kong_db` | `/var/lib/postgresql/data` | Kong DB |
| `agent-portal_konga_db` | `/var/lib/postgresql/data` | Konga DB |
| `agent-portal_monitoring_clickhouse` | `/var/lib/clickhouse` | ClickHouse 데이터 |
| `agent-portal_litellm_pg_data` | `/var/lib/postgresql/data` | LiteLLM DB |
| `agent-portal_prometheus_data` | `/prometheus` | Prometheus 메트릭 |

---

## 4. 기동 순서 및 의존성

### 4.1 서비스 의존성 그래프

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Infrastructure (No Dependencies)                    │
├─────────────────────────────────────────────────────────────┤
│  mariadb, redis, kong-db, konga-db                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ wait: service_healthy
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Core Services                                       │
├─────────────────────────────────────────────────────────────┤
│  kong-migrations → kong, konga                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ depends_on
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Application                                         │
├─────────────────────────────────────────────────────────────┤
│  backend (→ mariadb, redis, minio, kong)                     │
│  chromadb, prometheus                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ depends_on
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Frontend                                            │
├─────────────────────────────────────────────────────────────┤
│  webui (→ backend)                                           │
└─────────────────────────────────────────────────────────────┘

[External Services - 별도 실행 필요]
  litellm (→ litellm-postgres) - 4000
  otel-collector (→ clickhouse) - 4317/4318
  clickhouse - 8124
```

### 4.2 정상 기동을 위한 필수 조건

1. **MariaDB 스키마 초기화**:
   ```bash
   # 최초 1회 또는 볼륨 초기화 후
   ./scripts/init-all-schemas.sh
   ```

2. **외부 서비스 실행** (별도 터미널):
   ```bash
   # LiteLLM + OTEL + ClickHouse
   cd /path/to/agentops && docker compose up -d
   cd /path/to/litellm && docker compose up -d
   ```

3. **Agent Portal 기동**:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

---

## 5. 스키마 초기화 스크립트

### 5.1 전체 초기화 스크립트 생성

```bash
#!/bin/bash
# scripts/init-all-schemas.sh

set -e

echo "=== MariaDB 스키마 초기화 ==="

# Wait for MariaDB to be ready
echo "Waiting for MariaDB..."
until docker exec agent-portal-mariadb-1 mariadb -uroot -prootpass -e "SELECT 1" &>/dev/null; do
    sleep 2
done
echo "MariaDB is ready!"

# Initialize schemas in order (due to foreign key dependencies)
echo "1. Initializing project schema..."
docker exec -i agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal < scripts/init-project-schema.sql

echo "2. Initializing MCP schema..."
docker exec -i agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal < scripts/init-mcp-schema.sql

echo "3. Initializing Data Cloud schema..."
docker exec -i agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal < scripts/init-datacloud-schema.sql

echo "=== 스키마 초기화 완료 ==="

# Verify tables
echo ""
echo "=== 테이블 확인 ==="
docker exec agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal -e "SHOW TABLES;"
```

### 5.2 개별 스키마 파일

| 파일 | 테이블 | 의존성 |
|------|--------|--------|
| `scripts/init-project-schema.sql` | projects, teams, team_members, team_projects | 없음 |
| `scripts/init-mcp-schema.sql` | mcp_servers, mcp_server_tools, mcp_server_projects, mcp_server_permissions, mcp_call_logs | projects |
| `scripts/init-datacloud-schema.sql` | db_connections, db_schema_cache, db_table_cache, db_business_terms, db_connection_permissions, db_query_logs | 없음 |

---

## 6. 환경 변수

### 6.1 필수 환경 변수 (`.env`)

```bash
# MariaDB
MARIADB_ROOT_PASSWORD=rootpass
MARIADB_DATABASE=agent_portal

# Redis
REDIS_PASSWORD=your_redis_password

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# LiteLLM
LITELLM_MASTER_KEY=sk-your-key
LITELLM_SALT_KEY=your-salt-key

# ClickHouse
CLICKHOUSE_DATABASE=otel_2
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password

# Default Project
DEFAULT_PROJECT_ID=8c59e361-3727-418c-bc68-086b69f7598b
```

### 6.2 개발 환경 오버라이드 (`docker-compose.dev.yml`)

```yaml
backend:
  environment:
    - CLICKHOUSE_HOST=host.docker.internal  # 외부 ClickHouse
    - CLICKHOUSE_HTTP_PORT=8124
    
webui:
  environment:
    - OPENAI_API_BASE_URLS=http://host.docker.internal:4000/v1  # 외부 LiteLLM
```

---

## 7. 트러블슈팅

### 7.1 MariaDB 연결 실패

```bash
# 컨테이너 상태 확인
docker compose ps mariadb

# 로그 확인
docker compose logs mariadb --tail=50

# 수동 연결 테스트
docker exec -it agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal
```

### 7.2 스키마 테이블 누락

```bash
# 테이블 확인
docker exec agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal -e "SHOW TABLES;"

# 스키마 재초기화
./scripts/init-all-schemas.sh
```

### 7.3 ClickHouse 연결 실패 (Monitoring)

```bash
# 외부 ClickHouse 상태 확인
curl http://localhost:8124/ping

# Backend 환경변수 확인
docker inspect agent-portal-backend-1 --format '{{range .Config.Env}}{{println .}}{{end}}' | grep CLICKHOUSE
```

---

## 8. 백업 및 복구

### 8.1 MariaDB 백업

```bash
# 전체 백업
docker exec agent-portal-mariadb-1 mysqldump -uroot -prootpass agent_portal > backup_$(date +%Y%m%d).sql

# 복구
docker exec -i agent-portal-mariadb-1 mariadb -uroot -prootpass agent_portal < backup_YYYYMMDD.sql
```

### 8.2 볼륨 백업

```bash
# 볼륨 목록
docker volume ls | grep agent-portal

# 볼륨 백업 (tar)
docker run --rm -v agent-portal_mariadb:/data -v $(pwd):/backup alpine tar cvf /backup/mariadb_backup.tar /data
```

