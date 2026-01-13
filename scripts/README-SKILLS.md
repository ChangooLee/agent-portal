# Skills System Guide

Agent Portal의 Skills 시스템 가이드입니다.

## 목차

1. [개요](#개요)
2. [Skills 시스템 구조](#skills-시스템-구조)
3. [.mdc 파일 작성 가이드](#mdc-파일-작성-가이드)
4. [자동화 스크립트](#자동화-스크립트)
5. [Git Hooks 연동](#git-hooks-연동)
6. [주간 리뷰 프로세스](#주간-리뷰-프로세스)
7. [FAQ](#faq)

---

## 개요

Skills 시스템은 AI 에이전트(Cursor AI)가 프로젝트를 이해하고 효율적으로 작업할 수 있도록 돕는 문서화 시스템입니다.

### 핵심 원칙

- **.mdc 파일이 최종 규칙**: AI가 직접 읽고 참조하는 Markdown 문서
- **Skills JSON은 중간 분석 결과**: 자동 분석 스크립트의 출력물
- **학습 내용 자동 통합**: `.cursor/learnings/` → `.mdc` 파일로 자동 통합
- **Git Hooks 자동화**: 커밋 시 Skills 시스템 자동 업데이트

### Anthropic Skills와의 차이

| 항목 | Anthropic Skills | Agent Portal Skills |
|------|------------------|---------------------|
| 플랫폼 | Claude.ai / Claude Code | Cursor AI |
| 구조 | 1 skill = 1 dir (SKILL.md) | .cursor/rules/*.mdc |
| 사용 방식 | API 동적 로딩 | Context 주입 |
| 자동화 | 수동 관리 | Git Hooks 자동 업데이트 |
| 학습 통합 | 미지원 | 주간 리뷰로 자동 통합 |

**채택한 원칙**:
- ✅ YAML frontmatter (name, description, version, lastUpdated)
- ✅ Examples 섹션 (실제 코드 스니펫)
- ✅ Learning History 섹션 (자동 통합)
- ❌ 1 skill = 1 dir (불필요, .mdc 파일로 충분)

---

## Skills 시스템 구조

```
agent-portal/
├── .cursor/
│   ├── rules/                          # AI가 읽는 최종 규칙
│   │   ├── ui-development.mdc          # UI 개발 규칙
│   │   ├── backend-api.mdc             # Backend API 규칙
│   │   ├── news-feature.mdc            # News 기능 규칙
│   │   ├── admin-screens.mdc           # Admin 화면 규칙
│   │   ├── planning-strategies.mdc     # 8가지 계획 전략
│   │   └── learning-patterns.mdc       # 학습 축적 시스템
│   └── learnings/                      # 학습 내용 (자동 통합)
│       ├── ui-patterns.md
│       ├── api-patterns.md
│       ├── bug-fixes.md
│       └── preferences.md
├── webui/.skills/                      # UI 분석 결과 (JSON)
│   ├── ui-structure.json
│   ├── ui-patterns.json
│   ├── ui-layouts.json
│   └── ui-navigation.json
├── backend/.skills/                    # Backend 분석 결과 (JSON)
│   └── backend-structure.json
└── scripts/
    ├── integrate-learnings-to-rules.js # 학습 내용 자동 통합
    ├── weekly-review.sh                # 주간 리뷰 스크립트
    └── update-ui-skills.sh             # UI Skills JSON 업데이트
```

### 문서 우선 순위

AI가 참조하는 순서:

1. **`.cursor/rules/*.mdc`** (특화 규칙) ⭐ 최우선
2. **`CLAUDE.md`, `AGENTS.md`** (프로젝트 가이드)
3. **`.cursor/learnings/*.md`** (학습 내용)
4. **`webui/.skills/*.json`** (분석 결과, 보조)

---

## .mdc 파일 작성 가이드

### YAML Frontmatter

모든 .mdc 파일은 다음 YAML frontmatter를 포함해야 합니다:

```yaml
---
name: skill-name
description: 스킬 설명 (한 줄)
globs: path/to/files/**/*.ext
alwaysApply: false
version: 1.0
lastUpdated: 2025-11-14
---
```

**필드 설명**:
- `name`: 스킬 이름 (영문, kebab-case)
- `description`: 스킬 설명 (한 줄, 한글)
- `globs`: 이 스킬이 적용되는 파일 패턴
- `alwaysApply`: 항상 적용 여부 (true/false)
- `version`: 스킬 버전 (Semantic Versioning)
- `lastUpdated`: 마지막 업데이트 날짜 (YYYY-MM-DD, Git Hook 자동 업데이트)

### 필수 섹션

#### 1. Overview

스킬의 목적과 범위를 설명합니다.

```markdown
## Overview

이 문서는 SvelteKit 기반 UI 개발의 모든 패턴과 규칙을 정의합니다. 
Skills 시스템을 활용한 자연어 기반 UI 검색, Glassmorphism 디자인, 
무한 스크롤, 실시간 검색 등 현대적인 웹 개발 패턴을 포함합니다.
```

#### 2. Examples

실제 코드 스니펫과 Before/After 비교를 포함합니다.

```markdown
## Examples

### Example 1: 탭 스타일 변경 (Before/After)

**Before** (구식 패턴):
\`\`\`svelte
<!-- ❌ 사용하지 말 것 -->
<button class="border-b-2 {activeTab === 'summary' ? 'border-blue-500' : 'border-transparent'}">
  탭
</button>
\`\`\`

**After** (모던 패턴):
\`\`\`svelte
<!-- ✅ 권장 패턴 -->
<button 
  class="px-4 py-2 rounded-lg {activeTab === 'summary' ? 'bg-[#0072CE] text-white shadow-sm' : 'text-gray-600 hover:bg-gray-50'} transition-all duration-200"
>
  탭
</button>
\`\`\`

**학습**: border-b-2 대신 rounded-lg 버튼이 더 모던하고 사용자 친화적
```

#### 3. Guidelines

구체적인 규칙과 패턴을 설명합니다.

```markdown
## Guidelines

### 패턴 1: 무한 스크롤

**사용 시점**: 목록이 20개 이상인 경우

**패턴**:
- `IntersectionObserver` 사용
- `afterUpdate`에서 observer 설정 (onMount는 DOM 준비 보장 안 됨)
- `threshold: 0.1`로 조기 로딩

**구현**:
\`\`\`svelte
// ... 코드 ...
\`\`\`
```

#### 4. Learning History (자동 생성)

주간 리뷰 시 `.cursor/learnings/`에서 자동 통합됩니다.

```markdown
## Learning History

이 섹션은 `.cursor/learnings/` 디렉토리의 학습 내용에서 자동 생성되었습니다.

### 반복 패턴 (자동 통합)

#### afterUpdate (5회 등장)

**학습**: onMount가 아닌 afterUpdate에서 IntersectionObserver 설정해야 DOM 준비 보장

**재사용**: 무한 스크롤 구현 시 항상 afterUpdate 사용

### 최근 학습 내용

#### 2025-11-14: 무한 스크롤 IntersectionObserver 설정 시점

**피드백**: ✅ 잘 잡았어 (onMount에서는 DOM 준비 보장 안 됨)

**적용**: afterUpdate에서 observer 설정

**재사용**: 무한 스크롤 구현 시 항상 afterUpdate 사용
```

---

## 자동화 스크립트

### 1. integrate-learnings-to-rules.js

**목적**: `.cursor/learnings/*.md`의 학습 내용을 분석하여 `.cursor/rules/*.mdc`의 Learning History 섹션에 자동 통합

**사용**:
```bash
node scripts/integrate-learnings-to-rules.js
```

**기능**:
- 학습 파일 파싱 (ui-patterns.md, api-patterns.md, bug-fixes.md, preferences.md)
- 반복 패턴 추출 (3회 이상 등장하는 키워드)
- Learning History 섹션 생성
- 버그 수정 → 가드레일 변환

### 2. weekly-review.sh

**목적**: 주간 리뷰 (매주 금요일 실행 권장)

**사용**:
```bash
./scripts/weekly-review.sh
```

**기능**:
1. 학습 내용 요약
2. 학습 내용 자동 통합 (`integrate-learnings-to-rules.js` 호출)
3. 반복 패턴 분석
4. 가드레일 업데이트 제안
5. 문서 동기화 확인
6. Skills JSON 업데이트

### 3. update-ui-skills.sh

**목적**: UI Skills JSON 파일 업데이트

**사용**:
```bash
./scripts/update-ui-skills.sh
```

**기능**:
- `ui-structure.json` 생성 (라우트/컴포넌트 구조)
- `ui-patterns.json` 생성 (스타일 패턴)
- `ui-layouts.json` 생성 (레이아웃 계층)
- `ui-navigation.json` 생성 (네비게이션 구조)

### 4. protect-env.sh / restore-env.sh

**목적**: `.env` 파일 보호 (민감 정보 - API 키, 비밀번호 등)

**사용**:
```bash
# git clean 실행 전 백업
./scripts/protect-env.sh

# git clean 실행
git clean -fdx

# git clean 실행 후 복구
./scripts/restore-env.sh
```

**기능**:
- `protect-env.sh`: `.env` 파일을 `.env.backup.protected`로 백업
- `restore-env.sh`: 백업 파일에서 `.env` 파일 복구 후 백업 파일 삭제

**주의사항**:
- `git clean -fdx` 실행 시 `-x` 옵션으로 `.gitignore`에 포함된 파일도 삭제됨
- `.env` 파일은 `.gitignore`에 포함되어 있어 `git clean -fdx` 실행 시 삭제될 수 있음
- **반드시** `git clean -fdx` 실행 전에 `./scripts/protect-env.sh` 실행 필요

---

## Git Hooks 연동

### pre-commit Hook

**위치**: `.githooks/pre-commit`

**기능**:
1. UI 파일 변경 시 Skills 업데이트 알림
2. **.mdc 파일 lastUpdated 자동 업데이트** ⭐
3. 핵심 문서 동기화 체크
4. Python 파일 린트 (flake8)
5. Svelte 파일 체크 (svelte-check)

**설치**:
```bash
# Git hooks 설치
cp .githooks/* .git/hooks/
chmod +x .git/hooks/*

# 또는 자동 설치 스크립트 사용
./scripts/install-git-hooks.sh
```

### post-commit Hook

**위치**: `.githooks/post-commit`

**기능**:
- 커밋 메시지에서 학습 내용 추출 (`Learning:` 키워드)
- `.cursor/learnings/` 디렉토리에 자동 분류 저장

**커밋 메시지 형식**:
```bash
git commit -m "feat(ui): 탭 스타일 변경

- border-b-2 → rounded-lg 버튼으로 변경

Learning: 탭 스타일은 border-b-2 대신 rounded-lg 버튼으로 변경하는 것이 더 모던함
"
```

---

## 주간 리뷰 프로세스

### 목적

학습 내용을 핵심 문서에 통합하여 AI가 반복적인 실수를 방지하도록 합니다.

### 절차

**매주 금요일 실행**:
```bash
./scripts/weekly-review.sh
```

**프로세스**:
1. **학습 내용 요약**: `.cursor/learnings/` 파일 통계
2. **자동 통합**: `integrate-learnings-to-rules.js` 실행
3. **반복 패턴 분석**: 3회 이상 등장하는 키워드 추출
4. **가드레일 제안**: 버그 수정 → 가드레일 변환
5. **문서 동기화**: `sync-docs.sh` 실행
6. **Skills 업데이트**: `update-ui-skills.sh` 실행

**수동 리뷰 필요**:
- Learning History 섹션 검토
- 중요한 패턴을 CLAUDE.md/AGENTS.md에 수동 추가
- 가드레일 업데이트
- PR 생성

---

## FAQ

### Q1: .mdc 파일과 Skills JSON의 차이는?

**A**: 
- **.mdc 파일**: AI가 직접 읽는 **최종 규칙** (Markdown, Examples, Learning History 포함)
- **Skills JSON**: 자동 분석 스크립트의 **중간 결과** (UI 구조/패턴 분석)

AI는 .mdc 파일을 우선 참조합니다.

### Q2: 언제 .mdc 파일을 수정하나?

**A**:
- **자동**: Git pre-commit hook이 `lastUpdated` 필드 자동 업데이트
- **수동**: 새로운 패턴 발견, 규칙 변경, 가드레일 추가 시

### Q3: 학습 내용은 어떻게 통합되나?

**A**:
1. **자동 기록**: Git post-commit hook이 커밋 메시지에서 추출
2. **수동 기록**: `./scripts/record-learning.sh` 사용
3. **자동 통합**: 주간 리뷰(`weekly-review.sh`)가 Learning History 섹션에 통합

### Q4: 기존 규칙을 변경하려면?

**A**:
1. 해당 .mdc 파일 직접 수정
2. `lastUpdated`는 Git pre-commit hook이 자동 업데이트
3. 커밋 후 AI가 자동으로 새 규칙 참조

### Q5: 새 .mdc 파일을 추가하려면?

**A**:
1. `.cursor/rules/` 디렉토리에 새 파일 생성
2. YAML frontmatter + 필수 섹션(Overview, Examples, Guidelines) 작성
3. `.cursorrules` 파일의 "필수 참조 문서" 섹션에 추가
4. 커밋

### Q6: Skills JSON은 언제 업데이트하나?

**A**:
- **UI Skills**: UI 파일 변경 시 `./scripts/update-ui-skills.sh` 실행
- **Backend Skills**: Backend 파일 변경 시 `./scripts/analyze-backend-structure.js` 실행 (주간 리뷰에 포함)

### Q7: Anthropic Skills와 호환되나?

**A**:
**부분 호환**:
- ✅ YAML frontmatter 구조 유사
- ✅ Examples 섹션 패턴 동일
- ❌ 디렉토리 구조 다름 (1 skill = 1 file, not 1 dir)
- ❌ API 동적 로딩 미지원 (Cursor AI는 Context 주입 방식)

Anthropic Skills의 핵심 원칙만 차용하되, Cursor AI 환경에 최적화했습니다.

---

## 참고 자료

- [Anthropic Skills Documentation](https://docs.claude.com/en/docs/claude-code/skills)
- [Planning-Centric AI Coding](https://news.hada.io/topic?id=24266)
- [Cursor AI 사용 가이드](https://news.hada.io/topic?id=24099)
- [프로젝트 CLAUDE.md](../CLAUDE.md)
- [프로젝트 AGENTS.md](../AGENTS.md)

---

**마지막 업데이트**: 2025-11-14  
**버전**: 1.0

