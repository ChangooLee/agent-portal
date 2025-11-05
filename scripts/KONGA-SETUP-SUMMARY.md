# Konga 설정 완료 요약

## 완료된 작업

### 1. PostgreSQL 11 전환
- Konga의 `sails-postgresql` 어댑터 호환성을 위해 PostgreSQL 11로 다운그레이드
- PostgreSQL 12+에서 제거된 `consrc` 컬럼 참조 문제 해결

### 2. 스키마 수동 생성
- Konga의 자동 스키마 생성 실패로 수동 생성 스크립트 작성
- 생성된 테이블:
  - `konga_users` - 사용자 정보
  - `konga_connections` - Kong 연결 설정
  - `konga_snapshots` - 스냅샷 데이터
  - `konga_settings` - Konga 설정

### 3. 설치 프로세스 통합
- `scripts/init-konga-schema.sql` - 스키마 생성 SQL 스크립트
- `scripts/README-KONGA.md` - 설치 가이드
- `docker-compose.yml` - `MIGRATE=safe`, `KONGA_SEED=false` 설정

## 현재 상태

### 실행 중인 서비스
- ✅ PostgreSQL 11-alpine (konga-db)
- ✅ Konga 컨테이너 실행 중
- ✅ 스키마 생성 완료 (4개 테이블)

### 알려진 문제
- Konga의 seed 데이터 삽입 시 "null value in column key" 오류
- `KONGA_SEED=false`로 설정했으나 여전히 seed 시도 중
- Konga HTTP 응답 없음 (000)

## 해결 방법

### 스키마 수동 생성
```bash
# 스키마 생성
docker exec -i agent-portal-konga-db-1 psql -U konga -d konga < scripts/init-konga-schema.sql

# Konga 재시작
docker compose restart konga
```

### 추가 조치 필요 사항
1. Konga의 seed 프로세스 완전 비활성화 방법 확인
2. Konga 커뮤니티 패치 확인 및 적용
3. Konga 초기 설정 데이터 수동 삽입 고려

## 다음 단계
1. Konga GitHub 이슈 확인
2. 커뮤니티 워크어라운드 적용
3. Konga 초기화 프로세스 수정


