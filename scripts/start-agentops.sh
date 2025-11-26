#!/bin/bash

set -e

echo "🚀 AgentOps Self-Hosted Setup Script"
echo "====================================="
echo ""
echo "이 스크립트는 AgentOps 인스턴스를 로컬에서 시작합니다."
echo "상세 가이드: docs/AGENTOPS_SETUP.md"
echo ""

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTOPS_DIR="$PROJECT_ROOT/external/agentops/app"

# AgentOps 디렉토리 존재 확인
if [ ! -d "$AGENTOPS_DIR" ]; then
    echo "❌ AgentOps 디렉토리가 없습니다: $AGENTOPS_DIR"
    echo "서브모듈을 초기화하세요:"
    echo "  git submodule update --init --recursive"
    exit 1
fi

cd "$AGENTOPS_DIR"

echo "📂 작업 디렉토리: $AGENTOPS_DIR"
echo ""

# 1단계: Supabase CLI 설치 확인
echo "1️⃣  Supabase CLI 확인..."
if ! command -v supabase &> /dev/null; then
    echo "⚠️  Supabase CLI가 설치되지 않았습니다."
    echo "설치 방법:"
    echo "  npm install -g supabase"
    echo ""
    read -p "지금 설치하시겠습니까? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        npm install -g supabase
    else
        echo "❌ Supabase CLI가 필요합니다. 설치 후 다시 실행하세요."
        exit 1
    fi
fi
echo "✅ Supabase CLI 설치됨"

# 2단계: Supabase 시작
echo ""
echo "2️⃣  Supabase 로컬 인스턴스 시작..."
echo "   (처음 실행 시 Docker 이미지 다운로드로 시간이 걸릴 수 있습니다)"
supabase start

# Supabase 출력에서 키 추출 (선택적)
echo ""
echo "✅ Supabase 시작 완료"
echo ""
echo "📋 Supabase 연결 정보는 위 출력을 참고하세요."
echo "   - API URL: http://127.0.0.1:54321"
echo "   - anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
echo "   - service_role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
echo ""

# 3단계: .env 파일 확인
echo "3️⃣  환경 변수 설정 확인..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다."
    if [ -f ".env.example" ]; then
        echo "   .env.example에서 복사합니다..."
        cp .env.example .env
        echo "✅ .env 파일 생성됨"
        echo "   ⚠️  .env 파일을 편집하여 Supabase 키를 입력하세요!"
        echo "   vim .env"
    else
        echo "❌ .env.example 파일도 없습니다."
        exit 1
    fi
else
    echo "✅ .env 파일 존재"
fi

# 4단계: ClickHouse 및 OpenTelemetry Collector 시작
echo ""
echo "4️⃣  ClickHouse 및 OTEL Collector 시작..."
docker-compose up -d
echo "✅ 인프라 서비스 시작 완료"

# 5단계: 다음 단계 안내
echo ""
echo "🎉 AgentOps 인프라 설정 완료!"
echo ""
echo "📌 다음 단계:"
echo "   1. API 서버 시작:"
echo "      cd $AGENTOPS_DIR/api"
echo "      uv sync  # 또는 pip install -e ."
echo "      uv run python run.py  # 또는 python run.py"
echo ""
echo "   2. Dashboard 시작 (별도 터미널):"
echo "      cd $AGENTOPS_DIR/dashboard"
echo "      npm install  # 또는 bun install"
echo "      npm run dev  # 또는 bun dev"
echo ""
echo "   3. Dashboard 접속:"
echo "      http://localhost:3006"
echo ""
echo "   4. 계정 생성 및 API 키 발급:"
echo "      - Sign Up으로 계정 생성"
echo "      - Settings → API Keys → Create API Key"
echo "      - 생성된 키를 프로젝트 .env에 추가"
echo ""
echo "상세 가이드: $PROJECT_ROOT/docs/AGENTOPS_SETUP.md"

