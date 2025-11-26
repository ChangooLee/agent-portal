# Open-WebUI 백엔드 초기화 실패 원인 분석

## 날짜: 2025-11-25

## 문제 상황

Open-WebUI 백엔드가 초기화 중 멈춰서 `/api/config` 엔드포인트가 응답하지 않음.

### 증상
- Uvicorn은 실행 중 (`INFO: Uvicorn running on http://0.0.0.0:8080`)
- Worker process가 시작되지 않음 ("Started server process" 메시지 없음)
- Health check 타임아웃 (30초)
- 프론트엔드는 시작되었으나 백엔드 API 호출 실패

## 근본 원인 (Root Cause Analysis)

### 1. `vite.config.ts` 들여쓰기 에러 (PRIMARY CAUSE)

**문제**:
```typescript
// 잘못된 들여쓰기
'/api/agentops': {
    target: ...,
    changeOrigin: true
},
// ❌ 이 부분이 '/api/agentops' 블록 안에 잘못 들어감!
'/api': {
    target: 'http://localhost:8080',
    changeOrigin: true,
    ws: true
},
```

**원인**:
- 수동 편집 중 들여쓰기 실수
- `proxy` 객체의 중괄호 구조가 망가짐
- Vite가 프록시 설정을 파싱하지 못함

**영향**:
- Vite 개발 서버가 크래시하거나
- 프록시 라우팅이 작동하지 않음
- `/api/config` 요청이 백엔드로 전달되지 않음

**해결**:
```typescript
// ✅ 올바른 들여쓰기
'/api/agentops': {
    target: ...,
    changeOrigin: true
},
'/api': {
    target: 'http://localhost:8080',
    changeOrigin: true,
    ws: true
},
```

### 2. ChromaDB Tenant 에러 (SECONDARY CAUSE)

**문제**:
```
chromadb.errors.NotFoundError: Tenant [default] not found
```

**원인**:
- `docker-compose.dev.yml`에 잘못된 ChromaDB 환경변수 추가:
  ```yaml
  - CHROMA_TENANT=default
  - CHROMA_DATABASE=default
  - CHROMA_HTTP_HOST=chromadb
  - CHROMA_HTTP_PORT=8000
  ```
- Open-WebUI가 환경변수를 읽어 ChromaDB에 연결 시도
- ChromaDB에 `default` tenant가 초기화되지 않음
- 백엔드 초기화 중 예외 발생

**해결**:
- `docker-compose.dev.yml`에서 ChromaDB 환경변수 제거
- Open-WebUI가 기본 설정 사용 (로컬 SQLite 또는 자동 초기화)

### 3. Embedding 모델 로딩 지연 (TERTIARY CAUSE - 실제 원인 아님!)

**초기 가정** (잘못된 판단):
- Embedding 모델 로딩 중 블로킹
- `sentence-transformers/all-MiniLM-L6-v2` 다운로드 지연
- RAG 기능이 백엔드 초기화를 막음

**실제 상황**:
- Embedding 모델 로딩은 정상 완료 (`INFO [open_webui.env] Embedding model set:...`)
- 로딩 후에는 ChromaDB 초기화 단계로 진행
- ChromaDB Tenant 에러로 인해 백엔드가 크래시

**교훈**:
- "마지막 로그 메시지 = 원인"이라고 단정하지 말 것!
- 전체 초기화 플로우를 이해하고 에러 메시지 확인 필요

## Git Diff 분석

### 변경된 파일 확인
```bash
git diff webui/vite.config.ts
git diff docker-compose.dev.yml
```

### 핵심 발견
1. **`vite.config.ts`**: 들여쓰기 에러 (프록시 설정 망가짐)
2. **`docker-compose.dev.yml`**: 잘못된 ChromaDB 환경변수 추가

## 해결 시도 (실패한 방법들)

### 시도 1: RAG 비활성화 환경변수 ❌
```yaml
environment:
  - ENABLE_RAG_WEB_SEARCH=false
  - ENABLE_RAG_HYBRID_SEARCH=false
  - RAG_EMBEDDING_ENGINE=""
```
**결과**: Open-WebUI가 DB 설정 우선, 환경변수 무시

### 시도 2: ChromaDB 환경변수 설정 ❌
```yaml
environment:
  - CHROMA_TENANT=default
  - CHROMA_DATABASE=default
  - CHROMA_HTTP_HOST=chromadb
  - CHROMA_HTTP_PORT=8000
```
**결과**: ChromaDB에 `default` tenant가 없어서 오히려 에러 발생!

### 시도 3: Vector DB 비활성화 ❌
```yaml
environment:
  - CHROMA_DATA_PATH=""
  - VECTOR_DB=none
```
**결과**: Open-WebUI가 환경변수를 무시하고 코드에서 직접 ChromaDB 초기화

## 최종 해결 방법

### ✅ 해결책: ChromaDB tenant/database 자동 생성

Open-WebUI는 ChromaDB를 반드시 사용하도록 하드코딩되어 있음. 
환경변수로 비활성화할 수 없으므로, ChromaDB를 제대로 초기화해야 함.

**문제의 핵심**:
- ChromaDB는 tenant 및 database가 사전에 생성되어 있어야 함
- Open-WebUI는 `default` tenant와 `default` database를 기대
- 하지만 ChromaDB는 비어있는 상태로 시작됨

**해결 방법**:
1. ChromaDB에서 tenant/database 자동 생성 활성화
2. 또는 초기화 스크립트로 수동 생성
3. 또는 프로덕션 모드 사용 (pre-built 이미지는 초기화가 더 안정적)

## 예방 방법

### 1. vite.config.ts 편집 시
- ✅ **항상 Linter/Formatter 사용** (ESLint, Prettier)
- ✅ **저장 전 구문 검증** (VS Code syntax check)
- ✅ **diff 확인** 후 커밋

### 2. 환경변수 추가 시
- ✅ **공식 문서 참조** (Open-WebUI 환경변수 목록)
- ✅ **기본값 먼저 확인** (불필요한 오버라이드 방지)
- ✅ **서비스 로그 확인** (환경변수 적용 여부)

### 3. 디버깅 시
- ✅ **전체 로그 확인** (마지막 메시지만 보지 말 것!)
- ✅ **에러 메시지 정확히 읽기** (ChromaDB Tenant 에러를 놓침!)
- ✅ **Git diff 우선 확인** (최근 변경사항이 원인일 가능성 높음)

## 체크리스트

**WebUI 백엔드가 시작되지 않을 때**:

- [ ] **Git diff 확인** (`git diff webui/`)
- [ ] **vite.config.ts 구문 검증** (들여쓰기, 중괄호)
- [ ] **최신 에러 로그 확인** (`docker logs --tail 100`)
- [ ] **전체 초기화 로그 확인** (Started reloader → Started server process)
- [ ] **환경변수 검증** (`docker exec <container> env | grep CHROMA`)
- [ ] **필요시 컨테이너 재생성** (`docker-compose rm -f webui && docker-compose up -d webui`)

## 참고 자료

- [Open-WebUI 환경변수](https://docs.openwebui.com/getting-started/env-configuration)
- [ChromaDB 초기화](https://docs.trychroma.com/docs/deployment/docker)
- [Vite 프록시 설정](https://vitejs.dev/config/server-options.html#server-proxy)

---

**마지막 업데이트**: 2025-11-25  
**작성자**: AI Assistant  
**카테고리**: Debugging, Root Cause Analysis

