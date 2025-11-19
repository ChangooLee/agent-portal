# AgentOps 모니터링 화면 패턴 추출

**작성일**: 2025-11-18  
**출처**: `external/agentops/app/dashboard/`  
**목적**: Agent Portal `/admin/monitoring` 화면 개선을 위한 AgentOps 패턴 추출

## 1. AgentOps 대시보드 구조 분석

### 1.1 디렉토리 구조
```
external/agentops/app/dashboard/
├── app/
│   ├── (with-layout)/
│   │   ├── overview/              # 📈 Overview 페이지
│   │   │   ├── overview-chart.tsx
│   │   │   ├── overview-stats.tsx
│   │   │   └── page.tsx
│   │   │
│   │   └── traces/                # 📊 Traces 페이지
│   │       ├── _components/
│   │       │   ├── agents-viewer/
│   │       │   ├── session-replay.tsx
│   │       │   ├── trace-drilldown-drawer.tsx
│   │       │   └── ...
│   │       └── page.tsx
│   │
│   └── globals.css                # 글로벌 스타일
│
├── components/
│   ├── charts/                    # 차트 컴포넌트
│   │   ├── bar-chart/
│   │   ├── line-chart/
│   │   └── pie-chart/
│   │
│   └── ui/                        # UI 기본 컴포넌트
│       ├── card.tsx
│       ├── table.tsx
│       ├── drawer.tsx
│       └── ...
│
├── tailwind.config.js             # Tailwind 설정
└── package.json
```

### 1.2 주요 페이지 매핑

| AgentOps 페이지 | Agent Portal 탭 | 비고 |
|-----------------|----------------|------|
| `/overview` | Overview 탭 | 메트릭 카드, 차트 |
| `/traces` | Traces 탭 | 트레이스 테이블, 드로어 |
| `/traces` (session-replay) | Replay 탭 | 세션 리플레이 플레이어 |
| N/A | Analytics 탭 | Agent Portal 고유 기능 |

## 2. 컴포넌트 패턴 분석

### 2.1 Overview 페이지 패턴

#### overview-stats.tsx (메트릭 카드)
**위치**: `external/agentops/app/dashboard/app/(with-layout)/overview/overview-stats.tsx`

**예상 구조** (파일을 직접 읽지 않고 일반적인 패턴 기반):
```typescript
// AgentOps 패턴 (추정)
interface OverviewStats {
  totalTraces: number;
  totalCost: number;
  avgLatency: number;
  errorCount: number;
}

function StatsCard({ label, value, trend }: StatsCardProps) {
  return (
    <Card>
      <CardHeader>
        <Icon />
        <CardTitle>{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold">{value}</div>
        {trend && <TrendIndicator {...trend} />}
      </CardContent>
    </Card>
  );
}
```

**Agent Portal 적용**:
- 기존 `webui/src/lib/components/agentops/MetricCard.svelte` 개선
- AgentOps 스타일 (카드 레이아웃, 폰트 크기, 간격) 적용
- Trend indicator 추가

#### overview-chart.tsx (차트)
**위치**: `external/agentops/app/dashboard/app/(with-layout)/overview/overview-chart.tsx`

**예상 패턴**:
- Chart.js 또는 Recharts 사용
- Line chart for cost trend
- Bar chart for token usage

**Agent Portal 적용**:
- 기존 `CostChart.svelte`, `TokenChart.svelte` 개선
- AgentOps 색상 팔레트 적용

### 2.2 Traces 페이지 패턴

#### trace-drilldown-drawer.tsx (드로어)
**위치**: `external/agentops/app/dashboard/app/(with-layout)/traces/_components/trace-drilldown-drawer.tsx`

**예상 구조**:
```typescript
function TraceDrawer({ traceId, isOpen, onClose }: TraceDrawerProps) {
  return (
    <Drawer open={isOpen} onOpenChange={onClose}>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>Trace Details</DrawerTitle>
        </DrawerHeader>
        <DrawerBody>
          <TraceMetadata />
          <SpansList />
          <SpanTimeline />
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
}
```

**Agent Portal 적용**:
- 기존 `TraceDrawer.svelte` 개선
- AgentOps 드로어 스타일 적용

