#!/bin/bash
# WebUI Database Backup Script
# 백업 webui.db 파일을 지정된 위치에 저장
# Usage: ./scripts/backup-webui-db.sh [backup_dir]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 백업 디렉토리 설정 (기본값: ./backups)
BACKUP_DIR="${1:-./backups}"
DB_PATH="webui/backend/data/webui.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/webui.db.${TIMESTAMP}.backup"

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

# DB 파일 존재 확인
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database file not found at $DB_PATH"
    exit 1
fi

# 백업 실행
echo "Backing up WebUI database..."
cp "$DB_PATH" "$BACKUP_FILE"

# 백업 파일 크기 확인
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✓ Backup completed: $BACKUP_FILE ($BACKUP_SIZE)"

# 최근 백업 5개만 유지 (선택사항)
if [ -d "$BACKUP_DIR" ]; then
    cd "$BACKUP_DIR"
    ls -t webui.db.*.backup 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
    echo "✓ Old backups cleaned (keeping latest 5)"
fi

echo "Backup location: $BACKUP_FILE"
