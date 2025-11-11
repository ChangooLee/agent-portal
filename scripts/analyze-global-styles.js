#!/usr/bin/env node

/**
 * Global Styles Analysis Script
 * Analyzes Tailwind config, global CSS, and theme system
 */

const fs = require('fs');
const path = require('path');

const WEBUI_DIR = path.join(__dirname, '../webui');
const OUTPUT_DIR = path.join(__dirname, '../webui/.skills');

// Ensure output directory exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

/**
 * Analyze Tailwind config
 */
function analyzeTailwindConfig() {
  const configPath = path.join(WEBUI_DIR, 'tailwind.config.js');
  
  if (!fs.existsSync(configPath)) {
    return null;
  }
  
  const content = fs.readFileSync(configPath, 'utf-8');
  
  // Extract color palette
  const colors = {};
  const colorRegex = /colors:\s*\{([^}]+)\}/s;
  const colorMatch = content.match(colorRegex);
  
  if (colorMatch) {
    const colorContent = colorMatch[1];
    // Extract gray scale
    const grayRegex = /gray:\s*\{([^}]+)\}/s;
    const grayMatch = colorContent.match(grayRegex);
    
    if (grayMatch) {
      const grayScale = grayMatch[1];
      const grayValues = grayScale.match(/(\d+):\s*['"]([^'"]+)['"]/g);
      
      if (grayValues) {
        grayValues.forEach(match => {
          const parts = match.match(/(\d+):\s*['"]([^'"]+)['"]/);
          if (parts) {
            colors[`gray-${parts[1]}`] = parts[2];
          }
        });
      }
    }
  }
  
  // Extract breakpoints (default Tailwind breakpoints)
  const breakpoints = {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px'
  };
  
  // Check for custom breakpoints
  const breakpointRegex = /screens:\s*\{([^}]+)\}/s;
  const breakpointMatch = content.match(breakpointRegex);
  if (breakpointMatch) {
    // Parse custom breakpoints if any
  }
  
  // Extract plugins
  const plugins = [];
  const pluginRegex = /plugins:\s*\[([^\]]+)\]/s;
  const pluginMatch = content.match(pluginRegex);
  if (pluginMatch) {
    const pluginContent = pluginMatch[1];
    const pluginNames = pluginContent.match(/(\w+)/g);
    if (pluginNames) {
      plugins.push(...pluginNames);
    }
  }
  
  return {
    colors: colors,
    breakpoints: breakpoints,
    plugins: plugins,
    darkMode: content.includes("darkMode: 'class'") ? 'class' : 'media'
  };
}

/**
 * Analyze global CSS files
 */
function analyzeGlobalCSS() {
  const cssFiles = [
    path.join(WEBUI_DIR, 'src/app.css'),
    path.join(WEBUI_DIR, 'src/tailwind.css')
  ];
  
  const globalStyles = {
    fonts: [],
    customClasses: [],
    cssVariables: [],
    mediaQueries: []
  };
  
  cssFiles.forEach(cssPath => {
    if (!fs.existsSync(cssPath)) return;
    
    const content = fs.readFileSync(cssPath, 'utf-8');
    const fileName = path.basename(cssPath);
    
    // Extract @font-face
    const fontRegex = /@font-face\s*\{[^}]+font-family:\s*['"]([^'"]+)['"][^}]+}/g;
    let match;
    while ((match = fontRegex.exec(content)) !== null) {
      globalStyles.fonts.push({
        name: match[1],
        file: fileName
      });
    }
    
    // Extract custom CSS classes
    const classRegex = /\.([a-zA-Z][a-zA-Z0-9_-]*)\s*\{[^}]+\}/g;
    const classes = [];
    while ((match = classRegex.exec(content)) !== null) {
      classes.push(match[1]);
    }
    globalStyles.customClasses.push(...classes);
    
    // Extract CSS variables
    const varRegex = /--([a-zA-Z][a-zA-Z0-9_-]*):\s*([^;]+);/g;
    while ((match = varRegex.exec(content)) !== null) {
      globalStyles.cssVariables.push({
        name: match[1],
        value: match[2].trim(),
        file: fileName
      });
    }
    
    // Extract media queries
    const mediaRegex = /@media\s+\([^)]+\)\s*\{[^}]+\}/g;
    while ((match = mediaRegex.exec(content)) !== null) {
      globalStyles.mediaQueries.push({
        query: match[0].substring(0, 100), // First 100 chars
        file: fileName
      });
    }
  });
  
  return globalStyles;
}

/**
 * Analyze theme system
 */
