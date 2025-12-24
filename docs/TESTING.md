# Agent Portal 테스트 가이드

## 개요

Agent Portal의 핵심 네트워크 경로와 통합 기능을 검증하는 테스트 절차입니다.

## 테스트 환경 요구사항

- Docker 및 Docker Compose 설치
- `curl` 또는 `httpie` 설치
- `jq` (JSON 파서, 선택사항)
- 포트 3009 사용 가능

## 핵심 네트워크 경로 테스트

### 1. 기본 연결 테스트

**경로**: Browser → WebUI Frontend (3009)

```bash
# WebUI Frontend 접근 확인
curl -I http://localhost:3009/

# 예상 결과: HTTP/1.1 200 OK
```

**검증 포인트**:
- HTML 응답 수신
- 정적 파일 로드 가능
- CORS 헤더 확인

### 2. WebUI Backend 프록시 테스트

**경로**: Browser → BFF (3009) → WebUI Backend (8080)

```bash
# WebUI Backend health check
curl http://localhost:3009/api/webui/health

# 채팅 API 호출 (인증 필요)
curl -X POST http://localhost:3009/api/webui/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"message": "Hello"}'

# 모델 목록 조회
curl http://localhost:3009/api/webui/v1/models
```

**검증 포인트**:
- 인증 토큰 전달 확인
- 응답 정상 수신
- 프록시 헤더 확인

### 3. BFF 직접 API 테스트

**경로**: Browser → BFF (3009)

```bash
# BFF health check
curl http://localhost:3009/health

# 모니터링 API
curl http://localhost:3009/monitoring/traces?limit=10

# MCP 서버 목록
curl http://localhost:3009/mcp/servers

# DataCloud 연결 목록
curl http://localhost:3009/datacloud/connections
```

**검증 포인트**:
- BFF 라우터 정상 동작
- 응답 형식 확인
- 에러 처리 확인

### 4. Kong Gateway 통합 테스트

**경로**: Browser → BFF (3009) → Kong (8000, 내부) → MCP Server

```bash
# 1. MCP 서버 등록 (Kong에 자동 등록)
curl -X POST http://localhost:3009/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-mcp",
    "endpoint_url": "http://example.com/mcp",
    "transport_type": "streamable_http"
  }'

# 2. Kong을 통한 MCP 호출
curl http://localhost:3009/api/mcp/servers/{server_id}/tools \
  -H "X-API-Key: <kong_api_key>"

# 3. API Key 인증 확인
curl http://localhost:3009/api/mcp/servers/{server_id}/tools
# 예상: 401 Unauthorized (API Key 없음)

# 4. Rate Limiting 확인 (100회 이상 요청)
for i in {1..101}; do
  curl http://localhost:3009/api/mcp/servers/{server_id}/tools \
    -H "X-API-Key: <kong_api_key>"
done
# 예상: 429 Too Many Requests
```

**검증 포인트**:
- Kong을 통한 라우팅 정상 동작
- API Key 인증 확인
- Rate Limiting 동작 확인
- Kong Admin에서 서비스/라우트 확인

### 5. DataCloud Kong 통합 테스트

**경로**: Browser → BFF (3009) → Kong (8000, 내부) → Database

```bash
# 1. DB 연결 생성 (Kong에 자동 등록)
curl -X POST http://localhost:3009/datacloud/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-db",
    "db_type": "mariadb",
    "host": "mariadb",
    "port": 3306,
    "database_name": "agent_portal",
    "username": "root",
    "password": "rootpass"
  }'

# 2. Kong을 통한 DB 쿼리 (연결 정보는 Kong을 통해 관리)
curl -X POST http://localhost:3009/datacloud/connections/{conn_id}/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <kong_api_key>" \
  -d '{"query": "SELECT 1"}'

# 3. 연결 정보 암호화 확인
curl http://localhost:3009/datacloud/connections/{conn_id}
# 예상: password 필드가 암호화되어 있음
```

**검증 포인트**:
- Kong을 통한 DB 접근
- 연결 정보 암호화 확인
- 쿼리 실행 정상 동작

### 6. WebSocket 연결 테스트

**경로**: Browser → BFF (3009) → WebUI Backend (8080)

```bash
# WebSocket 연결 테스트 (wscat 사용)
wscat -c ws://localhost:3009/api/webui/ws

# 또는 curl로 WebSocket 업그레이드 확인
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://localhost:3009/api/webui/ws
```

**검증 포인트**:
- WebSocket 연결 수립
- 실시간 메시지 전송/수신
- 연결 유지 확인

## 자동화 테스트 스크립트

### 기동 및 테스트 스크립트

`scripts/start-and-test.sh`를 실행하여 서비스를 기동하고 기본 테스트를 수행합니다.

```bash
./scripts/start-and-test.sh
```

**기능**:
- Docker Compose 서비스 기동
- 서비스 헬스 체크 대기 (최대 120초)
- 기본 연결 테스트 자동 실행
- 실패 시 로그 출력 및 종료

### 회귀 테스트 스크립트

`scripts/regression-test.sh`를 실행하여 모든 핵심 경로를 테스트합니다.

```bash
./scripts/regression-test.sh
```

**기능**:
- 모든 핵심 경로 테스트 실행
- 테스트 결과 리포트 생성 (JSON, HTML)
- 실패한 테스트 상세 로그
- 테스트 실행 시간 측정

### 네트워크 경로 검증 스크립트

`scripts/verify-network-paths.sh`를 실행하여 네트워크 경로를 검증합니다.

```bash
./scripts/verify-network-paths.sh
```

**기능**:
- 각 네트워크 경로별 연결 확인
- 응답 시간 측정
- 에러율 통계
- 네트워크 토폴로지 검증

## 테스트 결과 해석

### 성공 기준

- 모든 핵심 경로 테스트 통과
- 응답 시간 < 1초 (로컬 환경)
- 에러율 0%

### 실패 시 디버깅

1. **서비스 로그 확인**
   ```bash
   docker compose logs backend --tail=100
   docker compose logs webui --tail=100
   docker compose logs kong --tail=100
   ```

2. **포트 확인**
   ```bash
   lsof -i :3009
   docker compose ps
   ```

3. **네트워크 연결 확인**
   ```bash
   docker compose exec backend curl http://webui:8080/health
   docker compose exec backend curl http://kong:8000/status
   ```

## CI/CD 통합

### GitHub Actions 예시

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker compose up -d
      - name: Wait for services
        run: ./scripts/start-and-test.sh
      - name: Run regression tests
        run: ./scripts/regression-test.sh
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results/
```

## 트러블슈팅

### 포트 충돌

```bash
# 포트 사용 확인
lsof -i :3009

# 프로세스 종료
kill -9 <PID>
```

### 서비스 시작 실패

```bash
# 로그 확인
docker compose logs <service> --tail=100

# 컨테이너 재시작
docker compose restart <service>
```

### Kong Gateway 연결 실패

```bash
# Kong 상태 확인
docker compose exec kong kong health

# Kong Admin API 확인
curl http://localhost:8001/services
```

## 참고 자료

- [AGENTS.md](../AGENTS.md) - 아키텍처 상세 설명
- [README.md](../README.md) - 프로젝트 개요
- [Kong Gateway 문서](https://docs.konghq.com/)





