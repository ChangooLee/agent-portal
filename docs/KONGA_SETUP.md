# Konga 설정 가이드

> **목적**: Kong Gateway Admin UI (Konga)를 설정하고 사용하는 방법
> **상태**: 설정 완료 (2025-11-27)

---

## 개요

Konga는 Kong Gateway의 OSS Admin UI입니다. Agent Portal에서 다음 두 가지 방법으로 접근할 수 있습니다:

1. **Agent Portal 임베딩**: `http://localhost:3001/admin/gateway` - "Kong Admin" 탭
2. **직접 접근**: `http://localhost:1337`

---

## 초기 설정

### 1. 관리자 계정 생성

Konga를 처음 시작하면 관리자 계정 생성 화면이 표시됩니다.

**설정 정보**:

| 항목 | 값 |
|------|-----|
| Username | admin |
| Email | lchangoo@gmail.com |
| Password | Cksrn0604! |

### 2. Kong Gateway 연결

관리자 계정 생성 후 Kong 연결 설정이 필요합니다.

**연결 정보**:

| 항목 | 값 |
|------|-----|
| Connection Name | local-kong |
| Kong Admin URL | http://kong:8001 |

> **참고**: Docker 네트워크 내에서 Kong에 접근하므로 `http://kong:8001`을 사용합니다.

---

## Agent Portal 임베딩 화면에서 연결 활성화

Agent Portal의 Gateway 페이지(`/admin/gateway`)에서 Konga를 사용할 때:

1. "Kong Admin" 탭 클릭
2. iframe 내에서 **CONNECTIONS** 메뉴 클릭
3. `local-kong` 연결의 **"activate"** 버튼 클릭
4. 연결이 활성화되면 사이드바에 메뉴들이 나타남

---

## Konga 메뉴 및 기능

### API GATEWAY 메뉴

| 메뉴 | 설명 | 주요 기능 |
|------|------|----------|
| **DASHBOARD** | Kong 연결 상태 및 노드 정보 | 연결 상태, 사용 가능한 플러그인 목록 |
| **INFO** | Kong 버전 및 설정 정보 | 노드 상세 정보, 구성 확인 |
| **SERVICES** | API 서비스 관리 | 서비스 추가/수정/삭제, 호스트/포트 설정 |
| **ROUTES** | 라우팅 규칙 관리 | 경로/메서드 설정, 서비스 연결 |
| **CONSUMERS** | API 사용자 관리 | Consumer 생성, API Key 발급/관리 |
| **PLUGINS** | 플러그인 관리 | 인증(key-auth, jwt), Rate Limiting, CORS 등 |
| **UPSTREAMS** | 로드밸런싱 관리 | 대상 서버 추가, 헬스체크 설정 |
| **CERTIFICATES** | SSL 인증서 관리 | 인증서 업로드, SNI 설정 |

### 현재 등록된 리소스

| 리소스 타입 | 이름 | 설명 |
|-------------|------|------|
| **Service** | `mcp-e13ae9f3-...` | MCP OpenDART 서버 (121.141.60.219) |
| **Consumer** | `mcp-consumer-e13ae9f3-...` | MCP 서버용 API Key 소유자 |
| **Plugin** | `key-auth` | API Key 인증 플러그인 |
| **Plugin** | `rate-limiting` | 요청 제한 플러그인 (분당 60회) |

---

## 주요 작업 가이드

### 1. 새 MCP 서버 등록 시 Kong 리소스 확인

MCP 서버를 Admin UI(`/admin/mcp`)에서 등록하면 자동으로 Kong 리소스가 생성됩니다:

1. **SERVICES** 메뉴에서 새 서비스 확인
2. **ROUTES** 메뉴에서 라우트 확인
3. **CONSUMERS** 메뉴에서 Consumer 및 API Key 확인
4. **PLUGINS** 메뉴에서 key-auth, rate-limiting 플러그인 확인

### 2. API Key 확인/재발급

1. **CONSUMERS** 메뉴 클릭
2. 해당 Consumer 클릭
3. **Credentials** - **API Keys** 탭에서 확인
4. 새 키 발급: **"CREATE API KEY"** 버튼 클릭

### 3. Rate Limiting 설정 변경

1. **PLUGINS** 메뉴 클릭
2. `rate-limiting` 플러그인 클릭
3. 설정 수정:
   - `minute`: 분당 요청 제한
   - `hour`: 시간당 요청 제한
   - `day`: 일간 요청 제한

### 4. 새 플러그인 추가

1. **PLUGINS** 메뉴 - **"ADD GLOBAL PLUGINS"** 또는 서비스/라우트별 추가
2. 사용 가능한 OSS 플러그인:
   - **Authentication**: key-auth, basic-auth, jwt, oauth2
   - **Security**: cors, ip-restriction, bot-detection
   - **Traffic Control**: rate-limiting, request-size-limiting
   - **Logging**: file-log, http-log, tcp-log

---

## 트러블슈팅

### 1. "Connecting to node. Please wait.." 메시지

**원인**: Kong 연결이 비활성화 상태

**해결**:
1. **CONNECTIONS** 메뉴로 이동
2. `local-kong` 연결의 **"activate"** 버튼 클릭

### 2. "No authorization header was found" 에러

**원인**: Konga 세션 만료 또는 로그인 필요

**해결**:
1. Konga 로그인 페이지에서 다시 로그인
2. Email: `lchangoo@gmail.com`
3. Password: `Cksrn0604!`

### 3. iframe에서 Konga가 로드되지 않음

**원인**: 프록시 설정 문제 또는 Konga 컨테이너 미실행

**해결**:

```bash
# Konga 컨테이너 상태 확인
docker ps | grep konga

# 컨테이너 재시작
docker-compose up -d konga
```

### 4. Kong Admin API 연결 실패

**원인**: Kong 컨테이너 미실행 또는 네트워크 문제

**해결**:

```bash
# Kong 상태 확인
docker ps | grep kong

# Kong 헬스체크
curl http://localhost:8001/status

# Kong 재시작
docker-compose restart kong
```

---

## 아키텍처

```
Agent Portal (/admin/gateway)
    |
    +-- 개요 탭 (Services, MCP, API Keys)
    |
    +-- Kong Admin 탭 (iframe)
            |
            v
        Backend BFF (FastAPI)
        /kong-admin-proxy/* -> Konga (http://konga:1337)
            |
            v
        Konga (Port: 1337)
        Kong Admin URL: http://kong:8001
            |
            v
        Kong Gateway
        Admin API: 8001 (내부) | Proxy: 8002 (외부)
```

---

## 관련 문서

- [MCP Gateway 구현 계획](./plans/MCP_GATEWAY_PLAN.md)
- [Kong 설정 파일](../config/kong.yml)
- [README.md](../README.md) - 전체 프로젝트 개요

---

**마지막 업데이트**: 2025-11-27



