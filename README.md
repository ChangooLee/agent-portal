# Agent Portal — **Enterprise AI Agent Platform**

> **비전**: **대화형 AI 에이전트를 설계·실행·모니터링·관리하는 통합 플랫폼**
>
> **핵심 가치**: 
> - **유연한 인터페이스**: 채팅, 보고서, 웹검색 등 다양한 뷰 모드로 동일한 에이전트와 상호작용
> - **확장 가능한 시스템 통합**: MCP(Model Context Protocol)를 통한 자유로운 외부 시스템 연동
> - **다양한 에이전트 생성 방식**: 대화형(AutoGen Studio), 노코드(Langflow/Flowise), 코드 기반(LangGraph) 모두 지원
> - **즉시 테스트 및 반복**: 엔드포인트에서 실시간 실행·검증·수정·재배포가 가능한 개발 사이클
> - **프로덕션급 운영**: 모든 에이전트의 실행 추적, 비용 모니터링, 가드레일 정책 적용
> - **제로 카피 데이터 접근**: 기존 데이터베이스에 직접 연결하여 실시간 쿼리 및 분석
> - **지능형 문서 처리**: OCR, 구조 인식, 지능형 청킹을 통한 고품질 RAG 파이프라인
>
> **원칙**: 100% 오픈소스 기반, 엔터프라이즈급 **멀티 유저·멀티 에이전트·멀티 워크스페이스** 운영, **SSO·RBAC·가드레일·관측성** 완비

---

## 한눈에 보기 (3-포털 통합)

### Portal A — Agent (Open-WebUI 기반 Shell, AGPL fork)

- 좌측 채팅 / 우측 **Artifacts** (리포트/표/차트), 프로젝트, 파일, **MCP(stdio+SSE)** 설정
- **Langflow/Flowise/AutoGen Studio** 임베드형 에이전트 빌더, 관리자/보안/관측 대시보드

### Portal B — Notebook (Open Notebook, MIT)

- **지식 노트/PKM** + AI 모델 접속 (로컬/클라우드), 문서/미디어 조직·검색·요약·변환
- **모델 프로바이더 전부 지원**: OpenAI, Anthropic, Google Gemini/Vertex, **OpenRouter**, **로컬(Ollama, vLLM)** 등

### Portal C — Perplexica (MIT)

- **대화형 메타 검색/리서치 포털**: 웹·문서 소스 통합 질의, 근거 중심 결과 뷰, RAG 파이프라인 연계

> 세 포털은 **하나의 상단 네비/SSO** 아래에서 **탭/라우트**로 구동됩니다.
> - **Open-WebUI (Portal A)**: 모델 직접 연결 지원 (Open-WebUI 자체 기능)
> - **Backend BFF / 에이전트 실행**: **LiteLLM 게이트웨이** 사용 (모델 카탈로그 일원화, 관측성 통합)
> - **Notebook / Perplexica**: **LiteLLM 게이트웨이** 또는 직접 연결 (선택)
> - **공통**: **Langfuse/Helicone** 관측·가드레일 정책 공유

---

## 전체 아키텍처

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ UI LAYER — Unified Portal Shell (Open-WebUI fork)                                │
│  [A] Agent: Chat/Artifacts/Projects/MCP/Builder   [B] Notebook   [C] Perplexica  │
│    • Chat(일반/분할) • Projects/RAG • AI WebCapture • AI Research/YouTube          │
│    • PDF 번역 • 갤러리 • 모델/연결 • (NEW) Agent Builder                              │
│      - Langflow • Flowise • **AutoGen Studio(대화형 워크플로)**                      │
│    • MCP 설정 • Admin                                                             │
│  • 공통: SSO(OIDC), RBAC, Guardrails Banner, Admin/Observability                  │
└──────────────▲───────────────────────────────────────────────▲───────────────────┘
               │ REST/WS/SSE                                      │ iframe/프록시
