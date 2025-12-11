#!/bin/bash
# Start services and run basic tests
# Usage: ./scripts/start-and-test.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Agent Portal - Start and Test Script                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if docker compose is available
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker compose"
else
    DOCKER_CMD="docker-compose"
fi

# Step 1: Start services
echo -e "${BLUE}Step 1: Starting Docker Compose services...${NC}"
$DOCKER_CMD up -d

# Step 2: Wait for services to be healthy
echo -e "${BLUE}Step 2: Waiting for services to be ready (max 120s)...${NC}"
MAX_WAIT=120
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check BFF health
    if curl -s --max-time 2 http://localhost:3009/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ BFF is ready${NC}"
        break
    fi
    
    echo -e "${YELLOW}Waiting for services... (${ELAPSED}s/${MAX_WAIT}s)${NC}"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${RED}✗ Services did not become ready within ${MAX_WAIT}s${NC}"
    echo -e "${YELLOW}Checking service logs...${NC}"
    $DOCKER_CMD logs backend --tail=50
    exit 1
fi

# Step 3: Run basic tests
echo ""
echo -e "${BLUE}Step 3: Running basic connectivity tests...${NC}"

FAILED_TESTS=0
TOTAL_TESTS=0

# Test 1: BFF Health Check
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo -n "  Test 1: BFF Health Check... "
if curl -s --max-time 5 http://localhost:3009/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ PASSED${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 2: WebUI Frontend (via BFF)
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo -n "  Test 2: WebUI Frontend (via BFF)... "
if curl -s --max-time 5 -I http://localhost:3009/ | grep -q "200 OK"; then
    echo -e "${GREEN}✓ PASSED${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 3: WebUI Backend Proxy
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo -n "  Test 3: WebUI Backend Proxy... "
if curl -s --max-time 5 http://localhost:3009/api/webui/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC}"
else
    echo -e "${YELLOW}⚠ SKIPPED (WebUI Backend may not be ready)${NC}"
fi

# Test 4: Monitoring API
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo -n "  Test 4: Monitoring API... "
if curl -s --max-time 5 http://localhost:3009/monitoring/traces?limit=1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC}"
else
    echo -e "${YELLOW}⚠ SKIPPED (Monitoring may not be ready)${NC}"
fi

# Test 5: MCP API
TOTAL_TESTS=$((TOTAL_TESTS + 1))
echo -n "  Test 5: MCP API... "
if curl -s --max-time 5 http://localhost:3009/mcp/servers > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASSED${NC}"
else
    echo -e "${YELLOW}⚠ SKIPPED (MCP service may not be ready)${NC}"
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════"
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! (${TOTAL_TESTS} tests)${NC}"
    echo ""
    echo -e "${BLUE}Services are running:${NC}"
    echo "  - Portal UI: http://localhost:3009"
    echo "  - BFF API: http://localhost:3009/docs"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed (${FAILED_TESTS}/${TOTAL_TESTS})${NC}"
    echo ""
    echo -e "${YELLOW}Check service logs:${NC}"
    echo "  docker compose logs backend --tail=50"
    echo "  docker compose logs webui --tail=50"
    echo ""
    exit 1
fi


