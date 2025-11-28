# Bug Fixes Log

## 2025-11-28: 모니터링 화면 데이터 표시 안 됨

### 문제
모니터링 화면에서 데이터가 0으로 표시됨

### 원인 (2가지)

#### 1. ClickHouse 쿼리 구문 오류
`monitoring_adapter.py`에서 존재하지 않는 컬럼 `project_id` 직접 참조

```sql
-- ❌ 잘못된 쿼리 (project_id 컬럼이 없음)
WHERE (ResourceAttributes['project_id'] = '{project_id}' 
       OR ResourceAttributes['project_id'] = '' 
       OR project_id = '')  -- ← 이 부분이 문제

-- ✅ 올바른 쿼리
WHERE (ResourceAttributes['project_id'] = '{project_id}' 
       OR ResourceAttributes['project_id'] = '')
```

#### 2. WebSocket URL 하드코딩
`webui/src/lib/monitoring/api-client.ts`에서 WebSocket URL이 `ws://localhost:8000`으로 하드코딩되어 Docker 환경에서 작동 안 함

```typescript
// ❌ 잘못된 설정
const WS_BASE_URL = 'ws://localhost:8000/api/monitoring';

// ✅ 올바른 설정 (동적 URL)
const WS_BASE_URL = typeof window !== 'undefined' 
  ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/monitoring`
  : 'ws://localhost:3005/api/monitoring';
```

### 수정 파일
- `backend/app/services/monitoring_adapter.py`: 8곳에서 `OR project_id = ''` 제거
- `webui/src/lib/monitoring/api-client.ts`: WebSocket URL 동적으로 변경

### 테스트
1. Backend API 호출: `curl http://localhost:8000/api/monitoring/metrics?...`
2. 브라우저에서 모니터링 화면 확인: http://localhost:3005/admin/monitoring

### 예방 조치
1. ClickHouse 쿼리 작성 시 `DESCRIBE otel_2.otel_traces`로 컬럼 존재 여부 확인
2. WebSocket/API URL은 환경에 따라 동적으로 설정
3. Docker 환경에서는 `localhost` 대신 서비스 이름 또는 동적 URL 사용

---

## ClickHouse otel_traces 테이블 주요 컬럼

```sql
-- 직접 접근 가능한 컬럼
TraceId, SpanId, SpanName, ServiceName, Duration, Timestamp, StatusCode

-- Map 타입 컬럼 (키로 접근)
ResourceAttributes['project_id']
ResourceAttributes['service.name']
SpanAttributes['llm.usage.total_tokens']
SpanAttributes['gen_ai.usage.prompt_cost']
```

**주의**: `project_id`는 직접 컬럼이 아니라 `ResourceAttributes` Map 안에 있음

---

## 2025-11-28: Konga (Kong Admin UI) iframe 표시 안 됨

### 문제
Gateway 화면에서 "Kong Admin" 탭 클릭 시 `{"detail":"Not Found"}` 오류

### 원인
`vite.config.ts`에 `/api/embed` 프록시 설정 누락

```
요청 흐름:
Frontend → /api/embed/kong-admin/ → Vite 프록시 → ?

문제:
- /api/embed 규칙 없음
- /api 규칙이 WebUI Backend(8080)로 전달
- WebUI Backend에 /embed 라우트 없음 → 404
```

### 수정
`webui/vite.config.ts`에 프록시 추가:

```typescript
// Embed Proxy (Kong Admin, Langfuse, Helicone) → FastAPI BFF (포트 8000)
'/api/embed': {
    target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/embed/, '/embed')
},
```

### 테스트
```bash
# 프록시 정상 작동 확인
curl -s http://localhost:3005/api/embed/kong-admin/ -o /dev/null -w "%{http_code}"
# → 200
```

### 예방 조치
1. 새 Backend API 라우트 추가 시 `vite.config.ts` 프록시 설정도 확인
2. `/api/*` 규칙이 마지막에 있으므로, 새 규칙은 그 위에 추가
3. Vite 프록시 규칙 순서: 구체적인 경로 → 일반적인 경로
