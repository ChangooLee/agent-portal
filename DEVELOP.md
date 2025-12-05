# Agent Portal — 개발 가이드 (DEVELOP.md)

> 본 문서는 Agent Portal의 단계별 개발 계획, 포크 전략, 테스트 절차, CI/CD 파이프라인을 포함한 개발 가이드입니다.

---

## 0. 사전 준비

### 0.1 Git 저장소 구조 설정

```bash
repo/
├─ webui/                # Open-WebUI fork
├─ backend/              # FastAPI BFF
├─ document-service/    # OCR/VLM/청킹/임베딩 마이크로서비스
├─ open-notebook/       # Open Notebook fork
├─ perplexica/          # Perplexica fork
├─ config/
│  ├─ litellm.yaml
│  ├─ kong.yml
│  └─ guardrails/
├─ kong-admin-ui/       # OSS 기반 Kong Admin React UI
├─ compose/             # env별 컴포즈 오버레이
├─ scripts/
│  ├─ setup-forks.sh
│  ├─ test-stage-*.sh
│  └─ deploy.sh
├─ .github/
│  └─ workflows/
│     ├─ stage-1.yml
│     ├─ stage-2.yml
│     └─ ...
└─ docs/
```

### 0.2 개발 환경 요구사항

- Docker & Docker Compose (v2.0+)
- Git
- Node.js 18+ (webui 개발용)
- Python 3.10+ (backend 개발용)
- (선택) NVIDIA 드라이버/CUDA (vLLM 사용 시)

**AutoGen Studio 관련**:
- AutoGen Studio는 로컬 빌드 방식 사용 (라이선스 충돌 회피 및 커스터마이즈 용이)
- `autogen-studio/`, `autogen-api/` 디렉토리에 Dockerfile 포함 필요

### 0.3 초기 저장소 설정

```bash
# 저장소 초기화
git init
git branch -M main

# 기본 .gitignore 생성
echo "*.env
*.log
__pycache__/
node_modules/
*.pyc
.DS_Store
.env.local" > .gitignore
```

### 0.4 WebUI 개발 모드 (Hot Reload)

UI 코드 수정 시 전체 재빌드 없이 즉시 반영되도록 개발 모드를 사용할 수 있습니다.

#### 개발 모드 실행

```bash
# 개발 모드 시작 (Hot Reload 지원)
./scripts/dev-webui.sh

# 또는 직접 docker-compose 실행
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build webui
```

#### 개발 모드 특징

- **Hot Reload**: `webui/src/` 디렉토리의 파일 변경 시 자동으로 브라우저에 반영
- **빠른 반복**: 전체 이미지 재빌드 불필요
- **기존 포트 사용**: 포트 3000을 그대로 사용 (프로덕션과 동일)
- **볼륨 마운트**: 소스 코드가 실시간으로 컨테이너에 마운트됨

#### 개발 모드 vs 프로덕션 모드

| 항목 | 개발 모드 | 프로덕션 모드 |
|:---|:---|:---|
| 실행 방법 | `docker-compose.dev.yml` 사용 | `docker-compose.yml` 사용 |
| 빌드 시간 | 즉시 시작 (의존성만 설치) | 전체 빌드 필요 (5-10분) |
| Hot Reload | 지원 | 미지원 |
| 포트 | 3000 (기존과 동일) | 3000 (빌드된 정적 파일) |
| 소스 코드 | 볼륨 마운트 (실시간 반영) | 이미지에 포함 (재빌드 필요) |

#### 개발 모드 접속

- **프론트엔드**: http://localhost:3001 (Vite dev server, 백엔드 API 자동 프록시)
- **백엔드 API 직접 접근**: http://localhost:8080 (내부용, 프록시를 통해 사용)

#### 주의사항

- 개발 모드에서는 `node_modules`가 볼륨으로 분리되어 성능이 최적화됩니다
- 의존성 추가 시 컨테이너를 재시작해야 할 수 있습니다
- 프로덕션 배포 전에는 반드시 프로덕션 빌드로 테스트하세요

---

## 1. 포크 전략 및 라이선스

### 1.1 포크할 오픈소스 리스트

| 컴포넌트 | 라이선스 | 포크 기준 | 저장소 위치 | 비고 |
|:---|:---|:---|:---|:---|
| **Open-WebUI** | AGPL-3.0 | 커밋 `60d84a3aae9802339705826e9095e272e3c83623` (2025-10-02) | `webui/` | AGPL 마지막 커밋 고정 |
| **Open Notebook** | MIT | 최신 안정 태그 또는 main HEAD | `open-notebook/` | LICENSE 포함 |
| **Perplexica** | MIT | 최신 릴리스 태그 (v1.11.x 등) | `perplexica/` | 포크 시점 LICENSE 보관 |
| Langflow | MIT | upstream release 태그 | (임베드만) | iframe 방식 |
| Flowise | Apache-2.0 | upstream release 태그 | (임베드만) | iframe 방식 |

### 1.2 포크 스크립트 (`scripts/setup-forks.sh`)

```bash
#!/bin/bash
set -e

# Open-WebUI 포크 (AGPL 커밋 고정)
echo "Forking Open-WebUI..."
cd webui
git clone https://github.com/open-webui/open-webui.git .
git checkout 60d84a3aae9802339705826e9095e272e3c83623
git checkout -b agent-portal-custom
cd ..

# Open Notebook 포크
echo "Forking Open Notebook..."
cd open-notebook
git clone https://github.com/open-notebook/open-notebook.git .
# 최신 태그 확인 및 체크아웃
LATEST_TAG=$(git describe --tags --abbrev=0)
git checkout $LATEST_TAG
git checkout -b agent-portal-custom
cd ..

# Perplexica 포크
echo "Forking Perplexica..."
cd perplexica
git clone https://github.com/ItzCrazyKns/Perplexica.git .
# 최신 릴리스 태그 확인
LATEST_RELEASE=$(git describe --tags --abbrev=0)
git checkout $LATEST_RELEASE
git checkout -b agent-portal-custom
cd ..

echo "All forks completed. Check LICENSE files in each directory."
```