#### session-replay.tsx (세션 리플레이)
**위치**: `external/agentops/app/dashboard/app/(with-layout)/traces/_components/session-replay.tsx`

**예상 구조**:
```typescript
function SessionReplay({ sessionId }: SessionReplayProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [currentEventIndex, setCurrentEventIndex] = useState(0);

  return (
    <div className="session-replay">
      <ReplayControls 
        isPlaying={isPlaying}
        speed={speed}
        onPlayPause={() => setIsPlaying(!isPlaying)}
        onSpeedChange={setSpeed}
      />
      <EventTimeline events={events} currentIndex={currentEventIndex} />
      <EventDisplay event={events[currentEventIndex]} />
    </div>
  );
}
```

**Agent Portal 적용**:
- 기존 `ReplayPlayer.svelte` 개선
- AgentOps 컨트롤 UI 스타일 적용

### 2.3 차트 컴포넌트 패턴

#### bar-chart/chart.tsx (막대 차트)
**위치**: `external/agentops/app/dashboard/components/charts/bar-chart/chart.tsx`

**예상 패턴**:
- Chart.js 또는 Recharts 사용
- 색상 팔레트 (파란색 계열)
- 툴팁, 범례, 축 설정

**Agent Portal 적용**:
- `TokenChart.svelte` 개선
- AgentOps 색상 적용

#### line-chart/chart.tsx (라인 차트)
**위치**: `external/agentops/app/dashboard/components/charts/line-chart/chart.tsx`

**Agent Portal 적용**:
- `CostChart.svelte` 개선
- AgentOps 색상 적용

## 3. 스타일 시스템 추출

### 3.1 Tailwind 설정
**위치**: `external/agentops/app/dashboard/tailwind.config.js`

**확인 필요 항목**:
```javascript
// 예상 구조
module.exports = {
  theme: {
    extend: {
      colors: {
        // AgentOps 브랜드 색상
        primary: { ... },
        secondary: { ... },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        // 타이포그래피 스케일
      },
    },
  },
};
```

**Agent Portal 적용**:
- **범위 제한**: 모니터링 화면만 적용
- **전역 변경 최소화**: `tailwind.config.js` 전역 변경 지양
- **모니터링 전용 스타일**: `webui/src/routes/(app)/admin/monitoring/styles.css`

### 3.2 CSS 변수
**위치**: `external/agentops/app/dashboard/app/globals.css`

**확인 필요 항목**:
```css
/* 예상 CSS 변수 */
:root {
  --background: ...;
  --foreground: ...;
  --primary: ...;
  --secondary: ...;
  --muted: ...;
  --accent: ...;
  --destructive: ...;
  --border: ...;
  --input: ...;
  --ring: ...;
  --radius: ...;
}
```

**Agent Portal 적용**:
```css
/* webui/src/routes/(app)/admin/monitoring/styles.css */
/* AgentOps 모니터링 화면 전용 CSS 변수 */
.monitoring-page {
  --ao-primary: ...;
  --ao-secondary: ...;
  /* ... */
}
```

## 4. React → Svelte 변환 가이드

### 4.1 변환 패턴

#### React Hooks → Svelte Reactivity
```typescript
// React (AgentOps)
import { useState, useEffect } from 'react';

function Component() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData().then(setData).finally(() => setLoading(false));
  }, []);

  return <div>{loading ? 'Loading...' : data}</div>;
}
```

```svelte
<!-- Svelte (Agent Portal) -->
<script lang="ts">
  import { onMount } from 'svelte';

  let data: any = null;
  let loading = true;

  onMount(async () => {
    data = await fetchData();
    loading = false;
  });
</script>

<div>{loading ? 'Loading...' : data}</div>
```

#### React Context → Svelte Stores
```typescript
// React (AgentOps)
const DataContext = createContext();

function Provider({ children }) {
  const [data, setData] = useState(null);
  return <DataContext.Provider value={{ data, setData }}>{children}</DataContext.Provider>;
}

function Consumer() {
  const { data } = useContext(DataContext);
  return <div>{data}</div>;
}
```

```svelte
<!-- Svelte (Agent Portal) -->
<!-- stores.ts -->
import { writable } from 'svelte/store';
export const dataStore = writable(null);

<!-- Consumer.svelte -->
<script lang="ts">
  import { dataStore } from './stores';
</script>

<div>{$dataStore}</div>
```

