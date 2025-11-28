#!/bin/bash
# Rollback Script for Agent Portal
# Restores previous state from rollback point

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STATE_FILE="$PROJECT_ROOT/.cursor/state/services.json"
ROLLBACK_DIR="$PROJECT_ROOT/.cursor/state/rollback"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Agent Portal Rollback                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check rollback directory
if [ ! -d "$ROLLBACK_DIR" ]; then
    echo -e "${RED}Error: No rollback directory found at $ROLLBACK_DIR${NC}"
    exit 1
fi

# List available rollback points
rollback_files=($(ls -t "$ROLLBACK_DIR"/*.json 2>/dev/null))

if [ ${#rollback_files[@]} -eq 0 ]; then
    echo -e "${YELLOW}No rollback points available.${NC}"
    echo "Create one with: ./scripts/pre-build.sh <service>"
    exit 1
fi

echo -e "${BLUE}Available rollback points:${NC}"
echo ""

for i in "${!rollback_files[@]}"; do
    file="${rollback_files[$i]}"
    filename=$(basename "$file")
    timestamp=$(echo "$filename" | sed 's/rollback_//' | sed 's/.json//')
    
    # Extract info from rollback file
    if command -v jq &> /dev/null; then
        mode=$(jq -r '.mode // "unknown"' "$file" 2>/dev/null)
        containers=$(jq -r '.running_containers // "?"' "$file" 2>/dev/null)
        echo "  $((i+1)). $timestamp (mode: $mode, containers: $containers)"
    else
        echo "  $((i+1)). $timestamp"
    fi
done

echo ""

# Get rollback point selection
if [ -n "$1" ]; then
    selection=$1
else
    read -p "Select rollback point (1-${#rollback_files[@]}) or 'latest': " selection
fi

# Determine which file to use
if [ "$selection" = "latest" ] || [ "$selection" = "1" ]; then
    selected_file="${rollback_files[0]}"
elif [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -le "${#rollback_files[@]}" ]; then
    selected_file="${rollback_files[$((selection-1))]}"
else
    echo -e "${RED}Invalid selection: $selection${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Selected rollback point:${NC} $(basename "$selected_file")"

# Confirm rollback
if [ -z "$FORCE" ]; then
    read -p "Proceed with rollback? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Rollback cancelled."
        exit 0
    fi
fi

echo ""
echo -e "${YELLOW}Starting rollback...${NC}"

# Read rollback state
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required for rollback. Install with: brew install jq${NC}"
    exit 1
fi

ROLLBACK_MODE=$(jq -r '.mode // "development"' "$selected_file")
ROLLBACK_COMPOSE=$(jq -r '.compose_file // "docker-compose.yml"' "$selected_file")

echo ""
echo -e "${BLUE}Rollback configuration:${NC}"
echo "  Mode: $ROLLBACK_MODE"
echo "  Compose file: $ROLLBACK_COMPOSE"
echo ""

# Step 1: Stop current containers
echo -e "${YELLOW}Step 1: Stopping current containers...${NC}"
docker compose down --remove-orphans 2>/dev/null || true

# Step 2: Restore compose file mode
echo -e "${YELLOW}Step 2: Restoring compose mode...${NC}"
if [ "$ROLLBACK_MODE" = "development" ]; then
    COMPOSE_CMD="docker compose -f docker-compose.yml"
    if [ -f "$PROJECT_ROOT/docker-compose.dev.yml" ]; then
        COMPOSE_CMD="$COMPOSE_CMD -f docker-compose.dev.yml"
    fi
else
    COMPOSE_CMD="docker compose -f docker-compose.yml"
    if [ -f "$PROJECT_ROOT/docker-compose.prod.yml" ]; then
        COMPOSE_CMD="$COMPOSE_CMD -f docker-compose.prod.yml"
    fi
fi

# Step 3: Start services in dependency order
echo -e "${YELLOW}Step 3: Starting services in dependency order...${NC}"
echo ""

# Infrastructure services first
echo "  Starting infrastructure services..."
$COMPOSE_CMD up -d mariadb redis 2>/dev/null || docker compose up -d mariadb redis

echo "  Waiting for databases to be ready (10s)..."
sleep 10

# Core services
echo "  Starting core services..."
$COMPOSE_CMD up -d litellm kong 2>/dev/null || docker compose up -d litellm kong
sleep 5

# Observability
echo "  Starting observability services..."
$COMPOSE_CMD up -d otel-collector clickhouse prometheus 2>/dev/null || docker compose up -d otel-collector clickhouse prometheus
sleep 5

# Application services
echo "  Starting application services..."
$COMPOSE_CMD up -d backend chromadb minio 2>/dev/null || docker compose up -d backend chromadb minio
sleep 5

# Frontend
echo "  Starting frontend..."
$COMPOSE_CMD up -d webui 2>/dev/null || docker compose up -d webui

echo ""
echo -e "${YELLOW}Step 4: Verifying services...${NC}"
sleep 10

# Run health check
"$SCRIPT_DIR/health-check.sh"

echo ""
echo -e "${GREEN}✓ Rollback completed!${NC}"
echo ""
echo "If issues persist, check logs with:"
echo "  docker compose logs <service> --tail=100"
echo ""