### 1.3 라이선스 준수 체크리스트

- [ ] 각 포크 디렉토리에 LICENSE 파일 보존
- [ ] AGPL 의무: 소스 공개 및 저작권 고지
- [ ] MIT/Apache-2.0: LICENSE 파일 포함
- [ ] 상용 배포 시 라이선스 요구사항 재확인

---

## 2. 단계별 개발 계획

### 2.1 1단계: Open-WebUI 커스터마이즈 및 UI 필터링

**목표**: Open-WebUI를 포크하여 필요한 기능만 노출하고 나머지 UI는 숨김 처리

#### 작업 내용

1. **Open-WebUI 포크 및 기본 설정**
   ```bash
   cd webui
   # setup-forks.sh 실행 또는 수동 포크
   ```

2. **UI 필터링 설정**
   - `webui/overrides/` 디렉토리 생성
   - 사이드바 메뉴 필터링 (필요 기능만 표시)
   - 관리자 메뉴 접근 권한 설정

3. **Docker 설정**
   - `webui/Dockerfile` 생성 (기본 이미지 확장)
   - `webui/.dockerignore` 설정

4. **환경 변수 설정**
   ```bash
   # .env
   WEBUI_PORT=3000
   WEBUI_DISABLE_SIGNUP=true
   WEBUI_DEFAULT_USER_ROLE=user
   ```

#### 구현 작업

**파일 구조:**

```
webui/
├─ Dockerfile
├─ .dockerignore
├─ overrides/
│  ├─ components/
│  │  └─ Sidebar.tsx          # 메뉴 필터링
│  └─ pages/
│     └─ Settings.tsx         # 설정 페이지 커스터마이즈
└─ plugins/
   └─ custom-features/        # 커스텀 기능 플러그인
```

**주요 수정 사항:**
- `overrides/components/Sidebar.tsx`: 불필요한 메뉴 항목 숨김
- 기본 채팅, 프로젝트, 설정 메뉴만 노출
- 관리자 메뉴는 `admin` 역할만 접근

#### docker-compose 설정

```yaml
services:
  webui:
    build: ./webui
    ports:
      - "3000:8080"
    env_file: .env
    environment:
      - WEBUI_DISABLE_SIGNUP=true
      - WEBUI_DEFAULT_USER_ROLE=user
    volumes:
      - ./webui/overrides:/app/overrides
      - ./webui/plugins:/app/plugins
```

#### 테스트 절차

1. **구동 테스트**
   ```bash
   docker-compose up -d webui
   ```

2. **기본 동작 확인**
   - [ ] `http://localhost:3000` 접근 가능
   - [ ] 기본 로그인 화면 표시
   - [ ] 사이드바에 채팅, 프로젝트, 설정만 표시
   - [ ] 관리자 메뉴는 admin 역할에서만 표시

3. **회귀 테스트**
   - [ ] 기본 채팅 기능 동작
   - [ ] 프로젝트 생성/삭제 동작

#### 완료 기준

- [ ] Open-WebUI 기본 화면에서 필터링된 메뉴만 표시
- [ ] 불필요한 기능 UI 숨김 처리 완료
- [ ] Docker 컨테이너 정상 구동 및 접근 가능

---

### 2.2 2단계: Chat 엔드포인트 연동 및 모니터링 ✅ **완료**

**목표**: FastAPI BFF 생성, LiteLLM 연동, Langfuse/Helicone 모니터링 및 관리자 화면 임베드

**상태**: ✅ **코드 레벨 완료** (환경 설정 필요)

#### 작업 내용

1. **Backend BFF 기본 구조 생성** ✅
   ```bash
   mkdir -p backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install fastapi uvicorn litellm langfuse-sdk
   ```

2. **LiteLLM 설정** ⚠️
   - `config/litellm.yaml` 생성 (구조 준비)
   - 기본 모델 리스트 설정 (테스트용) - 환경 설정 필요

3. **관찰성 도구 설정** ✅
   - Langfuse 컨테이너 추가 (docker-compose.yml)
   - Helicone 컨테이너 추가 (docker-compose.yml)
   - Langfuse/Helicone 서비스 레이어 구현 완료

4. **관리자 대시보드 임베드** ✅
   - Langfuse/Helicone iframe 카드 추가
   - Monitoring 페이지 구현 (`webui/src/routes/(app)/admin/monitoring/+page.svelte`)

#### 구현 작업

**파일 구조:**

```
backend/
├─ Dockerfile
├─ requirements.txt
├─ app/
│  ├─ __init__.py
│  ├─ main.py                 # FastAPI 앱
│  ├─ routes/
│  │  ├─ chat.py              # /chat/stream
│  │  └─ observability.py     # /observability/*
│  ├─ services/
│  │  ├─ litellm_service.py   # LiteLLM 연동
│  │  └─ langfuse_service.py  # Langfuse 연동
│  └─ config.py
```

**주요 API:**
- `POST /chat/stream`: 채팅 스트리밍
- `GET /observability/usage`: Langfuse/Helicone 요약 데이터
- `GET /catalog/models`: LiteLLM 모델 카탈로그

**webui 오버라이드:**

- `overrides/pages/Admin.tsx`: 모니터링 임베드 카드 추가

