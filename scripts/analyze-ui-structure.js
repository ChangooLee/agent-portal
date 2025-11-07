#!/usr/bin/env node

/**
 * UI Structure Analysis Script
 * Analyzes webui directory structure to create Skills mapping for code agents
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
 * Extract imports from Svelte file content
 */
function extractImports(content) {
  const imports = {
    components: [],
    apis: [],
    stores: [],
    utils: []
  };

  // Match import statements
  const importRegex = /import\s+.*?\s+from\s+['"]([^'"]+)['"]/g;
  let match;

  while ((match = importRegex.exec(content)) !== null) {
    const importPath = match[1];
    
    if (importPath.startsWith('$lib/components/')) {
      const componentPath = importPath.replace('$lib/components/', '');
      imports.components.push(componentPath);
    } else if (importPath.startsWith('$lib/apis/')) {
      const apiPath = importPath.replace('$lib/apis/', '');
      imports.apis.push(apiPath);
    } else if (importPath.startsWith('$lib/stores')) {
      imports.stores.push('stores');
    } else if (importPath.startsWith('$lib/utils')) {
      imports.utils.push('utils');
    }
  }

  return imports;
}

/**
 * Extract API calls from file content
 */
function extractAPICalls(content) {
  const apiCalls = [];
  
  // Match fetch calls
  const fetchRegex = /fetch\([^)]+\)/g;
  let match;
  
  while ((match = fetchRegex.exec(content)) !== null) {
    const fetchCall = match[0];
    // Extract URL if it's a string literal
    const urlMatch = fetchCall.match(/['"`]([^'"`]+)['"`]/);
    if (urlMatch) {
      apiCalls.push({
        type: 'fetch',
        url: urlMatch[1]
      });
    }
  }

  // Match API function calls (e.g., getModels, getChats, etc.)
  const apiFunctionRegex = /\b(get|create|update|delete|toggle)([A-Z][a-zA-Z]+)\s*\(/g;
  while ((match = apiFunctionRegex.exec(content)) !== null) {
    const functionName = match[1] + match[2];
    apiCalls.push({
      type: 'function',
      name: functionName
    });
  }

  return apiCalls;
}

/**
 * Extract keywords from file content
 */
function extractKeywords(content, filePath) {
  const keywords = [];
  
  // Extract from comments
  const commentRegex = /<!--\s*(.*?)\s*-->/g;
  let match;
  while ((match = commentRegex.exec(content)) !== null) {
    keywords.push(match[1].toLowerCase());
  }

  // Extract from title tags
  const titleMatch = content.match(/<title>([^<]+)<\/title>/);
  if (titleMatch) {
    keywords.push(...titleMatch[1].toLowerCase().split(/\s+/));
  }

  // Extract from i18n keys
  const i18nMatch = content.match(/\$i18n\.t\(['"]([^'"]+)['"]/g);
  if (i18nMatch) {
    i18nMatch.forEach(m => {
      const keyMatch = m.match(/['"]([^'"]+)['"]/);
      if (keyMatch) {
        keywords.push(keyMatch[1].toLowerCase());
      }
    });
  }

  // Extract from path
  const pathParts = filePath.split('/');
  pathParts.forEach(part => {
    if (part && part !== 'src' && part !== 'routes' && part !== 'app' && !part.startsWith('+') && !part.endsWith('.svelte')) {
      keywords.push(part.toLowerCase());
    }
  });

  // Remove duplicates and filter
  return [...new Set(keywords)].filter(k => k.length > 2);
}

/**
 * Analyze a single route file
 */
function analyzeRouteFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const relativePath = path.relative(WEBUI_DIR, filePath);
  
  const imports = extractImports(content);
  const apiCalls = extractAPICalls(content);
  const keywords = extractKeywords(content, relativePath);

  // Extract route description from comments or title
  let description = '';
  const titleMatch = content.match(/<title>([^<]+)<\/title>/);
  if (titleMatch) {
    description = titleMatch[1].trim();
  } else {
    // Use file path as description
    const pathParts = relativePath.split('/');
    const fileName = pathParts[pathParts.length - 1].replace('.svelte', '').replace('+', '');
    description = fileName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  }

  // Extract route path pattern
  let routePath = relativePath
    .replace('routes/', '/')
    .replace('/(app)/', '')
    .replace(/\+page\.svelte$/, '')
    .replace(/\+layout\.svelte$/, '')
    .replace(/\[(\w+)\]/g, ':$1');

  if (routePath.endsWith('/')) {
    routePath = routePath.slice(0, -1);
  }
  if (!routePath) {
    routePath = '/';
  }

  return {
    path: relativePath,
    routePath: routePath,
    description: description,
    components: imports.components,
    apis: imports.apis,
    apiCalls: apiCalls,
    stores: imports.stores,
    keywords: keywords,
    fileSize: content.length,
    lineCount: content.split('\n').length
  };
}

/**
 * Analyze all routes
 */
function analyzeRoutes() {
  const routesDir = path.join(WEBUI_DIR, 'routes');
  const routes = [];

  function scanDirectory(dir, basePath = '') {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      const relativePath = path.join(basePath, entry.name);

      if (entry.isDirectory()) {
        scanDirectory(fullPath, relativePath);
      } else if (entry.name.endsWith('.svelte') && (entry.name.startsWith('+page') || entry.name.startsWith('+layout'))) {
        const routeInfo = analyzeRouteFile(fullPath);
        routes.push(routeInfo);
      }
    }
  }

  scanDirectory(routesDir);
  return routes;
}

/**
 * Analyze all components
 */
function analyzeComponents() {
  const componentsDir = path.join(WEBUI_DIR, 'lib/components');
  const components = [];

  function scanDirectory(dir, basePath = '') {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      const relativePath = path.join(basePath, entry.name);

      if (entry.isDirectory()) {
        scanDirectory(fullPath, relativePath);
      } else if (entry.name.endsWith('.svelte')) {
        const content = fs.readFileSync(fullPath, 'utf-8');
        const imports = extractImports(content);
        const keywords = extractKeywords(content, relativePath);
        
        const componentName = entry.name.replace('.svelte', '');
        const componentPath = path.join('lib/components', relativePath);

        components.push({
          name: componentName,
          path: componentPath,
          directory: basePath || 'root',
          imports: imports.components,
          keywords: keywords,
          fileSize: content.length,
          lineCount: content.split('\n').length
        });
      }
    }
  }

  scanDirectory(componentsDir);
  return components;
}

/**
 * Analyze API structure
 */
function analyzeAPIs() {
  const apisDir = path.join(WEBUI_DIR, 'lib/apis');
  const apis = [];

  function scanDirectory(dir, basePath = '') {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      const relativePath = path.join(basePath, entry.name);

      if (entry.isDirectory()) {
        scanDirectory(fullPath, relativePath);
      } else if (entry.name === 'index.ts' || entry.name === 'index.js') {
        const content = fs.readFileSync(fullPath, 'utf-8');
        
        // Extract exported functions
        const exportRegex = /export\s+(const|async\s+function|function)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)/g;
        const functions = [];
        let match;
        
        while ((match = exportRegex.exec(content)) !== null) {
          functions.push(match[2]);
        }

        if (functions.length > 0) {
          apis.push({
            path: path.join('lib/apis', basePath, 'index.ts'),
            module: basePath || 'root',
            functions: functions,
            fileSize: content.length,
            lineCount: content.split('\n').length
          });
        }
      }
    }
  }

  scanDirectory(apisDir);
  return apis;
}

/**
 * Main analysis function
 */
function main() {
  console.log('Analyzing UI structure...');
  
  const routes = analyzeRoutes();
  console.log(`Found ${routes.length} routes`);
  
  const components = analyzeComponents();
  console.log(`Found ${components.length} components`);
  
  const apis = analyzeAPIs();
  console.log(`Found ${apis.length} API modules`);

  // Create structure mapping
  const structure = {
    metadata: {
      generatedAt: new Date().toISOString(),
      webuiDir: WEBUI_DIR,
      routeCount: routes.length,
      componentCount: components.length,
      apiModuleCount: apis.length
    },
    routes: routes,
    components: components,
    apis: apis
  };

  // Write structure file
  const structurePath = path.join(OUTPUT_DIR, 'ui-structure.json');
  fs.writeFileSync(structurePath, JSON.stringify(structure, null, 2));
  console.log(`\nStructure written to: ${structurePath}`);

  // Create search index
  const searchIndex = {
    metadata: {
      generatedAt: new Date().toISOString(),
      version: '1.0.0'
    },
    routes: routes.map(route => ({
      path: route.path,
      routePath: route.routePath,
      description: route.description,
      keywords: route.keywords,
      components: route.components,
      apis: route.apis
    })),
    components: components.map(comp => ({
      name: comp.name,
      path: comp.path,
      directory: comp.directory,
      keywords: comp.keywords
    })),
    apis: apis.map(api => ({
      path: api.path,
      module: api.module,
      functions: api.functions
    })),
    // Create keyword index for fast lookup
    keywordIndex: {}
  };

  // Build keyword index
  routes.forEach(route => {
    route.keywords.forEach(keyword => {
      if (!searchIndex.keywordIndex[keyword]) {
        searchIndex.keywordIndex[keyword] = {
          routes: [],
          components: [],
          apis: []
        };
      }
      searchIndex.keywordIndex[keyword].routes.push(route.path);
    });
  });

  components.forEach(comp => {
    comp.keywords.forEach(keyword => {
      if (!searchIndex.keywordIndex[keyword]) {
        searchIndex.keywordIndex[keyword] = {
          routes: [],
          components: [],
          apis: []
        };
      }
      searchIndex.keywordIndex[keyword].components.push(comp.path);
    });
  });

  // Write search index
  const indexPath = path.join(OUTPUT_DIR, 'ui-search-index.json');
  fs.writeFileSync(indexPath, JSON.stringify(searchIndex, null, 2));
  console.log(`Search index written to: ${indexPath}`);

  console.log('\nAnalysis complete!');
}

main();

