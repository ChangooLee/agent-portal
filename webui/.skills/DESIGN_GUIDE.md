# Agent Portal UI Design Guide

> **Purpose**: 일관된 다크 테마 UI를 유지하기 위한 디자인 가이드
> **Base Reference**: 메인 홈페이지 (`/+page.svelte`)
> **Version**: 1.0 (2025-12-08)

---

## 1. 기본 원칙

### 1.1 다크 테마 전용

이 프로젝트는 **다크 테마 전용**입니다. `dark:` 접두사를 사용하지 않고 직접 다크 테마 색상을 사용합니다.

```html
<!-- ❌ WRONG: dark: 접두사 사용 -->
<h1 class="text-gray-900 dark:text-white">제목</h1>

<!-- ✅ CORRECT: 직접 다크 테마 색상 사용 -->
<h1 class="text-white">제목</h1>
```

### 1.2 배경 색상

| 용도 | 클래스 |
|------|--------|
| 페이지 배경 | `bg-gray-950` |
| 카드 배경 | `bg-slate-900/80` |
| 호버 상태 | `hover:bg-slate-800/80` |
| 비활성 상태 | `bg-slate-800/30` |

---

## 2. 색상 팔레트

### 2.1 텍스트 색상

| 용도 | 클래스 | 예시 |
|------|--------|------|
| **제목 (H1, H2)** | `text-white` | 페이지 제목, 섹션 제목 |
| **카드 제목 (H3)** | `text-white` | 카드 내 제목 |
| **본문 텍스트** | `text-slate-300` | 설명, 내용 |
| **보조 텍스트** | `text-slate-400` | 힌트, 캡션, 날짜 |
| **비활성 텍스트** | `text-slate-500` | 비활성 버튼 텍스트 |
| **링크/액션** | `text-blue-400` | 클릭 가능한 링크 |

### 2.2 히어로 섹션 설명 텍스트

페이지별 테마 색상에 따라 설명 텍스트 색상을 다르게 사용:

| 테마 | 설명 텍스트 클래스 |
|------|-------------------|
| 블루 (기본) | `text-blue-200/80` |
| 퍼플 | `text-purple-200/80` |
| 시안 | `text-cyan-200/80` |
| 에메랄드 | `text-emerald-200/80` |
| 앰버 | `text-amber-200/80` |
| 레드 | `text-red-200/80` |
| 인디고 | `text-indigo-200/80` |

### 2.3 테두리 색상

| 용도 | 클래스 |
|------|--------|
| 기본 테두리 | `border-slate-800/50` |
| 호버 테두리 | `hover:border-blue-500/50` (또는 테마 색상) |
| 비활성 테두리 | `border-slate-700/50` |

---

## 3. 컴포넌트 스타일

### 3.1 카드 (Card)

```html
<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 
            shadow-lg shadow-black/20 
            hover:shadow-xl hover:shadow-black/30 
            hover:bg-slate-800/80 hover:border-blue-500/50 
            hover:-translate-y-1 transition-all duration-300">
    <h3 class="text-lg font-bold text-white mb-3">카드 제목</h3>
    <p class="text-sm text-slate-300">카드 설명</p>
</div>
```

### 3.2 섹션 제목 (Section Header)

```html
<h2 class="text-2xl font-bold text-white mb-6">
    🔥 섹션 제목
</h2>
```

### 3.3 히어로 섹션 (Hero Section) ⭐

> **표준 디자인**: 모든 페이지에서 사용 (반응형, 가로 길이 제한 없음)

```html
<div class="relative overflow-hidden border-b border-slate-800/50">
    <!-- 그라디언트 배경 -->
    <div class="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-purple-600/5"></div>
    <!-- 그리드 패턴 -->
    <div class="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
    
    <div class="relative px-6 py-8 text-center">
        <h1 class="text-3xl md:text-4xl font-bold mb-3 text-white">
            📰 페이지 제목
        </h1>
        <p class="text-base text-blue-200/80">
            페이지 설명 텍스트 (반응형, 가로 길이 제한 없음)
        </p>
    </div>
</div>
```

**히어로 섹션 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **제목** | `text-3xl md:text-4xl font-bold text-white` | 반응형 크기, 흰색 |
| **설명 텍스트** | `text-base text-{theme}-200/80` | 테마 색상 사용, **가로 길이 제한 없음** (`max-w-*` 사용 금지) |
| **중앙 정렬** | `text-center` | 제목과 설명 모두 중앙 정렬 |
| **패딩** | `px-6 py-8` | 기본 패딩 |

