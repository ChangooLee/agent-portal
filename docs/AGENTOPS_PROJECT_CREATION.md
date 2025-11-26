# AgentOps 프로젝트 생성 로직 분석

> **분석 일자**: 2025-11-20  
> **분석 대상**: `external/agentops` Git submodule  
> **목적**: 프로젝트 생성 시 필요한 데이터 구조 및 로직 이해

---

## 1. 프로젝트 생성 흐름

### API 엔드포인트

**위치**: `external/agentops/app/api/agentops/opsboard/views/projects.py:73-104`

**함수**: `create_project()`

```python
def create_project(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
    body: ProjectCreateSchema,
) -> ProjectResponse:
    """
    Create a new project in an organization.
    User must be an admin or owner of the organization.
    """
    # 1. 조직 조회
    org = OrgModel.get_by_id(orm, body.org_id)
    
    # 2. 권한 검증
    if not org or not org.is_user_admin_or_owner(request.state.session.user_id):
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # 3. 프로젝트 제한 확인
    if org.max_project_count and not org.current_project_count < org.max_project_count:
        raise HTTPException(status_code=403, detail="Organization has reached it's project limit")
    
    # 4. 환경 설정 (default: development)
    environment = Environment(body.environment) if body.environment else Environment.development
    
    # 5. 프로젝트 생성
    project = ProjectModel(
        name=body.name,
        org_id=body.org_id,
        environment=environment,
    )
    
    orm.add(project)
    orm.commit()
    
    # 6. 재조회하여 관계 로드
    project = ProjectModel.get_by_id(orm, project.id)
    project.org.set_current_user(request.state.session.user_id)
    return ProjectResponse.model_validate(project)
```

### 필수 입력 데이터

**스키마**: `external/agentops/app/api/agentops/opsboard/schemas.py:337-344`

```python
class ProjectCreateSchema(BaseSchema):
    name: str              # 프로젝트 이름
    org_id: str            # 조직 ID (UUID)
    environment: str | None = None  # 환경 (development, staging, production)
```

### 자동 생성 필드

**모델**: `external/agentops/app/api/agentops/opsboard/models.py:611-622`

```python
class ProjectModel(BaseProjectModel, BaseModel):
    __tablename__ = "projects"
    __table_args__ = {"schema": "public"}
    
    id = model.Column(model.UUID, primary_key=True, default=uuid.uuid4)  # 자동 생성
    org_id = model.Column(model.UUID, model.ForeignKey("public.orgs.id"), nullable=False)
    api_key = model.Column(model.UUID, unique=True, default=uuid.uuid4)  # 자동 생성 ✅
    name = model.Column(model.String, nullable=False)
    environment = model.Column(model.Enum(Environment), default=Environment.development, nullable=False)
    
    org = orm.relationship("OrgModel", back_populates="projects")
```

**핵심**: `api_key`는 UUID로 **자동 생성**됨

---

## 2. 조직 생성 흐름

### API 엔드포인트

**위치**: `external/agentops/app/api/agentops/opsboard/views/orgs.py:226-259`

```python
def create_org(
    *,
    request: Request,
    orm: Session = Depends(get_orm_session),
    body: OrgCreateSchema,
) -> OrgResponse:
    """
    Create a new organization and add the authenticated user as owner.
    """
    # 1. 사용자 확인
    if not (user := UserModel.get_by_id(orm, request.state.session.user_id)):
        raise HTTPException(status_code=500, detail="User not found")
    
    # 2. 조직 생성
    org: OrgModel = OrgModel(name=body.name)
    orm.add(org)
    orm.flush()  # ID 생성
    
    # 3. user_orgs 관계 생성 (중요! ⚠️)
    user_org: UserOrgModel = UserOrgModel(
        user_id=user.id,
        org_id=org.id,
        role=OrgRoles.owner,      # ⚠️ owner로 설정
        user_email=user.email,    # ⚠️ 이메일 필수
        is_paid=True,             # ⚠️ owner는 paid=true
    )
    orm.add(user_org)
    
    orm.commit()
    
    return OrgResponse.model_validate(org)
```

---

## 3. 데이터베이스 구조

### 3.1 필수 테이블

#### `auth.users` (Supabase Auth)
```sql
CREATE TABLE auth.users (
    instance_id UUID,
    id UUID PRIMARY KEY,
    email VARCHAR(255),
    encrypted_password VARCHAR(255),
    email_confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    raw_user_meta_data JSONB,
    aud VARCHAR(255),
    role VARCHAR(255)
);
```

#### `public.orgs`
```sql
CREATE TABLE public.orgs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL
    -- prem_status, subscription_id 등은 선택적
);
```

