#!/usr/bin/env node

/**
 * UI Style Patterns Analysis Script
 * Analyzes Tailwind CSS patterns and common UI component styles
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
 * Extract Tailwind classes from HTML/Svelte content
 */
function extractTailwindClasses(content) {
  const classes = [];
  
  // Match class attributes (class="...", className="...", class={...})
  const classRegex = /class(?:Name)?=(["'])((?:(?=(\\?))\3.)*?)\1|class=\{`([^`]+)`\}|class=\{([^}]+)\}/g;
  let match;
  
  while ((match = classRegex.exec(content)) !== null) {
    let classString = match[2] || match[4] || match[5] || '';
    
    // Remove Svelte expressions and get literal classes
    classString = classString.replace(/\{[^}]+\}/g, '').trim();
    
    if (classString) {
      const classList = classString.split(/\s+/).filter(c => c && !c.includes('{'));
      classes.push(...classList);
    }
  }
  
  return [...new Set(classes)];
}

/**
 * Identify UI component patterns based on class patterns
 */
function identifyComponentPatterns(classes, elementType, context) {
  const patterns = {
    type: 'unknown',
    style: {},
    variants: []
  };
  
  const classStr = classes.join(' ');
  
  // Button patterns
  if (elementType === 'button' || classStr.includes('button') || classStr.includes('cursor-pointer')) {
    patterns.type = 'button';
    
    // Extract button styles
    if (classStr.match(/px-\d+|py-\d+|p-\d+/)) {
      patterns.style.padding = classes.find(c => c.match(/px-\d+|py-\d+|p-\d+/));
    }
    if (classStr.match(/rounded-\w+/)) {
      patterns.style.borderRadius = classes.find(c => c.match(/rounded-\w+/));
    }
    if (classStr.match(/bg-\w+-\d+/)) {
      patterns.style.background = classes.filter(c => c.match(/bg-\w+-\d+/));
    }
    if (classStr.match(/text-\w+-\d+/)) {
      patterns.style.textColor = classes.filter(c => c.match(/text-\w+-\d+/));
    }
    if (classStr.match(/hover:bg-\w+-\d+/)) {
      patterns.style.hoverBackground = classes.filter(c => c.match(/hover:bg-\w+-\d+/));
    }
    if (classStr.match(/dark:bg-\w+-\d+/)) {
      patterns.style.darkBackground = classes.filter(c => c.match(/dark:bg-\w+-\d+/));
    }
    if (classStr.match(/dark:text-\w+-\d+/)) {
      patterns.style.darkTextColor = classes.filter(c => c.match(/dark:text-\w+-\d+/));
    }
    if (classStr.match(/border-\w+/)) {
      patterns.style.border = classes.filter(c => c.match(/border-\w+/));
    }
    if (classStr.match(/transition/)) {
      patterns.style.transition = classes.filter(c => c.match(/transition/));
    }
  }
  
  // Tab patterns
  if (classStr.includes('tab') || (elementType === 'button' && classStr.match(/border-b-\d+/))) {
    patterns.type = 'tab';
    
    if (classStr.match(/border-b-\d+/)) {
      patterns.style.activeBorder = classes.find(c => c.match(/border-b-\d+/));
    }
    if (classStr.match(/border-\w+-\d+/)) {
      patterns.style.borderColor = classes.filter(c => c.match(/border-\w+-\d+/));
    }
    // Extract active tab colors
    if (classStr.match(/border-(blue|green|red|yellow|purple|pink|indigo)-\d+/)) {
      const borderColor = classes.find(c => c.match(/border-(blue|green|red|yellow|purple|pink|indigo)-\d+/));
      if (borderColor) {
        patterns.style.activeBorderColor = borderColor;
      }
    }
    if (classStr.match(/text-(blue|green|red|yellow|purple|pink|indigo)-\d+/)) {
      const textColor = classes.find(c => c.match(/text-(blue|green|red|yellow|purple|pink|indigo)-\d+/));
      if (textColor) {
        patterns.style.activeTextColor = textColor;
      }
    }
  }
  
  // Card patterns
  if (classStr.match(/bg-white|bg-gray-\d+/) && classStr.match(/rounded-\w+/) && classStr.match(/shadow|p-\d+/)) {
    patterns.type = 'card';
    
    if (classStr.match(/bg-\w+-\d+/)) {
      patterns.style.background = classes.filter(c => c.match(/bg-\w+-\d+/));
    }
    if (classStr.match(/rounded-\w+/)) {
      patterns.style.borderRadius = classes.find(c => c.match(/rounded-\w+/));
    }
    if (classStr.match(/shadow/)) {
      patterns.style.shadow = classes.filter(c => c.match(/shadow/));
    }
    if (classStr.match(/p-\d+/)) {
      patterns.style.padding = classes.find(c => c.match(/p-\d+/));
    }
  }
  
  // Modal patterns
  if (classStr.includes('modal') || classStr.includes('fixed') && classStr.includes('z-\d+/')) {
    patterns.type = 'modal';
    
    if (classStr.match(/fixed|absolute/)) {
      patterns.style.position = classes.find(c => c.match(/fixed|absolute/));
    }
    if (classStr.match(/z-\d+/)) {
      patterns.style.zIndex = classes.find(c => c.match(/z-\d+/));
    }
  }
  
  return patterns;
}

/**
 * Extract color usage patterns
 */
function extractColorPatterns(classes) {
  const colors = {
    primary: [],
    secondary: [],
    accent: [],
    background: [],
    text: [],
    border: []
  };
  
  classes.forEach(cls => {
    // Primary colors (blue, green, etc.)
    if (cls.match(/bg-(blue|green|red|yellow|purple|pink|indigo)-\d+/)) {
      const color = cls.match(/(blue|green|red|yellow|purple|pink|indigo)-\d+/)[0];
      if (!colors.primary.includes(color)) colors.primary.push(color);
    }
    
    // Gray scale
    if (cls.match(/bg-gray-\d+/)) {
      const color = cls.match(/gray-\d+/)[0];
      if (!colors.background.includes(color)) colors.background.push(color);
    }
    
    // Text colors
    if (cls.match(/text-(blue|green|red|yellow|purple|pink|indigo|gray)-\d+/)) {
      const colorMatch = cls.match(/(blue|green|red|yellow|purple|pink|indigo|gray)-\d+/);
      if (colorMatch) {
        const color = colorMatch[0];
        if (!colors.text.includes(color)) colors.text.push(color);
      }
    }
    
    // Border colors
    if (cls.match(/border-(blue|green|red|yellow|purple|pink|indigo|gray)-\d+/)) {
      const colorMatch = cls.match(/(blue|green|red|yellow|purple|pink|indigo|gray)-\d+/);
      if (colorMatch) {
        const color = colorMatch[0];
        if (!colors.border.includes(color)) colors.border.push(color);
      }
    }
  });
  
  return colors;
}

/**
 * Analyze a single file for style patterns
 */
function analyzeFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const relativePath = path.relative(WEBUI_DIR, filePath);
  
  // Extract all class attributes
  const classRegex = /<(button|div|a|nav|section|header|footer|main|aside|article|span|p|h[1-6]|input|select|textarea|form|ul|li|ol|table|tr|td|th|thead|tbody|tfoot)[^>]*class(?:Name)?=(["'])((?:(?=(\\?))\4.)*?)\2|class=\{`([^`]+)`\}|class=\{([^}]+)\}[^>]*>/g;
  
  const patterns = [];
  let match;
  
  while ((match = classRegex.exec(content)) !== null) {
    const elementType = match[1] || 'div';
    let classString = match[3] || match[5] || match[6] || '';
    
    // Extract literal classes (remove Svelte expressions)
    const literalClasses = classString
      .replace(/\{[^}]+\}/g, '')
      .split(/\s+/)
      .filter(c => c && !c.includes('{') && !c.includes('$'));
    
    if (literalClasses.length > 0) {
      const pattern = identifyComponentPatterns(literalClasses, elementType, {
        file: relativePath,
        line: content.substring(0, match.index).split('\n').length
      });
      
      pattern.classes = literalClasses;
      pattern.file = relativePath;
      pattern.element = elementType;
      
      patterns.push(pattern);
    }
  }
  
  return patterns;
}

/**
 * Build color-to-files mapping
 */
function buildColorFileMapping(patterns) {
  const colorMap = {};
  
  patterns.forEach(pattern => {
    if (!pattern.classes || !Array.isArray(pattern.classes)) return;
    
    // Combine all classes into a single string for matching
    const classString = pattern.classes.join(' ');
    
    // Extract all color classes
    const colorRegex = /(?:bg|text|border)-(blue|green|red|yellow|purple|pink|indigo|gray)-(\d+)/g;
    let match;
    
    while ((match = colorRegex.exec(classString)) !== null) {
      const colorKey = `${match[1]}-${match[2]}`;
      const fullMatch = match[0];
      const colorType = fullMatch.startsWith('bg-') ? 'bg' : 
                       fullMatch.startsWith('text-') ? 'text' : 'border';
      const fullColorKey = `${colorType}-${colorKey}`;
      
      if (!colorMap[fullColorKey]) {
        colorMap[fullColorKey] = {
          files: [],
          routes: [],
          components: []
        };
      }
      
      const filePath = pattern.file;
      if (!colorMap[fullColorKey].files.includes(filePath)) {
        colorMap[fullColorKey].files.push(filePath);
        
        if (filePath.startsWith('routes/')) {
          colorMap[fullColorKey].routes.push(filePath);
        } else {
          colorMap[fullColorKey].components.push(filePath);
        }
      }
    }
  });
  
  return colorMap;
}

/**
 * Analyze all files and aggregate patterns
 */
function analyzeAllFiles() {
  const allPatterns = [];
  const colorUsage = {};
  const componentPatterns = {
    buttons: [],
    tabs: [],
    cards: [],
    modals: [],
    other: []
  };
  
  function scanDirectory(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      
      if (entry.isDirectory()) {
        scanDirectory(fullPath);
      } else if (entry.name.endsWith('.svelte')) {
        const patterns = analyzeFile(fullPath);
        allPatterns.push(...patterns);
        
        patterns.forEach(pattern => {
          const colors = extractColorPatterns(pattern.classes);
          
          // Aggregate color usage
          Object.keys(colors).forEach(type => {
            if (!colorUsage[type]) colorUsage[type] = [];
            colors[type].forEach(color => {
              if (!colorUsage[type].includes(color)) {
                colorUsage[type].push(color);
              }
            });
          });
          
          // Categorize patterns
          if (pattern.type === 'button') {
            componentPatterns.buttons.push(pattern);
          } else if (pattern.type === 'tab') {
            componentPatterns.tabs.push(pattern);
          } else if (pattern.type === 'card') {
            componentPatterns.cards.push(pattern);
          } else if (pattern.type === 'modal') {
            componentPatterns.modals.push(pattern);
          } else {
            componentPatterns.other.push(pattern);
          }
        });
      }
    }
  }
  
  scanDirectory(WEBUI_DIR);
  
  // Find common patterns
  const commonPatterns = {
    tab: findCommonTabPattern(componentPatterns.tabs),
    button: findCommonButtonPattern(componentPatterns.buttons),
    card: findCommonCardPattern(componentPatterns.cards)
  };
  
  // Build color-to-files mapping
  const colorFileMapping = buildColorFileMapping(allPatterns);
  
  return {
    metadata: {
      generatedAt: new Date().toISOString(),
      totalPatterns: allPatterns.length,
      buttonCount: componentPatterns.buttons.length,
      tabCount: componentPatterns.tabs.length,
      cardCount: componentPatterns.cards.length,
      modalCount: componentPatterns.modals.length
    },
    colorUsage: colorUsage,
    colorFileMapping: colorFileMapping,
    commonPatterns: commonPatterns,
    componentPatterns: {
      buttons: componentPatterns.buttons.slice(0, 50), // Limit for file size
      tabs: componentPatterns.tabs.slice(0, 50),
      cards: componentPatterns.cards.slice(0, 50),
      modals: componentPatterns.modals.slice(0, 20)
    },
    allPatterns: allPatterns.slice(0, 200) // Limit for file size
  };
}

