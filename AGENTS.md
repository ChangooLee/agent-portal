# AGENTS.md — AI-Powered Automatic Upgrade & Maintenance Workflows

> **목표**: AI 에이전트를 활용하여 **루틴 업그레이드, 의존성 관리, 보안 패치, 코드 개선**을 자동화하고,
> 각 단계마다 **PR(Pull Request) 검토 및 승인**을 통해 안전하게 변경사항을 적용하는 워크플로우 구축

---

## 0. 철학 및 원칙 (Philosophy)

### 0.1 "Shoot and Forget" — 결과 중심 위임

AI 에이전트에게 **충분한 컨텍스트와 명확한 목표**를 제공한 후,
중간 과정보다는 **최종 PR의 품질**로 평가합니다.

**핵심 원칙**:
- 에이전트는 **작업 완료 후 PR 생성**까지 자율적으로 수행
- 인간은 **PR 검토 및 승인** 단계에서만 개입
- 실패 시 에이전트가 **자동 재시도** 또는 **이슈 생성**

### 0.2 Context is King — CLAUDE.md를 "헌법"으로

프로젝트 루트의 **CLAUDE.md** 파일이 에이전트의 행동 규칙과 가드레일을 정의합니다.

**CLAUDE.md 작성 원칙**:
- **간결하게 유지**: 13KB 이하 권장 (엔터프라이즈 모노레포 기준)
- **실패 기반 학습**: 실제 에이전트 실패 사례를 바탕으로 가드레일 추가
- **@-file 남용 금지**: 컨텍스트 창을 불필요한 파일로 채우지 않음
- **업데이트 전략**: 새로운 실패 패턴 발견 시마다 점진적 개선

### 0.3 Hooks as Enforcement — 실패 방지 안전장치

**Block-at-submit hooks**: 테스트 실패 시 커밋 차단
**Hint hooks**: 비차단 피드백 제공 (예: 코드 스타일 경고)

**예시**:
- `pre-commit`: 린트/포맷 자동 실행
- `pre-push`: 유닛 테스트 통과 확인
- `user-prompt-submit-hook`: 에이전트가 특정 체크리스트 완료 여부 검증

### 0.4 PR-Based Workflow — 안전한 변경 관리

모든 AI 에이전트의 작업은 **Pull Request**로 제출되며,
인간 검토자가 **승인 후 병합**합니다.

**워크플로우**:
1. 에이전트가 작업 수행 (코드 수정, 테스트 실행)
2. 변경사항을 새 브랜치에 커밋
3. PR 생성 (자동 템플릿 포함)
4. CI/CD 파이프라인 실행 (자동 테스트)
5. **인간 검토 및 승인 대기** ← **핵심 게이트**
6. 승인 후 자동 병합 (또는 수동 병합)

---

## 1. 프로젝트 구조 및 에이전트 역할

### 1.1 Agent Portal 프로젝트 개요

본 프로젝트는 **3-in-1 OSS 슈퍼 포털**로 다음을 통합합니다:
- **Portal A (Agent)**: Open-WebUI 기반
- **Portal B (Notebook)**: Open Notebook
- **Portal C (Research)**: Perplexica

**기술 스택**:
- Backend: FastAPI, LiteLLM, LangGraph
- Frontend: Open-WebUI (AGPL 포크)
- Data: MariaDB, ChromaDB, Redis, MinIO
- Observability: Langfuse, Helicone
- Security: Kong Gateway

### 1.2 AI 에이전트 적용 영역

| 영역 | 에이전트 작업 | 주기 | PR 필수 여부 |
|------|--------------|------|--------------|
| **의존성 업그레이드** | Python/Node 패키지 업데이트 | 주간 | ✅ 필수 |
| **보안 패치** | CVE 대응, 취약점 수정 | 즉시 | ✅ 필수 |
| **포크 동기화** | Open-WebUI/Perplexica 상류 머지 | 월간 | ✅ 필수 |
| **문서 갱신** | README/DEVELOP.md 자동 업데이트 | 변경 시 | ⚠️ 선택 |
| **테스트 생성** | 새 기능에 대한 유닛 테스트 | 기능 추가 시 | ✅ 필수 |
| **코드 리팩토링** | 중복 제거, 성능 개선 | 분기별 | ✅ 필수 |
| **Docker 이미지 업데이트** | 베이스 이미지 갱신 | 월간 | ✅ 필수 |

