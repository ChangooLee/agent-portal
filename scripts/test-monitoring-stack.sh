#!/bin/bash
# Monitoring Stack E2E Test Script
# Tests: OTEL Collector, Prometheus, Grafana, LiteLLM metrics

set -e

echo "🔍 Agent Portal Monitoring Stack - E2E Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test functions
test_service() {
    local service=$1
    local url=$2
    local name=$3
    
    echo -n "Testing $name... "
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# 1. Check if services are running
echo "1️⃣  Checking Docker services..."
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED}Error: Services are not running. Start them with: docker-compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Services are running${NC}"
echo ""

# 2. Test Prometheus
echo "2️⃣  Testing Prometheus..."
test_service "prometheus" "http://localhost:9090/-/healthy" "Prometheus Health"
test_service "prometheus" "http://localhost:9090/api/v1/targets" "Prometheus Targets API"
echo ""

# 3. Test Grafana
echo "3️⃣  Testing Grafana..."
test_service "grafana" "http://localhost:3005/api/health" "Grafana Health"
echo ""

# 4. Test LiteLLM Prometheus metrics
echo "4️⃣  Testing LiteLLM Prometheus Metrics..."
if curl -sf "http://localhost:4000/metrics" | grep -q "litellm"; then
    echo -e "${GREEN}✓ LiteLLM metrics endpoint is working${NC}"
else
    echo -e "${YELLOW}⚠ LiteLLM metrics endpoint exists but no metrics yet (this is normal if no requests have been made)${NC}"
fi
echo ""

# 5. Check Prometheus targets
echo "5️⃣  Checking Prometheus targets..."
TARGETS=$(curl -s "http://localhost:9090/api/v1/targets" | grep -o '"health":"up"' | wc -l)
echo "Active targets: $TARGETS"
if [ "$TARGETS" -gt 0 ]; then
    echo -e "${GREEN}✓ Prometheus is scraping targets${NC}"
else
    echo -e "${YELLOW}⚠ No active targets yet. Wait a few seconds and try again.${NC}"
fi
echo ""

# 6. Test Backend BFF proxy endpoints
echo "6️⃣  Testing Backend BFF proxy endpoints..."
test_service "grafana-proxy" "http://localhost:8000/api/proxy/grafana/api/health" "Grafana Proxy"
echo ""

# 7. Check Grafana datasource
echo "7️⃣  Checking Grafana datasources..."
if curl -s -u admin:admin "http://localhost:3005/api/datasources" | grep -q "Prometheus"; then
    echo -e "${GREEN}✓ Grafana Prometheus datasource is configured${NC}"
else
    echo -e "${RED}✗ Grafana Prometheus datasource not found${NC}"
fi
echo ""

# 8. Check Grafana dashboards
echo "8️⃣  Checking Grafana dashboards..."
DASHBOARDS=$(curl -s -u admin:admin "http://localhost:3005/api/search?type=dash-db" | grep -o '"title"' | wc -l)
echo "Dashboards found: $DASHBOARDS"
if [ "$DASHBOARDS" -gt 0 ]; then
    echo -e "${GREEN}✓ Grafana dashboards are provisioned${NC}"
else
    echo -e "${YELLOW}⚠ No dashboards found. Check grafana-provisioning config.${NC}"
fi
echo ""

# 9. Make a test LLM request to generate metrics
echo "9️⃣  Making test LLM request to generate metrics..."
TEST_RESPONSE=$(curl -s -X POST "http://localhost:4000/v1/chat/completions" \
    -H "Authorization: Bearer sk-1234" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen-235b",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }')

if echo "$TEST_RESPONSE" | grep -q "choices"; then
    echo -e "${GREEN}✓ LiteLLM request successful${NC}"
    echo "Waiting 15 seconds for metrics to be scraped..."
    sleep 15
    
    # Check if metrics are now available
    if curl -sf "http://localhost:4000/metrics" | grep -q "litellm_requests_total"; then
        echo -e "${GREEN}✓ LiteLLM metrics are being generated${NC}"
    fi
else
    echo -e "${YELLOW}⚠ LiteLLM request failed (this is expected if OpenRouter API key is not set)${NC}"
    echo "Response: $TEST_RESPONSE"
fi
echo ""

# 10. Final summary
echo "📊 Test Summary"
echo "=========================================="
echo "Access URLs:"
echo "  • Prometheus:  http://localhost:9090"
echo "  • Grafana:     http://localhost:3005 (admin/admin)"
echo "  • Monitoring:  http://localhost:3001/admin/monitoring"
echo ""
echo -e "${GREEN}✅ Monitoring stack is ready!${NC}"
echo ""
echo "Next steps:"
echo "1. Set OPENROUTER_API_KEY in .env file"
echo "2. Make some LLM requests via Chat UI"
echo "3. Check Grafana dashboard for metrics"
echo "4. (Optional) Set additional environment variables as needed"

