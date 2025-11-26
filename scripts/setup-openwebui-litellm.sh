#!/bin/bash
# Open-WebUI에 LiteLLM 연결 설정 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 색상 코드
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Open-WebUI LiteLLM 연결 설정 시작...${NC}"

# .env 파일에서 API 키 읽기
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo -e "${RED}오류: .env 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

# 필수 변수 확인
if [ -z "$LITELLM_MASTER_KEY" ]; then
    echo -e "${RED}오류: LITELLM_MASTER_KEY가 .env에 설정되지 않았습니다.${NC}"
    exit 1
fi

# Open-WebUI 컨테이너 내부에서 SQLite 직접 수정
echo -e "${YELLOW}SQLite 데이터베이스에 LiteLLM 설정 삽입...${NC}"

# 현재 config 데이터 가져오기
CURRENT_CONFIG=$(docker-compose exec -T webui sh -c '
cd /app/backend && \
python3 -c "
import sqlite3
import json
import sys

conn = sqlite3.connect(\"data/webui.db\")
cursor = conn.cursor()

# 현재 config 조회
cursor.execute(\"SELECT data FROM config WHERE id = 1\")
row = cursor.fetchone()

if row:
    data = json.loads(row[0])
    print(json.dumps(data))
else:
    print(\"{}\")

conn.close()
"
')

if [ -z "$CURRENT_CONFIG" ] || [ "$CURRENT_CONFIG" = "{}" ]; then
    echo -e "${YELLOW}기존 설정이 없습니다. 새로운 설정 생성...${NC}"
    CURRENT_CONFIG='{}'
fi

echo -e "${GREEN}현재 설정:${NC}"
echo "$CURRENT_CONFIG" | jq .

# LiteLLM 설정 추가
NEW_CONFIG=$(echo "$CURRENT_CONFIG" | jq --arg api_key "$LITELLM_MASTER_KEY" '
{
    "version": (.version // 0),
    "ui": (.ui // {}),
    "model": (.model // {}),
    "audio": (.audio // {}),
    "ENABLE_OPENAI_API": true,
    "OPENAI_API_BASE_URLS": ["http://litellm:4000/v1"],
    "OPENAI_API_KEYS": [$api_key],
    "OPENAI_API_CONFIGS": {
        "0": {
            "name": "LiteLLM Gateway",
            "url": "http://litellm:4000/v1",
            "key": $api_key
        }
    }
} + .
')

echo -e "${GREEN}새 설정:${NC}"
echo "$NEW_CONFIG" | jq .

# SQLite에 설정 저장
docker-compose exec -T webui sh -c "
cd /app/backend && \
python3 <<'PYTHON_SCRIPT'
import sqlite3
import json
from datetime import datetime

config = '''$NEW_CONFIG'''

conn = sqlite3.connect('data/webui.db')
cursor = conn.cursor()

# 기존 config 업데이트 또는 삽입
cursor.execute('SELECT id FROM config WHERE id = 1')
row = cursor.fetchone()

if row:
    # 업데이트
    cursor.execute(
        'UPDATE config SET data = ?, version = version + 1, updated_at = ? WHERE id = 1',
        (config, datetime.now())
    )
    print('✅ 기존 설정 업데이트 완료')
else:
    # 삽입
    cursor.execute(
        'INSERT INTO config (id, data, version, created_at) VALUES (1, ?, 0, ?)',
        (config, datetime.now())
    )
    print('✅ 새 설정 삽입 완료')

conn.commit()
conn.close()
PYTHON_SCRIPT
"

echo -e "${GREEN}✅ Open-WebUI에 LiteLLM 연결 설정 완료!${NC}"
echo ""
echo -e "${YELLOW}다음 단계:${NC}"
echo "1. Open-WebUI 컨테이너 재시작: docker-compose restart webui"
echo "2. 브라우저에서 http://localhost:3000 접속"
echo "3. Settings > Connections > OpenAI API에서 설정 확인"
echo ""
echo -e "${GREEN}LiteLLM 모델 사용 가능:${NC}"
echo "  - qwen-235b (기본)"
echo "  - gpt-4 (호환성 별칭)"
echo "  - gpt-3.5-turbo (호환성 별칭)"

