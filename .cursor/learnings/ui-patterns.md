# UI 개발 학습 내용

Agent Portal의 UI 개발에서 학습한 패턴과 방법을 기록합니다.

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

