# SvelteKit Navigation Best Practices

## 2025-11-19: 새 채팅 버튼 새로고침 문제 해결

### 문제 증상

**사용자 피드백**: "사이드바의 새 채팅 누를 때 항상 새로고침 되는 이유가 뭐야?"

**근본 원인**:
- `webui/src/lib/components/layout/TopNavbar.svelte` (Line 38)
- `initNewChat()` 함수에서 `window.location.href = '/'` 사용
- 이 방식은 브라우저의 전체 페이지 새로고침을 유발

**문제점**:
- 전체 페이지 새로고침 → UX 저하
- JavaScript 상태 초기화 → 불필요한 데이터 재로딩
- 네트워크 요청 증가 → 성능 저하
- SvelteKit의 클라이언트 사이드 라우팅 이점 상실

### 해결 방법

**File**: `webui/src/lib/components/layout/TopNavbar.svelte`

**수정 전**:
```typescript
const initNewChat = () => {
    chatId.set('');
    window.location.href = '/'; // ❌ 전체 페이지 새로고침
};
```

**수정 후**:
```typescript
import { goto } from '$app/navigation'; // ✅ SvelteKit 네비게이션 import

const initNewChat = async () => {
    chatId.set('');
    await goto('/', { 
        replaceState: false,  // 히스토리에 추가
        noScroll: false,      // 페이지 상단으로 스크롤
        keepFocus: false,     // 포커스 초기화
        invalidateAll: true   // 모든 load 함수 재실행
    }); // ✅ SPA 네비게이션
};
```

**변경 내용**:
1. `import { goto } from '$app/navigation'` 추가 (Line 12)
2. `initNewChat()` 함수를 `async` 함수로 변경
3. `window.location.href = '/'` → `await goto('/', {...})` 변경

### SvelteKit Navigation 옵션 설명

**`goto(url, options)`**:

```typescript
interface GotoOptions {
    replaceState?: boolean;  // true: history 교체, false: history 추가 (기본값)
    noScroll?: boolean;      // true: 스크롤 유지, false: 페이지 상단으로 (기본값)
    keepFocus?: boolean;     // true: 포커스 유지, false: 포커스 초기화 (기본값)
    invalidateAll?: boolean; // true: 모든 load 재실행, false: 캐시 사용 (기본값)
    state?: any;             // 네비게이션 상태 전달 ($page.state로 접근)
}
```

### 사용 사례별 권장 옵션

#### 1. 새 채팅 시작 (현재 케이스)
```typescript
await goto('/', { 
    replaceState: false,  // 히스토리에 추가 (뒤로가기 가능)
    noScroll: false,      // 페이지 상단으로
    keepFocus: false,     // 포커스 초기화
    invalidateAll: true   // 데이터 새로고침
});
```

#### 2. 탭 전환 (같은 페이지 내)
```typescript
await goto('/admin/monitoring?tab=analytics', {
    replaceState: true,   // 히스토리 교체 (뒤로가기 시 이전 탭으로 안 감)
    noScroll: true,       // 스크롤 위치 유지
    keepFocus: true,      // 포커스 유지
    invalidateAll: false  // 캐시 사용 (빠른 전환)
});
```

#### 3. 로그아웃/리다이렉트
```typescript
await goto('/login', {
    replaceState: true,   // 히스토리 교체 (뒤로가기로 인증 페이지 접근 방지)
    noScroll: false,      // 페이지 상단으로
    keepFocus: false,     // 포커스 초기화
    invalidateAll: true   // 모든 데이터 재로딩
});
```

#### 4. 모달 닫기 후 URL 정리
```typescript
await goto('/dashboard', {
    replaceState: true,   // 히스토리 교체 (모달 URL 히스토리에 남기지 않음)
    noScroll: true,       // 스크롤 위치 유지
    keepFocus: true,      // 포커스 유지
    invalidateAll: false  // 캐시 사용
});
```

### 핵심 원칙

#### ✅ SvelteKit에서는 항상 `goto()` 사용

**권장**:
```typescript
import { goto } from '$app/navigation';

// SPA 네비게이션
await goto('/path');
```

**금지**:
```typescript
// ❌ 전체 페이지 새로고침
window.location.href = '/path';

// ❌ 브라우저 API 직접 사용
window.location.replace('/path');
window.location.assign('/path');
```

#### ⚠️ 예외: 외부 URL로 이동 시

**외부 URL**은 `window.location.href` 사용:
```typescript
// ✅ 외부 사이트로 이동
window.location.href = 'https://example.com';

// ✅ 또는
window.open('https://example.com', '_blank');
```