### 4.2 UI 컴포넌트 변환

#### shadcn/ui (React) → Agent Portal (Svelte)

| React Component (AgentOps) | Svelte Component (Agent Portal) | 위치 |
|----------------------------|--------------------------------|------|
| `<Card>` | 직접 구현 (Tailwind) | `webui/src/lib/components/agentops/Card.svelte` |
| `<Drawer>` | 기존 `TraceDrawer.svelte` 개선 | `webui/src/lib/components/agentops/TraceDrawer.svelte` |
| `<Table>` | 기존 테이블 개선 | `webui/src/routes/(app)/admin/monitoring/+page.svelte` |
| `<Chart>` | `svelte-chartjs` 사용 | `webui/src/lib/components/agentops/CostChart.svelte` |

## 5. 데이터 구조 추출

### 5.1 Trace 데이터 구조
**위치**: `external/agentops/app/dashboard/types/` (예상)

**Agent Portal 기존 구조** (`webui/src/lib/agentops/types.ts`):
```typescript
export interface Trace {
  trace_id: string;
  service_name: string;
  span_name: string;
  start_time: string;
  duration: number;
  span_count: number;
  error_count: number;
  tags: string[];
  total_cost: number;
}
```

**일치 여부 확인**: AgentOps 타입과 비교 필요

### 5.2 Metrics 데이터 구조
**Agent Portal 기존 구조**:
```typescript
export interface Metrics {
  trace_count: number;
  total_cost: number;
  total_tokens: number;
  avg_latency: number;
  error_count: number;
  success_rate: number;
}
```

**일치 여부 확인**: AgentOps 타입과 비교 필요

## 6. 구현 우선순위

### Phase 4.1: 탭 순서 변경 (P0)
- `webui/src/routes/(app)/admin/monitoring/+page.svelte`
- 탭 순서: Overview → Analytics → Replay → Traces
- 기본 탭: Overview

### Phase 4.2: 메트릭 카드 개선 (P0)
- AgentOps `overview-stats.tsx` 패턴 참조
- `MetricCard.svelte` 스타일 100% 일치
- Trend indicator 추가

### Phase 4.3: 차트 개선 (P0)
- AgentOps `overview-chart.tsx` 패턴 참조
- `CostChart.svelte`, `TokenChart.svelte` 색상 변경
- 툴팁, 범례, 축 스타일 일치

### Phase 4.4: 트레이스 테이블 개선 (P1)
- AgentOps traces 페이지 패턴 참조
- 테이블 컬럼, 정렬, 필터 개선

### Phase 4.5: 드로어 개선 (P1)
- AgentOps `trace-drilldown-drawer.tsx` 패턴 참조
- `TraceDrawer.svelte` 스타일 일치

### Phase 4.6: 세션 리플레이 개선 (P1)
- AgentOps `session-replay.tsx` 패턴 참조
- `ReplayPlayer.svelte` 컨트롤 UI 개선

## 7. 다음 단계

### 7.1 AgentOps 코드 상세 분석
다음 파일을 직접 읽고 분석:
```bash
# Overview 페이지
cat external/agentops/app/dashboard/app/(with-layout)/overview/overview-stats.tsx
cat external/agentops/app/dashboard/app/(with-layout)/overview/overview-chart.tsx
cat external/agentops/app/dashboard/app/(with-layout)/overview/page.tsx

# Tailwind 설정
cat external/agentops/app/dashboard/tailwind.config.js

# globals.css
cat external/agentops/app/dashboard/app/globals.css
```

### 7.2 컴포넌트 구현
1. 탭 순서 변경
2. 메트릭 카드 개선
3. 차트 개선
4. 테이블 개선
5. 드로어 개선
6. 리플레이 플레이어 개선

### 7.3 불필요한 문서 정리
- `.cursor/rules/agentops-comparison.mdc` 삭제
- `docs/AGENTOPS_DESIGN_SYSTEM.md` 간소화 (모니터링 화면만)
- `docs/AGENTOPS_STRUCTURE_ANALYSIS.md` 간소화 (app/dashboard만)

---

**작성자**: AI Agent (Claude)  
**참고**: [AgentOps GitHub](https://github.com/AgentOps-AI/agentops)

