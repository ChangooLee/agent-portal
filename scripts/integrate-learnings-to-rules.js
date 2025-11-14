#!/usr/bin/env node

/**
 * integrate-learnings-to-rules.js
 * 
 * .cursor/learnings/*.md의 학습 내용을 분석하여
 * .cursor/rules/*.mdc 파일의 "Learning History" 섹션에 자동 통합합니다.
 * 
 * 기능:
 * 1. 학습 내용 파일 읽기 (.cursor/learnings/*)
 * 2. 반복 패턴 추출 (3회 이상 등장하는 키워드)
 * 3. .mdc 파일의 Learning History 섹션 업데이트
 * 4. 가드레일 자동 생성 (버그 수정 사례 → 가드레일)
 */

const fs = require('fs');
const path = require('path');

// 경로 설정
const PROJECT_ROOT = path.join(__dirname, '..');
const LEARNINGS_DIR = path.join(PROJECT_ROOT, '.cursor/learnings');
const RULES_DIR = path.join(PROJECT_ROOT, '.cursor/rules');

// 학습 파일 매핑
const LEARNING_TO_RULE_MAP = {
  'ui-patterns.md': 'ui-development.mdc',
  'api-patterns.md': 'backend-api.mdc',
  'bug-fixes.md': 'backend-api.mdc', // 버그 수정은 backend-api로
  'preferences.md': null // 모든 파일에 적용 (선호도)
};

// 최소 반복 횟수 (3회 이상 등장하는 패턴만 통합)
const MIN_PATTERN_COUNT = 3;

/**
 * 학습 파일 읽기
 */
function readLearningFile(filename) {
  const filepath = path.join(LEARNINGS_DIR, filename);
  
  if (!fs.existsSync(filepath)) {
    console.log(`⚠️  ${filename} not found, skipping...`);
    return null;
  }
  
  const content = fs.readFileSync(filepath, 'utf-8');
  return content;
}

/**
 * 학습 항목 파싱
 * 
 * 형식:
 * ## YYYY-MM-DD: 제목
 * **요청**: ...
 * **적용**: ...
 * **피드백**: ✅ or ❌
 * **재사용**: ...
 * ---
 */
function parseLearningItems(content) {
  const items = [];
  const regex = /## (\d{4}-\d{2}-\d{2}): (.+?)\n([\s\S]+?)---/g;
  
  let match;
  while ((match = regex.exec(content)) !== null) {
    const [, date, title, body] = match;
    
    // 필드 추출
    const requestMatch = body.match(/\*\*요청\*\*: (.+?)(?:\n|$)/);
    const appliedMatch = body.match(/\*\*적용\*\*: (.+?)(?:\n|$)/);
    const feedbackMatch = body.match(/\*\*피드백\*\*: (.+?)(?:\n|$)/);
    const reuseMatch = body.match(/\*\*재사용\*\*: (.+?)(?:\n|$)/);
    
    items.push({
      date,
      title,
      request: requestMatch ? requestMatch[1].trim() : '',
      applied: appliedMatch ? appliedMatch[1].trim() : '',
      feedback: feedbackMatch ? feedbackMatch[1].trim() : '',
      reuse: reuseMatch ? reuseMatch[1].trim() : '',
      rawBody: body.trim()
    });
  }
  
  return items;
}

/**
 * 반복 패턴 추출
 * 
 * "재사용" 필드에서 키워드 추출하여 반복 횟수 계산
 */
function extractRepeatingPatterns(items) {
  const patterns = {};
  
  items.forEach(item => {
    if (item.reuse) {
      const keywords = item.reuse
        .toLowerCase()
        .split(/[,.\s]+/)
        .filter(word => word.length > 2);
      
      keywords.forEach(keyword => {
        if (!patterns[keyword]) {
          patterns[keyword] = { count: 0, items: [] };
        }
        patterns[keyword].count++;
        patterns[keyword].items.push(item);
      });
    }
  });
  
  // MIN_PATTERN_COUNT 이상 등장하는 패턴만 반환
  const repeatingPatterns = Object.entries(patterns)
    .filter(([, data]) => data.count >= MIN_PATTERN_COUNT)
    .sort((a, b) => b[1].count - a[1].count);
  
  return repeatingPatterns;
}

/**
 * Learning History 섹션 생성
 */
function generateLearningHistorySection(items, repeatingPatterns) {
  let section = '\n## Learning History\n\n';
  section += '이 섹션은 `.cursor/learnings/` 디렉토리의 학습 내용에서 자동 생성되었습니다.\n\n';
  
  // 반복 패턴 섹션
  if (repeatingPatterns.length > 0) {
    section += '### 반복 패턴 (자동 통합)\n\n';
    
    repeatingPatterns.forEach(([keyword, data]) => {
      section += `#### ${keyword} (${data.count}회 등장)\n\n`;
      
      // 대표 사례 1개 표시
      const representative = data.items[0];
      section += `**학습**: ${representative.applied}\n\n`;
      section += `**재사용**: ${representative.reuse}\n\n`;
    });
  }
  
  // 최근 학습 내용 (최근 5개)
  section += '### 최근 학습 내용\n\n';
  
  const recentItems = items.slice(-5).reverse();
  recentItems.forEach(item => {
    section += `#### ${item.date}: ${item.title}\n\n`;
    section += `**피드백**: ${item.feedback}\n\n`;
    if (item.applied) {
      section += `**적용**: ${item.applied}\n\n`;
    }
    if (item.reuse) {
      section += `**재사용**: ${item.reuse}\n\n`;
    }
  });
  
  return section;
}