### Sidebar.svelte의 "새 채팅" 버튼

**File**: `webui/src/lib/components/layout/Sidebar.svelte` (Line 623-633)

**현재 구현**:
```typescript
on:click={async () => {
    selectedChatId = null;
    await goto('/'); // ✅ 이미 SvelteKit goto() 사용
    const newChatButton = document.getElementById('new-chat-button');
    setTimeout(() => {
        newChatButton?.click(); // TopNavbar의 initNewChat() 호출
        if ($mobile) {
            showSidebar.set(false);
        }
    }, 0);
}}
```

**동작 흐름**:
1. Sidebar "새 채팅" 클릭
2. `goto('/')` → SPA 네비게이션 (새로고침 없음) ✅
3. TopNavbar의 `new-chat-button` 클릭
4. `initNewChat()` 호출 → ~~`window.location.href = '/'`~~ (수정 전 새로고침 발생 ❌)
5. `initNewChat()` 호출 → `goto('/')` (수정 후 새로고침 없음 ✅)

**결과**: 이제 새 채팅 버튼 클릭 시 새로고침 없이 부드러운 네비게이션 동작!

### 관련 학습

#### history.pushState vs SvelteKit goto

**SvelteKit에서 `history.pushState` 사용 금지**:
```typescript
// ❌ SvelteKit 라우터와 충돌
history.pushState({}, '', '/path');
history.replaceState({}, '', '/path');

// ✅ SvelteKit goto 사용
import { goto } from '$app/navigation';
await goto('/path');
```

**경고 메시지**:
```
Avoid using `history.pushState(...)` and `history.replaceState(...)` 
as these will conflict with SvelteKit's router. 
Use the `pushState` and `replaceState` imports from `$app/navigation` instead.
```

#### $app/navigation API

**SvelteKit 제공 네비게이션 함수**:
- `goto(url, options)` — 프로그래매틱 네비게이션
- `beforeNavigate(callback)` — 네비게이션 전 콜백
- `afterNavigate(callback)` — 네비게이션 후 콜백
- `pushState(url, state)` — history.pushState 대체
- `replaceState(url, state)` — history.replaceState 대체

**예시**:
```typescript
import { goto, beforeNavigate, afterNavigate } from '$app/navigation';

beforeNavigate(({ from, to, cancel }) => {
    if (hasUnsavedChanges) {
        if (!confirm('Unsaved changes. Continue?')) {
            cancel(); // 네비게이션 취소
        }
    }
});

afterNavigate(({ from, to }) => {
    console.log(`Navigated from ${from?.url.pathname} to ${to?.url.pathname}`);
});
```

### 테스트 방법

1. **브라우저 하드 새고침** (필수!)
   ```
   Mac: Cmd + Shift + R
   ```

2. **확인 항목**:
   - ✅ 사이드바 "새 채팅" 클릭 시 새로고침 없음
   - ✅ TopNavbar "새 채팅" 클릭 시 새로고침 없음
   - ✅ 부드러운 페이지 전환 애니메이션
   - ✅ 브라우저 콘솔에 에러 없음
   - ✅ 뒤로가기/앞으로가기 정상 동작

3. **네트워크 탭 확인**:
   - ❌ 새로고침 시: `index.html` 재요청
   - ✅ SPA 네비게이션: API 요청만 발생

### 예방 체크리스트

#### 네비게이션 구현 시
- [ ] `window.location.href` 대신 `goto()` 사용
- [ ] `goto()` 옵션 명시 (명확한 의도 표현)
- [ ] `async` 함수로 구현 (`await goto()`)
- [ ] 외부 URL만 `window.location.href` 허용
- [ ] `history.pushState/replaceState` 사용 금지
- [ ] 브라우저 네트워크 탭에서 새로고침 확인

#### SPA 네비게이션 검증
- [ ] 페이지 전환 시 새로고침 없음
- [ ] 브라우저 히스토리 정상 동작
- [ ] 상태 유지 확인 (스크롤, 포커스 등)
- [ ] 로딩 인디케이터 표시 (필요 시)

### 참고 자료

- [SvelteKit Navigation](https://kit.svelte.dev/docs/modules#$app-navigation)
- [SvelteKit Routing](https://kit.svelte.dev/docs/routing)
- [SvelteKit goto API](https://kit.svelte.dev/docs/modules#$app-navigation-goto)
- `.cursor/rules/ui-development.mdc`: UI 개발 규칙

---

**마지막 업데이트**: 2025-11-19  
**관련 파일**: 
- `webui/src/lib/components/layout/TopNavbar.svelte`
- `webui/src/lib/components/layout/Sidebar.svelte`

