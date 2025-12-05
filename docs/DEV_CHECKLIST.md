# 개발 환경 체크리스트

Agent Portal 프로젝트의 개발 환경 설정 및 확인 사항입니다.

## WebUI Backend 개발 시 (CRITICAL)

### 작업 전 확인

- [ ] PYTHONPATH 설정 확인 (`webui/Dockerfile.dev` line 29)
- [ ] dev-start.sh에 PYTHONPATH=. 명시 (line 27)
- [ ] 볼륨 마운트 확인 (`docker-compose.dev.yml`)

### 작업 후 확인

- [ ] 개발 서버 시작: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d webui`
- [ ] 로그 확인: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f webui`
- [ ] ModuleNotFoundError 발생 여부 확인
- [ ] 포트 접속: `http://localhost:3009` (Frontend), `http://localhost:8000/docs` (Backend)

### 일반적인 문제 해결

**문제**: `ModuleNotFoundError: No module named 'open_webui'`

**해결**:
1. `webui/dev-start.sh` line 27 확인:
   ```bash
   PYTHONPATH=. WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' --reload &
   ```

2. `webui/Dockerfile.dev` line 29 확인:
   ```dockerfile
   ENV PYTHONPATH=/app/backend:$PYTHONPATH
   ```

3. 컨테이너 재빌드:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache webui
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d webui
   ```

## FastAPI BFF 개발 시

### 작업 전 확인

- [ ] 서비스 레이어 패턴 준수 (Singleton)
- [ ] Type hints 및 Docstring 작성
- [ ] 에러 핸들링 및 타임아웃 설정 (30초)

### 작업 후 확인

- [ ] OpenAPI 문서 확인: `http://localhost:8000/docs`
- [ ] API 엔드포인트 테스트
- [ ] 컨테이너 로그 확인: `docker-compose logs backend`

### 새 API 엔드포인트 추가 시

- [ ] 라우터 파일 생성 (`backend/app/routes/`)
- [ ] Pydantic 모델 정의 (요청/응답)
- [ ] 엔드포인트 함수 구현 (비동기 메서드)
- [ ] `backend/app/main.py`에 라우터 등록
- [ ] 에러 핸들링 및 타임아웃 설정
- [ ] OpenAPI 문서 확인 (`/docs`)

### 새 서비스 추가 시

- [ ] 서비스 파일 생성 (`backend/app/services/`)
- [ ] 클래스 정의 및 초기화
- [ ] 비동기 메서드 구현
- [ ] 타임아웃 설정 (기본 30초)
- [ ] 에러 핸들링 (try/except)
- [ ] Singleton 인스턴스 생성

## Docker 개발 환경

### 서비스 기동 전 필수 체크 (⚠️ CRITICAL)

```bash
# 포트 충돌 확인 (반드시 실행!)
./scripts/check-ports.sh
```

**확인 항목**:
- [ ] 모든 필수 포트가 사용 가능한지 확인
- [ ] 충돌 발견 시 해결 (⚠️ 기존 프로세스는 종료하지 말 것):
  - **우선**: docker-compose.yml에서 포트 변경 (예: `7860:7860` → `7861:7860`)
  - scripts/check-ports.sh의 포트 목록 업데이트
- [ ] 로컬 환경의 상시 실행 서비스 확인 (Stable Diffusion 등)

**주요 포트 목록**:
- Backend BFF: 8000
- WebUI: 3009
- Flowise: 3002
- LiteLLM: 4000
- AutoGen Studio: 5050
- AutoGen API: 5051
- Langflow: 7861 (⚠️ 7860은 Stable Diffusion)
- Kong: 8002, 8443

### 개발 모드 시작

```bash
# WebUI 개발 서버 (핫 리로드)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d webui

# Backend BFF
docker-compose up -d backend

# 전체 서비스
docker-compose up -d
```

### 로그 확인

```bash
# WebUI 로그
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f webui

# Backend 로그
docker-compose logs -f backend

# 전체 로그
docker-compose logs -f
```

### 컨테이너 재빌드

```bash
# WebUI (개발 모드)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache webui
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d webui

# Backend BFF
docker-compose build --no-cache backend
docker-compose up -d backend
```

## Skills 시스템 업데이트

### UI 구조 변경 시

```bash
# 모든 Skills 파일 업데이트 (UI + Backend)
./scripts/update-ui-skills.sh

# 개별 업데이트
node scripts/analyze-ui-structure.js
node scripts/analyze-backend-structure.js
```

### Backend 구조 변경 시

```bash
# Backend Skills 업데이트
node scripts/analyze-backend-structure.js

# 또는 전체 업데이트
./scripts/update-ui-skills.sh
```

## 테스트

### Frontend 테스트

- [ ] 브라우저에서 `http://localhost:3009` 접속 확인
- [ ] 다크/라이트 모드 전환 테스트
- [ ] 모바일/태블릿/데스크톱 반응형 테스트
- [ ] 브라우저 콘솔 에러 확인

### Backend 테스트

- [ ] OpenAPI 문서 확인: `http://localhost:8000/docs`
- [ ] API 엔드포인트 직접 호출 테스트
- [ ] 타임아웃 및 에러 핸들링 테스트
- [ ] 컨테이너 로그 확인

## 트러블슈팅

### 포트 충돌

```bash
# 포트 사용 현황 확인
./scripts/check-ports.sh

# 또는 특정 포트 확인
lsof -i :3009 -i :8000 -i :4000
```

**해결 방법** (⚠️ 기존 프로세스 종료 금지):
1. docker-compose.yml에서 충돌하는 서비스의 포트 변경
   ```yaml
   # 변경 전
   ports:
     - "7860:7860"
   
   # 변경 후
   ports:
     - "7861:7860"
   ```
2. scripts/check-ports.sh의 포트 목록 업데이트
3. 서비스 재시작: `docker-compose restart <service-name>`

### 볼륨 마운트 문제

```bash
# 볼륨 확인
docker volume ls

# 볼륨 삭제 (데이터 손실 주의)
docker volume rm agent-portal_webui_node_modules
docker volume rm agent-portal_webui_backend_data

# 재생성
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d webui
```

### 빌드 캐시 문제

```bash
# Docker 빌드 캐시 삭제
docker builder prune -a

# 재빌드
docker-compose build --no-cache
```

## 참고 문서

- `CLAUDE.md`: 프로젝트 가이드
- `AGENTS.md`: 에이전트 워크플로우
- `.cursor/rules/backend-api.mdc`: Backend API 개발 규칙
- `.cursor/learnings/bug-fixes.md`: 버그 수정 학습 내용
- `backend/.skills/backend-structure.json`: FastAPI BFF 구조
- `webui/.skills/backend-structure.json`: WebUI Backend 구조