### 3.4 버튼 스타일

#### Primary Button
```html
<button class="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 
               text-white font-medium shadow-lg shadow-blue-500/25 
               hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300">
    버튼 텍스트
</button>
```

#### Secondary Button (태그, 필터)
```html
<!-- 선택됨 -->
<button class="px-3 py-1.5 rounded-full text-xs font-medium 
               bg-blue-600 text-white border border-blue-500 
               shadow-lg shadow-blue-500/25">
    선택된 태그
</button>

<!-- 미선택 -->
<button class="px-3 py-1.5 rounded-full text-xs font-medium 
               bg-slate-800/80 text-blue-300 border border-slate-700/50 
               hover:bg-slate-700 hover:border-blue-500/50 hover:text-white">
    태그
</button>

<!-- 비활성 -->
<button class="px-3 py-1.5 rounded-full text-xs font-medium 
               opacity-40 cursor-not-allowed 
               bg-slate-800/30 text-slate-500 border border-slate-700/50">
    비활성 태그
</button>
```

### 3.5 빈 상태 (Empty State)

```html
<div class="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
    <p class="text-slate-400">데이터가 없습니다.</p>
</div>
```

### 3.6 테이블 (Table) ⭐

> **표준 디자인**: 모든 테이블에서 사용

```html
<div class="overflow-x-auto">
    <table class="w-full">
        <!-- 헤더 -->
        <thead class="bg-slate-800/50 border-b border-slate-700/50">
            <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                    컬럼명
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                    컬럼명2
                </th>
            </tr>
        </thead>
        
        <!-- 본문 -->
        <tbody class="divide-y divide-slate-800/50">
            <tr class="border-b border-slate-800/50 
                      hover:bg-slate-800/80 hover:border-cyan-500/50 
                      transition-all duration-200">
                <td class="px-6 py-4 text-white font-medium">
                    주요 내용
                </td>
                <td class="px-6 py-4 text-slate-300">
                    보조 내용
                </td>
            </tr>
        </tbody>
    </table>
</div>
```

**테이블 스타일 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **테이블 컨테이너** | `overflow-x-auto` | 가로 스크롤 지원 |
| **헤더 배경** | `bg-slate-800/50` | 반투명 다크 배경 |
| **헤더 테두리** | `border-b border-slate-700/50` | 하단 테두리 |
| **헤더 텍스트** | `text-white` | 흰색 텍스트 |
| **행 구분선** | `divide-y divide-slate-800/50` | 행 간 구분선 |
| **행 호버** | `hover:bg-slate-800/80 hover:border-{theme}-500/50` | 호버 시 배경 밝아짐 + 테두리 색상 (테마 색상 사용) |
| **셀 패딩** | `px-6 py-4` | 기본 패딩 |
| **주요 텍스트** | `text-white font-medium` | 흰색, 중간 굵기 |
| **보조 텍스트** | `text-slate-300` | 밝은 회색 |
| **상태 뱃지** | `bg-{color}-500/20 text-{color}-400 border border-{color}-500/30` | 상태별 색상 (예: `bg-emerald-500/20 text-emerald-400`) |

### 3.7 뉴스/기사 카드 (Article Card) ⭐

> **표준 디자인**: 메인화면 및 Today 페이지에서 사용

```html
<button class="text-left bg-slate-900/80 border border-slate-800/50 rounded-xl p-5 
               shadow-lg shadow-black/20 
               hover:shadow-xl hover:shadow-black/30 
               hover:bg-slate-800/80 hover:border-slate-700/50 
               hover:-translate-y-1 transition-all duration-300 cursor-pointer">
    <!-- 카테고리 & 중요도 뱃지 -->
    <div class="flex items-center gap-2 mb-3 flex-wrap">
        <span class="bg-blue-500/20 text-blue-400 border border-blue-500/30 
                     px-2.5 py-1 rounded-full text-xs font-medium">
            카테고리명
        </span>
        <!-- 중요도 뱃지 (optional) -->
        <span class="bg-gradient-to-r from-red-500 to-pink-500 text-white 
                     px-2.5 py-1 rounded-full text-xs font-semibold shadow-sm">
            🔥 HOT
        </span>
    </div>
    
    <!-- 제목 -->
    <h3 class="text-sm font-medium text-white mb-2 line-clamp-2 leading-relaxed">
        기사 제목
    </h3>
    
    <!-- 설명 -->
    <p class="text-xs text-slate-400 mb-3 line-clamp-2 leading-relaxed">
        기사 요약 내용
    </p>
    
    <!-- 태그 (optional) -->
    <div class="flex flex-wrap gap-1.5">
        <span class="bg-blue-500/20 text-blue-400 border border-blue-500/30 
                     px-2 py-0.5 rounded-md text-xs font-medium">
            태그1
        </span>
    </div>
</button>
```

