# Chat 화면 레이아웃 수정 (입력창 하단 고정)

## 날짜
2025-11-19

## 문제 상황

### 증상
- 채팅 화면에서 메시지 입력창이 화면 하단에 고정되지 않음
- 입력창이 화면 아래로 가려져서 사용자가 메시지를 입력하기 어려움

### 근본 원인

**레이아웃 구조 문제**:
```html
<!-- 수정 전 (잘못된 구조) -->
<div class="flex flex-col flex-auto">  <!-- flex-auto로 자식이 전체 높이 차지 -->
  <div class="overflow-auto h-0">  <!-- h-0으로 높이 고정 불가 -->
    <Messages />
  </div>
  <div class="pb-[1rem]">  <!-- 하단 고정 안됨 -->
    <MessageInput />
  </div>
</div>
```

**문제점**:
1. 부모 컨테이너가 `flex-auto`로 설정되어 자식이 전체 높이를 차지하려고 함
2. 메시지 영역이 `h-0`로 설정되어 스크롤이 제대로 작동하지 않음
3. 입력 영역이 `flex-shrink-0` 없이 하단에 고정되지 않음

## 해결 방법

### 문제의 근본 원인

**상위 레이아웃 구조**:
```html
<!-- +layout.svelte -->
<div class="flex-1 flex flex-col h-screen max-h-screen overflow-y-auto">  ❌
  <TopNavbar />  <!-- 일부 높이 차지 -->
  <main class="flex-1">  ❌ overflow-hidden 없음
    <Chat />  <!-- h-screen 사용 → 충돌 -->
  </main>
</div>
```

**문제점**:
1. 부모 div가 `overflow-y-auto`로 스크롤 생성
2. TopNavbar가 높이를 차지
3. Chat.svelte가 `h-screen`을 사용하여 전체 화면 높이 요구
4. main에 `overflow-hidden` 없어서 자식이 넘침

### 수정 파일

#### 1. `webui/src/routes/(app)/+layout.svelte` (Line 338-344)

**수정 전**:
```html
<div class="flex-1 flex flex-col h-screen max-h-screen overflow-y-auto">
  {#if !$page.url.pathname.startsWith('/admin')}
    <TopNavbar />
  {/if}
  
  {#if loaded}
    <main class="flex-1">
      <slot />
    </main>
```

**수정 후**:
```html
<div class="flex-1 flex flex-col h-screen max-h-screen">
  {#if !$page.url.pathname.startsWith('/admin')}
    <TopNavbar class="flex-shrink-0" />
  {/if}
  
  {#if loaded}
    <main class="flex-1 {$page.url.pathname.startsWith('/c/') || $page.url.pathname === '/' ? 'overflow-hidden' : 'overflow-y-auto'}">
      <slot />
    </main>
```

**변경 내용**:
- 부모 div에서 `overflow-y-auto` 제거
- TopNavbar에 `flex-shrink-0` 추가
- main에 조건부 overflow 적용:
  - Chat 페이지 (`/c/` 또는 `/`): `overflow-hidden`
  - 다른 페이지: `overflow-y-auto`

#### 2. `webui/src/lib/components/chat/Chat.svelte` (Line 2013)

**수정 전**:
```html
<div
  class="h-screen max-h-[100dvh] w-full flex flex-col"
  id="chat-container"
>
```

**수정 후**:
```html
<div
  class="h-full w-full flex flex-col"
  id="chat-container"
>
```

**변경 내용**:
- `h-screen max-h-[100dvh]` → `h-full`
- 부모 컨테이너의 높이를 따르도록 변경

### 수정 3: 부모 컨테이너 (Chat.svelte Line 2041)

**수정 전**:
```html
<div class="flex flex-col flex-auto z-10 w-full @container">
```

**수정 후**:
```html
<div class="flex flex-col h-full z-10 w-full @container">
```

**변경 내용**:
- `flex-auto` → `h-full`
- 부모 컨테이너가 전체 높이를 명확하게 차지

### 수정 2: 메시지 영역 (Line 2043)

**수정 전**:
```html
<div class="pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden">
```

**수정 후**:
```html
<div class="pb-2.5 flex flex-col justify-between w-full flex-1 overflow-y-auto max-w-full z-10 scrollbar-hidden">
```

**변경 내용**:
- `flex-auto` → `flex-1`
- `overflow-auto` → `overflow-y-auto`
- `h-0` 제거
- 메시지 영역이 남은 공간을 모두 차지하도록 설정

### 수정 3: 입력 영역 (Line 2073)

**수정 전**:
```html
<div class=" pb-[1rem]">
  <MessageInput />
</div>
```

**수정 후**:
```html
<div class="flex-shrink-0 pb-4 px-4 w-full">
  <MessageInput />
</div>
```

**변경 내용**:
- `flex-shrink-0` 추가: 입력 영역이 축소되지 않도록 고정
- `pb-[1rem]` → `pb-4 px-4`: 일관된 간격 사용
- `w-full` 추가: 전체 너비 차지

## 최종 레이아웃 구조

```html
<!-- 전체 레이아웃 구조 (+layout.svelte + Chat.svelte) -->

<!-- +layout.svelte -->
<div class="flex-1 flex flex-col h-screen max-h-screen">  <!-- 부모 -->
  <TopNavbar class="flex-shrink-0" />  <!-- 고정 높이 -->
  <main class="flex-1 overflow-hidden">  <!-- 남은 공간, overflow 제한 -->
    <slot />  <!-- Chat.svelte -->
  </main>
</div>

<!-- Chat.svelte -->
<div class="h-full w-full flex flex-col">  <!-- 부모(main) 높이에 맞춤 -->
  <div class="flex flex-col h-full">  <!-- 전체 높이 -->
    <div class="flex-1 overflow-y-auto">  <!-- 메시지 영역, 스크롤 -->
      <Messages />
    </div>
    <div class="flex-shrink-0 pb-4 px-4 w-full">  <!-- 입력 영역, 하단 고정 -->
      <MessageInput />
    </div>
  </div>
</div>
```

