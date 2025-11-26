#!/bin/bash

# AgentOps API Key 자동 생성 및 설정 스크립트
# Supabase PostgreSQL에 직접 사용자와 프로젝트를 생성합니다.

AGENTOPS_EMAIL="admin@agent-portal.local"
AGENTOPS_PASSWORD="agentops-admin-password"
AGENTOPS_FULLNAME="Agent Portal Admin"
AGENTOPS_PROJECT_NAME="agent-portal"
ORG_NAME="Agent Portal Organization"

echo "🔐 AgentOps API Key 자동 설정"
echo "================================"

# 1. Supabase 컨테이너 확인
echo "1️⃣  Supabase 상태 확인 중..."
if ! docker ps | grep -q "supabase_db_agentops"; then
    echo "❌ Supabase 컨테이너가 실행 중이지 않습니다."
    echo "   다음 명령어를 실행하세요: cd external/agentops && supabase start"
    exit 1
fi
echo "✅ Supabase 실행 중"

# 2. 사용자, 조직, 프로젝트를 한번에 생성
echo ""
echo "2️⃣  사용자, 조직, 프로젝트 생성 중..."
RESULT=$(docker exec supabase_db_agentops psql -U postgres -d postgres << EOSQL 2>&1
-- 사용자 생성
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
    '$AGENTOPS_EMAIL',
    crypt('$AGENTOPS_PASSWORD', gen_salt('bf')),
    NOW(),
    NOW(),
    NOW(),
    '{"full_name": "$AGENTOPS_FULLNAME"}'::jsonb,
    'authenticated',
    'authenticated'
WHERE NOT EXISTS (
    SELECT 1 FROM auth.users WHERE email = '$AGENTOPS_EMAIL'
);

-- 조직 생성
INSERT INTO public.orgs (id, name)
SELECT gen_random_uuid(), '$ORG_NAME'
WHERE NOT EXISTS (
    SELECT 1 FROM public.orgs WHERE name = '$ORG_NAME'
);

-- user_orgs 연결
INSERT INTO public.user_orgs (user_id, org_id, role)
SELECT u.id, o.id, 'admin'
FROM auth.users u
CROSS JOIN public.orgs o
WHERE u.email = '$AGENTOPS_EMAIL'
  AND o.name = '$ORG_NAME'
  AND NOT EXISTS (
    SELECT 1 FROM public.user_orgs uo2
    WHERE uo2.user_id = u.id AND uo2.org_id = o.id
  );

-- 프로젝트 생성
INSERT INTO public.projects (id, org_id, name)
SELECT gen_random_uuid(), o.id, '$AGENTOPS_PROJECT_NAME'
FROM public.orgs o
WHERE o.name = '$ORG_NAME'
  AND NOT EXISTS (
    SELECT 1 FROM public.projects WHERE name = '$AGENTOPS_PROJECT_NAME'
  );
EOSQL
)

if [ $? -ne 0 ]; then
    echo "❌ 데이터베이스 작업 실패"
    echo "$RESULT"
    exit 1
fi

echo "$RESULT" | grep -v "^$"
echo "✅ 데이터 생성 완료"

# 3. API 키 추출
echo ""
echo "3️⃣  API 키 및 프로젝트 ID 추출 중..."
PROJECT_ID=$(docker exec supabase_db_agentops psql -U postgres -d postgres -t -A -c \
  "SELECT p.id FROM public.projects p WHERE p.name = '$AGENTOPS_PROJECT_NAME' LIMIT 1;")

API_KEY=$(docker exec supabase_db_agentops psql -U postgres -d postgres -t -A -c \
  "SELECT p.api_key FROM public.projects p WHERE p.name = '$AGENTOPS_PROJECT_NAME' LIMIT 1;")

if [ -z "$API_KEY" ] || [ -z "$PROJECT_ID" ]; then
    echo "❌ API 키 또는 프로젝트 ID 추출 실패"
    echo "   생성된 프로젝트 확인:"
    docker exec supabase_db_agentops psql -U postgres -d postgres -c \
      "SELECT id, name, api_key FROM public.projects;"
    exit 1
fi

echo "✅ 추출 성공"
echo "   Project ID: $PROJECT_ID"
echo "   API Key: $API_KEY"

# 4. .env 파일 업데이트
echo ""
echo "4️⃣  .env 파일 업데이트 중..."
ENV_FILE=".env"

# AGENTOPS_API_KEY 업데이트
if grep -q "^AGENTOPS_API_KEY=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s/^AGENTOPS_API_KEY=.*/AGENTOPS_API_KEY=$API_KEY/" "$ENV_FILE"
    echo "✅ AGENTOPS_API_KEY 업데이트 완료"
else
    echo "" >> "$ENV_FILE"
    echo "AGENTOPS_API_KEY=$API_KEY" >> "$ENV_FILE"
    echo "✅ AGENTOPS_API_KEY 추가 완료"
fi

# 5. Backend 재시작 (AgentOps API Client가 새 키 사용하도록)
echo ""
echo "5️⃣  Backend BFF 재시작 중..."
docker-compose restart backend > /dev/null 2>&1
echo "✅ Backend 재시작 완료"

echo ""
echo "🎉 AgentOps 설정 완료!"
echo "================================"
echo "📊 생성된 정보:"
echo "   Email: $AGENTOPS_EMAIL"
echo "   Password: $AGENTOPS_PASSWORD"
echo "   Project: $AGENTOPS_PROJECT_NAME"
echo "   Project ID: $PROJECT_ID"
echo "   API Key: $API_KEY"
echo ""
echo "📋 다음 단계:"
echo "   1. AgentOps Dashboard: http://localhost:3006 (로그인)"
echo "   2. Monitoring 화면: http://localhost:3001/admin/monitoring"
echo "   3. LiteLLM 호출 시 자동으로 AgentOps에 데이터 전송됨"
echo ""
echo "💡 참고: 프론트엔드 모니터링 화면에서 Project ID를 '$PROJECT_ID'로 설정하세요."
