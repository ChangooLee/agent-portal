#!/usr/bin/env node

/**
 * Navigation Structure Analysis Script
 * Analyzes sidebar menu, tab navigation, and menu hierarchy
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
 * Analyze Sidebar component for menu structure
 */
function analyzeSidebar() {
  const sidebarPath = path.join(WEBUI_DIR, 'lib/components/layout/Sidebar.svelte');
  
  if (!fs.existsSync(sidebarPath)) {
    return null;
  }
  
  const content = fs.readFileSync(sidebarPath, 'utf-8');
  const menuItems = [];
  const menuStructure = [];
  
  // Extract navigation links (href attributes) - more comprehensive
  const linkRegex = /<a[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/g;
  let match;
  let linkIndex = 0;
  
  while ((match = linkRegex.exec(content)) !== null) {
    const href = match[1];
    const innerContent = match[2];
    
    // Extract i18n key or text
    const i18nMatch = innerContent.match(/\$i18n\.t\(['"]([^'"]+)['"]/);
    const textMatch = innerContent.match(/>([^<{]+)</);
    const label = i18nMatch ? i18nMatch[1] : (textMatch ? textMatch[1].trim() : '');
    
    if (href && !href.startsWith('#') && !href.includes('javascript:')) {
      const menuItem = {
        href: href,
        label: label || href,
        type: 'link',
        depth: 1,
        index: linkIndex++
      };
      
      menuItems.push(menuItem);
      menuStructure.push(menuItem);
    }
  }
  
  // Extract buttons that navigate
  const buttonNavRegex = /<button[^>]*on:click=\{([^}]*goto[^}]+)\}[^>]*>([\s\S]*?)<\/button>/g;
  while ((match = buttonNavRegex.exec(content)) !== null) {
    const gotoMatch = match[1].match(/goto\(['"]([^'"]+)['"]/);
    const innerContent = match[2];
    const i18nMatch = innerContent.match(/\$i18n\.t\(['"]([^'"]+)['"]/);
    const label = i18nMatch ? i18nMatch[1] : 'Button Navigation';
    
    if (gotoMatch) {
      menuItems.push({
        href: gotoMatch[1],
        label: label,
        type: 'button',
        depth: 1
      });
    }
  }
  
  // Extract Folder components (menu groups) with better parsing
  const folderRegex = /<Folder[^>]*name=\{([^}]+)\}[^>]*>([\s\S]*?)<\/Folder>/g;
  const folders = [];
  while ((match = folderRegex.exec(content)) !== null) {
    const folderName = match[1].replace(/\$i18n\.t\(['"]([^'"]+)['"]/, '$1');
    const folderContent = match[2];
    
    // Extract items within folder
    const folderItems = [];
    const folderLinkRegex = /<a[^>]*href=["']([^"']+)["'][^>]*>/g;
    let folderLinkMatch;
    while ((folderLinkMatch = folderLinkRegex.exec(folderContent)) !== null) {
      folderItems.push({
        href: folderLinkMatch[1],
        depth: 2
      });
    }
    
    folders.push({
      name: folderName,
      type: 'folder',
      depth: 1,
      items: folderItems,
      itemCount: folderItems.length
    });
  }
  
  // Extract workspace link
  const workspaceMatch = content.match(/href=["']\/workspace["'][^>]*>[\s\S]*?\$i18n\.t\(['"]([^'"]+)['"]/);
  if (workspaceMatch) {
    menuItems.push({
      href: '/workspace',
      label: workspaceMatch[1],
      type: 'link',
      depth: 1
    });
  }
  
  return {
    component: 'Sidebar.svelte',
    componentPath: 'lib/components/layout/Sidebar.svelte',
    menuItems: menuItems,
    menuStructure: menuStructure,
    folders: folders,
    hasSearch: /SearchInput|search/.test(content),
    hasChannels: /Channel|channel/.test(content),
    hasChats: /Chat|chat/.test(content),
    maxDepth: folders.length > 0 ? 2 : 1,
    totalMenuItems: menuItems.length + folders.reduce((sum, f) => sum + (f.itemCount || 0), 0)
  };
}

/**
 * Analyze tab navigation in layouts
 */
function analyzeTabNavigation() {
  const layouts = [];
  const routesDir = path.join(WEBUI_DIR, 'routes');
  
  function scanDirectory(dir, basePath = '') {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      const relativePath = path.join(basePath, entry.name);
      
      if (entry.isDirectory()) {
        scanDirectory(fullPath, relativePath);
      } else if (entry.name === '+layout.svelte') {
        const content = fs.readFileSync(fullPath, 'utf-8');
        
        // Extract tab navigation
        const tabs = [];
        
        // Find tab buttons or links
        const tabRegex = /<button[^>]*class=["'][^"']*tab[^"']*["'][^>]*>|<\/button>|<a[^>]*class=["'][^"']*tab[^"']*["'][^>]*>|<\/a>/g;
        const tabSection = content.match(/<!--\s*Tab[^>]*-->[\s\S]*?<\/div>/i);
        
        if (tabSection || /tab|Tab/.test(content)) {
          // Extract href from links
          const linkRegex = /href=["']([^"']+)["']/g;
          let linkMatch;
          while ((linkMatch = linkRegex.exec(content)) !== null) {
            const href = linkMatch[1];
            if (!tabs.find(t => t.href === href)) {
              tabs.push({
                href: href,
                type: 'tab'
              });
            }
          }
          
          // Extract button text
          const buttonTextRegex = /<button[^>]*>([^<]+)<\/button>/g;
          let buttonMatch;
          while ((buttonMatch = buttonTextRegex.exec(content)) !== null) {
            const text = buttonMatch[1].trim();
            if (text && !tabs.find(t => t.label === text)) {
              tabs.push({
                label: text,
                type: 'tab'
              });
            }
          }
          
          // Extract i18n keys
          const i18nRegex = /\$i18n\.t\(['"]([^'"]+)['"]/g;
          let i18nMatch;
          const i18nKeys = [];
          while ((i18nMatch = i18nRegex.exec(content)) !== null) {
            i18nKeys.push(i18nMatch[1]);
          }
          
          if (tabs.length > 0 || i18nKeys.length > 0) {
            const routePath = relativePath
              .replace('routes/', '/')
              .replace('/(app)/', '')
              .replace(/\+layout\.svelte$/, '');
            
            layouts.push({
              path: relativePath,
              routePath: routePath || '/',
              tabs: tabs,
              i18nKeys: i18nKeys,
              hasTabNavigation: true
            });
          }
        }
      }
    }
  }
  
  scanDirectory(routesDir);
  return layouts;
}

/**
 * Analyze navigation structure in admin layout
 */
function analyzeAdminNavigation() {
  const adminLayoutPath = path.join(WEBUI_DIR, 'routes/(app)/admin/+layout.svelte');
  
  if (!fs.existsSync(adminLayoutPath)) {
    return null;
  }
  
  const content = fs.readFileSync(adminLayoutPath, 'utf-8');
  const tabs = [];
  
  // Extract tab links
  const tabLinkRegex = /<a[^>]*href=["']([^"']+)["'][^>]*class=["'][^"']*\{[^}]*\$\w+\.url\.pathname[^}]*\}[^"']*["'][^>]*>([^<]+)<\/a>/g;
  let match;
  
  while ((match = tabLinkRegex.exec(content)) !== null) {
    tabs.push({
      href: match[1],
      label: match[2].trim(),
      type: 'admin-tab'
    });
  }
  
  // Also extract i18n keys
  const i18nRegex = /\$i18n\.t\(['"]([^'"]+)['"]/g;
  const i18nKeys = [];
  while ((match = i18nRegex.exec(content)) !== null) {
    i18nKeys.push(match[1]);
  }
  
  return {
    layout: 'admin/+layout.svelte',
    tabs: tabs,
    i18nKeys: i18nKeys,
    depth: 1
  };
}

/**
 * Analyze workspace navigation
 */
function analyzeWorkspaceNavigation() {
  const workspaceLayoutPath = path.join(WEBUI_DIR, 'routes/(app)/workspace/+layout.svelte');
  
  if (!fs.existsSync(workspaceLayoutPath)) {
    return null;
  }
  
  const content = fs.readFileSync(workspaceLayoutPath, 'utf-8');
  
  // Extract navigation items
  const navItems = [];
  const linkRegex = /href=["']([^"']+)["']/g;
  let match;
  
  while ((match = linkRegex.exec(content)) !== null) {
    const href = match[1];
    if (href.includes('/workspace/')) {
      navItems.push({
        href: href,
        type: 'workspace-nav'
      });
    }
  }
  
  return {
    layout: 'workspace/+layout.svelte',
    navItems: navItems,
    depth: 1
  };
}

/**
 * Build navigation hierarchy
 */
function buildNavigationHierarchy() {
  const sidebar = analyzeSidebar();
  const tabNavigation = analyzeTabNavigation();
  const adminNav = analyzeAdminNavigation();
  const workspaceNav = analyzeWorkspaceNavigation();
  
  const navigation = {
    metadata: {
      generatedAt: new Date().toISOString()
    },
    sidebar: sidebar,
    tabNavigation: tabNavigation,
    adminNavigation: adminNav,
    workspaceNavigation: workspaceNav,
    hierarchy: {
      level1: [], // Top level (sidebar, main nav)
      level2: [], // Sub-navigation (tabs, sub-menus)
      level3: []  // Deep navigation
    }
  };
  
  // Organize by hierarchy level
  if (sidebar && sidebar.menuItems) {
    navigation.hierarchy.level1.push(...sidebar.menuItems);
  }
  
  if (tabNavigation && tabNavigation.length > 0) {
    navigation.hierarchy.level2.push(...tabNavigation);
  }
  
  if (adminNav && adminNav.tabs) {
    navigation.hierarchy.level2.push(...adminNav.tabs);
  }
  
  // Calculate menu depth
  const maxDepth = Math.max(
    sidebar ? 1 : 0,
    tabNavigation ? 2 : 0,
    adminNav ? 2 : 0,
    workspaceNav ? 2 : 0
  );
  
  navigation.metadata.maxDepth = maxDepth;
  navigation.metadata.totalMenuItems = 
    (sidebar?.menuItems?.length || 0) +
    (tabNavigation?.length || 0) +
    (adminNav?.tabs?.length || 0) +
    (workspaceNav?.navItems?.length || 0);
  
  return navigation;
}

/**
 * Main function
 */
function main() {
  console.log('Analyzing navigation structure...');
  
  const navigation = buildNavigationHierarchy();
  
  const outputPath = path.join(OUTPUT_DIR, 'ui-navigation.json');
  fs.writeFileSync(outputPath, JSON.stringify(navigation, null, 2));
  
  console.log(`\nNavigation structure written to: ${outputPath}`);
  
  if (navigation.sidebar) {
    console.log(`\nSidebar menu items: ${navigation.sidebar.menuItems.length}`);
    console.log(`  Folders: ${navigation.sidebar.folders.length}`);
  }
  
  if (navigation.tabNavigation) {
    console.log(`Tab navigation layouts: ${navigation.tabNavigation.length}`);
  }
  
  if (navigation.adminNavigation) {
    console.log(`Admin navigation tabs: ${navigation.adminNavigation.tabs.length}`);
  }
  
  console.log(`\nNavigation hierarchy:`);
  console.log(`  Max depth: ${navigation.metadata.maxDepth}`);
  console.log(`  Total menu items: ${navigation.metadata.totalMenuItems}`);
  console.log(`  Level 1 items: ${navigation.hierarchy.level1.length}`);
  console.log(`  Level 2 items: ${navigation.hierarchy.level2.length}`);
}

main();