---

## 2. CLAUDE.md 설정 (프로젝트 컨텍스트)

### 2.1 기본 구조

```markdown
# Agent Portal — AI 에이전트 가이드

## 프로젝트 개요
3-in-1 OSS 포털 (Open-WebUI + Open Notebook + Perplexica)
기술 스택: FastAPI, LiteLLM, LangGraph, Kong, MariaDB, ChromaDB

## 디렉토리 구조
- `backend/`: FastAPI BFF
- `webui/`: Open-WebUI 포크 (AGPL)
- `open-notebook/`, `perplexica/`: 추가 포털
- `config/`: litellm.yaml, kong.yml
- `scripts/`: 테스트 및 배포 스크립트

## 코딩 표준
- Python: PEP 8, type hints 필수
- JavaScript/TypeScript: ESLint + Prettier
- Docker: 멀티스테이지 빌드 권장
- 커밋 메시지: Conventional Commits 형식

## 테스트 요구사항
- 유닛 테스트: pytest (Python), Jest (JS)
- E2E 테스트: `scripts/test-stage-*.sh` 실행
- 커버리지: 최소 80% 유지

## 보안 가이드라인
- 비밀키는 `.env` 파일로 관리 (절대 커밋 금지)
- Kong 설정 변경 시 보안 검토 필수
- 의존성 취약점: `pip-audit`, `npm audit` 통과 확인

## 금지 사항
- `main` 브랜치에 직접 푸시 금지
- `.env` 파일 커밋 금지
- 포크 라이선스 변경 금지 (AGPL/MIT 준수)
- 테스트 없이 PR 생성 금지

## 성공 기준
- 모든 CI 체크 통과
- 코드 리뷰 승인 (최소 1명)
- 문서 업데이트 포함 (기능 변경 시)
```

### 2.2 프로젝트 루트에 CLAUDE.md 생성

```bash
# 프로젝트 루트에 생성
cat > CLAUDE.md << 'EOF'
[위 기본 구조 내용 붙여넣기]
EOF
```

---

## 3. 자동 업그레이드 워크플로우

### 3.1 의존성 업그레이드 (Python 패키지)

**시나리오**: `backend/requirements.txt` 패키지를 최신 버전으로 업데이트

#### 3.1.1 GitHub Actions 워크플로우

`.github/workflows/auto-upgrade-python.yml`

```yaml
name: Auto Upgrade Python Dependencies

on:
  schedule:
    - cron: '0 2 * * 1'  # 매주 월요일 02:00 UTC
  workflow_dispatch:       # 수동 트리거

jobs:
  upgrade:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Run Claude Code Agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          # Claude Code CLI를 사용한 에이전트 실행
          npx @anthropic-ai/claude-code run \
            --prompt "Upgrade all Python dependencies in backend/requirements.txt to latest compatible versions. Run tests and create PR if successful." \
            --auto-approve-tools \
            --output upgrade-report.md

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          branch: auto/upgrade-python-deps
          title: "chore: Upgrade Python dependencies"
          body: |
            ## Automated Dependency Upgrade

            This PR was created by AI agent to upgrade Python dependencies.

            ### Changes
            - Updated packages in `backend/requirements.txt`
            - All tests passed

            ### Review Checklist
            - [ ] Check breaking changes in upgrade notes
            - [ ] Verify test coverage
            - [ ] Review security advisories

            Generated with [Claude Code](https://claude.com/claude-code)
          commit-message: |
            chore: Upgrade Python dependencies

            - Update backend/requirements.txt to latest versions
            - All tests passing

            Generated with [Claude Code](https://claude.com/claude-code)

            Co-Authored-By: Claude <noreply@anthropic.com>
          labels: dependencies, automated
```

#### 3.1.2 로컬 테스트 (Claude Code CLI)

```bash
# 로컬에서 에이전트 실행 (대화형)
claude-code

# 프롬프트 입력:
# "Upgrade Python dependencies in backend/requirements.txt.
#  For each package, check latest compatible version, update requirements.txt,
#  run pytest, and create a summary report."
```

### 3.2 보안 패치 자동 적용

