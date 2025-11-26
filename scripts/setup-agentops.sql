-- AgentOps 초기 설정 SQL

-- 1. 사용자 생성
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

-- 3. user_orgs 연결 (role, user_email, is_paid 포함)
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

-- 4. 프로젝트 생성
INSERT INTO public.projects (id, org_id, name)
SELECT gen_random_uuid(), o.id, 'agent-portal'
FROM public.orgs o
WHERE o.name = 'Agent Portal Organization'
  AND NOT EXISTS (
    SELECT 1 FROM public.projects WHERE name = 'agent-portal'
  );

-- 5. 결과 출력
SELECT 
    'USER' as type,
    u.id::text as id,
    u.email as name,
    NULL as api_key
FROM auth.users u
WHERE u.email = 'admin@agent-portal.local'
UNION ALL
SELECT 
    'ORG' as type,
    o.id::text as id,
    o.name as name,
    NULL as api_key
FROM public.orgs o
WHERE o.name = 'Agent Portal Organization'
UNION ALL
SELECT 
    'PROJECT' as type,
    p.id::text as id,
    p.name as name,
    p.api_key::text as api_key
FROM public.projects p
WHERE p.name = 'agent-portal';

