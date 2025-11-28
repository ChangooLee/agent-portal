#!/bin/bash

# 포트 충돌 체크 스크립트
# 서비스 기동 전 필수 포트가 사용 가능한지 확인

set -e

echo "🔍 포트 사용 현황 확인 중..."
echo ""

# 체크할 포트 목록 (서비스명:포트)
PORTS=(
    "Backend BFF:8000"
    "WebUI:3000"
    "WebUI Dev:3001"
    "Flowise:3002"
    "MariaDB:3306"
    "LiteLLM:4000"
    "AutoGen Studio:5050"
    "AutoGen API:5051"
    "Redis:6379"
    "Langflow:7861"
    "ChromaDB:8001"
    "Kong Proxy:8002"
    "Kong Admin:8001"
    "MinIO API:9000"
    "MinIO Console:9001"
)

CONFLICTS=0

for entry in "${PORTS[@]}"; do
    SERVICE="${entry%%:*}"
    PORT="${entry##*:}"
    
    # macOS/Linux에서 포트 사용 확인
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        PID=$(lsof -Pi :$PORT -sTCP:LISTEN -t)
        PROCESS=$(ps -p $PID -o comm= 2>/dev/null || echo "unknown")
        echo "⚠️  포트 $PORT 사용 중: $SERVICE (PID: $PID, Process: $PROCESS)"
        CONFLICTS=$((CONFLICTS + 1))
    else
        echo "✅ 포트 $PORT 사용 가능: $SERVICE"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $CONFLICTS -gt 0 ]; then
    echo "❌ $CONFLICTS 개 포트 충돌 발견!"
    echo ""
    echo "해결 방법:"
    echo "1. docker-compose.yml에서 충돌하는 서비스의 포트 변경 (권장)"
    echo "   예: '7860:7860' → '7861:7860'"
    echo "2. 충돌하는 서비스의 포트 목록을 scripts/check-ports.sh에 업데이트"
    echo ""
    echo "⚠️  기존 프로세스는 종료하지 마세요!"
    echo "    (Stable Diffusion 등 상시 실행 서비스일 수 있음)"
    echo ""
    exit 1
else
    echo "✅ 모든 포트 사용 가능!"
    echo ""
    exit 0
fi