#### `public.user_orgs` ⚠️ 주의
```sql
CREATE TABLE public.user_orgs (
    user_id UUID REFERENCES auth.users(id) PRIMARY KEY,
    org_id UUID REFERENCES public.orgs(id) PRIMARY KEY,
    role org_roles NOT NULL DEFAULT 'owner',  -- ⚠️ Enum: owner, admin, member
    user_email VARCHAR,                       -- ⚠️ 필수
    is_paid BOOLEAN DEFAULT false,            -- ⚠️ 필수
    PRIMARY KEY (user_id, org_id)
);
```

**중요**: 
- `role`, `user_email`, `is_paid` 컬럼이 누락되면 프로젝트 조회 시 SQL 에러 발생
- `role`은 Enum 타입 (`org_roles`)

#### `public.projects`
```sql
CREATE TABLE public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES public.orgs(id) NOT NULL,
    api_key UUID UNIQUE DEFAULT gen_random_uuid(),  -- ⚠️ 자동 생성
    name TEXT NOT NULL,
    environment environment DEFAULT 'development'   -- Enum: development, staging, production
);
```

#### `public.org_invites` (선택적, 프로젝트 조회 시 JOIN에 사용)
```sql
CREATE TABLE public.org_invites (
    inviter_id UUID REFERENCES auth.users(id) NOT NULL,
    invitee_email VARCHAR PRIMARY KEY,
    org_id UUID REFERENCES public.orgs(id) PRIMARY KEY,
    role org_roles NOT NULL,
    org_name VARCHAR,
    created_at TIMESTAMPTZ,
    PRIMARY KEY (invitee_email, org_id)
);
```

**주의**: 이 테이블이 없으면 `ProjectModel.get_by_id()`에서 SQL 에러 발생

---

## 4. 권한 모델

### OrgRoles Enum

**위치**: `external/agentops/app/api/agentops/opsboard/models.py`

```python
class OrgRoles(str, Enum):
    owner = "owner"      # 모든 권한 (조직 삭제, 프로젝트 생성/삭제)
    admin = "admin"      # 관리 권한 (프로젝트 생성)
    member = "member"    # 읽기 전용
```

### 권한 검증

```python
def is_user_admin_or_owner(self, user_id: UUID) -> bool:
    """사용자가 admin 또는 owner인지 확인"""
    for user_org in self.users:
        if user_org.user_id == user_id:
            return user_org.role in [OrgRoles.owner, OrgRoles.admin]
    return False
```

**프로젝트 생성 권한**: `owner` 또는 `admin`만 가능

---

## 5. 우리 프로젝트 적용

### 수정된 SQL (`scripts/setup-agentops.sql`)

```sql
-- 1. 사용자 생성 (Supabase Auth)
INSERT INTO auth.users (
    instance_id, 
    id,
    email, 
    encrypted_password, 
    email_confirmed_at, 
    created_at, 
    updated_at,
    raw_user_meta_data,
    aud,
    role
)
SELECT
    '00000000-0000-0000-0000-000000000000',
    gen_random_uuid(),
    'admin@agent-portal.local',
    crypt('agentops-admin-password', gen_salt('bf')),
    NOW(),
    NOW(),
    NOW(),
    '{"full_name": "Agent Portal Admin"}'::jsonb,
    'authenticated',
    'authenticated'
WHERE NOT EXISTS (
    SELECT 1 FROM auth.users WHERE email = 'admin@agent-portal.local'
);

-- 2. 조직 생성
INSERT INTO public.orgs (id, name)
SELECT gen_random_uuid(), 'Agent Portal Organization'
WHERE NOT EXISTS (
    SELECT 1 FROM public.orgs WHERE name = 'Agent Portal Organization'
);

-- 3. user_orgs 연결 (⚠️ role, user_email, is_paid 포함)
INSERT INTO public.user_orgs (user_id, org_id, role, user_email, is_paid)
SELECT u.id, o.id, 'owner', u.email, true
FROM auth.users u
CROSS JOIN public.orgs o
WHERE u.email = 'admin@agent-portal.local'
  AND o.name = 'Agent Portal Organization'
  AND NOT EXISTS (
    SELECT 1 FROM public.user_orgs uo2
    WHERE uo2.user_id = u.id AND uo2.org_id = o.id
  );

-- 4. 프로젝트 생성 (api_key 자동 생성)
INSERT INTO public.projects (id, org_id, name)
SELECT gen_random_uuid(), o.id, 'agent-portal'
FROM public.orgs o
WHERE o.name = 'Agent Portal Organization'
  AND NOT EXISTS (
    SELECT 1 FROM public.projects WHERE name = 'agent-portal'
  );
```

