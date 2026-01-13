#!/bin/bash
# .env 파일 복구 스크립트

ENV_FILE=".env"
BACKUP_FILE=".env.backup.protected"

if [ -f "$BACKUP_FILE" ]; then
    cp "$BACKUP_FILE" "$ENV_FILE"
    echo "✓ .env 파일 복구 완료"
    rm "$BACKUP_FILE"
else
    echo "✗ 백업 파일을 찾을 수 없습니다: $BACKUP_FILE"
    echo "  .env 파일을 수동으로 복구해야 합니다."
    exit 1
fi
