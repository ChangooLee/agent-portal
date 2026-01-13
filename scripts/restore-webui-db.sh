#!/bin/bash
# WebUI Database Restore Script
# 백업된 webui.db 파일을 복구
# Usage: ./scripts/restore-webui-db.sh <backup_file>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 백업 파일 경로 확인
BACKUP_FILE="$1"
DB_PATH="webui/backend/data/webui.db"
DB_DIR="webui/backend/data"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    if [ -d "./backups" ]; then
        ls -lh ./backups/webui.db.*.backup 2>/dev/null | tail -5 || echo "  No backups found"
    else
        echo "  No backups directory found"
    fi
    exit 1
fi

# 백업 파일 존재 확인
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# DB 디렉토리 생성
mkdir -p "$DB_DIR"

# 기존 DB 백업 (복구 전 안전 백업)
if [ -f "$DB_PATH" ]; then
    CURRENT_BACKUP="${DB_PATH}.before_restore.$(date +%Y%m%d_%H%M%S)"
    echo "Creating safety backup of current database..."
    cp "$DB_PATH" "$CURRENT_BACKUP"
    echo "✓ Current DB backed up to: $CURRENT_BACKUP"
fi

# 복구 실행
echo "Restoring WebUI database from: $BACKUP_FILE"
cp "$BACKUP_FILE" "$DB_PATH"

# 파일 권한 설정
chmod 644 "$DB_PATH"

# 복구 확인
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo "✓ Database restored successfully: $DB_PATH ($DB_SIZE)"
    echo ""
    echo "⚠️  Note: You may need to restart the webui service:"
    echo "   docker compose restart webui"
else
    echo "✗ Error: Database restore failed"
    exit 1
fi
