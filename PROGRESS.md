# Agent Portal — 진행 상황

> 최종 업데이트: 2025-11-26

---

## 📊 전체 진행 상황

| 단계 | 상태 | 완료율 | 비고 |
|------|------|--------|------|
| **Stage 1** | ✅ 완료 | 100% | 인프라 및 기본 설정 (1-2주) |
| **Stage 2** | ✅ 완료 | 100% | LiteLLM + Monitoring + Grafana (2-3주) |
| **Stage 3** | 🚧 진행 중 | 35% | 에이전트 빌더 (3-4주) |
| **Stage 4** | ❌ 미시작 | 0% | MCP SSE + Kong (2-3주) |
| **Stage 5** | ❌ 미시작 | 0% | 데이터베이스 (3-4주) |
| **Stage 6** | ❌ 미시작 | 0% | Document Intelligence (3-4주) |
| **Stage 7** | ❌ 미시작 | 0% | UI 뷰 모드 (2주) |
| **Stage 8** | ❌ 미시작 | 0% | 포털 통합 (2-3주) |
| **Stage 9** | ❌ 미시작 | 0% | 가드레일 (2-3주) |

**전체 진행률**: 약 **27%** (Stage 1-2 완료, Stage 3 진행 중)  
**총 예상 개발 기간**: 약 **22-30주** (5.5-7.5개월)

---

## ✅ Stage 1: 인프라 및 기본 설정 (완료)

**목표**: 개발 환경 구축 및 기본 인프라 설정

**완료 항목**:
- ✅ Docker Compose 설정
- ✅ Open-WebUI 포크 및 커스터마이즈
- ✅ UI 개선 (탭 스타일, 브랜딩)
- ✅ 레이아웃 수정 (사이드바 여백 문제 해결)
- ✅ 브라우저 제목 통일 (SFN AI Portal)
- ✅ 관리자 메뉴 구조 개편
  - 사용자관리, 사용량, MCP, Gateway, 가드레일, 리더보드
- ✅ 메인 네비게이션 메뉴 구현
  - 보고서, 에이전트, 노트북, 검색, 사용량, 일정관리, 관리자
- ✅ Git hooks 설정 (pre-commit, post-commit)
- ✅ AI 코딩 가이드라인 작성 (.cursorrules, AGENTS.md, CLAUDE.md)

**실행 중인 서비스**:
- ✅ Open-WebUI (포트 3001)
- ✅ Backend BFF (포트 8000)
- ✅ LiteLLM (포트 4000)
- ✅ Monitoring ClickHouse (포트 8124/9002)
- ✅ Monitoring OTEL Collector (포트 4317/4318)

---

## ✅ Stage 2: Chat 엔드포인트 연동 및 모니터링 (완료)

**목표**: FastAPI BFF 생성, LiteLLM 연동, ClickHouse 기반 모니터링

**완료 항목**:
- ✅ Backend BFF 기본 구조 생성
- ✅ Chat API 구현 (`/chat/stream`, `/chat/completions`)
- ✅ LiteLLM 통합 (OpenRouter 연동)
- ✅ Embed 프록시 구현 (`/proxy/grafana`, `/embed/kong-admin` 등)
- ✅ **Monitoring 시스템 구현** (ClickHouse 기반)
  - ✅ LiteLLM → OTEL Collector → ClickHouse 파이프라인
  - ✅ Backend BFF → ClickHouse 직접 조회 (`monitoring_adapter.py`)
  - ✅ Monitoring UI (4개 탭: Overview, Analytics, Traces, Replay)
- ✅ **프로젝트 관리 시스템 구현**
  - ✅ 프로젝트 CRUD API (`/api/projects`)
  - ✅ 팀 관리 API (`/api/teams`)
  - ✅ Admin 프로젝트 관리 UI
- ✅ 모니터링 대시보드 구현 (관리자 > 사용량)
- ✅ 모니터링 스택 구축
  - ✅ OTEL Collector (4317/4318)
  - ✅ ClickHouse (8124/9002)
  - ✅ Prometheus (9090)
  - ✅ Grafana (3005)
- ✅ Agent Flow Graph + Guardrail 모니터링
  - ✅ 실제 호출 흐름 시각화: Client → Input Guardrail → LiteLLM → LLM Provider → Output Guardrail
  - ✅ 각 단계별 통계: call_count, avg_latency_ms, total_tokens, total_cost
  - ✅ Guardrail Stats API (`/api/monitoring/analytics/guardrails`)
  - ✅ 가드레일 노드 시각적 구분 (🛡️ 아이콘, 둥근 모서리)

