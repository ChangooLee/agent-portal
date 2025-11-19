# 개발 도구 학습 내용

Agent Portal의 개발 도구 및 유틸리티 사용 학습 내용을 기록합니다.

## 형식

```markdown
## YYYY-MM-DD: 제목

**도구**: 도구 이름
**용도**: 사용 목적
**사용법**: 명령어 및 옵션
**학습 포인트**: 배운 내용
**재사용**: 향후 활용 방법

---
```

---

## 2025-11-19: 임시 문서 정리 스크립트 추가

**도구**: `scripts/clean-temp-docs.sh`
**용도**: 개발 중 생성된 임시 문서를 검증 후 백업하고 정리

**사용법**:
```bash
# 인터랙티브 모드 (각 파일 검증)
./scripts/clean-temp-docs.sh

# 자동 모드 (중요 문서 보존, 나머지 자동 백업)
./scripts/clean-temp-docs.sh --auto
```

**학습 포인트**:
1. **임시 문서 패턴 자동 감지**:
   - `IMPLEMENTATION_*.md`, `TEMP_*.md`, `TODO_*.md` 등
   - 11가지 패턴 자동 감지

2. **중요 문서 보호**:
   - `CRITICAL`, `IMPORTANT`, `PRODUCTION`, `LICENSE` 등 키워드 체크
   - 최근 7일 이내 수정 파일 자동 보존
   - 자동 모드에서도 안전하게 보호

3. **백업 시스템**:
   - `.backup/temp-docs/YYYYMMDD-HHMMSS/` 디렉토리에 백업
   - 원본 경로 구조 유지
   - 복원 간편 (`mv` 명령어 안내)

4. **Git Hook 통합**:
   - `pre-commit` hook에서 임시 문서 자동 체크
   - 경고 메시지로 정리 권장
   - 커밋은 차단하지 않음 (비간섭적)

5. **색상 출력 및 UX**:
   - 색상 코드로 시각적 구분 (빨강/초록/노랑/파랑)
   - 파일 정보 상세 표시 (크기, 줄 수, 수정일, 미리보기)
   - 작업 결과 요약 (보존/백업/오류 개수)

**재사용**:
- 주간 리뷰 시 `./scripts/clean-temp-docs.sh --auto` 실행
- 대규모 리팩토링 후 임시 문서 정리
- CI/CD 파이프라인에 통합 가능 (자동 모드)

**통합 위치**:
- `.cursorrules` — 임시 문서 관리 섹션 추가
- `DEVELOP.md` — 부록 C: 임시 문서 관리
- `.githooks/pre-commit` — 자동 체크 로직
- `.gitignore` — `.backup/` 디렉토리 제외

**참고**:
- scripts/clean-temp-docs.sh (line 1-190)
- .githooks/pre-commit (line 78-88)
- commit 준비 중

---

