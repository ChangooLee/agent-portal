#!/bin/bash
# 개발 모드: 프론트엔드와 백엔드를 함께 실행

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

# 백엔드 환경 변수 설정
KEY_FILE=backend/.webui_secret_key
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

if test "$WEBUI_SECRET_KEY $WEBUI_JWT_SECRET_KEY" = " "; then
  if ! [ -e "$KEY_FILE" ]; then
    echo "Generating WEBUI_SECRET_KEY"
    echo $(head -c 12 /dev/random | base64) > "$KEY_FILE"
  fi
  echo "Loading WEBUI_SECRET_KEY from $KEY_FILE"
  export WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
fi

# 백엔드를 백그라운드로 실행
echo "Starting backend server..."
cd backend
WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' --reload &
BACKEND_PID=$!
cd ..

# 백엔드가 시작될 때까지 대기
echo "Waiting for backend to start..."
sleep 3
for i in {1..30}; do
  if curl -s http://localhost:${PORT}/health > /dev/null 2>&1; then
    echo "Backend is ready!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "Warning: Backend may not be ready yet"
  fi
  sleep 1
done

# 프론트엔드 개발 서버 실행 (포그라운드로 실행하여 로그 확인 가능)
echo "Starting frontend dev server..."
npm run dev
