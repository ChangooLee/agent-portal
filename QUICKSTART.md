# 빠른 시작 가이드

## 사전 요구사항

- Docker & Docker Compose (v2.0+)
- Git

## 1. 저장소 클론

```bash
git clone https://github.com/ChangooLee/agent-portal.git
cd agent-portal
```

## 2. 환경 변수 설정

```bash
cp .env.example .env
# 필요시 .env 파일 수정
```

## 3. 서비스 실행

### Kong & Konga만 실행 (Kong Admin UI 테스트)

```bash
# Kong/Konga DB 시작
docker compose up -d kong-db konga-db

# Kong 마이그레이션 실행
docker compose up kong-migrations

# Kong & Konga 시작
docker compose up -d kong konga

# Backend BFF 시작
docker compose build backend
docker compose up -d backend
```

### 전체 서비스 실행

```bash
docker compose up -d
```

## 4. 접근

- **Kong Proxy**: http://localhost:8002
- **Backend BFF**: http://localhost:8000
- **Konga (Kong Admin UI)**: http://localhost:8000/embed/kong-admin (BFF 프록시를 통해)
- **Open-WebUI**: http://localhost:3000 (Admin > Gateway 메뉴에서 Konga 접근)

## 5. Konga 초기 설정

1. Open-WebUI에 admin으로 로그인
2. Admin > Gateway 메뉴 클릭
3. Konga UI에서 초기 관리자 계정 생성 (첫 접속 시)
4. Kong Admin API 연결 설정:
   - Kong Admin URL: `http://kong:8001` (내부 네트워크)
   - Name: `Kong Gateway`

## 주요 설정

### Kong Admin API 보안
- Kong Admin API(8001)는 외부에 노출하지 않음
- BFF 프록시(`/embed/kong-admin`)를 통해서만 접근
- RBAC: admin 역할만 접근 가능

### PostgreSQL 버전
- Kong DB: postgres:15-alpine
- Konga DB: postgres:13-alpine (호환성)

## 문제 해결

### Konga 실행 실패
- PostgreSQL 인증 문제 시 Konga DB를 13으로 유지
- Konga 로그 확인: `docker logs agent-portal-konga-1`

### Backend 오류
- Backend 재빌드: `docker compose build backend`
- Backend 로그 확인: `docker logs agent-portal-backend-1`
