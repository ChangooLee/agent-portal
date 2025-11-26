# AgentOps 데이터베이스 스키마 설정

## 2025-11-19: AgentOps 스키마 생성 및 500 에러 해결

### 문제 상황

**에러 메시지**:
```
Request URL: http://localhost:8000/api/agentops/metrics?project_id=default-project&start_time=...
Status Code: 500 Internal Server Error

Response: {"detail":"Failed to fetch metrics: (1146, \"Table 'agent_portal.trace_summaries' doesn't exist\")"}
```

**근본 원인**:
- AgentOps 관련 데이터베이스 테이블이 생성되지 않음
- `trace_summaries`, `otel_traces`, `agent_sessions`, `llm_calls` 테이블 누락
- 컬럼 누락: `cache_read_input_tokens`, `reasoning_tokens`

### 해결 방법

**1단계: 스키마 파일 생성** (`scripts/init-agentops-schema.sql`):

```sql
-- otel_traces: OpenTelemetry 트레이스 원본 데이터
CREATE TABLE IF NOT EXISTS otel_traces (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trace_id VARCHAR(32) NOT NULL,
    span_id VARCHAR(16) NOT NULL,
    parent_span_id VARCHAR(16),
    service_name VARCHAR(255),
    span_name VARCHAR(255),
    timestamp DATETIME NOT NULL,
    duration BIGINT,
    span_attributes LONGTEXT,  -- JSON
    resource_attributes LONGTEXT,  -- JSON
    project_id VARCHAR(255) NOT NULL DEFAULT 'default-project',
    -- ... (인덱스 생략)
);

-- trace_summaries: 트레이스 요약 정보
CREATE TABLE IF NOT EXISTS trace_summaries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trace_id VARCHAR(32) NOT NULL UNIQUE,
    project_id VARCHAR(255) NOT NULL DEFAULT 'default-project',
    service_name VARCHAR(255),
    root_span_name VARCHAR(255),
    start_time DATETIME NOT NULL,
    duration BIGINT,
    span_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0.0,
    total_tokens INT DEFAULT 0,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    cache_read_input_tokens INT DEFAULT 0,
    reasoning_tokens INT DEFAULT 0,
    model_name VARCHAR(255),
    status VARCHAR(50),
    -- ... (인덱스 생략)
);

-- llm_calls: LLM 호출 로그
CREATE TABLE IF NOT EXISTS llm_calls (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trace_id VARCHAR(32),
    project_id VARCHAR(255) NOT NULL DEFAULT 'default-project',
    model_name VARCHAR(255),
    provider VARCHAR(100),
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0.0,
    latency BIGINT,
    timestamp DATETIME NOT NULL,
    -- ... (인덱스 생략)
);

-- agent_sessions: 에이전트 세션 정보
CREATE TABLE IF NOT EXISTS agent_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    project_id VARCHAR(255) NOT NULL DEFAULT 'default-project',
    agent_name VARCHAR(255),
    status VARCHAR(50),
    start_time DATETIME NOT NULL,
    total_cost DECIMAL(10, 6) DEFAULT 0.0,
    total_tokens INT DEFAULT 0,
    -- ... (인덱스 생략)
);
```

**2단계: 스키마 적용**:

```bash
# MariaDB에 스키마 적용
docker-compose exec -T mariadb mariadb -uroot -p"${MARIADB_ROOT_PASSWORD:-rootpass}" agent_portal < scripts/init-agentops-schema.sql
```

**3단계: 누락 컬럼 추가** (초기 스키마에서 누락된 경우):

```bash
# cache_read_input_tokens, reasoning_tokens 컬럼 추가
docker-compose exec -T mariadb mariadb -uroot -p"${MARIADB_ROOT_PASSWORD:-rootpass}" agent_portal -e "
ALTER TABLE trace_summaries 
ADD COLUMN IF NOT EXISTS cache_read_input_tokens INT DEFAULT 0 AFTER completion_tokens,
ADD COLUMN IF NOT EXISTS reasoning_tokens INT DEFAULT 0 AFTER cache_read_input_tokens;
"
```