### 3.8 카테고리 뱃지 색상 맵

```typescript
const categoryColors = {
    '금융규제': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    'AI디지털': 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
    '경영전략': 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
    'ESG': 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    '금융일반': 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30',
    '인사조직': 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    '리스크관리': 'bg-red-500/20 text-red-400 border border-red-500/30',
    '기본값': 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
};
```

### 3.9 태그 뱃지 색상 (순환)

```typescript
const tagColors = [
    'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    'bg-purple-500/20 text-purple-400 border border-purple-500/30',
    'bg-pink-500/20 text-pink-400 border border-pink-500/30',
    'bg-amber-500/20 text-amber-400 border border-amber-500/30'
];
// 사용: tagColors[index % tagColors.length]
```

### 3.10 중요도 뱃지

```html
<!-- HOT (importance_score >= 10) -->
<span class="bg-gradient-to-r from-red-500 to-pink-500 text-white 
             px-2.5 py-1 rounded-full text-xs font-semibold shadow-sm">
    🔥 HOT
</span>

<!-- 주요 (importance_score >= 5) -->
<span class="bg-gradient-to-r from-orange-500 to-yellow-500 text-white 
             px-2.5 py-1 rounded-full text-xs font-semibold shadow-sm">
    ⭐ 주요
</span>
```

### 3.11 제안(Suggestions) 카드

> Chat 페이지의 제안 섹션에서 사용

```html
<button class="flex flex-col w-full px-3 py-2 rounded-xl 
               bg-slate-900/80 border border-slate-800/50
               hover:bg-slate-800/80 hover:border-blue-500/50
               hover:shadow-lg hover:shadow-black/30 hover:-translate-y-0.5
               transition-all duration-300 ease-out group">
    <div class="font-medium text-white group-hover:text-blue-100 transition line-clamp-1">
        제안 제목
    </div>
    <div class="text-xs text-slate-400 font-normal line-clamp-1">
        제안 설명
    </div>
</button>
```

---

## 4. 호버 효과

### 4.1 카드 호버 (메인화면 기준)

```html
hover:bg-slate-800/80          /* 배경 밝아짐 */
hover:border-blue-500/50       /* 테두리 색상 (테마 색상 사용) */
hover:shadow-xl                 /* 그림자 강화 */
hover:shadow-black/30          /* 그림자 색상 */
hover:-translate-y-1           /* 살짝 올라감 */
transition-all duration-300    /* 부드러운 전환 */
```

### 4.2 아이콘/버튼 호버

```html
group-hover:scale-110          /* 아이콘 확대 */
group-hover:text-white         /* 텍스트 밝아짐 */
```

---

## 5. 금지 사항

### 5.1 절대 사용하지 말 것

```html
<!-- ❌ dark: 접두사 (다크 모드 클래스가 없어 동작 안함) -->
<p class="text-gray-600 dark:text-gray-300">

<!-- ❌ 밝은 배경색 (다크 테마에서 눈에 띔) -->
<div class="bg-white">
<div class="bg-gray-50">
<div class="bg-gray-100">

<!-- ❌ 어두운 텍스트 (다크 배경에서 안보임) -->
<p class="text-gray-600">
<p class="text-gray-700">
<p class="text-gray-900">
```

### 5.2 항상 확인할 것

1. **다크 배경에서 텍스트 가시성** - `text-white` 또는 `text-slate-300` 사용
2. **호버 상태 확인** - 호버 시 시각적 피드백 있는지
3. **비활성 상태 구분** - `opacity-40` + `cursor-not-allowed` 사용
4. **일관된 그림자** - `shadow-black/20` 또는 `shadow-black/30`

---

## 6. 페이지별 테마 색상

