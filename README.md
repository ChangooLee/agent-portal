# Agent Portal — **Enterprise AI Agent Platform**

> **비전**: **대화형 AI 에이전트를 설계·실행·모니터링·관리하는 통합 플랫폼**
>
> **핵심 가치**: 
> - **유연한 인터페이스**: 채팅, 보고서, 웹검색 등 다양한 뷰 모드로 동일한 에이전트와 상호작용
> - **확장 가능한 시스템 통합**: MCP(Model Context Protocol)를 통한 자유로운 외부 시스템 연동
> - **다양한 에이전트 생성 방식**: 대화형, 노코드, 코드 기반(LangGraph) 모두 지원
> - **즉시 테스트 및 반복**: 엔드포인트에서 실시간 실행·검증·수정·재배포가 가능한 개발 사이클
> - **프로덕션급 운영**: 모든 에이전트의 실행 추적, 비용 모니터링, 가드레일 정책 적용
> - **제로 카피 데이터 접근**: 기존 데이터베이스에 직접 연결하여 실시간 쿼리 및 분석
>
> **원칙**: 100% 오픈소스 기반, 엔터프라이즈급 **멀티 유저·멀티 에이전트·멀티 워크스페이스** 운영, **SSO·RBAC·가드레일·관측성** 완비

---

## 📊 현재 상태 (2025-12-05)

### ✅ 완료된 기능

| 기능 | 상태 | 설명 |
|------|------|------|
| **Portal Shell** | ✅ 완료 | Open-WebUI 기반 통합 UI (포트 3009) |
| **LLM Gateway** | ✅ 완료 | LiteLLM Proxy (포트 4000) |
| **모니터링** | ✅ 완료 | LiteLLM + OTEL + ClickHouse |
| **Data Cloud** | ✅ 완료 | MariaDB/PostgreSQL/ClickHouse 연결 |
| **Text-to-SQL Agent** | ✅ 완료 | LangGraph 기반 Plan-and-Execute 패턴 |
| **MCP 관리** | ✅ 완료 | MCP 서버 등록/관리 UI |
| **Kong Gateway** | ✅ 완료 | API Gateway + Konga Admin UI |
| **사용자 관리** | ✅ 완료 | Open-WebUI SQLite 기반 |

### 🔧 주요 서비스

| 서비스 | 포트 | 상태 | 용도 |
|--------|------|------|------|
| webui | 3009 | ✅ Running | Portal UI (SvelteKit) |
| backend | 8000 | ✅ Running | FastAPI BFF |
| litellm | 4000 | ✅ Running | LLM Gateway |
| mariadb | 3306 | ✅ Running | App Database |
| clickhouse | 8124 | ✅ Running | Trace Storage (OTEL) |
| kong | 8002 | ✅ Running | API Gateway |
| konga | 1337 | ✅ Running | Kong Admin UI |
| redis | 6379 | ✅ Running | Cache |
| prometheus | 9090 | ✅ Running | Metrics |

---