### 실행 방법

```bash
cd /path/to/agent-portal

# SQL 파일 복사 및 실행
docker cp scripts/setup-agentops.sql supabase_db_agentops:/tmp/setup.sql
docker exec supabase_db_agentops psql -U postgres -d postgres -f /tmp/setup.sql

# 결과 확인
docker exec supabase_db_agentops psql -U postgres -d postgres -c \
  "SELECT p.id, p.name, p.api_key FROM public.projects p WHERE p.name = 'agent-portal';"
```

---

## 6. 테스트 코드에서 배운 패턴

**위치**: `external/agentops/app/api/tests/opsboard/views/test_projects.py:89-122`

```python
# 1. 조직 생성
org = OrgModel(name="Test Org for Create")
orm_session.add(org)
orm_session.flush()  # ID 생성

# 2. user_orgs 관계 생성 (owner 권한)
user_org = UserOrgModel(
    user_id=user_id, 
    org_id=org.id, 
    role=OrgRoles.owner,          # ⚠️ 필수
    user_email="test@example.com" # ⚠️ 필수
)
orm_session.add(user_org)
orm_session.flush()

# 3. 프로젝트 생성
body = ProjectCreateSchema(
    name="New Test Project", 
    org_id=str(org.id), 
    environment=Environment.staging.value
)
result = create_project(request=mock_request, orm=orm_session, body=body)

# 4. 검증
assert result.api_key is not None  # api_key 자동 생성 확인
```

---

## 7. 주요 발견 사항

### ✅ 성공적으로 동작하는 부분
1. `api_key`는 UUID로 자동 생성됨 (수동 입력 불필요)
2. `environment`는 기본값 `development` 사용
3. 프로젝트 생성 시 조직 ID만 필요

### ⚠️  주의해야 할 부분
1. **`user_orgs` 테이블**: `role`, `user_email`, `is_paid` 컬럼 필수
2. **`org_invites` 테이블**: 프로젝트 조회 시 LEFT JOIN에 사용됨 (없으면 SQL 에러)
3. **권한**: 프로젝트 생성은 `owner` 또는 `admin`만 가능
4. **조직 owner**: `is_paid=true`로 설정해야 함

### ❌ 기존 SQL의 문제점
1. `user_orgs`에 `role` 컬럼 없음 → SQL INSERT 에러
2. `user_email`, `is_paid` 누락 → 프로젝트 조회 시 에러
3. `org_invites` 테이블 완전 누락 → 프로젝트 조회 시 SQL 에러

---

## 8. 재발 방지 체크리스트

### Supabase 마이그레이션 확인
- [ ] `user_orgs` 테이블에 `role`, `user_email`, `is_paid` 컬럼 존재
- [ ] `org_invites` 테이블 존재
- [ ] `org_roles` Enum 타입 정의
- [ ] `environment` Enum 타입 정의

### 초기 데이터 생성
- [ ] 사용자 생성 (auth.users)
- [ ] 조직 생성 (public.orgs)
- [ ] user_orgs 관계 생성 (role='owner', is_paid=true)
- [ ] 프로젝트 생성 (public.projects, api_key 자동 생성)

### 검증
- [ ] API 키 확인:
  ```bash
  docker exec supabase_db_agentops psql -U postgres -d postgres -c \
    "SELECT p.id, p.api_key FROM public.projects p WHERE p.name = 'agent-portal';"
  ```
- [ ] 권한 확인:
  ```bash
  docker exec supabase_db_agentops psql -U postgres -d postgres -c \
    "SELECT uo.role FROM public.user_orgs uo JOIN auth.users u ON uo.user_id = u.id WHERE u.email = 'admin@agent-portal.local';"
  ```

---

## 9. 참고 자료

- [AgentOps 프로젝트 생성 코드](../external/agentops/app/api/agentops/opsboard/views/projects.py)
- [AgentOps 조직 생성 코드](../external/agentops/app/api/agentops/opsboard/views/orgs.py)
- [AgentOps 모델 정의](../external/agentops/app/api/agentops/opsboard/models.py)
- [AgentOps 테스트 코드](../external/agentops/app/api/tests/opsboard/views/test_projects.py)
- [자동 설정 SQL](../scripts/setup-agentops.sql)
- [트러블슈팅 가이드](./AGENTOPS_TROUBLESHOOTING.md)

---

**마지막 업데이트**: 2025-11-20  
**버전**: 1.0  
**분석자**: Claude (Code Analysis)