| 페이지 | 그라디언트 | 버튼/액센트 |
|--------|-----------|-------------|
| 홈 (/) | blue → purple | blue-600 |
| Today | blue → purple | blue-600 |
| Agents | blue → purple | blue-600 |
| MCP | purple → pink | purple-600 |
| Monitoring | cyan → teal | cyan-600 |
| LLM | blue → cyan | blue-600 |
| Gateway | indigo → violet | indigo-600 |
| Data Cloud | cyan → blue | cyan-600 |
| Guardrails | red → rose | red-600 |
| Evaluations | amber → yellow | amber-600 |
| Workflows | purple → blue | purple-600 |
| Prompts | amber → orange | amber-600 |
| Knowledge | emerald → teal | emerald-600 |
| Settings | slate → zinc | slate-600 |
| Users | blue → cyan | blue-600 |

---

## 7. Quick Reference

### 자주 사용하는 클래스 조합

```css
/* 페이지 컨테이너 */
.page-container {
    @apply min-h-full bg-gray-950 text-slate-50;
}

/* 카드 */
.card {
    @apply bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 
           shadow-lg shadow-black/20 
           hover:shadow-xl hover:shadow-black/30 
           hover:bg-slate-800/80 hover:border-blue-500/50 
           hover:-translate-y-1 transition-all duration-300;
}

/* 섹션 제목 */
.section-title {
    @apply text-2xl font-bold text-white mb-6;
}

/* 설명 텍스트 */
.description {
    @apply text-slate-300;
}

/* 보조 텍스트 */
.muted {
    @apply text-slate-400;
}
```

---

**Last Updated**: 2025-12-08
**Maintainer**: Agent Portal Team

---

## 8. 채팅 화면 디자인 표준 ⭐

### 8.1 채팅 입력창 (Chat Input)

> **표준 디자인**: 다크 테마에 맞춘 반투명 배경, 블러 효과

```html
<div class="flex-1 flex flex-col relative w-full rounded-3xl px-1 
            text-white bg-slate-900/80 backdrop-blur-sm 
            border border-slate-700/50 
            hover:border-slate-600/70 
            focus-within:border-blue-500/50 
            hover:shadow-lg hover:shadow-black/30 
            focus-within:shadow-xl focus-within:shadow-blue-500/20 
            transition-all duration-300 ease-out">
    <div class="scrollbar-hidden text-left bg-transparent text-white 
                outline-hidden w-full py-2.5 px-1 resize-none 
                h-fit max-h-80 overflow-auto">
        <!-- 입력 필드 -->
    </div>
</div>
```

**입력창 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **컨테이너** | `bg-slate-900/80 backdrop-blur-sm` | 반투명 배경, 블러 효과 |
| **테두리** | `border-slate-700/50` | 기본 테두리 |
| **호버** | `hover:border-slate-600/70 hover:shadow-lg hover:shadow-black/30` | 호버 시 테두리 및 그림자 |
| **포커스** | `focus-within:border-blue-500/50 focus-within:shadow-xl focus-within:shadow-blue-500/20` | 포커스 시 파란색 테두리 및 그림자 |
| **텍스트** | `text-white` | 흰색 텍스트 |
| **플레이스홀더** | `placeholder:text-slate-400` | 회색 플레이스홀더 |

### 8.2 사용자 메시지 버블 (User Message Bubble)

> **표준 디자인**: 파란색 반투명 배경, 테두리

```html
<div class="rounded-3xl max-w-[90%] px-5 py-2 
            bg-blue-500/20 text-white 
            border border-blue-500/30">
    <!-- 메시지 내용 -->
</div>
```

**사용자 메시지 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **배경** | `bg-blue-500/20` | 파란색 반투명 배경 |
| **테두리** | `border border-blue-500/30` | 파란색 반투명 테두리 |
| **텍스트** | `text-white` | 흰색 텍스트 |
| **최대 너비** | `max-w-[90%]` | 화면의 90%까지 확장 |
| **패딩** | `px-5 py-2` | 기본 패딩 |

### 8.3 응답 메시지 (Response Message)

> **표준 디자인**: 일반 텍스트, 다크 테마 색상

```html
<div class="chat-assistant w-full min-w-full markdown-prose">
    <div>
        <!-- 메시지 내용 -->
    </div>
</div>
```

**응답 메시지 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **모델 이름** | `text-white` | 흰색 텍스트 |
| **타임스탬프** | `text-slate-400` | 회색 텍스트 |
| **버튼 영역** | `text-slate-300` | 회색 텍스트 |
| **콘텐츠** | `markdown-prose` | 마크다운 스타일 적용 |


