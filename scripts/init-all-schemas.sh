#!/bin/bash
# Agent Portal MariaDB 스키마 전체 초기화
# Usage: ./scripts/init-all-schemas.sh

set -e

echo "=== Agent Portal MariaDB 스키마 초기화 ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
MARIADB_CONTAINER="agent-portal-mariadb-1"
MARIADB_USER="root"
MARIADB_PASSWORD="${MARIADB_ROOT_PASSWORD:-rootpass}"
MARIADB_DATABASE="${MARIADB_DATABASE:-agent_portal}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to execute SQL file
execute_sql() {
    local sql_file="$1"
    local description="$2"
    
    if [ ! -f "$sql_file" ]; then
        echo -e "${RED}✗ File not found: $sql_file${NC}"
        return 1
    fi
    
    echo -n "  → $description... "
    if docker exec -i "$MARIADB_CONTAINER" mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE" < "$sql_file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
        return 1
    fi
}

# Check if MariaDB container is running
echo "1. MariaDB 컨테이너 확인..."
if ! docker ps --format '{{.Names}}' | grep -q "^${MARIADB_CONTAINER}$"; then
    echo -e "${RED}✗ MariaDB container is not running${NC}"
    echo "  Run: docker compose up -d mariadb"
    exit 1
fi
echo -e "  ${GREEN}✓ $MARIADB_CONTAINER is running${NC}"

# Wait for MariaDB to be ready
echo ""
echo "2. MariaDB 연결 대기..."
MAX_RETRIES=30
RETRY_COUNT=0
until docker exec "$MARIADB_CONTAINER" mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" -e "SELECT 1" &>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo -e "${RED}✗ MariaDB is not ready after $MAX_RETRIES attempts${NC}"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}✓ MariaDB is ready${NC}"

# Initialize schemas (order matters due to foreign key dependencies)
echo ""
echo "3. 스키마 초기화..."

# Project schema first (no dependencies)
execute_sql "$SCRIPT_DIR/init-project-schema.sql" "Project 스키마 (projects, teams)"

# MCP schema (depends on projects)
execute_sql "$SCRIPT_DIR/init-mcp-schema.sql" "MCP 스키마 (mcp_servers, mcp_server_tools)"

# Data Cloud schema (no dependencies)
execute_sql "$SCRIPT_DIR/init-datacloud-schema.sql" "Data Cloud 스키마 (db_connections)"

# Verify
echo ""
echo "4. 테이블 확인..."
TABLES=$(docker exec "$MARIADB_CONTAINER" mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE" -e "SHOW TABLES;" 2>/dev/null | tail -n +2 | wc -l)
echo -e "  ${GREEN}✓ $TABLES 테이블 생성됨${NC}"

# List tables
echo ""
echo "5. 생성된 테이블 목록:"
docker exec "$MARIADB_CONTAINER" mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE" -e "SHOW TABLES;" 2>/dev/null | tail -n +2 | while read table; do
    echo "  - $table"
done

echo ""
echo -e "${GREEN}=== 스키마 초기화 완료 ===${NC}"

