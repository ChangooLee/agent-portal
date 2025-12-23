"""
message_refiner.py
사용자 친화적 메시지로 변환하는 메시지 정제 시스템
"""


class MessageRefiner:
    """사용자 친화적 메시지로 변환"""

    def __init__(self):
        self.tool_name_mapping = {
            "get_corporation_code_by_name": "기업 코드 조회",
            "get_corporation_info": "기업 상세 정보 조회",
            "get_disclosure_list": "공시 목록 조회",
            "get_single_acnt": "재무제표 조회",
            "get_single_index": "재무지표 조회",
            "get_major_shareholder": "주주 정보 조회",
            "get_executive_info": "임원 정보 조회",
            "get_financial_analysis": "재무 분석",
            "get_risk_assessment": "리스크 평가",
            "search_financial_notes": "재무제표 주석 검색",
            "get_disclosure_document": "공시 문서 조회",
            "get_governance_info": "지배구조 정보 조회",
            "get_capital_change": "자본변동 정보 조회",
            "get_debt_funding": "부채자금조달 정보 조회",
            "get_business_structure": "사업구조 정보 조회",
            "get_overseas_business": "해외사업 정보 조회",
            "get_legal_risk": "법적리스크 정보 조회",
            "get_executive_audit": "경영진감사 정보 조회",
        }

    def refine(self, technical_message: str, message_type: str = "progress") -> str:
        """기술적 메시지를 사용자 친화적으로 변환"""
        # 도구 이름인 경우 먼저 매핑 시도
        if technical_message in self.tool_name_mapping:
            return self.tool_name_mapping[technical_message]
        
        if message_type == "tool_call":
            return self._refine_tool_call_message(technical_message)
        elif message_type == "progress":
            return self._refine_progress_message(technical_message)
        elif message_type == "result":
            return self._refine_result_message(technical_message)
        else:
            return technical_message
    
    def get_tool_display_name(self, tool_name: str) -> str:
        """도구 이름을 사용자 친화적 이름으로 변환"""
        return self.tool_name_mapping.get(tool_name, tool_name)
    
    def extract_tool_name_from_tc_id(self, tc_id: str) -> str:
        """tool_call_id에서 도구 이름 추출
        
        예: "call_get_corporation_info" -> "get_corporation_info"
        """
        if not tc_id:
            return ""
        if tc_id.startswith("call_"):
            potential_name = tc_id[5:]  # "call_" 제거
            if "_" in potential_name:
                return potential_name
        return ""

    def _refine_tool_call_message(self, message: str) -> str:
        """도구 호출 메시지 정제"""
        # 도구명 추출 및 변환
        for tool_name, korean_name in self.tool_name_mapping.items():
            if tool_name in message:
                return f"{korean_name}를 실행하고 있습니다..."

        # 기본 변환
        if "도구를 호출" in message or "tool" in message.lower():
            return "데이터를 수집하고 있습니다..."

        return message

    def _refine_progress_message(self, message: str) -> str:
        """진행 상황 메시지 정제"""
        import re
        # 이모지 제거
        message = re.sub(r"[🔥🚀📊✅❌⚠️]", "", message)

        # 기술적 용어 변환
        replacements = {
            "analyzing": "분석하고 있습니다",
            "processing": "처리하고 있습니다",
            "collecting": "수집하고 있습니다",
            "executing": "실행하고 있습니다",
            "computing": "계산하고 있습니다",
            "evaluating": "평가하고 있습니다",
        }

        for eng, kor in replacements.items():
            message = message.replace(eng, kor)

        return message.strip()

    def _refine_result_message(self, message: str) -> str:
        """결과 메시지 정제"""
        import re
        # 불필요한 로그 정보 제거
        message = re.sub(r"\[.*?\]", "", message)
        message = re.sub(r"🔥🔥🔥.*?", "", message)

        return message.strip()