> **Purpose**: 일관된 다크 테마 UI를 유지하기 위한 디자인 가이드
> **Base Reference**: 메인 홈페이지 (`/+page.svelte`)
> **Version**: 1.0 (2025-12-08)

---

## 1. 기본 원칙

### 1.1 다크 테마 전용

이 프로젝트는 **다크 테마 전용**입니다. `dark:` 접두사를 사용하지 않고 직접 다크 테마 색상을 사용합니다.

```html
<!-- ❌ WRONG: dark: 접두사 사용 -->
<h1 class="text-gray-900 dark:text-white">제목</h1>

<!-- ✅ CORRECT: 직접 다크 테마 색상 사용 -->
<h1 class="text-white">제목</h1>
```

### 1.2 배경 색상

| 용도 | 클래스 |
|------|--------|
| 페이지 배경 | `bg-gray-950` |
| 카드 배경 | `bg-slate-900/80` |
| 호버 상태 | `hover:bg-slate-800/80` |
| 비활성 상태 | `bg-slate-800/30` |

---

## 2. 색상 팔레트

### 2.1 텍스트 색상

| 용도 | 클래스 | 예시 |
|------|--------|------|
| **제목 (H1, H2)** | `text-white` | 페이지 제목, 섹션 제목 |
| **카드 제목 (H3)** | `text-white` | 카드 내 제목 |
| **본문 텍스트** | `text-slate-300` | 설명, 내용 |
| **보조 텍스트** | `text-slate-400` | 힌트, 캡션, 날짜 |
| **비활성 텍스트** | `text-slate-500` | 비활성 버튼 텍스트 |
| **링크/액션** | `text-blue-400` | 클릭 가능한 링크 |

### 2.2 히어로 섹션 설명 텍스트

페이지별 테마 색상에 따라 설명 텍스트 색상을 다르게 사용:

| 테마 | 설명 텍스트 클래스 |
|------|-------------------|
| 블루 (기본) | `text-blue-200/80` |
| 퍼플 | `text-purple-200/80` |
| 시안 | `text-cyan-200/80` |
| 에메랄드 | `text-emerald-200/80` |
| 앰버 | `text-amber-200/80` |
| 레드 | `text-red-200/80` |
| 인디고 | `text-indigo-200/80` |

### 2.3 테두리 색상

| 용도 | 클래스 |
|------|--------|
| 기본 테두리 | `border-slate-800/50` |
| 호버 테두리 | `hover:border-blue-500/50` (또는 테마 색상) |
| 비활성 테두리 | `border-slate-700/50` |

---

## 3. 컴포넌트 스타일

### 3.1 카드 (Card)

```html
<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 
            shadow-lg shadow-black/20 
            hover:shadow-xl hover:shadow-black/30 
            hover:bg-slate-800/80 hover:border-blue-500/50 
            hover:-translate-y-1 transition-all duration-300">
    <h3 class="text-lg font-bold text-white mb-3">카드 제목</h3>
    <p class="text-sm text-slate-300">카드 설명</p>
</div>
```

### 3.2 섹션 제목 (Section Header)

```html
<h2 class="text-2xl font-bold text-white mb-6">
    🔥 섹션 제목
</h2>
```

### 3.3 히어로 섹션 (Hero Section) ⭐

> **표준 디자인**: 모든 페이지에서 사용 (반응형, 가로 길이 제한 없음)

```html
<div class="relative overflow-hidden border-b border-slate-800/50">
    <!-- 그라디언트 배경 -->
    <div class="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-purple-600/5"></div>
    <!-- 그리드 패턴 -->
    <div class="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
    
    <div class="relative px-6 py-8 text-center">
        <h1 class="text-3xl md:text-4xl font-bold mb-3 text-white">
            📰 페이지 제목
        </h1>
        <p class="text-base text-blue-200/80">
            페이지 설명 텍스트 (반응형, 가로 길이 제한 없음)
        </p>
    </div>
</div>
```

**히어로 섹션 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **제목** | `text-3xl md:text-4xl font-bold text-white` | 반응형 크기, 흰색 |
| **설명 텍스트** | `text-base text-{theme}-200/80` | 테마 색상 사용, **가로 길이 제한 없음** (`max-w-*` 사용 금지) |
| **중앙 정렬** | `text-center` | 제목과 설명 모두 중앙 정렬 |
| **패딩** | `px-6 py-8` | 기본 패딩 |

