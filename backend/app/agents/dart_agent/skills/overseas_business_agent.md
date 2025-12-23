---
name: overseas-business-agent
description: 해외사업 데이터 수집 및 분석 전문 에이전트 - 해외 증권시장 상장/상장폐지 분석
---

# Overseas Business Agent

해외사업 데이터 수집 및 분석 전문 에이전트입니다. 해외 증권시장 상장/상장폐지 분석을 담당합니다.

## 역할

- 해외 진출/철수 리스크 평가
- 글로벌 확장 전략 분석
- 해외 상장 현황 추적

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/overseas_business_agent.py`
- **도구 설명**: `app/agents/dart_agent/utils/prompt_templates/overseas_business_tools.py`

## 사용 도구 (4개)

### 해외 상장 관련 도구 (4개)
- `get_foreign_listing_decision`: 해외상장 결정 조회
- `get_foreign_delisting_decision`: 해외상장폐지 결정 조회
- `get_foreign_listing`: 해외상장 조회
- `get_foreign_delisting`: 해외상장폐지 조회

## 코드 패턴

### BaseAgent 상속

```python
class OverseasBusinessAgent(DartBaseAgent):
    """해외사업 데이터 수집 및 분석 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="OverseasBusinessAgent",
            model=model,
            max_iterations=10
        )
    
    async def analyze_overseas_business_data(
        self, 
        context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        # 해외사업 데이터 분석
```

## 개선 가이드라인

### 해외 진출 분석

- 해외 상장의 목적 및 배경 분석
- 해외 진출이 사업 구조에 미치는 영향 평가
- 글로벌 확장 전략 분석

### 리스크 평가

- 해외 상장폐지 리스크 평가
- 해외 진출/철수의 재무 영향 분석

## 주의사항

1. **상장 목적**: 해외 상장의 구체적인 목적 및 배경 분석
2. **재무 영향**: 해외 진출/철수가 재무제표에 미치는 영향 평가
3. **전략적 의미**: 글로벌 확장 전략의 일관성 평가

## 관련 파일

- `dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/utils/prompt_templates/overseas_business_tools.py`: 해외사업 도구 설명

