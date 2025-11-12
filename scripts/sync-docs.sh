#!/bin/bash
# 핵심 문서 동기화 스크립트

echo "🔄 Synchronizing core documents..."

# 핵심 문서 목록
CORE_DOCS=("CLAUDE.md" "AGENTS.md" "README.md" "DEVELOP.md")

# 1. 문서 존재 확인
echo "  📋 Checking core documents..."
MISSING_DOCS=()
for doc in "${CORE_DOCS[@]}"; do
    if [ ! -f "$doc" ]; then
        MISSING_DOCS+=("$doc")
    fi
done

if [ ${#MISSING_DOCS[@]} -gt 0 ]; then
    echo "  ⚠️  Missing documents:"
    printf '     - %s\n' "${MISSING_DOCS[@]}"
fi

# 2. Skills 시스템 최신 상태 확인
echo "  🎨 Checking Skills system..."
if [ -d "webui/.skills" ]; then
    SKILLS_FILES=("ui-structure.json" "ui-search-index.json" "ui-patterns.json" "ui-layouts.json" "ui-navigation.json" "ui-styles.json" "ui-class-mapping-guide.json")
    MISSING_SKILLS=()
    for file in "${SKILLS_FILES[@]}"; do
        if [ ! -f "webui/.skills/$file" ]; then
            MISSING_SKILLS+=("$file")
        fi
    done
    
    if [ ${#MISSING_SKILLS[@]} -gt 0 ]; then
        echo "  ⚠️  Missing Skills files:"
        printf '     - %s\n' "${MISSING_SKILLS[@]}"
        echo "     Run: ./scripts/update-ui-skills.sh"
    else
        echo "  ✅ Skills system up to date"
    fi
else
    echo "  ⚠️  Skills directory not found: webui/.skills"
    echo "     Run: ./scripts/update-ui-skills.sh"
fi

# 3. 학습 디렉토리 확인
echo "  📚 Checking learning directory..."
if [ -d ".cursor/learnings" ]; then
    LEARNING_FILES=("ui-patterns.md" "api-patterns.md" "bug-fixes.md" "preferences.md")
    MISSING_LEARNING=()
    for file in "${LEARNING_FILES[@]}"; do
        if [ ! -f ".cursor/learnings/$file" ]; then
            MISSING_LEARNING+=("$file")
        fi
    done
    
    if [ ${#MISSING_LEARNING[@]} -gt 0 ]; then
        echo "  ⚠️  Missing learning files:"
        printf '     - %s\n' "${MISSING_LEARNING[@]}"
    else
        echo "  ✅ Learning files up to date"
    fi
else
    echo "  ⚠️  Learning directory not found: .cursor/learnings"
fi

# 4. 문서 크기 확인 (CLAUDE.md는 13KB 이하 권장)
echo "  📏 Checking document sizes..."
if [ -f "CLAUDE.md" ]; then
    CLAUDE_SIZE=$(wc -c < "CLAUDE.md")
    CLAUDE_KB=$((CLAUDE_SIZE / 1024))
    if [ $CLAUDE_KB -gt 13 ]; then
        echo "  ⚠️  CLAUDE.md is ${CLAUDE_KB}KB (recommended: <13KB)"
        echo "     Consider splitting into separate rule files in .cursor/rules/"
    else
        echo "  ✅ CLAUDE.md size OK (${CLAUDE_KB}KB)"
    fi
fi

echo ""
echo "✅ Document synchronization check completed"
echo ""
echo "💡 Tips:"
echo "   - Keep CLAUDE.md concise (<13KB)"
echo "   - Update Skills system after UI changes: ./scripts/update-ui-skills.sh"
echo "   - Record learnings after each task: ./scripts/record-learning.sh"

