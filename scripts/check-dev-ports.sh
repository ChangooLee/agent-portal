#!/bin/bash
# 개발 환경 포트 충돌 체크 스크립트
# Cursor IDE가 동적으로 포트를 점유하므로 기동 전 확인 필요

set -e

echo "🔍 개발 포트 확인 중..."
echo ""

# 주요 포트 목록
PORTS=(
    "3009:WebUI Vite"
    "3000:WebUI Backend"
    "8000:Backend BFF"
    "8125:ClickHouse"
    "4000:LiteLLM"
    "1337:Konga"
    "8004:Kong Proxy"
)

CONFLICT=0

for ENTRY in "${PORTS[@]}"; do
    PORT="${ENTRY%%:*}"
    NAME="${ENTRY##*:}"
    
    # LISTEN 상태인 프로세스만 확인
    LISTEN_INFO=$(lsof -i :$PORT -sTCP:LISTEN 2>/dev/null | grep -v "^COMMAND" | head -1)
    
    if [ -n "$LISTEN_INFO" ]; then
        PNAME=$(echo "$LISTEN_INFO" | awk '{print $1}')
        
        if [[ "$PNAME" == *"Cursor"* ]]; then
            echo "⚠️  $NAME (포트 $PORT): Cursor IDE 점유! → 포트 변경 필요"
            CONFLICT=1
        elif [[ "$PNAME" == *"docker"* ]] || [[ "$PNAME" == *"com.docke"* ]]; then
            echo "✅ $NAME (포트 $PORT): Docker 사용 중"
        elif [[ "$PNAME" == "node" ]]; then
            echo "⚠️  $NAME (포트 $PORT): Node.js 사용 중"
            CONFLICT=1
        else
            echo "⚠️  $NAME (포트 $PORT): $PNAME 사용 중"
        fi
    else
        echo "✅ $NAME (포트 $PORT): 사용 가능"
    fi
done

echo ""

if [ $CONFLICT -eq 1 ]; then
    echo "⚠️  포트 충돌 발견! docker-compose.dev.yml에서 포트 변경 필요"
    echo "   참고: docs/PORT-CONFLICT-GUIDE.md"
    exit 1
else
    echo "✅ 모든 포트 사용 가능!"
fi

