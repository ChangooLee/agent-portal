---
name: intent-classifier-agent
description: 사용자 질문의 의도를 분류하여 적절한 전문 에이전트를 선택하는 분류기 - 기업 식별, 의도 분류, 에이전트 선택
---

# Intent Classifier Agent

사용자 질문의 의도를 분류하고 적절한 전문 에이전트를 선택하는 분류기입니다. 기업 식별, 의도 분류, 에이전트 선택을 담당합니다.

## 역할

- 사용자 질문에서 기업명 추출 (LLM 기반)
- 기업 코드 조회 (**MCP 도구만 사용** - 아키텍처 원칙 준수)
- 단일/복수 기업 분류
- LLM 기반 에이전트 선택 (8개 전문 에이전트 중)
- IntentClassificationResult 생성 및 반환

> ⚠️ **아키텍처 원칙**: 에이전트는 MCP 도구만 사용하며, 직접 리소스(파일, 캐시 등)에 접근하지 않습니다.

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/intent_classifier_agent.py`

## 클래스 구조

```python
class IntentClassifierAgent(DartBaseAgent):
    """사용자 질문 의도 분류 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        # DartBaseAgent 초기화
        # 분류 패턴 초기화
        # 메시지 정제 시스템 초기화
    
    async def classify_intent_and_select_agents(
        self,
        user_question: str,
        corp_info: Dict[str, Any] = None
    ) -> AsyncGenerator[Dict[str, Any], IntentClassificationResult]:
        # 기업명 추출
        # 기업 코드 조회
        # 에이전트 선택
        # 결과 반환
```

## 주요 메서드

### `classify_intent_and_select_agents()`

의도 분류 및 에이전트 선택의 메인 메서드입니다:

1. **기업명 추출**: `_extract_company_name()` - LLM 기반 기업명 추출 (업종별 80개 기업 참고)
2. **기업 코드 조회**: `_find_corporation_code()` - **MCP 도구만 사용**
3. **단일/복수 기업 분기**: 기업명이 여러 개인지 확인
4. **에이전트 선택**: `_llm_based_agent_selection()` - LLM 기반 에이전트 선택
5. **결과 생성**: IntentClassificationResult 생성 및 반환

### `_extract_company_name()`

LLM을 사용하여 사용자 질문에서 기업명을 추출합니다:

- 업종별 대표기업 80개 참고 (생명보험 10개, 손해보험 10개, 증권 10개 등)
- 강제 응답 요구: "절대 '없음'이라고 답하지 마세요"
- 맥락 기반 추론: 목록에 없어도 적절한 기업명 추론 가능
- 쉼표로 구분된 기업명 리스트 반환

### `_find_corporation_code()`

기업명으로 기업 코드를 조회합니다:

> ⚠️ **아키텍처 변경 (2024-12-17)**: 로컬 CORPCODE.xml 검색 제거, MCP 도구만 사용

1. **MCP 도구 호출**: `get_corporation_code_by_name` 도구 사용
2. **코드 추출**: `_extract_corp_code_from_result()` - JSON 파싱 및 기업코드 추출
3. **기업명 변형 시도**: 정규화된 기업명 변형으로 재시도

### `_llm_based_agent_selection()`

LLM을 사용하여 적절한 에이전트를 선택합니다:

- 8개 전문 에이전트 상세 설명 포함
- JSON 형식 응답 요청
- scope, domain, depth Enum 변환
- Fallback: LLM 실패 시 기본 에이전트 사용

## 코드 패턴

### BaseAgent 상속

```python
from app.agents.dart_agent.base import DartBaseAgent

class IntentClassifierAgent(DartBaseAgent):
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="IntentClassifierAgent",
            model=model,
            max_iterations=10
        )
```

### 기업명 추출

```python
async def _extract_company_name(self, user_question: str) -> str:
    """LLM을 사용하여 사용자 질문에서 기업명 추출"""
    # 업종별 대표기업 80개 참고
    reference_companies = """
    생명보험: 삼성생명, 한화생명, 교보생명, ...
    손해보험: 삼성화재, 현대해상, DB손해보험, ...
    ...
    """
    
    prompt = f"""사용자 질문에서 기업명을 추출하세요.
    
    질문: {user_question}
    참고 기업 목록: {reference_companies}
    
    절대 '없음'이라고 답하지 마세요. 목록에 없어도 적절한 기업명을 추론하세요.
    여러 기업이면 쉼표로 구분하세요.
    
    기업명:"""
    
    response = await self.llm.ainvoke([HumanMessage(content=prompt)])
    return response.content.strip()
```

### 기업 코드 조회

```python
async def _find_corporation_code(self, company_name: str) -> Dict[str, Any]:
    """기업명으로 기업코드 찾기 - MCP 도구만 사용 (아키텍처 원칙: 에이전트는 MCP만 이용)
    
    Note: 에이전트는 직접 리소스(CORPCODE.xml 등)에 접근하지 않습니다.
    모든 데이터 접근은 MCP 도구를 통해서만 수행됩니다.
    """
    # MCP 도구 호출
    mcp_client = await get_opendart_mcp_client()
    
    for variation in company_variations:
        tool_result = await mcp_client.call_tool(
            "get_corporation_code_by_name", 
            {"corp_name": variation}
        )
        
        parsed_result = self._parse_mcp_result(tool_result)
        if parsed_result.get("items"):
            return {"result": tool_result, "company_name": variation}
    
    return {"error": f"기업을 찾을 수 없습니다"}
```

### 에이전트 선택

```python
async def _llm_based_agent_selection(
    self,
    user_question: str,
    corp_info: Dict[str, Any],
    classification: Dict[str, Any]
) -> Dict[str, Any]:
    """LLM 기반 에이전트 선택"""
    # 8개 전문 에이전트 설명
    agents_description = """
    1. FinancialAgent: 재무 건전성, 수익성, 유동성 분석
    2. GovernanceAgent: 주주구조, 임원현황, 지배구조 분석
    ...
    """
    
    prompt = f"""사용자 질문에 가장 적합한 에이전트를 선택하세요.
    
    질문: {user_question}
    기업 정보: {corp_info}
    
    사용 가능한 에이전트:
    {agents_description}
    
    JSON 형식으로 응답:
    {{
        "scope": "single_company" | "multi_company" | "industry_analysis",
        "domain": "financial" | "governance" | ...,
        "depth": "basic" | "intermediate" | "advanced",
        "required_agents": ["financial"],
        "reasoning": "선택 이유"
    }}"""
    
    response = await self.agent_executor.ainvoke([HumanMessage(content=prompt)])
    # JSON 파싱 및 Enum 변환
    return parsed_result
```

## 개선 가이드라인

### 기업명 추출 강화

- 업종별 참고 기업 목록을 주기적으로 업데이트
- LLM이 "없음"이라고 답하지 않도록 강력한 프롬프트 사용
- 맥락 기반 추론 능력 활용

### 기업 코드 조회 최적화

- **MCP 도구만 사용** (아키텍처 원칙 준수)
- MCP 서버가 CORPCODE.xml 캐시 및 검색 담당
- 기업명 변형으로 다양한 매칭 시도

### 에이전트 선택 정확도 향상

- 각 에이전트의 역할과 도구를 명확히 설명
- 사용자 질문과 공시 데이터를 연결하여 분석
- 의미 기반 선택 (키워드 매칭 아님)

### 에러 처리

```python
# 조기 종료: LLM 기업명 추출 실패 시 즉시 에러 반환
if not company_name or len(company_name.strip()) < 2:
    yield {"type": "error", "content": "기업명을 추출할 수 없습니다."}
    return

# 부분 성공: 복수 기업 중 일부 실패는 허용
for company in company_names:
    try:
        corp_code = await self._find_corporation_code(company)
        if corp_code:
            corp_info_list.append({"corp_name": company, "corp_code": corp_code})
    except Exception as e:
        log_step("기업 코드 조회", "WARNING", f"{company} 조회 실패: {str(e)}")
        continue

# 기본값 제공: LLM 에이전트 선택 실패 시 기본 에이전트 사용
if not selected_agents:
    selected_agents = ["financial"]  # 기본값
```

## 주의사항

1. **기업명 추출 필수**: 기업명 추출 실패 시 전체 프로세스 중단
2. **MCP 도구만 사용**: 에이전트가 직접 파일/캐시 접근 금지 (아키텍처 원칙)
3. **복수 기업 처리**: 각 기업별로 순차 처리, 일부 실패 허용
4. **LLM Fallback**: 에이전트 선택 실패 시 기본 에이전트 사용
5. **MCP 응답 문제 시**: MCP 서버 코드 수정 (`/data/mcp/mcp-opendart/`), 에이전트에서 우회 금지

## 관련 파일

- `app/agents/dart_agent/dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/dart_types.py`: IntentClassificationResult 정의
- `app/agents/dart_agent/message_refiner.py`: 메시지 정제 시스템

