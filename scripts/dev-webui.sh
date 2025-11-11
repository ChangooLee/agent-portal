#!/bin/bash
# WebUI 개발 모드 실행 스크립트
# Hot reload 지원으로 UI 코드 변경 시 즉시 반영

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🚀 WebUI 개발 모드 시작..."
echo "📝 UI 코드 변경 시 자동으로 반영됩니다 (Hot Reload)"
echo ""

# docker-compose 파일 확인
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml을 찾을 수 없습니다."
    exit 1
fi

if [ ! -f "docker-compose.dev.yml" ]; then
    echo "❌ docker-compose.dev.yml을 찾을 수 없습니다."
    exit 1
fi

# 기존 컨테이너 중지 (선택적)
if [ "$1" = "--clean" ]; then
    echo "🧹 기존 컨테이너 정리 중..."
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml down webui 2>/dev/null || true
fi

# 개발 모드로 시작
echo "🔨 개발 모드 컨테이너 시작 중..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build webui


