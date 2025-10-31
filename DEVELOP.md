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

### 2.2 2단계: Chat 엔드포인트 연동 및 모니터링

**목표**: FastAPI BFF 생성, LiteLLM 연동, Langfuse/Helicone 모니터링 및 관리자 화면 임베드

#### 작업 내용

1. **Backend BFF 기본 구조 생성**
   ```bash
   mkdir -p backend
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install fastapi uvicorn litellm langfuse-sdk
   ```

2. **LiteLLM 설정**
   - `config/litellm.yaml` 생성
   - 기본 모델 리스트 설정 (테스트용)

3. **관찰성 도구 설정**
   - Langfuse 컨테이너 추가
   - Helicone 컨테이너 추가

4. **관리자 대시보드 임베드**
   - Langfuse/Helicone iframe 카드 추가

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

- [ ] 채팅 스트리밍 API 정상 동작
- [ ] LiteLLM 게이트웨이 연동 완료
- [ ] Langfuse/Helicone 데이터 수집 및 표시
- [ ] 관리자 화면에 모니터링 임베드 완료

---

### 2.3 3단계: 에이전트 빌더 (Langflow + Flowise)

**목표**: Langflow와 Flowise를 임베드하고, Export → LangGraph 변환 기능 구현

#### 작업 내용

1. **Langflow/Flowise 컨테이너 설정**
   - 각각 별도 컨테이너로 실행
   - 리버스 프록시 설정

2. **Open-WebUI 에이전트 빌더 페이지 추가**
   - `/builder/langflow`, `/builder/flowise` 라우트 생성
   - iframe 임베드

3. **Export → LangGraph 변환**
   - 플로우 정의를 LangGraph JSON으로 변환
   - 버전/리비전 관리

#### 구현 작업

**파일 구조:**

```
backend/
└─ app/
   ├─ routes/
   │  └─ agents.py            # /agents/*
   └─ services/
      └─ langgraph_export.py  # 플로우 → LangGraph 변환

webui/
└─ overrides/
   └─ pages/
      ├─ BuilderLangflow.tsx  # Langflow 임베드
      └─ BuilderFlowise.tsx   # Flowise 임베드
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

  flowise:
    image: flowiseai/flowise:latest
    ports:
      - "3000:3000"
    environment:
      - FLOWISE_USERNAME=admin
      - FLOWISE_PASSWORD=admin123
```

#### 테스트 절차

1. **구동 테스트**
   ```bash
   docker-compose up -d langflow flowise
   ```

2. **빌더 접근 확인**
   - [ ] `/builder/langflow` 접근 가능
   - [ ] `/builder/flowise` 접근 가능
   - [ ] iframe 임베드 정상 동작

3. **플로우 생성 및 Export**
   - [ ] Langflow에서 간단한 플로우 생성
   - [ ] Export 버튼 클릭 시 LangGraph JSON 생성
   - [ ] 저장된 에이전트 정의 확인

#### 완료 기준

- [ ] Langflow/Flowise 임베드 접근 가능
- [ ] 플로우 생성 및 저장 기능 동작
- [ ] Export → LangGraph 변환 완료

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

### 2.8 8단계: Open Notebook + Perplexica 통합

**목표**: Open Notebook과 Perplexica를 통합하고, DB 통합 시작 (공통 사용자/워크스페이스)

#### 작업 내용

1. **Open Notebook 포크 및 설정**
   - 포크 완료 (1단계에서 수행)
   - Docker 설정 및 LiteLLM 연동

2. **Perplexica 포크 및 설정**
   - 포크 완료 (1단계에서 수행)
   - Docker 설정 및 LiteLLM 연동

3. **SSO 전파**
   - Open-WebUI에서 인증 후 JWT 생성
   - 하위 포털에 JWT 전파

4. **DB 통합 시작**
   - 공통 사용자/워크스페이스 테이블 참조
   - 각 포털별 별도 테이블 유지

#### 구현 작업

**파일 구조:**

```
open-notebook/
├─ Dockerfile
└─ .env.example

perplexica/
├─ Dockerfile
└─ .env.example

backend/
└─ app/
   └─ services/
      └─ sso_jwt.py           # JWT 생성/검증
```

#### docker-compose 설정

```yaml
services:
  open-notebook:
    build: ./open-notebook
    ports:
      - "3100:3000"
    env_file: .env
    environment:
      - API_BASE_URL=http://litellm:4000
      - SSO_JWT_SECRET=${JWT_SECRET}
    depends_on:
      - litellm

  perplexica:
    build: ./perplexica
    ports:
      - "3210:3000"
    env_file: .env
    environment:
      - API_BASE_URL=http://litellm:4000
      - SSO_JWT_SECRET=${JWT_SECRET}
    depends_on:
      - litellm
```

#### 테스트 절차

1. **각 포털 접근 확인**
   - [ ] Open Notebook (`http://localhost:3100`) 접근
   - [ ] Perplexica (`http://localhost:3210`) 접근

2. **SSO 전파 확인**
   - [ ] Open-WebUI 로그인 → JWT 생성
   - [ ] Open Notebook/Perplexica에서 JWT 검증 성공

3. **데이터 공유 확인**
   - [ ] 공통 사용자 정보 조회
   - [ ] 워크스페이스 정보 공유

#### 완료 기준

- [ ] Open Notebook 및 Perplexica 통합 완료
- [ ] SSO JWT 전파 동작
- [ ] 공통 사용자/워크스페이스 데이터 공유 시작

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

#### 8단계: 포털 통합
- **이슈**: SSO JWT 검증 실패
  - **해결**: JWT 시크릿 키 일치 확인, 만료 시간 확인

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

---

**문서 버전**: 1.0  
**최종 업데이트**: 2025-01-XX

