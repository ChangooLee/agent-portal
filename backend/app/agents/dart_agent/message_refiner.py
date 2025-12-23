"""
message_refiner.py
사용자 친화적 메시지로 변환하는 메시지 정제 시스템
"""


class MessageRefiner:
    """사용자 친화적 메시지로 변환"""

    def __init__(self):
        self.tool_name_mapping = {
            # 기업 기본 정보
            "get_corporation_code_by_name": "기업 코드 조회",
            "get_corporation_info": "기업 정보 조회",
            "get_corporation_code": "기업 코드 목록 조회",
            "get_disclosure_list": "공시 목록 조회",
            
            # 재무제표/지표
            "get_single_acnt": "재무제표 조회",
            "get_multi_acnt": "재무제표 비교",
            "get_single_acc": "계정과목 분석",
            "get_single_index": "재무지표 조회",
            "get_multi_index": "재무지표 비교",
            "get_xbrl_taxonomy": "XBRL 분류체계",
            
            # 문서 분석
            "get_disclosure_document": "공시 문서 다운로드",
            "search_financial_notes": "재무제표 주석 검색",
            
            # 지배구조
            "get_major_shareholder": "최대주주 조회",
            "get_major_shareholder_changes": "주주 변동 조회",
            "get_minority_shareholder": "소액주주 조회",
            "get_major_holder_changes": "대량보유 변동",
            "get_executive_trading": "임원 거래 조회",
            "get_executive_info": "임원 정보 조회",
            "get_employee_info": "직원 정보 조회",
            "get_outside_director_status": "사외이사 현황",
            
            # 자본변동
            "get_stock_increase_decrease": "증자/감자 조회",
            "get_stock_total": "주식 총수 조회",
            "get_treasury_stock": "자기주식 현황",
            "get_treasury_stock_acquisition": "자기주식 취득",
            "get_treasury_stock_disposal": "자기주식 처분",
            "get_treasury_stock_trust_contract": "신탁계약 조회",
            "get_treasury_stock_trust_termination": "신탁해지 조회",
            "get_paid_in_capital_increase": "유상증자 조회",
            "get_free_capital_increase": "무상증자 조회",
            "get_paid_free_capital_increase": "유무상증자 조회",
            "get_capital_reduction": "감자 조회",
            "get_dividend_info": "배당 정보 조회",
            
            # 부채/자금조달
            "get_debt": "채무증권 조회",
            "get_debt_securities_issued": "채무증권 발행",
            "get_convertible_bond": "전환사채 조회",
            "get_bond_with_warrant": "신주인수권부사채",
            "get_exchangeable_bond": "교환사채 조회",
            "get_write_down_bond": "조건부자본증권",
            "get_commercial_paper_outstanding": "기업어음 잔액",
            "get_short_term_bond_outstanding": "단기사채 잔액",
            "get_corporate_bond_outstanding": "회사채 잔액",
            "get_hybrid_securities_outstanding": "신종자본증권",
            "get_conditional_capital_securities_outstanding": "조건부증권 잔액",
            "get_public_capital_usage": "공모자금 사용",
            "get_private_capital_usage": "사모자금 사용",
            "get_equity": "지분증권 조회",
            "get_depository_receipt": "예탁증권 조회",
            
            # 해외사업
            "get_foreign_listing_decision": "해외상장 결정",
            "get_foreign_delisting_decision": "해외상장폐지 결정",
            "get_foreign_listing": "해외상장 현황",
            "get_foreign_delisting": "해외상장폐지",
            
            # 임원보수/감사
            "get_individual_compensation": "개별임원 보수",
            "get_total_compensation": "총임원 보수",
            "get_individual_compensation_amount": "임원보수 금액",
            "get_unregistered_exec_compensation": "미등기임원 보수",
            "get_executive_compensation_approved": "임원보수 승인",
            "get_executive_compensation_by_type": "임원보수 유형별",
            "get_accounting_auditor_opinion": "감사의견 조회",
            "get_audit_service_contract": "감사계약 조회",
            "get_non_audit_service_contract": "비감사계약 조회",
            
            # 법적 리스크
            "get_bankruptcy": "부도 조회",
            "get_business_suspension": "영업정지 조회",
            "get_rehabilitation": "회생절차 조회",
            "get_dissolution": "해산사유 조회",
            "get_creditor_management": "채권관리 조회",
            "get_creditor_management_termination": "채권관리 종료",
            "get_lawsuit": "소송 조회",
            
            # 사업구조
            "get_business_acquisition": "영업양수 조회",
            "get_business_transfer": "영업양도 조회",
            "get_merger": "합병 조회",
            "get_division": "분할 조회",
            "get_division_merger": "분할합병 조회",
            "get_stock_exchange": "주식교환 조회",
            "get_merger_report": "합병 신고서",
            "get_stock_exchange_report": "주식교환 신고서",
            "get_division_report": "분할 신고서",
            "get_other_corp_stock_acquisition": "타법인 주식 양수",
            "get_other_corp_stock_transfer": "타법인 주식 양도",
            "get_stock_related_bond_acquisition": "사채권 양수",
            "get_stock_related_bond_transfer": "사채권 양도",
            "get_tangible_asset_acquisition": "유형자산 양수",
            "get_tangible_asset_transfer": "유형자산 양도",
            "get_asset_transfer": "자산양수도 조회",
            "get_investment_in_other_corp": "타법인 출자 조회",
            
            # 기타
            "get_financial_analysis": "재무 분석",
            "get_risk_assessment": "리스크 평가",
            "get_opendart_tool_info": "도구 정보 조회",
        }
        
        # 도구별 액션 메시지 매핑 (전체 70개 도구)
        self.tool_action_messages = {
            # 재무 분석 (8개)
            "get_corporation_code_by_name": "기업 정보를 조회하고 있습니다",
            "get_corporation_info": "기업 상세 정보를 확인하고 있습니다",
            "get_disclosure_list": "공시 목록을 검색하고 있습니다",
            "get_single_acnt": "재무제표를 조회하고 있습니다",
            "get_multi_acnt": "여러 기업의 재무제표를 비교하고 있습니다",
            "get_single_acc": "계정과목을 분석하고 있습니다",
            "get_single_index": "재무지표를 계산하고 있습니다",
            "get_multi_index": "여러 기업의 재무지표를 비교하고 있습니다",
            
            # 문서 분석 (3개)
            "get_disclosure_document": "공시 문서를 다운로드하고 있습니다",
            "search_financial_notes": "재무제표 주석을 검색하고 있습니다",
            "get_corporation_code": "전체 기업 고유번호 목록을 조회하고 있습니다",
            
            # 지배구조 (8개)
            "get_major_shareholder": "최대주주 정보를 조회하고 있습니다",
            "get_major_shareholder_changes": "주주 지분 변동 내역을 확인하고 있습니다",
            "get_minority_shareholder": "소액주주 현황을 파악하고 있습니다",
            "get_major_holder_changes": "5% 이상 주주의 변동을 추적하고 있습니다",
            "get_executive_trading": "임원 주식 거래 내역을 조회하고 있습니다",
            "get_executive_info": "임원 현황을 확인하고 있습니다",
            "get_employee_info": "직원 정보를 조회하고 있습니다",
            "get_outside_director_status": "사외이사 현황을 파악하고 있습니다",
            
            # 자본변동 (11개)
            "get_stock_increase_decrease": "증자/감자 현황을 조회하고 있습니다",
            "get_stock_total": "주식 총수를 확인하고 있습니다",
            "get_treasury_stock": "자기주식 현황을 파악하고 있습니다",
            "get_treasury_stock_acquisition": "자기주식 취득 결정을 검토하고 있습니다",
            "get_treasury_stock_disposal": "자기주식 처분 내역을 조회하고 있습니다",
            "get_treasury_stock_trust_contract": "자기주식 신탁계약을 확인하고 있습니다",
            "get_treasury_stock_trust_termination": "신탁계약 해지 내역을 조회하고 있습니다",
            "get_paid_in_capital_increase": "유상증자 결정을 검토하고 있습니다",
            "get_free_capital_increase": "무상증자 현황을 확인하고 있습니다",
            "get_paid_free_capital_increase": "유무상증자 내역을 조회하고 있습니다",
            "get_capital_reduction": "감자 결정을 파악하고 있습니다",
            
            # 부채 및 자금조달 (15개)
            "get_debt": "채무증권 발행 내역을 조회하고 있습니다",
            "get_debt_securities_issued": "채무증권 발행 실적을 확인하고 있습니다",
            "get_convertible_bond": "전환사채 발행을 검토하고 있습니다",
            "get_bond_with_warrant": "신주인수권부사채를 조회하고 있습니다",
            "get_exchangeable_bond": "교환사채 정보를 확인하고 있습니다",
            "get_write_down_bond": "조건부자본증권을 파악하고 있습니다",
            "get_commercial_paper_outstanding": "기업어음 미상환 잔액을 조회하고 있습니다",
            "get_short_term_bond_outstanding": "단기사채 잔액을 확인하고 있습니다",
            "get_corporate_bond_outstanding": "회사채 미상환 잔액을 파악하고 있습니다",
            "get_hybrid_securities_outstanding": "신종자본증권을 조회하고 있습니다",
            "get_conditional_capital_securities_outstanding": "조건부자본증권 잔액을 확인하고 있습니다",
            "get_public_capital_usage": "공모자금 사용내역을 검토하고 있습니다",
            "get_private_capital_usage": "사모자금 사용처를 파악하고 있습니다",
            "get_equity": "지분증권 발행 내역을 조회하고 있습니다",
            "get_depository_receipt": "예탁증권 정보를 확인하고 있습니다",
            
            # 해외사업 (4개)
            "get_foreign_listing_decision": "해외상장 결정을 검토하고 있습니다",
            "get_foreign_delisting_decision": "해외상장폐지를 확인하고 있습니다",
            "get_foreign_listing": "해외상장 현황을 조회하고 있습니다",
            "get_foreign_delisting": "해외상장폐지 내역을 파악하고 있습니다",
            
            # 임원보수 및 감사 (9개)
            "get_individual_compensation": "개별임원보수를 조회하고 있습니다",
            "get_total_compensation": "총임원보수를 확인하고 있습니다",
            "get_individual_compensation_amount": "개별임원보수금액을 파악하고 있습니다",
            "get_unregistered_exec_compensation": "미등기임원보수를 조회하고 있습니다",
            "get_executive_compensation_approved": "임원보수승인을 확인하고 있습니다",
            "get_executive_compensation_by_type": "임원보수유형별 현황을 파악하고 있습니다",
            "get_accounting_auditor_opinion": "회계감사인의견을 조회하고 있습니다",
            "get_audit_service_contract": "감사서비스계약을 확인하고 있습니다",
            "get_non_audit_service_contract": "비감사서비스계약을 파악하고 있습니다",
            
            # 법적 리스크 (7개)
            "get_bankruptcy": "부도 발생 사실을 조회하고 있습니다",
            "get_business_suspension": "영업정지 사실을 확인하고 있습니다",
            "get_rehabilitation": "회생절차 개시신청을 파악하고 있습니다",
            "get_dissolution": "해산사유 발생을 조회하고 있습니다",
            "get_creditor_management": "채권은행 관리절차를 확인하고 있습니다",
            "get_creditor_management_termination": "채권은행 관리절차 종료를 파악하고 있습니다",
            "get_lawsuit": "소송 제기 사실을 조회하고 있습니다",
            
            # 사업구조 변화 (17개)
            "get_business_acquisition": "영업양수 결정을 조회하고 있습니다",
            "get_business_transfer": "영업양도 결정을 확인하고 있습니다",
            "get_merger": "회사합병 결정을 파악하고 있습니다",
            "get_division": "회사분할 결정을 조회하고 있습니다",
            "get_division_merger": "분할합병 결정을 확인하고 있습니다",
            "get_stock_exchange": "주식교환/이전 결정을 파악하고 있습니다",
            "get_merger_report": "합병 증권신고서를 조회하고 있습니다",
            "get_stock_exchange_report": "주식교환/이전 증권신고서를 확인하고 있습니다",
            "get_division_report": "분할 증권신고서를 파악하고 있습니다",
            "get_other_corp_stock_acquisition": "타법인 주식 양수 결정을 조회하고 있습니다",
            "get_other_corp_stock_transfer": "타법인 주식 양도 결정을 확인하고 있습니다",
            "get_stock_related_bond_acquisition": "주권 관련 사채권 양수를 파악하고 있습니다",
            "get_stock_related_bond_transfer": "주권 관련 사채권 양도를 조회하고 있습니다",
            "get_tangible_asset_acquisition": "유형자산 양수 결정을 확인하고 있습니다",
            "get_tangible_asset_transfer": "유형자산 양도 결정을 파악하고 있습니다",
            "get_asset_transfer": "자산양수도 계약을 조회하고 있습니다",
            "get_investment_in_other_corp": "타법인 출자 현황을 확인하고 있습니다",
        }

    def refine(self, technical_message: str, message_type: str = "progress") -> str:
        """기술적 메시지를 사용자 친화적으로 변환"""
        if technical_message is None:
            return ""
        
        # 도구 이름인 경우 먼저 매핑 시도 (한국어 이름 반환)
        if technical_message in self.tool_name_mapping:
            return self.tool_name_mapping[technical_message]
        
        # tool_action_messages에서도 확인 (더 많은 도구 포함)
        if technical_message in self.tool_action_messages:
            # 액션 메시지에서 도구명 추출 ("기업 정보를 조회하고 있습니다" -> "기업 정보 조회")
            action_msg = self.tool_action_messages[technical_message]
            if action_msg.endswith("있습니다"):
                # "조회하고 있습니다" -> "조회"
                return action_msg.replace("하고 있습니다", "").replace("을 ", " ").replace("를 ", " ").strip()
            return action_msg
        
        if message_type == "tool_call":
            return self._refine_tool_call_message(technical_message)
        elif message_type == "progress":
            return self._refine_progress_message(technical_message)
        elif message_type == "result":
            return self._refine_result_message(technical_message)
        else:
            return technical_message

    def _refine_tool_call_message(self, message: str) -> str:
        """도구 호출 메시지 정제"""
        # tool_action_messages에서 먼저 확인 (더 많은 도구 포함)
        if message in self.tool_action_messages:
            return self.tool_action_messages[message]
        
        # tool_name_mapping에서 확인
        if message in self.tool_name_mapping:
            return f"{self.tool_name_mapping[message]}를 실행하고 있습니다..."

        # 도구명 추출 및 변환 (메시지에 도구명이 포함된 경우)
        for tool_name, korean_name in self.tool_name_mapping.items():
            if tool_name in message:
                return f"{korean_name}를 실행하고 있습니다..."

        # 기본 변환
        if "도구를 호출" in message or "tool" in message.lower():
            return "데이터를 수집하고 있습니다..."

        return message

    def _refine_progress_message(self, message: str) -> str:
        """진행 상황 메시지 정제"""
        if message is None:
            return ""
        
        import re
        # 이모지 제거
        message = re.sub(r"[🔥🚀📊✅❌⚠️]", "", str(message))

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
    
    def get_action_message(self, tool_name: str) -> str:
        """도구 호출 시 사용자 친화적 액션 메시지 반환 (즉시 반환, 블로킹 없음)"""
        return self.tool_action_messages.get(
            tool_name, 
            f"{self.refine(tool_name)}를 실행하고 있습니다"
        )
