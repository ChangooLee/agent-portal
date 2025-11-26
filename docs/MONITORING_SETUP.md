# Monitoring Setup Guide

## Overview

Agent Portal의 모니터링은 **두 가지 독립적인 스택**으로 구성됩니다:

### 1. LLM 모니터링: LiteLLM ↔ AgentOps Self-Hosted (직접 연결)
```
LiteLLM (LLM Gateway)
  └─> AgentOps SDK (콜백/직접 연결)
        └─> AgentOps API (8003, self-hosted)
              └─> ClickHouse (메트릭 저장)
                    ↑
Backend BFF → AgentOps API v4 (httpx 클라이언트)
  └─> 모니터링 화면 (실제 데이터 표시)
```

### 2. 인프라 모니터링: Prometheus + Grafana
```
vLLM / 애플리케이션
  └─> OTEL Collector (메트릭 수집)
        └─> Prometheus (시계열 데이터 저장)
              └─> Grafana (시각화)
```

**Langfuse**는 별도의 **Agent 품질 관리 도구**로 제공되며 선택적입니다.

---

## Quick Start

### 1. 환경 변수 설정

```bash
# .env 파일에 다음 추가
# AgentOps Self-Hosted (필수)
AGENTOPS_API_KEY=da317188-e3be-4ecf-be31-7bb5d5f015e3  # AgentOps self-hosted API 키
AGENTOPS_API_ENDPOINT=http://localhost:8003
AGENTOPS_APP_URL=http://localhost:3006
AGENTOPS_EXPORTER_ENDPOINT=http://otel-collector:4318/v1/traces

# Langfuse (선택적, Agent 품질 관리 필요 시에만)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

**참고**: AgentOps self-hosted 설정 가이드는 [AGENTOPS_SETUP.md](./AGENTOPS_SETUP.md)를 참조하세요.

### 2. 서비스 시작

```bash
# 모니터링 스택 빌드 및 시작
docker-compose up -d otel-collector prometheus grafana

# LiteLLM 재빌드 (AgentOps SDK 포함)
docker-compose build --no-cache litellm
docker-compose up -d litellm

# Backend BFF 재빌드 (Grafana/Langfuse 프록시 포함)
docker-compose build --no-cache backend
docker-compose up -d backend
```

### 3. 서비스 상태 확인

```bash
# E2E 테스트 실행
./scripts/test-monitoring-stack.sh
```

### 4. UI 접속

| 서비스 | URL | 계정 | 설명 |
|--------|-----|------|------|
| **Grafana** | http://localhost:3005 | admin/admin | LiteLLM 메트릭 대시보드 |
| **Prometheus** | http://localhost:9090 | - | 메트릭 쿼리 및 타겟 확인 |
| **Monitoring (Portal)** | http://localhost:3001/admin/monitoring | 관리자 | AgentOps 대시보드 + Grafana 탭 |
| **Langfuse** | http://localhost:3001/admin/langfuse | 관리자 | Agent 품질 관리 (선택적) |

---

## Architecture Details

### 1. LiteLLM → AgentOps (직접 연결)

LiteLLM은 SDK/콜백을 통해 AgentOps에 **직접 연결**됩니다. Prometheus와는 무관합니다.

**설정** (`litellm/config.yaml`):
```yaml
litellm_settings:
  success_callback: ["agentops"]
  agentops_api_key: os.environ/AGENTOPS_API_KEY
  default_tags:
    - project:agent-portal
    - environment:development
```

**추적 데이터**:
- LLM 호출 세션 (시작/종료)
- 모델별 비용 및 토큰 사용량
- 요청/응답 지연 시간
- 에이전트 실행 흐름 (세션 리플레이)

**Backend BFF의 역할**:
- `backend/app/services/agentops_adapter.py`: AgentOps API v4 클라이언트
- AgentOps self-hosted API (8003)를 직접 호출하여 ClickHouse 데이터 조회
- MariaDB는 사용하지 않음 (AgentOps가 ClickHouse에 저장)
- 엔드포인트: `/api/agentops/traces`, `/api/agentops/metrics` 등

### 2. Prometheus + Grafana (인프라 모니터링)

Prometheus는 **인프라 메트릭만** 수집합니다. LiteLLM은 포함되지 않습니다.

**설정** (`config/prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']
  
  # 향후 추가 예정: vLLM, 애플리케이션 메트릭
  # Note: LiteLLM은 AgentOps로 직접 연결 (SDK/콜백)
```

### 3. Prometheus

Prometheus는 OTEL Collector와 LiteLLM을 직접 스크랩합니다.

**설정** (`config/prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']
  
  - job_name: 'litellm'
    static_configs:
      - targets: ['litellm:4000']
    metrics_path: '/metrics'
```

### 4. Grafana

Grafana는 Prometheus를 데이터소스로 사용하여 대시보드를 표시합니다.

**자동 프로비저닝**:
- Datasource: `config/grafana-datasources.yaml`
- Dashboard: `config/grafana-dashboards/litellm-monitoring.json`

**대시보드 패널**:
1. Total Requests (5m)
2. Request Rate (1m)
3. Error Rate (%)
4. P95 Latency (ms)
5. Request Rate by Model
6. Latency by Model
7. Token Usage (5m)
8. Cost per Model (5m)

### 5. AgentOps SDK (Optional)

AgentOps는 LiteLLM에서 각 LLM 호출을 추적하고 비용/세션 리플레이를 제공합니다.

**활성화 방법** (`litellm/config.yaml`):
```yaml
litellm_settings:
  success_callback: ["agentops"]
  agentops_api_key: os.environ/AGENTOPS_API_KEY
