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
1. 충돌하는 서비스의 포트 변경 (⚠️ 기존 프로세스는 종료하지 않음)
   - Langflow: `7860:7860` → `7861:7860` (docker-compose.yml 수정)
   - 외부 포트만 변경, 내부 포트는 유지
2. 포트 충돌 체크 스크립트 생성: `scripts/check-ports.sh`
   - 서비스별 필수 포트 목록 정의
   - lsof로 포트 사용 현황 확인
   - 충돌 시 PID 및 프로세스명 표시
   - 해결 방법: docker-compose.yml 포트 변경 안내
3. 개발 프로세스에 포트 체크 단계 추가

**예방**:
- **서비스 기동 전 필수**: `./scripts/check-ports.sh` 실행
- 충돌 발견 시 docker-compose.yml에서 포트 변경 (kill 금지)
- scripts/check-ports.sh의 포트 목록 동기화
- DEV_CHECKLIST.md에 포트 체크 항목 추가
- 로컬 환경의 상시 실행 서비스 목록 문서화 (Stable Diffusion 등)

**참고**:
- docker-compose.yml (line 243: Langflow 포트 7860 → 7861)
- scripts/check-ports.sh (신규 생성)
- .cursor/learnings/bug-fixes.md (이 문서)

---

## 2025-11-18: AgentOps API SQL 쿼리 스키마 불일치

**증상**:
- `/api/agentops/agents/usage` 엔드포인트 호출 시 500 Internal Server Error 발생
- 에러 메시지: `(1054, "Unknown column 'attributes' in 'SELECT'")`
- 프론트엔드에서 "Failed to fetch agent usage stats: Internal Server Error" 표시

**근본 원인**:
- SQL 쿼리에서 사용한 컬럼명이 실제 MariaDB 테이블 스키마와 불일치
- 쿼리: `JSON_EXTRACT(attributes, '$.service.name')` (존재하지 않는 컬럼)
- 실제 테이블: `service_name`, `span_attributes`, `resource_attributes` 컬럼 사용
- `otel_traces` 테이블 스키마를 확인하지 않고 추측으로 쿼리 작성

**해결 방법**:
1. 실제 테이블 스키마 확인:
   ```bash
   docker-compose exec mariadb mariadb -uroot -prootpass agent_portal -e "DESCRIBE otel_traces;"
   ```
2. SQL 쿼리 수정 (`backend/app/services/agentops_adapter.py`):
   ```python
   # 수정 전
   query = """
   SELECT 
       COALESCE(JSON_UNQUOTE(JSON_EXTRACT(attributes, '$.service.name')), 'Unknown Agent') as agent_name,
       ... JSON_EXTRACT(attributes, '$.llm.usage.total_tokens') ...
   FROM otel_traces
   WHERE JSON_EXTRACT(resource_attributes, '$.project.id') = %s
       AND start_time >= %s
       AND end_time <= %s
   """
   
   # 수정 후
   query = """
   SELECT 
       COALESCE(service_name, 'Unknown Agent') as agent_name,
       ... JSON_EXTRACT(span_attributes, '$.llm.usage.total_tokens') ...
   FROM otel_traces
   WHERE project_id = %s
       AND timestamp >= %s
       AND timestamp <= %s
   """
   ```
3. Docker 이미지 완전 재빌드:
   ```bash
   docker-compose down backend
   docker rmi agent-portal-backend:latest
   docker-compose build --no-cache --pull backend
   docker-compose up -d backend
   ```

**예방**:
- 새 테이블/스키마 작업 시 **반드시 실제 스키마 먼저 확인**
- `DESCRIBE table_name;` 또는 `SHOW CREATE TABLE table_name;` 실행
- SQL 쿼리 작성 전 컬럼명과 데이터 타입 확인
- 추측으로 쿼리 작성 금지
- Docker 볼륨 마운트 제거 후 재빌드하여 확실히 코드 반영 확인
- 로컬 파일 수정 후 컨테이너 내부 파일도 확인 (`docker-compose exec backend cat /app/...`)

**참고**:
- backend/app/services/agentops_adapter.py (line 703-718)
- scripts/init-agentops-schema.sql (otel_traces 테이블 정의)
- commit: 2025-11-18 SQL 스키마 수정

---
