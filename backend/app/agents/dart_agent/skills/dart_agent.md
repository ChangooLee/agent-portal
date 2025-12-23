---
name: dart-agent
description: DART 멀티에이전트 시스템의 메인 에이전트 - 전체 시스템 초기화 및 관리, 멀티에이전트 워크플로우 진입점
---

# Dart Agent

DART 공시 데이터 분석을 위한 멀티에이전트 시스템의 메인 진입점입니다. 전체 시스템을 초기화하고 멀티에이전트 워크플로우를 관리합니다.

## 역할

- 멀티에이전트 시스템 초기화 및 관리
- DartMasterAgent, IntentClassifierAgent, 전문 에이전트들 생성 및 등록
- 사용자 요청을 멀티에이전트 시스템으로 라우팅
- 스트리밍 응답 처리

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/dart_agent.py`
- **라우터**: `app/agents/dart_agent/dart_routes.py`

## 클래스 구조

```python
class DartAgent(DartBaseAgent):
    """DART 멀티에이전트 시스템 - 기존 호환성 유지하면서 멀티에이전트 기능 제공"""
    
    def __init__(self, model: str = "qwen-235b"):
        # DartBaseAgent 초기화
        # 멀티에이전트 시스템 구성요소 초기화
    
    async def initialize(self):
        # BaseAgent 초기화
        # 멀티에이전트 시스템 초기화
    
    async def process_chat_request_stream(
        self, 
        message: str, 
        thread_id: Optional[str] = None, 
        user_email: Optional[str] = None
    ):
        # 스트리밍 요청 처리
        # DartMasterAgent로 위임
```

## 주요 메서드

### `initialize()`

멀티에이전트 시스템을 초기화합니다:

1. BaseAgent 초기화 (MCP 매니저 등)
2. `_initialize_multi_agent_system()` 호출
   - DartMasterAgent 생성
   - IntentClassifierAgent 생성
   - 9개 전문 에이전트 생성 및 등록

### `process_chat_request_stream()`

사용자 요청을 스트리밍으로 처리합니다:

1. 멀티에이전트 모드 확인
2. DartMasterAgent의 `coordinate_analysis_stream()` 호출
3. 스트리밍 청크를 yield하여 전달

## 초기화 순서

```
DartAgent.__init__()
    ↓
DartAgent.initialize()
    ↓
DartBaseAgent.initialize()  # MCP 클라이언트 초기화
    ↓
_initialize_multi_agent_system()
    ↓
1. DartMasterAgent 생성
2. IntentClassifierAgent 생성
3. 전문 에이전트들 생성 (9개)
   - FinancialAgent
   - GovernanceAgent
   - CapitalChangeAgent
   - DebtFundingAgent
   - BusinessStructureAgent
   - OverseasBusinessAgent
   - LegalComplianceAgent
   - ExecutiveAuditAgent
   - DocumentAnalysisAgent
```

## 코드 패턴

### BaseAgent 상속

```python
from app.agents.dart_agent.base import DartBaseAgent

class DartAgent(DartBaseAgent):
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="DartAgent",
            model=model,
            max_iterations=10
        )
```

### 멀티에이전트 시스템 초기화

```python
async def _initialize_multi_agent_system(self):
    # 마스터 에이전트 생성
    self.master_agent = DartMasterAgent(model=self.model)
    await self.master_agent.initialize()
    
    # 의도 분류 에이전트 생성
    self.intent_classifier = IntentClassifierAgent(model=self.model)
    await self.intent_classifier.initialize()
    
    # 전문 에이전트들 생성
    agent_configs = [
        ("financial", FinancialAgent),
        ("governance", GovernanceAgent),
        ("capital_change", CapitalChangeAgent),
        ("debt_funding", DebtFundingAgent),
        ("business_structure", BusinessStructureAgent),
        ("overseas_business", OverseasBusinessAgent),
        ("legal_risk", LegalComplianceAgent),
        ("executive_audit", ExecutiveAuditAgent),
        ("document_analysis", DocumentAnalysisAgent),
    ]
    
    for agent_name, agent_class in agent_configs:
        agent_instance = agent_class(model=self.model)
        await agent_instance.initialize()
        self.master_agent.register_sub_agent(agent_name, agent_instance)
```

### 스트리밍 처리

```python
async def process_chat_request_stream(
    self, 
    message: str, 
    thread_id: Optional[str] = None, 
    user_email: Optional[str] = None
):
    async for strategy_chunk in self.master_agent.coordinate_analysis_stream(
        message, thread_id=thread_id, user_email=user_email
    ):
        yield strategy_chunk
        
        if strategy_chunk.get("type") == "end":
            break
```

## 개선 가이드라인

### 초기화 최적화

- 에이전트 생성 실패 시 부분 실패 허용 (최소 2개 이상 성공 시 계속 진행)
- 각 에이전트 초기화 실패는 개별적으로 처리하여 다른 에이전트에 영향 없음
- 상세한 로깅으로 실패 원인 추적 가능

### 에러 처리

```python
try:
    await self._initialize_multi_agent_system()
    log_step("DartAgent 초기화", "SUCCESS", "멀티에이전트 시스템 초기화 완료")
except Exception as e:
    log_step("DartAgent 초기화", "WARNING", f"멀티에이전트 시스템 초기화 실패: {str(e)}")
    # 멀티에이전트 실패해도 기본 에이전트로 동작
```

### 스트리밍 최적화

- "end" 타입 청크를 받을 때까지 모든 청크를 yield
- 에러 발생 시 즉시 사용자에게 전달
- 중간 진행 상황을 실시간으로 표시

## 주의사항

1. **MCP 서버 의존성**: MCP 클라이언트는 DartBaseAgent에서 자동으로 초기화됨
2. **초기화 순서**: DartBaseAgent 초기화 후 멀티에이전트 시스템 초기화
3. **에러 복구**: 일부 에이전트 초기화 실패해도 시스템은 계속 동작
4. **스트리밍 일관성**: 모든 청크를 순서대로 yield하여 클라이언트가 올바르게 처리할 수 있도록 함

## 관련 파일

- `app/agents/dart_agent/dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/intent_classifier_agent.py`: 의도 분류 에이전트
- `app/agents/dart_agent/dart_routes.py`: FastAPI 라우터
- `app/agents/dart_agent/base.py`: 기본 에이전트 클래스 (DartBaseAgent)

