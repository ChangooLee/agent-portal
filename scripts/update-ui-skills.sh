#!/bin/bash

# UI Skills Auto-Update Script
# Updates UI structure and search index files when UI code changes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEBUI_DIR="$PROJECT_ROOT/webui"

# Analysis scripts
ANALYZE_STRUCTURE="$SCRIPT_DIR/analyze-ui-structure.js"
ANALYZE_PATTERNS="$SCRIPT_DIR/analyze-ui-patterns.js"
ANALYZE_LAYOUTS="$SCRIPT_DIR/analyze-layout-hierarchy.js"
ANALYZE_NAVIGATION="$SCRIPT_DIR/analyze-navigation-structure.js"
ANALYZE_STYLES="$SCRIPT_DIR/analyze-global-styles.js"
ENHANCE_INDEX="$SCRIPT_DIR/enhance-search-index.js"
ANALYZE_BACKEND="$SCRIPT_DIR/analyze-backend-structure.js"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Updating UI Skills files...${NC}"

# Check if webui directory exists
if [ ! -d "$WEBUI_DIR" ]; then
    echo -e "${RED}Error: webui directory not found at $WEBUI_DIR${NC}"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed or not in PATH${NC}"
    exit 1
fi

# Run all analysis scripts
cd "$PROJECT_ROOT"

echo -e "${YELLOW}Running UI structure analysis...${NC}"
if [ -f "$ANALYZE_STRUCTURE" ]; then
    node "$ANALYZE_STRUCTURE"
else
    echo -e "${RED}Warning: analyze-ui-structure.js not found${NC}"
fi

echo -e "${YELLOW}Running UI patterns analysis...${NC}"
if [ -f "$ANALYZE_PATTERNS" ]; then
    node "$ANALYZE_PATTERNS"
else
    echo -e "${RED}Warning: analyze-ui-patterns.js not found${NC}"
fi

echo -e "${YELLOW}Running layout hierarchy analysis...${NC}"
if [ -f "$ANALYZE_LAYOUTS" ]; then
    node "$ANALYZE_LAYOUTS"
else
    echo -e "${RED}Warning: analyze-layout-hierarchy.js not found${NC}"
fi

echo -e "${YELLOW}Running navigation structure analysis...${NC}"
if [ -f "$ANALYZE_NAVIGATION" ]; then
    node "$ANALYZE_NAVIGATION"
else
    echo -e "${RED}Warning: analyze-navigation-structure.js not found${NC}"
fi

echo -e "${YELLOW}Running global styles analysis...${NC}"
if [ -f "$ANALYZE_STYLES" ]; then
    node "$ANALYZE_STYLES"
else
    echo -e "${RED}Warning: analyze-global-styles.js not found${NC}"
fi

echo -e "${YELLOW}Enhancing search index...${NC}"
if [ -f "$ENHANCE_INDEX" ]; then
    node "$ENHANCE_INDEX"
else
    echo -e "${RED}Warning: enhance-search-index.js not found${NC}"
fi

echo -e "${YELLOW}Running backend structure analysis...${NC}"
if [ -f "$ANALYZE_BACKEND" ]; then
    node "$ANALYZE_BACKEND"
else
    echo -e "${RED}Warning: analyze-backend-structure.js not found${NC}"
fi

echo -e "${GREEN}✓ UI Skills files updated successfully${NC}"

# Show summary
SKILLS_DIR="$WEBUI_DIR/.skills"
if [ -d "$SKILLS_DIR" ]; then
    echo -e "${GREEN}Summary:${NC}"
    echo -e "  - Skills directory: $SKILLS_DIR"
    echo -e "  - Files generated at: $(date)"
    
    ls -lh "$SKILLS_DIR"/*.json 2>/dev/null | awk '{print "    - " $9 " (" $5 ")"}'
fi

