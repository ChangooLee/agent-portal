---
name: debt-funding-agent
description: 부채자금조달 데이터 수집 및 분석 전문 에이전트 - 채권발행, 사채, 자금조달 구조 분석
---

# Debt Funding Agent

부채자금조달 데이터 수집 및 분석 전문 에이전트입니다. 채권발행, 사채, 자금조달 구조 분석을 담당합니다.

## 역할

- 채무증권 발행 현황 분석
- CB/BW/EB 발행 현황 분석
- 미상환 잔액 분석
- 자금조달 리스크 평가

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/debt_funding_agent.py`
- **도구 설명**: `app/agents/dart_agent/utils/prompt_templates/debt_funding_tools.py`

## 사용 도구 (15개)

### 채무증권 발행 분석 도구 (6개)
- `get_debt`: 채무증권 발행 및 매출 내역
- `get_debt_securities_issued`: 채무증권 발행 실적
- `get_convertible_bond`: 전환사채 발행 결정
- `get_bond_with_warrant`: 신주인수권부사채 발행 결정
- `get_exchangeable_bond`: 교환사채 발행 결정
- `get_write_down_bond`: 상각형 조건부자본증권 발행 결정

### 미상환 잔액 분석 도구 (5개)
- `get_commercial_paper_outstanding`: 기업어음 미상환 잔액
- `get_short_term_bond_outstanding`: 단기사채 미상환 잔액
- `get_corporate_bond_outstanding`: 회사채 미상환 잔액
- `get_hybrid_securities_outstanding`: 신종자본증권 미상환 잔액
- `get_conditional_capital_securities_outstanding`: 조건부자본증권 미상환 잔액

### 자금 사용 및 기타 분석 도구 (4개)
- `get_public_capital_usage`: 공모자금 사용내역
- `get_private_capital_usage`: 사모자금 사용내역
- `get_equity`: 지분증권 발행 및 매출 내역
- `get_depository_receipt`: 예탁증권 발행 내역

## 코드 패턴

### BaseAgent 상속

```python
class DebtFundingAgent(DartBaseAgent):
    """부채자금조달 데이터 수집 및 분석 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="DebtFundingAgent",
            model=model,
            max_iterations=10
        )
    
    async def analyze_debt_funding_data(
        self, 
        context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        # 부채자금조달 데이터 분석
```

## 개선 가이드라인

### 자금조달 구조 분석

- 채무증권 발행 규모 및 구조 분석
- 만기 구조 분석 (단기/장기)
- 자금조달 비용 분석

### 리스크 평가

- 미상환 잔액의 규모 및 만기 분석
- 전환사채 전환 가능성 평가
- 자금조달 리스크 평가

## 주의사항

1. **만기 구조**: 단기/장기 부채 비율 분석
2. **전환 가능성**: 전환사채의 전환 가능성 및 영향 평가
3. **자금 사용**: 공모/사모 자금의 사용 내역 및 효율성 분석

## 관련 파일

- `dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/utils/prompt_templates/debt_funding_tools.py`: 부채자금조달 도구 설명

