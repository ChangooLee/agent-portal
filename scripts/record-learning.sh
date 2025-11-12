#!/bin/bash
# 학습 내용 수동 기록 스크립트

# 사용법 체크
if [ $# -lt 2 ]; then
    echo "Usage: $0 <category> <content>"
    echo ""
    echo "Categories:"
    echo "  UI   - UI development patterns"
    echo "  API  - Backend API patterns"
    echo "  BUG  - Bug fixes"
    echo "  PREF - Developer preferences"
    echo ""
    echo "Example:"
    echo "  $0 \"UI\" \"Rounded-lg buttons are more modern than border-b-2 style\""
    exit 1
fi

CATEGORY="$1"
CONTENT="$2"
DATE=$(date +%Y-%m-%d)
COMMIT_HASH=$(git log -1 --pretty=%h 2>/dev/null || echo "N/A")

# 카테고리에 따라 파일 선택
case "$CATEGORY" in
    UI|ui)
        LEARNING_FILE=".cursor/learnings/ui-patterns.md"
        CATEGORY_NAME="UI Pattern"
        ;;
    API|api)
        LEARNING_FILE=".cursor/learnings/api-patterns.md"
        CATEGORY_NAME="API Pattern"
        ;;
    BUG|bug)
        LEARNING_FILE=".cursor/learnings/bug-fixes.md"
        CATEGORY_NAME="Bug Fix"
        ;;
    PREF|pref|preference)
        LEARNING_FILE=".cursor/learnings/preferences.md"
        CATEGORY_NAME="Preference"
        ;;
    *)
        echo "❌ Error: Unknown category '$CATEGORY'"
        echo "Valid categories: UI, API, BUG, PREF"
        exit 1
        ;;
esac

# 학습 내용 추가
echo "" >> "$LEARNING_FILE"
echo "## $DATE: Manual Entry" >> "$LEARNING_FILE"
echo "" >> "$LEARNING_FILE"
echo "**내용**: $CONTENT" >> "$LEARNING_FILE"
if [ "$COMMIT_HASH" != "N/A" ]; then
    echo "**커밋**: $COMMIT_HASH" >> "$LEARNING_FILE"
fi
echo "" >> "$LEARNING_FILE"
echo "---" >> "$LEARNING_FILE"

echo "✅ Learning recorded in $LEARNING_FILE"
echo ""
echo "📝 Entry:"
echo "   Category: $CATEGORY_NAME"
echo "   Date:     $DATE"
echo "   Content:  $CONTENT"
if [ "$COMMIT_HASH" != "N/A" ]; then
    echo "   Commit:   $COMMIT_HASH"
fi

