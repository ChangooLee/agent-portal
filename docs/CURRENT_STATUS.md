# Agent Portal — 현재 상태 (2025-11-27)

> **마지막 업데이트**: 2025-11-27 22:35
> **작성자**: AI Assistant (Claude)

---

## 📊 전체 진행 상황 요약

| 영역 | 상태 | 완료율 | 비고 |
|------|------|--------|------|
| **Stage 1** | ✅ 완료 | 100% | 인프라 및 기본 설정 |
| **Stage 2** | ✅ 완료 | 95% | Chat + Observability (LiteLLM + OTEL + ClickHouse 통합 완료) |
| **Stage 3** | 🚧 진행 중 | 40% | 에이전트 빌더 (iframe 임베딩 완료, LangGraph 변환 미완) |
| **Stage 4** | ✅ 완료 | 100% | MCP Gateway + Kong 통합 + 권한 관리 + SSE 지원 |
| **Stage 5** | 🚧 진행 중 | 85% | Data Cloud 커넥터 (UI/API 완료, Kong 통합 미완) |
| **Stage 8** | ❌ 미시작 | 0% | Perplexica + Open-Notebook 임베드 |

**전체 진행률**: 약 **60%**  
**최근 주요 작업**: Data Cloud 커넥터 구현 (Zero Copy DB 연결)

---

## ✅ 최근 완료된 작업 (2025-11-25 ~ 2025-11-27)

### 0. Data Cloud 커넥터 ✨ (2025-11-27) - NEW

**완료 사항**:
- ✅ DB 스키마 설계 및 적용 (`scripts/init-datacloud-schema.sql`)
- ✅ Backend 서비스 구현 (`datacloud_service.py`)
- ✅ API 라우터 구현 (`/datacloud/*`)
- ✅ Admin UI 구현 (`/admin/datacloud`) - Glassmorphism 적용
- ✅ 브라우저 테스트 완료 (스키마 조회, 쿼리 실행)

**등록된 DB 연결**:
| DB | 호스트 | 포트 | 상태 |
|-----|--------|------|------|
| Agent Portal MariaDB | mariadb | 3306 | ✅ 정상 |
| LiteLLM PostgreSQL | litellm-postgres | 5432 | ✅ 정상 |

**접속 경로**: http://localhost:3001/admin/datacloud

### 1. MCP Gateway + Kong 통합 ✨ (2025-11-27)

**완료 사항**:
- ✅ MCP 서버 DB 스키마 설계 및 적용 (`mcp_servers`, `mcp_server_permissions`)
- ✅ Kong Gateway 서비스 통합 (`kong_service.py`)
- ✅ MCP 관리 API 구현 (`/mcp/servers`, CRUD + 권한 관리)
- ✅ MCP Admin UI 구현 (`/admin/mcp`)
- ✅ MCP 권한 관리 시스템 (사용자/그룹 단위)
- ✅ Gateway Admin UI 개선 (`/admin/gateway` - 개요 + Kong Admin 탭)
- ✅ Konga 설정 및 Kong 연결 완료
- ✅ **SSE 전송 방식 지원 추가** (2025-11-27)

**지원 MCP 전송 방식**:

| 전송 방식 | 프로토콜 | 예시 | 상태 |
|----------|----------|------|------|
| **Streamable HTTP** | POST + `mcp-session-id` 헤더 | MCP OpenDART (85개 도구) | ✅ 정상 |
| **SSE** | GET `/sse` + POST `/messages/?session_id=...` | MCP Naver News (2개 도구) | ✅ 정상 |

