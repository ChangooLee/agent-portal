# LiteLLM ↔ AgentOps 연동 완료 가이드

**작성일**: 2025-11-21  
**최종 업데이트**: 2025-11-21 13:50  
**상태**: ✅ 연동 완료 (데이터 전송 확인 필요)

## 최종 성공 결과

### ✅ 완료된 작업

1. **LiteLLM 설정**
   - AgentOps 콜백 활성화: `general_settings.success_callback: ["agentops"]`
   - AgentOps SDK 설치: v0.4.21
   - 초기화 로그 확인: `Initialized Success Callbacks - ['agentops']`
   - Chat Completion: ✅ 정상 작동

2. **AgentOps Self-Hosted 실행**
   - Supabase (20개 컨테이너): ✅ 정상 실행
   - AgentOps API (PID 15724): ✅ http://localhost:8003
   - AgentOps Dashboard (PID 15878): ✅ http://localhost:3006
   - 계정/프로젝트: ✅ 자동 생성 완료

3. **Supabase 데이터베이스 마이그레이션** (CRITICAL)
   - **org_invites 테이블 수정**:
     - `user_id` → `inviter_id`
     - `inviter` → `invitee_email`
     - `created_at` 컬럼 추가
   - **orgs 테이블 수정**:
     - `subscription_id` 컬럼 추가
   - **결과**: AgentOps API 인증 성공! JWT 토큰 획득 ✅

4. **Backend BFF 설정**
   - `AGENTOPS_API_URL`: `http://host.docker.internal:8003` (Docker 외부 AgentOps API)
   - `AGENTOPS_API_KEY`: `0c26af2a-8bac-4809-8b30-433ae3850608`
   - JWT 토큰 자동 갱신: ✅ 구현 완료
   - Backend 재시작: ✅ 새 설정 적용

5. **LiteLLM Config 수정**
   - `litellm/config.yaml`:
     ```yaml
     general_settings:
       success_callback: ["agentops"]  # ← 추가됨
     ```
   - LiteLLM 이미지 재빌드: ✅ 완료
   - 콜백 초기화 확인: ✅ 로그에 표시됨

## 주요 문제 및 해결

### 문제 1: LiteLLM `success_callback` 미설정

**증상**:
- `litellm.success_callback` 비어있음
- `Filtered callbacks: []` 로그

**근본 원인**:
- `litellm_settings`에만 설정했고 `general_settings`에 설정 안 함

**해결**:
```yaml
# litellm/config.yaml
general_settings:
  success_callback: ["agentops"]  # ← 이 부분 추가
  
litellm_settings:
  agentops_api_key: os.environ/AGENTOPS_API_KEY
  agentops_endpoint: os.environ/AGENTOPS_API_ENDPOINT
  agentops_app_url: os.environ/AGENTOPS_APP_URL
```

**학습**: LiteLLM Proxy는 `general_settings`의 `success_callback`을 읽음

### 문제 2: Backend `AGENTOPS_API_URL` 잘못된 설정

**증상**:
- Backend에서 AgentOps API 연결 실패
- `[Errno -2] Name or service not known`

**근본 원인**:
- `backend/app/config.py`: `AGENTOPS_API_URL = "http://agentops-api:8003"`
- AgentOps API는 Docker 외부 프로세스 (포트 8003)
- Docker 네트워크 이름 `agentops-api`가 존재하지 않음

**해결**:
```python
# backend/app/config.py
AGENTOPS_API_URL: str = "http://host.docker.internal:8003"  # Docker 외부 AgentOps API
```

**학습**: Docker 외부 서비스는 `host.docker.internal` 사용

### 문제 3: Supabase 데이터베이스 스키마 불일치 (CRITICAL)

**증상**:
- AgentOps API 인증 실패
- `(psycopg.errors.UndefinedColumn) column org_invites_1.inviter_id does not exist`
- `column org_invites_1.created_at does not exist`
- `column orgs_1.subscription_id does not exist`

**근본 원인**:
- AgentOps는 최신 마이그레이션 파일 기준으로 작성됨
- Supabase는 초기 스키마로 시작 (마이그레이션 미적용)

**해결 (단계별)**:
```bash
# 1. org_invites 테이블 수정
docker exec 72ddf3dd387b psql -U postgres -d postgres -c "
BEGIN;
ALTER TABLE public.org_invites DROP CONSTRAINT org_invites_pkey;
ALTER TABLE public.org_invites DROP CONSTRAINT org_invites_users_id_fkey;
ALTER TABLE public.org_invites RENAME COLUMN user_id TO inviter_id;
ALTER TABLE public.org_invites RENAME COLUMN inviter TO invitee_email;
ALTER TABLE public.org_invites ADD CONSTRAINT org_invites_pkey PRIMARY KEY (org_id, invitee_email);
CREATE INDEX idx_org_invites_inviter_id ON public.org_invites(inviter_id);
CREATE INDEX idx_org_invites_invitee_email ON public.org_invites(invitee_email);
ALTER TABLE public.org_invites ADD CONSTRAINT org_invites_inviter_id_fkey 
  FOREIGN KEY (inviter_id) REFERENCES auth.users(id) ON UPDATE CASCADE ON DELETE CASCADE;
ALTER TABLE public.org_invites ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
COMMIT;
"

# 2. orgs 테이블 수정
docker exec 72ddf3dd387b psql -U postgres -d postgres -c "
ALTER TABLE public.orgs ADD COLUMN subscription_id TEXT;
"
```

