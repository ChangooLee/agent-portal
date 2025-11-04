# Konga Database Schema Initialization

Konga의 자동 스키마 생성이 실패하는 경우, 이 스크립트를 사용하여 수동으로 스키마를 생성할 수 있습니다.

## 문제 상황

- Konga의 `sails-postgresql` 어댑터가 PostgreSQL 12+에서 `consrc` 컬럼 관련 오류 발생
- PostgreSQL 11로 다운그레이드 후에도 스키마 자동 생성이 실패

## 해결 방법

### 1. 스키마 수동 생성

```bash
# PostgreSQL에 직접 접속하여 실행
docker exec -i agent-portal-konga-db-1 psql -U konga -d konga < scripts/init-konga-schema.sql

# 또는 psql 명령으로 직접 실행
docker exec agent-portal-konga-db-1 psql -U konga -d konga -f /path/to/init-konga-schema.sql
```

### 2. 설치 프로세스 통합

`docker-compose.yml`에서 Konga DB 볼륨에 스크립트를 마운트하여 자동 실행되도록 설정할 수 있습니다.

## 참고 사항

- Konga는 Sails.js Waterline ORM을 사용하며 camelCase 컬럼명을 사용합니다
- 모든 컬럼명은 큰따옴표로 감싸서 대소문자를 보존해야 합니다
- Konga 재시작 후 스키마가 올바르게 인식되는지 확인하세요

