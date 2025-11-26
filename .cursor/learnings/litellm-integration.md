# LiteLLM 통합 학습 내용

## 2025-11-21: AgentOps Self-Hosted OTLP 통합 시도 및 제한사항 (최종)

### 작업 목표

LiteLLM의 트레이스를 Self-Hosted AgentOps로 전송하여 LLM 호출 모니터링

### 시도한 방법 및 결과

#### 방법 1: LiteLLM AgentOps Callback 사용 ❌

**시도**:
- `litellm/config.yaml`에 `success_callback: ["agentops"]` 설정
- 환경 변수로 OTLP endpoint 설정:
  - `AGENTOPS_EXPORTER_ENDPOINT=http://agentops-otel-collector:4318/v1/traces`
  - `OTEL_EXPORTER_OTLP_ENDPOINT=http://agentops-otel-collector:4318`
  - `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://agentops-otel-collector:4318/v1/traces`
  - `OTEL_SERVICE_NAME=litellm-proxy`

**결과**: **실패**
```
OTEL config settings=OpenTelemetryConfig(exporter='otlp_http', endpoint='https://otlp.agentops.cloud/v1/traces', ...)
Failed to export span batch code: 401, reason: Unauthorized
```

**원인**: 
- LiteLLM의 AgentOps callback은 **하드코딩된 AgentOps Cloud endpoint** 사용
- 환경 변수를 무시하고 항상 `https://otlp.agentops.cloud/v1/traces`로 전송
- Self-hosted AgentOps로 변경 불가

#### 방법 2: OTLP 인프라 구축 ✅ (부분 성공)

**구현**:
1. ClickHouse 포트 충돌 해결 (9000 → 9002)
2. `docker-compose.yml`에 AgentOps 전용 서비스 추가:
   - `agentops-clickhouse`: Time-series 데이터베이스 (포트 9002)
   - `agentops-otel-collector`: OTLP Collector (포트 4317/4318)
3. OTLP Collector 설정 (ClickHouse 연동, 자동 테이블 생성)
4. LiteLLM `config.yaml`에서 AgentOps callback 제거

**결과**: **인프라 구축 성공**, **트레이스 수집 실패**
```
✅ ClickHouse 정상 실행 (포트 9002)
✅ OTLP Collector 정상 실행 (포트 4317/4318)
✅ 테이블 자동 생성 (otel_traces, otel_traces_trace_id_ts, ...)
❌ LiteLLM에서 트레이스 전송 안 됨 (OpenTelemetry 수동 활성화 필요)
```

#### 방법 3: OpenTelemetry 초기화 스크립트 ⚠️ (미완료)

**시도**:
- `litellm/init_otel.py`: OpenTelemetry TracerProvider 초기화 스크립트
- `litellm/start.sh`: LiteLLM 시작 전 OpenTelemetry 초기화
- `litellm/Dockerfile`: 스크립트 포함 및 권한 설정

**문제**: 
- LiteLLM Proxy는 **OpenTelemetry를 기본 활성화하지 않음**
- 환경 변수만으로는 충분하지 않으며, **LiteLLM 내부 코드 수정 필요**
- 초기화 스크립트는 LiteLLM 프로세스 전에 실행되어 span capture 불가

### 핵심 제한사항

1. **LiteLLM AgentOps Callback은 Cloud 전용**:
   - Endpoint가 하드코딩됨: `https://otlp.agentops.cloud/v1/traces`
   - 환경 변수 무시
   - Self-hosted 지원 없음

2. **LiteLLM OpenTelemetry는 수동 활성화 필요**:
   - 환경 변수만으로는 충분하지 않음
   - LiteLLM 소스코드 수정 또는 custom callback 필요

3. **Self-Hosted AgentOps OTLP 제한**:
   - OpenTelemetry Collector는 정상 동작
   - ClickHouse에 트레이스 저장 가능
   - **문제는 LiteLLM → OTLP Collector 연결**

### 대안 솔루션

