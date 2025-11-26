# UI 개발 학습 내용

Agent Portal의 UI 개발에서 학습한 패턴과 방법을 기록합니다.

## 2025-11-19: 상단 네비게이션 메뉴 페이지 전체 너비 사용

**요청**: 상단 네비게이션 메뉴의 모든 메뉴 내부 화면의 가로 사이즈를 full로 채우기
**적용**: 모든 주요 페이지의 `max-w-*` 제한 제거
**변경 내용**:
- `/today`: `max-w-7xl` → `w-full`
- `/agent`: `max-w-[1400px]` → `w-full`
- `/report`: `max-w-[1200px]` → `w-full`
- `/notebook`: `max-w-[1200px]` → `w-full`
- `/search`: `max-w-[1200px]` → `w-full`
- `/usage`: `max-w-4xl` → `w-full`

**재사용**: 새 페이지 생성 시 컨텐츠 영역에 `max-w-*` 제한 사용하지 않고 `w-full` 사용

---

## 형식

```markdown
## YYYY-MM-DD: 제목

**요청**: 사용자 요청 내용
**적용**: 적용한 패턴/방법
**피드백**: ✅ 잘 잡았어 / ❌ 이거 싫어함
**재사용**: 향후 유사 작업 시 적용 방법
**참고**: 관련 파일 경로, 커밋 해시 등

---
```

---

## 2025-11-12: 탭 스타일 모던화

**요청**: monitoring 페이지의 탭 버튼 스타일 변경
**적용**: border-b-2 → rounded-lg 버튼 (bg-[#0072CE] 활성 상태)
**피드백**: ✅ 잘 잡았어 (모던한 디자인)
**재사용**: 향후 모든 탭 네비게이션에 rounded-lg 버튼 스타일 적용
**참고**: 
- webui/src/routes/(app)/admin/monitoring/+page.svelte
- webui/src/routes/(app)/admin/gateway/+page.svelte

---


## 2025-11-12: Auto-extracted from commit 9853788

**내용**: 브라우저 title은 APP_NAME (constants.ts)과 WEBUI_NAME (stores)를 통해 중앙 관리
**커밋**: 9853788

---

## 2025-11-12: Auto-extracted from commit 6008376

**내용**: svelte:head에서 변수를 사용할 때는 반드시 해당 store를 import 해야 함
**커밋**: 6008376

---

## 2025-11-12: Auto-extracted from commit 15325cc

**내용**: webui backend의 WEBUI_NAME은 env.py에 하드코딩되어 있으며, 이 값이 /api/config로 프론트엔드에 전달됨
**커밋**: 15325cc

---

## 2025-11-12: Auto-extracted from commit 2c64b05

**내용**: CSS max-width는 최대 너비만 제한하고 요소를 밀어내지 않음. 사이드바와 같이 고정 요소 옆에 컨텐츠를 배치하려면 margin-left 사용
**커밋**: 2c64b05

---

## 2025-11-19: Auto-extracted from commit dd53594

**내용**: {@const}는 항상 블록 레벨 요소의 직접 자식으로 배치
**커밋**: dd53594

---
