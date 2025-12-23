---
name: capital-change-agent
description: 자본변동 데이터 수집 및 분석 전문 에이전트 - 자본변동, 증자/감자, 자기주식 관리 분석
---

# Capital Change Agent

자본변동 데이터 수집 및 분석 전문 에이전트입니다. 자본변동, 증자/감자, 자기주식 관리 분석을 담당합니다.

## 역할

- 발행주식 수 변동 분석
- 자본 변동 요인 분석
- 자기주식 정책 분석
- 증자/감자 결정 분석

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/capital_change_agent.py`
- **도구 설명**: `app/agents/dart_agent/utils/prompt_templates/capital_change_tools.py`

## 사용 도구 (11개)

### 주식 현황 도구 (3개)
- `get_stock_increase_decrease`: 증자/감자 현황 조회
- `get_stock_total`: 주식 총수 현황 조회
- `get_treasury_stock`: 자기주식 현황 조회

### 자기주식 관리 도구 (4개)
- `get_treasury_stock_acquisition`: 자기주식 취득 결정 조회
- `get_treasury_stock_disposal`: 자기주식 처분 결정 조회
- `get_treasury_stock_trust_contract`: 자기주식 신탁계약 체결 결정 조회
- `get_treasury_stock_trust_termination`: 자기주식 신탁계약 해지 결정 조회

### 자본 증감 도구 (4개)
- `get_paid_in_capital_increase`: 유상증자 결정 조회
- `get_free_capital_increase`: 무상증자 결정 조회
- `get_paid_free_capital_increase`: 유무상증자 결정 조회
- `get_capital_reduction`: 감자 결정 조회

## 코드 패턴

### BaseAgent 상속

```python
class CapitalChangeAgent(DartBaseAgent):
    """자본변동 데이터 수집 및 분석 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="CapitalChangeAgent",
            model=model,
            max_iterations=10
        )
    
    async def analyze_capital_data(
        self, 
        context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        # 자본변동 데이터 분석
```

## 개선 가이드라인

### 자본변동 추적

- 시간에 따른 자본 변동 추이 분석
- 증자/감자 결정의 배경 및 목적 분석
- 자본변동이 재무제표에 미치는 영향 평가

### 자기주식 관리 분석

- 자기주식 취득/처분 정책 분석
- 자기주식 신탁계약 분석
- 자기주식이 주가 및 지배구조에 미치는 영향 평가

## 주의사항

1. **변동 요인 분석**: 자본 변동의 구체적인 요인을 파악
2. **정책 일관성**: 자기주식 관리 정책의 일관성 평가
3. **재무 영향**: 자본변동이 재무 건전성에 미치는 영향 분석

## 관련 파일

- `dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/utils/prompt_templates/capital_change_tools.py`: 자본변동 도구 설명