/**
 * Find common tab pattern
 */
function findCommonTabPattern(tabs) {
  if (tabs.length === 0) return null;
  
  const activeBorder = {};
  const activeBorderColor = {};
  const activeTextColor = {};
  const borderColors = {};
  
  tabs.forEach(tab => {
    if (tab.style.activeBorder) {
      const border = tab.style.activeBorder;
      activeBorder[border] = (activeBorder[border] || 0) + 1;
    }
    if (tab.style.activeBorderColor) {
      const color = tab.style.activeBorderColor;
      activeBorderColor[color] = (activeBorderColor[color] || 0) + 1;
    }
    if (tab.style.activeTextColor) {
      const color = tab.style.activeTextColor;
      activeTextColor[color] = (activeTextColor[color] || 0) + 1;
    }
    if (tab.style.borderColor && tab.style.borderColor.length > 0) {
      tab.style.borderColor.forEach(color => {
        borderColors[color] = (borderColors[color] || 0) + 1;
      });
    }
  });
  
  return {
    activeBorder: Object.entries(activeBorder).sort((a, b) => b[1] - a[1])[0]?.[0],
    activeBorderColor: Object.entries(activeBorderColor).sort((a, b) => b[1] - a[1])[0]?.[0],
    activeTextColor: Object.entries(activeTextColor).sort((a, b) => b[1] - a[1])[0]?.[0],
    borderColors: Object.entries(borderColors).sort((a, b) => b[1] - a[1])[0]?.[0],
    files: [...new Set(tabs.map(t => t.file))].slice(0, 20)
  };
}