**핵심 포인트**:
1. `+layout.svelte`: TopNavbar를 `flex-shrink-0`로 고정, main에 조건부 overflow 적용
   - Chat 페이지: `overflow-hidden`
   - 다른 페이지: `overflow-y-auto`
2. `Chat.svelte`: `h-full`로 부모 높이에 맞춤
3. 메시지 영역: `flex-1 overflow-y-auto`로 스크롤 가능
4. 입력 영역: `flex-shrink-0`로 하단 고정

## 핵심 원칙

### Flexbox 레이아웃 규칙

1. **부모 컨테이너**:
   - `flex flex-col h-full` 또는 `h-screen`
   - 전체 높이를 명확하게 지정

2. **스크롤 영역** (메시지, 콘텐츠):
   - `flex-1`: 남은 공간 모두 차지
   - `overflow-y-auto`: 세로 스크롤만 활성화
   - `h-0` 제거: flexbox에서 자동으로 높이 계산

3. **고정 영역** (입력창, 버튼 등):
   - `flex-shrink-0`: 축소되지 않도록 고정
   - `w-full`: 전체 너비 차지
   - 적절한 패딩 설정 (`pb-4 px-4` 등)

### 잘못된 패턴 (사용 금지)

```html
<!-- ❌ 사용하지 말 것 -->
<div class="flex flex-col flex-auto">  <!-- flex-auto는 예측 불가능 -->
  <div class="overflow-auto h-0">  <!-- h-0은 스크롤 동작 방해 -->
    ...
  </div>
  <div class="pb-[1rem]">  <!-- 하단 고정 안됨 -->
    ...
  </div>
</div>
```

### 올바른 패턴 (권장)

```html
<!-- ✅ 권장 패턴 -->
<div class="flex flex-col h-full">  <!-- 전체 높이 명확히 설정 -->
  <div class="flex-1 overflow-y-auto">  <!-- 스크롤 영역 -->
    ...
  </div>
  <div class="flex-shrink-0">  <!-- 고정 영역 -->
    ...
  </div>
</div>
```

## 테스트 방법

### 1. 브라우저 하드 새고침
```
Mac: Cmd + Shift + R
Windows: Ctrl + Shift + R
```

### 2. 채팅 화면 확인
1. http://localhost:3001 접속
2. 채팅 시작 또는 기존 채팅 열기
3. 화면 크기 조절 (작게, 크게)

### 3. 확인 사항
- ✅ 메시지 입력창이 화면 하단에 고정
- ✅ 메시지 영역이 스크롤 가능
- ✅ 화면 크기 조절 시에도 입력창 위치 유지
- ✅ 반응형 디자인 정상 작동

## 관련 수정 이력

### 1. Chat UI 스트리밍 응답 처리
- **파일**: `webui/src/lib/components/chat/Chat.svelte` (Line 1671-1742)
- **변경**: SSE 스트리밍 응답 처리 로직 추가
- **관련**: `.cursor/learnings/chat-streaming-ui-fix.md`

### 2. Chat 레이아웃 수정 (초기)
- **파일**: `webui/src/routes/(app)/+layout.svelte`, `webui/src/lib/components/chat/Chat.svelte` (Line 2041-2073)
- **변경**: 메시지 입력창 하단 고정
- **이유**: 사용자가 메시지를 입력할 수 없는 문제 해결

### 3. 전역 스크롤 복구 (수정)
- **날짜**: 2025-11-19
- **파일**: `webui/src/routes/(app)/+layout.svelte` (Line 344)
- **문제**: `overflow-hidden`이 모든 페이지에 적용되어 스크롤 사라짐
- **해결**: 조건부 overflow 적용
  - Chat 페이지 (`/c/`, `/`): `overflow-hidden`
  - 다른 페이지 (Today, Admin 등): `overflow-y-auto`
- **교훈**: 전역 레이아웃 수정 시 다른 페이지 영향 항상 고려

## 예방 체크리스트

### 레이아웃 수정 시
- [ ] 부모 컨테이너에 `h-full` 또는 `h-screen` 설정
- [ ] 스크롤 영역에 `flex-1` + `overflow-y-auto` 사용
- [ ] 고정 영역에 `flex-shrink-0` 사용
- [ ] `h-0`과 `flex-auto` 조합 사용 지양
- [ ] **전역 레이아웃 수정 시 조건부 적용 고려** (다른 페이지 영향)
- [ ] 브라우저에서 실제 화면 확인 (다양한 화면 크기)
- [ ] **모든 페이지에서 스크롤 동작 확인** (Chat, Today, Admin 등)

### 반응형 디자인 확인
- [ ] 모바일 (< 640px)
- [ ] 태블릿 (≥ 768px)
- [ ] 데스크톱 (≥ 1024px)
- [ ] 와이드 (≥ 1536px)

## 참고 자료

- [Tailwind CSS Flexbox](https://tailwindcss.com/docs/flex)
- [Tailwind CSS Overflow](https://tailwindcss.com/docs/overflow)
- `.cursor/rules/ui-development.mdc`: UI 개발 규칙

