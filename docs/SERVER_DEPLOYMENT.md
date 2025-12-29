# Agent Portal 서버 배포 가이드

> **Purpose**: 서버 환경에서 Agent Portal을 개발 모드로 실행하기 위한 가이드
> **Port**: 3005 (통합 포트)
> **Last Updated**: 2025-12-29

---

## 목차

1. [사전 요구사항](#1-사전-요구사항)
2. [환경 설정](#2-환경-설정)
3. [서비스 시작](#3-서비스-시작)
4. [서비스 확인](#4-서비스-확인)
5. [문제 해결](#5-문제-해결)
6. [참조 문서](#6-참조-문서)

---

## 1. 사전 요구사항

### 1.1 시스템 요구사항

- Docker 24.0+ 
- Docker Compose v2.20+
- 최소 16GB RAM (권장 32GB)
- 최소 50GB 디스크 공간

### 1.2 Docker 설치 확인

```bash
docker --version
docker compose version
```

### 1.3 포트 확인

3005 포트가 사용 가능한지 확인:

```bash
lsof -i :3005
# 또는
netstat -tlnp | grep 3005
```

---

## 2. 환경 설정

### 2.1 소스 코드 다운로드

```bash
git clone https://github.com/ChangooLee/agent-portal.git
cd agent-portal
```

### 2.2 환경 변수 설정

`.env` 파일 생성:

```bash
cp .env.example .env
```

필수 환경 변수 설정:

```bash
# .env 파일 편집
nano .env
```

**필수 환경 변수:**

```env
# LiteLLM Master Key (필수)
LITELLM_MASTER_KEY=sk-your-master-key

# OpenRouter API Key (LLM 호출용)
OPENROUTER_API_KEY=sk-or-v1-your-key

# OpenAI API Key (선택)
OPENAI_API_KEY=sk-your-openai-key

# Anthropic API Key (선택)
ANTHROPIC_API_KEY=sk-ant-your-key

# DART API Key (기업공시 분석용)
DART_API_KEY=your-dart-api-key

# MCP Storage Path (서버 경로에 맞게 수정)
MCP_STORAGE_PATH=/data/mcp

# News Data Path (선택)
NEWS_DATA_PATH_HOST=/data/news
```

### 2.3 서버용 포트 설정 (3005)

서버에서 3005 포트를 사용하려면 `docker-compose.override.yml` 생성:

```bash
cat > docker-compose.override.yml << 'EOF'
# Server Override - Port 3005
# 서버 환경용 포트 설정

services:
  backend:
    ports:
      - "3005:3010"    # 외부:3005 -> 내부:3010
    environment:
      - VITE_HMR_PORT=3005
      
  webui:
    environment:
      - VITE_HMR_PORT=3005
EOF
```

> **Note**: 이 파일은 기본 `docker-compose.yml`의 설정을 오버라이드합니다.

---

## 3. 서비스 시작

### 3.1 전체 서비스 시작

```bash
# 개발 모드로 시작 (백그라운드)
docker compose up -d

# 로그 확인
docker compose logs -f
```

### 3.2 서비스 시작 순서

서비스는 자동으로 의존성 순서에 따라 시작됩니다:

1. **Layer 1 (Infrastructure)**: mariadb, redis
2. **Layer 2 (Core)**: litellm, kong
3. **Layer 3 (Observability)**: otel-collector, clickhouse, prometheus
4. **Layer 4 (Application)**: backend, chromadb, minio
5. **Layer 5 (Frontend)**: webui

### 3.3 특정 서비스만 재시작

```bash
# 백엔드만 재시작
docker compose restart backend

# 프론트엔드만 재시작
docker compose restart webui

# 전체 재빌드 후 시작
docker compose build --no-cache && docker compose up -d
```

---

## 4. 서비스 확인

### 4.1 서비스 상태 확인

```bash
# 모든 서비스 상태
docker compose ps

# 헬스 체크 스크립트
./scripts/health-check.sh
```

### 4.2 주요 엔드포인트 확인

| 서비스 | URL | 설명 |
|--------|-----|------|
| Portal UI | http://서버IP:3005 | 메인 UI |
| API Docs | http://서버IP:3005/docs | FastAPI Swagger |
| Health | http://서버IP:3005/health | 헬스 체크 |
| LiteLLM | http://서버IP:4000/health | LLM Gateway 상태 |
| Prometheus | http://서버IP:9090 | 메트릭 모니터링 |

### 4.3 기본 테스트

```bash
# 헬스 체크
curl http://localhost:3005/health

# API 문서 확인
curl http://localhost:3005/docs

# MCP 서버 목록
curl http://localhost:3005/api/mcp/servers
```

---

## 5. 문제 해결

### 5.1 포트 충돌

```bash
# 3005 포트 사용 프로세스 확인
lsof -i :3005

# 프로세스 종료
kill -9 <PID>
```

### 5.2 서비스 시작 실패

```bash
# 로그 확인
docker compose logs <서비스명> --tail=100

# 예: 백엔드 로그
docker compose logs backend --tail=100

# 전체 재시작
docker compose down
docker compose up -d
```

### 5.3 데이터베이스 연결 오류

```bash
# MariaDB 상태 확인
docker compose exec mariadb mariadb -uroot -prootpass -e "SELECT 1;"

# ClickHouse 상태 확인
curl http://localhost:8124/ping
```

### 5.4 MCP 서버 연결 오류

```bash
# MCP 볼륨 상태 확인
docker volume inspect agent-portal_mcp_storage

# MCP 서버 로그 확인
docker compose logs backend --tail=100 | grep -i mcp
```

### 5.5 완전 초기화 (주의!)

```bash
# 모든 컨테이너, 볼륨 삭제 후 재시작
docker compose down -v
docker compose up -d
```

---

## 6. 참조 문서

### 프로젝트 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| AGENTS.md | `/AGENTS.md` | 전체 아키텍처 참조 |
| README.md | `/README.md` | 프로젝트 개요 |
| TESTING.md | `/docs/TESTING.md` | 테스트 가이드 |
| PORT-CONFLICT-GUIDE.md | `/docs/PORT-CONFLICT-GUIDE.md` | 포트 충돌 해결 |
| LITELLM_SETUP.md | `/docs/LITELLM_SETUP.md` | LLM Gateway 설정 |
| MONITORING_SETUP.md | `/docs/MONITORING_SETUP.md` | 모니터링 설정 |

### 서비스 포트 참조

| 서비스 | 외부 포트 | 내부 포트 | 용도 |
|--------|----------|----------|------|
| backend (BFF) | 3005 | 3010 | 메인 진입점 |
| litellm | 4000 | 4000 | LLM Gateway |
| mariadb | 3306 | 3306 | 앱 DB |
| clickhouse | 8124 | 8123 | 트레이스 저장 |
| prometheus | 9090 | 9090 | 메트릭 |
| redis | 6379 | 6379 | 캐시 |
| minio | 9000/9001 | 9000/9001 | 오브젝트 스토리지 |

### Docker Compose 파일

| 파일 | 용도 |
|------|------|
| `docker-compose.yml` | 기본 개발 환경 |
| `docker-compose.override.yml` | 서버 환경 오버라이드 (포트 3005) |
| `docker-compose.prod.yml` | 프로덕션 환경 |

---

## 빠른 시작 요약

```bash
# 1. 소스 다운로드
git clone https://github.com/ChangooLee/agent-portal.git
cd agent-portal

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에서 API 키들 설정

# 3. 서버용 포트 설정 (3005)
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

# 4. 서비스 시작
docker compose up -d

# 5. 상태 확인
docker compose ps
curl http://localhost:3005/health

# 6. 브라우저에서 접속
# http://서버IP:3005
```

---

**Last Updated**: 2025-12-29

