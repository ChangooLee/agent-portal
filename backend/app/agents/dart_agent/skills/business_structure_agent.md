---
name: business-structure-agent
description: 사업구조 데이터 수집 및 분석 전문 에이전트 - M&A, 분할/합병, 자산양수도, 사업구조 변화 분석
---

# Business Structure Agent

사업구조 데이터 수집 및 분석 전문 에이전트입니다. M&A, 분할/합병, 자산양수도, 사업구조 변화 분석을 담당합니다.

## 역할

- 사업 재편 분석
- 인수합병 리스크 평가
- 자산 구조조정 분석
- 사업구조 변화 추적

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/business_structure_agent.py`
- **도구 설명**: `app/agents/dart_agent/utils/prompt_templates/business_structure_tools.py`

## 사용 도구 (17개)

### 사업양수도 (2개)
- `get_business_acquisition`: 영업양수 결정 조회
- `get_business_transfer`: 영업양도 결정 조회

### 합병분할 (6개)
- `get_merger`: 회사합병 결정 조회
- `get_division`: 회사분할 결정 조회
- `get_division_merger`: 분할합병 결정 조회
- `get_stock_exchange`: 주식교환/이전 결정 조회
- `get_merger_report`: 합병 증권신고서 조회
- `get_stock_exchange_report`: 주식교환/이전 증권신고서 조회
- `get_division_report`: 분할 증권신고서 조회

### 자산거래 (9개)
- `get_other_corp_stock_acquisition`: 타법인 주식 양수 결정 조회
- `get_other_corp_stock_transfer`: 타법인 주식 양도 결정 조회
- `get_stock_related_bond_acquisition`: 주권 관련 사채권 양수 결정 조회
- `get_stock_related_bond_transfer`: 주권 관련 사채권 양도 결정 조회
- `get_tangible_asset_acquisition`: 유형자산 양수 결정 조회
- `get_tangible_asset_transfer`: 유형자산 양도 결정 조회
- `get_asset_transfer`: 자산양수도 및 풋백옵션 계약 조회
- `get_investment_in_other_corp`: 타법인 출자 현황 조회

## 코드 패턴

### BaseAgent 상속

```python
class BusinessStructureAgent(DartBaseAgent):
    """사업구조 데이터 수집 및 분석 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="BusinessStructureAgent",
            model=model,
            max_iterations=10
        )
    
    async def analyze_business_structure_data(
        self, 
        context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        # 사업구조 데이터 분석
```

## 개선 가이드라인

### 사업 재편 분석

- M&A 거래의 규모 및 목적 분석
- 분할/합병이 사업 구조에 미치는 영향 평가
- 사업 재편의 전략적 의미 분석

### 리스크 평가

- 인수합병 리스크 평가
- 자산 구조조정 리스크 평가
- 사업구조 변화의 재무 영향 분석

## 주의사항

1. **거래 규모**: M&A 거래의 규모와 중요성 평가
2. **전략적 의미**: 사업 재편의 전략적 배경 및 목적 분석
3. **재무 영향**: 사업구조 변화가 재무제표에 미치는 영향 평가

## 관련 파일

- `dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/utils/prompt_templates/business_structure_tools.py`: 사업구조 도구 설명

