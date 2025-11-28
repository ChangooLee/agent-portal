#!/bin/bash
# Safe Restart Script for Agent Portal
# Restarts services in correct dependency order

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Agent Portal Safe Restart                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Parse arguments
SERVICE=$1
FULL_RESTART=false

if [ -z "$SERVICE" ]; then
    FULL_RESTART=true
fi

# Service dependency order (bottom to top)
# Layer 1: Infrastructure (no dependencies)
LAYER1="mariadb redis"

# Layer 2: Core services (depends on Layer 1)
LAYER2="litellm litellm-postgres kong kong-db"

# Layer 3: Observability (depends on Layer 1-2)
LAYER3="otel-collector monitoring-clickhouse prometheus"

# Layer 4: Application (depends on Layer 1-3)
LAYER4="backend chromadb minio"

# Layer 5: Frontend (depends on everything)
LAYER5="webui"

# Function to get service layer
get_layer() {
    local svc=$1
    case "$svc" in
        mariadb|redis) echo 1 ;;
        litellm|litellm-postgres|kong|kong-db) echo 2 ;;
        otel-collector|monitoring-clickhouse|prometheus) echo 3 ;;
        backend|chromadb|minio) echo 4 ;;
        webui) echo 5 ;;
        *) echo 0 ;;
    esac
}

# Function to restart a layer
restart_layer() {
    local layer=$1
    local services=$2
    local wait_time=${3:-5}
    
    echo -e "${BLUE}Layer $layer:${NC} $services"
    
    for svc in $services; do
        if docker compose ps -q "$svc" > /dev/null 2>&1; then
            echo -e "  Restarting ${YELLOW}$svc${NC}..."
            docker compose restart "$svc" 2>/dev/null || docker compose up -d "$svc"
        fi
    done
    
    echo -e "  Waiting ${wait_time}s for services to stabilize..."
    sleep $wait_time
}

# Check current status first
echo -e "${BLUE}Pre-restart health check:${NC}"
"$SCRIPT_DIR/health-check.sh" 2>/dev/null | head -30 || echo "(health check skipped)"
echo ""

if [ "$FULL_RESTART" = true ]; then
    echo -e "${YELLOW}Performing full restart in dependency order...${NC}"
    echo ""
    
    # Stop all first (in reverse order)
    echo -e "${YELLOW}Stopping services...${NC}"
    docker compose stop webui 2>/dev/null || true
    docker compose stop backend chromadb minio 2>/dev/null || true
    docker compose stop otel-collector monitoring-clickhouse prometheus 2>/dev/null || true
    docker compose stop litellm kong 2>/dev/null || true
    echo "Stopped."
    echo ""
    
    # Start in order
    echo -e "${YELLOW}Starting services in dependency order...${NC}"
    echo ""
    
    restart_layer 1 "$LAYER1" 10
    restart_layer 2 "$LAYER2" 10
    restart_layer 3 "$LAYER3" 10
    restart_layer 4 "$LAYER4" 5
    restart_layer 5 "$LAYER5" 5
    
else
    # Single service restart
    layer=$(get_layer "$SERVICE")
    
    if [ "$layer" = "0" ]; then
        echo -e "${YELLOW}Warning: Unknown service '$SERVICE'. Attempting direct restart...${NC}"
        docker compose restart "$SERVICE"
    else
        echo -e "${BLUE}Service '$SERVICE' is in Layer $layer${NC}"
        echo ""
        
        # Stop dependent services first
        if [ "$layer" -lt 5 ]; then
            echo -e "${YELLOW}Stopping dependent services...${NC}"
            
            case $layer in
                1) 
                    docker compose stop webui backend 2>/dev/null || true
                    ;;
                2)
                    docker compose stop webui backend 2>/dev/null || true
                    ;;
                3)
                    docker compose stop webui 2>/dev/null || true
                    ;;
                4)
                    docker compose stop webui 2>/dev/null || true
                    ;;
            esac
        fi
        
        # Restart the target service
        echo -e "${YELLOW}Restarting $SERVICE...${NC}"
        docker compose restart "$SERVICE"
        sleep 5
        
        # Restart dependent services
        if [ "$layer" -lt 5 ]; then
            echo -e "${YELLOW}Starting dependent services...${NC}"
            
            case $layer in
                1|2)
                    docker compose start backend 2>/dev/null || docker compose up -d backend
                    sleep 5
                    docker compose start webui 2>/dev/null || docker compose up -d webui
                    ;;
                3|4)
                    docker compose start webui 2>/dev/null || docker compose up -d webui
                    ;;
            esac
        fi
    fi
fi

echo ""
echo -e "${YELLOW}Post-restart health check:${NC}"
sleep 5
"$SCRIPT_DIR/health-check.sh"

echo ""
echo -e "${GREEN}✓ Restart completed!${NC}"

