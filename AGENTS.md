# AGENTS.md — AI 에이전트 가이드 (Claude Code)

> **목적**: AI 에이전트(Claude Code 등)가 Agent Portal 프로젝트를 이해하고 작업할 수 있도록 제공하는 핵심 가이드 문서  
> **대상**: AI 코딩 어시스턴트, 자동화 워크플로우, 신규 개발자 온보딩  
> **참고**: [Claude Code 사용 가이드](https://news.hada.io/topic?id=24099)

---

## 0. 철학 및 원칙

### 0.1 "Shoot and Forget" — 결과 중심 위임

**핵심 원칙**: AI 에이전트에게 **충분한 컨텍스트와 명확한 목표**를 제공한 후, 중간 과정보다는 **최종 PR의 품질**로 평가합니다.

- 에이전트는 **작업 완료 후 PR 생성**까지 자율적으로 수행
- 인간은 **PR 검토 및 승인** 단계에서만 개입
- 출력 스타일이나 UI가 아닌 **최종 결과물**로 평가

### 0.2 CLAUDE.md는 "헌법"

프로젝트 루트의 **`CLAUDE.md`** 파일이 에이전트의 행동 규칙과 가드레일을 정의합니다. 이 파일이 없으면 생성하거나, 이 문서를 참고하여 작성하세요.

**CLAUDE.md 작성 원칙**:
- **간결하게 유지**: 13KB 이하 권장 (엔터프라이즈 모노레포 기준)
- **가드레일로 시작, 매뉴얼이 아님**: 에이전트가 잘못하는 부분 기반으로 소규모 문서화 시작
- **@-파일 문서화 금지**: 다른 곳의 광범위한 문서를 `@`-언급하면 매 실행마다 전체 파일이 컨텍스트 윈도우에 임베딩되어 비대화
- **"절대 안 됨"만 말하지 말 것**: 항상 대안 제시
- **실패 기반 학습**: 실제 에이전트 실패 사례를 바탕으로 가드레일 추가

---

## 1. 프로젝트 구조 및 아키텍처

### 전체 디렉토리 구조

```
agent-portal/
├── backend/                    # FastAPI BFF (Backend for Frontend)
│   ├── app/
│   │   ├── routes/            # API 엔드포인트
│   │   │   ├── chat.py        # Chat API (Stage 2 ✅)
│   │   │   ├── observability.py  # Observability API (Stage 2 ✅)
│   │   │   ├── embed.py       # Embed 프록시
│   │   │   └── kong_admin.py # Kong Admin 프록시
│   │   ├── services/          # 비즈니스 로직 레이어
│   │   │   ├── litellm_service.py  # LiteLLM 게이트웨이 (Stage 2 ✅)
│   │   │   └── langfuse_service.py # Langfuse 관측성 (Stage 2 ✅)
│   │   ├── middleware/        # 미들웨어 (RBAC 등)
│   │   ├── config.py          # 설정 관리
│   │   └── main.py            # FastAPI 앱 진입점
│   ├── requirements.txt       # Python 의존성
│   └── Dockerfile
│
├── webui/                      # Open-WebUI 포크 (AGPL)
│   └── src/routes/(app)/admin/
│       └── monitoring/        # Monitoring 대시보드 (Stage 2 ✅)
│
├── config/                     # 설정 파일
│   ├── litellm.yaml           # LiteLLM 게이트웨이 설정
│   └── kong.yml               # Kong Gateway 설정
│
├── scripts/                    # 유틸리티 스크립트
│   ├── init-konga-schema.sql  # Konga DB 스키마 (Stage 1 ✅)
│   └── *.sh                   # 배포/테스트 스크립트
│
├── docker-compose.yml          # 전체 서비스 오케스트레이션
│
└── docs/                      # 문서
    ├── README.md              # 프로젝트 개요
    ├── DEVELOP.md             # 개발 가이드
    ├── PROGRESS.md            # 진행 상황
    └── AGENTS.md              # 이 문서
```

### 핵심 서비스 및 상태

| 서비스 | 포트 | 역할 | 상태 |
|--------|------|------|------|
| **Backend BFF** | 8000 | FastAPI 백엔드, API 게이트웨이 | ✅ 실행 중 |
| **Kong** | 8002/8443 | API Gateway, 보안/라우팅 | ✅ 실행 중 |
| **Konga** | 1337 | Kong Admin UI | ✅ 실행 중 |
| **LiteLLM** | 4000 | LLM 게이트웨이 | ⚠️ 설정 필요 |
| **Langfuse** | 3000 | LLM 관측성 | ⚠️ 설정 필요 |
| **Helicone** | 8787 | LLM 프록시/비용 추적 | ⚠️ 설정 필요 |

### 현재 진행 상황

**Stage 1**: ✅ 완료
- Kong Gateway 설정 및 실행
- Konga 스키마 생성 및 실행

**Stage 2**: ✅ 코드 완료 (환경 설정 필요)
- Chat API (`/chat/stream`, `/chat/completions`)
- Observability API (`/observability/health`, `/observability/usage`, `/observability/models`)
- Open-WebUI Monitoring 페이지
- Embed 프록시

**상세 진행 상황**: [PROGRESS.md](./PROGRESS.md) 참조

---

## 2. 코딩 표준 및 패턴

### Python (Backend)

**스타일 가이드**:
- PEP 8 준수
- Type hints 필수 (`from typing import ...`)
- Docstring 사용 (Google 스타일)

**서비스 레이어 패턴**:
- 서비스는 `app/services/`에 위치
- Singleton 패턴 사용 (모듈 레벨 인스턴스)
- 비동기 메서드 사용 (`async def`)
- 외부 호출 시 `httpx.AsyncClient` 사용, 타임아웃 설정 (기본 30초)

**예시**:
```python
# app/services/example_service.py
from typing import Optional, Dict, Any
import httpx

class ExampleService:
    def __init__(self):
        self.base_url = "http://example-service:8080"
    
    async def get_data(self, id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/data/{id}")
            response.raise_for_status()
            return response.json()

# Singleton
example_service = ExampleService()
```

### Frontend (Svelte/TypeScript)

**컴포넌트 구조**:
- `/admin/monitoring/` 같은 경로 구조 준수
- `+page.svelte` 파일명 사용 (SvelteKit 규칙)
- TypeScript 타입 정의 필수

---

## 3. 주요 컴포넌트별 작업 가이드

### 3.1 Backend API 엔드포인트 추가

**절차**:
1. `backend/app/routes/`에 새 라우터 파일 생성
2. `APIRouter` 인스턴스 생성
3. 엔드포인트 함수 구현
4. `backend/app/main.py`에 라우터 등록

**예시**:
```python
# backend/app/routes/new_feature.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/new-feature", tags=["new-feature"])

class RequestModel(BaseModel):
    field: str

@router.post("/")
async def new_endpoint(request: RequestModel):
    return {"result": "success"}
```

```python
# backend/app/main.py에 추가
from app.routes import new_feature
app.include_router(new_feature.router)
```

### 3.2 Observability 통합

**Langfuse 통합**:
- `langfuse_service.create_trace()` 사용
- 선택적 import (모듈 미설치 시 graceful degradation)

**예시**:
```python
from app.services.langfuse_service import langfuse_service

trace = langfuse_service.create_trace(name="operation_name")
span = trace.span(name="sub_operation")
# ... 작업 수행 ...
span.end(output={"result": "data"})
trace.end()
```

---

## 4. 자주 발생하는 문제 및 해결 (가드레일)

> **중요**: 이 섹션은 실제 실패 사례를 기반으로 작성되었습니다. 새로운 문제 발생 시 여기에 추가하세요.  
> **가드레일 원칙**: "절대 안 됨"만 말하지 말고 항상 대안을 제시하세요.

### 문제 1: 컨테이너 내부 파일과 로컬 파일 불일치

**증상**: 로컬 파일 수정이 컨테이너에 반영되지 않음

**원인**: Docker 빌드 캐시 또는 볼륨 마운트 설정 문제

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

### 문제 4: Konga 스키마 초기화 실패

**증상**: Konga 시작 시 데이터베이스 오류

**해결** (대안 제시):
- **방법 1**: 수동 스키마 생성 (권장)
  ```bash
  docker-compose exec konga-db psql -U konga -d konga < scripts/init-konga-schema.sql
  ```
- **방법 2**: Docker 초기화 스크립트 활용 (docker-entrypoint-initdb.d)
- **방법 3**: Konga 환경변수 설정 (`MIGRATE=safe`, `KONGA_SEED=false`)

---

## 5. 작업 체크리스트

### 새 API 엔드포인트 추가 시
- [ ] 라우터 파일 생성 (`backend/app/routes/`)
- [ ] Pydantic 모델 정의 (요청/응답)
- [ ] 엔드포인트 함수 구현
- [ ] `main.py`에 라우터 등록
- [ ] RBAC 미들웨어 적용 (필요 시)
- [ ] Observability 통합 (Langfuse 트레이싱)
- [ ] 에러 핸들링
- [ ] OpenAPI 문서 확인 (`/docs`)

### 새 서비스 추가 시
- [ ] 서비스 파일 생성 (`backend/app/services/`)
- [ ] 클래스 정의 및 초기화
- [ ] 비동기 메서드 구현
- [ ] 타임아웃 설정
- [ ] 에러 핸들링
- [ ] Singleton 인스턴스 생성

---

## 6. Claude Code 고급 기능 활용

### 6.1 컨텍스트 관리

**슬래시 명령어**:
- `/clear`: 컨텍스트 초기화
- `/catchup`: 변경된 파일 다시 읽기
- `/compact`: 컨텍스트 압축 (주의: 지연 가능)

**권장 사용법**:
```bash
# 컨텍스트 초기화 및 재시작
/clear
/catchup
```

### 6.2 서브에이전트 활용

복잡한 작업은 서브에이전트로 분할:
- 각 서브에이전트는 독립적인 작업 수행
- 마스터 에이전트가 결과 통합

### 6.3 Hooks 활용

**Pre-commit Hook**:
- 린트/포맷 자동 실행
- 테스트 실패 시 커밋 차단

**Pre-push Hook**:
- 유닛 테스트 통과 확인

---

## 7. 주요 원칙

1. **비동기 우선**: 모든 I/O 작업은 `async/await` 사용
2. **에러 핸들링**: 모든 외부 호출은 try/except로 감싸기
3. **타입 안전성**: Type hints 필수
4. **관측성**: 중요한 작업은 Langfuse로 추적
5. **보안**: 모든 엔드포인트는 RBAC 적용 (현재 미완료, TODO)

---

## 8. 관련 문서

- [README.md](./README.md) - 프로젝트 개요 및 시작 가이드
- [DEVELOP.md](./DEVELOP.md) - 개발 가이드 및 단계별 계획
- [PROGRESS.md](./PROGRESS.md) - 현재 진행 상황
- [Claude Code 사용 가이드](https://news.hada.io/topic?id=24099) - 참고 자료

---

## 9. 단계별 완료 체크리스트

### Stage 1: 인프라 및 기본 설정
- [x] Kong Gateway 설정 및 실행
- [x] Konga 스키마 생성 및 실행
- [x] Backend BFF 기본 구조
- [x] Docker Compose 서비스 정의
- [x] Embed 프록시 라우트 구현

### Stage 2: Chat 및 Observability API
- [x] Chat API 엔드포인트 구현 (`/chat/stream`, `/chat/completions`)
- [x] Observability API 엔드포인트 구현 (`/observability/*`)
- [x] LiteLLM 서비스 레이어 구현
- [x] Langfuse 서비스 레이어 구현
- [x] Open-WebUI Monitoring 페이지 추가
- [x] 라우터 등록 완료
- [ ] LiteLLM 서비스 실행 및 설정 (환경 설정 필요)
- [ ] Langfuse 서비스 실행 및 연동 (환경 설정 필요)
- [ ] 프론트엔드-백엔드 데이터 연동 (BFF API 호출)

### Stage 3: 문서 인텔리전스 및 통합
- [ ] 문서 인텔리전스 파이프라인
- [ ] LangGraph 서버 연동
- [ ] Open Notebook 통합
- [ ] Perplexica 통합

**상세 진행 상황**: [PROGRESS.md](./PROGRESS.md) 참조

---

**마지막 업데이트**: 2025-11-04  
**버전**: 2.0 (Claude Code 가이드라인 반영)  
**참고**: [Claude Code 사용 가이드](https://news.hada.io/topic?id=24099)