**시나리오**: GitHub Dependabot/Snyk 경고 발생 시 자동 패치

`.github/workflows/auto-security-patch.yml`

```yaml
name: Auto Security Patch

on:
  repository_dispatch:
    types: [security-alert]
  schedule:
    - cron: '0 0 * * *'  # 매일 00:00 UTC

jobs:
  security-patch:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      security-events: read

    steps:
      - uses: actions/checkout@v4

      - name: Check for vulnerabilities
        id: audit
        run: |
          pip install pip-audit
          pip-audit -r backend/requirements.txt --format json > vulnerabilities.json || true

          npm audit --json > npm-vulnerabilities.json || true

      - name: Run Claude Code Agent
        if: steps.audit.outcome == 'success'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          npx @anthropic-ai/claude-code run \
            --prompt "Review vulnerabilities.json and npm-vulnerabilities.json. Fix all HIGH and CRITICAL issues. Update dependencies, run tests, and create PR with security advisory summary." \
            --context "vulnerabilities.json,npm-vulnerabilities.json,CLAUDE.md" \
            --output patch-report.md

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          branch: auto/security-patch
          title: "security: Fix vulnerabilities in dependencies"
          body-path: patch-report.md
          labels: security, automated, high-priority
```

### 3.3 포크 동기화 (Open-WebUI 상류 머지)

**시나리오**: Open-WebUI 상류 저장소의 보안 패치를 선별적으로 체리픽

`.github/workflows/auto-fork-sync.yml`

```yaml
name: Auto Fork Sync (Open-WebUI)

on:
  schedule:
    - cron: '0 3 1 * *'  # 매월 1일 03:00 UTC
  workflow_dispatch:

jobs:
  fork-sync:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 전체 히스토리 필요

      - name: Add upstream remote
        run: |
          git remote add upstream https://github.com/open-webui/open-webui.git
          git fetch upstream

      - name: Run Claude Code Agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          npx @anthropic-ai/claude-code run \
            --prompt "Review upstream commits since our AGPL fork (60d84a3a). Cherry-pick security patches and critical bug fixes. Avoid features that conflict with our customizations in webui/overrides/. Create PR with detailed changelog." \
            --context "CLAUDE.md,README.md,webui/overrides/*" \
            --output sync-report.md

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          branch: auto/fork-sync-webui
          title: "chore: Sync Open-WebUI upstream security patches"
          body-path: sync-report.md
          labels: maintenance, upstream-sync
```

### 3.4 Docker 베이스 이미지 업데이트

**시나리오**: `Dockerfile`의 베이스 이미지를 최신 보안 패치 버전으로 업데이트

`.github/workflows/auto-docker-update.yml`

```yaml
name: Auto Docker Base Image Update

on:
  schedule:
    - cron: '0 4 * * 0'  # 매주 일요일 04:00 UTC
  workflow_dispatch:

jobs:
  docker-update:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - name: Run Claude Code Agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          npx @anthropic-ai/claude-code run \
            --prompt "Update all Dockerfile base images (python, node, nginx) to latest patch versions. Rebuild images locally and run docker-compose smoke tests. Create PR with build logs." \
            --context "*/Dockerfile,docker-compose.yml,CLAUDE.md" \
            --output docker-update.md

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          branch: auto/docker-base-update
          title: "chore: Update Docker base images"
          body-path: docker-update.md
          labels: docker, maintenance
```

---

## 4. 로컬 에이전트 실행 (Claude Code)

### 4.1 설치

```bash
# Claude Code CLI 설치
npm install -g @anthropic-ai/claude-code

# 또는 로컬 프로젝트에서
npx @anthropic-ai/claude-code --version
```

### 4.2 대화형 모드

```bash
# 프로젝트 루트에서 실행
cd /path/to/agent-portal
claude-code

# 에이전트와 대화 시작
# 예: "Upgrade LiteLLM to latest version and update config/litellm.yaml if needed"
```

### 4.3 스크립트 모드 (자동화)

```bash
# 단일 프롬프트 실행
claude-code run --prompt "Analyze backend/app/routes/chat.py for potential performance improvements"

# 컨텍스트 파일 지정
claude-code run \
  --prompt "Review all API endpoints in backend/app/routes/ and generate OpenAPI docs" \
  --context "backend/app/routes/*.py,CLAUDE.md"

# 출력 파일 지정
claude-code run \
  --prompt "Run all E2E tests and create summary report" \
  --output test-report.md
```