**아키텍처**:
```
[LiteLLM Proxy] → [OTEL Collector] → [ClickHouse]
                                           ↓
[Backend BFF] ← [monitoring_adapter.py] ←─┘
      ↓
[Open-WebUI Monitoring UI]
```

**코드 위치**:
- Backend BFF: `backend/app/`
- Chat API: `backend/app/routes/chat.py`
- Monitoring API: `backend/app/routes/monitoring.py`
- Monitoring Adapter: `backend/app/services/monitoring_adapter.py`
- Monitoring UI: `webui/src/routes/(app)/admin/monitoring/+page.svelte`
- Monitoring Components: `webui/src/lib/components/monitoring/`
- Projects API: `backend/app/routes/projects.py`
- Projects UI: `webui/src/routes/(app)/admin/projects/+page.svelte`

---

## 🚧 Stage 3: 에이전트 빌더 (진행 중)

**목표**: Langflow, Flowise, AutoGen Studio 임베드, Langflow UI 재구현, LangGraph 변환 + 실행 + 모니터링

**완료 항목**:
- ✅ Langflow 컨테이너 설정 (포트 7861)
- ✅ Flowise 컨테이너 설정 (포트 3002)
- ✅ AutoGen Studio/API 컨테이너 설정 (로컬 빌드, 포트 5050/5051)
- ✅ 에이전트 빌더 페이지 구현 (`/agent` 탭 UI)
- ✅ 리버스 프록시 구현 (`/api/proxy/langflow`, `/api/proxy/flowise`, `/api/proxy/autogen`)
- ✅ 사이드바 에이전트 섹션 구현
  - ✅ 채팅/에이전트 섹션 분리
  - ✅ 통합 검색 기능

**진행 중 항목**:
- 🚧 Langflow UI 재구현 - Phase 1-B (LangGraph 변환 + 실행)
  - ⏳ Langflow → LangGraph 변환기 구현 (`backend/app/services/langflow_converter.py`)
  - ⏳ LangGraph 실행 서비스 구현 (`backend/app/services/langgraph_service.py`)
  - ⏳ 변환/실행 API 엔드포인트 추가 (`backend/app/routes/agents.py`)
  - ⏳ 플로우 카드 컴포넌트 (Export/Run 버튼)
  - ⏳ 실행 결과 패널 (비용 정보, 리플레이 링크)

**미완성 항목**:
- ❌ Flowise/AutoGen 플로우 → LangGraph JSON 변환 (Phase 2)
- ❌ 에이전트 버전/리비전 관리 시스템 (Phase 2)

**코드 위치**:
- Backend API: `backend/app/routes/agents.py`
- Frontend: `webui/src/routes/(app)/agent/+page.svelte`

---

## ❌ Stage 4: MCP 연동 및 Kong Gateway (미시작)

**목표**: MCP stdio/SSE 엔드포인트 구현, Kong Gateway 보안/레이트리밋

**계획된 작업**:
- ⏳ Kong Gateway 실제 동작 확인
- ⏳ Konga (Kong Admin UI) 연동
- ⏳ MCP stdio 엔드포인트 구현 (`/mcp/stdio/launch`)
- ⏳ MCP SSE 엔드포인트 구현 (`/mcp/sse`)
- ⏳ MCP Manager UI (서버 등록, Kong 키 발급/회수, 스코프 관리)
- ⏳ Key-Auth 및 Rate-Limiting 설정

**상세 계획**: `docs/plans/MCP_GATEWAY_PLAN.md` 참조

---

## ❌ Stage 5: 데이터베이스 및 관리 기능 (미시작)

**목표**: MariaDB 스키마 설계, 사용자/워크스페이스/에이전트 관리 API, 데이터베이스 커넥터

**계획된 작업**:
- ⏳ MariaDB 스키마 설계 (users, workspaces, agents, mcp_servers)
- ⏳ 관리 API 구현 (CRUD 엔드포인트)
- ⏳ RBAC 권한 체크
- ⏳ 관리자 UI 연동
- ⏳ 데이터베이스 커넥터 구현 (SAP HANA, Oracle, MariaDB, Postgres, S3/CSV/Parquet)

---

## ❌ Stage 6: Document Intelligence (미시작)

**목표**: 문서 파싱, OCR, 청킹, 임베딩 파이프라인 및 ChromaDB 연동

**계획된 작업**:
- ⏳ Document Service 마이크로서비스 생성 (FastAPI, 포트 8080)
- ⏳ unstructured + PaddleOCR 파이프라인
- ⏳ 레이아웃 인식 (표/캡션/도형) 및 VLM 캡셔닝 (선택)
- ⏳ 지능형 청킹 (페이지 경계 인지, 문맥 overlap, 표/제목 보존)
- ⏳ bge-m3 임베딩 및 ChromaDB 벡터 저장소 연동
- ⏳ RAG 검색 API 구현 (하이브리드: 키워드+벡터)
- ⏳ MinIO 오브젝트 스토리지 연동 (원본 문서 저장)

