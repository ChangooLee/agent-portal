#!/bin/bash
# Download background images for Slide Studio

set -e

BACKGROUNDS_DIR="backend/app/services/slide_studio/assets/backgrounds"
mkdir -p "$BACKGROUNDS_DIR"

echo "Downloading background images..."

# Note: For production, download from:
# - Unsplash API (requires API key)
# - Pexels API (requires API key)
# - Pixabay API (requires API key)
# Or manually download free images

echo "Background images: Please download from:"
echo "  - Unsplash: https://unsplash.com/ (Free, commercial use OK)"
echo "  - Pexels: https://www.pexels.com/ (Free, commercial use OK)"
echo "  - Pixabay: https://pixabay.com/ (Free, commercial use OK)"
echo ""
echo "Place images in: $BACKGROUNDS_DIR/"
echo "Recommended: 1920x1080 PNG files"

# Generate default gradient backgrounds using ImageMagick (if available)
if command -v convert &> /dev/null; then
    echo "Generating default gradient backgrounds..."
    
    # Blue gradient
    convert -size 1920x1080 gradient:"#1e40af-#3b82f6" "$BACKGROUNDS_DIR/gradient_blue_1.png"
    
    # Purple gradient
    convert -size 1920x1080 gradient:"#6366f1-#8b5cf6" "$BACKGROUNDS_DIR/gradient_purple_1.png"
    
    # White solid
    convert -size 1920x1080 xc:white "$BACKGROUNDS_DIR/solid_white.png"
    
    echo "Default backgrounds generated."
else
    echo "ImageMagick not found. Skipping gradient generation."
    echo "Backgrounds will be generated on-the-fly by BackgroundRenderer."
fi

echo "Background download script completed."
