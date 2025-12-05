# 다음 단계 솔루션 가이드

> **작성일**: 2025-01-14  
> **현재 단계**: Stage 2 (부분 완료, 40%)  
> **목적**: 다음 단계에서 적용할 솔루션 및 구현 방법 정리

---

## 📊 현재 상태 점검

### ✅ 완료된 항목
- Backend BFF 기본 구조 생성
- Chat API 구현 (`/chat/stream`, `/chat/completions`)
- Observability API 구현 (`/observability/*`)
- LiteLLM 서비스 레이어 구현
- Monitoring 페이지 추가 (OTEL + ClickHouse 기반)
- `config/litellm.yaml`, `config/kong.yml` 설정 파일 생성
- Docker Compose 서비스 정의 (LiteLLM, Kong, ClickHouse 등)

### ⚠️ 미완성 항목 (Critical)
1. **인증/인가 시스템** - RBAC 미들웨어는 있으나 placeholder 상태
2. **테스트 코드** - 완전 부재
3. **서비스 통합 테스트** - docker-compose up으로 전체 스택 실행 미완
4. **LiteLLM 실제 연동** - 환경 설정 및 테스트 필요
5. **프론트엔드-백엔드 데이터 연동** - BFF API 호출 미완

---

## 🎯 다음 단계 솔루션 (P0 우선순위)

### 1. 인증/인가 시스템 구현 (보안 취약점 해결)

**현재 상태**:
- `backend/app/middleware/rbac.py`에 RBAC 미들웨어 존재
- 하지만 `user_info = {"role": "admin"}` placeholder 상태
- JWT 토큰 검증 미구현

**솔루션**:

#### 1.1 Open-WebUI 인증 시스템 연동

**방법 1: Open-WebUI JWT 토큰 재사용** (권장)
- Open-WebUI는 자체 인증 시스템을 가지고 있음
- Open-WebUI의 JWT 토큰을 BFF에서 검증
- 세션 쿠키 또는 Authorization 헤더로 전달

**구현 단계**:
1. Open-WebUI의 JWT 시크릿 키 확인
2. BFF에서 JWT 토큰 검증 미들웨어 구현
3. 토큰에서 사용자 정보 추출 (user_id, role, workspace_id)
4. RBAC 미들웨어에 실제 사용자 정보 주입

**참고 문서**:
- Open-WebUI 인증 시스템: `webui/backend/open_webui/auth/`
- JWT 토큰 생성 위치: `webui/backend/open_webui/auth/utils.py`

**코드 예시**:
```python
# backend/app/middleware/auth.py
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config import get_settings

settings = get_settings()
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Open-WebUI JWT 토큰 검증"""
    try:
        # Open-WebUI의 JWT 시크릿 키 (환경변수 또는 설정에서 가져오기)
        secret_key = settings.WEBUI_SECRET_KEY
        token = credentials.credentials
        
        # JWT 토큰 디코딩
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
        role = payload.get("role", "user")
        workspace_id = payload.get("workspace_id")
        
        return {
            "user_id": user_id,
            "role": role,
            "workspace_id": workspace_id
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

#### 1.2 RBAC 미들웨어 업데이트

**현재 코드** (`backend/app/middleware/rbac.py`):
```python
# Placeholder - integrate with actual auth
user_info = {"role": "admin"}
```

**수정 방안**:
```python
# backend/app/middleware/rbac.py
from app.middleware.auth import verify_token

