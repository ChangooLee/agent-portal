---
name: legal-compliance-agent
description: 법적컴플라이언스 데이터 수집 및 분석 전문 에이전트 - 경영위기, 법적위험, 소송, 회생절차 분석
---

# Legal Compliance Agent

법적컴플라이언스 데이터 수집 및 분석 전문 에이전트입니다. 경영위기, 법적위험, 소송, 회생절차 분석을 담당합니다.

## 역할

- 법적 분쟁 분석
- 규제 리스크 평가
- 부도/파산 위험 평가
- 회생절차 분석

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/legal_compliance_agent.py`
- **도구 설명**: `app/agents/dart_agent/utils/prompt_templates/legal_compliance_tools.py`

## 사용 도구 (7개)

### 경영위기 도구 (4개)
- `get_bankruptcy`: 부도 발생 사실 조회
- `get_business_suspension`: 영업정지 사실 조회
- `get_rehabilitation`: 회생절차 개시신청 사실 조회
- `get_dissolution`: 해산사유 발생 사실 조회

### 채권관리 도구 (2개)
- `get_creditor_management`: 채권은행 관리절차 개시 사실 조회
- `get_creditor_management_termination`: 채권은행 관리절차 종료 사실 조회

### 법적분쟁 도구 (1개)
- `get_lawsuit`: 소송 제기 사실 조회

## 코드 패턴

### BaseAgent 상속

```python
class LegalComplianceAgent(DartBaseAgent):
    """법적컴플라이언스 데이터 수집 및 분석 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="LegalComplianceAgent",
            model=model,
            max_iterations=10
        )
    
    async def analyze_legal_risk_data(
        self, 
        context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        # 법적컴플라이언스 데이터 분석
```

## 개선 가이드라인

### 법적 리스크 평가

- 소송 규모 및 중요성 분석
- 법적 분쟁이 사업에 미치는 영향 평가
- 규제 리스크 평가

### 경영위기 분석

- 부도/파산 위험 평가
- 회생절차 진행 상황 분석
- 경영위기가 재무에 미치는 영향 평가

## 주의사항

1. **리스크 수준**: 법적 리스크의 심각성 및 영향 범위 평가
2. **경영위기 신호**: 부도/파산 위험의 조기 신호 파악
3. **재무 영향**: 법적 분쟁 및 경영위기가 재무제표에 미치는 영향 분석

## 관련 파일

- `dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/utils/prompt_templates/legal_compliance_tools.py`: 법적컴플라이언스 도구 설명