### 4.4 Planning Mode 활용

**복잡한 작업 (예: 새 기능 추가)에는 Planning Mode 사용**:

```bash
claude-code plan

# 프롬프트:
# "Add rate limiting to all FastAPI endpoints using Kong.
#  Update Kong config, add middleware, write tests, update docs."

# 에이전트가 계획 수립 → 승인 → 실행
```

---

## 5. Hooks 설정 (실패 방지)

### 5.1 Pre-Commit Hook (코드 품질)

`.git/hooks/pre-commit`

```bash
#!/bin/bash
set -e

echo "Running pre-commit checks..."

# Python: Black, Flake8
if git diff --cached --name-only | grep -q '\.py$'; then
  echo "Checking Python files..."
  black --check backend/
  flake8 backend/
fi

# JavaScript: ESLint, Prettier
if git diff --cached --name-only | grep -q '\.[jt]sx\?$'; then
  echo "Checking JavaScript/TypeScript files..."
  npm run lint
  npm run format:check
fi

# 비밀키 검사
echo "Scanning for secrets..."
git diff --cached --name-only | xargs grep -E "(API_KEY|SECRET|PASSWORD)" && {
  echo "ERROR: Potential secret detected in staged files!"
  exit 1
} || true

echo "Pre-commit checks passed!"
```

### 5.2 Pre-Push Hook (테스트 실행)

`.git/hooks/pre-push`

```bash
#!/bin/bash
set -e

echo "Running pre-push checks..."

# 유닛 테스트
echo "Running Python tests..."
cd backend && pytest tests/unit/ && cd ..

echo "Running JavaScript tests..."
cd webui && npm test && cd ..

# Docker 빌드 테스트
echo "Testing Docker build..."
docker-compose build backend webui

echo "Pre-push checks passed!"
```

### 5.3 User Prompt Submit Hook (에이전트용)

`.claude/hooks/user-prompt-submit.sh`

```bash
#!/bin/bash
# Claude Code 에이전트가 PR 생성 전 실행하는 체크리스트

echo "Checking agent submission requirements..."

# 1. 테스트 실행 여부 확인
if [ ! -f "test-results.xml" ]; then
  echo "ERROR: Tests not run. Please run pytest before submission."
  exit 1
fi

# 2. 문서 업데이트 확인 (API 변경 시)
if git diff --name-only | grep -q 'backend/app/routes/'; then
  if ! git diff --name-only | grep -q 'README.md\|DEVELOP.md'; then
    echo "WARNING: API routes changed but docs not updated."
    # 차단하지는 않음 (hint hook)
  fi
fi

# 3. CHANGELOG 업데이트 확인
if [ -f "CHANGELOG.md" ]; then
  if ! git diff --name-only | grep -q 'CHANGELOG.md'; then
    echo "WARNING: Changes detected but CHANGELOG not updated."
  fi
fi

echo "Agent submission checks completed."
```

---

## 6. PR 템플릿 설정

### 6.1 기본 PR 템플릿

`.github/pull_request_template.md`

```markdown
## Description
<!-- AI 에이전트 또는 개발자가 변경사항 설명 -->

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Dependency upgrade
- [ ] Security patch

## Automated Checks
- [ ] All CI/CD pipelines passed
- [ ] Test coverage maintained or improved
- [ ] No new security vulnerabilities introduced
- [ ] Linting and formatting checks passed

## Human Review Checklist
- [ ] Code changes reviewed for logic errors
- [ ] Breaking changes identified and documented
- [ ] Security implications assessed
- [ ] Performance impact evaluated
- [ ] Documentation updated (if applicable)

## Testing
<!-- Describe the tests that ran to verify your changes -->

- [ ] Unit tests added/updated
- [ ] E2E tests passed
- [ ] Manual testing completed (if applicable)

## Screenshots (if applicable)
<!-- Add screenshots for UI changes -->

---

**AI Generated**: This PR was created by an AI agent. Please review carefully before merging.

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 6.2 보안 패치 전용 템플릿

`.github/PULL_REQUEST_TEMPLATE/security_patch.md`

```markdown
## Security Patch Summary

