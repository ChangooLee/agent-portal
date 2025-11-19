# AgentOps 통합 학습 내용

**작성일**: 2025-11-18  
**목적**: AgentOps 서브모듈 추가 및 모니터링 화면 개선 과정에서 학습한 내용

## 1. 서브모듈 추가 과정

### 성공 사례

**작업**: AgentOps 저장소를 Git 서브모듈로 추가

**명령어**:
```bash
git submodule add https://github.com/AgentOps-AI/agentops.git external/agentops
git submodule update --init --recursive
```

**결과**: ✅ 성공
- `external/agentops/` 디렉토리에 AgentOps 코드 클론
- `.gitmodules` 파일 자동 생성
- `.gitignore`에 빌드 파일 제외 규칙 추가

**학습**:
- Git 서브모듈은 외부 프로젝트를 독립적으로 관리하면서도 참조 가능
- 빌드 파일(`node_modules/`, `app/.next/`, `app/out/`)은 반드시 `.gitignore`에 추가
- 서브모듈 커밋 해시는 상위 저장소에 기록되어 버전 고정 가능

## 2. 범위 제한 전략

### 핵심 원칙

**문제**: 초기 계획은 전체 프로젝트를 AgentOps 디자인으로 100% 복제

**피드백**: ❌ 이거 싫어함 (사용자 요청: 모니터링 화면만 개선)

**해결**:
- **개선 대상**: `/admin/monitoring` 페이지만
- **유지 대상**: Today, Agent, Chat 등 기존 Glassmorphism 디자인
- **전역 스타일**: `tailwind.config.js` 전역 변경 최소화
- **모니터링 전용**: 색상, 폰트, 레이아웃은 모니터링 화면에만 적용

**학습**:
- 대규모 디자인 개편은 범위를 명확히 제한해야 함
- 전역 스타일 변경은 다른 화면에 영향을 미칠 수 있음
- 특정 화면만 개선할 때는 scoped CSS 또는 인라인 스타일 사용

## 3. React → Svelte 변환 패턴

### React Hooks → Svelte Reactivity

**React (AgentOps)**:
```typescript
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

**Svelte (Agent Portal)**:
```svelte
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

**학습**:
- Svelte는 `useState` 대신 `let` 변수로 상태 관리
- `useEffect` 대신 `onMount`, `onDestroy` 생명주기 함수 사용
- Svelte의 반응성은 변수 재할당으로 자동 업데이트 (`data = ...`)

### React Context → Svelte Stores

**React (AgentOps)**:
```typescript
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

**Svelte (Agent Portal)**:
```typescript
// stores.ts
import { writable } from 'svelte/store';
export const dataStore = writable(null);

// Consumer.svelte
<script lang="ts">
  import { dataStore } from './stores';
</script>

<div>{$dataStore}</div>
```

**학습**:
- Svelte Stores는 React Context보다 간결
- `$` 접두사로 store 값 자동 구독
- `writable`, `readable`, `derived` 세 가지 타입

## 4. 탭 순서 변경

### 작업 내용

**변경 전**: `Traces → Overview → Replay → Analytics`  
**변경 후**: `Overview → Analytics → Replay → Traces`

**이유**: AgentOps 대시보드와 동일한 순서로 변경

**학습**:
- 탭 순서는 사용자 경험에 영향
- Overview가 첫 번째 탭일 때 메인 화면으로 인식됨
- 기본 `activeTab` 값도 `'overview'`로 설정

## 5. WebSocket 실시간 업데이트

### 문제 해결

**증상**: WebSocket 연결 시 `/api/v1/chats` API가 무한 반복 호출

**근본 원인**: `Loader.svelte`의 `setInterval`이 계속 `visible` 이벤트 발생

**해결**:
- `Loader.svelte`에서 `setInterval` 제거
- `IntersectionObserver`가 한 번만 이벤트 발생하도록 수정
- 500ms 후 재관찰하여 다음 배치 로딩 지원

**학습**:
- WebSocket 문제는 다른 컴포넌트의 부작용일 수 있음
- 무한 루프는 이벤트 핸들러를 신중히 확인
- `IntersectionObserver`는 한 번만 트리거하도록 설계

## 6. 문서 정리

### 삭제된 문서

1. `.cursor/rules/agentops-comparison.mdc` - 전체 디자인 시스템 복제 (불필요)
2. `docs/AGENTOPS_DESIGN_SYSTEM.md` - 전체 디자인 시스템 추출 (중복)
3. `docs/AGENTOPS_STRUCTURE_ANALYSIS.md` - 저장소 전체 구조 (과도)

### 유지된 문서

1. `docs/AGENTOPS_SUBMODULE.md` - 서브모듈 관리 가이드
2. `docs/AGENTOPS_MONITORING_PATTERNS.md` - 모니터링 화면 패턴 (모니터링 전용)
3. `docs/AGENTOPS_LAYOUT_COMPARISON.md` - 4개 탭 비교
4. `docs/AGENTOPS_GAP_ANALYSIS.md` - 기능 갭 분석 (범위 업데이트)

**학습**:
- 문서는 프로젝트 범위에 맞게 유지
- 중복 문서는 혼란을 야기하므로 삭제
- 명확한 범위 설정이 중요

## 7. 다음 단계

### 즉시 수행 (P0)

1. AgentOps 코드 상세 분석:
   ```bash
   cat external/agentops/app/dashboard/app/(with-layout)/overview/overview-stats.tsx
   cat external/agentops/app/dashboard/app/(with-layout)/overview/overview-chart.tsx
   cat external/agentops/app/dashboard/tailwind.config.js
   ```

2. 메트릭 카드 스타일 개선:
   - AgentOps 패턴 참조
   - 아이콘, 색상, 간격 100% 일치

3. 차트 색상 변경:
   - `CostChart.svelte`, `TokenChart.svelte`
   - AgentOps 색상 팔레트 적용

### 1주 내 수행 (P1)

1. Agent Flow Graph 실제 데이터 연동
2. Trace Table 정렬 기능 완성
3. Filter Panel 모든 필터 완성
4. Export CSV/JSON 백엔드 구현

### 추후 개선 (P2)

1. 추가 분석 도구 (Cost Breakdown 등)
2. PDF Export 백엔드 구현
3. Share 기능 완전 구현
4. 모바일 최적화

## 8. 피해야 할 실수

### ❌ 절대 하지 말 것

1. **전역 스타일 변경**: `tailwind.config.js` 전역 변경은 다른 화면에 영향
2. **서브모듈 직접 수정**: `external/agentops/` 내부 파일은 수정하지 않음
3. **범위 초과**: 모니터링 화면 외 다른 화면 디자인 변경 금지

### ✅ 권장 사항

1. **모니터링 전용 스타일**: `webui/src/routes/(app)/admin/monitoring/styles.css` 사용
2. **서브모듈 업데이트**: 월 1회 AgentOps 저장소 확인
3. **라이선스 준수**: AgentOps MIT License 명시

---

**작성자**: AI Agent (Claude)  
**참고**: [AgentOps GitHub](https://github.com/AgentOps-AI/agentops)