### 3.4 버튼 스타일

#### Primary Button
```html
<button class="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 
               text-white font-medium shadow-lg shadow-blue-500/25 
               hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300">
    버튼 텍스트
</button>
```

#### Secondary Button (태그, 필터)
```html
<!-- 선택됨 -->
<button class="px-3 py-1.5 rounded-full text-xs font-medium 
               bg-blue-600 text-white border border-blue-500 
               shadow-lg shadow-blue-500/25">
    선택된 태그
</button>

<!-- 미선택 -->
<button class="px-3 py-1.5 rounded-full text-xs font-medium 
               bg-slate-800/80 text-blue-300 border border-slate-700/50 
               hover:bg-slate-700 hover:border-blue-500/50 hover:text-white">
    태그
</button>

<!-- 비활성 -->
<button class="px-3 py-1.5 rounded-full text-xs font-medium 
               opacity-40 cursor-not-allowed 
               bg-slate-800/30 text-slate-500 border border-slate-700/50">
    비활성 태그
</button>
```

### 3.5 빈 상태 (Empty State)

```html
<div class="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
    <p class="text-slate-400">데이터가 없습니다.</p>
</div>
```

### 3.6 테이블 (Table) ⭐

> **표준 디자인**: 모든 테이블에서 사용

```html
<div class="overflow-x-auto">
    <table class="w-full">
        <!-- 헤더 -->
        <thead class="bg-slate-800/50 border-b border-slate-700/50">
            <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                    컬럼명
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                    컬럼명2
                </th>
            </tr>
        </thead>
        
        <!-- 본문 -->
        <tbody class="divide-y divide-slate-800/50">
            <tr class="border-b border-slate-800/50 
                      hover:bg-slate-800/80 hover:border-cyan-500/50 
                      transition-all duration-200">
                <td class="px-6 py-4 text-white font-medium">
                    주요 내용
                </td>
                <td class="px-6 py-4 text-slate-300">
                    보조 내용
                </td>
            </tr>
        </tbody>
    </table>
</div>
```

**테이블 스타일 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **테이블 컨테이너** | `overflow-x-auto` | 가로 스크롤 지원 |
| **헤더 배경** | `bg-slate-800/50` | 반투명 다크 배경 |
| **헤더 테두리** | `border-b border-slate-700/50` | 하단 테두리 |
| **헤더 텍스트** | `text-white` | 흰색 텍스트 |
| **행 구분선** | `divide-y divide-slate-800/50` | 행 간 구분선 |
| **행 호버** | `hover:bg-slate-800/80 hover:border-{theme}-500/50` | 호버 시 배경 밝아짐 + 테두리 색상 (테마 색상 사용) |
| **셀 패딩** | `px-6 py-4` | 기본 패딩 |
| **주요 텍스트** | `text-white font-medium` | 흰색, 중간 굵기 |
| **보조 텍스트** | `text-slate-300` | 밝은 회색 |
| **상태 뱃지** | `bg-{color}-500/20 text-{color}-400 border border-{color}-500/30` | 상태별 색상 (예: `bg-emerald-500/20 text-emerald-400`) |

### 3.7 뉴스/기사 카드 (Article Card) ⭐

> **표준 디자인**: 메인화면 및 Today 페이지에서 사용

```html
<button class="text-left bg-slate-900/80 border border-slate-800/50 rounded-xl p-5 
               shadow-lg shadow-black/20 
               hover:shadow-xl hover:shadow-black/30 
               hover:bg-slate-800/80 hover:border-slate-700/50 
               hover:-translate-y-1 transition-all duration-300 cursor-pointer">
    <!-- 카테고리 & 중요도 뱃지 -->
    <div class="flex items-center gap-2 mb-3 flex-wrap">
        <span class="bg-blue-500/20 text-blue-400 border border-blue-500/30 
                     px-2.5 py-1 rounded-full text-xs font-medium">
            카테고리명
        </span>
        <!-- 중요도 뱃지 (optional) -->
        <span class="bg-gradient-to-r from-red-500 to-pink-500 text-white 
                     px-2.5 py-1 rounded-full text-xs font-semibold shadow-sm">
            🔥 HOT
        </span>
    </div>
    
    <!-- 제목 -->
    <h3 class="text-sm font-medium text-white mb-2 line-clamp-2 leading-relaxed">
        기사 제목
    </h3>
    
    <!-- 설명 -->
    <p class="text-xs text-slate-400 mb-3 line-clamp-2 leading-relaxed">
        기사 요약 내용
    </p>
    
    <!-- 태그 (optional) -->
    <div class="flex flex-wrap gap-1.5">
        <span class="bg-blue-500/20 text-blue-400 border border-blue-500/30 
                     px-2 py-0.5 rounded-md text-xs font-medium">
            태그1
        </span>
    </div>
</button>
```

