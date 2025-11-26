# 2025-11-20: AgentOps Self-Hosting 설정 학습 패턴

## 배경

사용자로부터 AgentOps self-hosting 구조에 대한 상세한 설명을 받았다:
- **AgentOps.Next 리포지토리**를 self-host로 띄워야 함
- Dashboard (기본 3000), API (기본 8000)로 구성
- 대시보드에서 로컬 계정 생성 후 **내부용 API 키 발급**
- 발급된 키를 `AGENTOPS_API_KEY` 환경변수로 사용
- 폐쇄망 환경에서는 `AGENTOPS_API_ENDPOINT`, `AGENTOPS_APP_URL`, `AGENTOPS_EXPORTER_ENDPOINT` 설정 필요

## 구조 이해

### AgentOps Self-Hosting = 내부 API 키 발급

**핵심 개념**: Self-host한 AgentOps 인스턴스에서도 **API 키를 발급**받아 내부용(폐쇄망용)으로 사용하는 구조.

```
1. AgentOps 인스턴스 띄우기 (Supabase + ClickHouse + API + Dashboard)
2. Dashboard에서 계정 생성 (첫 계정 = 관리자)
3. Dashboard > Settings > API Keys에서 내부용 API 키 생성
4. LiteLLM에서 생성한 키를 AGENTOPS_API_KEY로 사용
```

### 폐쇄망 환경 설정

**필수 환경변수**:
```bash
AGENTOPS_API_KEY=ao-xxx-your-generated-key-xxx  # 대시보드에서 생성
AGENTOPS_API_ENDPOINT=http://agentops-api:8003  # 내부 API 서버
AGENTOPS_APP_URL=http://localhost:3006          # 내부 Dashboard
AGENTOPS_EXPORTER_ENDPOINT=http://otel-collector:4318/v1/traces  # OTEL 컬렉터
```

## 구현 결정

### 결정 1: 문서 중심 가이드 제공

**요청**: "agentops 화면을 어떻게 띄우면 되는지 알려주고"

**선택한 접근법**: 
- **전체 스택을 docker-compose에 추가하지 않음**
- 대신 **상세한 가이드 문서 제공** (`docs/AGENTOPS_SETUP.md`)
- 이유:
  - AgentOps는 Supabase + ClickHouse라는 복잡한 의존성 필요
  - 사용자가 원하는 것은 "어떻게 띄우는지 가이드" (실제 통합 X)
  - 프로젝트 복잡도 증가 방지

### 결정 2: LiteLLM 설정만 업데이트

**litellm/config.yaml**에 Self-hosted AgentOps 엔드포인트 추가:
```yaml
litellm_settings:
  success_callback: ["agentops"]
  agentops_api_key: os.environ/AGENTOPS_API_KEY
  agentops_endpoint: os.environ/AGENTOPS_API_ENDPOINT
  agentops_app_url: os.environ/AGENTOPS_APP_URL
  agentops_exporter_endpoint: os.environ/AGENTOPS_EXPORTER_ENDPOINT
```

**이유**:
- LiteLLM은 이미 AgentOps SDK를 사용하고 있음
- 엔드포인트만 내부 주소로 변경하면 즉시 사용 가능
- 추가 코드 변경 최소화

### 결정 3: 포트 할당

우리 프로젝트의 빈 포트 사용:
- **AgentOps Dashboard**: `3006`
- **AgentOps API**: `8003`

기존 포트와 충돌 방지:
- 3000-3005: 이미 사용 중
- 8000-8002: 이미 사용 중

## 학습 내용

**피드백**: ✅ 잘 이해했음

**성공 요인**:
1. **Self-hosting = 내부 API 키 발급**: 클라우드 API 키가 아닌, 내부에서 생성한 키를 사용
2. **폐쇄망 엔드포인트**: AGENTOPS_API_ENDPOINT 등을 내부 주소로 설정
3. **문서 우선**: 복잡한 통합보다는 명확한 가이드 제공

**향후 적용**:
- Self-hosting 서비스는 **전체 통합 전에 문서 제공 우선**
- 복잡한 의존성(Supabase, ClickHouse)이 있는 경우 **단계별 가이드** 중요
- LiteLLM 설정은 **엔드포인트만 추가**하면 즉시 사용 가능

**트레이드오프**:
- docker-compose에 AgentOps 전체 스택 미포함 (복잡도 감소)
- 대신 사용자가 별도로 AgentOps 인스턴스를 띄워야 함
- 하지만 문서가 충분히 상세하여 쉽게 따라할 수 있음

## 참고

- `docs/AGENTOPS_SETUP.md`: 완전한 self-hosting 가이드
- `litellm/config.yaml` (line 30-42): AgentOps 엔드포인트 설정
- `.env.example`: AgentOps 환경변수 템플릿
- `external/agentops/`: AgentOps 서브모듈 (참고용)

