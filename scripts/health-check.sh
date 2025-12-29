#!/bin/bash
# Health Check Script for Agent Portal
# Updates .cursor/state/services.json with current service status

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STATE_FILE="$PROJECT_ROOT/.cursor/state/services.json"
STATE_DIR="$PROJECT_ROOT/.cursor/state"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create state directory if not exists
mkdir -p "$STATE_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Agent Portal Health Check                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Detect compose file
if [ -f "$PROJECT_ROOT/docker-compose.dev.yml" ]; then
    COMPOSE_FILE="docker-compose.dev.yml"
    MODE="development"
elif [ -f "$PROJECT_ROOT/docker-compose.prod.yml" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    MODE="production"
else
    COMPOSE_FILE="docker-compose.yml"
    MODE="development"
fi

echo -e "${BLUE}Mode:${NC} $MODE"
echo -e "${BLUE}Compose File:${NC} $COMPOSE_FILE"
echo ""

# Check if docker compose is available
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker compose"
else
    DOCKER_CMD="docker-compose"
fi

# Function to check port
check_port() {
    local port=$1
    if nc -z localhost $port 2>/dev/null; then
        echo "open"
    else
        echo "closed"
    fi
}

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local timeout=${2:-5}
    if curl -s --max-time $timeout "$url" > /dev/null 2>&1; then
        echo "ok"
    else
        echo "fail"
    fi
}

# Header
printf "%-20s %-10s %-10s %-10s\n" "SERVICE" "PORT" "STATUS" "HEALTH"
printf "%-20s %-10s %-10s %-10s\n" "-------" "----" "------" "------"

# Service list (service:port:health_url)
# Single Port Architecture: BFF is main entry point at port 3010
SERVICES="
backend:3010:http://localhost:3010/health
webui:3001:http://localhost:3001
litellm:4000:http://localhost:4000/health
clickhouse:8124:http://localhost:8124/ping
mariadb:3306:
kong:8004:http://localhost:8004/status
redis:6379:
prometheus:9090:http://localhost:9090/-/healthy
otel-collector:4317:
chromadb:8001:
minio:9001:http://localhost:9001
"

# JSON output
JSON_SERVICES="{"
FIRST=true

# Check each service
for service_def in $SERVICES; do
    [ -z "$service_def" ] && continue
    
    service=$(echo "$service_def" | cut -d':' -f1)
    port=$(echo "$service_def" | cut -d':' -f2)
    health_url=$(echo "$service_def" | cut -d':' -f3-)
    
    # Get container status
    container_status=$($DOCKER_CMD ps --format "{{.Names}}:{{.Status}}" 2>/dev/null | grep -i "$service" | head -1)
    
    if [ -n "$container_status" ]; then
        status_text=$(echo "$container_status" | cut -d':' -f2-)
        
        if echo "$status_text" | grep -q "Up"; then
            status="running"
            status_color=$GREEN
        else
            status="stopped"
            status_color=$RED
        fi
        
        if echo "$status_text" | grep -q "healthy"; then
            status="healthy"
        fi
    else
        status="not_found"
        status_color=$RED
    fi
    
    # Check health endpoint
    if [ -n "$health_url" ]; then
        health=$(check_http "$health_url")
        if [ "$health" = "ok" ]; then
            health_color=$GREEN
            health_icon="✓"
        else
            health_color=$RED
            health_icon="✗"
        fi
    else
        health="-"
        health_color=$NC
        health_icon="-"
    fi
    
    # Print row
    printf "%-20s ${status_color}%-10s${NC} ${status_color}%-10s${NC} ${health_color}%s${NC}\n" \
        "$service" "$port" "$status" "$health_icon"
    
    # Build JSON
    if [ "$FIRST" = true ]; then
        FIRST=false
    else
        JSON_SERVICES="$JSON_SERVICES,"
    fi
    JSON_SERVICES="$JSON_SERVICES\"$service\":{\"port\":$port,\"status\":\"$status\",\"health\":\"$health\"}"
done

JSON_SERVICES="$JSON_SERVICES}"

echo ""
echo "═══════════════════════════════════════════════════════════════"

# Count status
running_count=$($DOCKER_CMD ps --format "{{.Names}}" 2>/dev/null | wc -l | tr -d ' ')

if [ "$running_count" -ge 10 ]; then
    echo -e "${GREEN}✓ All core services are running ($running_count containers)${NC}"
else
    echo -e "${YELLOW}⚠ Some services may be down (${running_count} running)${NC}"
fi

# Update state file
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Get last successful build from existing file
LAST_BUILD="null"
if [ -f "$STATE_FILE" ] && command -v jq &> /dev/null; then
    LAST_BUILD=$(jq '.last_successful_build // null' "$STATE_FILE" 2>/dev/null || echo 'null')
fi

ROLLBACK="null"
if [ -f "$STATE_FILE" ] && command -v jq &> /dev/null; then
    ROLLBACK=$(jq '.rollback_point // null' "$STATE_FILE" 2>/dev/null || echo 'null')
fi

cat > "$STATE_FILE" << EOF
{
  "last_updated": "$TIMESTAMP",
  "mode": "$MODE",
  "compose_file": "$COMPOSE_FILE",
  "running_containers": $running_count,
  "services": $JSON_SERVICES,
  "last_successful_build": $LAST_BUILD,
  "rollback_point": $ROLLBACK
}
EOF

echo ""
echo -e "${BLUE}State file updated:${NC} $STATE_FILE"
echo ""

# Quick commands
echo "Quick Commands:"
echo "  View logs:    docker compose logs <service> --tail=50"
echo "  Restart:      docker compose restart <service>"
echo "  Rebuild:      docker compose build --no-cache <service>"
echo ""