**Option A: Langfuse Callback 사용** (✅ 권장)
- LiteLLM의 Langfuse callback은 이미 설정 가능
- `litellm/config.yaml`:
  ```yaml
  litellm_settings:
    success_callback: ["langfuse"]
    langfuse_public_key: os.environ/LANGFUSE_PUBLIC_KEY
    langfuse_secret_key: os.environ/LANGFUSE_SECRET_KEY
    langfuse_host: http://langfuse:3000
  ```
- Langfuse가 트레이스를 캡처하고 저장
- 별도 Langfuse → AgentOps 통합 필요 (추후 구현)

**Option B: LiteLLM Custom Callback** (⚠️ 개발 필요)
- LiteLLM의 custom callback 기능 활용
- Python 코드로 직접 OTLP Collector로 span 전송
- 참고: `litellm.integrations.custom_logger.CustomLogger`

**Option C: LiteLLM Fork** (❌ 비권장)
- LiteLLM 소스코드 포크
- AgentOps callback endpoint를 환경 변수로 변경
- 유지보수 부담 증가

### 완료된 작업

1. ✅ ClickHouse 포트 충돌 해결 (`9000` → `9002`)
2. ✅ `docker-compose.yml`에 AgentOps OTLP 인프라 추가:
   ```yaml
   agentops-clickhouse:
     image: clickhouse/clickhouse-server:24.12
     ports:
       - "9002:9000"
       - "8124:8123"
   
   agentops-otel-collector:
     build: ./external/agentops/app/opentelemetry-collector
     ports:
       - "4317:4317"  # otlp grpc
       - "4318:4318"  # otlp http
     environment:
       - CLICKHOUSE_ENDPOINT=clickhouse://agentops-clickhouse:9000
   ```
3. ✅ OTLP Collector 설정 수정 (`create_schema: true`)
4. ✅ LiteLLM `config.yaml`에서 AgentOps callback 제거
5. ✅ 환경 변수 설정:
   - `OTEL_EXPORTER_OTLP_ENDPOINT=http://agentops-otel-collector:4318`
   - `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://agentops-otel-collector:4318/v1/traces`
   - `OTEL_SERVICE_NAME=litellm-proxy`

### 검증된 인프라

```bash
# ClickHouse 연결 테스트
$ docker exec agentops-clickhouse clickhouse-client --query "SELECT version()"
24.12.1.1616

# 테이블 생성 확인
$ docker exec agentops-clickhouse clickhouse-client --query "SHOW TABLES FROM otel_2"
otel_logs
otel_logs_events
otel_metrics_exponential_histogram
otel_metrics_gauge
otel_metrics_histogram
otel_metrics_summary
otel_traces                  ← 트레이스 저장 테이블
otel_traces_trace_id_ts      ← 인덱스 테이블

# OTLP Collector 상태 확인
$ docker logs agentops-otel-collector --tail 10
Everything is ready. Begin running and processing data.
```

### 학습 내용

1. **LiteLLM의 관측성 callback은 Cloud 전용 제한**:
   - AgentOps, Helicone 등은 자사 클라우드 서비스 전용
   - Self-hosted 지원은 제한적

2. **OpenTelemetry 환경 변수만으로는 부족**:
   - `OTEL_EXPORTER_OTLP_ENDPOINT` 설정만으로는 자동 활성화 안 됨
   - TracerProvider 초기화 코드 필요

3. **OTLP 인프라는 독립적으로 동작**:
   - Collector와 ClickHouse는 정상 작동
   - 문제는 클라이언트 (LiteLLM) 연결

4. **Langfuse가 현실적 대안**:
   - LiteLLM이 공식 지원
   - Self-hosted 가능
   - 추후 Langfuse → AgentOps 데이터 파이프라인 구축 가능

### 다음 단계

**즉시 실행 가능** (✅ 권장):
1. Langfuse 서비스 설정 및 시작
2. LiteLLM `config.yaml`에서 Langfuse callback 활성화
3. LiteLLM 재시작 및 트레이스 확인

