# Monitoring Architecture Learning Patterns

## 2025-11-20: LiteLLM ↔ AgentOps 직접 연결 + Prometheus 인프라 모니터링 분리

### 아키텍처 선택 이유

**요청**: LiteLLM을 AgentOps에 직접 연결하고, Prometheus는 인프라 모니터링용으로 완전히 분리

**최종 아키텍처**:
```
1. LLM 모니터링 (직접 연결):
   LiteLLM (LLM Gateway)
     └─> AgentOps SDK (콜백/직접 연결)
           └─> AgentOps Dashboard (LLM 호출 추적, 비용, 세션)

2. 인프라 모니터링 (별도 스택):
   vLLM / 애플리케이션
     └─> OTEL Collector (메트릭 수집)
           └─> Prometheus (시계열 데이터 저장)
                 └─> Grafana (시각화)

3. Agent 품질 관리 (선택적):
   Langfuse (트레이스 분석, 프롬프트 관리)
```

**선택 이유**:
1. **명확한 역할 분리**: LiteLLM ↔ AgentOps는 SDK로 직접 연결. Prometheus와는 무관.
2. **AgentOps의 강점 활용**: 에이전트 실행 흐름, 세션 리플레이, 비용 추적에 최적화.
3. **Prometheus는 인프라용**: vLLM, 애플리케이션 메트릭 등 인프라 레벨만 담당.
4. **복잡도 감소**: LiteLLM을 Prometheus에 붙일 필요 없음. 직접 연결이 더 단순.

**트레이드오프**:
- AgentOps self-hosted 인스턴스 필요 (포트 8003, ClickHouse 사용)
- 하지만 폐쇄망 환경에서 완전히 독립적으로 운영 가능
- 설정이 단순하고 명확함

### LiteLLM + AgentOps 직접 연결 패턴

**구현 방법**:

1. **LiteLLM Dockerfile** (`litellm/Dockerfile`):
```dockerfile
RUN pip install --no-cache-dir 'litellm[proxy]' langfuse agentops
```

2. **LiteLLM Config** (`litellm/config.yaml`):
```yaml
general_settings:
  set_verbose: true
  master_key: os.environ/LITELLM_MASTER_KEY
  # Prometheus 메트릭 비활성화 (AgentOps로 직접 연결)

litellm_settings:
  success_callback: ["agentops"]  # AgentOps SDK로 직접 전송
  agentops_api_key: os.environ/AGENTOPS_API_KEY
  default_tags:
    - project:agent-portal
    - environment:development
```

3. **환경 변수** (`.env`):
```bash
AGENTOPS_API_KEY=your-agentops-api-key
```

**동작 방식**:
- LiteLLM이 LLM 호출을 받으면, AgentOps SDK가 자동으로 호출 데이터를 AgentOps로 전송
- 비용, 토큰, 지연 시간, 세션 정보 모두 AgentOps에 기록
- Prometheus와는 완전히 독립적

### Prometheus + Grafana 인프라 모니터링 패턴

**구현 방법**:

1. **Prometheus Config** (`config/prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']
  
  # 향후 추가 예정: vLLM, 애플리케이션 메트릭
  # Note: LiteLLM은 AgentOps로 직접 연결 (SDK/콜백)
```

2. **OTEL Collector Config** (`config/otel-collector-config.yaml`):
```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"

service:
  pipelines:
    metrics:
      receivers: [otlp]
      exporters: [prometheus]
```

**동작 방식**:
- OTEL Collector가 vLLM, 애플리케이션 메트릭을 수집 (OTLP 프로토콜)
- Prometheus가 OTEL Collector에서 메트릭을 스크랩
- Grafana가 Prometheus에서 데이터를 읽어 시각화
- LiteLLM과는 무관

### Langfuse 품질 관리 패턴

**구현 방법**:

1. **Admin 네비게이션** (`webui/src/routes/(app)/admin/+layout.svelte`):
```svelte
<a href="/admin/langfuse" class="...">
  <Star className="size-4" />
  <span>Langfuse</span>
</a>
```

2. **Langfuse 페이지** (`webui/src/routes/(app)/admin/langfuse/+page.svelte`):
```svelte
<iframe src="http://localhost:3003" title="Langfuse Dashboard" class="flex-1 w-full h-full" />
```

3. **리버스 프록시** (`backend/app/routes/proxy.py`):
```python
@router.api_route("/langfuse/{path:path}", ...)
async def proxy_langfuse(path: str, request: Request) -> Response:
    # X-Frame-Options 제거, CSP 설정
    ...
```

**동작 방식**:
- Langfuse는 별도 서비스로 실행 (포트 3003)
- Admin 패널에서 iframe으로 임베드
- 리버스 프록시로 CORS 문제 해결

### 학습 내용

**피드백**: ✅ 잘 잡았어

**성공 요인**:
1. **명확한 분리**: LiteLLM ↔ AgentOps (직접), Prometheus (인프라)
2. **단순한 설정**: LiteLLM에 AgentOps SDK 콜백만 추가
3. **역할 명확화**: 각 도구의 강점을 살림

**향후 적용**:
- 새로운 모니터링 요구사항이 있을 때, 역할별로 명확히 분리
- LLM 모니터링 = AgentOps (직접 연결)
- 인프라 모니터링 = Prometheus + Grafana
- 품질 관리 = Langfuse (선택적)

**참고**:
- `litellm/config.yaml` (line 30-42)
- `config/prometheus.yml` (line 12-25)
- `docs/MONITORING_SETUP.md`

---

## 2025-11-20: AgentOps Self-Hosted API 직접 조회로 백엔드 전환

### 문제 상황

**증상**: 모니터링 화면에 샘플 데이터만 표시됨 (실제 LLM 호출 데이터 없음)

**근본 원인**:
- LiteLLM → AgentOps SDK → AgentOps API (8003) → **ClickHouse**
- 모니터링 화면 → Backend BFF → **MariaDB (샘플 데이터)**
- 두 데이터베이스가 연결되지 않음 🚨

### 해결 방법

**선택**: `agentops_adapter.py`를 AgentOps API v4 클라이언트로 재작성

**기존 아키텍처** (잘못됨):
```
LiteLLM → AgentOps SDK → AgentOps API → ClickHouse
                                           ↓ (연결 없음)
Backend BFF → agentops_adapter → MariaDB (샘플 데이터)
               ↓
모니터링 화면 (빈 데이터)
```

**새 아키텍처** (올바름):
```
LiteLLM → AgentOps SDK → AgentOps API (8003) → ClickHouse
                            ↑ (v4 API 호출)
Backend BFF → agentops_adapter (httpx 클라이언트)
               ↓
모니터링 화면 (실제 데이터 ✅)
```

### 구현 세부사항

**1. AgentOps API v4 엔드포인트 활용**:

```python
# backend/app/services/agentops_adapter.py (재작성)
import httpx

class AgentOpsAdapter:
    def __init__(
        self,
        api_url: str = "http://localhost:8003",
        api_key: str = "da317188-e3be-4ecf-be31-7bb5d5f015e3"
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_traces(
        self, project_id: str, start_time: datetime, end_time: datetime, ...
    ) -> Dict[str, Any]:
        """AgentOps API v4 /traces/list/{project_id} 호출"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.api_url}/v4/traces/list/{project_id}",
                headers=self.headers,
                params={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "limit": size,
                    "offset": offset
                }
            )
            response.raise_for_status()
            return response.json()
```

**2. 주요 변경사항**:
- ❌ `aiomysql` 제거 (MariaDB 직접 조회 제거)
- ✅ `httpx.AsyncClient` 추가 (AgentOps API 호출)
- ❌ SQL 쿼리 제거 (ClickHouse는 AgentOps가 담당)
- ✅ AgentOps API v4 호환 응답 변환

**3. AgentOps API v4 엔드포인트**:
- `GET /v4/traces/list/{project_id}`: 트레이스 목록 + 메트릭
- `GET /v4/traces/detail/{trace_id}`: 트레이스 상세 (스팬 포함)
- `GET /v4/meterics/project/{project_id}`: 프로젝트 집계 메트릭

### 동작 확인

**테스트 curl**:
```bash
# 1. AgentOps API 직접 호출 (정상 작동)
curl -H "Authorization: Bearer da317188-e3be-4ecf-be31-7bb5d5f015e3" \
  "http://localhost:8003/v4/traces/list/default-project?start_time=2025-11-13T00:00:00Z&end_time=2025-11-20T23:59:59Z"

# 2. Backend BFF 호출 (AgentOps 데이터 반환)
curl "http://localhost:8000/api/agentops/traces?project_id=default-project&start_time=2025-11-13T04:54:01.972Z&end_time=2025-11-20T04:54:01.972Z"
```

### 학습 내용

**피드백**: ✅ 잘 잡았어

**성공 요인**:
1. **근본 원인 파악**: 두 DB가 연결되지 않은 것을 발견
2. **직접 API 호출**: MariaDB 우회, AgentOps API v4 직접 호출
3. **AgentOps 소스 분석**: `/v4/traces/list`, `/v4/traces/detail` 엔드포인트 발견

**향후 적용**:
- 외부 서비스 연동 시, 중간 DB 없이 직접 API 호출 고려
- AgentOps self-hosted는 ClickHouse에 데이터를 저장하므로, API를 통해서만 접근
- MariaDB는 Agent Portal 자체 데이터만 저장 (사용자, 설정 등)

**참고**:
- `backend/app/services/agentops_adapter.py` (전체 재작성)
- `external/agentops/app/api/agentops/api/routes/v4/__init__.py` (AgentOps API v4 라우트)
- `external/agentops/app/api/agentops/api/routes/v4/traces/views.py` (트레이스 뷰)
