#!/bin/bash
# Pre-build Script for Agent Portal
# Saves current state before rebuild for rollback capability

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STATE_FILE="$PROJECT_ROOT/.cursor/state/services.json"
STATE_DIR="$PROJECT_ROOT/.cursor/state"
ROLLBACK_DIR="$STATE_DIR/rollback"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Agent Portal Pre-Build Check                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Create directories
mkdir -p "$STATE_DIR"
mkdir -p "$ROLLBACK_DIR"

# Check if docker compose is available
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker compose"
else
    DOCKER_CMD="docker-compose"
fi

# Get service to rebuild (optional argument)
SERVICE=${1:-""}

# Step 1: Run health check first
echo -e "${BLUE}Step 1: Running health check...${NC}"
"$SCRIPT_DIR/health-check.sh" || true
echo ""

# Step 2: Save current state as rollback point
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
echo -e "${BLUE}Step 2: Saving rollback point...${NC}"

# Save current container states
$DOCKER_CMD ps --format "{{.Names}},{{.Image}},{{.Status}}" > "$ROLLBACK_DIR/containers_$TIMESTAMP.txt"

# Save current images
if [ -n "$SERVICE" ]; then
    echo -e "  Saving image for: $SERVICE"
    IMAGE_ID=$($DOCKER_CMD images --format "{{.Repository}}:{{.Tag}}" | grep -i "$SERVICE" | head -1)
    if [ -n "$IMAGE_ID" ]; then
        echo "$IMAGE_ID" > "$ROLLBACK_DIR/image_$SERVICE_$TIMESTAMP.txt"
    fi
fi

# Copy current state file
if [ -f "$STATE_FILE" ]; then
    cp "$STATE_FILE" "$ROLLBACK_DIR/services_$TIMESTAMP.json"
fi

# Update state file with rollback info
if [ -f "$STATE_FILE" ]; then
    ROLLBACK_JSON=$(cat << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "rollback_id": "$TIMESTAMP",
  "service": "${SERVICE:-all}",
  "containers_backup": "$ROLLBACK_DIR/containers_$TIMESTAMP.txt",
  "state_backup": "$ROLLBACK_DIR/services_$TIMESTAMP.json"
}
EOF
)
    # Update state file with jq if available
    if command -v jq &> /dev/null; then
        TMP_FILE=$(mktemp)
        jq --argjson rollback "$ROLLBACK_JSON" '.rollback_point = $rollback' "$STATE_FILE" > "$TMP_FILE"
        mv "$TMP_FILE" "$STATE_FILE"
    fi
fi

echo -e "${GREEN}  ✓ Rollback point saved: $TIMESTAMP${NC}"
echo ""

# Step 3: Verify all critical services are running
echo -e "${BLUE}Step 3: Verifying critical services...${NC}"

CRITICAL_SERVICES=("backend" "webui" "mariadb" "litellm")
ALL_RUNNING=true

for svc in "${CRITICAL_SERVICES[@]}"; do
    STATUS=$($DOCKER_CMD ps --format "{{.Status}}" --filter "name=$svc" 2>/dev/null | head -1)
    if echo "$STATUS" | grep -q "Up"; then
        echo -e "  ${GREEN}✓${NC} $svc: running"
    else
        echo -e "  ${YELLOW}⚠${NC} $svc: not running"
        ALL_RUNNING=false
    fi
done

echo ""

if [ "$ALL_RUNNING" = true ]; then
    echo -e "${GREEN}✓ All critical services are running. Safe to proceed with build.${NC}"
else
    echo -e "${YELLOW}⚠ Some critical services are not running.${NC}"
    echo -e "  Consider running: docker compose up -d"
    echo ""
fi

# Step 4: Show recommended build commands
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${BLUE}Recommended Build Commands:${NC}"
echo ""

if [ -n "$SERVICE" ]; then
    echo "  # Rebuild $SERVICE:"
    echo "  docker compose build --no-cache $SERVICE"
    echo "  docker compose up -d $SERVICE"
    echo ""
    echo "  # Verify:"
    echo "  ./scripts/health-check.sh"
else
    echo "  # Rebuild specific service:"
    echo "  docker compose build --no-cache <service>"
    echo "  docker compose up -d <service>"
    echo ""
    echo "  # Rebuild all:"
    echo "  docker compose build --no-cache"
    echo "  docker compose up -d"
fi

echo ""
echo -e "${BLUE}Rollback Command (if build fails):${NC}"
echo "  ./scripts/rollback.sh $TIMESTAMP"
echo ""

# Step 5: Show last successful build info
if [ -f "$STATE_FILE" ] && command -v jq &> /dev/null; then
    LAST_BUILD=$(jq -r '.last_successful_build // empty' "$STATE_FILE" 2>/dev/null)
    if [ -n "$LAST_BUILD" ] && [ "$LAST_BUILD" != "null" ]; then
        echo "═══════════════════════════════════════════════════════════════"
        echo -e "${BLUE}Last Successful Build:${NC}"
        echo "$LAST_BUILD" | jq -r '"  Time: \(.timestamp // "unknown")\n  Services: \(.services_rebuilt // [] | join(", "))\n  Command: \(.command // "unknown")"'
        echo ""
    fi
fi