**중장기 계획** (⚠️ 개발 필요):
1. Langfuse → AgentOps 데이터 파이프라인 구축
2. 또는 LiteLLM Custom Callback 개발

### 관련 파일

- `docker-compose.yml` (line 313-351): AgentOps ClickHouse 및 OTLP Collector 서비스
- `external/agentops/app/opentelemetry-collector/config/base.yaml` (line 103-110): OTLP Collector ClickHouse exporter 설정
- `external/agentops/app/opentelemetry-collector/compose.yaml` (line 18-26): ClickHouse 포트 변경 (9002)
- `litellm/config.yaml` (line 1-18): AgentOps callback 제거, OpenTelemetry 환경 변수 안내
- `litellm/Dockerfile` (line 1-22): OpenTelemetry SDK 포함, 초기화 스크립트 추가
- `.env` (lines 추가): OTEL 환경 변수

### 참고 자료

- [LiteLLM Custom Logger](https://docs.litellm.ai/docs/observability/custom_callback)
- [OpenTelemetry Python SDK](https://opentelemetry-python.readthedocs.io/en/latest/)
- [Langfuse Self-Hosted](https://langfuse.com/docs/deployment/self-host)

---

## 2025-11-21: AgentOps API 인증 구조 분석 및 최종 해결

### 발견 사항

**AgentOps API 인증 방식**:
1. **v4 읽기 엔드포인트** (`/v4/traces/list/{project_id}`):
   - 인증: **세션 쿠키** (AuthenticatedRoute 미들웨어)
   - 용도: AgentOps Dashboard UI 전용
   - `request.state.session.user_id` 필요
   - JWT Bearer 토큰 사용 불가 ❌

2. **v1/v2 쓰기 엔드포인트** (`/v1/sessions`, `/v2/sessions`):
   - 인증: **API 키** (`X-Agentops-Auth` 헤더)
   - 용도: SDK/LiteLLM이 트레이스 데이터 전송
   - JWT Bearer 토큰도 가능 (v3에서 발급)

3. **v3 JWT 인증** (`/v3/auth/token`):
   - API 키 → JWT 토큰 변환
   - JWT는 v1/v2 POST 엔드포인트에 사용 가능
   - v4 읽기 엔드포인트에는 사용 불가

**LiteLLM AgentOps 콜백 제한**:
- LiteLLM의 AgentOps 통합은 **AgentOps 클라우드 전용**
- OTLP 엔드포인트: `https://otlp.agentops.cloud/v1/traces`
- Self-hosted AgentOps는 OpenTelemetry 엔드포인트 미제공
- 인증 실패: `Failed to export span batch code: 401, reason: Unauthorized`

**최종 해결 방안 (재검토 후 원복 ⚠️)**:
1. **iframe 임베드 방식 시도 → 실패**:
   - AgentOps Dashboard는 **별도 로그인 절차** 필요
   - 계정 생성/관리 복잡도 증가
   - 사용자 경험 저하 (이중 로그인)

2. **원래 구현 유지 (Chart.js 기반)**:
   - Frontend: 기존 Chart.js 기반 UI 유지
   - Backend BFF: AgentOps Adapter (v4 API 호출)
   - **남은 문제**: v4 API 세션 쿠키 인증 해결 필요

3. **LiteLLM**: 별도 관측성 도구 사용 (Langfuse, Helicone 등)
   - AgentOps 직접 연동 불가 (클라우드 전용)
   - OpenTelemetry → AgentOps 변환 로직 없음

**핵심 교훈**:
- AgentOps v4 API는 Dashboard UI용 (세션 쿠키 인증)
- Backend BFF는 v4 읽기 엔드포인트를 직접 호출할 수 없음
- LiteLLM → AgentOps 직접 연동은 클라우드 전용
- Self-hosted AgentOps는 Dashboard iframe 임베드 방식 권장

**참고 파일**:
- `external/agentops/app/api/agentops/api/routes/v4/traces/views.py` (line 126-145: BaseTraceView, 세션 쿠키 인증)
- `external/agentops/app/api/agentops/auth/middleware.py` (line 32-49: AuthenticatedRoute, 쿠키 확인)
- `external/agentops/app/api/agentops/api/auth.py` (line 96-122: get_jwt_token, Bearer 토큰)
- `external/agentops/app/api/agentops/api/routes/v1.py` (line 22-23: X-Agentops-Auth 헤더)

---

# LiteLLM 통합 학습 내용

## 2025-11-19: LiteLLM 단일 게이트웨이 구축 완료

**작업**: LiteLLM을 단일 LLM 게이트웨이로 설정하여 모든 컴포넌트 통합

**목표**: 
- Open-WebUI, Langflow, Flowise, LangGraph, Backend BFF가 모두 LiteLLM을 통해 LLM 사용
- OpenRouter를 통한 Qwen 235B 모델 사용
- 단일 설정 파일(`litellm/config.yaml`)로 모든 LLM 관리

### 적용한 방법

#### 1. Docker 볼륨 마운트 이슈 해결

**문제**: LiteLLM Docker 이미지가 마운트된 설정 파일을 무시하고 내장 Azure 예제 설정 사용

**해결**: Dockerfile로 직접 빌드하여 설정 완전 제어

**구현**:
```dockerfile
# litellm/Dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir 'litellm[proxy]'
COPY config.yaml /app/config.yaml
EXPOSE 4000
CMD ["litellm", "--config", "/app/config.yaml", "--port", "4000", "--detailed_debug"]
```

**학습**: 
- Docker 이미지의 entrypoint/cmd가 설정 파일 로드를 우회할 수 있음
- 로컬 빌드로 전체 제어 가능
- `.gitignore`에서 제외하여 Git 추적

#### 2. Langfuse 콜백 선택적 비활성화

**문제**: Langfuse Python SDK 미설치 상태에서 LiteLLM 시작 실패

**해결**: `litellm/config.yaml`에서 Langfuse 콜백 주석 처리

**구현**:
```yaml
# Observability: Langfuse integration (disabled until Langfuse is set up)
# litellm_settings:
#   success_callback: ["langfuse"]
#   langfuse_public_key: os.environ/LANGFUSE_PUBLIC_KEY
#   langfuse_secret_key: os.environ/LANGFUSE_SECRET_KEY
#   langfuse_host: os.environ/LANGFUSE_HOST
```

**학습**:
- Graceful degradation 전략: 선택적 기능은 주석 처리
- 나중에 Langfuse 설정 완료 시 주석 해제 가능
- 에러 로그를 통한 근본 원인 파악 중요 ("No module named 'langfuse'")

#### 3. LiteLLM 서비스 클라이언트 인증 추가

**문제**: Backend BFF에서 LiteLLM API 호출 시 인증 에러

**해결**: Authorization 헤더 추가

**구현**:
```python
# backend/app/services/litellm_service.py
class LiteLLMService:
    def __init__(self):
        self.base_url = getattr(settings, 'LITELLM_HOST', 'http://litellm:4000')
        self.api_key = getattr(settings, 'LITELLM_MASTER_KEY', 'sk-1234')
    
    async def list_models(self) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/v1/models", headers=headers)
            # ...
```

**학습**:
- LiteLLM은 `master_key`를 통한 인증 필수
- 모든 API 호출에 `Authorization: Bearer <key>` 헤더 포함
- `config.py`에 `LITELLM_MASTER_KEY` 설정 필요

#### 4. 환경 변수 계층 구조

**최종 구조**:
```
.env (root)
  ├─ LITELLM_MASTER_KEY
  ├─ OPENROUTER_API_KEY
  └─ OPENROUTER_MODEL_NAME
       ↓
docker-compose.yml
  ├─ litellm: env_file + environment
  ├─ webui: OPENAI_API_BASE_URLS, OPENAI_API_KEYS
  ├─ backend: env_file (config.py에서 로드)
  ├─ langflow: LANGFLOW_DEFAULT_OPENAI_*
  └─ flowise: OPENAI_API_BASE, OPENAI_API_KEY
```

**학습**:
- `.env` 파일은 Docker Compose `env_file`로 로드
- 중요 변수는 `environment`에 명시적으로 전달
- 각 서비스가 예상하는 환경 변수 이름 차이 주의
  - Open-WebUI: `OPENAI_API_BASE_URLS` (복수형)
  - Langflow: `LANGFLOW_DEFAULT_OPENAI_BASE_URL` (접두사 + 단수형)
  - Flowise: `OPENAI_API_BASE` (단수형)

### 성과

✅ **성공적으로 구현**:
- LiteLLM 정상 실행 (포트 4000)
- OpenRouter를 통한 Qwen 235B 모델 응답 확인
- Backend BFF Chat API 정상 동작
- 비용 계산 정상 (0.00001086 USD per request)
- Open-WebUI, Langflow, Flowise 환경 변수 설정 완료

✅ **테스트 결과**:
```json
{
  "id": "gen-1763526219-miYWclMluAKRpml4aqeS",
  "model": "qwen/qwen3-235b-a22b-2507",
  "usage": {
    "total_tokens": 30,
    "cost": 0.00001086
  },
  "provider": "DeepInfra"
}
```

### 재사용 가능한 패턴

#### 패턴 1: Docker 로컬 빌드로 설정 제어

**상황**: 공식 이미지가 설정 파일을 제대로 로드하지 않는 경우

**해결**:
1. `<service>/Dockerfile` 생성
2. 설정 파일 `COPY`
3. `docker-compose.yml`에서 `build: ./<service>` 사용

#### 패턴 2: 선택적 의존성 Graceful Degradation

**상황**: 선택적 기능(Langfuse 등)의 SDK가 설치되지 않은 경우

**해결**:
```yaml
# 주석 처리로 비활성화
# litellm_settings:
#   success_callback: ["langfuse"]
```

또는 Python 코드에서:
```python
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
```

#### 패턴 3: API 인증 헤더 일관성

**상황**: 외부 API 호출 시 인증 필요

**해결**:
```python
headers = {
    "Authorization": f"Bearer {self.api_key}",
    "Content-Type": "application/json"
}
async with httpx.AsyncClient(timeout=60.0) as client:
    response = await client.post(url, json=payload, headers=headers)
```

### 트러블슈팅 체크리스트

- [ ] LiteLLM 컨테이너 실행 확인 (`docker-compose ps litellm`)
- [ ] LiteLLM 로그 확인 (`docker-compose logs litellm`)
- [ ] 헬스체크 성공 (`curl http://localhost:4000/health -H "Authorization: Bearer sk-1234"`)
- [ ] 모델 목록 조회 (`curl http://localhost:4000/v1/models -H "Authorization: Bearer sk-1234"`)
- [ ] Backend BFF 연동 테스트 (`curl http://localhost:8000/chat/completions ...`)
- [ ] `.env` 파일에 `LITELLM_MASTER_KEY`, `OPENROUTER_API_KEY` 존재 확인
- [ ] `backend/app/config.py`에 `LITELLM_MASTER_KEY` 정의 확인

### 관련 문서

- `docs/LITELLM_SETUP.md` - LiteLLM 설정 가이드
- `litellm/Dockerfile` - LiteLLM Docker 빌드 파일
- `litellm/config.yaml` - LiteLLM 설정 파일 (SSOT)
- `backend/app/services/litellm_service.py` - LiteLLM 서비스 클라이언트
- `backend/app/config.py` - Backend 설정 (LITELLM_MASTER_KEY 정의)

### 다음 단계

1. Langfuse 설정 및 콜백 활성화
2. Open-WebUI에서 실제 채팅 테스트
3. Langflow/Flowise에서 LiteLLM 모델 사용 테스트
4. 비용 모니터링 대시보드 연동

---

**참고 자료**:
- [LiteLLM 공식 문서](https://docs.litellm.ai/)
- [OpenRouter API 문서](https://openrouter.ai/docs)