#### docker-compose 설정

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - litellm
      - langfuse
      - helicone

  litellm:
    image: ghcr.io/berriai/litellm:main
    command: ["--config", "/app/config.yaml"]
    volumes:
      - ./config/litellm.yaml:/app/config.yaml
    ports:
      - "4000:4000"

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
```

#### 테스트 절차

1. **구동 테스트**
   ```bash
   docker-compose up -d backend litellm langfuse helicone
   ```

2. **API 동작 확인**
   - [ ] `POST /chat/stream` 엔드포인트 동작
   - [ ] LiteLLM을 통한 모델 호출 성공
   - [ ] Langfuse에 트레이스 기록
   - [ ] Helicone에 요청 로깅

3. **관리자 화면 확인**
   - [ ] 관리자 대시보드에 Langfuse/Helicone 임베드 카드 표시
   - [ ] 모니터링 데이터 정상 조회

#### 완료 기준

- [x] 채팅 스트리밍 API 코드 구현 완료 (`/chat/stream`, `/chat/completions`)
- [x] LiteLLM 게이트웨이 서비스 레이어 구현 완료 (`litellm_service.py`)
- [x] Langfuse/Helicone 서비스 레이어 구현 완료 (`langfuse_service.py`)
- [x] Observability API 엔드포인트 구현 완료 (`/observability/*`)
- [x] 관리자 화면에 모니터링 페이지 추가 완료
- [ ] LiteLLM 서비스 실행 및 설정 (환경 설정 필요)
- [ ] Langfuse/Helicone 실제 연동 테스트 (환경 설정 필요)
- [ ] 프론트엔드-백엔드 데이터 연동 (BFF API 호출)

**참고**: 상세 진행 상황은 [PROGRESS.md](./PROGRESS.md) 참조

---

### 2.3 3단계: 에이전트 빌더 (Langflow + Flowise + AutoGen Studio) 🚧 **진행 중**

**목표**: Langflow, Flowise, AutoGen Studio를 임베드하고, Langflow UI 재구현, LangGraph 변환 + 실행 + Opentelemetry 모니터링

**상태**: 🚧 **Phase 1-A 완료, Phase 1-B 진행 중**

#### 작업 내용

1. **Langflow/Flowise/AutoGen Studio 컨테이너 설정** ✅
   - Langflow: 포트 7861 (Stable Diffusion 충돌 회피)
   - Flowise: 포트 3002
   - AutoGen Studio: 포트 5050 (UI)
   - AutoGen API: 포트 5051 (백엔드)
   - 각각 별도 컨테이너로 실행 (AutoGen은 로컬 빌드)
   - 리버스 프록시 설정 (`/api/proxy/langflow`, `/api/proxy/flowise`, `/api/proxy/autogen`)

2. **Open-WebUI 에이전트 빌더 페이지 추가** ✅
   - `/agent` 라우트에 탭 UI 구현
   - iframe 임베드 (직접 포트 접근)

3. **Langflow UI 재구현 - Phase 1-A** ✅
   - Backend API: `/api/agents/flows` (목록/상세/삭제)
   - Frontend: 플로우 카드 그리드 (Glassmorphism)
   - 검색/필터 (Fuse.js)

4. **Langflow UI 재구현 - Phase 1-B** 🚧
   - AgentOps SDK 통합 (에이전트 실행 모니터링)
   - Langflow → LangGraph 변환기 구현
   - LangGraph 실행 서비스 구현
   - 변환/실행 API 엔드포인트 추가
   - 플로우 카드 컴포넌트 (Export/Run 버튼)
   - 실행 결과 패널 (비용 정보, AgentOps 리플레이 링크)

5. **Phase 2 (미래)** ❌
   - Flowise/AutoGen 플로우 → LangGraph JSON 변환
   - 버전/리비전 관리 시스템

#### 구현 작업

**파일 구조:**

```
backend/
└─ app/
   ├─ routes/
   │  ├─ agents.py            # /api/agents/flows/* (목록/상세/삭제/변환/실행)
   │  └─ proxy.py              # /api/proxy/langflow, /api/proxy/flowise, /api/proxy/autogen
   └─ services/
      ├─ langflow_converter.py # Langflow → LangGraph 변환
      └─ langgraph_service.py # LangGraph 실행 서비스

autogen-studio/              # AutoGen Studio UI (임베드)
├─ Dockerfile
└─ ...

autogen-api/                 # AutoGen Studio 백엔드(프록시/어댑터)
├─ Dockerfile
└─ ...

webui/
└─ overrides/
   └─ pages/
      ├─ BuilderLangflow.tsx  # Langflow 임베드
      ├─ BuilderFlowise.tsx   # Flowise 임베드
      └─ BuilderAutogen.tsx   # AutoGen Studio 임베드
```

#### docker-compose 설정

```yaml
services:
  langflow:
    image: langflowai/langflow:latest
    ports:
      - "7860:7860"
    environment:
      - LANGFLOW_DATABASE_URL=sqlite:///./langflow.db
    volumes:
      - langflow_data:/data

  flowise:
    image: flowiseai/flowise:latest
    ports:
      - "3002:3000"  # Langfuse UI(3001)와 포트 충돌 방지
    environment:
      - PORT=3000
    volumes:
      - flowise_data:/root/.flowise

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
      - AGENTOPS_API_KEY=${AGENTOPS_API_KEY}
    depends_on: [litellm, langfuse]

volumes:
  langflow_data:
  flowise_data:
```

#### 테스트 절차

1. **구동 테스트**
   ```bash
   docker-compose up -d langflow flowise autogen-studio autogen-api
   ```

2. **빌더 접근 확인**
   - [ ] `/builder/langflow` 접근 가능
   - [ ] `/builder/flowise` 접근 가능
   - [ ] `/builder/autogen` 접근 가능
   - [ ] iframe 임베드 정상 동작

3. **플로우 생성 및 Export**
   - [ ] Langflow에서 간단한 플로우 생성
   - [ ] Flowise에서 간단한 플로우 생성
   - [ ] AutoGen Studio에서 그룹챗 시나리오 생성
   - [ ] 각 빌더에서 Export 버튼 클릭 시 LangGraph JSON 생성
   - [ ] 저장된 에이전트 정의 확인

4. **리버스 프록시 확인**
   - [ ] `/proxy/langflow` 프록시 동작
   - [ ] `/proxy/flowise` 프록시 동작
   - [ ] `/proxy/autogen` 프록시 동작
   - [ ] `/autogen/api/*` Kong 보호 하에 프록시 동작

#### 완료 기준

- [ ] Langflow/Flowise/AutoGen Studio 임베드 접근 가능
- [ ] 플로우 생성 및 저장 기능 동작
- [ ] Export → LangGraph 변환 완료 (Langflow/Flowise/AutoGen 모두)
- [ ] AutoGen 그룹챗 시나리오 → LangGraph 등록 파이프라인 완료
- [ ] 리버스 프록시 동작 확인

---

### 2.4 4단계: MCP SSE 연동 및 Kong Gateway

**목표**: MCP SSE 엔드포인트 구현, Kong Gateway를 통한 보안 및 레이트리밋 설정

#### 작업 내용

1. **Kong Gateway 설정**
   - Kong 선언적 설정 (`config/kong.yml`)
   - Key-Auth, Rate-Limiting 플러그인 설정

2. **MCP SSE 엔드포인트 구현**
   - `backend/app/routes/mcp.py` 생성
   - SSE 스트리밍 구현

3. **MCP Manager UI**
   - Open-WebUI에 MCP 설정 페이지 추가
   - Kong 키 발급/회수 기능

4. **Kong Admin UI**
   - Kong Admin UI 컨테이너 추가

#### 구현 작업

**파일 구조:**

```
backend/
└─ app/
   ├─ routes/
   │  └─ mcp.py               # /mcp/*
   └─ services/
      └─ mcp_sse.py           # SSE 브릿지

config/
└─ kong.yml                   # Kong 선언적 설정

kong-admin-ui/
├─ Dockerfile
└─ src/                       # Kong Admin React UI

webui/
└─ overrides/
   └─ pages/
      └─ MCPManager.tsx       # MCP 설정 UI
```

#### docker-compose 설정

```yaml
services:
  kong:
    image: kong:3.6
    ports:
      - "8000:8000"
      - "8443:8443"
      - "8001:8001"
    environment:
      - KONG_DATABASE=off
      - KONG_DECLARATIVE_CONFIG=/kong/kong.yml
    volumes:
      - ./config/kong.yml:/kong/kong.yml

  kong-admin-ui:
    build: ./kong-admin-ui
    ports:
      - "9090:80"
    environment:
      - KONG_ADMIN_URL=http://kong:8001
```

#### Kong 설정 (`config/kong.yml`)

```yaml
_format_version: "3.0"
services:
  - name: mcp-sse
    url: http://backend:8000/mcp/sse
    routes:
      - name: mcp-sse-route
        paths: ["/mcp/sse"]
        protocols: ["http", "https"]
        methods: ["GET"]
    plugins:
      - name: key-auth
      - name: rate-limiting
        config:
          minute: 120
          hour: 1000

  - name: autogen-api
    url: http://autogen-api:5051
    routes:
      - name: autogen-api-route
        paths: ["/autogen/api"]
        protocols: ["http", "https"]
    plugins:
      - name: key-auth
      - name: rate-limiting
        config:
          minute: 600

consumers:
  - username: agent-portal-user
    keyauth_credentials:
      - key: test-key-12345
```

#### 테스트 절차

1. **구동 테스트**
   ```bash
   docker-compose up -d kong kong-admin-ui backend
   ```

2. **MCP SSE 연결 확인**
   - [ ] Kong을 통한 `/mcp/sse` 접근 (키 인증)
   - [ ] SSE 스트리밍 정상 동작
   - [ ] 레이트리밋 동작 확인

3. **MCP Manager UI 확인**
   - [ ] MCP 설정 페이지 접근
   - [ ] Kong 키 발급/조회 기능

4. **Kong Admin UI 확인**
   - [ ] `http://localhost:9090` 접근
   - [ ] 서비스/라우트/플러그인 관리 가능

#### 완료 기준

- [ ] Kong Gateway를 통한 MCP SSE 보안 설정 완료
- [ ] Key-Auth 및 Rate-Limiting 동작 확인
- [ ] MCP Manager UI 기능 완료
- [ ] Kong Admin UI 접근 및 관리 가능

---

### 2.5 5단계: 데이터베이스 및 관리 기능

**목표**: MariaDB 스키마 설계, 사용자/워크스페이스/에이전트 관리 API 구현

#### 작업 내용

1. **MariaDB 스키마 설계**
   - 사용자, 워크스페이스, 에이전트 테이블
   - 마이그레이션 스크립트

2. **관리 API 구현**
   - CRUD 엔드포인트
   - RBAC 권한 체크

3. **관리자 UI 연동**
   - 사용자/워크스페이스/에이전트 관리 페이지

#### 구현 작업

**파일 구조:**

```
backend/
└─ app/
   ├─ db/
   │  ├─ models.py            # SQLAlchemy 모델
   │  └─ migrations/
   │     └─ 001_initial.sql   # 초기 스키마
   ├─ routes/
   │  └─ admin.py              # /admin/*
   └─ services/
      └─ rbac.py               # RBAC 체크
```

**스키마 설계:**
- `users` (id, email, role, created_at)
- `workspaces` (id, name, created_at)
- `workspace_members` (workspace_id, user_id, role)
- `agents` (id, name, langgraph_definition, workspace_id, version, created_at)
- `mcp_servers` (id, name, type, endpoint, scopes, workspace_id, enabled)

#### docker-compose 설정

```yaml
services:
  mariadb:
    image: mariadb:11
    ports:
      - "3306:3306"
    environment:
      - MARIADB_ROOT_PASSWORD=${MARIADB_ROOT_PASSWORD}
      - MARIADB_DATABASE=${MARIADB_DATABASE}
    volumes:
      - mariadb:/var/lib/mysql
      - ./backend/app/db/migrations:/docker-entrypoint-initdb.d
```

#### 테스트 절차

1. **구동 테스트**
   ```bash
   docker-compose up -d mariadb backend
   ```

2. **스키마 확인**
   - [ ] MariaDB 접속 및 테이블 생성 확인
   - [ ] 마이그레이션 스크립트 실행 확인

3. **API 동작 확인**
   - [ ] 사용자 CRUD 동작
   - [ ] 워크스페이스 CRUD 동작
   - [ ] 에이전트 CRUD 동작
   - [ ] 권한 격리 동작 (워크스페이스별)

4. **관리자 UI 확인**
   - [ ] 사용자 관리 페이지 접근
   - [ ] 워크스페이스 관리 페이지 접근
   - [ ] 에이전트 관리 페이지 접근

#### 완료 기준

- [ ] MariaDB 스키마 생성 완료
- [ ] 사용자/워크스페이스/에이전트 CRUD API 동작
- [ ] RBAC 권한 체크 동작
- [ ] 관리자 UI 연동 완료

---

### 2.6 6단계: Document Intelligence

**목표**: 문서 파싱, OCR, 청킹, 임베딩 파이프라인 구현 및 ChromaDB 연동

#### 작업 내용

1. **Document Service 마이크로서비스 생성**
   - unstructured + PaddleOCR 파이프라인
   - 청킹 및 임베딩 처리

2. **ChromaDB 설정**
   - 벡터 저장소 구성
   - bge-m3 임베딩 모델 연동

3. **RAG 연동**
   - 문서 업로드 → 파이프라인 처리 → ChromaDB 색인
   - 검색 API 구현

#### 구현 작업

**파일 구조:**

```
document-service/
├─ Dockerfile
├─ requirements.txt
└─ app/
   ├─ main.py
   ├─ services/
   │  ├─ parser.py            # unstructured 파싱
   │  ├─ ocr.py               # PaddleOCR
   │  ├─ chunking.py          # 지능형 청킹
   │  └─ embedding.py         # bge-m3 임베딩
   └─ routes/
      └─ documents.py          # /documents/*

backend/
└─ app/
   └─ routes/
      └─ documents.py          # 프록시/통합 엔드포인트
```

#### docker-compose 설정

```yaml
services:
  document-service:
    build: ./document-service
    ports:
      - "8002:8000"
    env_file: .env
    depends_on:
      - chromadb

  chromadb:
    image: ghcr.io/chroma-core/chroma:latest
    ports:
      - "8001:8000"
    environment:
      - IS_PERSISTENT=TRUE
      - PERSIST_DIRECTORY=/chroma/chroma
    volumes:
      - chroma_data:/chroma/chroma
```

#### 테스트 절차

1. **구동 테스트**
   ```bash
   docker-compose up -d document-service chromadb
   ```

2. **문서 업로드 파이프라인 확인**
   - [ ] PDF 업로드 → 파싱 성공
   - [ ] OCR 처리 성공
   - [ ] 청킹 처리 성공
   - [ ] 임베딩 생성 및 ChromaDB 저장

3. **검색 기능 확인**
   - [ ] 벡터 검색 동작
   - [ ] 하이브리드 검색 (키워드+벡터) 동작
   - [ ] 검색 결과 근거 표시

#### 완료 기준

- [ ] 문서 파이프라인 (파싱/OCR/청킹/임베딩) 완료
- [ ] ChromaDB 색인 및 검색 동작
- [ ] RAG 검색 API 동작

---

### 2.7 7단계: UI 뷰 모드 전환 (채팅형/포털형/레포트형)

**목표**: 대화창을 채팅형, 포털형, 레포트형으로 자유롭게 전환 가능하게 구현

#### 작업 내용

1. **뷰 모드 토글 컴포넌트**
   - Open-WebUI 오버라이드로 뷰 모드 선택기 추가

2. **레포트형 렌더링 강화**
   - Artifacts 렌더링 (차트/표)
   - 검색 결과를 리포트 형식으로 변환

3. **포털형 UI**
   - 검색 결과를 카드/타일 형식으로 표시

#### 구현 작업

**파일 구조:**

```
webui/
└─ overrides/
   └─ components/
      ├─ ViewModeToggle.tsx   # 뷰 모드 선택
      ├─ ChatView.tsx         # 채팅형
      ├─ PortalView.tsx       # 포털형
      └─ ReportView.tsx       # 레포트형
```

#### 테스트 절차

1. **뷰 모드 전환 확인**
   - [ ] 채팅형 → 포털형 전환 동작
   - [ ] 포털형 → 레포트형 전환 동작
   - [ ] 레포트형 → 채팅형 전환 동작

2. **각 모드 렌더링 확인**
   - [ ] 채팅형: 메시지 스레드 형식
   - [ ] 포털형: 카드/타일 형식 검색 결과
   - [ ] 레포트형: 차트/표/그래프 Artifacts

#### 완료 기준

- [ ] 3가지 뷰 모드 전환 기능 완료
- [ ] 각 모드별 렌더링 정상 동작
- [ ] Artifacts 리포트 형식 표시 완료

---

### 2.8 8단계: Perplexica + Open-Notebook 임베드

**목표**: Perplexica와 Open-Notebook을 Open-WebUI 포털 쉘에 iframe으로 임베드

#### 작업 내용

1. **Perplexica 포크 및 컨테이너 설정**
   - 포크 완료 (1단계에서 수행)
   - Docker 설정 (포트 5173)
   - LiteLLM 연동

2. **Open-Notebook 포크 및 컨테이너 설정**
   - 포크 완료 (1단계에서 수행)
   - Docker 설정 (포트 3030)
   - LiteLLM Base URL 연동

3. **FastAPI BFF 리버스 프록시 구현**
   - `/proxy/perplexica/{path:path}` 프록시 라우트
   - `/proxy/notebook/{path:path}` 프록시 라우트
   - 헤더 변환 (X-Frame-Options 제거, CSP frame-ancestors 'self' 추가)

4. **Open-WebUI Apps 탭 추가**
   - `/apps/perplexica` 라우트 (iframe 임베드)
   - `/apps/notebook` 라우트 (iframe 임베드)
   - iframe 컴포넌트 구현 (전체 화면 높이, 로딩 스켈레톤, 에러 처리)

5. **Kong 헤더 정규화 (선택)**
   - response-transformer 플러그인으로 X-Frame-Options 제거
   - CSP frame-ancestors 'self' 추가

#### 구현 작업

**파일 구조:**

```
perplexica/
├─ Dockerfile
└─ .env.example

open-notebook/
├─ Dockerfile
└─ .env.example

backend/
└─ app/
   ├─ routes/
   │  └─ proxy.py              # /proxy/perplexica, /proxy/notebook 추가
   └─ services/
      └─ proxy_service.py      # 프록시 헤더 변환 로직

webui/
└─ overrides/
   └─ pages/
      ├─ AppsPerplexica.tsx    # Perplexica iframe 페이지
      └─ AppsNotebook.tsx       # Open-Notebook iframe 페이지
```

#### docker-compose 설정

```yaml
services:
  # Perplexica (검색 포털, iframe 임베드)
  perplexica:
    build: ./perplexica        # 리포지토리 서브모듈/복제 후 Dockerfile로 빌드
    environment:
      - PORT=${PERPLEXICA_PORT}
    ports: ["${PERPLEXICA_PORT:-5173}:5173"]
    depends_on:
      - litellm

  # Open-Notebook (AI 노트북, iframe 임베드)
  notebook:
    build: ./open-notebook     # lfnovo/open-notebook 소스 빌드
    environment:
      - PORT=${NOTEBOOK_PORT}
      # Notebook이 외부 모델을 직접 쓰지 않고 LiteLLM을 경유하도록 선택 가능
      - LITELLM_BASE_URL=http://litellm:4000
    ports: ["${NOTEBOOK_PORT:-3030}:3030"]
    depends_on:
      - litellm
```

#### Kong 설정 (`config/kong.yml`) - 선택사항

```yaml
# (선택) Perplexica/Notebook 직접 접근 차단 및 헤더 정규화
- name: perplexica-svc
  url: http://perplexica:5173
  routes:
  - name: perplexica-route
    paths: ["/perplexica/"]
    protocols: ["http","https"]
  plugins:
  - name: response-transformer
    config:
      remove: { headers: ["X-Frame-Options"] }
      add:
        headers:
          - "Content-Security-Policy: frame-ancestors 'self'"

- name: notebook-svc
  url: http://notebook:3030
  routes:
  - name: notebook-route
    paths: ["/notebook/"]
    protocols: ["http","https"]
  plugins:
  - name: response-transformer
    config:
      remove: { headers: ["X-Frame-Options"] }
      add:
        headers:
          - "Content-Security-Policy: frame-ancestors 'self'"
```

#### 테스트 절차

1. **구동 테스트**
   ```bash
   docker-compose up -d perplexica notebook backend
   ```

2. **Apps 탭 접근 확인**
   - [ ] `/apps/perplexica` 접근 가능
   - [ ] `/apps/notebook` 접근 가능
   - [ ] iframe 임베드 정상 동작

3. **리버스 프록시 확인**
   - [ ] `/proxy/perplexica` 프록시 동작
   - [ ] `/proxy/notebook` 프록시 동작
   - [ ] 동일 도메인 접근 (CORS/XFO 이슈 없음)

4. **LiteLLM 연동 확인**
   - [ ] Perplexica에서 모델 호출 시 LiteLLM 경유
   - [ ] Open-Notebook에서 모델 호출 시 LiteLLM 경유
   - [ ] 관측성 통합 확인 (Langfuse/Helicone)

5. **헤더 변환 확인**
   - [ ] X-Frame-Options 제거 확인
   - [ ] CSP frame-ancestors 'self' 추가 확인

#### 완료 기준

- [ ] Perplexica 및 Open-Notebook이 포털 Apps 탭에서 iframe으로 정상 표시
- [ ] 리버스 프록시를 통한 동일 도메인 접근 (CORS/XFO 이슈 없음)
- [ ] LiteLLM을 통한 모델 호출 및 관측성 통합
- [ ] (옵션) SSO 인증 전파 동작

---

### 2.9 9단계: 가드레일 관리

**목표**: PII 감지, 입력/출력 필터, 가드레일 이벤트 로깅 및 관리자 대시보드

#### 작업 내용

1. **Presidio 기반 PII 감지**
   - 입력/출력 텍스트 스캔
   - 감지된 PII 마스킹 또는 차단

2. **입력/출력 필터 구현**
   - 독성/금칙어 필터
   - 워크스페이스 규칙 (정규식)
   - 근거 인용 강제 (RAG 미첨부 시 경고/차단)

3. **가드레일 이벤트 로깅**
   - `guardrail_events` 테이블에 이벤트 저장
   - 관리자 대시보드에 차트 표시

#### 구현 작업

**파일 구조:**

```
backend/
└─ app/
   ├─ services/
   │  ├─ guardrails.py        # 가드레일 로직
   │  ├─ pii_detection.py     # Presidio 연동
   │  └─ content_filter.py   # 독성/금칙어 필터
   └─ routes/
      └─ guardrails.py        # 가드레일 정책 관리

config/
└─ guardrails/
   ├─ toxic_words.txt         # 금칙어 리스트
   └─ workspace_rules.json    # 워크스페이스별 규칙
```

#### docker-compose 설정

```yaml
services:
  backend:
    # ... 기존 설정
    volumes:
      - ./config/guardrails:/app/config/guardrails
```

#### 테스트 절차

1. **PII 감지 확인**
   - [ ] 입력 텍스트에 이메일/전화번호 포함 시 감지
   - [ ] 마스킹 또는 차단 동작 확인

2. **필터 동작 확인**
   - [ ] 독성/금칙어 필터 동작
   - [ ] 워크스페이스 규칙 적용 확인
   - [ ] 근거 미첨부 시 경고/차단 동작

3. **이벤트 로깅 확인**
   - [ ] `guardrail_events` 테이블에 이벤트 저장
   - [ ] 관리자 대시보드에 차트 표시

#### 완료 기준

- [ ] PII 감지 및 마스킹/차단 동작
- [ ] 입력/출력 필터 동작
- [ ] 가드레일 이벤트 로깅 완료
- [ ] 관리자 대시보드에 차트 표시

---

## 3. 테스트 절차

### 3.1 단계별 E2E 테스트 시나리오

각 단계별 테스트 스크립트는 `scripts/test-stage-*.sh`에 위치합니다.

**예시: 1단계 테스트 스크립트** (`scripts/test-stage-1.sh`)

```bash
#!/bin/bash
set -e

echo "Testing Stage 1: Open-WebUI Customization"

# 구동 테스트
docker-compose up -d webui
sleep 10

# 기본 접근 확인
curl -f http://localhost:3000 || exit 1

# UI 요소 확인 (간단한 HTML 파싱)
curl -s http://localhost:3000 | grep -q "Chat" || exit 1

echo "Stage 1 tests passed!"
```

### 3.2 통합 테스트 체크리스트

각 단계 완료 후 다음 항목 확인:

- [ ] Docker 컨테이너 정상 구동
- [ ] 핵심 API 엔드포인트 동작
- [ ] UI 접근 및 기본 동작
- [ ] 데이터베이스 연결 및 쿼리 동작
- [ ] 로그에 치명적 에러 없음

### 3.3 회귀 테스트

새로운 단계 추가 전, 이전 단계 기능 정상 동작 확인:

```bash
# 모든 단계 테스트 실행
for stage in {1..9}; do
  ./scripts/test-stage-${stage}.sh
done
```

---

## 4. CI/CD 파이프라인 (GitHub Actions)

### 4.1 워크플로우 구조

각 단계별로 별도 워크플로우 파일 생성:

```
.github/workflows/
├─ stage-1.yml
├─ stage-2.yml
├─ ...
└─ stage-9.yml
```

### 4.2 기본 워크플로우 템플릿

**예시: 2단계 워크플로우** (`.github/workflows/stage-2.yml`)

```yaml
name: Stage 2 - Chat Endpoint & Monitoring

on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'
      - 'compose/stage-2.yml'
  pull_request:
    branches:
      - main
    paths:
      - 'backend/**'
      - 'compose/stage-2.yml'
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        working-directory: ./backend
        run: |
          pip install -r requirements.txt

      - name: Run tests
        working-directory: ./backend
        run: |
          pytest tests/

      - name: Build Docker images
        run: |
          docker-compose -f compose/stage-2.yml build

      - name: Start services
        run: |
          docker-compose -f compose/stage-2.yml up -d
          sleep 30

      - name: Run E2E tests
        run: |
          ./scripts/test-stage-2.sh

      - name: Stop services
        if: always()
        run: |
          docker-compose -f compose/stage-2.yml down

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to staging
        run: |
          # 배포 스크립트 실행
          ./scripts/deploy.sh staging stage-2
```

### 4.3 Webhook 설정

GitHub 저장소 설정에서 Webhook 추가:

1. **Settings → Webhooks → Add webhook**
2. **Payload URL**: `https://your-ci-server/webhook`
3. **Content type**: `application/json`
4. **Events**: `push`, `pull_request`
5. **Active**: 체크

### 4.4 환경별 배포 전략

- **Staging**: `main` 브랜치 푸시 시 자동 배포
- **Production**: 태그 푸시 시 수동 승인 후 배포

---

## 5. 폴더 구조 (단계별 진화)

### 5.1 1단계 완료 후

```
repo/
├─ webui/
│  ├─ Dockerfile
│  ├─ overrides/
│  └─ plugins/
├─ docker-compose.yml
└─ .env.example
```

### 5.2 2단계 완료 후

```
repo/
├─ webui/
├─ backend/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ app/
├─ config/
│  └─ litellm.yaml
├─ docker-compose.yml
└─ .env.example
```

### 5.3 최종 구조 (9단계 완료 후)

```
repo/
├─ webui/
├─ backend/
├─ document-service/
├─ open-notebook/
├─ perplexica/
├─ config/
│  ├─ litellm.yaml
│  ├─ kong.yml
│  └─ guardrails/
├─ kong-admin-ui/
├─ compose/
│  ├─ stage-1.yml
│  ├─ stage-2.yml
│  └─ ...
├─ scripts/
│  ├─ setup-forks.sh
│  ├─ test-stage-*.sh
│  └─ deploy.sh
├─ .github/
│  └─ workflows/
├─ docker-compose.yml
└─ .env.example
```

---

## 6. 트러블슈팅

### 6.1 단계별 예상 이슈

#### 1단계: Open-WebUI 커스터마이즈
- **이슈**: 오버라이드 파일이 적용되지 않음
  - **해결**: Docker 볼륨 마운트 경로 확인, Open-WebUI 버전 호환성 확인

#### 2단계: Chat 엔드포인트
- **이슈**: LiteLLM 연결 실패
  - **해결**: `config/litellm.yaml` 설정 확인, 네트워크 연결 확인

#### 3단계: 에이전트 빌더
- **이슈**: iframe CORS 에러
  - **해결**: 리버스 프록시 설정, CORS 헤더 추가

#### 4단계: MCP SSE
- **이슈**: Kong 인증 실패
  - **해결**: Kong 설정 파일 확인, 키 인증 플러그인 상태 확인

#### 5단계: 데이터베이스
- **이슈**: 마이그레이션 실패
  - **해결**: SQL 스크립트 문법 확인, 권한 확인

#### 6단계: Document Intelligence
- **이슈**: OCR 처리 실패
  - **해결**: PaddleOCR 모델 다운로드 확인, 메모리 리소스 확인

#### 7단계: UI 뷰 모드
- **이슈**: 뷰 전환 시 상태 유지 안 됨
  - **해결**: 상태 관리 로직 확인, React 상태 훅 확인

#### 8단계: Perplexica + Open-Notebook 임베드
- **이슈**: iframe CORS/X-Frame-Options 에러
  - **해결**: 리버스 프록시 헤더 변환 확인, Kong response-transformer 플러그인 확인
- **이슈**: 프록시 경로 매칭 실패
  - **해결**: FastAPI 경로 패턴 확인 (`{path:path}` 사용), 프록시 서비스 로직 확인

#### 9단계: 가드레일
- **이슈**: PII 감지 성능 저하
  - **해결**: 비동기 처리 적용, 캐싱 전략 적용

---

## 7. 다음 단계 (로드맵)

1단계부터 9단계까지 완료 후:

- [ ] Langflow/Flowise ↔ LangGraph 양방향 동기화
- [ ] Kong Admin UI 마법사 (컨슈머/키 자동 발급)
- [ ] 문서지능: 표 구조/수식 OCR 강화
- [ ] 평가 파이프라인 (Golden set/A/B/Drift)
- [ ] 비용 거버넌스 (모델별 Budget/Alert)

---

## 부록

### A. 참고 자료

- [Open-WebUI GitHub](https://github.com/open-webui/open-webui)
- [Open Notebook](https://www.open-notebook.ai/)
- [Perplexica GitHub](https://github.com/ItzCrazyKns/Perplexica)
- [LiteLLM 문서](https://docs.litellm.ai/)
- [Langfuse 문서](https://langfuse.com/docs)
- [Kong Gateway 문서](https://docs.konghq.com/)

### B. 유용한 명령어

```bash
# 모든 서비스 구동
docker-compose up -d

# 특정 단계만 구동
docker-compose -f compose/stage-N.yml up -d

# 로그 확인
docker-compose logs -f [service-name]

# 데이터베이스 초기화
docker-compose down -v
docker-compose up -d mariadb
```

### C. 임시 문서 관리

개발 중 생성된 임시 문서를 정리하는 유틸리티:

#### 자동 체크 (Git Hook)

커밋 시 임시 문서가 자동으로 체크됩니다:

```bash
git add .
git commit -m "..."

# 출력 예시:
# 🧹 임시 문서 발견: 2개
#    - IMPLEMENTATION_CLARIFICATION.md
#    - TEMP_NOTES.md
#    권장: ./scripts/clean-temp-docs.sh 실행하여 정리
```

#### 수동 정리

**인터랙티브 모드** (각 파일 검증):

```bash
./scripts/clean-temp-docs.sh

# 각 파일마다:
# - 파일 정보 표시 (크기, 수정일, 미리보기)
# - 중요 키워드 체크 (CRITICAL, IMPORTANT 등)
# - 최근 수정 여부 확인 (7일 이내)
# - 선택 옵션:
#   k = 보존
#   b = 백업+삭제 (.backup/temp-docs/에 백업)
#   s = 건너뛰기
```

**자동 모드** (중요 문서는 보존, 나머지 자동 백업):

```bash
./scripts/clean-temp-docs.sh --auto
```

#### 임시 문서 패턴

다음 패턴의 파일이 자동으로 감지됩니다:

- `IMPLEMENTATION_*.md` — 구현 방법 결정 문서
- `TEMP_*.md` — 임시 메모
- `TODO_*.md` — 작업 목록
- `DRAFT_*.md` — 초안 문서
- `WIP_*.md` — 작업 중 문서
- `DECISION_*.md` — 의사결정 문서
- `ANALYSIS_*.md` — 분석 문서
- `DEBUG_*.md` — 디버깅 메모
- `*_TEMP.md`, `*_WIP.md`, `*_DRAFT.md` — 접미사 형태

#### 백업 및 복원

**백업 위치**: `.backup/temp-docs/YYYYMMDD-HHMMSS/`

**복원 방법**:

```bash
# 특정 파일 복원
mv .backup/temp-docs/20251119-143022/IMPLEMENTATION_CLARIFICATION.md ./

# 전체 복원
cp -r .backup/temp-docs/20251119-143022/* ./
```

**오래된 백업 정리** (30일 이상):

```bash
find .backup/temp-docs -type d -mtime +30 -exec rm -rf {} \;
```

#### 중요 문서 보호

다음 키워드가 있는 문서는 자동으로 보존됩니다:

- `CRITICAL`
- `IMPORTANT`
- `DO NOT DELETE`
- `KEEP THIS`
- `PRODUCTION`
- `LICENSE`

**중요 문서 표시 예시**:

```markdown
# Implementation Plan

<!-- IMPORTANT: 프로덕션 배포 전 반드시 검토 필요 -->

...
```

#### 권장 워크플로우

1. **개발 중**: 자유롭게 임시 문서 생성
2. **작업 완료 후**: `./scripts/clean-temp-docs.sh` 실행
3. **커밋 전**: 임시 문서 정리 확인
4. **주간 리뷰**: 오래된 백업 삭제

**상세 가이드**: [.cursorrules](../.cursorrules#임시-문서-관리) 참조

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-XX

