# AGENTS.md — AI 에이전트 가이드 (Claude Code)

> **목적**: AI 에이전트(Claude Code 등)가 Agent Portal 프로젝트를 이해하고 작업할 수 있도록 제공하는 핵심 가이드 문서  
> **대상**: AI 코딩 어시스턴트, 자동화 워크플로우, 신규 개발자 온보딩  
> **참고**: [Claude Code 사용 가이드](https://news.hada.io/topic?id=24099)

---

## 0. 철학 및 원칙

### 0.0 테스트 확인 후 완료 판정 (CRITICAL)

**핵심 원칙**: 코드 작성은 시작일 뿐, **실제 테스트 수행 후에만 완료**입니다.

**작업 완료 기준**:
- ❌ 코드 작성만으로는 완료 아님
- ❌ "재시작했습니다"만으로는 완료 아님
- ✅ **실제 테스트 수행 + 결과 확인** 후 완료

**테스트 절차** (반드시 순서대로):
```bash
# 1. Backend API 테스트
curl -s "http://localhost:8000/api/endpoint" | python3 -m json.tool

# 2. 에러 확인
# - 200 OK: 정상
# - 500/503/504: 에러 로그 확인 필요
# - Connection refused: 서비스 미실행

# 3. Frontend 테스트
# - 브라우저 접속: http://localhost:3001
# - 브라우저 콘솔 에러 확인 (F12)
# - 실제 화면 동작 확인

# 4. 결과 판정
# ✅ 모든 테스트 통과 → TODO completed
# ❌ 에러 발생 → 수정 후 1번부터 재시도
```

**금지 사항**:
- ❌ "구현 완료했습니다" → 테스트 없이 선언
- ❌ "서버 재시작 완료" → API 응답 확인 없음
- ❌ "TODO 완료!" → 브라우저 확인 누락
- ❌ 추측 기반 완료 판정 ("아마 동작할 것")

**예시 (올바른 완료)**:
```
1. Monitoring Adapter 수정 완료
2. Backend 재시작 완료
3. ✅ 테스트 수행:
   $ curl http://localhost:8000/api/monitoring/metrics?...
   {"trace_count": 10, "total_cost": 1.23}
4. ✅ 브라우저 확인: 차트 정상 표시
5. ✅ TODO completed
```

**예시 (잘못된 완료)**:
```
1. Monitoring Adapter 수정 완료
2. Backend 재시작 완료
3. ❌ "구현 완료했습니다!" → 테스트 누락
```

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
│   │   │   ├── monitoring.py  # Monitoring API (ClickHouse 조회)
│   │   │   ├── projects.py    # 프로젝트 관리 API
│   │   │   ├── embed.py       # Embed 프록시
│   │   │   ├── kong_admin.py # Kong Admin 프록시
│   │   │   └── proxy.py       # 리버스 프록시 (Langflow/Flowise/AutoGen)
│   │   ├── services/          # 비즈니스 로직 레이어
│   │   │   ├── litellm_service.py  # LiteLLM 게이트웨이 (Stage 2 ✅)
│   │   │   ├── langfuse_service.py # Langfuse 관측성 (Stage 2 ✅)
│   │   │   ├── monitoring_adapter.py # ClickHouse 모니터링 어댑터
│   │   │   └── project_service.py # 프로젝트 관리 서비스
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
├── autogen-studio/             # AutoGen Studio UI (임베드)
│   └── Dockerfile
│
├── autogen-api/                # AutoGen Studio 백엔드(프록시/어댑터)
│   └── Dockerfile
│
├── perplexica/                 # Perplexica (iframe 임베드)
│   └── Dockerfile
│
├── open-notebook/              # Open Notebook (iframe 임베드)
│   └── Dockerfile
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

### 핵심 서비스 및 상태 (2025-11-26 업데이트)

| 서비스 | 포트 | 역할 | 상태 |
|--------|------|------|------|
| **Backend BFF** | 8000 | FastAPI 백엔드, API 게이트웨이 | ✅ 실행 중 |
| **Open-WebUI** | 3001 | Portal Shell (UI) | ✅ 실행 중 |
| **Kong** | 8002/8443 | API Gateway, 보안/라우팅 | ✅ 실행 중 |
| **Konga** | 1337 | Kong Admin UI | ✅ 실행 중 |
| **LiteLLM** | 4000 | LLM 게이트웨이 + PostgreSQL | ✅ 실행 중 |
| **Monitoring OTEL Collector** | 4317/4318 | OpenTelemetry traces 수집 | ✅ 실행 중 |
| **Monitoring ClickHouse** | 8124/9002 | Traces 저장소 | ✅ 실행 중 |
| **Langfuse** | 3003 | LLM 품질 관리 (선택적) | ⚠️ 선택적 |
| **Langflow** | 7861 | 노코드 에이전트 빌더 | ✅ 실행 중 |
| **Flowise** | 3002 | 노코드 에이전트 빌더 | ✅ 실행 중 |
| **AutoGen Studio** | 5050 | 대화형 워크플로 UI | ✅ 실행 중 |
| **AutoGen API** | 5051 | Studio 백엔드 | ⚠️ 의존성 오류 |
| **Perplexica** | 5173 | 검색 포털(iframe 임베드) | ❌ 미구현 |
| **Open-Notebook** | 3030 | AI 노트북(iframe 임베드) | ❌ 미구현 |

> **참고**: AgentOps Self-Hosted 서비스는 제거되었습니다. 모니터링은 ClickHouse + OTEL Collector 기반의 자체 구현으로 대체되었습니다.

### 현재 진행 상황 (2025-11-26 업데이트)

**Stage 1**: ✅ 완료
- Kong Gateway 설정 및 실행
- Konga 스키마 생성 및 실행

**Stage 2**: ✅ 완료 (95%)
- ✅ Chat API (`/chat/stream`, `/chat/completions`)
- ✅ Observability API (`/observability/health`, `/observability/usage`, `/observability/models`)
- ✅ Open-WebUI Monitoring 페이지 (4개 탭: Overview/Analytics/Traces/Replay)
- ✅ LiteLLM + PostgreSQL 통합
- ✅ LiteLLM → OTEL Collector → ClickHouse 파이프라인
- ✅ Backend BFF ClickHouse 직접 조회
- ✅ Guardrail 모니터링 (Agent Flow Graph + Stats)
- ⚠️ Langfuse 선택적 (품질 관리용)

**Stage 3**: 🚧 진행 중 (40%)
- ✅ 에이전트 빌더 iframe 임베딩 (Langflow + Flowise + AutoGen Studio)
- ✅ 리버스 프록시 구현
- 🚧 Langflow → LangGraph 변환기 (미구현)
- 🚧 에이전트 버전/리비전 관리 시스템 (미구현)

**Stage 8**: ❌ 미시작
- Perplexica + Open-Notebook 임베드 (iframe, 리버스 프록시)

**상세 진행 상황**: [docs/CURRENT_STATUS.md](./docs/CURRENT_STATUS.md) 참조

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

**Monitoring 통합** (LLM 호출 모니터링):
- LiteLLM → OTEL Collector → ClickHouse 파이프라인 활용
- `monitoring_adapter.get_traces()` 사용
- 비용 계산 및 세션 리플레이 제공

**예시**:
```python
from app.services.monitoring_adapter import monitoring_adapter

# 트레이스 조회
traces = await monitoring_adapter.get_traces(
    project_id="project-123",
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now()
)

# 메트릭 조회
metrics = await monitoring_adapter.get_metrics(
    project_id="project-123",
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now()
)
    
# 결과 사용
print(f"Total traces: {len(traces)}")
print(f"Total cost: ${metrics['total_cost']:.4f}")
```

**Langfuse vs Monitoring**:
- **Langfuse**: LLM 체인 추적, 프롬프트 비교, 세션 분석 (선택적)
- **Monitoring**: ClickHouse 기반 LLM 호출 모니터링, 비용 추적, 세션 리플레이
- **함께 사용**: 상호 보완적 (Langfuse는 품질 관리, Monitoring은 비용/성능 추적)

### 3.2.1 Agent Flow Graph 및 Guardrail 모니터링

**Agent Flow Graph**:
실제 LLM/Agent 호출 흐름을 시각화합니다:
```
[Client Request] → [Input Guardrail] → [LiteLLM Proxy] → [LLM Provider] → [Output Guardrail]
                                              ↓
                                       [Agent Builder]
                                              ↓
                                         [MCP Tools]
```

각 단계별 정보:
- `call_count`: 호출 횟수
- `avg_latency_ms`: 평균 레이턴시 (밀리초)
- `total_tokens`: 총 토큰 사용량
- `total_cost`: 총 비용
- `error_count`: 에러/차단 횟수
- `guardrail_applied`: 가드레일 적용 횟수

**가드레일 유형**:
| 유형 | 설명 | 감지 방법 |
|---|---|---|
| Input Guardrail | PII 감지, 프롬프트 인젝션 방지 | `proxy_pre_call` 스팬 |
| Output Guardrail | 유해 콘텐츠 필터링, 형식 검증 | `batch_write_to_db` 스팬 |
| Cost Guardrail | 비용 제한 초과 | 토큰 사용량 모니터링 |
| Rate Limit | 요청 빈도 제한 | 요청 횟수 모니터링 |

**Guardrail Stats API 사용법**:
```python
from app.services.agentops_adapter import agentops_adapter

# 가드레일 통계 조회
guardrail_stats = await agentops_adapter.get_guardrail_stats(
    project_id="project-uuid",
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now()
)

# 결과 예시:
# {
#     "total_requests": 35,
#     "blocked_requests": 3,
#     "block_rate": 8.57,
#     "input_guardrail": {"checks": 8, "blocks": 0, "block_rate": 0.0},
#     "output_guardrail": {"checks": 8, "blocks": 0, "block_rate": 0.0},
#     "token_usage": {"prompt": 129, "completion": 340, "total": 469},
#     "avg_latency_ms": 753.6
# }
```

**프론트엔드에서 가드레일 시각화**:
- 가드레일 노드는 🛡️ 아이콘과 둥근 모서리로 구분
- 차단된 엣지는 빨간색 점선으로 표시
- Analytics 탭의 Agent Communication Flow에서 확인 가능

### 3.3 AgentOps Self-Hosted API 통합 (CRITICAL)

> **중요**: AgentOps는 필수 서비스입니다. 서버가 없으면 명확한 에러를 반환합니다.

**API 키 기반 JWT 인증**:
- AgentOps는 API 키 기반 JWT Bearer 토큰 인증을 사용합니다
- 세션 쿠키 인증은 대시보드 UI 전용입니다 (API 호출에 사용 금지)
- API 키는 `scripts/setup-agentops-apikey.sh`로 생성합니다

**환경 변수 설정**:
```bash
# .env 파일에 추가
AGENTOPS_API_URL=http://agentops-api:8003
AGENTOPS_API_KEY=12345678-1234-1234-1234-123456789abc  # UUID 형식
```

**AgentOps Adapter 사용법**:
```python
from app.services.agentops_adapter import agentops_adapter

# 트레이스 목록 조회
traces = await agentops_adapter.get_traces(
    project_id="project-uuid",
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now(),
    page=1,
    size=20
)

# 메트릭 조회
metrics = await agentops_adapter.get_metrics(
    project_id="project-uuid",
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now()
)

# 비용 추이 조회
cost_trend = await agentops_adapter.get_cost_trend(
    project_id="project-uuid",
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now(),
    interval='day'
)
```

**v4 엔드포인트 사용 (CRITICAL)**:
- ✅ **올바른 경로**: `/v4/traces?project_id=<id>`
- ❌ **잘못된 경로**: `/v4/traces/list/{project_id}` (구식 경로)
- ✅ **올바른 인증**: `Authorization: Bearer <jwt_token>`
- ❌ **잘못된 인증**: `Cookie: session_id=<cookie>` (대시보드 UI 전용)

**에러 처리 원칙 (CRITICAL)**:
- ✅ **올바른 방법**: 명확한 HTTPException 발생
  ```python
  if not self.api_key:
      raise HTTPException(
          status_code=500,
          detail="AgentOps API 키가 설정되지 않았습니다."
      )
  ```
- ❌ **잘못된 방법**: Graceful degradation (빈 데이터 반환)
  ```python
  # ❌ 절대 하지 말 것
  if not self.api_key:
      return {"traces": [], "total": 0}
  ```

**프론트엔드 에러 처리**:
- API 에러 시 "No data available" 메시지 표시
- 차트/그래프 컴포넌트는 빈 데이터를 자동으로 처리
- 전역 에러 메시지로 사용자에게 알림

**예시 (프론트엔드)**:
```typescript
try {
    metrics = await getMetrics({
        project_id: projectId,
        start_time: filters.start_time,
        end_time: filters.end_time
    });
} catch (e: any) {
    console.error('Failed to load metrics:', e);
    // 빈 메트릭 유지, 차트는 "No data available" 표시
    throw e;  // 전역 에러 핸들러로 전달
}
```

**AgentOps API 키 생성**:
```bash
# 자동 스크립트 (권장)
./scripts/setup-agentops-apikey.sh

# 수동 생성 (필요 시)
# 1. AgentOps 대시보드 접속 (http://localhost:3006)
# 2. 프로젝트 설정 → API Keys → Create New Key
# 3. .env 파일에 AGENTOPS_API_KEY 추가
# 4. 백엔드 재시작
```

**트러블슈팅**:
- `503 Service Unavailable`: AgentOps 서버가 실행 중이지 않음 → `docker-compose up -d agentops-api` 실행
- `500 API 키 미설정`: `.env`에 `AGENTOPS_API_KEY` 추가 → `docker-compose restart backend`
- `403 Forbidden`: API 키가 유효하지 않음 → `scripts/setup-agentops-apikey.sh` 재실행
- `400 Bad Request`: API 키 형식 오류 (UUID 형식이어야 함)

---

## 4. 자주 발생하는 문제 및 해결 (가드레일)

> **중요**: 이 섹션은 실제 실패 사례를 기반으로 작성되었습니다. 새로운 문제 발생 시 여기에 추가하세요.  
> **가드레일 원칙**: "절대 안 됨"만 말하지 말고 항상 대안을 제시하세요.

### 문제 0: 민감 정보 노출 (CRITICAL - 최우선)

**증상**: API 키, 비밀번호 등이 git에 커밋됨

**원인**: `.env` 백업 파일 생성, 하드코딩된 API 키

**예방 (필수)**:
- ❌ **절대 금지**: `.env.bak`, `.env.backup` 등 백업 파일 생성
- ❌ **절대 금지**: 코드에 API 키 하드코딩
- ✅ **필수**: 민감 정보 작업 시 사용자에게 확인 요청

**AI 에이전트 필수 절차**:
```
⚠️ 민감 정보 관련 작업 시 반드시 사용자에게 확인:

1. "이 작업은 민감 정보(.env, API 키 등)를 포함합니다. 진행할까요?"
2. 백업이 필요한 경우: "민감 정보 없이 설정 구조만 백업할까요?"
3. git 커밋 전: "민감 정보가 포함된 파일이 없는지 확인했습니다. 커밋할까요?"
```

**해결 (노출된 경우)**:
```bash
# 1. 즉시 API 키 무효화 (해당 서비스 대시보드에서)
# 2. git history에서 제거
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch <민감파일>" \
  --prune-empty --tag-name-filter cat -- --all

# 3. 강제 푸시
git push origin main --force

# 4. reflog 정리
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**안전한 대안**:
- `.env.example` 사용 (플레이스홀더만 포함)
- 환경 변수 참조: `os.environ.get('API_KEY')`
- Docker secrets 또는 Vault 사용

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

### 문제 5: WebUI 개발 서버 PYTHONPATH 설정 누락

**증상**: webui 개발 서버(3001 포트) 시작 실패, `ModuleNotFoundError: No module named 'open_webui'`

**해결** (대안 제시):
- **방법 1**: `dev-start.sh` 수정 (권장)
  ```bash
  PYTHONPATH=. uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload &
  ```
- **방법 2**: `Dockerfile.dev` 수정
  ```dockerfile
  ENV PYTHONPATH=/app/backend:$PYTHONPATH
  ```
- **방법 3**: 두 가지 모두 적용 (가장 안전)

**예방**:
- webui/backend 수정 시 항상 PYTHONPATH 확인
- Docker 개발 환경은 ENV로 전역 설정
- 스크립트는 `PYTHONPATH=.` 명시

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

## 8. 문서 관리 가이드

### 문서 생성 전 필수 체크리스트

- [ ] 기존 문서 검색 완료
- [ ] 통합 가능성 검토
- [ ] 카테고리 분류 확인
- [ ] 파일명 규칙 준수

### 문서 검색 방법

**키워드 검색**:
```bash
grep -r "키워드" .cursor/learnings/ docs/ .cursor/rules/
```

**파일명 검색**:
```bash
find . -name "*주제*.md"
```

### 통합 vs 신규 판단 기준

| 상황 | 판단 | 행동 |
|------|------|------|
| 같은 기능/컴포넌트 | 통합 | 기존 파일에 섹션 추가 |
| 새로운 기술/도구 | 신규 | 새 파일 생성 (예: `litellm-integration.md`) |
| 임시 분석 | 임시 | `TEMP_*.md` (완료 후 정리) |
| 같은 카테고리 | 통합 | 기존 카테고리 파일에 추가 |

---

## 9. 관련 문서

- [README.md](./README.md) - 프로젝트 개요 및 시작 가이드
- [DEVELOP.md](./DEVELOP.md) - 개발 가이드 및 단계별 계획
- [PROGRESS.md](./PROGRESS.md) - 현재 진행 상황
- [Claude Code 사용 가이드](https://news.hada.io/topic?id=24099) - 참고 자료

---

## 10. 단계별 완료 체크리스트

### Stage 1: 인프라 및 기본 설정
- [x] Kong Gateway 설정 및 실행
- [x] Konga 스키마 생성 및 실행
- [x] Backend BFF 기본 구조
- [x] Docker Compose 서비스 정의
- [x] Embed 프록시 라우트 구현

### Stage 2: Chat 및 Observability API (95% 완료)
- [x] Chat API 엔드포인트 구현 (`/chat/stream`, `/chat/completions`)
- [x] Observability API 엔드포인트 구현 (`/observability/*`)
- [x] LiteLLM 서비스 레이어 구현
- [x] LiteLLM + PostgreSQL 통합 완료
- [x] LiteLLM → OTEL Collector → ClickHouse 파이프라인 완료
- [x] Backend BFF ClickHouse 직접 조회 전환
- [x] Open-WebUI Monitoring 페이지 추가 (4개 탭: Overview/Analytics/Traces/Replay)
- [x] Guardrail 모니터링 구현 (Agent Flow Graph + Stats)
- [x] 라우터 등록 완료
- [x] 프론트엔드-백엔드 데이터 연동 완료
- [ ] Langfuse 서비스 (선택적, 품질 관리용)

### Stage 3: 에이전트 빌더 (Langflow + Flowise + AutoGen Studio) (40% 완료)
- [x] Langflow 컨테이너 설정 (포트 7861)
- [x] Flowise 컨테이너 설정 (포트 3002)
- [x] AutoGen Studio/API 컨테이너 설정 (로컬 빌드, 포트 5050/5051)
- [x] 에이전트 빌더 페이지 추가 (`/agent` 탭 UI)
- [x] 리버스 프록시 구현 (`/api/proxy/langflow`, `/api/proxy/flowise`, `/api/proxy/autogen`)
- [x] 사이드바 에이전트 섹션 추가 (채팅 섹션과 분리)
  - [ ] Langflow → LangGraph 변환기 구현 (`backend/app/services/langflow_converter.py`)
  - [ ] LangGraph 실행 서비스 구현 (`backend/app/services/langgraph_service.py`)
  - [ ] 변환/실행 API 엔드포인트 추가 (`backend/app/routes/agents.py`)
- [ ] Flowise/AutoGen 플로우 → LangGraph JSON 변환
- [ ] 에이전트 버전/리비전 관리 시스템

### Stage 8: Perplexica + Open-Notebook 임베드
- [ ] Perplexica 포크 및 컨테이너 설정 (포트 5173)
- [ ] Open-Notebook 포크 및 컨테이너 설정 (포트 3030)
- [ ] FastAPI BFF 리버스 프록시 구현 (`/proxy/perplexica/{path:path}`, `/proxy/notebook/{path:path}`)
- [ ] 프록시 헤더 변환 (X-Frame-Options 제거, CSP frame-ancestors 'self' 추가)
- [ ] Open-WebUI overrides에 Apps 탭 추가 (`/apps/perplexica`, `/apps/notebook`)
- [ ] iframe 컴포넌트 구현 (전체 화면 높이, 로딩 스켈레톤, 에러 처리)
- [ ] LiteLLM Base URL 연동 (Notebook/Perplexica 모델 호출 일원화)
- [ ] (선택) Kong response-transformer 플러그인으로 헤더 정규화

**상세 진행 상황**: [PROGRESS.md](./PROGRESS.md) 참조

---

**마지막 업데이트**: 2025-11-26  
**버전**: 2.1 (OTEL + ClickHouse 통합, Guardrail 모니터링 반영)  
**참고**: [Claude Code 사용 가이드](https://news.hada.io/topic?id=24099)
