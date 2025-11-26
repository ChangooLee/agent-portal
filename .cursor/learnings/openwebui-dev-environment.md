# Open-WebUI 개발 환경 설정 및 문제 해결

## 2025-11-19: "지원되지 않는 방식(프론트엔드만)" 에러 해결

### 문제 상황

**에러 메시지**:
```
SFN AI Portal 백엔드가 필요합니다.

이런! 지원되지 않는 방식(프론트엔드만)을 사용하고 계십니다. 
백엔드에서 WebUI를 제공해주세요.
```

**근본 원인**:
- Open-WebUI는 프론트엔드와 백엔드가 함께 실행되어야 합니다
- 개발 환경에서 Vite 개발 서버(3001)와 백엔드(8080)가 분리되어 있음
- Vite 프록시가 백엔드 API를 제대로 프록시하지 못함

### 해결 방법

**1. Vite 프록시 설정 수정** (`webui/vite.config.ts`):

```typescript
// ⚠️ CRITICAL: Docker 컨테이너 내부에서는 127.0.0.1 사용
'/api': {
  target: 'http://127.0.0.1:8080',
  changeOrigin: true,
  ws: true  // WebSocket 지원
},
'/ollama': {
  target: 'http://127.0.0.1:8080',
  changeOrigin: true
},
'/openai': {
  target: 'http://127.0.0.1:8080',
  changeOrigin: true
},
'/health': {
  target: 'http://127.0.0.1:8080',
  changeOrigin: true
}
```

**2. 개발 환경 재시작**:

```bash
# 컨테이너 중지
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down webui

# 실행 권한 확인
chmod +x webui/dev-start.sh

# 개발 환경 시작
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d webui

# 로그 확인 (백엔드와 프론트엔드 모두 시작되는지 확인)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f webui
```

**3. 정상 동작 확인**:

```bash
# 백엔드 health 체크 (포트 8080)
curl http://localhost:8080/health
# 응답: {"status":true}

# Vite 프록시 health 체크 (포트 3001)
curl http://localhost:3001/health
# 응답: {"status":true}
```

### 개발 환경 구조

```
Docker Container (webui)
├── Vite Dev Server (포트 3001) ← 브라우저 접속
│   └── Proxy: /api → http://127.0.0.1:8080
│   └── Proxy: /ollama → http://127.0.0.1:8080
│   └── Proxy: /openai → http://127.0.0.1:8080
│   └── Proxy: /health → http://127.0.0.1:8080
│   └── Proxy: /api/news → http://backend:8000
│   └── Proxy: /api/proxy → http://backend:8000
└── Open-WebUI Backend (포트 8080)
    └── FastAPI + SQLite

External:
└── Backend BFF (포트 8000)
    └── News, AgentOps, Proxy APIs
```

### 포트 구분

| 서비스 | 포트 | 접속 방법 | 용도 |
|--------|------|-----------|------|
| **Vite Dev Server** | **3001** | http://localhost:3001 | **개발용 프론트엔드** (HMR) |
| Open-WebUI Backend | 8080 | http://localhost:8080 | 내부 API (Vite 프록시됨) |
| Backend BFF | 8000 | http://localhost:8000 | News, AgentOps, Proxy |
| LiteLLM | 4000 | http://localhost:4000 | LLM Gateway |

### 체크리스트: 개발 환경 문제 해결

**"프론트엔드만 사용" 에러 발생 시**:
- [ ] 백엔드가 실행 중인지 확인: `curl http://localhost:8080/health`
- [ ] Vite 프록시가 작동하는지 확인: `curl http://localhost:3001/health`
- [ ] Vite 로그에서 프록시 에러 확인: `docker-compose logs webui | grep "proxy error"`
- [ ] `vite.config.ts`의 프록시 설정 확인 (target: `http://127.0.0.1:8080`)
- [ ] 개발 환경 재시작: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart webui`

**백엔드가 시작되지 않을 때**:
- [ ] `dev-start.sh`에 실행 권한이 있는지 확인: `chmod +x webui/dev-start.sh`
- [ ] PYTHONPATH 설정 확인: `webui/dev-start.sh` line 27
- [ ] 백엔드 로그 확인: `docker-compose logs webui | grep -E "ERROR|Exception"`
- [ ] SQLite 데이터베이스 권한 확인: `webui/backend/data/webui.db`

**Vite 프록시 에러 발생 시**:
- [ ] 백엔드 포트 확인: `8080` (내부)
- [ ] Docker 환경 변수 확인: `DOCKER_ENV=true`
- [ ] 프록시 target 확인: `http://127.0.0.1:8080` (Docker 컨테이너 내부 통신)
- [ ] changeOrigin 설정 확인: `changeOrigin: true`

### 주의 사항

1. **Docker 컨테이너 내부 통신**:
   - Vite와 백엔드가 같은 컨테이너에서 실행됨
   - `localhost` 또는 `127.0.0.1` 사용 (서비스 이름 X)
   - 다른 컨테이너 통신 시에만 서비스 이름 사용 (예: `http://backend:8000`)

2. **프로덕션 vs 개발 환경**:
   - **프로덕션**: 프론트엔드 빌드 → 백엔드가 정적 파일 제공
   - **개발**: Vite 개발 서버 → 백엔드 API 프록시

3. **Hot Module Replacement (HMR)**:
   - 소스 코드 수정 → 브라우저 자동 새로고침
   - `webui/src/` 하위 모든 파일 감지
   - Docker 볼륨 마운트로 실시간 반영

### 프로덕션 환경으로 전환

개발이 완료되면 프로덕션 환경으로 전환:

```bash
# 개발 환경 중지
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down webui

# 프로덕션 환경 시작
docker-compose up -d webui

# 접속: http://localhost:3000 (프로덕션 포트)
```

### 참고 파일

- `webui/vite.config.ts` - Vite 프록시 설정
- `webui/dev-start.sh` - 개발 환경 시작 스크립트
- `webui/Dockerfile.dev` - 개발 환경 Docker 이미지
- `docker-compose.dev.yml` - 개발 환경 오버라이드 설정
- `.cursor/rules/backend-api.mdc` - 백엔드 개발 가이드

---

**학습 시점**: 2025-11-19  
**해결 시간**: 30분  
**재사용 가능성**: ⭐⭐⭐⭐⭐ (Open-WebUI 개발 환경 필수)