function analyzeThemeSystem() {
  // Look for theme-related files
  const themeFiles = [
    path.join(WEBUI_DIR, 'src/app.html'),
    path.join(WEBUI_DIR, 'src/lib/components/chat/Settings/General.svelte'),
    path.join(WEBUI_DIR, 'src/lib/stores/index.ts')
  ];
  
  const themes = {
    available: [],
    default: 'system',
    storageKey: 'theme',
    applyMethod: 'class'
  };
  
  themeFiles.forEach(filePath => {
    if (!fs.existsSync(filePath)) return;
    
    const content = fs.readFileSync(filePath, 'utf-8');
    
    // Extract theme options from select/options
    const optionRegex = /<option\s+value=["']([^"']+)["']/g;
    let match;
    while ((match = optionRegex.exec(content)) !== null) {
      const theme = match[1];
      if (!themes.available.includes(theme)) {
        themes.available.push(theme);
      }
    }
    
    // Extract default theme
    const defaultMatch = content.match(/localStorage\.theme\s*=\s*['"]([^'"]+)['"]/);
    if (defaultMatch) {
      themes.default = defaultMatch[1];
    }
    
    // Check for theme application method
    if (content.includes('document.documentElement.classList')) {
      themes.applyMethod = 'class';
    }
  });
  
  // Extract theme colors from CSS variables
  const appHtmlPath = path.join(WEBUI_DIR, 'src/app.html');
  if (fs.existsSync(appHtmlPath)) {
    const content = fs.readFileSync(appHtmlPath, 'utf-8');
    
    // Extract theme color variables
    const themeColorRegex = /setProperty\(['"]--color-([^'"]+)['"],\s*['"]([^'"]+)['"]\)/g;
    let match;
    while ((match = themeColorRegex.exec(content)) !== null) {
      themes.colorVariables = themes.colorVariables || {};
      themes.colorVariables[match[1]] = match[2];
    }
  }
  
  return themes;
}

/**
 * Analyze responsive design patterns
 */
function analyzeResponsivePatterns() {
  const srcDir = path.join(WEBUI_DIR, 'src');
  const breakpointUsage = {
    sm: 0,
    md: 0,
    lg: 0,
    xl: 0,
    '2xl': 0
  };
  
  function scanFiles(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      
      if (entry.isDirectory()) {
        scanFiles(fullPath);
      } else if (entry.name.endsWith('.svelte')) {
        const content = fs.readFileSync(fullPath, 'utf-8');
        
        // Count breakpoint usage
        Object.keys(breakpointUsage).forEach(bp => {
          const regex = new RegExp(`${bp}:`, 'g');
          const matches = content.match(regex);
          if (matches) {
            breakpointUsage[bp] += matches.length;
          }
        });
      }
    }
  }
  
  scanFiles(srcDir);
  
  return {
    breakpointUsage: breakpointUsage,
    mostUsed: Object.entries(breakpointUsage).sort((a, b) => b[1] - a[1])[0]?.[0]
  };
}

/**
 * Main function
 */
function main() {
  console.log('Analyzing global styles...');
  
  const tailwindConfig = analyzeTailwindConfig();
  const globalCSS = analyzeGlobalCSS();
  const themeSystem = analyzeThemeSystem();
  const responsivePatterns = analyzeResponsivePatterns();
  
  const styles = {
    metadata: {
      generatedAt: new Date().toISOString()
    },
    tailwind: tailwindConfig,
    globalCSS: globalCSS,
    themeSystem: themeSystem,
    responsive: responsivePatterns
  };
  
  const outputPath = path.join(OUTPUT_DIR, 'ui-styles.json');
  fs.writeFileSync(outputPath, JSON.stringify(styles, null, 2));
  
  console.log(`\nGlobal styles written to: ${outputPath}`);
  
  if (tailwindConfig) {
    console.log(`\nTailwind Config:`);
    console.log(`  Colors: ${Object.keys(tailwindConfig.colors).length} defined`);
    console.log(`  Breakpoints: ${Object.keys(tailwindConfig.breakpoints).length}`);
    console.log(`  Dark mode: ${tailwindConfig.darkMode}`);
  }
  
  console.log(`\nGlobal CSS:`);
  console.log(`  Fonts: ${globalCSS.fonts.length}`);
  console.log(`  Custom classes: ${globalCSS.customClasses.length}`);
  console.log(`  CSS variables: ${globalCSS.cssVariables.length}`);
  
  console.log(`\nTheme System:`);
  console.log(`  Available themes: ${themeSystem.available.join(', ')}`);
  console.log(`  Default theme: ${themeSystem.default}`);
  
  console.log(`\nResponsive Patterns:`);
  console.log(`  Most used breakpoint: ${responsivePatterns.mostUsed}`);
  Object.entries(responsivePatterns.breakpointUsage).forEach(([bp, count]) => {
    console.log(`    ${bp}: ${count} uses`);
  });
}

main();


