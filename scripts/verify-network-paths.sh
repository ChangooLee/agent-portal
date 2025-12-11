#!/bin/bash
# Network path verification script
# Verifies all network paths and measures response times
# Usage: ./scripts/verify-network-paths.sh

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
echo "║         Agent Portal - Network Path Verification             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Function to test a network path
test_path() {
    local name="$1"
    local url="$2"
    local method="${3:-GET}"
    
    echo -n "  Testing ${name}... "
    
    local start_time=$(date +%s%N)
    local response
    local status_code
    local error=""
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -o /dev/null "$url" 2>&1) || error="$response"
    else
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X "$method" -o /dev/null "$url" 2>&1) || error="$response"
    fi
    
    local end_time=$(date +%s%N)
    local response_time_ms=$(((end_time - start_time) / 1000000))
    
    if [ -n "$error" ] && ! echo "$error" | grep -q "HTTP_CODE"; then
        echo -e "${RED}✗ FAILED${NC} (Error: ${error:0:50})"
        return 1
    fi
    
    status_code=$(echo "$response" | grep -oE 'HTTP_CODE:[0-9]+' | grep -oE '[0-9]+' || echo "000")
    
    if [ "$status_code" -ge 200 ] && [ "$status_code" -lt 400 ]; then
        echo -e "${GREEN}✓ OK${NC} (${response_time_ms}ms, Status: ${status_code})"
        return 0
    else
        echo -e "${YELLOW}⚠ WARNING${NC} (${response_time_ms}ms, Status: ${status_code})"
        return 2
    fi
}

# Network Path 1: Browser → WebUI Frontend
echo -e "${BLUE}Path 1: Browser → WebUI Frontend (3009)${NC}"
test_path "WebUI Frontend" "http://localhost:3009/"

# Network Path 2: Browser → BFF → WebUI Backend
echo ""
echo -e "${BLUE}Path 2: Browser → BFF (3009) → WebUI Backend (8080)${NC}"
test_path "WebUI Backend Health" "http://localhost:3009/api/webui/health"

# Network Path 3: Browser → BFF
echo ""
echo -e "${BLUE}Path 3: Browser → BFF (3009)${NC}"
test_path "BFF Health" "http://localhost:3009/health"
test_path "BFF Monitoring" "http://localhost:3009/monitoring/traces?limit=1"
test_path "BFF MCP Servers" "http://localhost:3009/mcp/servers"
test_path "BFF DataCloud" "http://localhost:3009/datacloud/connections"

# Network Path 4: Browser → BFF → Kong → MCP
echo ""
echo -e "${BLUE}Path 4: Browser → BFF (3009) → Kong (8000) → MCP Server${NC}"
MCP_SERVERS=$(curl -s http://localhost:3009/mcp/servers 2>/dev/null || echo "[]")
if echo "$MCP_SERVERS" | grep -q '"id"'; then
    SERVER_ID=$(echo "$MCP_SERVERS" | grep -oE '"id"\s*:\s*"[^"]+"' | head -1 | sed 's/.*"id"\s*:\s*"\([^"]*\)".*/\1/')
    if [ -n "$SERVER_ID" ]; then
        test_path "MCP via Kong" "http://localhost:3009/api/mcp/servers/${SERVER_ID}/tools"
    else
        echo "  ⚠ No MCP servers found"
    fi
else
    echo "  ⚠ No MCP servers found"
fi

# Network Path 5: Internal Docker Network
echo ""
echo -e "${BLUE}Path 5: Internal Docker Network${NC}"
echo "  Testing internal service connectivity..."

# Check if we can access services from backend container
if docker compose exec -T backend curl -s http://webui:8080/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Backend → WebUI Backend${NC}"
else
    echo -e "  ${YELLOW}⚠ Backend → WebUI Backend (may not be ready)${NC}"
fi

if docker compose exec -T backend curl -s http://kong:8000/status > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Backend → Kong Gateway${NC}"
else
    echo -e "  ${YELLOW}⚠ Backend → Kong Gateway (may not be ready)${NC}"
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${BLUE}Network Topology Verification:${NC}"
echo ""
echo "  External Access (Port 3009):"
echo "    Browser → http://localhost:3009"
echo ""
echo "  Internal Network:"
echo "    BFF → WebUI Backend: http://webui:8080"
echo "    BFF → Kong Gateway: http://kong:8000"
echo "    Kong → MCP Servers: (via Kong routes)"
echo ""
echo -e "${GREEN}✓ Network path verification complete${NC}"
echo ""