**학습**:
- AgentOps Self-Hosted는 Supabase 마이그레이션 필수
- `external/agentops/app/supabase/migrations/` 파일 참조
- 특히 `20250620000000_fix_org_invites.sql` 중요

### 문제 4: LiteLLM 이미지 재빌드 필요

**증상**:
- `litellm/config.yaml` 수정했지만 변경 안 됨

**근본 원인**:
- Docker 이미지에 config 파일이 복사됨 (`COPY config.yaml /app/config.yaml`)
- 로컬 파일 수정만으로는 컨테이너에 반영 안 됨

**해결**:
```bash
# 캐시 없이 재빌드
docker-compose build --no-cache litellm
docker-compose up -d litellm
```

**학습**: Docker 이미지에 복사된 파일은 재빌드 필요

## 접속 정보

### LiteLLM
- **URL**: http://localhost:4000
- **Docs**: http://localhost:4000/docs
- **Master Key**: `sk-1234`
- **AgentOps 콜백**: ✅ 활성화

### AgentOps Self-Hosted
- **API URL**: http://localhost:8003
- **Dashboard URL**: http://localhost:3006
- **API Key**: `0c26af2a-8bac-4809-8b30-433ae3850608`
- **Project ID**: `94909765-19bf-475a-b7da-d448ab90d072`
- **로그인**:
  - Email: `admin@agent-portal.local`
  - Password: `agentops-admin-password`

### Backend BFF
- **URL**: http://localhost:8000
- **Monitoring**: http://localhost:3001/admin/monitoring
- **AgentOps 엔드포인트**: `/api/agentops/*`

## 다음 단계 (테스트 필요)

### 1. LiteLLM → AgentOps 데이터 전송 확인
```bash
# LiteLLM 호출
curl -X POST http://localhost:4000/chat/completions \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-235b",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'

# LiteLLM 로그 확인
docker-compose logs litellm --since 1m | grep -i agentops

# AgentOps API 로그 확인
tail -50 /tmp/agentops-api.log | grep -E "trace|session|span"
```

### 2. AgentOps Dashboard에서 트레이스 확인
1. http://localhost:3006 접속
2. 로그인 (admin@agent-portal.local / agentops-admin-password)
3. 프로젝트 'agent-portal' 선택
4. Traces 탭에서 LiteLLM 호출 데이터 확인

### 3. Backend를 통한 메트릭 조회 확인
```bash
# Backend BFF를 통한 메트릭 조회
curl "http://localhost:8000/api/agentops/metrics?project_id=94909765-19bf-475a-b7da-d448ab90d072&start_time=$(date -u -v-1d +%Y-%m-%dT%H:%M:%SZ)&end_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Monitoring 화면 접속
open http://localhost:3001/admin/monitoring
```

## 트러블슈팅 가이드

### AgentOps API 인증 실패
```bash
# JWT 토큰 획득 테스트
curl -X POST http://localhost:8003/v3/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "0c26af2a-8bac-4809-8b30-433ae3850608"}'

# 기대 출력:
# {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "project_id": "..."}

# 실패 시:
# 1. Supabase 데이터베이스 마이그레이션 확인
# 2. projects 테이블에 API 키 존재 확인
#    docker exec 72ddf3dd387b psql -U postgres -d postgres -c "SELECT api_key FROM public.projects;"
```

### LiteLLM 콜백 미작동
```bash
# 1. 콜백 초기화 확인
docker-compose logs litellm | grep "Initialized Success Callbacks"
# 기대: "Initialized Success Callbacks - ['agentops']"

# 2. 환경 변수 확인
docker-compose exec litellm env | grep AGENTOPS

# 3. LiteLLM 이미지 재빌드
docker-compose build --no-cache litellm
docker-compose up -d litellm
```

### Backend 연결 실패
```bash
# 1. AgentOps API Health Check
curl http://localhost:8003/health
# 기대: {"message":"Server Up"}

# 2. Backend 환경 변수 확인
docker-compose exec backend env | grep AGENTOPS

# 3. Backend 로그 확인
docker-compose logs backend --tail 50 | grep -i agentops

# 4. Backend 재시작
docker-compose restart backend
```

## 참고 문서

- AgentOps Self-Hosted: `.cursor/learnings/agentops-deployment-complete-guide.md`
- LiteLLM 통합: `.cursor/learnings/litellm-integration.md`
- Backend API 규칙: `.cursor/rules/backend-api.mdc`
- AGENTS.md: Section 3.3 (AgentOps Self-Hosted API 통합)

## 핵심 학습

1. **LiteLLM Proxy 설정**: `general_settings.success_callback` 사용 필수
2. **Docker 네트워킹**: 외부 서비스는 `host.docker.internal` 사용
3. **Supabase 마이그레이션**: AgentOps 사용 전 마이그레이션 필수 적용
4. **Docker 이미지 재빌드**: 설정 파일 변경 시 재빌드 필요
5. **JWT 인증**: AgentOps는 API 키 → JWT 토큰 변환 후 사용
6. **데이터베이스 스키마 검증**: Self-Hosted 서비스는 마이그레이션 상태 확인 필수

---

**작성자**: AI Agent (Claude)  
**버전**: 1.0  
**최종 테스트**: 2025-11-21 13:50 (AgentOps JWT 인증 성공)