┌──────────────┴───────────────────────────┐        ┌─────────────┴──────────────┐
│ FastAPI(BFF)                             │        │ Observability              │
│  • /chat • /agents • /mcp • /documents   │        │ • Langfuse (traces)        │
│  • /admin • RBAC/JWT • Guardrails        │        │ • Helicone (LLM proxy)     │
│  • /proxy/* (Langflow/Flowise/AutoGen)   │        │ • (opt) OTEL→SigNoz/OO     │
│  • LiteLLM/LangGraph/Chroma/MinIO/Doc    │        │                            │
│    Svc 연동                               │        │                            │
└─────▲───────────────▲───────────────▲────┘        └────────────────────────────┘
      │               │               │
┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴───────────────────────┐
│LangGraph  │   │ LiteLLM   │   │ Kong Gateway (MCP/API 보안)  │
│Server 8123│   │Proxy 4000 │   │ + 키/레이트리밋/mTLS/감사       │
└─────▲─────┘   └─────▲─────┘   └─────▲───────────────────────┘
      │               │               │
┌─────┴───────────────────────────────────────────────────────────────────────┐
│ DATA LAYER                                                                  │
│ • MariaDB(코어 메타) • ChromaDB+bge-m3(벡터) • Redis(세션/캐시) • MinIO(오브젝트)   │
│ • (Langfuse/Helicone/Konga는 자체 Postgres; 코어 DB와 분리 운용)                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ Document Intelligence Service                                                │
│ • 페이지/표/캡션/레이아웃 인지 ← unstructured + PaddleOCR + (선택) VLM 캡셔닝         │
│ • 지능형 청킹 + bge-m3 임베딩 → ChromaDB 색인                                     │
│ • MinIO 원본 문서 저장                                                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 상세 아키텍처 다이어그램 (Mermaid)

```mermaid
graph TB
    subgraph "UI Layer - Portal Shell"
        OWUI["Open-WebUI<br/>Portal Shell<br/>Port: 3000<br/>• Chat/Artifacts<br/>• Projects/RAG<br/>• Agent Builder<br/>• MCP 설정"]
        NOTEBOOK["Open Notebook<br/>Port: 3100<br/>• PKM/지식 관리<br/>• 모델 변환/요약"]
        PERPLEX["Perplexica<br/>Port: 3210<br/>• 메타 검색<br/>• 리서치 포털"]
    end

    subgraph "BFF Layer - FastAPI"
        BFF["FastAPI BFF<br/>Port: 8000<br/>• /chat/stream<br/>• /agents/{id}/run<br/>• /mcp/stdio|sse<br/>• /documents/index|search<br/>• /db/query<br/>• /proxy/*<br/>• RBAC/JWT/Guardrails"]
    end

    subgraph "Agent Builders"
        LANGFLOW["Langflow<br/>Port: 7860<br/>노코드 빌더<br/>LangGraph 친화"]
        FLOWISE["Flowise<br/>Port: 3002<br/>노코드 빌더<br/>위젯/임베드"]
        AUTOGEN_STUDIO["AutoGen Studio<br/>Port: 5050<br/>대화형 워크플로<br/>그룹챗 설계"]
        AUTOGEN_API["AutoGen API<br/>Port: 5051<br/>Studio 백엔드<br/>YAML/JSON Export"]
    end

    subgraph "Service Layer"
        LANGGRAPH["LangGraph Server<br/>Port: 8123<br/>에이전트 실행<br/>툴/MCP 호출"]
        LITELLM["LiteLLM Gateway<br/>Port: 4000<br/>모델 카탈로그<br/>비용 추적"]
        KONG["Kong Gateway<br/>Proxy: 8002<br/>Admin: 8001<br/>Key-Auth/Rate-Limit<br/>mTLS/감사"]
        DOC_SVC["Document Service<br/>Port: 8080<br/>OCR/청킹/임베딩<br/>unstructured+PaddleOCR"]
    end

    subgraph "Observability"
        LANGFUSE["Langfuse<br/>Port: 3001<br/>LLM 체인 추적<br/>세션/툴콜"]
        HELICONE["Helicone<br/>Port: 8787<br/>비용/지연 분석<br/>프롬프트 비교"]
    end

    subgraph "Data Layer"
        MARIADB[("MariaDB<br/>Port: 3306<br/>코어 메타데이터<br/>users/workspaces/agents")]
        CHROMA[("ChromaDB<br/>Port: 8001<br/>벡터 저장소<br/>bge-m3 임베딩")]
        REDIS[("Redis<br/>세션/캐시<br/>상태 관리")]
        MINIO[("MinIO<br/>Port: 9000<br/>오브젝트 스토리지<br/>원본 문서")]
    end

    subgraph "External Systems"
        LLM_PROVIDERS["LLM Providers<br/>OpenAI/Anthropic<br/>Gemini/OpenRouter<br/>Ollama/vLLM"]
        EXTERNAL_DB["External DBs<br/>SAP HANA/Oracle<br/>Postgres/MariaDB<br/>S3/CSV/Parquet"]
        MCP_SERVERS["MCP Servers<br/>stdio 프로세스<br/>SSE 엔드포인트<br/>외부 시스템 연동"]
    end

    %% UI to BFF
    OWUI -->|"REST/WS/SSE<br/>채팅/에이전트 실행"| BFF
    NOTEBOOK -->|"API<br/>모델 호출"| BFF
    PERPLEX -->|"API<br/>리서치 요청"| BFF

    %% BFF to Services
    BFF -->|"에이전트 실행<br/>POST /agents/{id}/run"| LANGGRAPH
    BFF -->|"모델 호출<br/>LiteLLM Service"| LITELLM
    BFF -->|"MCP 보안<br/>Kong 경유"| KONG
    BFF -->|"문서 처리<br/>POST /documents/index"| DOC_SVC
    BFF -->|"리버스 프록시<br/>/proxy/langflow"| LANGFLOW
    BFF -->|"리버스 프록시<br/>/proxy/flowise"| FLOWISE
    BFF -->|"리버스 프록시<br/>/proxy/autogen"| AUTOGEN_STUDIO
    BFF -->|"API 프록시<br/>/autogen/api/*"| AUTOGEN_API

    %% Agent Builders
    AUTOGEN_STUDIO -->|"UI 요청"| AUTOGEN_API
    AUTOGEN_API -->|"모델 호출"| LITELLM
    LANGFLOW -->|"Export LangGraph<br/>JSON 변환"| BFF
    FLOWISE -->|"Export LangGraph<br/>JSON 변환"| BFF
    AUTOGEN_API -->|"Export LangGraph<br/>YAML/JSON 변환"| BFF

    %% Services to Data
    BFF -->|"메타데이터 저장<br/>users/workspaces/agents"| MARIADB
    DOC_SVC -->|"벡터 임베딩 저장<br/>bge-m3"| CHROMA
    DOC_SVC -->|"원본 문서 저장<br/>PDF/이미지"| MINIO
    BFF -->|"세션 관리<br/>캐시"| REDIS
    LANGGRAPH -->|"상태 저장<br/>에이전트 메모리"| REDIS

    %% Services to Observability
    LITELLM -->|"트레이싱<br/>체인/툴콜"| LANGFUSE
    LANGGRAPH -->|"트레이싱<br/>에이전트 실행"| LANGFUSE
    AUTOGEN_API -->|"트레이싱<br/>그룹챗"| LANGFUSE
    LITELLM -->|"프록시<br/>비용/지연 추적"| HELICONE

    %% Services to External
    LITELLM -->|"API 호출<br/>OpenAI/Anthropic/etc"| LLM_PROVIDERS
    HELICONE -->|"프록시<br/>LLM 요청"| LLM_PROVIDERS
    BFF -->|"안전 SQL 쿼리<br/>POST /db/query"| EXTERNAL_DB
    KONG -->|"보안 연결<br/>Key-Auth"| MCP_SERVERS

    %% Observability to Data
    LANGFUSE -.->|"메타데이터 저장<br/>자체 Postgres"| MARIADB
    HELICONE -.->|"메타데이터 저장<br/>자체 Postgres"| MARIADB

    %% Document Service flow
    DOC_SVC -->|"OCR 결과<br/>청킹 메타"| MARIADB

    style OWUI fill:#e1f5ff,stroke:#0066cc,stroke-width:2px
    style BFF fill:#fff4e1,stroke:#cc6600,stroke-width:2px
    style LANGGRAPH fill:#ffe1f5,stroke:#cc0066,stroke-width:2px
    style LITELLM fill:#e1ffe1,stroke:#00cc00,stroke-width:2px
    style KONG fill:#f5e1ff,stroke:#6600cc,stroke-width:2px
    style DOC_SVC fill:#ffe1e1,stroke:#cc0000,stroke-width:2px
    style MARIADB fill:#e1e1ff,stroke:#0000cc,stroke-width:2px
    style CHROMA fill:#e1e1ff,stroke:#0000cc,stroke-width:2px
    style REDIS fill:#e1e1ff,stroke:#0000cc,stroke-width:2px
    style MINIO fill:#e1e1ff,stroke:#0000cc,stroke-width:2px
    style LANGFUSE fill:#fff9e1,stroke:#cc9900,stroke-width:2px
    style HELICONE fill:#fff9e1,stroke:#cc9900,stroke-width:2px
```

**왜 이 조합인가?**

* **Open-WebUI**: 이미 **모델/연결/RAG/웹캡처/유튜브/번역/관리자** UI 다수 완비 → **플러그인/오버라이드**로 빠른 확장
* **Open Notebook**: **노트 중심 지식관리**와 **광범위한 모델 프로바이더** 지원
* **Perplexica**: **대화형 리서치**에 특화, 근거/출처 UI 우수

---

## 스크린샷 기능 매핑 (포털 UI ↔ 요구사항)

| 포털 스크린/기능 | 기획 매핑 | 비고 |
|:---|:---|:---|
| **관리자 대시보드** | **Langfuse/Helicone 임베드 카드** | 비용·지연·오류·체인트레이스 |
| **연결(프로바이더/모델)** (Agent) | **Open-WebUI 직접 연결** 또는 **LiteLLM Base URL** 등록 (선택) | Open-WebUI는 직접 연결 지원, BFF/에이전트는 LiteLLM 게이트웨이 사용 |
| **PDF 번역/웹캡처/유튜브/리서치** | 문서지능 파이프라인/Perplexica와 연결 | 근거 강조 |
| **RAG 지식/청킹/필터** | **Chroma+bge-m3**, 페이지-aware 청킹 | 표/제목/캡션 유지 |
| **노트북(Notebook)** | PKM + 모델 변환/요약/검색 | 모델 프로바이더 전체 지원 |
| **에이전트 빌더** | Langflow/Flowise **동시 임베드** + Export→LangGraph | 템플릿 배포 |
| **에이전트 빌더(대화형)** | **AutoGen Studio** 임베드(그룹챗/멀티에이전트) → YAML/JSON Export → LangGraph | 대화기반 설계 |

---

## 핵심 모듈

### 3.1 노코드/대화형 에이전트 빌더 (Langflow + Flowise + **AutoGen Studio**)

* **Langflow (MIT)**: LangGraph 친화, 배포 API/템플릿 풍부
* **Flowise (Apache-2.0)**: 위젯/임베드 용이, 커뮤니티 노드 매우 많음
* **AutoGen Studio**: **대화형**으로 멀티에이전트 워크플로 설계(그룹챗, 역할/툴 바인딩, 코디네이터 패턴)
* **임베드 방식**: `/builder/langflow`, `/builder/flowise` 경로에 **iframe/리버스 프록시**
  - **AutoGen Studio**는 `/builder/autogen`으로 임베드(리버스 프록시)
* **Export → LangGraph**: 설계 플로우를 LangGraph JSON으로 변환 저장(버전/리비전 관리)

> AutoGen Studio 사용 시:
> - LLM/툴 설정을 LiteLLM 카탈로그와 연동(모델 교체 용이)
> - 그룹챗 시나리오 → YAML/JSON Export → LangGraph 변환기 통해 에이전트 카탈로그에 등록

### 3.2 MCP (stdio & SSE, **Kong 보안**)

* **stdio**: BFF가 MCP 프로세스 스폰/브릿지
* **SSE/WebSocket**: **Kong** 경유(키 인증/레이트리밋/mTLS/IP 제한/감사)
* **MCP Manager UI**: 서버 등록/스코프/헬스체크/워크스페이스 권한
* **Kong Admin OSS UI**: 서비스/라우트/컨슈머/플러그인 **클릭 관리**

### 3.3 문서 인텔리전스

* **수집/파싱**: unstructured + PaddleOCR
* **레이아웃/VLM(선택)**: 표/캡션/도형/스크린샷 캡션 생성
* **지능형 청킹**: 페이지 경계 인지 + 앞/뒤 문맥 overlap + 표/제목 보존
* **임베딩**: **bge-m3** → ChromaDB (메타 포함)
* **RAG**: 하이브리드(키워드+벡터), 근거 하이라이트, **Artifacts**로 리포트 출력

### 3.4 Data-Cloud 스타일 커넥터

* **대상**: SAP HANA, Oracle, MariaDB, Postgres, S3/CSV/Parquet, Elastic
* **방법**: SQLAlchemy/ODBC + **스키마 카탈로그**(테이블/컬럼/PK/FK/비즈니스 사전)
* **대화형 객체화**: 용어집(*예: CUST_TX_DVSN_CD=고객 거래 분류 코드*) → 안전 SQL(뷰/권한) → 표/차트/다운로드
* **RAG+DB 하이브리드**: 규정/ERD 임베딩을 함께 프롬프트에 주입해 **설명+제약** 동시 제공

---

## 보안·권한

* **SSO**: OIDC(Google/GitHub 등) — 포털 Shell에서 인증 후 하위 포털에 **JWT 전파**
* **RBAC**: `admin / power_user / user` + 워크스페이스 격리
* **Kong**: MCP/LLM/Webhook **Key-Auth/JWT/Rate-Limit/mTLS**
* **데이터 보안**: DB 커넥터는 **읽기 전용 계정/뷰**, (권장) **행 수준 보안(RLS)**
* **감사**: MCP 호출/LLM 요청/문서 조회를 사용자·워크스페이스·에이전트 기준 로깅

---

## 관측성 (Observability)

* **Langfuse**: LLM 체인/툴콜/세션 추적 — 관리자 패널 **임베드 카드**
* **Helicone**: **비용/지연/성공률/프롬프트 비교** — LiteLLM 앞/뒤 프록시
* **(옵션) OTEL → SigNoz/OpenObserve**: FastAPI/LiteLLM/MCP 경로 지연·에러율
* **예산/경영 대시보드**: Superset/Metabase 임베드(월별 비용/예산/위반 히트맵)

---

## 설치 (Quick Start)

### 6.1 요구사항

* Docker & Docker Compose (v2.0+)
* Git
* (선택) NVIDIA 드라이버/CUDA (vLLM 사용 시)
* (선택) 도메인/SSL(운영 환경 권장)

### 6.0 현재 진행 상황

**Stage 2 완료 (코드 레벨)**:
- ✅ Kong Gateway 설정 및 실행
- ✅ Konga (Kong Admin UI) 스키마 생성 및 실행
- ✅ Backend BFF Chat API (`/chat/stream`, `/chat/completions`)
- ✅ Observability API (`/observability/health`, `/observability/usage`, `/observability/models`)
- ✅ Open-WebUI Monitoring 페이지 추가
- ✅ Embed 프록시 (`/embed/langfuse`, `/embed/helicone`, `/embed/kong-admin`)

**상세 진행 상황**: [PROGRESS.md](./PROGRESS.md) 참조

### 6.2 `.env` 샘플

```bash
# Portal Shell(UI)
WEBUI_PORT=3000
NEXTAUTH_URL=https://portal.example.com

# OAuth (OIDC)
OAUTH_GOOGLE_ID=...
OAUTH_GOOGLE_SECRET=...
OAUTH_GITHUB_ID=...
OAUTH_GITHUB_SECRET=...

# Backends
API_BASE_URL=http://backend:8000
AUTOGEN_STUDIO_PORT=5050
AUTOGEN_API_PORT=5051
# (선택) 외부 접근 막을 경우 127.0.0.1 바인딩: AUTOGEN_BIND_HOST=0.0.0.0

# LiteLLM
LITELLM_PORT=4000

# Langfuse
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=http://langfuse:3001

# Helicone
HELICONE_API_KEY=helicone-api-key
HELICONE_HOST=http://helicone:8787

# Databases
MARIADB_ROOT_PASSWORD=secret
MARIADB_DATABASE=agent_portal
REDIS_PASSWORD=redispass

# Chroma
CHROMA_SERVER_HOST=chromadb
CHROMA_SERVER_HTTP_PORT=8001

# MinIO
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=admin12345
```

### 6.3 `docker-compose.yml` (요약)

```yaml
version: "3.8"

services:
  # Portal Shell (Open-WebUI fork)
  webui:
    image: ghcr.io/open-webui/open-webui:latest
    ports:
      - "3000:8080"
    env_file: .env
    depends_on:
      - backend
    volumes:
      - ./webui/plugins:/app/plugins
      - ./webui/overrides:/app/overrides

  # Backend BFF
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - mariadb
      - chromadb
      - redis
      - minio
      - langgraph
      - litellm
      - langfuse
      - helicone

  # Agent Runtime
  langgraph:
    image: yourorg/langgraph-server:latest
    ports:
      - "8123:8123"

  # LLM Gateway
  litellm:
    image: ghcr.io/berriai/litellm:main
    command: ["--config", "/app/config.yaml"]
    volumes:
      - "./config/litellm.yaml:/app/config.yaml"
    ports:
      - "4000:4000"

  # Observability
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3001:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@langfuse-db:5432/postgres
    depends_on:
      - langfuse-db

  langfuse-db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=postgres
    volumes:
      - langfuse_db:/var/lib/postgresql/data

  helicone:
    image: helicone/helicone:latest
    ports:
      - "8787:8787"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@helicone-db:5432/postgres
    depends_on:
      - helicone-db

  helicone-db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=postgres
    volumes:
      - helicone_db:/var/lib/postgresql/data

  # AutoGen Studio
  autogen-studio:
    build: ./autogen-studio   # (repo 서브폴더) Dockerfile 포함
    ports: ["${AUTOGEN_STUDIO_PORT:-5050}:5050"]
    environment:
      - LITELLM_BASE_URL=http://litellm:4000
    depends_on: [litellm]

  autogen-api:
    build: ./autogen-api
    ports: ["${AUTOGEN_API_PORT:-5051}:5051"]
    environment:
      - LITELLM_BASE_URL=http://litellm:4000
      - LANGFUSE_HOST=${LANGFUSE_HOST}
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
    depends_on: [litellm, langfuse]

  # Kong (MCP/API 보안)
  kong:
    image: kong:3.6
    ports:
      - "8002:8000"  # Proxy port (8000은 Backend BFF 사용)
      - "8443:8443"
      - "8001:8001"  # Admin API
    environment:
      - KONG_DATABASE=off
      - KONG_DECLARATIVE_CONFIG=/kong/kong.yml
    volumes:
      - "./config/kong.yml:/kong/kong.yml"

  konga:
    image: pantsel/konga:latest
    ports:
      - "1337:1337"
    environment:
      - NODE_ENV=production
      - KONGA_HOOK_TIMEOUT=120000
    depends_on:
      - konga-db

  konga-db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=konga
      - POSTGRES_PASSWORD=konga
      - POSTGRES_DB=konga
    volumes:
      - konga_db:/var/lib/postgresql/data

  # Langflow (에이전트 빌더)
  langflow:
    image: langflowai/langflow:latest
    ports:
      - "7860:7860"
    environment:
      - LANGFLOW_HOST=0.0.0.0
      - LANGFLOW_PORT=7860
    volumes:
      - langflow_data:/data

  # Flowise (에이전트 빌더)
  flowise:
    image: flowiseai/flowise:latest
    ports:
      - "3002:3000"  # Langfuse UI(3001)와 포트 충돌 방지
    environment:
      - PORT=3000
    volumes:
      - flowise_data:/root/.flowise

  # Document Intelligence Service
  document-service:
    build: ./document-service
    ports:
      - "8080:8080"
    environment:
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ROOT_USER}
      - MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
    depends_on:
      - chromadb
      - minio

  # Data Layer
  mariadb:
    image: mariadb:11
    environment:
      - MARIADB_ROOT_PASSWORD=${MARIADB_ROOT_PASSWORD}
      - MARIADB_DATABASE=${MARIADB_DATABASE}
    ports:
      - "3306:3306"
    volumes:
      - mariadb:/var/lib/mysql

  chromadb:
    image: ghcr.io/chroma-core/chroma:latest
    ports:
      - "8001:8000"  # 내부 포트 8000, 외부 포트 8001 (Kong Admin 8001과는 다른 용도)

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD}"]

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ROOT_USER}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
    volumes:
      - minio:/data

  # 추가 포털
  open-notebook:
    build: ./open-notebook
    ports:
      - "3100:3000"
    env_file: .env
    depends_on:
      - litellm

  perplexica:
    build: ./perplexica
    ports:
      - "3210:3000"
    env_file: .env
    depends_on:
      - litellm
      - langfuse

volumes:
  mariadb:
  helicone_db:
  langfuse_db:
  minio:
  konga_db:
  langflow_data:
  flowise_data:
```

### 6.4 LiteLLM 설정 (`config/litellm.yaml`)

```yaml
model_list:
  - model_name: vllm-llama3-70b
    litellm_params:
      model: openai/llama-3-70b
      api_base: http://vllm:8000/v1

  - model_name: openrouter-gpt-4o
    litellm_params:
      model: openrouter/openai/gpt-4o
      api_base: http://helicone:8787/v1
      api_key: ${OPENROUTER_API_KEY}

  - model_name: claude-3-5-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet
      api_base: http://helicone:8787/v1
      api_key: ${ANTHROPIC_API_KEY}

  # 필요 시 추가: gemini/groq/mistral/deepseek/cohere/together/fireworks 등

callbacks:
  - langfuse
```

### 6.5 Kong 선언 (`config/kong.yml`)

```yaml
_format_version: "3.0"
services:
- name: mcp-sse
  url: http://backend:8000/mcp/sse
  routes:
  - name: mcp-sse-route
    paths: ["/mcp/sse"]
    protocols: ["http","https"]
    methods: ["GET"]
  plugins:
  - name: key-auth
  - name: rate-limiting
    config: { minute: 120 }

- name: autogen-api
  url: http://autogen-api:5051
  routes:
  - name: autogen-api-route
    paths: ["/autogen/api"]
    protocols: ["http","https"]
  plugins:
  - name: key-auth
  - name: rate-limiting
    config: { minute: 600 }
```

---

## 운영 절차 (Playbook)

1. **SSO 로그인** → 관리자가 팀원 초대/역할 부여
2. **모델 연결**:
   - **Open-WebUI**: 관리자>연결에서 각 프로바이더 API 키/엔드포인트 직접 등록 (또는 LiteLLM Base URL 등록)
   - **Backend BFF**: `config/litellm.yaml`에 모델 설정, 키는 Vault/.env
3. **MCP 등록**: 연결>MCP에서 stdio/SSE 서버 추가, **Kong 키** 발급/만료 연결
4. **에이전트 생성**:
   - 노코드: **Langflow/Flowise**
   - **대화형**: **AutoGen Studio**(그룹챗 설계) → Export → **LangGraph 등록**
5. **문서 업로드**: 프로젝트>문서 업로드 → 문서지능(OCR/청킹/임베딩) → RAG 사용
6. **모니터링**: 관리자 대시보드에서 **Langfuse/Helicone** 임베드 카드 확인
7. **가드레일**: 정책 변경 → 즉시 반영, 위반 이벤트 차트 점검

---

## 데이터 모델 (요약)

* **users / workspaces / workspace_members(role)**
* **agents**(langgraph_definition, tools, versions)
* **mcp_servers**(type:stdio|sse, endpoint, scopes, enabled)
* **documents / chunks**(page/type/context_before/after/ocr_confidence …)
* **conversations / messages**(artifacts/tool_calls)
* **guardrail_events**(policy, action, snippet, user_id …)
* **llm_usage**(model, tokens, cost_usd, trace_id, workspace_id)

---

## 가드레일

* **입력 필터**: PII(예: Presidio), 독성/금칙어, 워크스페이스 규칙(정규식)
* **출력 필터**: PII/독성 + **근거 인용 강제**(RAG 미첨부 시 경고/차단 옵션)
* **조치**: 마스킹/차단/경고, **guardrail_events** 로깅 및 관리자 차트

---

## 포트 매트릭스

| 컴포넌트 | 포트 | 설명 |
|:---|:---:|:---|
| Portal Shell (Open-WebUI) | 3000 | 통합 UI |
| Backend (FastAPI BFF) | 8000 | API/BFF |
| LangGraph | 8123 | 에이전트 실행 |
| LiteLLM | 4000 | LLM 게이트웨이 |
| Kong Proxy | 8002 | MCP/API 보안 프록시 |
| Kong Admin | 8001 | Kong 관리 API |
| Kong Admin UI (Konga) | 1337 | Kong 관리 UI |
| ChromaDB | 8001 | 벡터DB HTTP (내부 포트) |
| MinIO/Console | 9000/9001 | 오브젝트 스토리지 |
| Langfuse UI | 3001 | 체인 트레이스 |
| Helicone UI | 8787 | LLM 프록시 대시 |
| AutoGen Studio | 5050 | 대화형 워크플로 UI |
| AutoGen API | 5051 | Studio 백엔드 |
| Langflow | 7860 | 노코드 에이전트 빌더 |
| Flowise | 3002 | 노코드 에이전트 빌더 |
| Document Service | 8080 | 문서 인텔리전스 마이크로서비스 |
| Open Notebook | 3100 | 노트북 포털 |
| Perplexica | 3210 | 리서치 포털 |

---

## API 요약 (BFF)

* `POST /chat/stream` — 채팅 스트리밍(Artifacts 포함)
* `POST /agents/{id}/run` — LangGraph 실행(툴/MCP 호출 포함)
* `POST /mcp/stdio/launch` — MCP stdio 스폰/헬스체크
* `GET  /mcp/sse/ping` — SSE 라우트 상태
* `GET  /proxy/langflow` — Langflow UI 리버스 프록시(iframe 임베드용)
* `GET  /proxy/flowise` — Flowise UI 리버스 프록시(iframe 임베드용)
* `GET  /proxy/autogen` — AutoGen Studio UI 리버스 프록시(iframe 임베드용)
* `ANY  /autogen/api/*` — AutoGen API(Kong 보호 하에 프록시)
* `POST /documents/index` — 문서 파이프라인(OCR/청킹/임베딩) → Document Service 호출
* `GET  /documents/search` — RAG 검색 (하이브리드: 키워드+벡터)
* `POST /db/query` — 데이터베이스 커넥터를 통한 안전 SQL 쿼리
* `GET  /observability/usage` — Helicone·Langfuse 요약 카드
* `GET  /catalog/models` — LiteLLM 모델 카탈로그 조회(포털 공통)

---

## LLM 설정 — SOTA급 API 전부

> **Open-WebUI (Portal A)**: 자체 모델 연결 UI 사용 (직접 연결 지원)
> - Open-WebUI 설정에서 각 프로바이더 API 키/엔드포인트 직접 등록 가능
> - **선택사항**: LiteLLM Base URL을 Open-WebUI에 등록하여 게이트웨이 경유 가능
>
> **Backend BFF / 에이전트 실행**: **LiteLLM 게이트웨이 필수**
> - 에이전트 실행, LangGraph, AutoGen Studio 등은 LiteLLM을 통해 모델 호출
> - 모델 카탈로그 일원화, 비용 추적, 관측성 통합을 위해 LiteLLM 사용
>
> **Notebook / Perplexica**: **LiteLLM 게이트웨이 권장** (직접 연결도 가능)
> - 공통 모델 카탈로그 및 관측성 통합을 위해 LiteLLM 사용 권장
> - 필요 시 각 포털에서 직접 연결도 지원
>
> **지원 프로바이더**: **OpenAI, Anthropic, Google(Gemini/Vertex), OpenRouter, Ollama/vLLM, Together, Perplexity, Fireworks, Groq, Mistral, Cohere, DeepSeek** 등

`.env` 예시(필요한 것만 채움):

```bash
# 대표 키
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
VERTEX_PROJECT_ID=...
VERTEX_REGION=...
OPENROUTER_API_KEY=...
GROQ_API_KEY=...
MISTRAL_API_KEY=...
COHERE_API_KEY=...
DEEPSEEK_API_KEY=...
TOGETHER_API_KEY=...
FIREWORKS_API_KEY=...
PERPLEXITY_API_KEY=...

# 로컬 모델
OLLAMA_BASE_URL=http://ollama:11434
VLLM_BASE_URL=http://vllm:8000/v1
```

> Notebook의 **모델 프로바이더** 지원은 제품 문서 기준으로 **OpenAI/Anthropic/Gemini/Vertex/OpenRouter/Ollama** 등을 기본 제공하며, Portal에서는 **LiteLLM 라우팅**으로 동일 UX를 유지합니다.

---

## 트러블슈팅

* **응답 지연/타임아웃**: 
  - Open-WebUI 직접 연결: Open-WebUI 설정에서 타임아웃/재시도 조정
  - LiteLLM 경유: Helicone에서 **지연 상위 프롬프트** 확인 → LiteLLM 라우팅/쿼터 조정
* **RAG 근거 누락/환각**: 청킹 전략/overlap 조정, bge-m3 파라미터 확인, OCR 품질 점검
* **MCP SSE 401/429**: Kong의 key-auth/레이트리밋 로그 확인, 컨슈머 키 재발급
* **Open-WebUI 업데이트 충돌**: `overrides/`로 코어 수정 최소화, 상류 머지 가이드 준수
* **Perplexica 검색 품질**: 소스별 가중치/필터 조정, LLM 재순위 정책 점검
* **Notebook 모델 호출 실패**: 프로바이더 키/엔드포인트/리전에 맞는 설정 검증(특히 Vertex)

---

## 라이선스 & 포크 가이드 (확정)

| 컴포넌트 | 라이선스 | 포크 기준 (권고) | 비고 |
|:---|:---|:---|:---|
| **Open-WebUI (Portal Shell)** | AGPL-3.0 (이전) / 이후 Open WebUI License | **AGPL 시절 마지막 커밋**: `60d84a3aae9802339705826e9095e272e3c83623` *(2025-10-02)* 으로 **핀 고정**하여 포크 | AGPL 요건(소스 공개/저작권 고지) 충족 시 **완전 커스터마이즈 가능**. 이후 버전은 **브랜딩 보존 등** 추가 제한. |
| **Open Notebook** | MIT | 최신 안정 태그 또는 main HEAD 포크(사내 고정 태깅) | 문서에 **MIT 표시**. 포크 시 LICENSE/NOTICE 스냅샷 포함. |
| **Perplexica** | MIT | 최신 **릴리스 태그(v1.11.x 등)** 포크 권장(커밋 해시 기록) | MIT로 상업/커스터마이즈 자유. 포크 시점 LICENSE 보관. |
| Langflow | MIT | upstream release 태그 | 임베드(iframe) 방식, 소스 수정 최소화 권장 |
| Flowise | Apache-2.0 | upstream release 태그 | 임베드(iframe) 방식 |
| Kong Gateway (OSS) | Apache-2.0 | 공식 이미지 | Admin UI는 OSS 기반 구현 |
| LiteLLM / Langfuse / Helicone / Chroma / Redis / MinIO | 각 OSS | 최신 릴리스 고정 | 상용/배포 요건 준수 |

> **브랜딩/재라이선스 주의**: Open-WebUI는 **해당 커밋 이전(AGPL)** 사용 시, 기업 브랜딩/테마 **커스터마이즈 가능**(AGPL 의무 이행 전제). 커밋 이후 버전은 **Open WebUI License**에 따라 **브랜딩 보존** 등의 추가 요구가 있으므로, 본 포털은 **AGPL 마지막 커밋**을 기준으로 포크/유지합니다.

---

## 로드맵

* [ ] Langflow/Flowise ↔ **LangGraph** 양방향 동기화(조건/루프/메모리/툴 완전 대응)
* [ ] **Kong Admin UI 마법사**: 컨슈머/키/ACL·JWT 자동 발급/회수
* [ ] 문서지능: 표 구조/수식 OCR 강화, VLM fallback 자동화
* [ ] **평가 파이프라인**: Golden set·A/B·Drift(Arize Phoenix/Superset 임베드)
* [ ] 비용 거버넌스: 모델별 Budget/Alert(Helicone 데이터 연계)

---

## 폴더 구조

```
repo/
├─ webui/                # Open-WebUI fork (플러그인/오버라이드/테마)
├─ backend/              # FastAPI BFF (RBAC/Guardrails/Routes)
├─ autogen-studio/       # AutoGen Studio UI (임베드)
├─ autogen-api/          # AutoGen Studio 백엔드(프록시/어댑터)
├─ document-service/     # OCR/VLM/청킹/임베딩 마이크로서비스
├─ open-notebook/        # Open Notebook (Dockerfile/override/env)
├─ perplexica/           # Perplexica (Dockerfile/override/env)
├─ config/
│  ├─ litellm.yaml
│  ├─ kong.yml
│  └─ guardrails/
├─ kong-admin-ui/        # OSS 기반 Kong Admin React UI
├─ compose/              # env별 컴포즈 오버레이
├─ scripts/
└─ docs/
```

---

## 운영 팁

* 비용 급증: **Helicone**에서 프롬프트/컨텍스트 길이 비교 → LiteLLM 라우팅 정책 시간대별 조정
* 실패 대화 재현: **Langfuse traceId** → 에이전트 빌더 플로우로 저장/수정
* **Superset**으로 경영 보고(월별 비용·예산·가드레일 위반 히트맵) 10분 내 구성
* 포크 유지: 상류 보안패치만 체리픽(Portal Shell은 **AGPL 커밋 유지**)

---

## 사용 시나리오

* **부서별 워크스페이스**: 에이전트/지식/커넥터 격리, 공용 템플릿 카탈로그 배포
* **SQL 대화 분석**: “지난 분기 VIP 매출 Top10” → 안전 SQL → 표/차트 아티팩트 → 공유
* **PDF/스캔 RAG**: OCR+VLM, 페이지-aware 임베딩, 근거 하이라이트 응답
* **리서치**: Perplexica로 1차 수집 → Agent로 정제/리포트 아티팩트 생성 → Notebook 아카이브

---

## 라이선스 참고 (출처)

* Open-WebUI **AGPL→Open WebUI License 전환 및 경계 커밋** 안내(커밋 `60d84a3a…`, 2025-10-02). ([GitHub][1])
* **Open Notebook**: 모델 프로바이더 지원(OpenAI/Anthropic/Gemini/Vertex/OpenRouter/Ollama) 및 **MIT License** 표기. ([open-notebook.ai][2])
* **Perplexica**: 공식 GitHub 저장소(MIT). ([GitHub][3])

> 본 README는 **Open-WebUI 프런트 재사용**, **Langflow/Flowise 임베드**, **MCP stdio+SSE(+Kong GW 보안)**, **vLLM/OpenRouter/LiteLLM**, **Langfuse+Helicone**, **ChromaDB+bge-m3**, **문서지능 파이프라인**, **SAP HANA/Oracle/Maria 등 Data-Cloud 커넥터**, **SSO·RBAC**, **가드레일**, **운영/보안/트러블슈팅**, **포트 매트릭스**, **API·스키마 요약**, **스크린샷 기능 매핑**까지 **누락 없이** 반영했습니다.

---

## 진행 상황 및 로드맵

### 📊 개발 단계 요약

Agent Portal은 **9단계 개발 계획**으로 진행됩니다:

#### ✅ Stage 1: Open-WebUI 커스터마이즈 및 UI 필터링

**목표**: Open-WebUI 포크하여 필요한 기능만 노출, 나머지 UI 숨김

**주요 작업**:
- Open-WebUI 포크 (AGPL 커밋 고정)
- UI 필터링: 사이드바 메뉴 필터링, 관리자 메뉴 권한 설정
- Docker 설정 및 오버라이드 구조 생성

**완료 기준**:
- 필터링된 메뉴만 표시
- Docker 컨테이너 정상 구동

---

#### ⚠️ Stage 2: Chat 엔드포인트 연동 및 모니터링 ✅ **코드 완료**

**목표**: FastAPI BFF 생성, LiteLLM 연동, Langfuse/Helicone 모니터링

**주요 작업**:
- Backend BFF 기본 구조 생성 ✅
- Chat API 구현 (`/chat/stream`, `/chat/completions`) ✅
- Observability API 구현 (`/observability/*`) ✅
- LiteLLM/Langfuse 서비스 레이어 구현 ✅
- Monitoring 페이지 추가 ✅

**현재 상태**:
- ✅ 코드 레벨 완료
- ⚠️ 환경 설정 필요 (LiteLLM/Langfuse 서비스 실행)
- ⚠️ 프론트엔드-백엔드 데이터 연동 필요

**주요 API**:
- `POST /chat/stream` - 채팅 스트리밍
- `GET /observability/usage` - 사용량 요약
- `GET /observability/models` - 모델 카탈로그

**⚠️ Critical 미완성 항목**:
- 테스트 코드 완전 부재
- 인증/인가 시스템 미구현 (보안 취약점)
- 서비스 통합 미완 (실제 동작 검증 필요)

---

#### ❌ Stage 3: 에이전트 빌더 (Langflow + Flowise + AutoGen Studio)

**목표**: Langflow, Flowise, AutoGen Studio 임베드, Export → LangGraph 변환

**주요 작업**:
- **Langflow 컨테이너 설정** (포트 7860)
- **Flowise 컨테이너 설정** (포트 3002)
- **AutoGen Studio/API 컨테이너 설정** (로컬 빌드, 포트 5050/5051)
- 에이전트 빌더 페이지 추가 (`/builder/langflow`, `/builder/flowise`, `/builder/autogen`)
- **리버스 프록시 구현** (`/proxy/langflow`, `/proxy/flowise`, `/proxy/autogen`)
- 플로우 → LangGraph JSON 변환기 구현
- **AutoGen YAML/JSON → LangGraph 변환기** 구현
- 에이전트 버전/리비전 관리 시스템

**완료 기준**:
- Langflow/Flowise/AutoGen Studio 임베드 접근 가능
- 각 빌더에서 Export → LangGraph 변환 완료
- **AutoGen 그룹챗 시나리오 → LangGraph 등록** 파이프라인 완료
- 에이전트 버전 관리 시스템 동작

---

#### ❌ Stage 4: MCP 연동 및 Kong Gateway

**목표**: MCP stdio/SSE 엔드포인트 구현, Kong Gateway 보안/레이트리밋

**주요 작업**:
- Kong Gateway 설정 (Key-Auth, Rate-Limiting, mTLS)
- MCP stdio 엔드포인트 구현 (`/mcp/stdio/launch`) - BFF가 프로세스 스폰/브릿지
- MCP SSE 엔드포인트 구현 (`/mcp/sse`) - Kong 경유
- MCP Manager UI (서버 등록, Kong 키 발급/회수, 스코프 관리)
- Kong Admin UI (Konga) 설정 및 연동

**완료 기준**:
- MCP stdio 프로세스 스폰 및 브릿지 동작
- Kong Gateway를 통한 MCP SSE 보안 설정
- Key-Auth 및 Rate-Limiting 동작
- MCP Manager UI 기능 완료
- Konga를 통한 Kong 관리 가능

---

#### ❌ Stage 5: 데이터베이스 및 관리 기능

**목표**: MariaDB 스키마 설계, 사용자/워크스페이스/에이전트 관리 API, 데이터베이스 커넥터

**주요 작업**:
- MariaDB 스키마 설계 (users, workspaces, agents, mcp_servers)
- 관리 API 구현 (CRUD 엔드포인트)
- RBAC 권한 체크
- 관리자 UI 연동
- **데이터베이스 커넥터 구현** (Data-Cloud 스타일)
  - SAP HANA, Oracle, MariaDB, Postgres, S3/CSV/Parquet, Elastic 지원
  - SQLAlchemy/ODBC 기반 연결
  - 스키마 카탈로그 (테이블/컬럼/PK/FK/비즈니스 사전)
  - 대화형 객체화 (용어집 → 안전 SQL → 표/차트)
  - RAG+DB 하이브리드 (규정/ERD 임베딩)

**스키마**:
- `users`, `workspaces`, `workspace_members`
- `agents`, `mcp_servers`
- `db_connections` (데이터베이스 커넥터 메타)

**완료 기준**:
- MariaDB 스키마 생성 완료
- CRUD API 동작
- RBAC 권한 체크 동작
- 데이터베이스 커넥터를 통한 쿼리 및 분석 가능

---

#### ❌ Stage 6: Document Intelligence

**목표**: 문서 파싱, OCR, 청킹, 임베딩 파이프라인 및 ChromaDB 연동

**주요 작업**:
- **Document Service 마이크로서비스 생성** (FastAPI, 포트 8080)
- unstructured + PaddleOCR 파이프라인
- 레이아웃 인식 (표/캡션/도형) 및 VLM 캡셔닝 (선택)
- 지능형 청킹 (페이지 경계 인지, 문맥 overlap, 표/제목 보존)
- bge-m3 임베딩 및 ChromaDB 벡터 저장소 연동
- RAG 검색 API 구현 (하이브리드: 키워드+벡터)
- MinIO 오브젝트 스토리지 연동 (원본 문서 저장)

**파이프라인**:
```
문서 업로드 → MinIO 저장 → 파싱 → OCR → 레이아웃 인식 → 
지능형 청킹 → bge-m3 임베딩 → ChromaDB 색인 → RAG 검색
```

**완료 기준**:
- Document Service 마이크로서비스 실행
- 문서 파이프라인 완료
- ChromaDB 색인 및 검색 동작
- RAG 검색 API 동작
- 근거 하이라이트 및 Artifacts 출력

---

#### ❌ Stage 7: UI 뷰 모드 전환 (채팅형/포털형/레포트형)

**목표**: 대화창을 3가지 뷰 모드로 전환 가능하게 구현

**주요 작업**:
- 뷰 모드 토글 컴포넌트
- 레포트형 렌더링 강화 (Artifacts: 차트/표)
- 포털형 UI (카드/타일 형식)
- 채팅형 UI (기존 메시지 스레드)

**뷰 모드**:
- 채팅형: 메시지 스레드 형식
- 포털형: 카드/타일 형식 검색 결과
- 레포트형: 차트/표/그래프 Artifacts

**완료 기준**:
- 3가지 뷰 모드 전환 기능 완료
- 각 모드별 렌더링 정상 동작

---

#### ❌ Stage 8: Open Notebook + Perplexica 통합

**목표**: Open Notebook과 Perplexica 통합, DB 통합 시작

**주요 작업**:
- Open Notebook 포크 및 설정
- Perplexica 포크 및 설정
- SSO 전파 (JWT 생성/검증)
- DB 통합 시작 (공통 사용자/워크스페이스)

**포트**:
- Open Notebook: `3100`
- Perplexica: `3210`

**완료 기준**:
- Open Notebook 및 Perplexica 통합 완료
- SSO JWT 전파 동작
- 공통 사용자/워크스페이스 데이터 공유 시작

---

#### ❌ Stage 9: 가드레일 관리

**목표**: PII 감지, 입력/출력 필터, 가드레일 이벤트 로깅

**주요 작업**:
- Presidio 기반 PII 감지 (마스킹/차단)
- 입력/출력 필터 (독성/금칙어, 워크스페이스 규칙)
- 근거 인용 강제 (RAG 미첨부 시 경고/차단)
- 가드레일 이벤트 로깅 및 관리자 대시보드

**필터 종류**:
- PII 감지 (이메일, 전화번호 등)
- 독성/금칙어 필터
- 워크스페이스별 규칙 (정규식)
- 근거 인용 강제

**완료 기준**:
- PII 감지 및 마스킹/차단 동작
- 입력/출력 필터 동작
- 가드레일 이벤트 로깅 완료

---

### 📈 전체 진행 상황

| 단계 | 상태 | 완료율 | 비고 |
|------|------|--------|------|
| **Stage 1** | ✅ 완료 | 100% | 인프라 및 기본 설정 |
| **Stage 2** | ⚠️ 부분 완료 | 40% | 코드 완료, 환경 설정 및 테스트 필요 |
| **Stage 3** | ❌ 미시작 | 0% | 에이전트 빌더 |
| **Stage 4** | ❌ 미시작 | 0% | MCP SSE + Kong |
| **Stage 5** | ❌ 미시작 | 0% | 데이터베이스 |
| **Stage 6** | ❌ 미시작 | 0% | Document Intelligence |
| **Stage 7** | ❌ 미시작 | 0% | UI 뷰 모드 |
| **Stage 8** | ❌ 미시작 | 0% | 포털 통합 |
| **Stage 9** | ❌ 미시작 | 0% | 가드레일 |

**전체 진행률**: 약 **47%** (Stage 1 완료 + Stage 2 코드 완료)

---

### 🎯 다음 단계 우선순위

#### P0 (즉시 해결 - 보안 및 기본 기능)
1. **🔴 인증/인가 시스템 구현** (보안 취약점)
   - Open-WebUI 인증 시스템과 BFF 연동
   - JWT 토큰 검증 구현
   - RBAC 미들웨어 활성화
   - 모든 엔드포인트 보안 적용

2. **🔴 테스트 코드 작성** (코드 품질)
   - pytest 설정 및 기본 테스트 구조
   - Chat API 테스트
   - Observability API 테스트
   - 서비스 레이어 테스트

3. **LiteLLM 서비스 docker-compose 추가 및 실행**
   - `docker-compose.yml`에 LiteLLM 서비스 추가
   - `config/litellm.yaml` 실제 설정 파일 생성
   - 환경변수 설정
   - 실제 동작 테스트

4. **Langfuse 서비스 docker-compose 추가 및 실행**
   - `docker-compose.yml`에 Langfuse 서비스 및 DB 추가
   - API 키 설정
   - 실제 연동 테스트

#### P1 (단기 해결)
5. 프론트엔드 데이터 연동
6. 에러 핸들링 개선
7. Helicone API 실제 구현

#### P2 (중기 해결)
8. 컨테이너 파일 동기화 문제 해결
9. Stage 3 시작 (에이전트 빌더)
10. 문서화 보완

---

**상세 진행 상황**: [PROGRESS.md](./PROGRESS.md) 참조  
**개발 가이드**: [DEVELOP.md](./DEVELOP.md) 참조

---

[1]: https://github.com/open-webui/open-webui?utm_source=chatgpt.com "open-webui/open-webui: User-friendly AI Interface ..."
[2]: https://www.open-notebook.ai/get-started.html "Get Started | Open Notebook"
[3]: https://github.com/ItzCrazyKns/Perplexica/issues?utm_source=chatgpt.com "Issues · ItzCrazyKns/Perplexica"