**Vulnerability ID**: <!-- CVE-XXXX-XXXX or Dependabot alert # -->

**Severity**: <!-- LOW / MEDIUM / HIGH / CRITICAL -->

**Affected Components**:
<!-- List affected packages/modules -->

## Fix Applied
<!-- Describe the patch or upgrade -->

## Testing
- [ ] Vulnerability scanner confirms fix (pip-audit / npm audit)
- [ ] All existing tests pass
- [ ] No breaking changes introduced

## Security Review Checklist
- [ ] Upgrade notes reviewed
- [ ] Transitive dependencies checked
- [ ] Runtime behavior verified
- [ ] Production deployment plan ready

---

**Automated Security Patch**: This PR was created by AI agent in response to security advisory.
```

---

## 7. 실전 예제: 단계별 PR 워크플로우

### 7.1 시나리오: LiteLLM 버전 업그레이드

**목표**: LiteLLM을 v1.30.0에서 v1.35.0으로 업그레이드

#### Step 1: 로컬에서 에이전트 실행

```bash
claude-code plan
```

**프롬프트**:
```
Upgrade LiteLLM from v1.30.0 to v1.35.0:

1. Update backend/requirements.txt
2. Check breaking changes in LiteLLM release notes
3. Update config/litellm.yaml if API changes exist
4. Run backend tests (pytest tests/)
5. Update documentation (README.md, DEVELOP.md)
6. Create git branch "upgrade/litellm-v1.35"
7. Commit changes
8. Create PR with detailed changelog

Wait for my approval at each step.
```

#### Step 2: 에이전트 실행 및 검토

에이전트가 각 단계를 실행하고 결과를 보고합니다:

```
✅ Step 1: Updated backend/requirements.txt (litellm==1.35.0)
✅ Step 2: Breaking changes reviewed - none affecting our usage
✅ Step 3: config/litellm.yaml - no changes needed
✅ Step 4: All 47 tests passed
✅ Step 5: Updated README.md with new version
❓ Step 6: Ready to create branch. Approve? (yes/no)
```

**승인**: `yes`

```
✅ Step 6: Created branch upgrade/litellm-v1.35
✅ Step 7: Committed changes
❓ Step 8: Ready to push and create PR. Approve? (yes/no)
```

**승인**: `yes`

#### Step 3: PR 생성 및 CI 실행

에이전트가 PR을 생성하고 GitHub Actions가 자동 실행됩니다:

```yaml
# .github/workflows/pr-checks.yml
name: PR Checks

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest tests/ --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

#### Step 4: 인간 검토 및 승인

**검토자 체크리스트**:
- [ ] PR 설명 읽기
- [ ] 변경 파일 확인 (Files changed 탭)
- [ ] CI 결과 확인 (모든 체크 통과)
- [ ] Breaking changes 확인
- [ ] 테스트 커버리지 유지 확인

**승인**:
```bash
# GitHub UI에서 "Approve" 클릭
# 또는 gh CLI 사용:
gh pr review 123 --approve --body "LGTM! All checks passed."
```

#### Step 5: 자동 병합 (옵션)

`.github/workflows/auto-merge.yml`

```yaml
name: Auto Merge Approved PRs

on:
  pull_request_review:
    types: [submitted]

jobs:
  auto-merge:
    if: github.event.review.state == 'approved'
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - name: Auto merge
        uses: pascalgn/automerge-action@v0.15.6
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          MERGE_LABELS: "automated,approved"
          MERGE_METHOD: "squash"
```

---

## 8. 고급 기법: 병렬 에이전트 실행

### 8.1 여러 포크 동시 업그레이드

**시나리오**: Open-WebUI, Open Notebook, Perplexica를 동시에 체크

`.github/workflows/parallel-fork-sync.yml`

