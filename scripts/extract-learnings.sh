#!/bin/bash
# Git 히스토리에서 학습 내용 추출 스크립트

echo "🔍 Extracting learnings from Git history..."

# 커밋 히스토리에서 "Learning:" 키워드 검색
COMMITS=$(git log --all --grep="Learning:" --pretty=format:"%H|%ad|%s|%b" --date=short)

if [ -z "$COMMITS" ]; then
    echo "  ℹ️  No commits with 'Learning:' keyword found."
    exit 0
fi

echo "  📝 Found commits with learning content:"
echo ""

# 각 커밋 처리
while IFS='|' read -r HASH DATE SUBJECT BODY; do
    # Learning 내용 추출
    LEARNING=$(echo "$BODY" | grep -i "^Learning:" | sed 's/^Learning://g' | xargs)
    
    if [ -n "$LEARNING" ]; then
        echo "  Commit: $HASH ($(echo $HASH | cut -c1-7))"
        echo "  Date:   $DATE"
        echo "  Learning: $LEARNING"
        echo ""
        
        # 학습 내용 분류 (커밋 메시지 기반)
        if echo "$SUBJECT $BODY" | grep -qi "ui\|svelte\|component\|style"; then
            LEARNING_FILE=".cursor/learnings/ui-patterns.md"
            CATEGORY="UI"
        elif echo "$SUBJECT $BODY" | grep -qi "api\|backend\|fastapi\|route"; then
            LEARNING_FILE=".cursor/learnings/api-patterns.md"
            CATEGORY="API"
        elif echo "$SUBJECT $BODY" | grep -qi "bug\|fix\|error"; then
            LEARNING_FILE=".cursor/learnings/bug-fixes.md"
            CATEGORY="BUG"
        else
            LEARNING_FILE=".cursor/learnings/preferences.md"
            CATEGORY="GENERAL"
        fi
        
        # 중복 확인 (간단한 체크: 동일한 날짜와 커밋 해시)
        SHORT_HASH=$(echo $HASH | cut -c1-7)
        if grep -q "$SHORT_HASH" "$LEARNING_FILE" 2>/dev/null; then
            echo "  ⏭️  Skipping (already recorded)"
        else
            # 학습 내용 추가
            echo "" >> "$LEARNING_FILE"
            echo "## $DATE: Extracted from commit $SHORT_HASH" >> "$LEARNING_FILE"
            echo "" >> "$LEARNING_FILE"
            echo "**내용**: $LEARNING" >> "$LEARNING_FILE"
            echo "**커밋**: $SHORT_HASH" >> "$LEARNING_FILE"
            echo "**제목**: $SUBJECT" >> "$LEARNING_FILE"
            echo "" >> "$LEARNING_FILE"
            echo "---" >> "$LEARNING_FILE"
            
            echo "  ✅ Recorded to $LEARNING_FILE"
        fi
        echo ""
    fi
done <<< "$COMMITS"

echo "✅ Learning extraction completed"
echo ""
echo "📚 Review extracted learnings in .cursor/learnings/"

