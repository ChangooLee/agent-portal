#!/usr/bin/env node

/**
 * Layout Hierarchy Analysis Script
 * Analyzes layout structure and inheritance relationships
 */

const fs = require('fs');
const path = require('path');

const WEBUI_DIR = path.join(__dirname, '../webui/src');
const OUTPUT_DIR = path.join(__dirname, '../webui/.skills');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

/**
 * Find all layout files
 */
function findLayoutFiles() {
  const layouts = [];
  const routesDir = path.join(WEBUI_DIR, 'routes');
  
  function scanDirectory(dir, basePath = '') {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      const relativePath = path.join(basePath, entry.name);
      
      if (entry.isDirectory()) {
        scanDirectory(fullPath, relativePath);
      } else if (entry.name === '+layout.svelte' || entry.name === '+layout.js') {
        const content = fs.readFileSync(fullPath, 'utf-8');
        const routePath = relativePath
          .replace('routes/', '/')
          .replace('/(app)/', '')
          .replace(/\+layout\.(svelte|js)$/, '')
          .replace(/\[(\w+)\]/g, ':$1');
        
        layouts.push({
          path: relativePath,
          fullPath: fullPath,
          routePath: routePath || '/',
          type: entry.name.endsWith('.js') ? 'js' : 'svelte',
          content: content
        });
      }
    }
  }
  
  scanDirectory(routesDir);
  return layouts;
}

/**
 * Find all page files
 */
function findPageFiles() {
  const pages = [];
  const routesDir = path.join(WEBUI_DIR, 'routes');
  
  function scanDirectory(dir, basePath = '') {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      const relativePath = path.join(basePath, entry.name);
      
      if (entry.isDirectory()) {
        scanDirectory(fullPath, relativePath);
      } else if (entry.name === '+page.svelte') {
        const routePath = relativePath
          .replace('routes/', '/')
          .replace('/(app)/', '')
          .replace(/\+page\.svelte$/, '')
          .replace(/\[(\w+)\]/g, ':$1');
        
        pages.push({
          path: relativePath,
          fullPath: fullPath,
          routePath: routePath || '/'
        });
      }
    }
  }
  
  scanDirectory(routesDir);
  return pages;
}

/**
 * Determine which layouts apply to a page
 */
function getLayoutsForPage(page, layouts) {
  const pagePath = page.path;
  const applicableLayouts = [];
  
  // Sort layouts by depth (deepest first)
  const sortedLayouts = layouts.sort((a, b) => {
    const aDepth = a.path.split('/').length;
    const bDepth = b.path.split('/').length;
    return bDepth - aDepth;
  });
  
  for (const layout of sortedLayouts) {
    const layoutDir = path.dirname(layout.path);
    const pageDir = path.dirname(pagePath);
    
    // Check if layout is in the same directory or parent directory
    if (pageDir.startsWith(layoutDir) || layoutDir === '.' || layoutDir === 'routes') {
      applicableLayouts.push({
        layout: layout.path,
        routePath: layout.routePath,
        type: layout.type
      });
    }
  }
  
  // Always include root layout if exists
  const rootLayout = layouts.find(l => l.path === 'routes/+layout.svelte' || l.path === 'routes/(app)/+layout.svelte');
  if (rootLayout && !applicableLayouts.find(al => al.layout === rootLayout.path)) {
    applicableLayouts.unshift({
      layout: rootLayout.path,
      routePath: rootLayout.routePath,
      type: rootLayout.type
    });
  }
  
  return applicableLayouts;
}

/**
 * Analyze layout hierarchy
 */
