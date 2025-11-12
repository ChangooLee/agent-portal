# API 개발 학습 내용

Agent Portal의 Backend API 개발에서 학습한 패턴과 방법을 기록합니다.

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

## 2025-11-12: API 타임아웃 및 에러 핸들링

**요청**: 외부 API 호출 시 안정성 개선
**적용**: httpx.AsyncClient(timeout=30.0) + try/except 에러 핸들링
**피드백**: ✅ 잘 잡았어 (안정성 향상)
**재사용**: 모든 외부 호출에 타임아웃 30초 설정 필수
**참고**: 
- backend/app/services/litellm_service.py
- backend/app/services/langfuse_service.py

---

