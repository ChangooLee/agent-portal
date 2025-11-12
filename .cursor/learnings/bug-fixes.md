# 버그 수정 학습 내용

Agent Portal에서 발생한 버그와 수정 방법을 기록합니다.

## 형식

```markdown
## YYYY-MM-DD: 버그 제목

**증상**: 버그 발생 상황 및 에러 메시지
**근본 원인**: 버그 발생 근본 원인
**해결 방법**: 적용한 해결 방법
**예방**: 향후 동일 버그 방지 방법
**참고**: 관련 파일 경로, 커밋 해시 등

---
```

---

## 2025-11-12: Monitoring 페이지 API 타임아웃

**증상**: 
- Monitoring 페이지 로딩 시 "Failed to load usage summary: TypeError: Failed to fetch" 에러
- 브라우저 콘솔에 네트워크 오류

**근본 원인**: 
- API 호출 시 타임아웃 미설정
- 에러 핸들링 미적용
- 네트워크 오류 시 사용자에게 에러 메시지 노출

**해결 방법**: 
- AbortController로 5초 타임아웃 설정
- try/catch로 에러 핸들링
- 네트워크 오류 시 샘플 데이터 사용 (graceful degradation)

**예방**: 
- API 호출 시 항상 타임아웃 설정
- 에러 핸들링 필수
- 사용자 친화적 에러 메시지

**참고**: 
- webui/src/routes/(app)/admin/monitoring/+page.svelte

---

