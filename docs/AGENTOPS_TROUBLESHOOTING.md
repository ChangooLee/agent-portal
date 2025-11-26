# AgentOps 트러블슈팅 가이드

> **목적**: AgentOps self-hosted 설정 시 발생하는 문제 해결 및 재발 방지

---

## 초기 설정 절차

### 1. Supabase 시작

```bash
cd external/agentops
supabase start
```

**확인사항**:
- Database URL: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- API URL: `http://127.0.0.1:54321`

### 2. AgentOps 환경 변수 설정

`external/agentops/app/api/.env`:
```bash
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_HOST=127.0.0.1
SUPABASE_PORT=54322
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=postgres
SUPABASE_SSLMODE=disable
```

### 3. 사용자 및 프로젝트 생성

```bash
cd /path/to/agent-portal
bash scripts/setup-agentops-apikey.sh
```

또는 수동으로:

```bash
cd /path/to/agent-portal
docker cp scripts/setup-agentops.sql supabase_db_agentops:/tmp/setup.sql
docker exec supabase_db_agentops psql -U postgres -d postgres -f /tmp/setup.sql
```

### 4. 생성된 정보 확인

```bash
docker exec supabase_db_agentops psql -U postgres -d postgres -c \
  "SELECT p.id as project_id, p.name, p.api_key FROM public.projects p WHERE p.name = 'agent-portal';"
```

### 5. .env 파일 업데이트

프로젝트 루트의 `.env`:
```bash
AGENTOPS_API_KEY=<생성된 API Key>
AGENTOPS_API_ENDPOINT=http://host.docker.internal:8003
AGENTOPS_APP_URL=http://localhost:3006
```

### 6. Backend 재시작

```bash
docker-compose restart backend
```

---

## 주요 문제 및 해결 방법

### 문제 1: Supabase 리셋 후 데이터 손실

**증상**:
- `supabase db reset` 실행 후 admin 사용자 및 프로젝트가 삭제됨
- AgentOps API가 404 또는 401 에러 반환

**원인**:
- Supabase 리셋은 모든 데이터를 초기화함
- AgentOps 마이그레이션만 적용되고 초기 데이터는 없음

**해결 방법**:
1. `scripts/setup-agentops-apikey.sh` 재실행
2. 또는 `scripts/setup-agentops.sql` 직접 실행
3. `.env` 파일의 `AGENTOPS_API_KEY` 업데이트
4. Backend 재시작

**재발 방지**:
- Supabase 리셋 전 백업:
  ```bash
  docker exec supabase_db_agentops pg_dump -U postgres postgres > agentops_backup.sql
  ```
- 리셋 후 복원:
  ```bash
  docker exec -i supabase_db_agentops psql -U postgres postgres < agentops_backup.sql
  ```

---

### 문제 2: AgentOps API 인증 실패 (401 Unauthorized)

**증상**:
- Backend API 호출 시 `401 Unauthorized`
- Backend 로그에 "User is not authenticated" 에러

**원인**:
- AgentOps는 Bearer 토큰이 아닌 **쿠키 기반 세션 인증** 사용
- `backend/app/services/agentops_adapter.py`가 로그인하여 세션 쿠키 획득 필요

**해결 방법**:
1. Backend BFF가 자동으로 AgentOps에 로그인하도록 구현됨
2. 로그인 실패 시 Backend 로그 확인:
   ```bash
   docker logs agent-portal-backend-1 --tail 50 | grep "AgentOps"
   ```
3. 쿠키 이름 확인 (`session_id`)

**재발 방지**:
- Backend BFF의 `_ensure_authenticated()` 메서드가 자동으로 로그인 처리
- 세션 만료 시 자동 재로그인

---

### 문제 3: PostgreSQL 연결 오류 (포트 에러)

**증상**:
- AgentOps API 시작 시 `ValueError: invalid literal for int() with base 10: 'None'`

**원인**:
- `SUPABASE_PORT` 환경 변수 누락

**해결 방법**:
1. `external/agentops/app/api/.env`에 환경 변수 추가:
   ```bash
   SUPABASE_HOST=127.0.0.1
   SUPABASE_PORT=54322
   SUPABASE_DATABASE=postgres
   SUPABASE_USER=postgres
   SUPABASE_PASSWORD=postgres
   ```
2. AgentOps API 재시작

**재발 방지**:
- `.env.example` 파일에 모든 필수 변수 명시
- Supabase 시작 후 자동으로 환경 변수 설정하는 스크립트 작성

---

### 문제 4: ClickHouse 연결 필요

**증상**:
- AgentOps API가 메트릭 데이터 조회 실패
- ClickHouse 관련 에러

**원인**:
- AgentOps는 PostgreSQL (메타데이터) + ClickHouse (텔레메트리) 구조
- 현재 설정은 PostgreSQL만 사용

**해결 방법**:
1. ClickHouse 컨테이너 추가 (TODO)
2. 또는 AgentOps SDK를 통해 LiteLLM에서 직접 데이터 전송

**재발 방지**:
- AgentOps 전체 스택 설정 문서화 필요
- `docker-compose.yml`에 ClickHouse 추가

---

### 문제 5: 마이그레이션 불완전

**증상**:
- `relation "public.org_invites" does not exist`
- `column "role" of relation "user_orgs" does not exist`

**원인**:
- Supabase 마이그레이션 파일이 불완전하거나 누락됨
- AgentOps 버전과 마이그레이션 파일 불일치

**해결 방법**:
1. 최신 AgentOps 마이그레이션 확인:
   ```bash
   ls -la external/agentops/app/supabase/migrations/
   ```
2. 누락된 마이그레이션 수동 적용:
   ```bash
   docker exec supabase_db_agentops psql -U postgres -d postgres -f /tmp/migration.sql
   ```
3. 또는 AgentOps Dashboard (http://localhost:3006)에서 직접 설정

**재발 방지**:
- Supabase 마이그레이션 상태 확인 스크립트 작성
- AgentOps 버전 고정

---

## 체크리스트

### 초기 설정 시

- [ ] Supabase 실행 확인 (`supabase status`)
- [ ] PostgreSQL 환경 변수 설정 (`SUPABASE_HOST`, `SUPABASE_PORT` 등)
- [ ] 사용자 및 프로젝트 생성 (`setup-agentops-apikey.sh`)
- [ ] API Key를 `.env`에 추가
- [ ] Backend 재시작 확인

### Supabase 리셋 시 (⚠️ 위험)

- [ ] **백업 필수**: `pg_dump`로 데이터 백업
- [ ] 리셋 실행: `supabase db reset`
- [ ] 백업 복원 또는 `setup-agentops-apikey.sh` 재실행
- [ ] `.env` 업데이트 확인
- [ ] Backend 재시작

### 트러블슈팅 시

- [ ] Backend 로그 확인: `docker logs agent-portal-backend-1`
- [ ] AgentOps API 로그 확인: `tail -f external/agentops/app/api/agentops_api.log`
- [ ] Supabase 상태 확인: `supabase status`
- [ ] 데이터베이스 확인:
  ```bash
  docker exec supabase_db_agentops psql -U postgres -d postgres -c "SELECT * FROM public.projects;"
  ```

---

## 참고 자료

- [AgentOps 설정 가이드](./AGENTOPS_SETUP.md)
- [Supabase 로컬 개발 가이드](https://supabase.com/docs/guides/cli/local-development)
- [AgentOps 마이그레이션 파일](../external/agentops/app/supabase/migrations/)
- [자동 설정 스크립트](../scripts/setup-agentops-apikey.sh)

---

**마지막 업데이트**: 2025-11-20  
**버전**: 1.0



