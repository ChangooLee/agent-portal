# Agent Portal 서버 배포 가이드

> **Purpose**: 서버 환경에서 Agent Portal을 개발 모드로 실행
> **Port**: 3005 (통합 포트)
> **Last Updated**: 2025-12-29

---

## 빠른 시작

### 1. 소스 다운로드

```bash
git clone https://github.com/ChangooLee/agent-portal.git
cd agent-portal
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
nano .env  # 필수 API 키 설정
```

**필수 환경 변수** (`.env` 파일):

```env
LITELLM_MASTER_KEY=sk-your-master-key
OPENROUTER_API_KEY=sk-or-v1-your-key
DART_API_KEY=your-dart-api-key
```

> 상세 환경 변수: [AGENTS.md - Section 4](../AGENTS.md#4-directory-structure)

### 3. 서버용 포트 설정 (3005)

```bash
cat > docker-compose.override.yml << 'EOF'
services:
  backend:
    ports:
      - "3005:3010"
    environment:
      - VITE_HMR_PORT=3005
  webui:
    environment:
      - VITE_HMR_PORT=3005
EOF
```

### 4. 서비스 시작

```bash
docker compose up -d
```

### 5. 상태 확인

```bash
# 컨테이너 상태
docker compose ps

# 헬스 체크
curl http://localhost:3005/health

# 또는 스크립트 사용
./scripts/health-check.sh
```

### 6. 브라우저 접속

```
http://서버IP:3005
```

---

## 서비스 관리

### 로그 확인

```bash
# 전체 로그
docker compose logs -f

# 특정 서비스 로그
docker compose logs -f backend
docker compose logs -f webui
```

### 서비스 재시작

```bash
# 전체 재시작
docker compose restart

# 특정 서비스만
docker compose restart backend
```

### 서비스 중지

```bash
docker compose down
```

### 완전 초기화 (데이터 포함)

```bash
docker compose down -v
docker compose up -d
```

---

## 주요 엔드포인트

| 서비스 | URL | 설명 |
|--------|-----|------|
| Portal UI | http://서버IP:3005 | 메인 UI |
| API Docs | http://서버IP:3005/docs | Swagger UI |
| Health | http://서버IP:3005/health | 헬스 체크 |
| LiteLLM | http://서버IP:4000/health | LLM Gateway |
| Prometheus | http://서버IP:9090 | 메트릭 |

---

## 문제 해결

### 포트 충돌

```bash
lsof -i :3005
kill -9 <PID>
```

> 상세 가이드: [PORT-CONFLICT-GUIDE.md](./PORT-CONFLICT-GUIDE.md)

### 서비스 시작 실패

```bash
docker compose logs <서비스명> --tail=100
```

### 데이터베이스 연결 오류

```bash
# MariaDB
docker compose exec mariadb mariadb -uroot -prootpass -e "SELECT 1;"

# ClickHouse
curl http://localhost:8124/ping
```

---

## 참조 문서

| 문서 | 설명 |
|------|------|
| [AGENTS.md](../AGENTS.md) | 전체 아키텍처, 서비스 카탈로그, API 참조 |
| [README.md](../README.md) | 프로젝트 개요, 철학, 기능 설명 |
| [TESTING.md](./TESTING.md) | 테스트 절차, 검증 포인트 |
| [PORT-CONFLICT-GUIDE.md](./PORT-CONFLICT-GUIDE.md) | 포트 충돌 해결 |
| [LITELLM_SETUP.md](./LITELLM_SETUP.md) | LLM Gateway 설정 |
| [MONITORING_SETUP.md](./MONITORING_SETUP.md) | 모니터링/트레이싱 설정 |

### 스크립트

| 스크립트 | 용도 |
|----------|------|
| `./scripts/health-check.sh` | 서비스 헬스 체크 |
| `./scripts/start-and-test.sh` | 기동 및 기본 테스트 |
| `./scripts/regression-test.sh` | 회귀 테스트 |

---

## 서비스 포트 참조

| 서비스 | 외부 | 내부 | 용도 |
|--------|------|------|------|
| backend | **3005** | 3010 | BFF (메인 진입점) |
| litellm | 4000 | 4000 | LLM Gateway |
| mariadb | 3306 | 3306 | 앱 DB |
| clickhouse | 8124 | 8123 | 트레이스 저장 |
| prometheus | 9090 | 9090 | 메트릭 |
| redis | 6379 | 6379 | 캐시 |

> 전체 포트 목록: [AGENTS.md - Section 3.1](../AGENTS.md#31-core-services)
