# MCP 연동 가이드

## 📋 요약

Agent Portal은 **Streamable HTTP**와 **SSE(Server-Sent Events)** 두 가지 방식의 MCP 서버를 모두 지원합니다.

### Agent Portal MCP Gateway 지원 현황 (2025-11-27)

| 전송 방식 | 지원 여부 | 예시 |
|----------|----------|------|
| **Streamable HTTP** | ✅ 지원 | MCP OpenDART (`/mcp`) |
| **SSE** | ✅ 지원 | MCP Naver News (`/sse`) |

---

## 🆕 Agent Portal MCP Gateway (권장)

Agent Portal의 MCP Gateway를 통해 MCP 서버를 등록하고 관리할 수 있습니다.

### 접속 방법

1. **Admin 페이지 접속**: `http://localhost:3009/admin/mcp`
2. **서버 추가** 버튼 클릭
3. 서버 정보 입력:
   - **이름**: MCP 서버 이름
   - **엔드포인트 URL**: MCP 서버 URL (예: `http://example.com:8089/mcp`)
   - **전송 타입**: `streamable_http` 또는 `sse`
   - **설명**: 서버 설명 (선택)
4. **추가** 버튼 클릭
5. **연결 테스트** 버튼으로 연결 확인

### 지원 기능

- ✅ MCP 서버 등록/수정/삭제
- ✅ 연결 테스트 및 도구 목록 조회
- ✅ Kong Gateway 자동 연동 (API Key 인증, Rate Limiting)
- ✅ 사용자/그룹별 권한 관리
- ✅ Streamable HTTP 및 SSE 전송 방식 지원

---

## 📚 Open-WebUI 기본 MCP 연동

Open-WebUI는 **Streamable HTTP** 방식의 MCP를 기본 지원하며, **SSE(Server-Sent Events)** 기반 MCP 서버는 `mcpo` 프록시를 통해 연동할 수 있습니다.

---

## 🚀 방법 1: Streamable HTTP 직접 연결 (권장)

Open-WebUI는 버전 0.6.31+부터 Streamable HTTP 기반 MCP 서버를 직접 지원합니다. 이 방법이 가장 간단하고 빠릅니다.

### 설정 방법

1. **관리자 설정 접근**
   - Open-WebUI 관리자 페이지 → Settings → External Tool Servers

2. **새 서버 추가**
   - "Add Server" 또는 "+" 버튼 클릭
   - **URL**: MCP 서버의 Streamable HTTP 엔드포인트 URL 입력
     - 예: `http://localhost:8000` 또는 `https://mcp-server.example.com`
   - **Path**: OpenAPI 스펙 경로 (일반적으로 `openapi.json` 또는 MCP 서버가 제공하는 스펙 경로)
   - **Auth Type**: 
     - `Bearer`: API 키 사용
     - `Session`: 시스템 사용자 세션 인증
   - **API Key**: Bearer 인증 시 API 키 입력 (선택사항)

3. **연결 확인**
   - "Verify Connection" 버튼으로 연결 테스트
   - 성공 시 "Connection successful" 메시지 표시

4. **설정 저장**
   - "Save" 클릭
   - Open-WebUI 재시작 (필요한 경우)

### Streamable HTTP MCP 서버 요구사항

- OpenAPI 스펙 제공 (`openapi.json` 또는 유사한 엔드포인트)
- HTTP POST 요청으로 도구 실행 지원
- JSON 형식 요청/응답

### 장점

- ✅ 프록시 없이 직접 연결
- ✅ 설정 간단
- ✅ 낮은 지연시간
- ✅ Open-WebUI 기본 지원

---

## 🔄 방법 2: SSE를 mcpo로 변환 (SSE 서버용)

Open-WebUI는 **SSE(Server-Sent Events)** 기반 MCP 서버와 직접 연동하는 기능을 제공하지 않습니다. 따라서 `mcpo`를 사용하여 SSE 기반 MCP 서버를 OpenAPI 호환 HTTP 서버로 변환한 후, Open-WebUI의 기존 OpenAPI 통합 기능을 통해 연동하는 것이 가장 효율적입니다.

### 1. mcpo 설치

```bash
pip install mcpo
```

### 2. mcpo 실행

SSE 기반 MCP 서버를 OpenAPI 호환 서버로 변환:

```bash
mcpo --port 8000 \
     --api-key "your_api_key" \
     --server-type "sse" \
     --header '{"Authorization": "Bearer token"}' \
     http://your_mcp_server_url/sse
```

