# AgentOps 서브모듈 관리 가이드

**작성일**: 2025-11-18  
**목적**: [AgentOps GitHub 저장소](https://github.com/AgentOps-AI/agentops)를 서브모듈로 관리하여 모니터링 화면 코드를 재활용

## 1. 서브모듈 개요

### 1.1 위치
```
agent-portal/
└── external/
    └── agentops/  # Git 서브모듈
```

### 1.2 용도
- **모니터링 화면 참조**: `/admin/monitoring` 화면의 UI/UX 개선을 위한 참조 코드
- **컴포넌트 패턴 재사용**: React 컴포넌트를 Svelte로 변환하여 재사용
- **디자인 시스템 참조**: 색상, 타이포그래피, 레이아웃 패턴

### 1.3 라이선스
- **AgentOps 라이선스**: [MIT License](https://github.com/AgentOps-AI/agentops/blob/main/LICENSE)
- **사용 가능 범위**: 상업적 사용, 수정, 배포 가능
- **의무 사항**: 원본 저작권 고지 및 라이선스 명시

## 2. 서브모듈 관리

### 2.1 초기 클론 (이미 완료)
```bash
# 서브모듈 추가
git submodule add https://github.com/AgentOps-AI/agentops.git external/agentops

# 서브모듈 초기화
git submodule update --init --recursive
```

### 2.2 서브모듈 업데이트
```bash
# AgentOps 저장소의 최신 변경사항 가져오기
cd external/agentops
git fetch origin
git checkout main
git pull origin main

# 상위 저장소로 돌아가서 서브모듈 참조 업데이트
cd ../..
git add external/agentops
git commit -m "chore: update AgentOps submodule to latest version"
```

### 2.3 특정 버전으로 고정
```bash
# 특정 커밋으로 체크아웃 (안정성을 위해 권장)
cd external/agentops
git checkout <commit-hash>

# 상위 저장소에서 변경사항 커밋
cd ../..
git add external/agentops
git commit -m "chore: pin AgentOps submodule to v<version>"
```

### 2.4 서브모듈 포함하여 클론 (신규 팀원용)
```bash
# 저장소 클론 시 서브모듈 자동 포함
git clone --recurse-submodules https://github.com/<your-org>/agent-portal.git

# 또는 클론 후 서브모듈 초기화
git clone https://github.com/<your-org>/agent-portal.git
cd agent-portal
git submodule update --init --recursive
```

## 3. 코드 재활용 가이드라인

### 3.1 참조 대상 디렉토리
```
external/agentops/
├── app/                    # Next.js/React 웹 대시보드 (주요 참조 대상)
│   ├── components/         # React 컴포넌트
│   │   ├── dashboard/      # 메트릭 카드, 차트
│   │   ├── traces/         # 트레이스 테이블, 드로어
│   │   ├── replay/         # 세션 리플레이
│   │   └── analytics/      # 분석 도구
│   ├── lib/                # API 클라이언트, 유틸리티
│   ├── styles/             # CSS, Tailwind 설정
│   └── tailwind.config.js  # Tailwind 설정
├── agentops/               # Python SDK (백엔드 참조용)
└── docs/                   # 문서
```

### 3.2 React → Svelte 변환 패턴

#### React 컴포넌트 (AgentOps)
```typescript
// external/agentops/app/components/dashboard/MetricCard.tsx
interface MetricCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
}

export function MetricCard({ title, value, icon, trend }: MetricCardProps) {
  return (
    <div className="bg-white rounded-lg p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-blue-50 rounded-lg">{icon}</div>
        <span className="text-sm font-medium text-gray-600">{title}</span>
      </div>
      <div className="text-3xl font-bold text-gray-900">{value}</div>
      {trend && (
        <div className="mt-2 flex items-center gap-1 text-sm">
          <span className={trend.direction === 'up' ? 'text-green-600' : 'text-red-600'}>
            {trend.direction === 'up' ? '↑' : '↓'} {trend.value}%
          </span>
        </div>
      )}
    </div>
  );
}
```

#### Svelte 변환 (Agent Portal)
```svelte
<!-- webui/src/lib/components/agentops/MetricCard.svelte -->
<script lang="ts">
  export let title: string;
  export let value: number | string;
  export let icon: any; // Svelte component
  export let trend: { value: number; direction: 'up' | 'down' } | null = null;
</script>

<div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
  <div class="flex items-center gap-3 mb-2">
    <div class="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
      <svelte:component this={icon} class="w-5 h-5 text-blue-600" />
    </div>
    <span class="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</span>
  </div>
  <div class="text-3xl font-bold text-gray-900 dark:text-gray-100">{value}</div>
  {#if trend}
    <div class="mt-2 flex items-center gap-1 text-sm">
      <span class="{trend.direction === 'up' ? 'text-green-600' : 'text-red-600'}">
        {trend.direction === 'up' ? '↑' : '↓'} {trend.value}%
      </span>
    </div>
  {/if}
</div>
```

### 3.3 스타일 추출 패턴

#### AgentOps Tailwind 설정 참조
```bash
# AgentOps Tailwind 설정 확인
cat external/agentops/app/tailwind.config.js

# 모니터링 화면에만 적용할 색상 추출
# webui/src/routes/(app)/admin/monitoring/styles.css에 적용
```

#### 모니터링 화면 전용 스타일 적용
```css
/* webui/src/routes/(app)/admin/monitoring/styles.css */
/* AgentOps 모니터링 화면 전용 스타일 */
/* 다른 화면에는 영향 없음 */

.monitoring-metric-card {
  @apply bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm;
}

.monitoring-chart-container {
  @apply bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm;
}
```

### 3.4 데이터 구조 참조
```bash
# AgentOps 데이터 타입 확인
cat external/agentops/app/lib/types/trace.ts
cat external/agentops/app/lib/types/metrics.ts

# Agent Portal 타입으로 변환
# webui/src/lib/agentops/types.ts에서 호환 가능한 인터페이스 정의
```

## 4. 주의사항

### 4.1 범위 제한
- **적용 대상**: 모니터링 화면(`/admin/monitoring`)만
- **제외 대상**: Today, Agent, Chat 등 다른 화면
- **전역 스타일 변경 최소화**: `tailwind.config.js` 전역 변경 지양

### 4.2 라이선스 준수
- AgentOps 코드를 참조할 때 주석에 출처 명시:
  ```typescript
  // Adapted from: https://github.com/AgentOps-AI/agentops
  // License: MIT
  ```

### 4.3 서브모듈 커밋 금지
- `external/agentops/` 내부 파일은 직접 수정하지 않음
- 필요한 경우 Agent Portal의 `webui/src/` 디렉토리에 복사하여 수정

### 4.4 업데이트 주기
- **권장**: 월 1회 AgentOps 저장소 확인
- **방법**: Release Notes 확인 후 필요한 변경사항 반영
- **안정성**: 특정 커밋으로 고정하여 예기치 않은 변경 방지

## 5. 트러블슈팅

### 5.1 서브모듈이 비어있음
```bash
# 서브모듈 초기화 및 업데이트
git submodule update --init --recursive
```

### 5.2 서브모듈 충돌
```bash
# 서브모듈 제거 후 재추가
git submodule deinit external/agentops
git rm external/agentops
rm -rf .git/modules/external/agentops
git submodule add https://github.com/AgentOps-AI/agentops.git external/agentops
git submodule update --init --recursive
```

### 5.3 서브모듈 브랜치 변경
```bash
cd external/agentops
git checkout <branch-name>
git pull origin <branch-name>
cd ../..
git add external/agentops
git commit -m "chore: switch AgentOps submodule to <branch-name>"
```

## 6. 참고 자료

- [AgentOps GitHub](https://github.com/AgentOps-AI/agentops)
- [AgentOps Documentation](https://docs.agentops.ai/)
- [Git Submodules Documentation](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [MIT License](https://opensource.org/licenses/MIT)

---

**작성자**: AI Agent (Claude)  
**다음 문서**: `docs/AGENTOPS_MONITORING_PATTERNS.md`