**Konga 설정 정보**:
- URL: http://localhost:1337
- Email: lchangoo@gmail.com
- Password: Cksrn0604!
- Kong Connection: `local-kong` (http://kong:8001)
- 설정 가이드: [docs/KONGA_SETUP.md](./KONGA_SETUP.md)

**등록된 MCP 서버**:
- MCP OpenDART (`http://121.141.60.219:8089/mcp`) - 85개 도구
- MCP Naver News (`http://121.141.60.219:30089/sse`) - 2개 도구

**등록된 Kong 리소스**:
- Service: `mcp-e13ae9f3-...` (MCP OpenDART), `mcp-fcb4e0b2-...` (MCP Naver News)
- Consumer: `mcp-consumer-e13ae9f3-...`, `mcp-consumer-fcb4e0b2-...`
- Plugins: `key-auth`, `rate-limiting`

### 1. LiteLLM + OTEL + ClickHouse 통합 ✨

**아키텍처**:
```
LiteLLM (4000) → OTEL Collector (4317/4318) → ClickHouse (otel_2.otel_traces)
                                                     ↓
                                              Backend BFF (8000)
                                                     ↓
                                              Monitoring UI (3001)
```

**완료 사항**:
- ✅ LiteLLM OTEL callback 활성화 (`callbacks: - otel`)
- ✅ OTEL Collector ClickHouse exporter 설정
- ✅ ClickHouse 스키마 마이그레이션 (`project_id` MATERIALIZED 컬럼)
- ✅ Backend BFF ClickHouse HTTP API 직접 조회 전환

**검증 완료**:
```bash
# ClickHouse에 traces 저장 확인
docker exec agentops-clickhouse clickhouse-client --query \
  "SELECT count(*) FROM otel_2.otel_traces"
# 결과: 35건 이상
```

### 2. Guardrail 모니터링 구현 🛡️

**Agent Flow Graph**:
```
[Client Request] → [Input Guardrail] → [LiteLLM Proxy] → [LLM Provider] → [Output Guardrail]
```

**완료 사항**:
- ✅ `get_agent_flow_graph()` 함수 개선 (가드레일 노드 추가)
- ✅ `get_guardrail_stats()` API 추가
- ✅ 프론트엔드 가드레일 시각화 (🛡️ 아이콘, 차단 엣지)

### 3. Monitoring 대시보드 완성 📊

**4개 탭 구현 완료**:
- ✅ **Overview**: LLM/Agent 호출 수, 총 비용, 평균 레이턴시
- ✅ **Analytics**: Agent Flow Graph, 성능 차트
- ✅ **Traces**: 트레이스 목록 (LLM/Agent 호출만 필터링)
- ✅ **Replay**: 세션 리플레이어

**주요 개선**:
- ✅ 비용 표시 형식 개선 (`$0.000016` 형식)
- ✅ Duration 나노초→밀리초 변환
- ✅ LLM/Agent 호출만 필터링 (auth, postgres 등 내부 호출 제외)

### 4. 사이드바 구조 개편 🎨

**완료 사항**:
- ✅ 에이전트 섹션을 채팅 섹션 위로 이동
- ✅ 섹션 제목 스타일 강화 (크기, 굵기, 색상)
- ✅ 새 채팅 버튼 모델 자동 선택 수정 (`$models` 로드 대기)
- ✅ 통합 검색 기능 (채팅 + 에이전트)

### 5. 민감 정보 보호 강화 🔒

**완료 사항**:
- ✅ Pre-commit hook에 민감 정보 패턴 검사 추가
- ✅ `.gitignore` 강화 (`.env.bak*`, `*.key`, `*.pem` 등)
- ✅ Git history에서 노출된 API 키 제거 (`git filter-branch`)
- ✅ 민감 정보 처리 절차 문서화 (`AGENTS.md` Section 4.0)

---

## 🚧 진행 중인 작업

### Stage 3: 에이전트 빌더 (40% 완료)

**완료**:
- ✅ Langflow/Flowise/AutoGen Studio iframe 임베딩
- ✅ 리버스 프록시 구현

**남은 작업**:
- [ ] Langflow → LangGraph 변환기 구현
- [ ] LangGraph 실행 서비스 구현
- [ ] 에이전트 버전/리비전 관리 시스템

### Stage 5: Data Cloud 커넥터 (85% 완료) ✨ NEW

**완료**:
- ✅ DB 스키마 설계 (`db_connections`, `db_schema_cache`, `db_business_terms`, `db_connection_permissions`, `db_query_logs`)
- ✅ Backend 서비스 (`datacloud_service.py`) - SQLAlchemy 스키마 리플렉션
- ✅ API 라우터 (`/datacloud/*`) - CRUD, 테스트, 스키마 조회, 쿼리 실행
- ✅ Admin UI (`/admin/datacloud`) - Glassmorphism 디자인
- ✅ 비밀번호 Fernet 암호화
- ✅ 2개 DB 연결 완료 (MariaDB, PostgreSQL)
- ✅ 스키마 조회/캐싱 정상 동작
- ✅ SQL 쿼리 실행 및 결과 표시

**남은 작업**:
- [ ] Kong Gateway 통합 (API Key 인증, Rate Limiting)
- [ ] 추가 DB 연결 (kong-db, konga-db 등)
- [ ] 비즈니스 용어집 UI
- [ ] 권한 관리 UI
- [ ] 쿼리 결과 차트 시각화

**계획 문서**: [docs/plans/DATA_CLOUD_DEVELOPMENT.md](./plans/DATA_CLOUD_DEVELOPMENT.md)

---

## 🎯 다음 우선순위 작업 (P0 → P1 → P2)

### P0 (Urgent - 즉시 착수)

#### 1. 테스트 코드 작성 (Critical)
- [ ] pytest 설정 및 기본 테스트 구조
- [ ] AgentOps API 테스트
- [ ] ClickHouse 쿼리 테스트

#### 2. 인증/인가 시스템 구현 (Critical)
- [ ] JWT 토큰 검증
- [ ] RBAC 미들웨어 활성화
- [ ] 모든 엔드포인트 보안 적용

### P1 (Important - 금주 내 완료)

#### 3. Langflow → LangGraph 변환기
- [ ] Langflow API 분석
- [ ] LangGraph JSON 스키마 정의
- [ ] 변환 로직 구현

#### 4. Today 페이지 뉴스 기능 개선
- [ ] News API 엔드포인트 구현
- [ ] 무한 스크롤 동작 확인
- [ ] 실시간 검색 필터링 테스트

---

## 📋 체크리스트

### 개발 환경 상태

- [x] Docker Compose 실행 중
- [x] Open-WebUI (3001 포트) 정상 동작
- [x] Backend BFF (8000 포트) 정상 동작
- [x] LiteLLM (4000 포트) 정상 동작
- [x] OTEL Collector (4317/4318 포트) 정상 동작
- [x] ClickHouse (8124 HTTP / 9002 Native 포트) 정상 동작
- [x] MariaDB (3306 포트) 정상 동작
- [x] Langflow (7861 포트) 정상 동작
- [x] Flowise (3002 포트) 정상 동작
- [x] Kong Gateway (8001/8002 포트) 정상 동작
- [x] Konga (1337 포트) 정상 동작 - [설정 가이드](./KONGA_SETUP.md)
- [ ] AutoGen API (5051 포트) 의존성 오류

### 테스트 상태

- [x] Chat 스트리밍 응답 정상
- [x] Monitoring 대시보드 데이터 표시
- [x] ClickHouse traces 저장/조회
- [x] 새 채팅 버튼 모델 자동 선택
- [x] 사이드바 구조 개편
- [ ] 테스트 코드 없음 (Critical)
- [ ] 인증/인가 시스템 없음 (Critical)

---

## 🚨 알려진 이슈

### Critical
- ❌ **테스트 코드 완전 부재**: pytest 미작성
- ❌ **인증/인가 시스템 없음**: 보안 취약점
- ⚠️ **AutoGen API 의존성 오류**: Python 버전 충돌

### High
- ⚠️ **LangGraph 변환 미구현**: Stage 3 핵심 기능 미완

### Medium
- ⚠️ **News API 미연동**: 샘플 데이터만 표시

---

## 📚 문서 상태

### 최신 문서 (2025-11-27)
- ✅ `docs/KONGA_SETUP.md` - Konga 설정 가이드
- ✅ `docs/plans/MCP_GATEWAY_PLAN.md` - MCP Gateway 구현 계획
- ✅ `.cursor/learnings/sensitive-info-protection.md`
- ✅ `docs/CURRENT_STATUS.md` (이 문서)

### 업데이트 필요
- ⚠️ `AGENTS.md` (Stage 진행 상황 업데이트 필요)
- ⚠️ `README.md` (전체 진행률 업데이트 필요)

---

## 🎯 권장 다음 단계 (우선순위 순)

### 1단계: 테스트 코드 작성 (4-6시간)
**목적**: 코드 품질 보장

**절차**:
1. pytest 설정 및 기본 구조
2. AgentOps API 테스트 작성
3. ClickHouse 쿼리 테스트 작성

### 2단계: 인증/인가 시스템 (8-12시간)
**목적**: 보안 강화

**절차**:
1. JWT 토큰 검증 미들웨어
2. RBAC 권한 체크
3. 관리자 전용 페이지 보호

### 3단계: Langflow → LangGraph 변환 (8-12시간)
**목적**: Stage 3 핵심 기능 완성

**절차**:
1. Langflow API 분석
2. LangGraph JSON 스키마 정의
3. 변환 로직 구현
4. API 엔드포인트 추가

---

**마지막 업데이트**: 2025-11-27 15:00  
**다음 리뷰 예정**: 2025-11-28