```yaml
name: Parallel Fork Sync

on:
  schedule:
    - cron: '0 5 * * 0'  # 매주 일요일
  workflow_dispatch:

jobs:
  sync-matrix:
    strategy:
      matrix:
        fork:
          - name: open-webui
            path: webui
            upstream: https://github.com/open-webui/open-webui.git
          - name: open-notebook
            path: open-notebook
            upstream: https://github.com/open-notebook/open-notebook.git
          - name: perplexica
            path: perplexica
            upstream: https://github.com/ItzCrazyKns/Perplexica.git

    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Sync ${{ matrix.fork.name }}
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          git remote add upstream-${{ matrix.fork.name }} ${{ matrix.fork.upstream }}
          git fetch upstream-${{ matrix.fork.name }}

          npx @anthropic-ai/claude-code run \
            --prompt "Cherry-pick security patches from upstream-${{ matrix.fork.name }} into ${{ matrix.fork.path }}/. Create PR with changelog." \
            --context "${{ matrix.fork.path }}/,CLAUDE.md"

      - name: Create PR
        uses: peter-evans/create-pull-request@v5
        with:
          branch: auto/sync-${{ matrix.fork.name }}
          title: "chore: Sync ${{ matrix.fork.name }} upstream"
          labels: ${{ matrix.fork.name }}, upstream-sync
```

### 8.2 Master-Clone 아키텍처

**마스터 에이전트**가 작업을 분석하고 **클론 에이전트**들에게 위임:

```python
# scripts/master_agent.py
import subprocess
import json

def master_agent(task: str):
    """마스터 에이전트: 작업 분석 및 위임"""

    # 1. 작업 분석
    subtasks = analyze_task(task)

    # 2. 각 하위 작업을 클론 에이전트에 위임
    results = []
    for subtask in subtasks:
        result = subprocess.run([
            "npx", "@anthropic-ai/claude-code", "run",
            "--prompt", subtask["prompt"],
            "--context", ",".join(subtask["context"]),
            "--output", f"results/{subtask['id']}.md"
        ], capture_output=True, text=True)

        results.append({
            "id": subtask["id"],
            "status": "success" if result.returncode == 0 else "failed",
            "output": result.stdout
        })

    # 3. 결과 통합
    create_master_pr(results)

def analyze_task(task: str) -> list:
    """작업을 하위 작업으로 분해"""
    # 예: "Upgrade all dependencies" → [Python, Node, Docker]
    if "upgrade" in task.lower() and "dependencies" in task.lower():
        return [
            {
                "id": "python-deps",
                "prompt": "Upgrade Python dependencies in backend/requirements.txt",
                "context": ["backend/requirements.txt", "backend/tests/"]
            },
            {
                "id": "node-deps",
                "prompt": "Upgrade Node dependencies in webui/package.json",
                "context": ["webui/package.json", "webui/package-lock.json"]
            },
            {
                "id": "docker-images",
                "prompt": "Upgrade Docker base images in all Dockerfiles",
                "context": ["*/Dockerfile", "docker-compose.yml"]
            }
        ]
    return []

if __name__ == "__main__":
    master_agent("Upgrade all dependencies and create separate PRs")
```

---

## 9. 모니터링 및 피드백 루프

### 9.1 에이전트 성공률 추적

**메트릭 수집**:
- PR 생성 성공률
- CI 통과율
- 인간 승인율
- 평균 리뷰 시간

`.github/workflows/agent-metrics.yml`

```yaml
name: Agent Metrics

on:
  pull_request:
    types: [closed]

jobs:
  collect-metrics:
    if: contains(github.event.pull_request.labels.*.name, 'automated')
    runs-on: ubuntu-latest
    steps:
      - name: Collect metrics
        run: |
          echo "PR #${{ github.event.pull_request.number }}" >> agent-metrics.log
          echo "Created: ${{ github.event.pull_request.created_at }}" >> agent-metrics.log
          echo "Merged: ${{ github.event.pull_request.merged_at }}" >> agent-metrics.log
          echo "Reviews: ${{ github.event.pull_request.reviews }}" >> agent-metrics.log

      - name: Send to analytics
        run: |
          curl -X POST https://analytics.example.com/agent-metrics \
            -H "Content-Type: application/json" \
            -d '{"pr": ${{ github.event.pull_request.number }}, "status": "merged"}'
```

### 9.2 실패 패턴 분석

**실패 로그를 CLAUDE.md에 반영**:

