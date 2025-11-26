# CLAUDE.md — Agent Portal 가이드

> **목적**: AI 에이전트(Claude Code, Cursor AI)가 Agent Portal 프로젝트를 이해하고 작업할 수 있도록 제공하는 핵심 가이드  

---

## 핵심 원칙

### IMPORTANT: "Shoot and Forget" — 결과 중심 위임
- 에이전트에게 **충분한 컨텍스트와 명확한 목표** 제공
- 중간 과정보다는 **최종 PR의 품질**로 평가
- 출력 스타일이나 UI가 아닌 **최종 결과물**로 평가
- **작업 완료 후 PR 생성까지 자율적으로 수행** (인간은 PR 검토 단계에서만 개입)

### ALWAYS: Skills 시스템 활용
- **UI 구조 매핑**: `webui/.skills/ui-structure.json`
- **자연어 검색 인덱스**: `webui/.skills/ui-search-index.json`
- 자연어 요청을 정확한 코드 위치로 매핑하는 데 사용
- **UI 관련 작업 시 반드시 Skills 파일을 먼저 확인** (직접 파일 검색 전에)

---

## UI 구조 및 Skills 시스템

### Skills 파일 위치
- `webui/.skills/ui-structure.json`: 전체 UI 구조 매핑 (라우트, 컴포넌트, API)
- `webui/.skills/ui-search-index.json`: 강화된 자연어 검색 인덱스 (키워드, 패턴, 스타일, 레이아웃 기반)
- `webui/.skills/ui-patterns.json`: 스타일 패턴 분석 (버튼, 탭, 카드, 모달 패턴)
- `webui/.skills/ui-layouts.json`: 레이아웃 계층 구조 및 페이지-레이아웃 매핑
- `webui/.skills/ui-navigation.json`: 네비게이션 구조 (사이드바, 탭 네비게이션)
- `webui/.skills/ui-styles.json`: 글로벌 스타일 정보 (Tailwind 설정, 테마 시스템, 반응형 패턴)
- `webui/.skills/ui-class-mapping-guide.json`: 클래스 매핑 가이드 (색상 변경, 패턴 매핑, 리팩토링 예시)

### 자연어 요청 처리 방법

**사용자 요청 예시**: "monitoring 페이지의 탭 버튼 스타일 변경"

**처리 절차**:
1. **키워드 추출**: "monitoring", "탭", "버튼", "스타일"
2. **검색 인덱스 조회**: `ui-search-index.json`에서 "monitoring" 키워드로 검색
3. **매핑된 경로 확인**: `routes/(app)/admin/monitoring/+page.svelte` 찾기
4. **구조 파일 확인**: `ui-structure.json`에서 해당 라우트의 상세 정보 확인
5. **정확한 위치 파악**: 라인 72-101 (탭 버튼 정의 부분)
6. **수정 방법 제안**: `activeTab` 상태와 조건부 클래스 수정

**Skills 시스템 사용 예시**:
```javascript
// 1. 검색 인덱스에서 키워드로 경로 찾기
const searchIndex = require('./webui/.skills/ui-search-index.json');
const monitoringRoutes = searchIndex.keywordIndex['monitoring'].routes;

// 2. 구조 파일에서 상세 정보 가져오기
const structure = require('./webui/.skills/ui-structure.json');
const route = structure.routes.find(r => r.path.includes('monitoring'));
// route.components, route.apis, route.keywords 등 활용
```

### UI 구조 변경 시 업데이트
- 자동 업데이트: `scripts/update-ui-skills.sh` 실행 (모든 분석 스크립트 실행)
- 개별 분석 스크립트:
  - `scripts/analyze-ui-structure.js`: 기본 구조 분석
  - `scripts/analyze-ui-patterns.js`: 스타일 패턴 분석
  - `scripts/analyze-layout-hierarchy.js`: 레이아웃 계층 분석
  - `scripts/analyze-navigation-structure.js`: 네비게이션 구조 분석
  - `scripts/analyze-global-styles.js`: 글로벌 스타일 분석
  - `scripts/enhance-search-index.js`: 검색 인덱스 강화
- Git hook으로 통합 가능 (선택사항)

---

## 프로젝트 구조

### 핵심 디렉토리
```
agent-portal/
├── backend/          # FastAPI BFF (Backend for Frontend)
├── webui/            # Open-WebUI 포크 (SvelteKit)
│   ├── src/
│   │   ├── routes/   # 페이지 라우트
│   │   ├── lib/
│   │   │   ├── components/  # Svelte 컴포넌트
│   │   │   └── apis/       # API 클라이언트
│   └── .skills/      # Skills 시스템 파일
├── autogen-studio/   # AutoGen Studio UI (임베드)
├── autogen-api/      # AutoGen Studio 백엔드
├── perplexica/       # Perplexica (iframe 임베드)
├── open-notebook/    # Open Notebook (iframe 임베드)
├── config/           # 설정 파일
└── scripts/          # 유틸리티 스크립트
```

