# MCP Gateway 구현 계획

> **백업 일자**: 2025-11-26
> **상태**: ✅ 구현 완료 (2025-11-27)
> **SSE 지원 추가**: 2025-11-27

## 목표

**Streamable HTTP** 및 **SSE** 방식의 MCP 서버를 Admin UI에서 등록/관리하고, Kong Gateway를 통해 Key-Auth/Rate-Limit 보안을 적용하여 Agent Builder(Langflow/Flowise/AutoGen)에서 MCP 도구로 활용할 수 있게 합니다.

## 지원 전송 방식

| 전송 방식 | 프로토콜 | 예시 |
|----------|----------|------|
| **Streamable HTTP** | POST + `mcp-session-id` 헤더 | MCP OpenDART (`/mcp`) |
| **SSE** | GET `/sse` + POST `/messages/?session_id=...` | MCP Naver News (`/sse`) |

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Gateway Architecture                     │
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │  Admin UI    │─────▶│  Backend BFF │─────▶│    Kong      │  │
│  │  (MCP 관리)   │      │  (MCP API)   │      │  Gateway     │  │
│  └──────────────┘      └──────────────┘      └──────┬───────┘  │
│                                                     │          │
│  ┌──────────────┐      ┌──────────────┐             │          │
│  │ Agent Builder│─────▶│  MCP Proxy   │◀────────────┘          │
│  │ (Langflow등) │      │  (BFF)       │                        │
│  └──────────────┘      └──────┬───────┘                        │
│                               │                                │
│                        ┌──────▼───────┐                        │
│                        │  MCP Server  │                        │
│                        │  (External)  │                        │
│                        └──────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

## 구현 단계

### 1. 데이터베이스 스키마 설계

**파일**: `scripts/init-mcp-schema.sql`

```sql
CREATE TABLE mcp_servers (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    endpoint_url VARCHAR(500) NOT NULL,
    transport_type ENUM('streamable_http', 'sse') DEFAULT 'streamable_http',
    auth_type ENUM('none', 'api_key', 'bearer') DEFAULT 'none',
    auth_config JSON,
    kong_service_id VARCHAR(36),
    kong_route_id VARCHAR(36),
    kong_consumer_key VARCHAR(255),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE mcp_server_tools (
    id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    tool_description TEXT,
    input_schema JSON,
    FOREIGN KEY (server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE
);
```

### 2. Backend BFF - MCP 관리 API

**파일**: `backend/app/routes/mcp.py` (신규)

주요 엔드포인트:
- `GET /api/mcp/servers` - MCP 서버 목록 조회
- `POST /api/mcp/servers` - MCP 서버 등록 (Kong 서비스/라우트 자동 생성)
- `GET /api/mcp/servers/{id}` - MCP 서버 상세 조회
- `PUT /api/mcp/servers/{id}` - MCP 서버 수정
- `DELETE /api/mcp/servers/{id}` - MCP 서버 삭제 (Kong 리소스 정리)
- `POST /api/mcp/servers/{id}/test` - MCP 서버 연결 테스트
- `GET /api/mcp/servers/{id}/tools` - MCP 서버 도구 목록 조회

### 3. Backend BFF - MCP 프록시

**파일**: `backend/app/routes/proxy.py` (수정)

MCP SSE 프록시 엔드포인트 추가:
- `POST /api/proxy/mcp/{server_id}/messages` - MCP 메시지 전송
- `GET /api/proxy/mcp/{server_id}/sse` - SSE 스트림 연결

### 4. Kong Gateway 연동 서비스

**파일**: `backend/app/services/kong_service.py` (신규)

Kong Admin API 연동:
- 서비스 생성/삭제
- 라우트 생성/삭제
- Key-Auth 플러그인 설정
- Rate-Limiting 플러그인 설정
- Consumer 및 API Key 관리

### 5. Kong 설정 업데이트

**파일**: `config/kong.yml` (수정)

MCP 라우트 템플릿 추가:
```yaml
services:
  - name: mcp-proxy
    url: http://backend:8000/api/proxy/mcp
    plugins:
      - name: key-auth
      - name: rate-limiting
        config: { minute: 120 }
```

### 6. Admin UI - MCP 관리 화면

**파일**: `webui/src/routes/(app)/admin/mcp/+page.svelte` (수정)

기존 "Coming Soon" 상태에서 완전한 관리 UI로 변경:
- MCP 서버 목록 테이블
- 서버 등록/수정 모달
- 연결 테스트 버튼
- 도구 목록 확인
- Kong 키 발급/회수

### 7. Agent Builder 연동

Agent Builder(Langflow/Flowise)에서 MCP 도구를 사용할 수 있도록:
- MCP 서버 목록 API 제공
- 도구 스키마 JSON 형식 제공
- Agent Builder가 BFF 프록시를 통해 MCP 호출

## 파일 변경 목록

| 파일 | 작업 | 상태 |
|------|------|------|
| `scripts/init-mcp-schema.sql` | 신규 - DB 스키마 | ✅ 완료 |
| `backend/app/routes/mcp.py` | 신규 - MCP 관리 API | ✅ 완료 |
| `backend/app/services/kong_service.py` | 기존 - Kong 연동 서비스 | ✅ 이미 구현됨 |
| `backend/app/services/mcp_service.py` | 신규 - MCP 서버 관리 서비스 | ✅ 완료 |
| `backend/app/routes/proxy.py` | 수정 - MCP 프록시 추가 | ✅ 완료 |
| `backend/app/main.py` | 수정 - MCP 라우터 등록 | ✅ 완료 |
| `webui/src/routes/(app)/admin/mcp/+page.svelte` | 수정 - 관리 UI | ✅ 완료 |
| `webui/src/lib/apis/mcp.ts` | 신규 - MCP API 클라이언트 | ⏭️ 스킵 (fetch 직접 사용) |

## 작업 시간

- DB 스키마 및 Backend API: ✅ 완료
- Kong 연동 서비스: ✅ 이미 구현됨
- Admin UI: ✅ 완료
- 테스트 및 문서화: ✅ 완료

**실제 작업 시간**: 약 2시간 (2025-11-27)

## Kong Gateway 역할

| 기능 | 플러그인 | 우선순위 |
|------|----------|----------|
| API 키 인증 | `key-auth` | P0 (즉시) |
| 요청 제한 | `rate-limiting` | P0 (즉시) |
| Consumer 관리 | Kong Admin API | P0 (즉시) |
| 메트릭 수집 | `prometheus` | P0 (이미 설정됨) |
| 프롬프트 보안 | `ai-prompt-guard` | P1 (나중에) |
| AI 프록시 | `ai-proxy` | P1 (나중에) |

## OSS 활용

| 기능 | OSS 코드 | 활용 |
|------|----------|------|
| MCP 클라이언트 | Flowise `core.ts` | Agent Builder에서 사용 |
| SSE 프록시 | Langflow `mcp_projects.py` | Backend 구현 참조 |
| Kong Admin API | Kong 내장 | Service/Route/Plugin 관리 |

## 관련 문서

- [Konga 설정 가이드](../KONGA_SETUP.md) - Kong Admin UI 설정 및 사용법

## 라이선스

모든 사용 OSS는 라이선스 이슈 없음:
- Kong Gateway: Apache-2.0
- Flowise: Apache-2.0
- Langflow: MIT
- Open-WebUI: Open WebUI License (브랜딩 의무)