```bash
# 스크립트: scripts/update-claude-md.sh
#!/bin/bash

# 최근 10개 실패한 에이전트 작업 분석
gh pr list --label "automated" --state closed --json number,title,conclusion | \
  jq '.[] | select(.conclusion == "failure")' > failures.json

# Claude Code로 실패 패턴 분석
npx @anthropic-ai/claude-code run \
  --prompt "Analyze failures.json and suggest new guardrails for CLAUDE.md" \
  --context "failures.json,CLAUDE.md" \
  --output claude-md-updates.md

# CLAUDE.md 업데이트 제안을 PR로 생성
gh pr create \
  --title "docs: Update CLAUDE.md with new guardrails" \
  --body-file claude-md-updates.md \
  --label documentation
```

---

## 10. 보안 고려사항

### 10.1 API 키 관리

**절대 금지**:
- GitHub Actions secrets에 직접 하드코딩
- 로그에 키 노출
- 공개 저장소에 `.env` 커밋

**권장 방법**:
- GitHub Secrets 사용 (`ANTHROPIC_API_KEY`)
- 로컬 개발: `.env` + `.gitignore`
- 프로덕션: AWS Secrets Manager / HashiCorp Vault

### 10.2 코드 검토 필수 항목

**자동화된 PR도 반드시 검토**:
1. **의존성 변경**: Breaking changes 확인
2. **보안 패치**: CVE 세부사항 확인
3. **Docker 이미지**: 베이스 이미지 출처 확인
4. **설정 파일**: 민감 정보 노출 여부
5. **테스트 결과**: 실제 통과 여부 (가짜 통과 방지)

### 10.3 Rate Limiting

**에이전트 과다 사용 방지**:

```yaml
# .github/workflows/rate-limit.yml
name: Rate Limit Check

on:
  workflow_run:
    workflows: ["Auto*"]
    types: [requested]

jobs:
  check-limit:
    runs-on: ubuntu-latest
    steps:
      - name: Check API usage
        run: |
          CURRENT_HOUR=$(date +%Y-%m-%d-%H)
          COUNT=$(gh run list --created "$CURRENT_HOUR" --json conclusion | jq 'length')

          if [ "$COUNT" -gt 10 ]; then
            echo "ERROR: Rate limit exceeded (max 10 runs/hour)"
            exit 1
          fi
```

---

## 11. 트러블슈팅

### 11.1 에이전트가 PR 생성 실패

**증상**: 작업은 완료되었으나 PR이 생성되지 않음

**해결**:
1. GitHub 권한 확인 (`contents: write`, `pull-requests: write`)
2. 브랜치 이름 충돌 확인 (기존 브랜치 삭제 후 재시도)
3. 에이전트 로그 확인 (`--verbose` 플래그 사용)

### 11.2 테스트 실패로 인한 차단

**증상**: Pre-push hook에서 테스트 실패

**해결**:
1. 로컬에서 테스트 재실행: `pytest tests/ -v`
2. 실패 원인 분석 (로그 확인)
3. 에이전트에게 테스트 수정 요청:
   ```bash
   claude-code run --prompt "Fix failing tests in backend/tests/test_chat.py"
   ```

### 11.3 컨텍스트 창 초과

**증상**: "Context window exceeded" 오류

**해결**:
1. CLAUDE.md 간소화 (13KB 이하 유지)
2. `--context` 플래그로 필요한 파일만 지정
3. `/clear` + `/catchup` 사용하여 컨텍스트 재설정

---

## 12. 모범 사례 (Best Practices)

### 12.1 DO's ✅

- **명확한 작업 정의**: 에이전트에게 구체적인 목표와 성공 기준 제시
- **점진적 승인**: 복잡한 작업은 단계별로 승인
- **실패 기반 학습**: 실패 사례를 CLAUDE.md에 반영
- **PR 템플릿 사용**: 일관된 검토 프로세스 유지
- **병렬 실행**: 독립적 작업은 동시에 실행하여 속도 향상
- **모니터링**: 에이전트 성공률 추적 및 개선

### 12.2 DON'Ts ❌

- **main 브랜치 직접 수정 금지**: 항상 PR 워크플로우 사용
- **맹목적 승인 금지**: 자동화된 PR도 반드시 검토
- **컨텍스트 과부하 금지**: 불필요한 파일 포함하지 않기
- **테스트 생략 금지**: 모든 변경사항은 테스트 필수
- **문서 누락 금지**: 기능 변경 시 문서 업데이트
- **보안 경고 무시 금지**: 모든 취약점 즉시 대응