---

## ❌ Stage 7: UI 뷰 모드 전환 (미시작)

**목표**: 대화창을 3가지 뷰 모드로 전환 가능하게 구현

**계획된 작업**:
- ⏳ 뷰 모드 토글 컴포넌트
- ⏳ 레포트형 렌더링 강화 (Artifacts: 차트/표)
- ⏳ 포털형 UI (카드/타일 형식)
- ⏳ 채팅형 UI (기존 메시지 스레드)

---

## ❌ Stage 8: Perplexica + Open-Notebook 임베드 (미시작)

**목표**: Perplexica와 Open-Notebook을 Open-WebUI 포털 쉘에 iframe으로 임베드

**계획된 작업**:
- ⏳ Perplexica 포크 및 컨테이너 설정
- ⏳ Open-Notebook 포크 및 컨테이너 설정
- ⏳ FastAPI BFF 리버스 프록시 구현
- ⏳ 프록시 헤더 변환 (X-Frame-Options 제거, CSP frame-ancestors 'self' 추가)
- ⏳ Apps 탭 추가 (`/apps/perplexica`, `/apps/notebook`)
- ⏳ iframe 컴포넌트 구현 (전체 화면 높이, 로딩 스켈레톤, 에러 처리)
- ⏳ LiteLLM Base URL 연동

---

## ❌ Stage 9: 가드레일 관리 (미시작)

**목표**: PII 감지, 입력/출력 필터, 가드레일 이벤트 로깅

**계획된 작업**:
- ⏳ Presidio 기반 PII 감지 (마스킹/차단)
- ⏳ 입력/출력 필터 (독성/금칙어, 워크스페이스 규칙)
- ⏳ 근거 인용 강제 (RAG 미첨부 시 경고/차단)
- ⏳ 가드레일 이벤트 로깅 및 관리자 대시보드

---

## 🎯 즉시 해결 필요 (P0)

### 1. 환경 설정 및 서비스 실행
- [ ] `.env` 파일 정리 및 `.env.example` 생성
- [ ] `docker-compose up -d` 전체 스택 실행 테스트
- [ ] 서비스 간 연결 확인 (health check)
- [ ] 실제 API 키 설정 (OpenAI, Anthropic 등)

### 2. 보안 (Critical)
- [ ] 인증/인가 시스템 구현
  - Open-WebUI 인증 시스템과 BFF 연동
  - JWT 토큰 검증 구현
  - RBAC 미들웨어 활성화
  - 모든 엔드포인트 보안 적용

### 3. 테스트
- [ ] pytest 설정 및 기본 테스트 구조
- [ ] Chat API 테스트
- [ ] Monitoring API 테스트
- [ ] 서비스 레이어 테스트

---

## 📝 알려진 문제점

### 1. 서비스 미실행
- **현상**: docker-compose.yml에 정의된 일부 서비스가 실행되지 않음
- **원인**: 환경변수 미설정, 의존성 문제
- **해결책**: 환경 설정 가이드 작성 및 단계별 서비스 실행

### 2. README 불일치
- **현상**: README의 docker-compose.yml 예시와 실제 파일이 다름
- **원인**: README는 최종 목표 구조, 실제는 개발 중
- **해결책**: README에 "현재 구현 상태" 섹션 추가

### 3. 포트 번호 불일치
- **현상**: README와 docker-compose.yml의 포트 번호가 다름
- **예시**:
  - Open-Notebook: README 3030 vs 실제 3100
  - Perplexica: README 5173 vs 실제 3210
- **해결책**: 포트 매트릭스 업데이트

### 4. 누락된 컴포넌트
- **document-service/**: 디렉토리만 존재, 구현 없음
- **Langflow/Flowise**: docker-compose.yml에 정의됨, 실행 중
- **AutoGen Studio/API**: docker-compose.yml에 정의됨

---

## 📚 참고 문서

- [README.md](./README.md) - 프로젝트 개요 및 최종 목표
- [DEVELOP.md](./DEVELOP.md) - 개발 가이드 및 단계별 계획
- [AGENTS.md](./AGENTS.md) - AI 에이전트 가이드
- [CLAUDE.md](./CLAUDE.md) - 프로젝트 헌법 (AI 행동 규칙)
- [docs/plans/MCP_GATEWAY_PLAN.md](./docs/plans/MCP_GATEWAY_PLAN.md) - MCP Gateway 계획

---

**작성자**: AI Agent (Claude)  
**마지막 업데이트**: 2025-11-26
