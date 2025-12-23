---
name: governance-agent
description: 지배구조 데이터 수집 및 분석 전문 에이전트 - 주주구조, 임원현황, 지배구조, 소유구조 분석
---

# Governance Agent

지배구조 데이터 수집 및 분석 전문 에이전트입니다. 주주구조, 임원현황, 지배구조, 소유구조 분석을 담당합니다.

## 역할

- 주주구조 분석 (최대주주, 소액주주, 지분 변동)
- 임원 및 사외이사 현황 분석
- 지배구조 리스크 평가
- 소액주주 보호 분석

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/governance_agent.py`
- **도구 설명**: `app/agents/dart_agent/utils/prompt_templates/governance_tools.py`

## 사용 도구 (8개)

### 주주구조 분석 도구 (4개)
- `get_major_shareholder`: 최대주주 및 특수관계인 지분 현황
- `get_major_shareholder_changes`: 최대주주 지분 변동 내역
- `get_minority_shareholder`: 소액주주 현황
- `get_major_holder_changes`: 5% 이상 주주의 지분 변동 내역

### 임원 및 거래 분석 도구 (4개)
- `get_executive_trading`: 임원 및 주요주주의 주식 거래 내역
- `get_executive_info`: 임원 현황
- `get_employee_info`: 직원 현황
- `get_outside_director_status`: 사외이사 현황

## 클래스 구조

```python
class GovernanceAgent(DartBaseAgent):
    """지배구조 데이터 수집 및 분석 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="GovernanceAgent",
            model=model,
            max_iterations=10
        )
    
    async def analyze_governance_data(
        self, 
        context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        # 지배구조 데이터 분석
        # 스트리밍 지원
```

## 코드 패턴

### 도구 필터링

```python
async def _filter_tools_for_agent(self, tools: List[BaseTool]) -> List[BaseTool]:
    """지배구조 분석에 특화된 도구 필터링 (8개 도구)"""
    governance_tool_names = [
        "get_major_shareholder",
        "get_major_shareholder_changes",
        "get_minority_shareholder",
        "get_major_holder_changes",
        "get_executive_trading",
        "get_executive_info",
        "get_employee_info",
        "get_outside_director_status",
    ]
    
    filtered_tools = []
    for tool in tools:
        if hasattr(tool, "name") and tool.name in governance_tool_names:
            filtered_tools.append(tool)
    
    return filtered_tools
```

## 개선 가이드라인

### 주주구조 분석 최적화

- 최대주주 변동 추이 분석
- 지분집중도 계산
- 소액주주 보호 수준 평가

### 임원 구조 분석

- 임원 구성의 독립성 평가
- 사외이사 비율 및 역할 분석
- 임원 거래 내역 모니터링

## 주의사항

1. **지분 변동 추적**: 시간에 따른 지분 변동을 추적하여 리스크 평가
2. **독립성 평가**: 사외이사 비율과 독립성을 종합적으로 평가
3. **거래 모니터링**: 임원 및 주요주주의 주식 거래 내역을 주의 깊게 분석

## 관련 파일

- `dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/utils/prompt_templates/governance_tools.py`: 지배구조 도구 설명