## 🏗 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                      http://localhost:3009                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Open-WebUI (port 3009)                        │
│              SvelteKit Frontend + Vite Proxy                     │
│    /api/* → Backend BFF    /admin/* → Admin Pages                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Backend BFF (port 8000)                        │
│                         FastAPI                                  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│  │   Chat   │ Monitor  │DataCloud │   MCP    │ Text2SQL │       │
│  │  /chat   │/monitor  │/datacloud│  /mcp    │/text2sql │       │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘       │
└───────┼──────────┼──────────┼──────────┼──────────┼─────────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ LiteLLM │ │ClickHs  │ │ MariaDB │ │  Kong   │ │LangGraph│
   │  :4000  │ │  :8124  │ │  :3306  │ │  :8002  │ │  Agent  │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
        │
        ▼
   ┌─────────────────────────────────────────┐
   │           OTEL Collector                 │
   │         :4317 (gRPC) :4318 (HTTP)       │
   └─────────────────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────────────────┐
   │              ClickHouse                  │
   │    otel_2.otel_traces (trace storage)   │
   └─────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/ChangooLee/agent-portal.git
cd agent-portal

# .env 파일 설정 (예시 복사)
cp .env.example .env
# .env 파일에서 API 키 설정
```

### 2. 서비스 실행

```bash
# 전체 서비스 실행
docker compose up -d

# 상태 확인
./scripts/health-check.sh
```

### 3. 접속

- **Portal UI**: http://localhost:3009
- **Backend API Docs**: http://localhost:8000/docs
- **LiteLLM Admin**: http://localhost:4000/ui
- **Kong Admin (Konga)**: http://localhost:1337

---

## 📁 프로젝트 구조

```
agent-portal/
├── backend/                    # FastAPI BFF
│   ├── app/
│   │   ├── main.py            # App entry, router registration
│   │   ├── routes/            # API endpoints
│   │   │   ├── chat.py        # /chat/*
│   │   │   ├── monitoring.py  # /monitoring/*
│   │   │   ├── datacloud.py   # /datacloud/*
│   │   │   ├── text2sql.py    # /text2sql/*
│   │   │   ├── mcp.py         # /mcp/*
│   │   │   └── gateway.py     # /gateway/*
│   │   ├── services/          # Business logic
│   │   │   ├── litellm_service.py
│   │   │   ├── monitoring_adapter.py
│   │   │   ├── datacloud_service.py
│   │   │   └── mcp_registry.py
│   │   └── agents/
│   │       └── text2sql/      # LangGraph Text-to-SQL Agent
│   │           ├── state.py   # Agent state definition
│   │           ├── nodes.py   # LangGraph nodes
│   │           ├── graph.py   # StateGraph configuration
│   │           └── tools.py   # DB tools
│   └── requirements.txt
│
├── webui/                      # Open-WebUI fork (SvelteKit)
│   ├── src/
│   │   ├── routes/
│   │   │   └── (app)/
│   │   │       ├── +page.svelte       # Chat page
│   │   │       └── admin/
│   │   │           ├── monitoring/    # Monitoring dashboard
│   │   │           ├── datacloud/     # Data Cloud management
│   │   │           ├── mcp/           # MCP server management
│   │   │           └── gateway/       # Gateway overview
│   │   └── lib/
│   │       ├── components/    # Shared components
│   │       └── monitoring/    # Monitoring-specific components
│   └── vite.config.ts         # Proxy configuration
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
├── docker-compose.yml         # Base orchestration
├── docker-compose.prod.yml    # Production overrides
│
├── AGENTS.md                  # AI Agent technical reference
└── README.md                  # This file
```

---

## 🔍 모니터링

### LLM 모니터링 스택

```
LiteLLM → OTEL Collector → ClickHouse → Backend BFF → Frontend
```

- **LiteLLM**: LLM 호출 시 OTEL 트레이스 생성
- **OTEL Collector**: 트레이스 수집 및 ClickHouse로 전송
- **ClickHouse**: `otel_2.otel_traces` 테이블에 트레이스 저장
- **Backend BFF**: ClickHouse 쿼리 및 API 제공
- **Frontend**: Agent/LLM Call/All 서브탭으로 트레이스 표시

### Monitoring Dashboard 기능

| 탭 | 내용 |
|---|---|
| **Overview** | Total Cost, LLM Calls, Agent Calls, Avg Latency, Fail Rate |
| **Analytics** | Cost Trend, Token Usage, Agent Flow Graph |
| **Traces** | Agent / LLM Call / All 서브탭으로 트레이스 필터링 |
| **Replay** | 세션 리플레이 (개발 중) |

---

## 🗄 Data Cloud

### 지원 데이터베이스

| DB | 상태 | 드라이버 |
|---|---|---|
| MariaDB | ✅ 지원 | pymysql |
| PostgreSQL | ✅ 지원 | psycopg2 |
| ClickHouse | ✅ 지원 | clickhouse-driver |
| Oracle | 🔧 드라이버 필요 | cx_Oracle |
| SAP HANA | 🔧 드라이버 필요 | hdbcli |
| Databricks | 🔧 드라이버 필요 | databricks-sql-connector |

### Text-to-SQL Agent

LangGraph 기반 Plan-and-Execute 패턴:

```
1. entry → 2. analyze → 3. generate → 4. validate → 
5. fix (if needed) → 6. execute → 7. format → 8. complete
```

**특징**:
- OTEL 기반 트레이스 로깅
- 다중 DB 지원 (Dialect 자동 감지)
- 스키마 캐싱
- 에러 자동 복구 (최대 3회 재시도)

---

## 🔌 MCP (Model Context Protocol)

### MCP 서버 관리

- **등록**: Admin > MCP에서 서버 등록
- **연결 방식**: stdio, SSE, Streamable HTTP
- **보안**: Kong Gateway를 통한 Key-Auth, Rate-Limiting

### Kong Gateway

- **Proxy**: http://localhost:8002
- **Admin API**: http://localhost:8001
- **Admin UI (Konga)**: http://localhost:1337
- **설정 가이드**: [docs/KONGA_SETUP.md](./docs/KONGA_SETUP.md)

---

## 📚 문서

| 문서 | 설명 |
|------|------|
| [AGENTS.md](./AGENTS.md) | AI Agent 기술 레퍼런스 |
| [docs/SERVICE-DATABASE-STATUS.md](./docs/SERVICE-DATABASE-STATUS.md) | 서비스 및 DB 상태 |
| [docs/MONITORING_SETUP.md](./docs/MONITORING_SETUP.md) | 모니터링 설정 가이드 |
| [docs/KONGA_SETUP.md](./docs/KONGA_SETUP.md) | Kong Gateway 설정 가이드 |
| [docs/TEXT2SQL_AGENT.md](./docs/TEXT2SQL_AGENT.md) | Text-to-SQL Agent 설명서 |

---

## 🛠 개발

### 로컬 개발 환경

```bash
# Backend 개발 (hot reload)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend 개발 (hot reload)
cd webui && npm install
npm run dev
```

### 서비스 재빌드

```bash
# 특정 서비스 재빌드
docker compose build --no-cache backend
docker compose up -d backend

# 전체 재빌드
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 로그 확인

```bash
# 특정 서비스 로그
docker compose logs backend --tail=50 -f

# 전체 로그
docker compose logs --tail=20 -f
```

---

## 📋 트러블슈팅

### 포트 충돌

```bash
# 포트 사용 확인
lsof -i :8000

# 프로세스 종료
kill -9 <PID>
```

### DB 연결 실패

```bash
# MariaDB 확인
docker compose exec mariadb mariadb -uroot -prootpass -e "SELECT 1;"

# ClickHouse 확인
curl http://localhost:8124/ping
```

### CORS 에러

```typescript
// ❌ WRONG: Direct call
fetch('http://localhost:8000/api/...')

// ✅ CORRECT: Use Vite proxy
fetch('/api/...')
```

---

## 📜 라이선스

| 컴포넌트 | 라이선스 |
|----------|----------|
| Open-WebUI (Portal Shell) | AGPL-3.0 (포크 기준 커밋) |
| LiteLLM | MIT |
| Kong Gateway (OSS) | Apache-2.0 |
| ClickHouse | Apache-2.0 |
| 본 프로젝트 코드 | MIT |

---

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Last Updated**: 2025-12-05