**파라미터 설명**:
- `--port`: mcpo가 실행될 포트 번호 (예: 8000)
- `--api-key`: 인증에 사용할 API 키 (선택사항)
- `--server-type`: 서버 타입 (`sse` 또는 `streamable-http`)
- `--header`: 필요한 헤더 정보 (JSON 형식)
- 마지막 인자: MCP 서버의 SSE 엔드포인트 URL

### 3. Open-WebUI에서 변환된 서버 추가

**방법 1의 설정 방법과 동일**:
- Settings → External Tool Servers → Add Server
- **URL**: `mcpo`가 실행 중인 URL (예: `http://localhost:8000`)
- **Path**: `openapi.json` (mcpo가 자동 생성)
- **Auth Type**: Bearer 또는 Session
- **API Key**: mcpo 실행 시 지정한 API 키 (있는 경우)

---

## 🔍 기술적 배경

### Open-WebUI의 MCP 지원 현황

- ✅ **Streamable HTTP**: 기본 지원 (버전 0.6.31+) - **직접 연결 가능**
- ❌ **SSE (Server-Sent Events)**: 직접 지원 안 함 - **mcpo 프록시 필요**
- ✅ **OpenAPI 서버 통합**: 완전 지원

### 방법 비교

| 방법 | 연결 방식 | 설정 복잡도 | 성능 | 권장 상황 |
|------|----------|------------|------|----------|
| **방법 1: Streamable HTTP** | 직접 연결 | ⭐ 낮음 | ⭐⭐⭐ 높음 | Streamable HTTP MCP 서버 |
| **방법 2: SSE + mcpo** | 프록시 경유 | ⭐⭐ 중간 | ⭐⭐ 중간 | SSE MCP 서버만 있는 경우 |

### mcpo의 역할

`mcpo`는 SSE MCP 서버를 OpenAPI 호환 HTTP 서버로 변환하는 프록시 역할을 합니다:

```
SSE MCP Server → mcpo (프록시) → OpenAPI HTTP Server → Open-WebUI
```

이를 통해 Open-WebUI의 기존 OpenAPI 통합 인프라를 그대로 활용할 수 있습니다.

---

## 📚 참고 자료

- **mcpo GitHub**: https://github.com/open-webui/mcpo
- **Open-WebUI MCP 문서**: https://docs.openwebui.com/features/mcp/
- **Open-WebUI OpenAPI 서버 문서**: https://docs.openwebui.com/openapi-servers/mcp/
- **Open-WebUI MCP SSE 이슈**: https://github.com/open-webui/open-webui/issues/12820

---

## 🔄 대안 방법 (고급)

만약 `mcpo`를 사용하지 않고 직접 SSE를 구현하려면:

1. **Langflow/LiteLLM 참고**: 
   - `langflow/src/backend/base/langflow/api/v1/mcp.py` (SSE 엔드포인트 구현 예시)
   - `litellm/litellm/proxy/_experimental/mcp_server/sse_transport.py` (SSE 트랜스포트 구현)

2. **FastAPI + sse-starlette 사용**:
   ```python
   from sse_starlette import EventSourceResponse
   from mcp.server.sse import SseServerTransport
   ```

하지만 이 방법은 개발 시간이 많이 소요되므로, **`mcpo` 사용을 강력히 권장**합니다.

---

## ✅ 체크리스트

### 방법 1: Streamable HTTP 직접 연결
- [ ] MCP 서버가 Streamable HTTP 지원 확인
- [ ] OpenAPI 스펙 엔드포인트 확인 (`openapi.json` 등)
- [ ] Open-WebUI에서 External Tool Servers에 추가
- [ ] 연결 테스트 성공
- [ ] MCP 도구가 Tools 메뉴에 표시되는지 확인
- [ ] 실제 도구 실행 테스트

### 방법 2: SSE + mcpo
- [ ] `mcpo` 설치 완료
- [ ] SSE MCP 서버 URL 확인
- [ ] `mcpo` 실행 및 포트 확인
- [ ] Open-WebUI에서 OpenAPI 서버로 등록
- [ ] MCP 도구가 Tools 메뉴에 표시되는지 확인
- [ ] 실제 도구 실행 테스트

---

**마지막 업데이트**: 2025-11-27  
**작성자**: AI Assistant  
**참고**: Open-WebUI v0.6.31+ 기준, Agent Portal MCP Gateway 지원