/**
 * .mdc 파일에 Learning History 섹션 추가/업데이트
 */
function updateMdcFile(filename, learningHistorySection) {
  const filepath = path.join(RULES_DIR, filename);
  
  if (!fs.existsSync(filepath)) {
    console.log(`⚠️  ${filename} not found, skipping...`);
    return false;
  }
  
  let content = fs.readFileSync(filepath, 'utf-8');
  
  // 기존 Learning History 섹션 제거
  content = content.replace(/\n## Learning History[\s\S]*$/, '');
  
  // 새 Learning History 섹션 추가
  content += learningHistorySection;
  
  fs.writeFileSync(filepath, content, 'utf-8');
  console.log(`✅ Updated ${filename} with Learning History`);
  
  return true;
}

/**
 * 가드레일 생성 (버그 수정 사례 → 가드레일)
 */
function generateGuardrailsFromBugFixes(bugFixItems) {
  const guardrails = [];
  
  bugFixItems.forEach(item => {
    // "증상", "근본 원인", "해결 방법", "예방" 필드 추출
    const symptomMatch = item.rawBody.match(/\*\*증상\*\*:[\s\S]+?(?=\*\*|$)/);
    const causeMatch = item.rawBody.match(/\*\*근본 원인\*\*:[\s\S]+?(?=\*\*|$)/);
    const solutionMatch = item.rawBody.match(/\*\*해결 방법\*\*:[\s\S]+?(?=\*\*|$)/);
    const preventionMatch = item.rawBody.match(/\*\*예방\*\*:[\s\S]+?(?=\*\*|$)/);
    
    if (symptomMatch && causeMatch && solutionMatch) {
      guardrails.push({
        title: item.title,
        symptom: symptomMatch[0].replace('**증상**:', '').trim(),
        cause: causeMatch[0].replace('**근본 원인**:', '').trim(),
        solution: solutionMatch[0].replace('**해결 방법**:', '').trim(),
        prevention: preventionMatch ? preventionMatch[0].replace('**예방**:', '').trim() : ''
      });
    }
  });
  
  return guardrails;
}

/**
 * 가드레일 섹션 업데이트
 */
function updateGuardrailsSection(filename, guardrails) {
  const filepath = path.join(RULES_DIR, filename);
  
  if (!fs.existsSync(filepath)) {
    console.log(`⚠️  ${filename} not found, skipping...`);
    return false;
  }
  
  let content = fs.readFileSync(filepath, 'utf-8');
  
  // 가드레일 섹션 찾기
  const guardrailSectionMatch = content.match(/## 가드레일[\s\S]*?(?=\n## |$)/);
  
  if (!guardrailSectionMatch) {
    console.log(`⚠️  No 가드레일 section found in ${filename}, skipping...`);
    return false;
  }
  
  // 기존 가드레일 섹션
  let guardrailSection = guardrailSectionMatch[0];
  
  // 새 가드레일 추가 (중복 체크)
  guardrails.forEach(guardrail => {
    if (!guardrailSection.includes(guardrail.title)) {
      guardrailSection += `\n\n### 문제: ${guardrail.title}\n\n`;
      guardrailSection += `**증상**:\n${guardrail.symptom}\n\n`;
      guardrailSection += `**근본 원인**:\n${guardrail.cause}\n\n`;
      guardrailSection += `**해결** (대안 제시):\n${guardrail.solution}\n\n`;
      if (guardrail.prevention) {
        guardrailSection += `**예방**:\n${guardrail.prevention}\n\n`;
      }
    }
  });
  
  // 업데이트
  content = content.replace(/## 가드레일[\s\S]*?(?=\n## |$)/, guardrailSection);
  
  fs.writeFileSync(filepath, content, 'utf-8');
  console.log(`✅ Updated 가드레일 section in ${filename}`);
  
  return true;
}

/**
 * 메인 함수
 */
function main() {
  console.log('📚 Integrating learnings to rules...\n');
  
  // 각 학습 파일 처리
  Object.entries(LEARNING_TO_RULE_MAP).forEach(([learningFile, ruleFile]) => {
    console.log(`\n🔍 Processing ${learningFile}...`);
    
    const content = readLearningFile(learningFile);
    if (!content) return;
    
    const items = parseLearningItems(content);
    console.log(`   Found ${items.length} learning items`);
    
    // 반복 패턴 추출
    const repeatingPatterns = extractRepeatingPatterns(items);
    console.log(`   Found ${repeatingPatterns.length} repeating patterns`);
    
    // Learning History 섹션 생성
    const learningHistorySection = generateLearningHistorySection(items, repeatingPatterns);
    
    // .mdc 파일 업데이트
    if (ruleFile) {
      updateMdcFile(ruleFile, learningHistorySection);
    }
    
    // 버그 수정 → 가드레일 변환
    if (learningFile === 'bug-fixes.md' && ruleFile) {
      const guardrails = generateGuardrailsFromBugFixes(items);
      console.log(`   Generated ${guardrails.length} guardrails from bug fixes`);
      
      if (guardrails.length > 0) {
        updateGuardrailsSection(ruleFile, guardrails);
      }
    }
  });
  
  console.log('\n✨ Integration complete!\n');
}

// 실행
if (require.main === module) {
  main();
}

module.exports = { main };

