# Agent Portal — 현재 상태 (2025-12-05)

> **마지막 업데이트**: 2025-12-05
> **작성자**: AI Assistant (Claude)

---

## 📊 전체 진행 상황 요약

| 영역 | 상태 | 완료율 | 비고 |
|------|------|--------|------|
| **Stage 1** | ✅ 완료 | 100% | 인프라 및 기본 설정 |
| **Stage 2** | ✅ 완료 | 100% | Chat + Observability (LiteLLM + OTEL + ClickHouse) |
| **Stage 3** | 🚧 진행 중 | 40% | 에이전트 빌더 (iframe 임베딩 완료) |
| **Stage 4** | ✅ 완료 | 100% | MCP Gateway + Kong 통합 + SSE 지원 |
| **Stage 5** | ✅ 완료 | 95% | Data Cloud + Text-to-SQL Agent |
| **Stage 8** | ❌ 미시작 | 0% | Perplexica + Open-Notebook 임베드 |

**전체 진행률**: 약 **75%**  
**최근 주요 작업**: 모니터링 Traces 서브탭 구현, 문서 정리

---

## ✅ 최근 완료된 작업 (2025-12-01 ~ 2025-12-05)

### 1. 모니터링 대시보드 개선 ✨

**완료 사항**:
- ✅ Traces 탭에 서브탭 추가 (Agent / LLM Call / All)
- ✅ 트레이스 필터링 기능 강화
- ✅ AgentOps 참조 제거 및 이름 통일 (`monitoring`)

**접속 경로**: http://localhost:3009/admin/monitoring

### 2. Text-to-SQL Agent (LangGraph) ✨

**완료 사항**:
- ✅ LangGraph 기반 Plan-and-Execute 패턴 구현
- ✅ 9개 노드 파이프라인 (entry → analyze → generate → validate → fix → execute → format → complete)
- ✅ OTEL 기반 전체 실행 추적
- ✅ 다중 DB 지원 (MariaDB, PostgreSQL, ClickHouse)
- ✅ 에러 자동 복구 (최대 3회 재시도)
- ✅ 복잡 쿼리 테스트 완료

**접속 경로**: http://localhost:3009/admin/datacloud → SQL 채팅 기능

### 3. 코드베이스 정리 ✨

**완료 사항**:
- ✅ `agentops-reference/` 폴더 삭제
- ✅ AgentOps 관련 코드/문서 참조 제거
- ✅ Langfuse/Helicone 관련 코드 제거
- ✅ 모니터링 스택 단순화 (LiteLLM + OTEL + ClickHouse)
- ✅ README.md 전면 업데이트

---

## 🏗 핵심 아키텍처

### 모니터링 파이프라인

```
LiteLLM (4000) → OTEL Collector (4317/4318) → ClickHouse (otel_2.otel_traces)
                                                     ↓
                                              Backend BFF (8000)
                                                     ↓
                                              Monitoring UI (3009)
```

### 서비스 현황 (주요)

| 서비스 | 포트 | 상태 | 용도 |
|--------|------|------|------|
| webui | 3009 | ✅ Running | Portal UI (SvelteKit) |
| backend | 8000 | ✅ Running | FastAPI BFF |
| litellm | 4000 | ✅ Running | LLM Gateway |
| mariadb | 3306 | ✅ Running | App Database |
| clickhouse | 8124 | ✅ Running | OTEL Traces |
| kong | 8002 | ✅ Running | API Gateway |
| konga | 1337 | ✅ Running | Kong Admin UI |

---

## 🚧 진행 중인 작업

### Stage 3: 에이전트 빌더 (40% 완료)

**완료**:
- ✅ Langflow/Flowise iframe 임베딩
- ✅ 리버스 프록시 구현

**남은 작업**:
- [ ] Langflow → LangGraph 변환기 구현
- [ ] 에이전트 버전/리비전 관리 시스템

### DART Agent (WIP)

**완료**:
- ✅ MCP HTTP 클라이언트 구현
- ✅ LiteLLM 기반 BaseAgent 구현
- ✅ 멀티에이전트 구조 포팅
- ✅ 좌우 분할 UI 구현

**남은 작업**:
- [ ] MCP 서버 연결 테스트 (외부 서버 필요)

---

## 📋 개발 환경 체크리스트

### 서비스 상태

- [x] Docker Compose 실행 중
- [x] Open-WebUI (3009 포트) 정상 동작
- [x] Backend BFF (8000 포트) 정상 동작
- [x] LiteLLM (4000 포트) 정상 동작
- [x] OTEL Collector (4317/4318 포트) 정상 동작
- [x] ClickHouse (8124 포트) 정상 동작
- [x] MariaDB (3306 포트) 정상 동작
- [x] Kong Gateway (8002 포트) 정상 동작
- [x] Konga (1337 포트) 정상 동작

### 테스트 상태

- [x] Chat 스트리밍 응답 정상
- [x] Monitoring 대시보드 데이터 표시
- [x] ClickHouse traces 저장/조회
- [x] Text-to-SQL Agent 복잡 쿼리
- [x] Data Cloud DB 연결/쿼리
- [x] MCP 서버 등록/도구 목록

---

## 🎯 다음 우선순위 작업

### P0 (Urgent)

1. **인증/인가 시스템 구현**
   - [ ] JWT 토큰 검증
   - [ ] RBAC 미들웨어 활성화
   - [ ] 관리자 전용 페이지 보호

### P1 (Important)

2. **에이전트 빌더 완성**
   - [ ] Langflow → LangGraph 변환기
   - [ ] 에이전트 버전 관리

3. **테스트 코드 작성**
   - [ ] pytest 기본 구조
   - [ ] API 엔드포인트 테스트
   - [ ] ClickHouse 쿼리 테스트

---

## 📚 주요 문서

| 문서 | 설명 | 상태 |
|------|------|------|
| [README.md](../README.md) | 프로젝트 개요 | ✅ 최신 |
| [AGENTS.md](../AGENTS.md) | AI Agent 기술 레퍼런스 | ✅ 최신 |
| [MONITORING_SETUP.md](./MONITORING_SETUP.md) | 모니터링 설정 가이드 | ✅ 최신 |
| [KONGA_SETUP.md](./KONGA_SETUP.md) | Kong Gateway 설정 가이드 | ✅ 최신 |
| [TEXT2SQL_AGENT.md](./TEXT2SQL_AGENT.md) | Text-to-SQL Agent 설명서 | ✅ 최신 |
| [SERVICE-DATABASE-STATUS.md](./SERVICE-DATABASE-STATUS.md) | 서비스/DB 상태 | ✅ 최신 |

---

**마지막 업데이트**: 2025-12-05
**다음 리뷰 예정**: 2025-12-06