### 3.8 카테고리 뱃지 색상 맵

```typescript
const categoryColors = {
    '금융규제': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    'AI디지털': 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
    '경영전략': 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
    'ESG': 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    '금융일반': 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30',
    '인사조직': 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    '리스크관리': 'bg-red-500/20 text-red-400 border border-red-500/30',
    '기본값': 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
};
```

### 3.9 태그 뱃지 색상 (순환)

```typescript
const tagColors = [
    'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    'bg-purple-500/20 text-purple-400 border border-purple-500/30',
    'bg-pink-500/20 text-pink-400 border border-pink-500/30',
    'bg-amber-500/20 text-amber-400 border border-amber-500/30'
];
// 사용: tagColors[index % tagColors.length]
```

### 3.10 중요도 뱃지

```html
<!-- HOT (importance_score >= 10) -->
<span class="bg-gradient-to-r from-red-500 to-pink-500 text-white 
             px-2.5 py-1 rounded-full text-xs font-semibold shadow-sm">
    🔥 HOT
</span>

<!-- 주요 (importance_score >= 5) -->
<span class="bg-gradient-to-r from-orange-500 to-yellow-500 text-white 
             px-2.5 py-1 rounded-full text-xs font-semibold shadow-sm">
    ⭐ 주요
</span>
```

### 3.11 제안(Suggestions) 카드

> Chat 페이지의 제안 섹션에서 사용

```html
<button class="flex flex-col w-full px-3 py-2 rounded-xl 
               bg-slate-900/80 border border-slate-800/50
               hover:bg-slate-800/80 hover:border-blue-500/50
               hover:shadow-lg hover:shadow-black/30 hover:-translate-y-0.5
               transition-all duration-300 ease-out group">
    <div class="font-medium text-white group-hover:text-blue-100 transition line-clamp-1">
        제안 제목
    </div>
    <div class="text-xs text-slate-400 font-normal line-clamp-1">
        제안 설명
    </div>
</button>
```

---

## 4. 호버 효과

### 4.1 카드 호버 (메인화면 기준)

```html
hover:bg-slate-800/80          /* 배경 밝아짐 */
hover:border-blue-500/50       /* 테두리 색상 (테마 색상 사용) */
hover:shadow-xl                 /* 그림자 강화 */
hover:shadow-black/30          /* 그림자 색상 */
hover:-translate-y-1           /* 살짝 올라감 */
transition-all duration-300    /* 부드러운 전환 */
```

### 4.2 아이콘/버튼 호버

```html
group-hover:scale-110          /* 아이콘 확대 */
group-hover:text-white         /* 텍스트 밝아짐 */
```

---

## 5. 금지 사항

### 5.1 절대 사용하지 말 것

```html
<!-- ❌ dark: 접두사 (다크 모드 클래스가 없어 동작 안함) -->
<p class="text-gray-600 dark:text-gray-300">

<!-- ❌ 밝은 배경색 (다크 테마에서 눈에 띔) -->
<div class="bg-white">
<div class="bg-gray-50">
<div class="bg-gray-100">

<!-- ❌ 어두운 텍스트 (다크 배경에서 안보임) -->
<p class="text-gray-600">
<p class="text-gray-700">
<p class="text-gray-900">
```

### 5.2 항상 확인할 것

1. **다크 배경에서 텍스트 가시성** - `text-white` 또는 `text-slate-300` 사용
2. **호버 상태 확인** - 호버 시 시각적 피드백 있는지
3. **비활성 상태 구분** - `opacity-40` + `cursor-not-allowed` 사용
4. **일관된 그림자** - `shadow-black/20` 또는 `shadow-black/30`

---

## 6. 페이지별 테마 색상

