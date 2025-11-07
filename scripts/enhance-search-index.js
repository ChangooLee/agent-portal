#!/usr/bin/env node

/**
 * Enhanced Search Index Script
 * Combines all analysis results into an enhanced search index
 */

const fs = require('fs');
const path = require('path');

const OUTPUT_DIR = path.join(__dirname, '../webui/.skills');

/**
 * Load all analysis files
 */
function loadAnalysisFiles() {
  const files = {
    structure: path.join(OUTPUT_DIR, 'ui-structure.json'),
    searchIndex: path.join(OUTPUT_DIR, 'ui-search-index.json'),
    patterns: path.join(OUTPUT_DIR, 'ui-patterns.json'),
    layouts: path.join(OUTPUT_DIR, 'ui-layouts.json'),
    navigation: path.join(OUTPUT_DIR, 'ui-navigation.json'),
    styles: path.join(OUTPUT_DIR, 'ui-styles.json')
  };
  
  const data = {};
  
  Object.keys(files).forEach(key => {
    const filePath = files[key];
    if (fs.existsSync(filePath)) {
      try {
        data[key] = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      } catch (e) {
        console.warn(`Warning: Could not load ${filePath}: ${e.message}`);
      }
    }
  });
  
  return data;
}

/**
 * Build pattern-based search index
 */
function buildPatternIndex(data) {
  const patternIndex = {};
  
  if (data.patterns && data.patterns.commonPatterns) {
    const patterns = data.patterns.commonPatterns;
    
    // Tab patterns
    if (patterns.tab) {
      patternIndex['tab-pattern'] = {
        type: 'tab',
        activeBorder: patterns.tab.activeBorder,
        activeText: patterns.tab.activeText,
        files: patterns.tab.files || []
      };
    }
    
    // Button patterns
    if (patterns.button) {
      patternIndex['button-pattern'] = {
        type: 'button',
        padding: patterns.button.padding,
        borderRadius: patterns.button.borderRadius,
        hoverBackground: patterns.button.hoverBackground,
        files: patterns.button.files || []
      };
    }
    
    // Card patterns
    if (patterns.card) {
      patternIndex['card-pattern'] = {
        type: 'card',
        background: patterns.card.background,
        borderRadius: patterns.card.borderRadius,
        shadow: patterns.card.shadow,
        padding: patterns.card.padding,
        files: patterns.card.files || []
      };
    }
  }
  
  return patternIndex;
}

/**
 * Build style-based search index
 */
function buildStyleIndex(data) {
  const styleIndex = {};
  
  // Use colorFileMapping if available (more accurate)
  if (data.patterns && data.patterns.colorFileMapping) {
    Object.keys(data.patterns.colorFileMapping).forEach(colorKey => {
      const mapping = data.patterns.colorFileMapping[colorKey];
      styleIndex[colorKey] = {
        routes: mapping.routes || [],
        components: mapping.components || [],
        fileCount: (mapping.routes || []).length + (mapping.components || []).length
      };
    });
  } else if (data.patterns && data.patterns.colorUsage) {
    // Fallback to colorUsage if colorFileMapping not available
    const colors = data.patterns.colorUsage;
    
    // Primary colors
    if (colors.primary && colors.primary.length > 0) {
      colors.primary.forEach(color => {
        if (!styleIndex[color]) styleIndex[color] = { routes: [], components: [] };
      });
    }
    
    // Background colors
    if (colors.background && colors.background.length > 0) {
      colors.background.forEach(color => {
        if (!styleIndex[`bg-${color}`]) {
          styleIndex[`bg-${color}`] = { routes: [], components: [] };
        }
      });
    }
    
    // Text colors
    if (colors.text && colors.text.length > 0) {
      colors.text.forEach(color => {
        if (!styleIndex[`text-${color}`]) {
          styleIndex[`text-${color}`] = { routes: [], components: [] };
        }
      });
    }
  }
  
  return styleIndex;
}

/**
 * Build layout-based search index
 */
function buildLayoutIndex(data) {
  const layoutIndex = {};
  
  if (data.layouts && data.layouts.pageLayoutMap) {
    Object.entries(data.layouts.pageLayoutMap).forEach(([routePath, pageInfo]) => {
      pageInfo.layouts.forEach(layout => {
        const layoutKey = layout.layout;
        if (!layoutIndex[layoutKey]) {
          layoutIndex[layoutKey] = {
            layout: layoutKey,
            routePath: layout.routePath,
            pages: []
          };
        }
        if (!layoutIndex[layoutKey].pages.includes(routePath)) {
          layoutIndex[layoutKey].pages.push(routePath);
        }
      });
    });
  }
  
  return layoutIndex;
}

/**
 * Build navigation-based search index
 */
