#!/usr/bin/env node
/**
 * Backend 구조 분석 스크립트
 * backend/ (FastAPI BFF)와 webui/backend (Open-WebUI)의 구조를 분석하여 JSON으로 저장
 */

const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..');

// FastAPI BFF 분석
function analyzeFastAPIBFF() {
  console.log('Analyzing FastAPI BFF (backend/)...');
  
  const backendPath = path.join(projectRoot, 'backend');
  const skillsPath = path.join(backendPath, '.skills');
  
  if (!fs.existsSync(skillsPath)) {
    fs.mkdirSync(skillsPath, { recursive: true });
  }
  
  const structure = {
    metadata: {
      project: 'agent-portal-backend-bff',
      description: 'FastAPI BFF (Backend for Frontend) structure mapping',
      generated: new Date().toISOString().split('T')[0],
      version: '1.0'
    },
    services: analyzeServices(path.join(backendPath, 'app/services')),
    routes: analyzeRoutes(path.join(backendPath, 'app/routes')),
    config: analyzeConfig(path.join(backendPath, 'app/config.py'))
  };
  
  const outputPath = path.join(skillsPath, 'backend-structure.json');
  fs.writeFileSync(outputPath, JSON.stringify(structure, null, 2));
  console.log(`✓ FastAPI BFF structure saved to ${outputPath}`);
}

// WebUI Backend 분석
function analyzeWebUIBackend() {
  console.log('Analyzing WebUI Backend (webui/backend/)...');
  
  const webuiBackendPath = path.join(projectRoot, 'webui/backend');
  const skillsPath = path.join(projectRoot, 'webui/.skills');
  
  if (!fs.existsSync(skillsPath)) {
    fs.mkdirSync(skillsPath, { recursive: true });
  }
  
  const structure = {
    metadata: {
      project: 'agent-portal-webui-backend',
      description: 'Open-WebUI backend structure mapping',
      generated: new Date().toISOString().split('T')[0],
      version: '1.0',
      pythonpath: '/app/backend (CRITICAL)'
    },
    structure: {
      root: 'webui/backend',
      module: 'open_webui',
      main: 'open_webui/main.py',
      pythonpath_required: true
    },
    routers: analyzeWebUIRouters(path.join(webuiBackendPath, 'open_webui/routers')),
    models: analyzeWebUIModels(path.join(webuiBackendPath, 'open_webui/models')),
    dev_environment: {
      dockerfile: 'webui/Dockerfile.dev',
      script: 'webui/dev-start.sh',
      pythonpath_config: [
        {
          location: 'Dockerfile.dev',
          line: 29,
          content: 'ENV PYTHONPATH=/app/backend:$PYTHONPATH'
        },
        {
          location: 'dev-start.sh',
          line: 27,
          content: 'PYTHONPATH=. uvicorn open_webui.main:app ...'
        }
      ],
      ports: {
        backend: 8080,
        frontend: 5173,
        external_backend: 3000,
        external_frontend: 3001
      }
    },
    common_issues: [
      {
        error: "ModuleNotFoundError: No module named 'open_webui'",
        cause: 'PYTHONPATH 미설정',
        solution: 'dev-start.sh에 PYTHONPATH=. 추가, Dockerfile.dev에 ENV PYTHONPATH 추가',
        reference: 'bug-fixes.md#2025-11-13'
      }
    ]
  };
  
  const outputPath = path.join(skillsPath, 'backend-structure.json');
  fs.writeFileSync(outputPath, JSON.stringify(structure, null, 2));
  console.log(`✓ WebUI Backend structure saved to ${outputPath}`);
}

// Helper functions
function analyzeServices(servicesPath) {
  if (!fs.existsSync(servicesPath)) return [];
  
  const files = fs.readdirSync(servicesPath).filter(f => f.endsWith('.py') && f !== '__init__.py');
  return files.map(file => {
    const name = file.replace('_service.py', '').split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') + ' Service';
    return {
      name,
      file: `app/services/${file}`,
      class: file.replace('.py', '').split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(''),
      singleton: file.replace('.py', ''),
      purpose: `Service for ${name.toLowerCase()}`,
      methods: []
    };
  });
}

function analyzeRoutes(routesPath) {
  if (!fs.existsSync(routesPath)) return [];
  
  const files = fs.readdirSync(routesPath).filter(f => f.endsWith('.py') && f !== '__init__.py');
  return files.map(file => {
    const name = file.replace('.py', '').split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') + ' API';
    const prefix = '/' + file.replace('.py', '').replace('_', '-');
    return {
      name,
      file: `app/routes/${file}`,
      prefix,
      endpoints: [],
      dependencies: []
    };
  });
}

function analyzeConfig(configPath) {
  if (!fs.existsSync(configPath)) return {};
  
  return {
    file: 'app/config.py',
    class: 'Settings',
    env_vars: []
  };
}

function analyzeWebUIRouters(routersPath) {
  if (!fs.existsSync(routersPath)) return [];
  
  const files = fs.readdirSync(routersPath).filter(f => f.endsWith('.py') && f !== '__init__.py');
  return files.map(file => {
    const prefix = '/' + file.replace('.py', '');
    const tags = [file.replace('.py', '')];
    return {
      path: `/routers/${file}`,
      prefix,
      tags
    };
  });
}

function analyzeWebUIModels(modelsPath) {
  if (!fs.existsSync(modelsPath)) return [];
  
  const files = fs.readdirSync(modelsPath).filter(f => f.endsWith('.py') && f !== '__init__.py');
  return files.map(file => {
    const table = file.replace('.py', '').replace(/s$/, '');
    return {
      file: `/models/${file}`,
      table
    };
  });
}

// 메인 실행
console.log('Starting backend structure analysis...\n');
analyzeFastAPIBFF();
console.log('');
analyzeWebUIBackend();
console.log('\n✓ Backend Skills analysis complete!');

