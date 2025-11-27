# AgentOps 제거 및 모니터링 시스템 전환

## 날짜: 2025-11-26

## 변경 사항

### 1. AgentOps Self-Hosted 완전 제거

**제거된 항목**:
- `external/agentops/` 서브모듈
- `agentops-dashboard/` 디렉토리
- `backend/app/services/agentops_session_service.py`
- `backend/app/routes/agentops.py`
- `proxy.py`의 `proxy_agentops_*` 함수 2개
- `requirements.txt`의 `agentops==0.3.0` 의존성

**이유**:
- AgentOps Self-Hosted는 Elastic 2.0 라이선스 (호스팅 서비스 제한)
- 실제로 AgentOps API/Dashboard는 사용하지 않고 ClickHouse 직접 조회만 사용 중
- 라이선스 안전한 Apache-2.0 기반 OTEL + ClickHouse로 충분

### 2. 코드 리네임

| 기존 | 변경 후 |
|------|---------|
| `agentops_adapter.py` | `monitoring_adapter.py` |
| `agentops.py` | `monitoring.py` |
| `$lib/agentops/` | `$lib/monitoring/` |
| `$lib/components/agentops/` | `$lib/components/monitoring/` |
| `agentops-clickhouse` | `monitoring-clickhouse` |
| `agentops-otel-collector` | `monitoring-otel-collector` |

### 3. 새로 추가된 기능

**프로젝트 관리 시스템**:
- `scripts/init-project-schema.sql` - DB 스키마
- `backend/app/routes/projects.py` - 프로젝트 CRUD API
- `backend/app/services/project_service.py` - 프로젝트 서비스
- `webui/src/routes/(app)/admin/projects/+page.svelte` - Admin UI

**Monitoring 페이지 업데이트**:
- 프로젝트 선택 드롭다운 추가
- 하드코딩된 project_id 제거

### 4. Docker 인프라 변경

**docker-compose.yml**:
- `agentops-clickhouse` → `monitoring-clickhouse`
- `agentops-otel-collector` → `monitoring-otel-collector`
- `agentops-dashboard` 서비스 제거
- 환경변수 `AGENTOPS_*` → `CLICKHOUSE_*`, `DEFAULT_PROJECT_ID`

**otel-collector/**:
- `external/agentops/app/opentelemetry-collector/` 내용 복사
- `AGENTOPS_PROJECT_ID` → `DEFAULT_PROJECT_ID`

### 5. 아키텍처 변경

**이전**:
```
LiteLLM → OTEL Collector → ClickHouse
                              ↓
                        AgentOps API
                              ↓
                     AgentOps Dashboard
                              ↓
                        (iframe 임베드)
```

**현재**:
```
LiteLLM → OTEL Collector → ClickHouse
                              ↓
                     monitoring_adapter.py
                              ↓
                     Backend BFF API
                              ↓
                   Open-WebUI Monitoring
```

## 검증 항목

### 모니터링 기능 테스트

| 탭 | 테스트 항목 | API 엔드포인트 |
|----|------------|----------------|
| Overview | 메트릭 로드 | `/api/monitoring/metrics` |
| Overview | 비용 추이 차트 | `/api/monitoring/analytics/cost-trend` |
| Overview | 토큰 사용량 차트 | `/api/monitoring/analytics/token-usage` |
| Analytics | 성능 메트릭 | `/api/monitoring/analytics/performance` |
| Analytics | Agent Flow Graph | `/api/monitoring/analytics/agent-flow` |
| Traces | 트레이스 목록 | `/api/monitoring/traces` |
| Traces | 트레이스 상세 | `/api/monitoring/traces/{id}` |
| Replay | 세션 리플레이 | `/api/monitoring/replay/{id}` |

### 프로젝트 관리 테스트

| 기능 | API 엔드포인트 |
|------|----------------|
| 목록 조회 | `GET /api/projects` |
| 생성 | `POST /api/projects` |
| 상세 조회 | `GET /api/projects/{id}` |
| 수정 | `PUT /api/projects/{id}` |
| 삭제 | `DELETE /api/projects/{id}` |

## 라이선스 현황

| 컴포넌트 | 라이선스 | 상태 |
|----------|----------|------|
| OpenTelemetry Collector | Apache-2.0 | ✅ 안전 |
| ClickHouse | Apache-2.0 | ✅ 안전 |
| LiteLLM | MIT | ✅ 안전 |
| Open-WebUI | Open WebUI License | ⚠️ 브랜딩 의무 |

## 향후 계획

1. **프로젝트 관리 고도화**:
   - 팀 관리 기능 추가
   - 사용자 접근 권한 관리
   - 프로젝트별 비용 한도 설정

2. **MCP Gateway 구현**:
   - `docs/plans/MCP_GATEWAY_PLAN.md` 참조
   - Kong Gateway 기반 MCP 서버 관리

---

**참고**: MCP Gateway 계획은 `docs/plans/MCP_GATEWAY_PLAN.md`에 백업되어 있습니다.