```

**주의**: API 키가 없으면 주석 처리하여 LiteLLM이 정상 동작하도록 해야 합니다.

### 6. Langfuse (Optional)

Langfuse는 Agent 품질 관리를 위한 별도 도구입니다.

**접속**: Admin 네비게이션 → Langfuse 메뉴
**기능**: 프롬프트 비교, A/B 테스팅, 트레이스 분석

---

## Monitoring Screen

Portal의 `/admin/monitoring` 화면은 다음 탭으로 구성됩니다:

1. **Overview**: 메트릭 카드 (Total Cost, Total Events, Avg Latency, Fail Rate)
2. **Analytics**: 성능 메트릭 차트, Agent Flow Graph
3. **Replay**: 세션 리플레이 (AgentOps)
4. **Traces**: 트레이스 목록 및 상세 정보
5. **Grafana**: LiteLLM 모니터링 대시보드 (iframe)

**Grafana 탭**:
- Grafana 대시보드를 iframe으로 임베드
- Kiosk 모드로 메뉴 바 숨김
- 30초 자동 새로고침
- Backend BFF 프록시 (`/api/proxy/grafana/...`)를 통해 CORS 해결

---

## Troubleshooting

### 문제 1: LiteLLM 메트릭이 보이지 않음

**증상**: Grafana 대시보드가 비어 있음

**원인**: LLM 요청이 아직 없어 메트릭이 생성되지 않음

**해결**:
```bash
# 테스트 요청 전송
curl -X POST "http://localhost:4000/v1/chat/completions" \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-235b",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'

# 15초 대기 후 Prometheus 확인
curl http://localhost:4000/metrics | grep litellm_requests_total
```

### 문제 2: Prometheus Target이 Down 상태

**증상**: Prometheus UI에서 LiteLLM target이 "DOWN"

**원인**: LiteLLM 컨테이너가 실행되지 않거나 네트워크 연결 문제

**해결**:
```bash
# LiteLLM 상태 확인
docker-compose ps litellm
docker-compose logs litellm

# 재시작
docker-compose restart litellm
```

### 문제 3: Grafana 대시보드가 로드되지 않음

**증상**: Monitoring 화면의 Grafana 탭이 빈 화면

**원인**: Grafana 프록시 설정 오류 또는 대시보드 미생성

**해결**:
```bash
# 1. Grafana 상태 확인
curl http://localhost:3005/api/health

# 2. 대시보드 확인
curl -u admin:admin http://localhost:3005/api/search?type=dash-db

# 3. 대시보드가 없으면 재빌드
docker-compose down grafana
docker-compose up -d grafana
```

### 문제 4: AgentOps 콜백 실패

**증상**: LiteLLM 로그에 "AgentOps API error"

**원인**: `AGENTOPS_API_KEY`가 설정되지 않았거나 유효하지 않음

**해결**:
```yaml
# litellm/config.yaml에서 AgentOps 주석 처리
# litellm_settings:
#   success_callback: ["agentops"]
#   agentops_api_key: os.environ/AGENTOPS_API_KEY
```

### 문제 5: Langfuse iframe이 로드되지 않음

**증상**: `/admin/langfuse` 페이지가 빈 화면

**원인**: Langfuse 컨테이너 미실행 또는 프록시 오류

**해결**:
```bash
# Langfuse 상태 확인
docker-compose ps langfuse langfuse-db
docker-compose logs langfuse

# 프록시 확인
curl http://localhost:8000/api/proxy/langfuse/
```

---

## Performance Tuning

### Prometheus Retention

기본 retention은 15일입니다. 디스크 공간에 따라 조정:

```yaml
# docker-compose.yml
prometheus:
  command:
    - '--storage.tsdb.retention.time=30d'  # 30일로 연장
    - '--storage.tsdb.retention.size=10GB'  # 최대 10GB
```

### Grafana Refresh Rate

대시보드 자동 새로고침 간격 조정:

```
# URL 파라미터
?refresh=10s  # 10초
?refresh=1m   # 1분
?refresh=5m   # 5분
```

### OTEL Collector Batch Size

메트릭 처리 성능 튜닝:

```yaml
# config/otel-collector-config.yaml
processors:
  batch:
    timeout: 5s        # 5초마다 export (기본: 10s)
    send_batch_size: 512  # 배치 크기 감소 (기본: 1024)
```

---

## Production Deployment Checklist

- [ ] Grafana 기본 비밀번호 변경 (admin/admin)
- [ ] Prometheus retention 정책 설정 (디스크 관리)
- [ ] OTEL Collector 로그 레벨 조정 (info → warn)
- [ ] Grafana 알림 규칙 설정 (예: Error Rate > 5%)
- [ ] Langfuse 데이터베이스 백업 설정
- [ ] AgentOps API 키 환경 변수 설정 (필요 시)
- [ ] Prometheus 외부 접근 차단 (Kong Gateway 경유만)
- [ ] Grafana 외부 접근 차단 (BFF 프록시만)
- [ ] Health check 설정 (모든 서비스)
- [ ] Resource limits 설정 (CPU/Memory)

---

## References

- [LiteLLM Prometheus Docs](https://docs.litellm.ai/docs/proxy/prometheus)
- [OTEL Collector Config](https://opentelemetry.io/docs/collector/configuration/)
- [Prometheus Configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [AgentOps SDK](https://github.com/AgentOps-AI/agentops)

