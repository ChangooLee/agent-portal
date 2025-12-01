# 포트 충돌 방지 가이드

## 문제

Cursor IDE가 개발 포트(3001, 3005, 8124 등)를 동적으로 점유하여 Docker 컨테이너 기동 실패.

## Cursor IDE가 사용하는 포트 (알려진 범위)

| 포트 | 용도 |
|------|------|
| 3001, 3005, 3006 | Language Server, Dev Tools |
| 8124 | Debug Server |

## 안전한 포트 범위

| 서비스 | 권장 포트 | 비고 |
|--------|-----------|------|
| WebUI Vite | 3009 | 3001-3008 피함 |
| ClickHouse | 8125 | 8124 피함 |
| Backend BFF | 8000 | 안전 |
| LiteLLM | 4000 | 안전 |

## 기동 전 체크 스크립트

```bash
#!/bin/bash
# scripts/check-dev-ports.sh

PORTS="3009 8000 8125 4000 3000"

echo "🔍 개발 포트 확인 중..."

for PORT in $PORTS; do
    PROCESS=$(lsof -i :$PORT -t 2>/dev/null)
    if [ -n "$PROCESS" ]; then
        PNAME=$(ps -p $PROCESS -o comm= 2>/dev/null)
        if [[ "$PNAME" == *"Cursor"* ]]; then
            echo "⚠️  포트 $PORT: Cursor IDE 점유 - 다른 포트 사용 권장"
        elif [[ "$PNAME" == *"docker"* ]] || [[ "$PNAME" == *"com.docke"* ]]; then
            echo "✅ 포트 $PORT: Docker 사용 중 (정상)"
        else
            echo "⚠️  포트 $PORT: $PNAME 사용 중"
        fi
    else
        echo "✅ 포트 $PORT: 사용 가능"
    fi
done
```

## 권장 기동 순서

```bash
# 1. 포트 확인
./scripts/check-dev-ports.sh

# 2. 인프라 서비스 먼저 (ClickHouse, MariaDB 등)
docker compose up -d monitoring-clickhouse mariadb redis

# 3. 5초 대기
sleep 5

# 4. Backend 기동
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend

# 5. WebUI 기동
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d webui
```

## 문제 발생 시 확인

```bash
# 포트 사용 현황
lsof -i :3009 -i :8125 -i :8000

# ClickHouse 연결 테스트
curl http://localhost:8125/ping

# Backend 로그 확인
docker logs agent-portal-backend-1 --tail=20
```

## 변경 이력

- 2025-12-01: ClickHouse 8124 → 8125 변경 (Cursor 충돌)
- 2025-12-01: WebUI Vite 3005 → 3009 변경 (Cursor 충돌)

