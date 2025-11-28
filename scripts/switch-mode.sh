#!/bin/bash
# Mode Switch Script for Agent Portal
# Safely switches between development and production modes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STATE_FILE="$PROJECT_ROOT/.cursor/state/services.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Agent Portal Mode Switch                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get current mode
CURRENT_MODE="unknown"
if [ -f "$STATE_FILE" ] && command -v jq &> /dev/null; then
    CURRENT_MODE=$(jq -r '.mode // "unknown"' "$STATE_FILE")
fi

echo -e "${BLUE}Current mode:${NC} $CURRENT_MODE"

# Parse target mode
TARGET_MODE=$1

if [ -z "$TARGET_MODE" ]; then
    echo ""
    echo "Usage: $0 <dev|prod>"
    echo ""
    echo "Modes:"
    echo "  dev  - Development mode (hot reload, volume mounts)"
    echo "  prod - Production mode (optimized builds, no debug)"
    exit 1
fi

# Normalize mode name
case "$TARGET_MODE" in
    dev|development) TARGET_MODE="development" ;;
    prod|production) TARGET_MODE="production" ;;
    *)
        echo -e "${RED}Error: Invalid mode '$TARGET_MODE'. Use 'dev' or 'prod'.${NC}"
        exit 1
        ;;
esac

if [ "$TARGET_MODE" = "$CURRENT_MODE" ]; then
    echo -e "${YELLOW}Already in $TARGET_MODE mode. No changes needed.${NC}"
    exit 0
fi

echo -e "${BLUE}Target mode:${NC} $TARGET_MODE"
echo ""

# Pre-switch checklist
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                Pre-Switch Checklist                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

CHECKLIST_OK=true

# 1. Check Docker
echo -n "  [1/5] Docker running: "
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    CHECKLIST_OK=false
fi

# 2. Check compose files exist
echo -n "  [2/5] Compose files present: "
if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    CHECKLIST_OK=false
fi

# 3. Check .env file
echo -n "  [3/5] Environment file (.env): "
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ (missing, using defaults)${NC}"
fi

# 4. Check disk space
echo -n "  [4/5] Disk space (>1GB free): "
FREE_SPACE=$(df -k "$PROJECT_ROOT" | tail -1 | awk '{print $4}')
if [ "$FREE_SPACE" -gt 1000000 ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ (low disk space)${NC}"
fi

# 5. Check port conflicts
echo -n "  [5/5] Critical ports available: "
PORTS_OK=true
for port in 3001 8000 4000; do
    if lsof -i :$port > /dev/null 2>&1; then
        # Port in use - check if it's our container
        if ! docker compose ps | grep -q "$port"; then
            PORTS_OK=false
        fi
    fi
done
if [ "$PORTS_OK" = true ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ (some ports may conflict)${NC}"
fi

echo ""

if [ "$CHECKLIST_OK" = false ]; then
    echo -e "${RED}Pre-flight check failed. Aborting.${NC}"
    exit 1
fi

# Create rollback point
echo -e "${YELLOW}Creating rollback point...${NC}"
"$SCRIPT_DIR/pre-build.sh" 2>/dev/null || true
echo ""

# Stop current services
echo -e "${YELLOW}Stopping current services...${NC}"
docker compose down --remove-orphans 2>/dev/null || true
echo ""

# Switch mode
echo -e "${YELLOW}Switching to $TARGET_MODE mode...${NC}"
echo ""

if [ "$TARGET_MODE" = "development" ]; then
    # Development mode
    export NODE_ENV=development
    export FASTAPI_ENV=development
    
    if [ -f "$PROJECT_ROOT/docker-compose.dev.yml" ]; then
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"
    else
        COMPOSE_FILES="-f docker-compose.yml"
    fi
    
    echo "Using: docker compose $COMPOSE_FILES"
    
    # Start in dependency order
    docker compose $COMPOSE_FILES up -d mariadb redis
    sleep 10
    docker compose $COMPOSE_FILES up -d litellm kong
    sleep 5
    docker compose $COMPOSE_FILES up -d otel-collector monitoring-clickhouse prometheus
    sleep 5
    docker compose $COMPOSE_FILES up -d backend chromadb minio
    sleep 5
    docker compose $COMPOSE_FILES up -d webui
    
else
    # Production mode
    export NODE_ENV=production
    export FASTAPI_ENV=production
    
    if [ -f "$PROJECT_ROOT/docker-compose.prod.yml" ]; then
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
    else
        COMPOSE_FILES="-f docker-compose.yml"
    fi
    
    echo "Using: docker compose $COMPOSE_FILES"
    echo ""
    echo -e "${YELLOW}Building production images...${NC}"
    docker compose $COMPOSE_FILES build --no-cache backend webui
    echo ""
    
    # Start in dependency order
    docker compose $COMPOSE_FILES up -d mariadb redis
    sleep 10
    docker compose $COMPOSE_FILES up -d litellm kong
    sleep 5
    docker compose $COMPOSE_FILES up -d otel-collector monitoring-clickhouse prometheus
    sleep 5
    docker compose $COMPOSE_FILES up -d backend chromadb minio
    sleep 5
    docker compose $COMPOSE_FILES up -d webui
fi

echo ""
echo -e "${YELLOW}Verifying services...${NC}"
sleep 10
"$SCRIPT_DIR/health-check.sh"

echo ""
echo -e "${GREEN}✓ Mode switch completed: $CURRENT_MODE → $TARGET_MODE${NC}"
echo ""
echo "To rollback if issues occur:"
echo "  ./scripts/rollback.sh latest"
echo ""

