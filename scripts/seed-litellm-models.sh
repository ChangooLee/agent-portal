#!/bin/bash
# LiteLLM 초기 모델 시딩 스크립트
# 
# 사용법:
#   ./scripts/seed-litellm-models.sh
#
# 이 스크립트는 LiteLLM DB에 기본 모델들을 등록합니다.
# store_model_in_db: true 설정으로 모델이 PostgreSQL에 저장됩니다.

set -e

# 설정
LITELLM_HOST="${LITELLM_HOST:-http://localhost:4001}"
LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-1234}"
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "LiteLLM 모델 시딩 스크립트"
echo "================================================"
echo ""

# LiteLLM 헬스체크
echo -e "${YELLOW}1. LiteLLM 헬스체크...${NC}"
for i in {1..30}; do
    if curl -s -f "${LITELLM_HOST}/health" -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" > /dev/null 2>&1; then
        echo -e "${GREEN}   ✓ LiteLLM이 정상 동작 중입니다.${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}   ✗ LiteLLM에 연결할 수 없습니다. 서비스가 실행 중인지 확인하세요.${NC}"
        exit 1
    fi
    echo "   대기 중... ($i/30)"
    sleep 2
done

# API 키 확인
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo -e "${YELLOW}   ⚠ OPENROUTER_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.${NC}"
fi

echo ""
echo -e "${YELLOW}2. 기존 모델 확인...${NC}"
EXISTING_MODELS=$(curl -s "${LITELLM_HOST}/v1/models" \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" | jq -r '.data[].id // empty' 2>/dev/null || echo "")

if [ -n "$EXISTING_MODELS" ]; then
    echo -e "${GREEN}   기존 모델이 있습니다:${NC}"
    echo "$EXISTING_MODELS" | while read -r model; do
        echo "   - $model"
    done
else
    echo "   등록된 모델이 없습니다."
fi

echo ""
echo -e "${YELLOW}3. 모델 등록 중...${NC}"

# 모델 등록 함수
add_model() {
    local model_name=$1
    local litellm_model=$2
    local api_base=$3
    
    # 이미 존재하는지 확인
    if echo "$EXISTING_MODELS" | grep -q "^${model_name}$"; then
        echo -e "   ${YELLOW}⊘ ${model_name}: 이미 존재함${NC}"
        return 0
    fi
    
    # API 키 확인 (환경변수에서 직접 읽기)
    if [ -z "$OPENROUTER_API_KEY" ]; then
        echo -e "   ${RED}✗ ${model_name}: OPENROUTER_API_KEY가 설정되지 않음${NC}"
        return 1
    fi
    
    local payload=$(cat <<EOF
{
    "model_name": "${model_name}",
    "litellm_params": {
        "model": "${litellm_model}",
        "api_base": "${api_base}",
        "api_key": "${OPENROUTER_API_KEY}"
    }
}
EOF
)
    
    local response=$(curl -s -X POST "${LITELLM_HOST}/model/new" \
        -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
        -H "Content-Type: application/json" \
        -d "${payload}")
    
    if echo "$response" | grep -q "error"; then
        echo -e "   ${RED}✗ ${model_name}: 등록 실패${NC}"
        echo "     Error: $(echo "$response" | jq -r '.error.message // .detail // .')"
        return 1
    else
        echo -e "   ${GREEN}✓ ${model_name}: 등록 완료${NC}"
        return 0
    fi
}

# OpenRouter 모델 등록
echo ""
echo "   --- OpenRouter Models ---"
add_model "qwen-235b" "openrouter/qwen/qwen3-235b-a22b-2507" "https://openrouter.ai/api/v1"
add_model "gpt-4" "openrouter/qwen/qwen3-235b-a22b-2507" "https://openrouter.ai/api/v1"
add_model "gpt-3.5-turbo" "openrouter/qwen/qwen3-235b-a22b-2507" "https://openrouter.ai/api/v1"
add_model "glm-4" "openrouter/z-ai/glm-4.6" "https://openrouter.ai/api/v1"
add_model "gpt-oss" "openrouter/openai/gpt-oss-120b" "https://openrouter.ai/api/v1"
add_model "gpt-oss-free" "openrouter/openai/gpt-oss-20b:free" "https://openrouter.ai/api/v1"

echo ""
echo -e "${YELLOW}4. 최종 모델 목록 확인...${NC}"
curl -s "${LITELLM_HOST}/v1/models" \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" | jq -r '.data[] | "   - \(.id)"' 2>/dev/null || echo "   모델 목록을 가져올 수 없습니다."

echo ""
echo "================================================"
echo -e "${GREEN}모델 시딩이 완료되었습니다!${NC}"
echo ""
echo "다음 명령어로 모델을 테스트할 수 있습니다:"
echo "  curl ${LITELLM_HOST}/v1/chat/completions \\"
echo "    -H 'Authorization: Bearer ${LITELLM_MASTER_KEY}' \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"model\": \"qwen-235b\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}'"
echo "================================================"