async def get_current_user_role(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """실제 인증 시스템과 연동"""
    if not credentials:
        return None
    
    # JWT 토큰 검증
    user_info = await verify_token(credentials)
    return user_info.get("role")
```

#### 1.3 환경변수 설정

**`.env` 파일에 추가**:
```bash
# Open-WebUI JWT Secret Key (Open-WebUI와 동일한 값 사용)
WEBUI_SECRET_KEY=your-secret-key-here

# 또는 Open-WebUI의 기본 시크릿 키 경로
WEBUI_SECRET_KEY_PATH=/app/backend/.webui_secret_key
```

**`backend/app/config.py`에 추가**:
```python
class Settings(BaseSettings):
    # ... 기존 설정 ...
    WEBUI_SECRET_KEY: str = ""
    WEBUI_SECRET_KEY_PATH: str = "/app/backend/.webui_secret_key"
    
    @property
    def get_webui_secret_key(self) -> str:
        """Open-WebUI 시크릿 키 가져오기"""
        if self.WEBUI_SECRET_KEY:
            return self.WEBUI_SECRET_KEY
        # 파일에서 읽기
        if os.path.exists(self.WEBUI_SECRET_KEY_PATH):
            with open(self.WEBUI_SECRET_KEY_PATH, "r") as f:
                return f.read().strip()
        raise ValueError("WEBUI_SECRET_KEY not found")
```

**참고 라이브러리**:
- `python-jose[cryptography]` - JWT 토큰 검증
- `python-multipart` - HTTP Bearer 토큰 파싱

**requirements.txt에 추가**:
```txt
python-jose[cryptography]>=3.3.0
python-multipart>=0.0.6
```

---

### 2. 테스트 코드 작성 (코드 품질 향상)

**현재 상태**: 테스트 코드 완전 부재

**솔루션**:

#### 2.1 pytest 설정

**파일 구조**:
```
backend/
├── app/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # pytest 설정 및 fixtures
│   ├── test_chat.py         # Chat API 테스트
│   ├── test_observability.py # Observability API 테스트
│   └── test_services/        # 서비스 레이어 테스트
│       └── test_litellm_service.py
```

**`backend/tests/conftest.py`**:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)

@pytest.fixture
def mock_jwt_token():
    """Mock JWT 토큰"""
    return "mock-jwt-token-here"

@pytest.fixture
def admin_headers(mock_jwt_token):
    """Admin 역할 헤더"""
    return {"Authorization": f"Bearer {mock_jwt_token}"}
```

**`backend/tests/test_chat.py`**:
```python
import pytest
from tests.conftest import client, admin_headers

def test_chat_stream_endpoint(client, admin_headers):
    """Chat 스트리밍 엔드포인트 테스트"""
    response = client.post(
        "/chat/stream",
        headers=admin_headers,
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "gpt-3.5-turbo"
        }
    )
    assert response.status_code == 200

def test_chat_completions_endpoint(client, admin_headers):
    """Chat completions 엔드포인트 테스트"""
    response = client.post(
        "/chat/completions",
        headers=admin_headers,
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "gpt-3.5-turbo"
        }
    )
    assert response.status_code == 200
    assert "choices" in response.json()
```

**`backend/pytest.ini`**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

**requirements.txt에 추가**:
```txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.24.0  # TestClient 대신 httpx 사용 가능
```

**실행 방법**:
```bash
cd backend
pytest tests/ -v
```

---

### 3. LiteLLM 서비스 실행 및 연동

**현재 상태**:
- `docker-compose.yml`에 LiteLLM 서비스 정의됨
- `config/litellm.yaml` 설정 파일 존재
- 실제 실행 및 연동 테스트 미완

**솔루션**:

#### 3.1 환경변수 설정

**`.env` 파일에 추가**:
```bash
# OpenAI API Key
OPENAI_API_KEY=sk-...

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-...

# vLLM API Base (로컬 모델 사용 시)
VLLM_API_BASE=http://vllm:8000/v1
```

#### 3.2 LiteLLM 서비스 실행

**명령어**:
```bash
# LiteLLM만 실행
docker-compose up -d litellm

# 로그 확인
docker-compose logs -f litellm

# 헬스체크
curl http://localhost:4000/health
```

#### 3.3 LiteLLM 연동 테스트

**`backend/app/services/litellm_service.py` 수정**:
```python
import httpx
from app.config import get_settings

settings = get_settings()

class LiteLLMService:
    def __init__(self):
        self.base_url = settings.LITELLM_BASE_URL or "http://litellm:4000"
    
    async def chat_completion(self, messages: list, model: str):
        """LiteLLM을 통한 채팅 완성"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages
                }
            )
            response.raise_for_status()
            return response.json()
```

**테스트 스크립트** (`scripts/test-litellm.sh`):
```bash
#!/bin/bash
set -e

echo "Testing LiteLLM connection..."

# LiteLLM 헬스체크
curl -f http://localhost:4000/health || exit 1

# 모델 리스트 확인
curl -f http://localhost:4000/v1/models || exit 1

# 간단한 채팅 테스트
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}]
  }' || exit 1

echo "LiteLLM test passed!"
```

---

### 4. 전체 스택 통합 테스트

**목적**: 모든 서비스가 정상적으로 연동되는지 확인

**솔루션**:

#### 5.1 통합 테스트 스크립트

**`scripts/test-integration.sh`**:
```bash
#!/bin/bash
set -e

echo "🚀 Starting integration tests..."

# 1. 모든 서비스 실행
echo "📦 Starting all services..."
docker-compose up -d

# 2. 서비스 준비 대기
echo "⏳ Waiting for services to be ready..."
sleep 30

# 3. 각 서비스 헬스체크
echo "🏥 Health checks..."

# Backend BFF
curl -f http://localhost:8000/health || exit 1
echo "✅ Backend BFF: OK"

# LiteLLM
curl -f http://localhost:4000/health || exit 1
echo "✅ LiteLLM: OK"

# ClickHouse
curl -f http://localhost:8124/ping || exit 1
echo "✅ ClickHouse: OK"

# 4. API 엔드포인트 테스트
echo "🧪 Testing API endpoints..."

# Chat API (인증 필요 시 헤더 추가)
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}], "model": "gpt-3.5-turbo"}' \
  || echo "⚠️  Chat API test skipped (auth required)"

# Observability API
curl -f http://localhost:8000/observability/health || exit 1
echo "✅ Observability API: OK"

echo "🎉 Integration tests passed!"
```

#### 4.2 단계별 서비스 실행

**개발 환경에서 단계별 실행**:
```bash
# 1단계: 데이터베이스만 실행
docker-compose up -d mariadb kong-db litellm-postgres

# 2단계: 관측성 서비스 실행 (OTEL + ClickHouse)
docker-compose up -d otel-collector monitoring-clickhouse

# 3단계: LiteLLM 실행
docker-compose up -d litellm

# 4단계: Backend BFF 실행
docker-compose up -d backend

# 5단계: WebUI 실행
docker-compose up -d webui
```

---

## 📋 구현 체크리스트

### P0 (즉시 해결)

- [ ] **인증/인가 시스템 구현**
  - [ ] Open-WebUI JWT 토큰 검증 미들웨어 구현
  - [ ] RBAC 미들웨어에 실제 사용자 정보 주입
  - [ ] 모든 엔드포인트에 인증 적용
  - [ ] 환경변수 설정 (WEBUI_SECRET_KEY)

- [ ] **테스트 코드 작성**
  - [ ] pytest 설정 및 기본 구조 생성
  - [ ] Chat API 테스트 작성
  - [ ] Observability API 테스트 작성
  - [ ] 서비스 레이어 테스트 작성

- [ ] **LiteLLM 서비스 실행**
  - [ ] 환경변수 설정 (.env)
  - [ ] docker-compose로 서비스 실행
  - [ ] 헬스체크 및 연동 테스트
  - [ ] Backend BFF와 연동 확인

- [x] **OTEL + ClickHouse 모니터링 실행**
  - [x] OTEL Collector 설정 완료
  - [x] ClickHouse 트레이스 저장소 구성 완료
  - [ ] API 키 생성 및 설정
  - [ ] Backend BFF와 연동 확인

- [ ] **전체 스택 통합 테스트**
  - [ ] 통합 테스트 스크립트 작성
  - [ ] 모든 서비스 헬스체크
  - [ ] API 엔드포인트 통합 테스트

### P1 (단기 해결)

- [x] 프론트엔드-백엔드 데이터 연동
- [x] 에러 핸들링 개선
- [x] ClickHouse 쿼리 API 구현
- [x] 환경변수 설정 가이드 문서화

---

## 🔗 참고 자료

### 인증/인가
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [python-jose JWT](https://python-jose.readthedocs.io/)
- [Open-WebUI Auth System](https://github.com/open-webui/open-webui/tree/main/backend/open_webui/auth)

### 테스트
- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

### LiteLLM
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [LiteLLM Docker Setup](https://docs.litellm.ai/docs/docker)

---

**작성자**: AI Agent (Claude)  
**마지막 업데이트**: 2025-01-14

