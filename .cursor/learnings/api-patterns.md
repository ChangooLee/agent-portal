# API 개발 학습 내용

Agent Portal의 Backend API 개발에서 학습한 패턴과 방법을 기록합니다.

## 형식

```markdown
## YYYY-MM-DD: 제목

**요청**: 사용자 요청 내용
**적용**: 적용한 패턴/방법
**피드백**: ✅ 잘 잡았어 / ❌ 이거 싫어함
**재사용**: 향후 유사 작업 시 적용 방법
**참고**: 관련 파일 경로, 커밋 해시 등

---
```

---

## 2025-11-12: API 타임아웃 및 에러 핸들링

**요청**: 외부 API 호출 시 안정성 개선
**적용**: httpx.AsyncClient(timeout=30.0) + try/except 에러 핸들링
**피드백**: ✅ 잘 잡았어 (안정성 향상)
**재사용**: 모든 외부 호출에 타임아웃 30초 설정 필수
**참고**: 
- backend/app/services/litellm_service.py
- backend/app/services/langfuse_service.py

---

## 2025-11-17: AgentOps 선택적 Import 패턴

**요청**: AgentOps SDK를 통한 에이전트 실행 모니터링
**적용**: 선택적 import 패턴 (Langfuse와 동일)
**피드백**: ✅ 잘 잡았어 (graceful degradation)
**재사용**: 모든 선택적 의존성에 동일 패턴 적용
**참고**: 
- backend/app/services/agentops_service.py
- backend/app/services/langfuse_service.py (참조 패턴)

**패턴**:
```python
try:
    import agentops
    AGENTOPS_AVAILABLE = True
except ImportError:
    AGENTOPS_AVAILABLE = False
    agentops = None

class AgentOpsService:
    def __init__(self):
        self.enabled = AGENTOPS_AVAILABLE
        if self.enabled:
            # Initialize AgentOps
            pass
    
    def start_session(self, flow_id: str, tags: list):
        if not self.enabled:
            return None
        # Start session
        pass
```

---

## 2025-11-17: AgentOps 세션 추적 패턴

**요청**: 플로우 실행을 세션 단위로 추적
**적용**: start_session → record_action → end_session 패턴
**피드백**: ✅ 잘 잡았어 (명확한 생명주기)
**재사용**: 모든 에이전트 실행에 동일 패턴 적용
**참고**: 
- backend/app/services/langgraph_service.py
- backend/app/routes/agents.py

**패턴**:
```python
# 세션 시작
session = agentops_service.start_session(
    flow_id=flow_id,
    tags=["langflow", "production"]
)

try:
    # 플로우 실행
    result = await langgraph_service.execute_flow(...)
    
    # 성공 기록
    agentops_service.record_action(
        session=session,
        action_type="flow_execution",
        result=result,
        cost=calculate_cost(result)
    )
    
    # 세션 종료 (성공)
    agentops_service.end_session(session, status="Success")
except Exception as e:
    # 세션 종료 (실패)
    agentops_service.end_session(session, status="Fail", error=str(e))
    raise
```

---

## 2025-11-17: LLM API 비용 계산 패턴

**요청**: LLM API 호출 비용 자동 계산
**적용**: 토큰 수 기반 비용 계산 로직
**피드백**: ✅ 잘 잡았어 (비용 투명성)
**재사용**: 모든 LLM 호출에 비용 계산 추가
**참고**: 
- backend/app/services/langgraph_service.py

**패턴**:
```python
def calculate_cost(result: Dict) -> float:
    """
    LLM API 호출 비용 계산
    
    Args:
        result: LangGraph 실행 결과 (usage 정보 포함)
    
    Returns:
        총 비용 (USD)
    """
    usage = result.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    
    # GPT-4 기준 가격 (예시)
    prompt_cost = prompt_tokens * 0.00003  # $0.03 per 1K tokens
    completion_cost = completion_tokens * 0.00006  # $0.06 per 1K tokens
    
    return prompt_cost + completion_cost
```

---

