#!/bin/bash
# .env 파일 보호 스크립트
# git clean 실행 전에 .env 파일을 백업하고, 실행 후 복구

ENV_FILE=".env"
BACKUP_FILE=".env.backup.protected"

# 백업
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$BACKUP_FILE"
    echo "✓ .env 파일 백업 완료: $BACKUP_FILE"
fi

# git clean 실행 (사용자가 직접 실행)
echo "⚠️  git clean 실행 후 다음 명령어로 .env 파일을 복구하세요:"
echo "   ./scripts/restore-env.sh"
