"""
프롬프트 조합기
공통 템플릿과 도메인별 특화 부분을 조합하여 최종 프롬프트 생성
"""

from typing import Dict, Any
from app.agents.dart_agent.dart_types import AnalysisContext
from .base_prompt import BasePromptTemplate
from .domain_specific import DomainSpecificTemplates


class PromptBuilder:
    """프롬프트 조합기"""

    def __init__(self):
        self.base_template = BasePromptTemplate()
        self.domain_template = DomainSpecificTemplates()

    def build_system_prompt(self, domain: str) -> str:
        """에이전트 초기화용 System Prompt 생성 - 도구 설명과 분석 방법 포함"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[PromptBuilder] build_system_prompt 호출: domain={domain}")
        
        domain_name = self.domain_template.get_domain_name(domain)
        system_prompt = self.base_template.get_system_prompt(domain_name)
        
        # 도메인별 역할 설명 추가
        domain_role = self.domain_template.get_system_role_description(domain)
        
        # 도구 설명 추가
        tools_info = self._get_tools_description(domain)
        
        # 도메인별 분석 지침 추가
        domain_guidelines = self.domain_template.get_domain_specific_prompt(domain)
        
        # 작업 지시사항 추가
        work_instructions = self.base_template.get_work_instructions()
        
        # 문서 분석 워크플로우 (해당 시)
        document_workflow = ""
        if domain == "document_analysis":
            document_workflow = self.base_template.get_document_analysis_workflow()
        
        final_prompt = f"""{system_prompt}

## 도메인 전문성
{domain_role}

{tools_info}

{domain_guidelines}

{work_instructions}

{document_workflow}"""
        
        logger.info(f"[PromptBuilder] 프롬프트 생성 완료: domain={domain}, 길이={len(final_prompt)}자")
        logger.debug(f"[PromptBuilder] 생성된 프롬프트 시작 부분:\n{final_prompt[:300]}...")
        
        return final_prompt

    def build_user_request_prompt(self, context: AnalysisContext, domain: str, tools_info: str) -> str:
        """실행 시 User Prompt 생성 - 간소화된 동적 context만 포함"""
        # 사용자 요청 기본 정보만 포함 (도구 설명, 분석 지침, 워크플로우는 System Prompt로 이동)
        user_request = self.base_template.get_user_request_prompt(context)
        
        return user_request

    def build_analysis_prompt(self, context: AnalysisContext, domain: str, tools_info: str) -> str:
        """분석 프롬프트 조합 - 하위 호환성을 위해 유지"""
        return self.build_user_request_prompt(context, domain, tools_info)

    def _get_tools_description(self, domain: str) -> str:
        """도메인별 도구 설명 반환"""
        tools_header = self.domain_template.get_tools_section_header(domain)
        
        # 도메인별 도구 설명 가져오기
        if domain == "financial":
            from .financial_tools import get_financial_tools_description
            tools_info = get_financial_tools_description()
        elif domain == "governance":
            from .governance_tools import get_governance_tools_description
            tools_info = get_governance_tools_description()
        elif domain == "capital_change":
            from .capital_change_tools import get_capital_change_tools_description
            tools_info = get_capital_change_tools_description()
        elif domain == "debt_funding":
            from .debt_funding_tools import get_debt_funding_tools_description
            tools_info = get_debt_funding_tools_description()
        elif domain == "business_structure":
            from .business_structure_tools import get_business_structure_tools_description
            tools_info = get_business_structure_tools_description()
        elif domain == "overseas_business":
            from .overseas_business_tools import get_overseas_business_tools_description
            tools_info = get_overseas_business_tools_description()
        elif domain == "legal_risk":
            from .legal_compliance_tools import get_legal_compliance_tools_description
            tools_info = get_legal_compliance_tools_description()
        elif domain == "executive_audit":
            from .executive_audit_tools import get_executive_audit_tools_description
            tools_info = get_executive_audit_tools_description()
        elif domain == "document_analysis":
            from .document_analysis_tools import get_document_analysis_tools_description
            tools_info = get_document_analysis_tools_description()
        else:
            tools_info = "사용 가능한 도구가 없습니다."
        
        return f"""{tools_header}

{tools_info}"""

    def _build_tools_section(self, domain: str, tools_info: str) -> str:
        """도구 정보 섹션 구성"""
        tools_header = self.domain_template.get_tools_section_header(domain)
        return f"""{tools_header}

{tools_info}"""