---

## 13. 로드맵

### 13.1 단기 (1-3개월)

- [ ] CLAUDE.md 작성 및 프로젝트 적용
- [ ] 기본 GitHub Actions 워크플로우 구축
  - [ ] Python 의존성 자동 업그레이드
  - [ ] 보안 패치 자동 적용
  - [ ] Docker 이미지 업데이트
- [ ] Pre-commit/Pre-push hooks 설정
- [ ] PR 템플릿 표준화

### 13.2 중기 (3-6개월)

- [ ] 포크 동기화 자동화 (Open-WebUI, Perplexica, Open Notebook)
- [ ] 병렬 에이전트 실행 구현
- [ ] 에이전트 메트릭 대시보드 구축
- [ ] 실패 패턴 자동 분석 및 CLAUDE.md 업데이트

### 13.3 장기 (6-12개월)

- [ ] Master-Clone 에이전트 아키텍처 도입
- [ ] 코드 리팩토링 자동화
- [ ] 성능 최적화 자동 제안
- [ ] 문서 자동 생성 (API docs, 아키텍처 다이어그램)
- [ ] A/B 테스트 자동 실행 및 분석

---

## 14. 참고 자료

### 14.1 공식 문서

- [Claude Code 공식 문서](https://docs.claude.com/claude-code)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)

### 14.2 커뮤니티 자료

- [Claude Code Cookbook](https://github.com/anthropics/claude-code-cookbook)
- [AI Agent Best Practices](https://news.hada.io/topic?id=24099)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)

### 14.3 프로젝트 문서

- [README.md](./README.md) — 프로젝트 개요
- [DEVELOP.md](./DEVELOP.md) — 개발 가이드
- [WHATWEDO.md](./WHATWEDO.md) — 프로젝트 목표

---

## 부록 A: 체크리스트

### A.1 프로젝트 초기 설정

- [ ] CLAUDE.md 작성 완료
- [ ] GitHub Actions 워크플로우 설정
- [ ] Pre-commit/Pre-push hooks 설치
- [ ] PR 템플릿 생성
- [ ] Branch protection rules 설정 (main 브랜치)

### A.2 워크플로우 검증

- [ ] 로컬에서 Claude Code 에이전트 실행 성공
- [ ] GitHub Actions에서 자동 PR 생성 성공
- [ ] CI/CD 파이프라인 통과 확인
- [ ] 인간 검토 프로세스 테스트
- [ ] Auto-merge 동작 확인 (옵션)

### A.3 정기 점검

- [ ] 월간: 에이전트 성공률 리뷰
- [ ] 분기별: CLAUDE.md 업데이트 (새로운 실패 패턴 반영)
- [ ] 연간: 워크플로우 전체 감사 및 개선

---

## 부록 B: 용어집

| 용어 | 설명 |
|------|------|
| **Agent** | 자율적으로 작업을 수행하는 AI 시스템 (Claude Code) |
| **CLAUDE.md** | 에이전트의 행동 규칙을 정의하는 프로젝트 설정 파일 |
| **Hook** | Git 이벤트 또는 워크플로우 단계에서 실행되는 스크립트 |
| **PR** | Pull Request — 코드 변경사항을 병합하기 위한 제안 |
| **CI/CD** | Continuous Integration/Deployment — 자동화된 테스트 및 배포 |
| **Master-Clone** | 마스터 에이전트가 작업을 분석하고 클론 에이전트가 실행하는 아키텍처 |
| **Context Window** | AI 모델이 한 번에 처리할 수 있는 텍스트 양 (토큰 단위) |

---

**문서 버전**: 1.0
**최종 업데이트**: 2025-01-04
**작성자**: AI Agent (Claude Code)

---

**이 문서는 AI 에이전트를 활용한 자동 업그레이드 워크플로우를 구축하기 위한 완전한 가이드입니다.**
모든 워크플로우는 **PR 검토 및 승인**을 통해 안전하게 관리되며,
**"Shoot and Forget" 철학**을 따라 에이전트에게 작업을 위임하되 최종 결과는 인간이 검토합니다.