function analyzeLayoutHierarchy() {
  const layouts = findLayoutFiles();
  const pages = findPageFiles();
  
  const layoutMap = {};
  const pageLayoutMap = {};
  
  // Build layout hierarchy
  layouts.forEach(layout => {
    const layoutDir = path.dirname(layout.path);
    const depth = layoutDir.split('/').filter(p => p && p !== 'routes').length;
    
    layoutMap[layout.path] = {
      path: layout.path,
      routePath: layout.routePath,
      type: layout.type,
      depth: depth,
      directory: layoutDir,
      children: []
    };
  });
  
  // Find parent-child relationships
  Object.keys(layoutMap).forEach(layoutPath => {
    const layout = layoutMap[layoutPath];
    const parentLayout = Object.values(layoutMap).find(l => 
      l.path !== layout.path && 
      layout.directory.startsWith(l.directory) &&
      l.depth < layout.depth
    );
    
    if (parentLayout) {
      if (!parentLayout.children) parentLayout.children = [];
      parentLayout.children.push(layout.path);
    }
  });
  
  // Map pages to layouts
  pages.forEach(page => {
    const applicableLayouts = getLayoutsForPage(page, layouts);
    pageLayoutMap[page.routePath] = {
      page: page.path,
      routePath: page.routePath,
      layouts: applicableLayouts,
      layoutChain: applicableLayouts.map(al => al.layout)
    };
  });
  
  // Extract layout features
  const layoutFeatures = {};
  layouts.forEach(layout => {
    const content = layout.content;
    const features = {
      hasNav: /<nav|<Navbar/.test(content),
      hasSidebar: /Sidebar|sidebar/.test(content),
      hasTabs: /tab|Tab/.test(content),
      hasBreadcrumb: /breadcrumb|Breadcrumb/.test(content),
      hasHeader: /<header|<h1|<h2/.test(content),
      hasFooter: /<footer/.test(content),
      imports: [],
      components: []
    };
    
    // Extract imports
    const importRegex = /import\s+.*?\s+from\s+['"]([^'"]+)['"]/g;
    let match;
    while ((match = importRegex.exec(content)) !== null) {
      features.imports.push(match[1]);
      if (match[1].includes('/components/')) {
        features.components.push(match[1]);
      }
    }
    
    layoutFeatures[layout.path] = features;
  });
  
  return {
    metadata: {
      generatedAt: new Date().toISOString(),
      layoutCount: layouts.length,
      pageCount: pages.length
    },
    layouts: Object.values(layoutMap),
    layoutFeatures: layoutFeatures,
    pageLayoutMap: pageLayoutMap,
    hierarchy: buildHierarchyTree(layoutMap)
  };
}

/**
 * Build hierarchy tree structure
 */
function buildHierarchyTree(layoutMap) {
  const rootLayouts = Object.values(layoutMap).filter(l => l.depth === 0 || l.directory === 'routes' || l.directory === '.');
  
  function buildTree(layout) {
    return {
      path: layout.path,
      routePath: layout.routePath,
      type: layout.type,
      depth: layout.depth,
      children: (layout.children || []).map(childPath => {
        const childLayout = layoutMap[childPath];
        return childLayout ? buildTree(childLayout) : null;
      }).filter(Boolean)
    };
  }
  
  return rootLayouts.map(buildTree);
}

/**
 * Main function
 */
function main() {
  console.log('Analyzing layout hierarchy...');
  
  const hierarchy = analyzeLayoutHierarchy();
  
  const outputPath = path.join(OUTPUT_DIR, 'ui-layouts.json');
  fs.writeFileSync(outputPath, JSON.stringify(hierarchy, null, 2));
  
  console.log(`\nLayout hierarchy written to: ${outputPath}`);
  console.log(`Found ${hierarchy.metadata.layoutCount} layouts`);
  console.log(`Mapped ${hierarchy.metadata.pageCount} pages to layouts`);
  console.log(`\nLayout hierarchy tree:`);
  hierarchy.hierarchy.forEach(root => {
    console.log(`  ${root.path} (depth: ${root.depth})`);
    if (root.children && root.children.length > 0) {
      root.children.forEach(child => {
        console.log(`    └─ ${child.path} (depth: ${child.depth})`);
      });
    }
  });
}

main();

