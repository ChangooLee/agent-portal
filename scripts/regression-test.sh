#!/bin/bash
# Regression test script for Agent Portal
# Tests all critical network paths and generates test report
# Usage: ./scripts/regression-test.sh

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

# Test results
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results"
mkdir -p "$TEST_RESULTS_DIR"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
REPORT_FILE="$TEST_RESULTS_DIR/regression-test-$(date +%Y%m%d-%H%M%S).json"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0
START_TIME=$(date +%s)

# Test results array (JSON format)
TESTS_JSON="["

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         Agent Portal - Regression Test Suite                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Function to run a test
run_test() {
    local test_name="$1"
    local test_path="$2"
    local test_command="$3"
    local expected_status="${4:-200}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    local test_start=$(date +%s%N)
    
    echo -n "  Test ${TOTAL_TESTS}: ${test_name}... "
    
    # Run test command
    local response
    local status_code
    local response_time_ms
    
    if response=$(eval "$test_command" 2>&1); then
        status_code=$(echo "$response" | grep -oE 'HTTP/[0-9]+\.[0-9]+ [0-9]+' | grep -oE '[0-9]{3}' | tail -1 || echo "200")
        response_time_ms=$((($(date +%s%N) - test_start) / 1000000))
        
        if [ "$status_code" = "$expected_status" ] || [ "$expected_status" = "any" ]; then
            echo -e "${GREEN}✓ PASSED${NC} (${response_time_ms}ms)"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            local status="passed"
        else
            echo -e "${RED}✗ FAILED${NC} (Status: ${status_code}, Expected: ${expected_status})"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            local status="failed"
        fi
    else
        response_time_ms=$((($(date +%s%N) - test_start) / 1000000))
        echo -e "${RED}✗ FAILED${NC} (Error: ${response:0:100})"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        local status="failed"
        status_code="000"
    fi
    
    # Add to JSON results
    if [ $TOTAL_TESTS -gt 1 ]; then
        TESTS_JSON="${TESTS_JSON},"
    fi
    TESTS_JSON="${TESTS_JSON}{\"name\":\"${test_name}\",\"path\":\"${test_path}\",\"status\":\"${status}\",\"response_time_ms\":${response_time_ms},\"status_code\":\"${status_code}\"}"
}

# Test Suite 1: Basic Connectivity
echo -e "${BLUE}Test Suite 1: Basic Connectivity${NC}"
run_test "BFF Health Check" "Browser → BFF (3010)" \
    "curl -s -w '\nHTTP_CODE:%{http_code}' -o /dev/null http://localhost:3010/health"

run_test "WebUI Frontend" "Browser → WebUI (3010)" \
    "curl -s -w '\nHTTP_CODE:%{http_code}' -I http://localhost:3010/ | tail -1"

# Test Suite 2: WebUI Backend Proxy
echo ""
echo -e "${BLUE}Test Suite 2: WebUI Backend Proxy${NC}"
run_test "WebUI Backend Health" "Browser → BFF (3010) → WebUI Backend (8080)" \
    "curl -s -w '\nHTTP_CODE:%{http_code}' -o /dev/null http://localhost:3010/api/webui/health" "any"

# Test Suite 3: BFF Direct APIs
echo ""
echo -e "${BLUE}Test Suite 3: BFF Direct APIs${NC}"
run_test "Monitoring Traces" "Browser → BFF (3010)" \
    "curl -s -w '\nHTTP_CODE:%{http_code}' -o /dev/null 'http://localhost:3010/monitoring/traces?limit=1'"

run_test "MCP Servers List" "Browser → BFF (3010)" \
    "curl -s -w '\nHTTP_CODE:%{http_code}' -o /dev/null http://localhost:3010/mcp/servers"

run_test "DataCloud Connections" "Browser → BFF (3010)" \
    "curl -s -w '\nHTTP_CODE:%{http_code}' -o /dev/null http://localhost:3010/datacloud/connections"

# Test Suite 4: Kong Gateway Integration (if MCP server exists)
echo ""
echo -e "${BLUE}Test Suite 4: Kong Gateway Integration${NC}"
# Check if any MCP servers exist
MCP_SERVERS=$(curl -s http://localhost:3010/mcp/servers 2>/dev/null || echo "[]")
if echo "$MCP_SERVERS" | grep -q '"id"'; then
    SERVER_ID=$(echo "$MCP_SERVERS" | grep -oE '"id"\s*:\s*"[^"]+"' | head -1 | sed 's/.*"id"\s*:\s*"\([^"]*\)".*/\1/')
    if [ -n "$SERVER_ID" ]; then
        run_test "MCP via Kong" "Browser → BFF (3010) → Kong (8000) → MCP" \
            "curl -s -w '\nHTTP_CODE:%{http_code}' -o /dev/null 'http://localhost:3010/api/mcp/servers/${SERVER_ID}/tools'" "any"
    else
        echo "  ⚠ No MCP servers found, skipping Kong integration tests"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
    fi
else
    echo "  ⚠ No MCP servers found, skipping Kong integration tests"
    SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
fi

# Calculate duration
END_TIME=$(date +%s)
DURATION_MS=$(((END_TIME - START_TIME) * 1000))

# Complete JSON
TESTS_JSON="${TESTS_JSON}]"

# Generate report
cat > "$REPORT_FILE" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "total_tests": ${TOTAL_TESTS},
  "passed": ${PASSED_TESTS},
  "failed": ${FAILED_TESTS},
  "skipped": ${SKIPPED_TESTS},
  "duration_ms": ${DURATION_MS},
  "tests": ${TESTS_JSON}
}
EOF

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo -e "${BLUE}Test Summary:${NC}"
echo "  Total: ${TOTAL_TESTS}"
echo -e "  ${GREEN}Passed: ${PASSED_TESTS}${NC}"
echo -e "  ${RED}Failed: ${FAILED_TESTS}${NC}"
echo -e "  ${YELLOW}Skipped: ${SKIPPED_TESTS}${NC}"
echo "  Duration: ${DURATION_MS}ms"
echo ""
echo -e "${BLUE}Test Report:${NC} ${REPORT_FILE}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi

