#!/bin/bash
# Git hooks 설치 스크립트

echo "📦 Installing Git hooks..."

# 현재 디렉토리 확인
if [ ! -d ".git" ]; then
    echo "❌ Error: .git directory not found. Run this script from the project root."
    exit 1
fi

# .githooks 디렉토리 확인
if [ ! -d ".githooks" ]; then
    echo "❌ Error: .githooks directory not found."
    exit 1
fi

# Git hooks 복사
cp .githooks/pre-commit .git/hooks/pre-commit
cp .githooks/post-commit .git/hooks/post-commit

# 실행 권한 부여
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/post-commit

echo "✅ Git hooks installed successfully!"
echo ""
echo "📝 Hooks installed:"
echo "   - pre-commit:  Document sync check, linting"
echo "   - post-commit: Learning extraction, weekly review reminder"
echo ""
echo "🎯 Usage:"
echo "   Git hooks will run automatically on commit."
echo "   To add learning content, include 'Learning: <content>' in commit messages."
echo ""
echo "📚 Example commit message:"
echo "   git commit -m \"feat(ui): Add new button style"
echo ""
echo "   - Rounded-lg buttons instead of border-b-2"
echo "   - Modern look and feel"
echo ""
echo "   Learning: Rounded-lg buttons are more modern than border-b-2 style\""

