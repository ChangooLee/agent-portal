---
name: executive-audit-agent
description: 임원감사 데이터 수집 및 분석 전문 에이전트 - 임원 보수, 감사계약, 회계감사 분석
---

# Executive Audit Agent

임원감사 데이터 수집 및 분석 전문 에이전트입니다. 임원 보수, 감사계약, 회계감사 분석을 담당합니다.

## 역할

- 보수 한도 분석
- 고액보수자 현황 분석
- 감사의견 적정성 평가
- 감사계약 투명성 분석

## 파일 위치

- **메인 파일**: `app/agents/dart_agent/executive_audit_agent.py`
- **도구 설명**: `app/agents/dart_agent/utils/prompt_templates/executive_audit_tools.py`

## 사용 도구 (9개)

### 임원보수 도구 (6개)
- `get_individual_compensation`: 개별임원보수 조회
- `get_total_compensation`: 총임원보수 조회
- `get_individual_compensation_amount`: 개별임원보수금액 조회
- `get_unregistered_exec_compensation`: 미등기임원보수 조회
- `get_executive_compensation_approved`: 임원보수승인 조회
- `get_executive_compensation_by_type`: 임원보수유형별 조회

### 감사 관련 도구 (3개)
- `get_accounting_auditor_opinion`: 회계감사인의견 조회
- `get_audit_service_contract`: 감사서비스계약 조회
- `get_non_audit_service_contract`: 비감사서비스계약 조회

## 코드 패턴

### BaseAgent 상속

```python
class ExecutiveAuditAgent(DartBaseAgent):
    """임원감사 데이터 수집 및 분석 전문 에이전트"""
    
    def __init__(self, model: str = "qwen-235b"):
        super().__init__(
            agent_name="ExecutiveAuditAgent",
            model=model,
            max_iterations=10
        )
    
    async def analyze_executive_audit_data(
        self, 
        context: AnalysisContext
    ) -> AsyncGenerator[Dict[str, Any], AgentResult]:
        # 임원감사 데이터 분석
```

## 개선 가이드라인

### 보수 분석

- 보수 한도 준수 여부 확인
- 고액보수자 현황 및 변동 추이 분석
- 보수 구조의 적정성 평가

### 감사 분석

- 감사의견의 적정성 평가
- 감사계약의 투명성 분석
- 비감사서비스 계약 분석

## 주의사항

1. **보수 한도**: 법적 보수 한도 준수 여부 확인
2. **감사의견**: 감사의견의 적정성 및 신뢰성 평가
3. **투명성**: 감사계약의 투명성 및 독립성 평가

## 관련 파일

- `dart_master_agent.py`: 마스터 조정 에이전트
- `app/agents/dart_agent/utils/prompt_templates/executive_audit_tools.py`: 임원감사 도구 설명

