#!/usr/bin/env node

/**
 * Class Mapping Guide Generator
 * Generates a guide for common class replacements during UI refactoring
 */

const fs = require('fs');
const path = require('path');

const OUTPUT_DIR = path.join(__dirname, '../webui/.skills');

/**
 * Generate class mapping guide
 */
function generateMappingGuide() {
  const guide = {
    metadata: {
      generatedAt: new Date().toISOString(),
      version: '1.0.0',
      description: 'Common class replacement patterns for UI refactoring'
    },
    colorMappings: {
      blue: {
        from: 'blue',
        to: 'green',
        examples: [
          {
            from: 'border-blue-500',
            to: 'border-green-500',
            description: 'Tab active border color'
          },
          {
            from: 'text-blue-600',
            to: 'text-green-600',
            description: 'Tab active text color'
          },
          {
            from: 'bg-blue-500',
            to: 'bg-green-500',
            description: 'Button/background color'
          }
        ]
      },
      gray: {
        from: 'gray',
        to: 'slate',
        examples: [
          {
            from: 'bg-gray-100',
            to: 'bg-slate-100',
            description: 'Background color'
          },
          {
            from: 'text-gray-500',
            to: 'text-slate-500',
            description: 'Text color'
          }
        ]
      }
    },
    patternMappings: {
      tab: {
        activeBorder: {
          common: 'border-b-2',
          alternatives: ['border-b', 'border-b-4', 'border-b-8'],
          description: 'Active tab bottom border'
        },
        activeBorderColor: {
          common: 'border-blue-500',
          alternatives: ['border-blue-600', 'border-indigo-500'],
          description: 'Active tab border color'
        },
        activeTextColor: {
          common: 'text-blue-600',
          alternatives: ['text-blue-500', 'text-blue-700'],
          description: 'Active tab text color'
        }
      },
      button: {
        padding: {
          common: 'px-3 py-1.5',
          alternatives: ['p-2', 'px-4 py-2', 'p-3'],
          description: 'Button padding'
        },
        borderRadius: {
          common: 'rounded-lg',
          alternatives: ['rounded-md', 'rounded-full', 'rounded-xl'],
          description: 'Button border radius'
        },
        hoverBackground: {
          common: 'hover:bg-gray-100',
          alternatives: ['hover:bg-gray-50', 'hover:bg-gray-200'],
          description: 'Button hover background'
        }
      },
      card: {
        background: {
          common: 'bg-white',
          alternatives: ['bg-gray-50', 'bg-gray-100'],
          description: 'Card background'
        },
        borderRadius: {
          common: 'rounded-lg',
          alternatives: ['rounded-md', 'rounded-xl'],
          description: 'Card border radius'
        },
        shadow: {
          common: 'shadow-md',
          alternatives: ['shadow-sm', 'shadow-lg', 'shadow-xl'],
          description: 'Card shadow'
        }
      }
    },
    refactoringExamples: [
      {
        scenario: 'Change all tab active colors from blue to green',
        steps: [
          '1. Find all files with border-blue-500 using colorFileMapping',
          '2. Replace border-blue-500 with border-green-500',
          '3. Replace text-blue-600 with text-green-600',
          '4. Replace text-blue-400 with text-green-400 (dark mode)'
        ],
        affectedFiles: 'Use ui-patterns.json > colorFileMapping > border-blue-500'
      },
      {
        scenario: 'Change all gray colors to slate',
        steps: [
          '1. Find all gray-* classes using colorFileMapping',
          '2. Replace bg-gray-* with bg-slate-*',
          '3. Replace text-gray-* with text-slate-*',
          '4. Replace border-gray-* with border-slate-*'
        ],
        affectedFiles: 'Use ui-patterns.json > colorFileMapping for all gray-* keys'
      },
      {
        scenario: 'Change button padding from px-3 py-1.5 to px-4 py-2',
        steps: [
          '1. Find all button patterns using ui-patterns.json > componentPatterns.buttons',
          '2. Search for px-3 py-1.5 in each file',
          '3. Replace with px-4 py-2'
        ],
        affectedFiles: 'Use ui-patterns.json > componentPatterns.buttons'
      }
    ]
  };
  
  return guide;
}

/**
 * Main function
 */
function main() {
  console.log('Generating class mapping guide...');
  
  const guide = generateMappingGuide();
  
  const outputPath = path.join(OUTPUT_DIR, 'ui-class-mapping-guide.json');
  fs.writeFileSync(outputPath, JSON.stringify(guide, null, 2));
  
  console.log(`\nClass mapping guide written to: ${outputPath}`);
  console.log(`\nGuide includes:`);
  console.log(`  - Color mappings: ${Object.keys(guide.colorMappings).length} examples`);
  console.log(`  - Pattern mappings: ${Object.keys(guide.patternMappings).length} patterns`);
  console.log(`  - Refactoring examples: ${guide.refactoringExamples.length} scenarios`);
}

main();


