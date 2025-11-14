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

# 2. 학습 내용 자동 통합
echo "🔄 Integrating Learnings to Rules"
echo "----------------------------------"
echo ""

if command -v node &> /dev/null; then
    echo "Running integrate-learnings-to-rules.js..."
    node scripts/integrate-learnings-to-rules.js
    echo ""
else
    echo "⚠️  Node.js not found, skipping automatic integration"
    echo ""
fi

# 3. 반복 패턴 분석
echo "🔍 Repeated Pattern Analysis"
echo "-----------------------------"
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
    echo "Patterns appearing 3+ times should be integrated into .mdc files."
    echo ""
fi

# 4. 가드레일 업데이트 제안
echo "🛡️  Guardrail Update Recommendations"
echo "--------------------------------------"
echo ""

if [ -f "$LEARNING_DIR/bug-fixes.md" ]; then
    echo "Bug fixes that should become guardrails:"
    grep -h "^## " "$LEARNING_DIR/bug-fixes.md" | tail -5 | sed 's/^##/   /'
    echo ""
    echo "Review these and add to CLAUDE.md or AGENTS.md as needed."
    echo ""
fi

# 5. 문서 동기화 상태
echo "📋 Document Sync Status"
echo "-----------------------"
echo ""

if [ -f "./scripts/sync-docs.sh" ]; then
    ./scripts/sync-docs.sh
else
    echo "⚠️  sync-docs.sh not found, skipping..."
fi

echo ""
echo ""

# 6. Skills 시스템 업데이트
echo "🎯 Skills System Update"
echo "------------------------"
echo ""

if [ -f "./scripts/update-ui-skills.sh" ]; then
    echo "Running UI Skills update..."
    ./scripts/update-ui-skills.sh
    echo ""
else
    echo "⚠️  update-ui-skills.sh not found, skipping..."
    echo ""
fi

# 7. 권장 사항
echo "💡 Recommended Actions"
echo "----------------------"
echo ""
echo "Automatic tasks completed:"
echo "  ✅ Learning integration to .mdc files"
echo "  ✅ Repeated pattern analysis"
echo "  ✅ Skills system update"
echo ""
echo "Manual review needed:"
echo "  1. Review new guardrails (from bug fixes)"
echo "  2. Update CLAUDE.md with critical patterns"
echo "  3. Update AGENTS.md with workflow improvements"
echo "  4. Review preferences and apply to project defaults"
echo ""
echo "📝 Integration Checklist:"
echo "   [ ] Review Learning History sections in .mdc files"
echo "   [ ] Add critical bug fixes to CLAUDE.md as guardrails"
echo "   [ ] Update coding standards if new patterns emerged"
echo "   [ ] Apply preferences to project settings"
echo "   [ ] Commit documentation updates"
echo ""
echo "🎯 Next Steps:"
echo "   1. Review auto-integrated learning history"
echo "   2. Manually add critical patterns to core docs"
echo "   3. Clean up old/redundant learning entries (optional)"
echo "   4. Create PR for documentation updates"
echo ""
echo "✅ Weekly review completed"

