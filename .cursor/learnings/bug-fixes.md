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

## 2025-11-13: WebUI 개발 서버 PYTHONPATH 설정 누락

**증상**:
- webui 개발 서버(docker-compose.dev.yml)가 3001 포트로 기동 실패
- 에러: `ModuleNotFoundError: No module named 'open_webui'`
- Backend: uvicorn이 `open_webui.main:app`을 찾지 못함

**근본 원인**:
- `dev-start.sh`에서 `cd backend` 후 uvicorn 실행 시 PYTHONPATH 미설정
- `Dockerfile.dev`에 PYTHONPATH 환경 변수 누락
- Python이 `backend/open_webui` 디렉토리를 모듈로 인식하지 못함

**해결 방법**:
1. `dev-start.sh` 수정:
   ```bash
   PYTHONPATH=. WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' --reload &
   ```
2. `Dockerfile.dev` 수정:
   ```dockerfile
   ENV PYTHONPATH=/app/backend:$PYTHONPATH
   ```

**예방**:
- 모든 Python 서비스는 PYTHONPATH를 명시적으로 설정
- Docker 개발 환경에서는 ENV로 전역 설정
- 스크립트 실행 시에는 `PYTHONPATH=.` 명시

**참고**:
- webui/dev-start.sh (line 27)
- webui/Dockerfile.dev (line 29)

---

## 2025-11-14: 서비스 기동 시 포트 충돌 미확인

**증상**:
- Langflow를 7860 포트로 기동했지만 이미 Stable Diffusion이 7860 포트 사용 중
- 포트 충돌로 인해 백엔드는 정상이지만 외부 접속 불가
- 사용자가 포트 충돌을 인지하지 못하고 백엔드 문제로 착각

**근본 원인**:
- 서비스 기동 전 포트 사용 현황 확인 절차 부재
- docker-compose.yml 작성 시 로컬 환경의 포트 사용 현황 미파악
- 포트 충돌 시 명확한 에러 메시지 없음 (컨테이너는 정상 실행되지만 접속 안 됨)

**해결 방법**:
1. Langflow 포트 변경: `7860:7860` → `7861:7860`
2. 포트 충돌 체크 스크립트 생성: `scripts/check-ports.sh`
   - 서비스별 필수 포트 목록 정의
   - lsof로 포트 사용 현황 확인
   - 충돌 시 PID 및 프로세스명 표시
3. 개발 프로세스에 포트 체크 단계 추가

**예방**:
- **서비스 기동 전 필수**: `./scripts/check-ports.sh` 실행
- docker-compose.yml 수정 시 포트 목록 업데이트
- DEV_CHECKLIST.md에 포트 체크 항목 추가
- 로컬 환경의 상시 실행 서비스 목록 문서화 (Stable Diffusion 등)

**참고**:
- docker-compose.yml (line 243: Langflow 포트 7860 → 7861)
- scripts/check-ports.sh (신규 생성)
- .cursor/learnings/bug-fixes.md (이 문서)

---