| 페이지 | 그라디언트 | 버튼/액센트 |
|--------|-----------|-------------|
| 홈 (/) | blue → purple | blue-600 |
| Today | blue → purple | blue-600 |
| Agents | blue → purple | blue-600 |
| MCP | purple → pink | purple-600 |
| Monitoring | cyan → teal | cyan-600 |
| LLM | blue → cyan | blue-600 |
| Gateway | indigo → violet | indigo-600 |
| Data Cloud | cyan → blue | cyan-600 |
| Guardrails | red → rose | red-600 |
| Evaluations | amber → yellow | amber-600 |
| Workflows | purple → blue | purple-600 |
| Prompts | amber → orange | amber-600 |
| Knowledge | emerald → teal | emerald-600 |
| Settings | slate → zinc | slate-600 |
| Users | blue → cyan | blue-600 |

---

## 7. Quick Reference

### 자주 사용하는 클래스 조합

```css
/* 페이지 컨테이너 */
.page-container {
    @apply min-h-full bg-gray-950 text-slate-50;
}

/* 카드 */
.card {
    @apply bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 
           shadow-lg shadow-black/20 
           hover:shadow-xl hover:shadow-black/30 
           hover:bg-slate-800/80 hover:border-blue-500/50 
           hover:-translate-y-1 transition-all duration-300;
}

/* 섹션 제목 */
.section-title {
    @apply text-2xl font-bold text-white mb-6;
}

/* 설명 텍스트 */
.description {
    @apply text-slate-300;
}

/* 보조 텍스트 */
.muted {
    @apply text-slate-400;
}
```

---

**Last Updated**: 2025-12-08
**Maintainer**: Agent Portal Team

---

## 8. 채팅 화면 디자인 표준 ⭐

### 8.1 채팅 입력창 (Chat Input)

> **표준 디자인**: 다크 테마에 맞춘 반투명 배경, 블러 효과

```html
<div class="flex-1 flex flex-col relative w-full rounded-3xl px-1 
            text-white bg-slate-900/80 backdrop-blur-sm 
            border border-slate-700/50 
            hover:border-slate-600/70 
            focus-within:border-blue-500/50 
            hover:shadow-lg hover:shadow-black/30 
            focus-within:shadow-xl focus-within:shadow-blue-500/20 
            transition-all duration-300 ease-out">
    <div class="scrollbar-hidden text-left bg-transparent text-white 
                outline-hidden w-full py-2.5 px-1 resize-none 
                h-fit max-h-80 overflow-auto">
        <!-- 입력 필드 -->
    </div>
</div>
```

**입력창 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **컨테이너** | `bg-slate-900/80 backdrop-blur-sm` | 반투명 배경, 블러 효과 |
| **테두리** | `border-slate-700/50` | 기본 테두리 |
| **호버** | `hover:border-slate-600/70 hover:shadow-lg hover:shadow-black/30` | 호버 시 테두리 및 그림자 |
| **포커스** | `focus-within:border-blue-500/50 focus-within:shadow-xl focus-within:shadow-blue-500/20` | 포커스 시 파란색 테두리 및 그림자 |
| **텍스트** | `text-white` | 흰색 텍스트 |
| **플레이스홀더** | `placeholder:text-slate-400` | 회색 플레이스홀더 |

### 8.2 사용자 메시지 버블 (User Message Bubble)

> **표준 디자인**: 파란색 반투명 배경, 테두리

```html
<div class="rounded-3xl max-w-[90%] px-5 py-2 
            bg-blue-500/20 text-white 
            border border-blue-500/30">
    <!-- 메시지 내용 -->
</div>
```

**사용자 메시지 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **배경** | `bg-blue-500/20` | 파란색 반투명 배경 |
| **테두리** | `border border-blue-500/30` | 파란색 반투명 테두리 |
| **텍스트** | `text-white` | 흰색 텍스트 |
| **최대 너비** | `max-w-[90%]` | 화면의 90%까지 확장 |
| **패딩** | `px-5 py-2` | 기본 패딩 |

### 8.3 응답 메시지 (Response Message)

> **표준 디자인**: 일반 텍스트, 다크 테마 색상

```html
<div class="chat-assistant w-full min-w-full markdown-prose">
    <div>
        <!-- 메시지 내용 -->
    </div>
</div>
```

**응답 메시지 규칙:**

| 요소 | 클래스 | 설명 |
|------|--------|------|
| **모델 이름** | `text-white` | 흰색 텍스트 |
| **타임스탬프** | `text-slate-400` | 회색 텍스트 |
| **버튼 영역** | `text-slate-300` | 회색 텍스트 |
| **콘텐츠** | `markdown-prose` | 마크다운 스타일 적용 |