function buildNavigationIndex(data) {
  const navIndex = {};
  
  if (data.navigation) {
    // Sidebar items
    if (data.navigation.sidebar && data.navigation.sidebar.menuItems) {
      data.navigation.sidebar.menuItems.forEach(item => {
        navIndex[item.href] = {
          type: 'sidebar-menu',
          href: item.href,
          label: item.label,
          depth: 1
        };
      });
    }
    
    // Tab navigation
    if (data.navigation.tabNavigation) {
      data.navigation.tabNavigation.forEach(tabNav => {
        if (!navIndex[tabNav.routePath]) {
          navIndex[tabNav.routePath] = {
            type: 'tab-navigation',
            routePath: tabNav.routePath,
            tabs: tabNav.tabs || [],
            depth: 2
          };
        }
      });
    }
    
    // Admin navigation
    if (data.navigation.adminNavigation && data.navigation.adminNavigation.tabs) {
      navIndex['admin-navigation'] = {
        type: 'admin-tabs',
        tabs: data.navigation.adminNavigation.tabs,
        depth: 2
      };
    }
  }
  
  return navIndex;
}

/**
 * Enhance existing search index
 */
function enhanceSearchIndex(data) {
  const originalIndex = data.searchIndex || {};
  
  // Build new indices
  const patternIndex = buildPatternIndex(data);
  const styleIndex = buildStyleIndex(data);
  const layoutIndex = buildLayoutIndex(data);
  const navigationIndex = buildNavigationIndex(data);
  
  // Enhance style index with color file mapping
  if (data.patterns && data.patterns.colorFileMapping) {
    Object.keys(data.patterns.colorFileMapping).forEach(colorKey => {
      const mapping = data.patterns.colorFileMapping[colorKey];
      if (!styleIndex[colorKey]) {
        styleIndex[colorKey] = {
          routes: mapping.routes || [],
          components: mapping.components || []
        };
      } else {
        // Merge with existing
        styleIndex[colorKey].routes = [...new Set([...styleIndex[colorKey].routes, ...(mapping.routes || [])])];
        styleIndex[colorKey].components = [...new Set([...styleIndex[colorKey].components, ...(mapping.components || [])])];
      }
    });
  }
  
  // Merge with existing keyword index
  const enhancedKeywordIndex = { ...(originalIndex.keywordIndex || {}) };
  
  // Add pattern-based entries
  Object.keys(patternIndex).forEach(key => {
    if (!enhancedKeywordIndex[key]) {
      enhancedKeywordIndex[key] = {
        routes: [],
        components: patternIndex[key].files || [],
        apis: []
      };
    }
  });
  
  // Add style-based entries
  Object.keys(styleIndex).forEach(color => {
    if (!enhancedKeywordIndex[color]) {
      enhancedKeywordIndex[color] = {
        routes: [],
        components: styleIndex[color].components || [],
        apis: []
      };
    }
  });
  
  // Add layout-based entries
  Object.keys(layoutIndex).forEach(layoutKey => {
    const layoutKeyName = `layout-${layoutKey.replace(/[^a-zA-Z0-9]/g, '-')}`;
    if (!enhancedKeywordIndex[layoutKeyName]) {
      enhancedKeywordIndex[layoutKeyName] = {
        routes: layoutIndex[layoutKey].pages || [],
        components: [],
        apis: []
      };
    }
  });
  
  return {
    metadata: {
      generatedAt: new Date().toISOString(),
      version: '2.0.0',
      enhanced: true
    },
    routes: originalIndex.routes || [],
    components: originalIndex.components || [],
    apis: originalIndex.apis || [],
    keywordIndex: enhancedKeywordIndex,
    patternIndex: patternIndex,
    styleIndex: styleIndex,
    layoutIndex: layoutIndex,
    navigationIndex: navigationIndex
  };
}

/**
 * Main function
 */
function main() {
  console.log('Enhancing search index...');
  
  const data = loadAnalysisFiles();
  
  if (!data.searchIndex) {
    console.error('Error: Base search index not found. Run analyze-ui-structure.js first.');
    process.exit(1);
  }
  
  const enhancedIndex = enhanceSearchIndex(data);
  
  const outputPath = path.join(OUTPUT_DIR, 'ui-search-index.json');
  fs.writeFileSync(outputPath, JSON.stringify(enhancedIndex, null, 2));
  
  console.log(`\nEnhanced search index written to: ${outputPath}`);
  console.log(`\nEnhancements:`);
  console.log(`  Pattern index entries: ${Object.keys(enhancedIndex.patternIndex).length}`);
  console.log(`  Style index entries: ${Object.keys(enhancedIndex.styleIndex).length}`);
  console.log(`  Layout index entries: ${Object.keys(enhancedIndex.layoutIndex).length}`);
  console.log(`  Navigation index entries: ${Object.keys(enhancedIndex.navigationIndex).length}`);
  console.log(`  Total keyword index entries: ${Object.keys(enhancedIndex.keywordIndex).length}`);
}

main();

