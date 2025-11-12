#!/bin/bash
# 주간 리뷰 스크립트 (매주 금요일 실행 권장)

echo "🗓️  Weekly Review - Agent Portal"
echo "================================"
echo ""

DATE=$(date +%Y-%m-%d)
WEEK=$(date +%V)

echo "📅 Date: $DATE (Week $WEEK)"
echo ""

# 1. 학습 내용 요약
echo "📚 Learning Summary"
echo "-------------------"

LEARNING_DIR=".cursor/learnings"
if [ -d "$LEARNING_DIR" ]; then
    echo ""
    echo "UI Patterns:"
    if [ -f "$LEARNING_DIR/ui-patterns.md" ]; then
        ENTRIES=$(grep -c "^## " "$LEARNING_DIR/ui-patterns.md")
        echo "  - Total entries: $ENTRIES"
        echo "  - Recent entries (last 7 days):"
        grep "^## " "$LEARNING_DIR/ui-patterns.md" | tail -5 | sed 's/^##/   /'
    fi
    
    echo ""
    echo "API Patterns:"
    if [ -f "$LEARNING_DIR/api-patterns.md" ]; then
        ENTRIES=$(grep -c "^## " "$LEARNING_DIR/api-patterns.md")
        echo "  - Total entries: $ENTRIES"
        echo "  - Recent entries (last 7 days):"
        grep "^## " "$LEARNING_DIR/api-patterns.md" | tail -5 | sed 's/^##/   /'
    fi
    
    echo ""
    echo "Bug Fixes:"
    if [ -f "$LEARNING_DIR/bug-fixes.md" ]; then
        ENTRIES=$(grep -c "^## " "$LEARNING_DIR/bug-fixes.md")
        echo "  - Total entries: $ENTRIES"
        echo "  - Recent entries (last 7 days):"
        grep "^## " "$LEARNING_DIR/bug-fixes.md" | tail -5 | sed 's/^##/   /'
    fi
    
    echo ""
    echo "Preferences:"
    if [ -f "$LEARNING_DIR/preferences.md" ]; then
        ENTRIES=$(grep -c "^## " "$LEARNING_DIR/preferences.md")
        echo "  - Total entries: $ENTRIES"
        echo "  - Positive feedback (✅):"
        grep -c "✅" "$LEARNING_DIR/preferences.md" | sed 's/^/     /'
        echo "  - Negative feedback (❌):"
        grep -c "❌" "$LEARNING_DIR/preferences.md" | sed 's/^/     /'
    fi
fi

echo ""
echo ""

# 2. 반복 패턴 식별
echo "🔍 Repeated Patterns"
echo "--------------------"
echo ""

if [ -d "$LEARNING_DIR" ]; then
    echo "Top repeated keywords (from '재사용:' and '향후 적용:' fields):"
    grep -h -E "^\*\*(재사용|향후 적용)\*\*:" "$LEARNING_DIR"/*.md 2>/dev/null | \
        sed 's/\*\*.*\*\*://g' | \
        tr '[:upper:]' '[:lower:]' | \
        tr ' ' '\n' | \
        grep -v '^$' | \
        sort | uniq -c | sort -rn | head -10 | \
        sed 's/^/   /'
    
    echo ""
fi

# 3. 문서 동기화 상태
echo "📋 Document Sync Status"
echo "-----------------------"
echo ""

./scripts/sync-docs.sh

echo ""
echo ""

# 4. 권장 사항
echo "💡 Recommended Actions"
echo "----------------------"
echo ""
echo "1. Review learning entries and identify patterns"
echo "2. Update CLAUDE.md with new guardrails (if failures found)"
echo "3. Update .cursor/rules/ with new patterns"
echo "4. Update AGENTS.md with workflow improvements"
echo "5. Run: ./scripts/sync-docs.sh"
echo ""
echo "📝 Integration Checklist:"
echo "   [ ] Review learnings for repeated patterns"
echo "   [ ] Add new guardrails to CLAUDE.md (failure cases)"
echo "   [ ] Add new patterns to .cursor/rules/ui-development.mdc"
echo "   [ ] Add new patterns to .cursor/rules/backend-api.mdc"
echo "   [ ] Update preferences in .cursor/rules/learning-patterns.mdc"
echo "   [ ] Commit documentation updates"
echo ""
echo "🎯 Next Steps:"
echo "   1. Review this week's learnings"
echo "   2. Integrate repeated patterns into core documents"
echo "   3. Clean up old/redundant learning entries (optional)"
echo ""
echo "✅ Weekly review completed"

