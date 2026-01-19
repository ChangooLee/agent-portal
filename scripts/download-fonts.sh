#!/bin/bash
# Download free Korean fonts for Slide Studio

set -e

FONTS_DIR="backend/app/services/slide_studio/assets/fonts"
mkdir -p "$FONTS_DIR"

echo "Downloading fonts..."

# Pretendard (from GitHub releases)
# Note: User needs to download manually or use CDN
echo "Pretendard: Please download from https://github.com/orioncactus/pretendard/releases"
echo "  Place files in: $FONTS_DIR/pretendard/"

# Noto Sans KR - Using Google Fonts API (will be loaded via CDN)
echo "Noto Sans KR: Will be loaded via Google Fonts CDN"

# Nanum Gothic - Using Google Fonts API
echo "Nanum Gothic: Will be loaded via Google Fonts CDN"

# Nanum Myeongjo - Using Google Fonts API
echo "Nanum Myeongjo: Will be loaded via Google Fonts CDN"

echo "Font download script completed."
echo "For local fonts, download from:"
echo "  - Pretendard: https://github.com/orioncactus/pretendard"
echo "  - Google Fonts: https://fonts.google.com/"