**4단계: 샘플 데이터 삽입** (테스트용):

스키마 파일에 샘플 데이터 INSERT 문 포함:
- 5개의 `trace_summaries` 레코드
- 5개의 `llm_calls` 레코드
- 3개의 `agent_sessions` 레코드

### 테스트 결과

**AgentOps Metrics API**:
```bash
curl -s "http://localhost:8000/api/agentops/metrics?project_id=default-project&start_time=2025-11-12T08:09:21.006Z&end_time=2025-11-19T08:09:21.006Z"

# 응답:
{
  "trace_count": 5,
  "span_count": 33,
  "error_count": 1,
  "total_cost": 0.105,
  "prompt_tokens": 7400,
  "completion_tokens": 3100,
  "cache_read_input_tokens": 0,
  "reasoning_tokens": 0
}
```

**AgentOps Cost Trend API**:
```bash
curl -s "http://localhost:8000/api/agentops/analytics/cost-trend?project_id=default-project&start_time=2025-11-12T08:09:21.006Z&end_time=2025-11-19T08:09:21.006Z&interval=day"

# 응답:
[
  {
    "timestamp": "2025-11-18",
    "cost": 0.012
  },
  {
    "timestamp": "2025-11-19",
    "cost": 0.093
  }
]
```

### 핵심 원칙

1. **데이터베이스 작업 시 스키마 확인 필수**:
   - ❌ 추측으로 쿼리 작성 → 컬럼 오류 발생
   - ✅ `DESCRIBE table_name;` 실행 후 쿼리 작성

2. **AgentOps 어댑터 개발 순서**:
   - 1단계: 스키마 생성 (`scripts/init-agentops-schema.sql`)
   - 2단계: 샘플 데이터 삽입 (테스트용)
   - 3단계: API 엔드포인트 개발 (`backend/app/routes/agentops.py`)
   - 4단계: 어댑터 구현 (`backend/app/services/agentops_adapter.py`)
   - 5단계: 프론트엔드 통합 (`webui/src/routes/(app)/admin/monitoring/+page.svelte`)

3. **스키마 변경 시 마이그레이션 필요**:
   - 테이블 추가/수정 시 `ALTER TABLE` 사용
   - 백업 필수 (`mysqldump` 또는 스냅샷)
   - 롤백 계획 수립

4. **샘플 데이터 중요성**:
   - 프론트엔드 개발 시 빈 대시보드가 아닌 샘플 데이터로 테스트
   - 엣지 케이스 포함 (에러, 0 값, 큰 숫자 등)
   - 시간 범위 다양화 (1시간 전, 1일 전, 1주일 전)

### 예방

**새 기능 개발 시 체크리스트**:
- [ ] 데이터베이스 스키마 파일 작성 (`scripts/init-*.sql`)
- [ ] 스키마 적용 (`docker-compose exec mariadb ...`)
- [ ] 샘플 데이터 삽입 (테스트용)
- [ ] API 엔드포인트 개발
- [ ] 실제 데이터로 테스트 (샘플 데이터로 먼저)
- [ ] 프론트엔드 통합
- [ ] 문서화 (README, API 문서)

**데이터베이스 스키마 변경 시**:
- [ ] 기존 데이터 백업
- [ ] 마이그레이션 스크립트 작성
- [ ] 개발 환경에서 테스트
- [ ] 프로덕션 배포 전 롤백 계획 수립

### 참고 파일

- `scripts/init-agentops-schema.sql` - AgentOps 스키마 정의
- `backend/app/services/agentops_adapter.py` - AgentOps 어댑터 (ClickHouse → MariaDB 변환)
- `backend/app/routes/agentops.py` - AgentOps API 엔드포인트
- `.cursor/rules/backend-api.mdc` - Backend API 개발 규칙 (데이터베이스 작업 패턴)

---

**학습 시점**: 2025-11-19  
**해결 시간**: 30분  
**재사용 가능성**: ⭐⭐⭐⭐⭐ (모든 데이터베이스 기반 기능 필수)