/**
 * Find common button pattern
 */
function findCommonButtonPattern(buttons) {
  if (buttons.length === 0) return null;
  
  const padding = {};
  const borderRadius = {};
  const hoverBg = {};
  
  buttons.forEach(btn => {
    if (btn.style.padding) {
      padding[btn.style.padding] = (padding[btn.style.padding] || 0) + 1;
    }
    if (btn.style.borderRadius) {
      borderRadius[btn.style.borderRadius] = (borderRadius[btn.style.borderRadius] || 0) + 1;
    }
    if (btn.style.hoverBackground && btn.style.hoverBackground.length > 0) {
      btn.style.hoverBackground.forEach(bg => {
        hoverBg[bg] = (hoverBg[bg] || 0) + 1;
      });
    }
  });
  
  return {
    padding: Object.entries(padding).sort((a, b) => b[1] - a[1])[0]?.[0],
    borderRadius: Object.entries(borderRadius).sort((a, b) => b[1] - a[1])[0]?.[0],
    hoverBackground: Object.entries(hoverBg).sort((a, b) => b[1] - a[1])[0]?.[0],
    files: [...new Set(buttons.map(b => b.file))].slice(0, 10)
  };
}

/**
 * Find common card pattern
 */
function findCommonCardPattern(cards) {
  if (cards.length === 0) return null;
  
  const background = {};
  const borderRadius = {};
  const shadow = {};
  const padding = {};
  
  cards.forEach(card => {
    if (card.style.background && card.style.background.length > 0) {
      card.style.background.forEach(bg => {
        background[bg] = (background[bg] || 0) + 1;
      });
    }
    if (card.style.borderRadius) {
      borderRadius[card.style.borderRadius] = (borderRadius[card.style.borderRadius] || 0) + 1;
    }
    if (card.style.shadow && card.style.shadow.length > 0) {
      card.style.shadow.forEach(s => {
        shadow[s] = (shadow[s] || 0) + 1;
      });
    }
    if (card.style.padding) {
      padding[card.style.padding] = (padding[card.style.padding] || 0) + 1;
    }
  });
  
  return {
    background: Object.entries(background).sort((a, b) => b[1] - a[1])[0]?.[0],
    borderRadius: Object.entries(borderRadius).sort((a, b) => b[1] - a[1])[0]?.[0],
    shadow: Object.entries(shadow).sort((a, b) => b[1] - a[1])[0]?.[0],
    padding: Object.entries(padding).sort((a, b) => b[1] - a[1])[0]?.[0],
    files: [...new Set(cards.map(c => c.file))].slice(0, 10)
  };
}

/**
 * Main function
 */
function main() {
  console.log('Analyzing UI style patterns...');
  
  const patterns = analyzeAllFiles();
  
  const outputPath = path.join(OUTPUT_DIR, 'ui-patterns.json');
  fs.writeFileSync(outputPath, JSON.stringify(patterns, null, 2));
  
  console.log(`\nPatterns written to: ${outputPath}`);
  console.log(`Found ${patterns.metadata.totalPatterns} total patterns`);
  console.log(`- Buttons: ${patterns.metadata.buttonCount}`);
  console.log(`- Tabs: ${patterns.metadata.tabCount}`);
  console.log(`- Cards: ${patterns.metadata.cardCount}`);
  console.log(`- Modals: ${patterns.metadata.modalCount}`);
  console.log('\nCommon patterns identified:');
  if (patterns.commonPatterns.tab) {
    console.log(`  Tab active border: ${patterns.commonPatterns.tab.activeBorder}`);
  }
  if (patterns.commonPatterns.button) {
    console.log(`  Button padding: ${patterns.commonPatterns.button.padding}`);
  }
  if (patterns.commonPatterns.card) {
    console.log(`  Card background: ${patterns.commonPatterns.card.background}`);
  }
}

main();