### 주요 라우트 구조
- `(app)/` 경로 그룹: 메인 앱 라우트
- `admin/` 경로: 관리자 전용 페이지
- `workspace/` 경로: 작업 공간 페이지
- `c/[id]/` 경로: 채팅 상세 페이지

### 컴포넌트 구조
- `layout/`: 레이아웃 컴포넌트 (Sidebar, Navbar 등)
- `chat/`: 채팅 관련 컴포넌트
- `admin/`: 관리자 전용 컴포넌트
- `common/`: 공통 컴포넌트

---

## 백엔드 아키텍처

### 이중 백엔드 구조 (CRITICAL)

Agent Portal은 **두 개의 독립적인 백엔드**를 운영합니다:

1. **webui/backend**: Open-WebUI 내장 백엔드
   - 역할: Chat, OpenAI/Ollama 프록시, RAG, 벡터 DB
   - 기술: FastAPI + SQLAlchemy + ChromaDB
   - 포트: 8080 (컨테이너 내부), 3000 (외부)
   - PYTHONPATH: `/app/backend` (반드시 설정 필요)

2. **backend/**: FastAPI BFF (Backend for Frontend)
   - 역할: News API, Observability, Kong/Embed 프록시
   - 기술: FastAPI + HTTPX
   - 포트: 8000
   - PYTHONPATH: 자동 설정 (WORKDIR=/app)

### PYTHONPATH 설정 규칙 (ALWAYS)

**webui/backend 개발 시 반드시 확인**:
- Dockerfile: `ENV PYTHONPATH=/app/backend:$PYTHONPATH`
- 스크립트: `PYTHONPATH=. uvicorn open_webui.main:app`
- Docker Compose: 볼륨 마운트 시에도 ENV 유지

**실패 사례**: 
- `ModuleNotFoundError: No module named 'open_webui'`
- 원인: PYTHONPATH 미설정
- 해결: `webui/dev-start.sh` line 27, `webui/Dockerfile.dev` line 29

---

## 코딩 표준

### Python (Backend)
- PEP 8 준수
- Type hints 필수
- 비동기 메서드 사용 (`async def`)
- 외부 호출 시 `httpx.AsyncClient` 사용, 타임아웃 설정 (기본 30초)

### Frontend (Svelte/TypeScript)
- `/admin/monitoring/` 같은 경로 구조 준수
- `+page.svelte` 파일명 사용 (SvelteKit 규칙)
- TypeScript 타입 정의 필수

---

## 주요 작업 가이드

### Backend API 엔드포인트 추가
1. `backend/app/routes/`에 새 라우터 파일 생성
2. `APIRouter` 인스턴스 생성
3. 엔드포인트 함수 구현
4. `backend/app/main.py`에 라우터 등록

### UI 컴포넌트 수정
**ALWAYS**: Skills 파일을 먼저 확인하고, 직접 파일 검색은 마지막 수단으로 사용

1. **자연어 요청 분석**: 사용자 요청에서 키워드 추출
2. **Skills 시스템 조회**: `ui-search-index.json`에서 관련 경로 찾기
3. **구조 파일 확인**: `ui-structure.json`에서 상세 정보 확인
4. **패턴 확인**: `ui-patterns.json`에서 공통 스타일 패턴 확인
5. **레이아웃 확인**: `ui-layouts.json`에서 레이아웃 영향 범위 확인
6. **정확한 위치 파악**: 컴포넌트 경로와 의존성 확인
7. **수정 수행**: 변경사항 적용

### 대규모 UI 개편 작업
**예시**: "전체 탭 스타일을 파란색에서 초록색으로 변경"
1. **색상 사용 위치 확인**: `ui-patterns.json`의 `colorFileMapping.border-blue-500`에서 사용 파일 목록 확인
2. **라우트 페이지 포함 확인**: `colorFileMapping.border-blue-500.routes`와 `components` 모두 확인
3. **매핑 가이드 참조**: `ui-class-mapping-guide.json`의 `colorMappings.blue` 예시 참조
4. **스타일 매핑 적용**:
   - `border-blue-500` → `border-green-500`
   - `text-blue-600` → `text-green-600`
   - `text-blue-400` → `text-green-400` (dark mode)
5. **일괄 수정**: `colorFileMapping`에 나열된 모든 파일에 적용

**예시**: "사이드바 메뉴를 2단계에서 3단계로 확장"
1. **현재 구조 확인**: `ui-navigation.json`의 `sidebar` 구조 확인
2. **메뉴 컴포넌트 위치**: `ui-structure.json`에서 Sidebar.svelte 경로 확인
3. **스타일 패턴**: `ui-patterns.json`에서 메뉴 스타일 패턴 확인
4. **수정 수행**: 메뉴 구조 및 스타일 수정

### Observability 통합
- Langfuse: `langfuse_service.create_trace()` 사용
- 선택적 import (모듈 미설치 시 graceful degradation)

---

## 자주 발생하는 문제 및 해결 (가드레일)

> **가드레일 원칙**: 실제 에이전트 실패 사례를 바탕으로 작성. "절대 안 됨"만 말하지 말고 항상 대안을 제시.

### 문제 1: 컨테이너 내부 파일과 로컬 파일 불일치
**증상**: 로컬 파일 수정이 컨테이너에 반영되지 않음

**해결** (대안 제시):
- **방법 1**: 캐시 없이 재빌드
  ```bash
  docker-compose build --no-cache backend
  docker-compose restart backend
  ```
- **방법 2**: 볼륨 마운트 확인 (docker-compose.yml)
  ```yaml
  volumes:
    - ./backend/app:/app/app:ro  # 읽기 전용 마운트
  ```
- **방법 3**: 개발 환경에서는 볼륨 마운트 사용, 프로덕션에서는 이미지 빌드

### 문제 2: 라우터가 등록되지 않음
**증상**: `main.py`에 라우터를 추가했으나 API에 나타나지 않음

**해결** (대안 제시):
- **방법 1**: `main.py`에서 import 및 `app.include_router()` 호출 확인
- **방법 2**: 컨테이너 내부 파일 확인
  ```bash
  docker-compose exec backend cat /app/app/main.py
  ```
- **방법 3**: 컨테이너 재시작 또는 재빌드
  ```bash
  docker-compose restart backend
  # 또는
  docker-compose build --no-cache backend && docker-compose up -d backend
  ```

### 문제 3: Import 오류 (선택적 의존성)
**증상**: `ModuleNotFoundError: No module named 'langfuse'`

**해결** (대안 제시):
- **권장 방법**: 선택적 import 패턴 사용
  ```python
  try:
      from langfuse import Langfuse
      LANGFUSE_AVAILABLE = True
  except ImportError:
      LANGFUSE_AVAILABLE = False
      Langfuse = None
  ```
- **대안**: `requirements.txt`에 의존성 추가 후 재빌드
  ```bash
  # requirements.txt에 langfuse 추가
  pip install langfuse
  docker-compose build --no-cache backend
  ```

---

## 주요 원칙

1. **비동기 우선**: 모든 I/O 작업은 `async/await` 사용
2. **에러 핸들링**: 모든 외부 호출은 try/except로 감싸기
3. **타입 안전성**: Type hints 필수
4. **관측성**: 중요한 작업은 Langfuse로 추적
5. **보안**: 모든 엔드포인트는 RBAC 적용 (현재 미완료, TODO)

---

## 문서 관리 원칙

### 문서 중복 방지 (CRITICAL)

**신규 문서 생성 전 반드시 확인**:
1. `.cursor/learnings/` - 학습 내용 기록
2. `docs/` - 상세 가이드 문서
3. `.cursor/rules/` - 개발 규칙
4. 루트 `*.md` - 프로젝트 전체 문서

**검색 방법**:
```bash
# 전체 문서 검색
find . -name "*.md" -o -name "*.mdc" | xargs grep -l "키워드"

# 특정 디렉토리만
grep -r "키워드" .cursor/learnings/
```

**통합 우선 원칙**:
- 기존 문서에 섹션 추가 > 신규 문서 생성
- 관련 내용은 한 곳에 집중
- 임시 문서는 작업 완료 후 정리 또는 통합

**문서 카테고리**:
- 학습 내용: `.cursor/learnings/*.md`
- 개발 규칙: `.cursor/rules/*.mdc`
- 가이드: `docs/*.md`
- 프로젝트 문서: `AGENTS.md`, `CLAUDE.md`, `README.md` 등

---

## 참고 문서

> **NOTE**: 아래 문서들은 필요 시에만 참조. 이 `CLAUDE.md`가 주요 가이드이며, 다른 문서를 읽어야 하는 경우는 복잡한 사용법이나 에러 발생 시 고급 문제 해결을 위한 경우에만 해당.

- `docs/AGENTS.md` - 상세 에이전트 가이드 (복잡한 워크플로우나 에이전트 실패 시 참조)
- `README.md` - 프로젝트 개요
- `docs/DEVELOP.md` - 개발 가이드 (초기 설정이나 환경 구성 시 참조)
- `docs/PROGRESS.md` - 진행 상황 (현재 상태 확인 시 참조)

---

**마지막 업데이트**: 2025-11-06  
**버전**: 1.0

