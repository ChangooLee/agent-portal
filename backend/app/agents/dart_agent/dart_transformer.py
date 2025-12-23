"""
dart_transformer.py
DART 에이전트 전용 결과 변환기
"""

import json
import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta

# 로거 설정
logger = logging.getLogger(__name__)


def log_step(step_name: str, status: str, message: str):
    """로깅 헬퍼 함수"""
    log_message = f"[{step_name}] {status}: {message}"
    if status == "ERROR":
        logger.error(log_message)
    elif status == "WARNING":
        logger.warning(log_message)
    else:
        logger.info(log_message)


def transform_dart_result(tool_name: str, data: Any) -> str:
    """DART 관련 도구 결과 변환"""
    
    try:
        # 로깅: 도구명과 입력 데이터 타입 확인
        data_type = type(data).__name__
        if isinstance(data, str):
            data_size = len(data)
            log_step(f"DART 변환 시작: {tool_name}", "INFO", f"문자열 데이터 크기: {data_size}자")
        else:
            log_step(f"DART 변환 시작: {tool_name}", "INFO", f"데이터 타입: {data_type}")
        
        # 도구별 변환 함수 호출
        if tool_name == "search_financial_notes":
            return _transform_search_financial_notes_result(data)
        elif tool_name == "get_single_acnt":
            transformed_data = _transform_single_acnt_statement_result(data)
        elif tool_name == "get_corporation_code_by_name":
            transformed_data = _transform_corporation_code_result(data)
        elif tool_name == "get_disclosure_list":
            transformed_data = _transform_disclosure_list_result(data)
        elif tool_name == "get_corporation_info":
            transformed_data = _transform_corporation_info_combined_result(data)
        elif tool_name == "get_multi_acnt":
            transformed_data = _transform_multi_acnt_result(data)
        elif tool_name == "get_single_acc":
            transformed_data = _transform_single_acc_result(data)
        elif tool_name == "get_multi_index":
            transformed_data = _transform_multi_index_result(data)
        elif tool_name == "get_major_shareholder":
            transformed_data = _transform_major_shareholder_result(data)
        elif tool_name == "get_major_holder_changes":
            transformed_data = _transform_major_holder_changes_result(data)
        elif tool_name == "get_executive_trading":
            transformed_data = _transform_executive_trading_result(data)
        elif tool_name == "get_executive_info":
            transformed_data = _transform_executive_info_result(data)
        elif tool_name == "get_employee_info":
            transformed_data = _transform_employee_info_result(data)
        elif tool_name == "get_bond_with_warrant":
            transformed_data = _transform_bond_with_warrant_result(data)
        elif tool_name == "get_debt":
            # 전자단기사채 통계를 LLM용 텍스트로 변환
            log_step("전자단기사채 변환", "INFO", "전자단기사채 통계 변환 시작")
            return _format_debt_statistics_for_llm(data)
        elif tool_name == "get_debt_securities_issued":
            # 회사채 통계를 LLM용 텍스트로 변환
            log_step("회사채 변환", "INFO", "회사채 통계 변환 시작")
            return _format_debt_securities_statistics_for_llm(data)
        elif tool_name == "get_investment_in_other_corp":
            # 타법인 출자현황 통계를 LLM용 텍스트로 변환
            log_step("타법인 출자현황 변환", "INFO", "타법인 출자현황 통계 변환 시작")
            return _format_investment_statistics_for_llm(data)
        else:
            log_step(f"DART 변환 완료: {tool_name}", "SUCCESS", "기본 JSON 변환")
            return json.dumps(data, ensure_ascii=False, indent=2)
        
        # items 배열이 있으면 items만 반환
        if (
            isinstance(transformed_data, dict)
            and "items" in transformed_data
            and isinstance(transformed_data["items"], list)
        ):
            log_step(f"DART 변환 완료: {tool_name}", "SUCCESS", f"items 배열 반환: {len(transformed_data['items'])}개")
            return json.dumps(transformed_data["items"], ensure_ascii=False, indent=2)
        # list 배열이 있으면 list만 반환
        elif (
            isinstance(transformed_data, dict)
            and "list" in transformed_data
            and isinstance(transformed_data["list"], list)
        ):
            log_step(f"DART 변환 완료: {tool_name}", "SUCCESS", f"list 배열 반환: {len(transformed_data['list'])}개")
            return json.dumps(transformed_data["list"], ensure_ascii=False, indent=2)
        # 그 외의 경우는 전체 데이터 반환
        else:
            log_step(f"DART 변환 완료: {tool_name}", "SUCCESS", "전체 데이터 반환")
            return json.dumps(transformed_data, ensure_ascii=False, indent=2)
            
    except Exception as e:
        log_step(f"DART 변환 오류: {tool_name}", "ERROR", f"오류: {str(e)[:200]}")
        print(f"[ERROR] DART transform 오류: {e}")
        return json.dumps(data, ensure_ascii=False, indent=2)


# =============================================================================
# 정규식 기반 데이터 추출 함수들
# =============================================================================

def _extract_items_with_regex(items_text: str) -> List[Dict[str, Any]]:
    """정규식으로 개별 항목들을 추출 (정확한 DART API 필드명 사용)"""
    import re
    items = []
    
    # 각 항목을 찾는 정규식 (중괄호로 감싸진 객체)
    item_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    item_matches = re.findall(item_pattern, items_text)
    
    for item_text in item_matches:
        item = {}
        
        # DART API 실제 필드명들
        fields = {
            'facvalu_totamt': r'"facvalu_totamt":\s*"([^"]+)"',  # 발행금액
            'intrt': r'"intrt":\s*"([^"]+)"',                    # 이자율
            'isu_de': r'"isu_de":\s*"([^"]+)"',                  # 발행일
            'isu_cmpny': r'"isu_cmpny":\s*"([^"]+)"',            # 발행기관
            'scrits_knd_nm': r'"scrits_knd_nm":\s*"([^"]+)"',    # 채권종류
            'repy_at': r'"repy_at":\s*"([^"]+)"',                # 상환상태
            'mtd': r'"mtd":\s*"([^"]+)"',                        # 만기일
            'evl_grad_instt': r'"evl_grad_instt":\s*"([^"]+)"'   # 신용등급
        }
        
        for field, pattern in fields.items():
            match = re.search(pattern, item_text)
            if match:
                item[field] = match.group(1)
        
        if item:  # 유효한 데이터가 있으면 추가
            items.append(item)
    
    return items

def _extract_and_calculate_statistics_directly(raw_data: str) -> str:
    """
    JSON 파싱 없이 정규식으로 데이터 추출 후 통계 계산

    DART API 응답이 매우 큰 경우 `json.loads`가 실패할 수 있으므로
    문자열에서 직접 필요한 필드를 추출하여 통계를 계산합니다. 이 함수는
    `_extract_items_with_regex`를 통해 전체 항목 목록을 만드는 대신,
    `re.finditer`를 사용하여 각 항목을 순회하면서 필요한 값만 추출해
    메모리 사용량을 최소화합니다.
    """
    import re
    # log_step already defined at module level

    # 로깅: 원본 데이터 크기 확인
    log_step("회사채 데이터 파싱 시작", "INFO", f"원본 데이터 크기: {len(raw_data)}자")
    log_step("회사채 원본 데이터 샘플", "DEBUG", f"데이터 시작 500자: {raw_data[:500]}")

    # 1. 상태 코드 확인
    status_match = re.search(r'"status":\s*"([^"]+)"', raw_data)
    if status_match:
        status_code = status_match.group(1)
        log_step("회사채 상태 코드 확인", "INFO", f"상태코드: {status_code}")
        if status_code != "000":
            log_step("회사채 상태 오류", "ERROR", f"상태코드: {status_code}")
            return f"회사채 조회 오류: 상태코드 {status_code}"
    else:
        log_step("회사채 상태 코드 없음", "WARNING", "status 필드를 찾을 수 없음")

    # 2. list 배열 내부 데이터 추출
    list_match = re.search(r'"list":\s*\[(.*?)\]', raw_data, re.DOTALL)
    if not list_match:
        log_step("회사채 데이터 없음", "WARNING", "list 배열을 찾을 수 없음")
        log_step("회사채 데이터 검색", "DEBUG", f"list 패턴 검색 결과: {list_match}")
        return "회사채 데이터가 없습니다."

    items_text = list_match.group(1)
    log_step("회사채 데이터 추출", "INFO", f"list 배열 크기: {len(items_text)}자")
    log_step("회사채 list 내용 샘플", "DEBUG", f"list 내용 시작 300자: {items_text[:300]}")

    # 3. 개별 항목들을 순회하며 필요한 값만 추출
    # 각 항목을 찾는 정규식 (중괄호로 감싸진 객체).
    # re.finditer를 사용하여 메모리를 절약합니다.
    item_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    log_step("회사채 아이템 패턴", "DEBUG", f"사용할 정규식 패턴: {item_pattern}")
   
    total_amount = 0.0
    total_count = 0
    interest_rates: List[float] = []
    amounts: List[float] = []
    months: List[str] = []
    companies: List[str] = []
    types: List[str] = []
    repayment_statuses: List[str] = []

    # 필드별 정규식 (DART API 실제 필드명 사용)
    field_patterns = {
        'facvalu_totamt': r'"facvalu_totamt":\s*"([^"]+)"',
        'intrt': r'"intrt":\s*"([^"]+)"',
        'isu_de': r'"isu_de":\s*"([^"]+)"',
        'isu_cmpny': r'"isu_cmpny":\s*"([^"]+)"',
        'scrits_knd_nm': r'"scrits_knd_nm":\s*"([^"]+)"',
        'repy_at': r'"repy_at":\s*"([^"]+)"'
    }
    log_step("회사채 필드 패턴", "DEBUG", f"필드별 정규식 패턴: {field_patterns}")

    for match in re.finditer(item_pattern, items_text):
        item_text = match.group(0)
        total_count += 1
        log_step("회사채 아이템 처리", "DEBUG", f"처리 중인 아이템 #{total_count}, 길이: {len(item_text)}자")
        log_step("회사채 아이템 샘플", "DEBUG", f"아이템 내용: {item_text[:200]}...")
        
        # 금액 처리
        amount_str_match = re.search(field_patterns['facvalu_totamt'], item_text)
        if amount_str_match:
            amount_str = amount_str_match.group(1)
            log_step("회사채 금액 매칭", "DEBUG", f"금액 문자열: {amount_str}")
            try:
                amount = float(amount_str.replace(",", ""))
                log_step("회사채 금액 변환", "DEBUG", f"변환된 금액: {amount}")
            except ValueError as e:
                amount = 0.0
                log_step("회사채 금액 변환 실패", "WARNING", f"금액 변환 오류: {e}, 원본: {amount_str}")
        else:
            amount = 0.0
            log_step("회사채 금액 매칭 실패", "WARNING", f"facvalu_totamt 필드를 찾을 수 없음")
        total_amount += amount
        amounts.append(amount)

        # 이자율 처리
        rate_str_match = re.search(field_patterns['intrt'], item_text)
        if rate_str_match:
            rate_str = rate_str_match.group(1)
            log_step("회사채 이자율 매칭", "DEBUG", f"이자율 문자열: {rate_str}")
            try:
                rate = float(rate_str.replace("%", ""))
                interest_rates.append(rate)
                log_step("회사채 이자율 변환", "DEBUG", f"변환된 이자율: {rate}")
            except ValueError as e:
                log_step("회사채 이자율 변환 실패", "WARNING", f"이자율 변환 오류: {e}, 원본: {rate_str}")
        else:
            log_step("회사채 이자율 매칭 실패", "WARNING", f"intrt 필드를 찾을 수 없음")

        # 발행월 처리
        date_match = re.search(field_patterns['isu_de'], item_text)
        if date_match:
            date_str = date_match.group(1)
            log_step("회사채 발행일 매칭", "DEBUG", f"발행일 문자열: {date_str}")
            # 날짜는 'YYYY.MM.DD' 형식으로 가정
            parts = date_str.split('.')
            if len(parts) >= 2:
                month_str = f"{parts[0]}년 {parts[1]}월"
                months.append(month_str)
                log_step("회사채 발행월 변환", "DEBUG", f"변환된 발행월: {month_str}")
            else:
                months.append("")
                log_step("회사채 발행월 변환 실패", "WARNING", f"날짜 형식 오류: {date_str}")
        else:
            months.append("")
            log_step("회사채 발행일 매칭 실패", "WARNING", f"isu_de 필드를 찾을 수 없음")

        # 기관 처리
        company_match = re.search(field_patterns['isu_cmpny'], item_text)
        if company_match:
            company = company_match.group(1)
            companies.append(company)
            log_step("회사채 발행기관 매칭", "DEBUG", f"발행기관: {company}")
        else:
            companies.append("")
            log_step("회사채 발행기관 매칭 실패", "WARNING", f"isu_cmpny 필드를 찾을 수 없음")

        # 종류 처리
        type_match = re.search(field_patterns['scrits_knd_nm'], item_text)
        if type_match:
            bond_type = type_match.group(1)
            types.append(bond_type)
            log_step("회사채 종류 매칭", "DEBUG", f"채권 종류: {bond_type}")
        else:
            types.append("")
            log_step("회사채 종류 매칭 실패", "WARNING", f"scrits_knd_nm 필드를 찾을 수 없음")

        # 상환상태 처리
        repy_match = re.search(field_patterns['repy_at'], item_text)
        if repy_match:
            status = repy_match.group(1)
            repayment_statuses.append(status)
            log_step("회사채 상환상태 매칭", "DEBUG", f"상환상태: {status}")
        else:
            repayment_statuses.append("")
            log_step("회사채 상환상태 매칭 실패", "WARNING", f"repy_at 필드를 찾을 수 없음")

    # 데이터가 하나도 없는 경우
    if total_count == 0:
        log_step("회사채 데이터 없음", "WARNING", "파싱된 항목이 없음")
        log_step("회사채 아이템 패턴 매칭", "DEBUG", f"정규식 패턴으로 찾은 매칭 수: {len(list(re.finditer(item_pattern, items_text)))}")
        return "회사채 데이터가 없습니다."

    log_step("회사채 데이터 파싱 완료", "SUCCESS", f"총 {total_count}개 항목, 총 금액: {total_amount:,.0f}원")
    log_step("회사채 수집된 데이터", "DEBUG", f"금액 리스트 길이: {len(amounts)}, 이자율 리스트 길이: {len(interest_rates)}")
    log_step("회사채 수집된 데이터", "DEBUG", f"발행월 리스트 길이: {len(months)}, 기관 리스트 길이: {len(companies)}")
    log_step("회사채 수집된 데이터", "DEBUG", f"종류 리스트 길이: {len(types)}, 상환상태 리스트 길이: {len(repayment_statuses)}")

    # 4. 통계 계산: 수집한 리스트들을 사용하여 통계 계산
    statistics = {
        "기본통계": {
            "총발행금액": total_amount,
            "총발행건수": total_count,
            "평균발행금액": total_amount / total_count if total_count > 0 else 0,
            # 이자율 범위는 3자리 소수까지 표시하여 정밀도를 높임
            "이자율범위": (lambda: (
                f"{min(interest_rates):.3f}% ~ {max(interest_rates):.3f}%"
                if interest_rates else "데이터 없음"
            ))(),
        },
        "월별통계": _group_by_month(months, amounts),
        "금액별통계": _group_by_amount(amounts),
        "이자율별통계": _group_by_rate(interest_rates),
        "기관별통계": _group_by_company(companies, amounts),
        "종류별통계": _group_by_type(types, amounts),
        "상환상태별통계": _group_by_repayment_status(repayment_statuses, amounts)
    }

    # 5. LLM용 텍스트 포맷팅
    return _format_debt_securities_statistics_text(statistics)

def _extract_and_calculate_debt_statistics_directly(raw_data: str) -> str:
    """
    전자단기사채용 JSON 파싱 없이 정규식으로 데이터 추출 후 통계 계산

    `get_debt` 도구의 응답이 크거나 JSON 파싱이 실패할 때를 대비하여,
    문자열에서 직접 필요한 값을 추출하여 통계를 계산합니다. 각 항목을
    `re.finditer`로 순회하며 메모리 사용을 최소화합니다.
    """
    import re
    # log_step already defined at module level

    # 로깅: 원본 데이터 크기 확인
    log_step("전자단기사채 데이터 파싱 시작", "INFO", f"원본 데이터 크기: {len(raw_data)}자")

    # 1. 상태 코드 확인
    status_match = re.search(r'"status":\s*"([^"]+)"', raw_data)
    if status_match and status_match.group(1) != "000":
        log_step("전자단기사채 상태 오류", "ERROR", f"상태코드: {status_match.group(1)}")
        return f"전자단기사채 조회 오류: 상태코드 {status_match.group(1)}"

    # 2. list 배열 내부 데이터 추출
    list_match = re.search(r'"list":\s*\[(.*?)\]', raw_data, re.DOTALL)
    if not list_match:
        log_step("전자단기사채 데이터 없음", "WARNING", "list 배열을 찾을 수 없음")
        return "전자단기사채 데이터가 없습니다."

    items_text = list_match.group(1)
    log_step("전자단기사채 데이터 추출", "INFO", f"list 배열 크기: {len(items_text)}자")

    # 3. 개별 항목들을 순회하며 필요한 값만 추출
    item_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'

    total_amount = 0.0
    total_count = 0
    interest_rates: List[float] = []
    amounts: List[float] = []
    months: List[str] = []
    companies: List[str] = []
    types: List[str] = []
    repayment_statuses: List[str] = []

    # 필드별 정규식 (전자단기사채의 변환된 필드명 사용)
    # get_debt 도구의 결과 변환 과정에서 DART API 필드가 한글 이름으로 변환될 수 있으므로
    # '발행금액', '이자율', '발행월', '발행기관', '채무증권종류', '상환상태'를 사용합니다.
    field_patterns = {
        'amount': r'"facvalu_totamt":\s*"([^\"]+)"|"발행금액":\s*"([^\"]+)"',
        'rate': r'"intrt":\s*"([^\"]+)"|"이자율":\s*"([^\"]+)"',
        'month': r'"isu_de":\s*"([^\"]+)"|"발행월":\s*"([^\"]+)"',
        'company': r'"isu_cmpny":\s*"([^\"]+)"|"발행기관":\s*"([^\"]+)"',
        'type': r'"scrits_knd_nm":\s*"([^\"]+)"|"채무증권종류":\s*"([^\"]+)"',
        'status': r'"repy_at":\s*"([^\"]+)"|"상환상태":\s*"([^\"]+)"'
    }

    for match in re.finditer(item_pattern, items_text):
        item_text = match.group(0)
        total_count += 1
        # 금액 처리
        amount_match = re.search(field_patterns['amount'], item_text)
        if amount_match:
            amount_str = amount_match.group(1) or amount_match.group(2) or ""
            try:
                amount = float(amount_str.replace(",", ""))
            except ValueError:
                amount = 0.0
        else:
            amount = 0.0
        total_amount += amount
        amounts.append(amount)

        # 이자율 처리
        rate_match = re.search(field_patterns['rate'], item_text)
        if rate_match:
            rate_str = rate_match.group(1) or rate_match.group(2) or ""
            try:
                rate = float(rate_str.replace("%", ""))
                interest_rates.append(rate)
            except ValueError:
                pass

        # 발행월 처리
        month_match = re.search(field_patterns['month'], item_text)
        if month_match:
            date_str = month_match.group(1) or month_match.group(2) or ""
            # 날짜는 'YYYY.MM.DD' 또는 'YYYYMM' 등으로 들어올 수 있습니다.
            if "." in date_str:
                parts = date_str.split('.')
                if len(parts) >= 2:
                    months.append(f"{parts[0]}년 {parts[1]}월")
            elif len(date_str) >= 6:
                months.append(f"{date_str[:4]}년 {date_str[4:6]}월")
            else:
                months.append("")
        else:
            months.append("")

        # 기관 처리
        company_match = re.search(field_patterns['company'], item_text)
        if company_match:
            company = company_match.group(1) or company_match.group(2) or ""
            companies.append(company)
        else:
            companies.append("")

        # 종류 처리
        type_match = re.search(field_patterns['type'], item_text)
        if type_match:
            debt_type = type_match.group(1) or type_match.group(2) or ""
            types.append(debt_type)
        else:
            types.append("")

        # 상환상태 처리
        status_match_item = re.search(field_patterns['status'], item_text)
        if status_match_item:
            status = status_match_item.group(1) or status_match_item.group(2) or ""
            repayment_statuses.append(status)
        else:
            repayment_statuses.append("")

    # 데이터가 하나도 없는 경우
    if total_count == 0:
        log_step("전자단기사채 데이터 없음", "WARNING", "파싱된 항목이 없음")
        return "전자단기사채 데이터가 없습니다."

    log_step("전자단기사채 데이터 파싱 완료", "SUCCESS", f"총 {total_count}개 항목, 총 금액: {total_amount:,.0f}원")

    # 4. 통계 계산
    statistics = {
        "기본통계": {
            "총발행금액": total_amount,
            "총발행건수": total_count,
            "평균발행금액": total_amount / total_count if total_count > 0 else 0,
            # 이자율 범위는 3자리 소수까지 표시하여 정밀도를 높임
            "이자율범위": (lambda: (
                f"{min(interest_rates):.3f}% ~ {max(interest_rates):.3f}%"
                if interest_rates else "데이터 없음"
            ))(),
        },
        "월별통계": _group_by_month(months, amounts),
        "금액별통계": _group_by_amount(amounts),
        "이자율별통계": _group_by_rate(interest_rates),
        "기관별통계": _group_by_company(companies, amounts),
        "종류별통계": _group_by_type(types, amounts),
        "상환상태별통계": _group_by_repayment_status(repayment_statuses, amounts)
    }

    # 5. LLM용 텍스트 포맷팅
    return _format_debt_statistics_text(statistics)

# =============================================================================
# 부채 및 자금조달 통계 변환 함수들
# =============================================================================

def _format_debt_statistics_for_llm(data: Dict[str, Any]) -> str:
    """전자단기사채 데이터를 LLM이 분석하기 쉬운 통계 형식으로 변환"""
    # log_step already defined at module level
    
    try:
        # 로깅: 입력 데이터 타입과 크기 확인
        if isinstance(data, str):
            log_step("전자단기사채 데이터 처리 시작", "INFO", f"문자열 데이터 크기: {len(data)}자")
            # JSON 파싱 시도. 응답이 매우 커서 MemoryError가 발생할 수 있으므로
            # 광범위한 예외를 포착하여 정규식 기반 파싱으로 대체합니다.
            try:
                data = json.loads(data)
                log_step("전자단기사채 JSON 파싱 성공", "SUCCESS", f"파싱된 데이터 타입: {type(data)}")
            except Exception as e:
                log_step("전자단기사채 JSON 파싱 실패", "WARNING", f"정규식 파싱으로 전환: {str(e)[:100]}")
                # JSON 파싱 실패 또는 메모리 문제 시 정규식으로 직접 추출
                return _extract_and_calculate_debt_statistics_directly(data)
        else:
            log_step("전자단기사채 데이터 처리 시작", "INFO", f"딕셔너리 데이터 타입: {type(data)}")
        
        # 데이터 구조 확인
        if not isinstance(data, dict):
            log_step("전자단기사채 데이터 형식 오류", "ERROR", f"dict가 아닌 {type(data)} 타입")
            return f"전자단기사채 데이터 형식 오류: dict가 아닌 {type(data)} 타입입니다."
        
        items = data.get("list", []) or data.get("items", [])
        if not items:
            # 상태 코드 확인
            status = data.get("status", "")
            message = data.get("message", "")
            if status == "013":
                log_step("전자단기사채 데이터 없음", "WARNING", "조회된 데이터 없음")
                return "전자단기사채 데이터가 없습니다. (조회된 데이터 없음)"
            elif status and status != "000":
                log_step("전자단기사채 조회 오류", "ERROR", f"상태코드: {status}, 메시지: {message}")
                return f"전자단기사채 조회 오류: {message} (상태코드: {status})"
            else:
                log_step("전자단기사채 데이터 없음", "WARNING", "빈 데이터")
                return "전자단기사채 데이터가 없습니다."
        
        log_step("전자단기사채 데이터 확인", "SUCCESS", f"총 {len(items)}개 항목 발견")
        
        # 통계 계산
        statistics = _calculate_debt_statistics(items)
        
        # LLM용 텍스트 포맷팅
        result = _format_debt_statistics_text(statistics)
        log_step("전자단기사채 통계 변환 완료", "SUCCESS", f"결과 길이: {len(result)}자")
        return result
        
    except Exception as e:
        log_step("전자단기사채 통계 변환 오류", "ERROR", f"오류: {str(e)[:200]}")
        return f"전자단기사채 통계 변환 오류: {str(e)[:200]}..."


def _format_debt_securities_statistics_for_llm(data: Dict[str, Any]) -> str:
    """회사채 데이터를 LLM이 분석하기 쉬운 통계 형식으로 변환"""
    # log_step already defined at module level
    
    try:
        # 로깅: 입력 데이터 타입과 크기 확인
        if isinstance(data, str):
            log_step("회사채 데이터 처리 시작", "INFO", f"문자열 데이터 크기: {len(data)}자")
            # JSON 파싱 시도. 응답이 매우 커서 MemoryError가 발생할 수 있으므로
            # 광범위한 예외를 포착하여 정규식 기반 파싱으로 대체합니다.
            try:
                data = json.loads(data)
                log_step("회사채 JSON 파싱 성공", "SUCCESS", f"파싱된 데이터 타입: {type(data)}")
            except Exception as e:
                log_step("회사채 JSON 파싱 실패", "WARNING", f"정규식 파싱으로 전환: {str(e)[:100]}")
                # JSON 파싱 실패 또는 메모리 문제 시 정규식으로 직접 추출
                return _extract_and_calculate_statistics_directly(data)
        else:
            log_step("회사채 데이터 처리 시작", "INFO", f"딕셔너리 데이터 타입: {type(data)}")
        
        # 데이터 구조 확인
        if not isinstance(data, dict):
            log_step("회사채 데이터 형식 오류", "ERROR", f"dict가 아닌 {type(data)} 타입")
            return f"회사채 데이터 형식 오류: dict가 아닌 {type(data)} 타입입니다."
        
        items = data.get("list", []) or data.get("items", [])
        if not items:
            # 상태 코드 확인
            status = data.get("status", "")
            message = data.get("message", "")
            if status == "013":
                log_step("회사채 데이터 없음", "WARNING", "조회된 데이터 없음")
                return "회사채 데이터가 없습니다. (조회된 데이터 없음)"
            elif status and status != "000":
                log_step("회사채 조회 오류", "ERROR", f"상태코드: {status}, 메시지: {message}")
                return f"회사채 조회 오류: {message} (상태코드: {status})"
            else:
                log_step("회사채 데이터 없음", "WARNING", "빈 데이터")
                return "회사채 데이터가 없습니다."
        
        log_step("회사채 데이터 확인", "SUCCESS", f"총 {len(items)}개 항목 발견")
        
        # 통계 계산
        statistics = _calculate_debt_securities_statistics(items)
        
        # LLM용 텍스트 포맷팅
        result = _format_debt_securities_statistics_text(statistics)
        log_step("회사채 통계 변환 완료", "SUCCESS", f"결과 길이: {len(result)}자")
        return result
        
    except Exception as e:
        log_step("회사채 통계 변환 오류", "ERROR", f"오류: {str(e)[:200]}")
        return f"회사채 통계 변환 오류: {str(e)[:200]}..."


def _calculate_debt_statistics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """전자단기사채 통계 계산"""
    if not items:
        return {}
    
    # 기본 통계
    total_amount = 0
    total_count = len(items)
    interest_rates = []
    amounts = []
    months = []
    companies = []
    types = []
    repayment_status = []
    
    for item in items:
        # 금액 처리
        amount_str = item.get("발행금액", "0")
        if amount_str and amount_str != "-":
            try:
                amount = float(str(amount_str).replace(",", ""))
                total_amount += amount
                amounts.append(amount)
            except:
                pass
        
        # 이자율 처리
        rate_str = item.get("이자율", "0")
        if rate_str and rate_str != "-":
            try:
                rate = float(str(rate_str).replace("%", ""))
                interest_rates.append(rate)
            except:
                pass
        
        # 월별 그룹핑
        month = item.get("발행월", "")
        if month:
            months.append(month)
        
        # 기관별 그룹핑
        company = item.get("발행기관", "")
        if company:
            companies.append(company)
        
        # 종류별 그룹핑
        debt_type = item.get("채무증권종류", "")
        if debt_type:
            types.append(debt_type)
        
        # 상환상태별 그룹핑
        status = item.get("상환상태", "")
        if status:
            repayment_status.append(status)
    
    # 통계 계산
    statistics = {
        "기본통계": {
            "총발행금액": total_amount,
            "총발행건수": total_count,
            "평균발행금액": total_amount / total_count if total_count > 0 else 0,
            # 이자율 범위는 소수점 셋째 자리까지 표시하여 동일 값이 되는 경우를 방지
            "이자율범위": (f"{min(interest_rates):.3f}% ~ {max(interest_rates):.3f}%" if interest_rates else "데이터 없음"),
        },
        "월별통계": _group_by_month(months, amounts),
        "금액별통계": _group_by_amount(amounts),
        "이자율별통계": _group_by_rate(interest_rates),
        "기관별통계": _group_by_company(companies, amounts),
        "종류별통계": _group_by_type(types, amounts),
        "상환상태별통계": _group_by_repayment_status(repayment_status, amounts)
    }
    
    return statistics


def _calculate_debt_securities_statistics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """회사채 통계 계산"""
    if not items:
        return {}
    
    # 기본 통계
    total_amount = 0
    total_count = len(items)
    interest_rates = []
    amounts = []
    months = []
    companies = []
    types = []
    maturity_years = []
    
    for item in items:
        # 금액 처리 - DART API 실제 필드명 사용
        amount_str = item.get("facvalu_totamt", "0")
        if amount_str and amount_str != "-":
            try:
                amount = float(str(amount_str).replace(",", ""))
                total_amount += amount
                amounts.append(amount)
            except:
                pass
        
        # 이자율 처리 - DART API 실제 필드명 사용
        rate_str = item.get("intrt", "0")
        if rate_str and rate_str != "-":
            try:
                rate = float(str(rate_str).replace("%", ""))
                interest_rates.append(rate)
            except:
                pass
        
        # 월별 그룹핑 - 발행일에서 월 추출
        issue_date = item.get("isu_de", "")
        if issue_date and issue_date != "-":
            try:
                # YYYY.MM.DD 형식에서 월 추출
                month = issue_date.split(".")[1] if "." in issue_date else ""
                if month:
                    months.append(f"{issue_date.split('.')[0]}년 {month}월")
            except:
                pass
        
        # 기관별 그룹핑 - DART API 실제 필드명 사용
        company = item.get("isu_cmpny", "")
        if company and company != "-":
            companies.append(company)
        
        # 종류별 그룹핑 - DART API 실제 필드명 사용
        bond_type = item.get("scrits_knd_nm", "")
        if bond_type and bond_type != "-":
            types.append(bond_type)
        
        # 만기별 그룹핑 - DART API에는 만기 정보가 없으므로 제거
        # maturity = item.get("만기", "")
        # if maturity:
        #     try:
        #         # 만기를 년수로 변환 (예: "3년" -> 3)
        #         years = float(maturity.replace("년", ""))
        #         maturity_years.append(years)
        #     except:
        #         pass
    
    # 상환상태별 그룹핑 추가
    repayment_status = []
    for item in items:
        status = item.get("repy_at", "")
        if status and status != "-":
            repayment_status.append(status)
    
    # 통계 계산
    statistics = {
        "기본통계": {
            "총발행금액": total_amount,
            "총발행건수": total_count,
            "평균발행금액": total_amount / total_count if total_count > 0 else 0,
            # 이자율 범위는 소수점 셋째 자리까지 표시하여 동일 값이 되는 경우를 방지
            "이자율범위": (f"{min(interest_rates):.3f}% ~ {max(interest_rates):.3f}%" if interest_rates else "데이터 없음"),
        },
        "월별통계": _group_by_month(months, amounts),
        "금액별통계": _group_by_amount(amounts),
        "이자율별통계": _group_by_rate(interest_rates),
        "기관별통계": _group_by_company(companies, amounts),
        "종류별통계": _group_by_type(types, amounts),
        "상환상태별통계": _group_by_repayment_status(repayment_status, amounts)
    }
    
    return statistics


def _group_by_month(months: List[str], amounts: List[float]) -> Dict[str, Any]:
    """
    월별 발행 금액과 건수를 집계합니다.

    주의: 기존 구현에서는 루프 내부에서 `return`을 수행하여 첫 번째 월의 데이터만
    반환하는 버그가 있었습니다. 또한 `months`와 `amounts` 리스트의 길이가
    서로 다를 경우를 고려하지 않았습니다. 이 함수는 전체 월별 데이터를
    반환하며, 두 리스트가 길이가 다를 경우에는 더 짧은 쪽에 맞춰 집계합니다.
    """
    from collections import defaultdict

    month_amounts = defaultdict(list)
    # zip을 사용하면 두 리스트 중 짧은 길이만큼 반복하여 잘못된 인덱스 접근을 방지할 수 있습니다.
    for month, amount in zip(months, amounts):
        # month나 amount가 비어 있는 경우는 건너뜁니다.
        if not month or amount is None:
            continue
        month_amounts[month].append(amount)

    result: Dict[str, Dict[str, Any]] = {}
    for month, month_amounts_list in month_amounts.items():
        count = len(month_amounts_list)
        total = sum(month_amounts_list)
        avg = total / count if count > 0 else 0
        result[month] = {
            "건수": count,
            "총금액": total,
            "평균금액": avg,
        }

    return result
        

def _group_by_amount(amounts: List[float]) -> Dict[str, Any]:
    """금액별 그룹핑 (10억 단위)"""
    from collections import defaultdict
    
    # 10억 단위로 그룹핑
    amount_groups = defaultdict(int)
    for amount in amounts:
        group = int(amount / 1000000000) * 10  # 10억 단위
        amount_groups[f"{group}억원 이상"] += 1
    
    return dict(amount_groups)


def _group_by_rate(rates: List[float]) -> Dict[str, Any]:
    """이자율별 그룹핑 (0.1% 단위)"""
    from collections import defaultdict
    
    # 0.1% 단위로 그룹핑
    rate_groups = defaultdict(int)
    for rate in rates:
        group = round(rate * 10) / 10  # 0.1% 단위
        rate_groups[f"{group}%"] += 1
    
    return dict(rate_groups)


def _group_by_company(companies: List[str], amounts: List[float]) -> Dict[str, Any]:
    """기관별 그룹핑"""
    from collections import defaultdict
    
    company_amounts = defaultdict(list)
    for company, amount in zip(companies, amounts):
        company_amounts[company].append(amount)
    
    result = {}
    for company, company_amounts_list in company_amounts.items():
        result[company] = {
            "건수": len(company_amounts_list),
            "총금액": sum(company_amounts_list),
            "평균금액": sum(company_amounts_list) / len(company_amounts_list)
        }
    
    return result


def _group_by_type(types: List[str], amounts: List[float]) -> Dict[str, Any]:
    """종류별 그룹핑"""
    from collections import defaultdict
    
    type_amounts = defaultdict(list)
    for debt_type, amount in zip(types, amounts):
        type_amounts[debt_type].append(amount)
    
    result = {}
    for debt_type, type_amounts_list in type_amounts.items():
        result[debt_type] = {
            "건수": len(type_amounts_list),
            "총금액": sum(type_amounts_list),
            "평균금액": sum(type_amounts_list) / len(type_amounts_list)
        }
    
    return result


def _group_by_repayment_status(statuses: List[str], amounts: List[float]) -> Dict[str, Any]:
    """상환상태별 그룹핑"""
    from collections import defaultdict
    
    status_amounts = defaultdict(list)
    for status, amount in zip(statuses, amounts):
        status_amounts[status].append(amount)
    
    result = {}
    for status, status_amounts_list in status_amounts.items():
        result[status] = {
            "건수": len(status_amounts_list),
            "총금액": sum(status_amounts_list),
            "평균금액": sum(status_amounts_list) / len(status_amounts_list)
        }
    
    return result


def _group_by_maturity_years(years: List[float], amounts: List[float]) -> Dict[str, Any]:
    """만기별 그룹핑 (년수)"""
    from collections import defaultdict
    
    maturity_amounts = defaultdict(list)
    for year, amount in zip(years, amounts):
        maturity_amounts[f"{year}년"] = maturity_amounts.get(f"{year}년", []) + [amount]
    
    result = {}
    for maturity, maturity_amounts_list in maturity_amounts.items():
        result[maturity] = {
            "건수": len(maturity_amounts_list),
            "총금액": sum(maturity_amounts_list),
            "평균금액": sum(maturity_amounts_list) / len(maturity_amounts_list)
        }
    
    return result


def _format_debt_statistics_text(statistics: Dict[str, Any]) -> str:
    """전자단기사채 통계를 LLM용 텍스트로 포맷팅"""
    if not statistics:
        return "전자단기사채 통계 데이터가 없습니다."
    
    text = "=== 전자단기사채 발행 통계 분석 ===\n\n"
    
    # 기본 통계
    basic = statistics.get("기본통계", {})
    text += f"📊 기본 통계:\n"
    text += f"  • 총 발행금액: {basic.get('총발행금액', 0):,.0f}원\n"
    text += f"  • 총 발행건수: {basic.get('총발행건수', 0)}건\n"
    text += f"  • 평균 발행금액: {basic.get('평균발행금액', 0):,.0f}원\n"
    text += f"  • 이자율 범위: {basic.get('이자율범위', '데이터 없음')}\n\n"
    
    # 월별 통계
    monthly = statistics.get("월별통계", {})
    if monthly:
        text += f"📅 월별 발행 현황:\n"
        for month, data in monthly.items():
            text += f"  • {month}: {data['건수']}건, {data['총금액']:,.0f}원 (평균 {data['평균금액']:,.0f}원)\n"
        text += "\n"
    
    # 금액별 통계
    amount_groups = statistics.get("금액별통계", {})
    if amount_groups:
        text += f"💰 금액별 분포:\n"
        for group, count in amount_groups.items():
            text += f"  • {group}: {count}건\n"
        text += "\n"
    
    # 이자율별 통계
    rate_groups = statistics.get("이자율별통계", {})
    if rate_groups:
        text += f"📈 이자율별 분포:\n"
        for rate, count in rate_groups.items():
            text += f"  • {rate}: {count}건\n"
        text += "\n"
    
    # 기관별 통계
    company_groups = statistics.get("기관별통계", {})
    if company_groups:
        text += f"🏢 기관별 발행 현황:\n"
        for company, data in company_groups.items():
            text += f"  • {company}: {data['건수']}건, {data['총금액']:,.0f}원\n"
        text += "\n"
    
    # 종류별 통계
    type_groups = statistics.get("종류별통계", {})
    if type_groups:
        text += f"📋 채무증권 종류별 분포:\n"
        for debt_type, data in type_groups.items():
            text += f"  • {debt_type}: {data['건수']}건, {data['총금액']:,.0f}원\n"
        text += "\n"
    
    # 상환상태별 통계
    status_groups = statistics.get("상환상태별통계", {})
    if status_groups:
        text += f"🔄 상환상태별 분포:\n"
        for status, data in status_groups.items():
            text += f"  • {status}: {data['건수']}건, {data['총금액']:,.0f}원\n"
        text += "\n"
    
    return text


def _format_debt_securities_statistics_text(statistics: Dict[str, Any]) -> str:
    """회사채 통계를 LLM용 텍스트로 포맷팅"""
    if not statistics:
        return "회사채 통계 데이터가 없습니다."
    
    text = "=== 회사채 발행 통계 분석 ===\n\n"
    
    # 기본 통계
    basic = statistics.get("기본통계", {})
    text += f"📊 기본 통계:\n"
    text += f"  • 총 발행금액: {basic.get('총발행금액', 0):,.0f}원\n"
    text += f"  • 총 발행건수: {basic.get('총발행건수', 0)}건\n"
    text += f"  • 평균 발행금액: {basic.get('평균발행금액', 0):,.0f}원\n"
    text += f"  • 이자율 범위: {basic.get('이자율범위', '데이터 없음')}\n\n"
    
    # 월별 통계
    monthly = statistics.get("월별통계", {})
    if monthly:
        text += f"📅 월별 발행 현황:\n"
        for month, data in monthly.items():
            text += f"  • {month}: {data['건수']}건, {data['총금액']:,.0f}원 (평균 {data['평균금액']:,.0f}원)\n"
        text += "\n"
    
    # 금액별 통계
    amount_groups = statistics.get("금액별통계", {})
    if amount_groups:
        text += f"💰 금액별 분포:\n"
        for group, count in amount_groups.items():
            text += f"  • {group}: {count}건\n"
        text += "\n"
    
    # 이자율별 통계
    rate_groups = statistics.get("이자율별통계", {})
    if rate_groups:
        text += f"📈 이자율별 분포:\n"
        for rate, count in rate_groups.items():
            text += f"  • {rate}: {count}건\n"
        text += "\n"
    
    # 기관별 통계
    company_groups = statistics.get("기관별통계", {})
    if company_groups:
        text += f"🏢 기관별 발행 현황:\n"
        for company, data in company_groups.items():
            text += f"  • {company}: {data['건수']}건, {data['총금액']:,.0f}원\n"
        text += "\n"
    
    # 종류별 통계
    type_groups = statistics.get("종류별통계", {})
    if type_groups:
        text += f"📋 채권 종류별 분포:\n"
        for bond_type, data in type_groups.items():
            text += f"  • {bond_type}: {data['건수']}건, {data['총금액']:,.0f}원\n"
        text += "\n"
    
    # 상환상태별 통계
    status_groups = statistics.get("상환상태별통계", {})
    if status_groups:
        text += f"🔄 상환상태별 분포:\n"
        for status, data in status_groups.items():
            text += f"  • {status}: {data['건수']}건, {data['총금액']:,.0f}원\n"
        text += "\n"
    
    return text


# =============================================================================
# 기존 변환 함수들 (간소화된 버전)
# =============================================================================

def _transform_single_acnt_statement_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """단일 재무제표 조회 결과 변환 (압축 테이블)"""
    field_mapping = {
        "rcept_no": "접수번호",
        "bsns_year": "사업연도",
        "stock_code": "종목코드",
        "reprt_code": "보고서코드",
        "account_nm": "계정명",
        "fs_div": "개별연결구분",
        "fs_nm": "개별연결명",
        "sj_div": "재무제표구분",
        "sj_nm": "재무제표명",
        "thstrm_nm": "당기명",
        "thstrm_dt": "당기일자",
        "thstrm_amount": {
            "key": "당기금액",
            "value_transform": _format_currency
        },
        "thstrm_add_amount": {
            "key": "당기누적금액",
            "value_transform": _format_currency
        },
        "frmtrm_nm": "전기명",
        "frmtrm_dt": "전기일자",
        "frmtrm_amount": {
            "key": "전기금액",
            "value_transform": _format_currency
        },
        "frmtrm_add_amount": {
            "key": "전기누적금액",
            "value_transform": _format_currency
        },
        "bfefrmtrm_nm": "전전기명",
        "bfefrmtrm_dt": "전전기일자",
        "bfefrmtrm_amount": {
            "key": "전전기금액",
            "value_transform": _format_currency
        },
        "ord": "정렬순서",
        "currency": "통화단위"
    }
    
    # 기존 변환
    if "list" in data and isinstance(data["list"], list):
        transformed_list = []
        for item in data["list"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_list.append(transformed_item)
        data["list"] = transformed_list
        return _compress_table(data, key="list")
    elif "items" in data and isinstance(data["items"], list):
        transformed_items = []
        for item in data["items"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_items.append(transformed_item)
        data["items"] = transformed_items
        return _compress_table(data, key="items")
    
    return data

def _transform_corporation_code_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """기업 코드 조회 결과 변환"""
    return data

def _transform_disclosure_list_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """공시 목록 조회 결과 변환"""
    return data

def _transform_corporation_info_combined_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """기업 정보와 사업 개요를 합친 결과 변환"""
    return data

def _transform_multi_acnt_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """다중 재무제표 조회 결과 변환 (압축 테이블)"""
    field_mapping = {
        "rcept_no": "접수번호",
        "bsns_year": "사업연도",
        "stock_code": "종목코드",
        "reprt_code": "보고서코드",
        "account_nm": "계정명",
        "fs_div": "개별연결구분",
        "fs_nm": "개별연결명",
        "sj_div": "재무제표구분",
        "sj_nm": "재무제표명",
        "thstrm_nm": "당기명",
        "thstrm_dt": "당기일자",
        "thstrm_amount": {
            "key": "당기금액",
            "value_transform": _format_currency
        },
        "thstrm_add_amount": {
            "key": "당기누적금액",
            "value_transform": _format_currency
        },
        "frmtrm_nm": "전기명",
        "frmtrm_dt": "전기일자",
        "frmtrm_amount": {
            "key": "전기금액",
            "value_transform": _format_currency
        },
        "frmtrm_add_amount": {
            "key": "전기누적금액",
            "value_transform": _format_currency
        },
        "bfefrmtrm_nm": "전전기명",
        "bfefrmtrm_dt": "전전기일자",
        "bfefrmtrm_amount": {
            "key": "전전기금액",
            "value_transform": _format_currency
        },
        "ord": "정렬순서",
        "currency": "통화단위"
    }
    
    # 기존 변환
    if "list" in data and isinstance(data["list"], list):
        transformed_list = []
        for item in data["list"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_list.append(transformed_item)
        data["list"] = transformed_list
        return _compress_table(data, key="list")
    elif "items" in data and isinstance(data["items"], list):
        transformed_items = []
        for item in data["items"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_items.append(transformed_item)
        data["items"] = transformed_items
        return _compress_table(data, key="items")
    return data

def _compress_table(data: dict, key: str = "list") -> dict:
    """테이블 데이터 압축"""
    rows = data.get(key, [])
    if not rows or not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return data
    exclude_cols = {"전기명", "전기일자", "전기금액", "전전기명", "전전기일자", "전전기금액", "보고서코드", "접수번호"}
    columns = [col for col in rows[0].keys() if col not in exclude_cols]
    values = [[row.get(col, None) for col in columns] for row in rows]
    return {
        "columns": columns,
        "rows": values
    }

def _compress_executive_table(data: dict, key: str = "list") -> dict:
    """임원 정보 테이블 압축"""
    rows = data.get(key, [])
    if not rows or not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return data
    
    # 임원 정보에서 제외할 컬럼들
    exclude_cols = {"접수번호", "고유번호", "법인구분", "결산기준일", "주요경력", "법인명"}
    columns = [col for col in rows[0].keys() if col not in exclude_cols]
    values = [[row.get(col, None) for col in columns] for row in rows]
    
    return {
        "columns": columns,
        "rows": values
    }

def _transform_fields(item: Dict[str, Any], field_mapping: Dict[str, Any]) -> Dict[str, Any]:
    """필드 매핑을 사용하여 딕셔너리 변환 (키와 값 모두 변환 가능)"""
    transformed = {}
    
    for old_key, mapping_info in field_mapping.items():
        if old_key in item:
            # mapping_info가 문자열인 경우 (기존 방식 - 키만 변환)
            if isinstance(mapping_info, str):
                transformed[mapping_info] = item[old_key]
            # mapping_info가 딕셔너리인 경우 (새로운 방식 - 키와 값 모두 변환)
            elif isinstance(mapping_info, dict):
                new_key = mapping_info.get("key", old_key)
                value_transform = mapping_info.get("value_transform")
                
                if value_transform is not None:
                    # 값 변환 함수가 있는 경우
                    if callable(value_transform):
                        original_value = item[old_key]
                        transformed_value = value_transform(original_value)
                        transformed[new_key] = transformed_value
                    else:
                        # 고정 값으로 변환
                        transformed[new_key] = value_transform
                else:
                    # 값 변환 없이 키만 변환
                    transformed[new_key] = item[old_key]
    
    # 매핑되지 않은 필드들만 포함 (매핑된 키는 제외)
    for key, value in item.items():
        if key not in field_mapping:
            transformed[key] = value
    
    return transformed

def _format_currency(value: Any) -> str:
    """통화 값 포맷팅 (한국어 화폐 단위: 조, 억, 만)"""
    if value is None or value == "":
        return "0원"
    
    try:
        # 콤마 제거 후 숫자로 변환
        if isinstance(value, str):
            value = value.replace(",", "")
        
        num_value = float(value)
        
        if num_value == 0:
            return "0원"
        
        # 절댓값으로 변환
        abs_value = abs(num_value)
        
        # 조 단위
        if abs_value >= 1000000000000:
            result = f"{num_value / 1000000000000:.1f}조원"
        # 억 단위
        elif abs_value >= 100000000:
            result = f"{num_value / 100000000:.1f}억원"
        # 만 단위
        elif abs_value >= 10000:
            result = f"{num_value / 10000:.1f}만원"
        # 원 단위
        else:
            result = f"{num_value:,.0f}원"
        
        return result
        
    except (ValueError, TypeError):
        return str(value) if value is not None else "0원"

def _safe_process_numeric_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    """숫자형 필드들을 안전하게 처리"""
    # 숫자형 필드들
    numeric_fields = [
        "기초보유주식수", "기말보유주식수", "보유주식수",
        "기초보유주식지분율", "기말보유주식지분율", "보유주식지분율"
    ]
    
    for field in numeric_fields:
        if field in item:
            value = item[field]
            
            # 문자열인 경우 처리
            if isinstance(value, str):
                # '-' 또는 빈 문자열인 경우
                if value in ['-', '', 'None', 'null']:
                    item[field] = "0"
                else:
                    # 콤마 제거
                    cleaned_value = value.replace(',', '')
                    
                    # 숫자 형식 검증 및 정리
                    try:
                        # 정수인지 확인
                        if '.' not in cleaned_value:
                            int(cleaned_value)
                            item[field] = cleaned_value
                        else:
                            float(cleaned_value)
                            item[field] = cleaned_value
                    except ValueError:
                        # 숫자가 아닌 경우 그대로 유지
                        pass
    
    return item

def _transform_single_acc_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """단일 계정과목 조회 결과 변환"""
    field_mapping = {
        "rcept_no": "접수번호",
        "reprt_code": "보고서코드",
        "bsns_year": "사업연도",
        "corp_code": "고유번호",
        "sj_div": "재무제표구분",
        "sj_nm": "재무제표명",
        "account_id": "계정ID",
        "account_nm": "계정명",
        "account_detail": "계정상세",
        "thstrm_nm": "당기명",
        "thstrm_amount": {
            "key": "당기금액",
            "value_transform": _format_currency
        },
        "thstrm_add_amount": {
            "key": "당기누적금액",
            "value_transform": _format_currency
        },
        "frmtrm_nm": "전기명",
        "frmtrm_amount": {
            "key": "전기금액",
            "value_transform": _format_currency
        },
        "frmtrm_q_nm": "전기명분반기",
        "frmtrm_q_amount": {
            "key": "전기금액분반기",
            "value_transform": _format_currency
        },
        "frmtrm_add_amount": {
            "key": "전기누적금액",
            "value_transform": _format_currency
        },
        "bfefrmtrm_nm": "전전기명",
        "bfefrmtrm_amount": {
            "key": "전전기금액",
            "value_transform": _format_currency
        },
        "ord": "정렬순서",
        "currency": "통화단위"
    }
    
    # list 키가 있는 경우 (계정과목 목록)
    if "list" in data and isinstance(data["list"], list):
        transformed_list = []
        for item in data["list"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_list.append(transformed_item)
        data["list"] = transformed_list
        return _compress_table(data, key="list")
    # items 키가 있는 경우 (기타)
    elif "items" in data and isinstance(data["items"], list):
        transformed_items = []
        for item in data["items"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_items.append(transformed_item)
        data["items"] = transformed_items
        return _compress_table(data, key="items")
    
    return data

def _transform_multi_index_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """다중 재무비율 지표 조회 결과 변환"""
    field_mapping = {
        "reprt_code": "보고서코드",
        "bsns_year": "사업연도",
        "corp_code": "고유번호",
        "stock_code": "종목코드",
        "stlm_dt": "결산기준일",
        "idx_cl_code": "지표분류코드",
        "idx_cl_nm": "지표분류명",
        "idx_code": "지표코드",
        "idx_nm": "지표명",
        "idx_val": "지표값"
    }
    
    # list 키가 있는 경우 (재무비율 지표 목록)
    if "list" in data and isinstance(data["list"], list):
        transformed_list = []
        for item in data["list"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_list.append(transformed_item)
        data["list"] = transformed_list
    # items 키가 있는 경우 (기타)
    elif "items" in data and isinstance(data["items"], list):
        transformed_items = []
        for item in data["items"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_items.append(transformed_item)
        data["items"] = transformed_items
    
    return data

def _transform_major_shareholder_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """최대주주 현황 조회 결과 변환 - 파이썬 딕셔너리 문자열 파싱 문제 해결"""
    import ast
    import re
    
    print(f"🔥🔥🔥 _transform_major_shareholder_result 호출됨!")
    print(f"🔥🔥🔥 데이터 타입: {type(data)}")
    print(f"🔥🔥🔥 데이터 내용: {repr(str(data)[:200])}...")
    
    # 이미 딕셔너리인 경우 그대로 진행
    if isinstance(data, dict):
        print(f"🔥🔥🔥 딕셔너리 타입으로 처리")
        return _process_major_shareholder_data(data)
    
    # 문자열인 경우 파싱 시도
    if isinstance(data, str):
        # 1. 잘린 JSON 감지 ({"로 시작하지만 }로 끝나지 않는 경우)
        if data.startswith('{"') and not data.endswith('}'):
            print(f"🔥 get_major_shareholder 잘린 데이터 감지: {len(data)}자")
            return {
                "status": "999",
                "message": "데이터 잘림 오류 - MCP 응답 크기 제한",
                "list": [],
                "error": "truncated_response",
                "original_length": len(data)
            }
        
        # 2. 파이썬 딕셔너리 문자열 파싱 시도
        try:
            # ast.literal_eval을 사용하여 안전하게 파싱
            parsed_data = ast.literal_eval(data)
            print(f"🔥 get_major_shareholder ast.literal_eval 성공: {type(parsed_data)}")
            return _process_major_shareholder_data(parsed_data)
        except (ValueError, SyntaxError) as e:
            print(f"🔥 get_major_shareholder ast.literal_eval 실패: {str(e)}")
            
            # 3. 안전한 JSON 변환 시도
            try:
                json_data = _safe_convert_to_json(data)
                parsed_data = json.loads(json_data)
                print(f"🔥 get_major_shareholder 안전한 JSON 변환 성공")
                return _process_major_shareholder_data(parsed_data)
            except Exception as e2:
                print(f"🔥 get_major_shareholder JSON 변환 실패: {str(e2)}")
                
                # 4. 최종 실패 시 원본 반환
                return {
                    "status": "999",
                    "message": "파싱 실패 - 파이썬 딕셔너리 문자열 파싱 오류",
                    "list": [],
                    "error": "parsing_failed",
                    "original_data": data[:500],  # 처음 500자만 보관
                    "parse_error": str(e)
                }
    
    # 기타 타입인 경우 문자열로 변환 후 재시도
    return _transform_major_shareholder_result(str(data))

def _safe_convert_to_json(python_dict_str: str) -> str:
    """파이썬 딕셔너리 문자열을 안전하게 JSON으로 변환"""
    import re
    
    # 1. 기본 정리
    cleaned = python_dict_str.strip()
    
    # 2. 문자열 내부의 싱글쿼트를 보호하면서 키-값 싱글쿼트를 더블쿼트로 변환
    # 정규식을 사용하여 키와 값의 싱글쿼트만 변환
    
    # 키 부분의 싱글쿼트를 더블쿼트로 변환 (': 앞의 '키')
    cleaned = re.sub(r"'([^']+)':", r'"\1":', cleaned)
    
    # 값 부분의 싱글쿼트를 더블쿼트로 변환 (: 뒤의 '값')
    # 하지만 값 내부에 싱글쿼트가 있는 경우를 고려해야 함
    
    # 3. None, True, False를 JSON 형식으로 변환
    cleaned = cleaned.replace('None', 'null')
    cleaned = cleaned.replace('True', 'true')
    cleaned = cleaned.replace('False', 'false')
    
    # 4. 값 부분의 싱글쿼트 처리 (복잡한 경우)
    # 간단한 값들부터 처리
    cleaned = re.sub(r": '([^']*)'", r': "\1"', cleaned)
    
    return cleaned

def _process_major_shareholder_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """최대주주 데이터 후처리"""
    field_mapping = {
        "rcept_no": "접수번호",
        "rcept_dt": "접수일자", 
        "corp_code": "고유번호",
        "corp_name": "회사명",
        "nm": "성명",
        "relate": "관계",
        "stock_knd": "주식종류",
        "bsis_posesn_stock_co": "기초보유주식수",
        "bsis_posesn_stock_qota_rt": "기초보유주식지분율",
        "trmend_posesn_stock_co": "기말보유주식수", 
        "trmend_posesn_stock_qota_rt": "기말보유주식지분율",
        "posesn_stock_co": "보유주식수",
        "posesn_stock_qota_rt": "보유주식지분율",
        "rm": "비고"
    }
    
    # list 키가 있는 경우 (최대주주 목록)
    if "list" in data and isinstance(data["list"], list):
        transformed_list = []
        for item in data["list"]:
            transformed_item = _transform_fields(item, field_mapping)
            
            # 숫자형 필드 안전 처리
            transformed_item = _safe_process_numeric_fields(transformed_item)
            
            transformed_list.append(transformed_item)
        data["list"] = transformed_list
    
    # items 키가 있는 경우 (기타)
    elif "items" in data and isinstance(data["items"], list):
        transformed_items = []
        for item in data["items"]:
            transformed_item = _transform_fields(item, field_mapping)
            
            # 숫자형 필드 안전 처리
            transformed_item = _safe_process_numeric_fields(transformed_item)
            
            transformed_items.append(transformed_item)
        data["items"] = transformed_items
    
    return data

def _transform_major_holder_changes_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """주요주주 변동 조회 결과 변환"""
    field_mapping = {
        "rcept_no": "접수번호",
        "rcept_dt": "접수일자",
        "corp_code": "고유번호",
        "corp_name": "회사명",
        "report_tp": "보고구분",
        "repror": "대표보고자",
        "stkqy": "보유주식수",
        "stkqy_irds": "보유주식증감",
        "stkrt": "보유비율",
        "stkrt_irds": "보유비율증감",
        "ctr_stkqy": "주요체결주식수",
        "ctr_stkrt": "주요체결보유비율",
        "report_resn": "보고사유"
    }
    
    # list 키가 있는 경우 (주요주주 변동 목록)
    if "list" in data and isinstance(data["list"], list):
        transformed_list = []
        for item in data["list"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_list.append(transformed_item)
        data["list"] = transformed_list
    # items 키가 있는 경우 (기타)
    elif "items" in data and isinstance(data["items"], list):
        transformed_items = []
        for item in data["items"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_items.append(transformed_item)
        data["items"] = transformed_items
    
    return data

def _transform_executive_trading_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """임원 주식거래 조회 결과 변환 (최신순 20건 + 최대값순 20건으로 제한)"""
    field_mapping = {
        "rcept_no": "접수번호",
        "rcept_dt": "접수일자",
        "corp_code": "고유번호",
        "corp_name": "회사명",
        "repror": "보고자",
        "isu_exctv_rgist_at": "발행회사관계임원등기여부",
        "isu_exctv_ofcps": "발행회사관계임원직위",
        "isu_main_shrholdr": "발행회사관계주요주주",
        "sp_stock_lmp_cnt": "특정증권소유수",
        "sp_stock_lmp_irds_cnt": "특정증권소유증감수",
        "sp_stock_lmp_rate": "특정증권소유비율",
        "sp_stock_lmp_irds_rate": "특정증권소유증감비율"
    }
    
    # list 키가 있는 경우 (임원 주식거래 목록)
    if "list" in data and isinstance(data["list"], list):
        transformed_list = []
        for item in data["list"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_list.append(transformed_item)
        data["list"] = transformed_list
    # items 키가 있는 경우 (기타)
    elif "items" in data and isinstance(data["items"], list):
        transformed_items = []
        for item in data["items"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_items.append(transformed_item)
        data["items"] = transformed_items
    
    return data

def _transform_executive_info_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """임원 정보 조회 결과 변환 (압축 테이블)"""
    field_mapping = {
        "rcept_no": "접수번호",
        "corp_cls": "법인구분",
        "corp_code": "고유번호",
        "corp_name": "법인명",
        "nm": "성명",
        "sexdstn": "성별",
        "birth_ym": "출생년월",
        "ofcps": "직위",
        "rgist_exctv_at": "등기임원여부",
        "fte_at": "상근여부",
        "chrg_job": "담당업무",
        "main_career": "주요경력",
        "mxmm_shrholdr_relate": "최대주주관계",
        "hffc_pd": "재직기간",
        "tenure_end_on": "임기만료일",
        "stlm_dt": "결산기준일"
    }
    
    # list 키가 있는 경우 (임원 정보 목록)
    if "list" in data and isinstance(data["list"], list):
        transformed_list = []
        for item in data["list"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_list.append(transformed_item)
        data["list"] = transformed_list
        return _compress_executive_table(data, key="list")
    # items 키가 있는 경우 (기타)
    elif "items" in data and isinstance(data["items"], list):
        transformed_items = []
        for item in data["items"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_items.append(transformed_item)
        data["items"] = transformed_items
        return _compress_executive_table(data, key="items")
    
    return data

def _transform_employee_info_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """직원 정보 조회 결과 변환"""
    field_mapping = {
        "rcept_no": "접수번호",
        "corp_cls": "법인구분",
        "corp_code": "고유번호",
        "corp_name": "법인명",
        "fo_bbm": "사업부문",
        "sexdstn": "성별",
        "reform_bfe_emp_co_rgllbr": "개정전직원수정규직",
        "reform_bfe_emp_co_cnttk": "개정전직원수계약직",
        "reform_bfe_emp_co_etc": "개정전직원수기타",
        "rgllbr_co": "정규직수",
        "rgllbr_abacpt_labrr_co": "정규직단시간근로자수",
        "cnttk_co": "계약직수",
        "cnttk_abacpt_labrr_co": "계약직단시간근로자수",
        "sm": "합계",
        "avrg_cnwk_sdytrn": "평균근속연수",
        "fyer_salary_totamt": "연간급여총액",
        "jan_salary_am": "1인평균급여액",
        "rm": "비고",
        "stlm_dt": "결산기준일"
    }
    
    # list 키가 있는 경우 (직원 정보 목록)
    if "list" in data and isinstance(data["list"], list):
        transformed_list = []
        for item in data["list"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_list.append(transformed_item)
        data["list"] = transformed_list
    # items 키가 있는 경우 (기타)
    elif "items" in data and isinstance(data["items"], list):
        transformed_items = []
        for item in data["items"]:
            transformed_item = _transform_fields(item, field_mapping)
            transformed_items.append(transformed_item)
        data["items"] = transformed_items
    
    return data

def _transform_bond_with_warrant_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """신주인수권부사채 발행 결과 변환"""
    if not isinstance(data, dict) or "list" not in data:
        return data
    
    bond_list = data.get("list", [])
    if not bond_list:
        return data
    
    # 최신순으로 정렬 (접수번호 기준)
    try:
        bond_list.sort(key=lambda x: x.get("rcept_no", ""), reverse=True)
    except:
        pass
    
    # 최대 10건으로 제한
    limited_list = bond_list[:10]
    
    # 중요 필드만 추출하여 요약
    summarized_list = []
    for bond in limited_list:
        summary = {
            "접수번호": bond.get("rcept_no", ""),
            "기업명": bond.get("corp_name", ""),
            "결정일": bond.get("bddd", ""),
            "사채종류": bond.get("bd_knd", ""),
            "발행총액": bond.get("bd_fta", ""),
            "만기일": bond.get("bd_mtd", ""),
            "표면이자율": bond.get("bd_intr_sf", ""),
            "행사가격": bond.get("ex_prc", ""),
            "신주발행주식수": bond.get("nstk_isstk_cnt", ""),
            "발행방식": bond.get("bdis_mthn", ""),
            "행사기간_시작": bond.get("expd_bgd", ""),
            "행사기간_종료": bond.get("expd_edd", "")
        }
        # 빈 값 제거
        summary = {k: v for k, v in summary.items() if v and v != "-"}
        summarized_list.append(summary)
    
    return {
        "status": data.get("status", ""),
        "message": data.get("message", ""),
        "list": summarized_list,
        "total_count": len(bond_list),
        "displayed_count": len(summarized_list)
    }


def _transform_search_financial_notes_result(data: Any) -> str:
    """search_financial_notes 결과 변환 - 불필요한 메타데이터 제거"""
    try:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return data
        
        if isinstance(data, dict) and "results" in data:
            results = data["results"]
            
            # paragraphs 필터링
            if "paragraphs" in results and isinstance(results["paragraphs"], list):
                for para in results["paragraphs"]:
                    if isinstance(para, dict):
                        para.pop("file_path", None)
                        para.pop("line_number", None)
                        para.pop("match_type", None)
            
            # tables 필터링
            if "tables" in results and isinstance(results["tables"], list):
                for table in results["tables"]:
                    if isinstance(table, dict):
                        table.pop("file_path", None)
                        table.pop("line_number", None)
                        table.pop("match_type", None)
        
        return json.dumps(data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps(data, ensure_ascii=False, indent=2)


# =============================================================================
# get_investment_in_other_corp 전용 통계 변환 함수들 (완전 재작성)
# =============================================================================

def _format_investment_statistics_for_llm(data: Dict[str, Any]) -> str:
    """타법인 출자현황 데이터를 LLM이 분석하기 쉬운 통계 형식으로 변환"""
    try:
        # 데이터 파싱 - 이미 변환된 텍스트인지 먼저 확인
        if isinstance(data, str):
            if not data.strip():
                return "타법인 출자현황 데이터가 없습니다."
            
            # 이미 변환된 텍스트인지 확인 (이모지나 특정 패턴으로 판단)
            if "📊 타법인 출자현황" in data or "🔍 전체 투자 규모" in data:
                return data  # 이미 변환된 텍스트이므로 그대로 반환
            
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                # JSON 파싱 실패 시 원본 데이터 반환
                return f"타법인 출자현황 데이터 파싱 오류: {str(e)[:100]}..."
        elif not isinstance(data, dict):
            return f"타법인 출자현황 데이터 형식 오류: {type(data)}"
        
        # 데이터 구조 확인
        if not data:
            return "타법인 출자현황 데이터가 없습니다."
        
        # list 또는 items 배열 찾기
        items = data.get("list", []) or data.get("items", [])
        if not items:
            # 상태 코드 확인
            status = data.get("status", "")
            message = data.get("message", "")
            if status == "013":
                return "타법인 출자현황 데이터가 없습니다. (조회된 데이터 없음)"
            elif status and status != "000":
                return f"타법인 출자현황 조회 오류: {message} (상태코드: {status})"
            else:
                return "타법인 출자현황 데이터가 없습니다."
        
        # 통계 계산
        statistics = _calculate_investment_statistics_new(items)
        
        # LLM용 텍스트 포맷팅
        return _format_investment_statistics_text_new(statistics)
        
    except Exception as e:
        return f"타법인 출자현황 통계 변환 오류: {str(e)}"


def _calculate_investment_statistics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """타법인 출자현황 통계 계산"""
    if not items:
        return {}
    
    # 기본 통계
    total_investment_amount = 0
    total_count = len(items)
    ownership_ratios = []
    investment_amounts = []
    purposes = []
    acquisition_dates = []
    profit_losses = []
    companies = []
    
    for item in items:
        # 출자금액 처리 (최초 취득 금액 기준)
        amount_str = item.get("frst_acqs_amount", "0")
        if amount_str and amount_str != "-":
            try:
                amount = float(str(amount_str).replace(",", ""))
                total_investment_amount += amount
                investment_amounts.append(amount)
            except:
                pass
        
        # 지분율 처리 (기말 잔액 지분수 기준으로 계산)
        # 실제 데이터에는 지분율이 없으므로 지분수로 대체
        ratio_str = item.get("trmend_blce_irds", "0")
        if ratio_str and ratio_str != "-":
            try:
                # 지분수를 지분율로 근사 계산 (실제로는 정확한 지분율이 필요)
                ratio = float(str(ratio_str).replace(",", ""))
                # 임시로 0-100% 범위로 정규화 (실제로는 총 발행주식수 대비 계산 필요)
                normalized_ratio = min(100, max(0, ratio / 1000000))  # 100만주당 1%로 가정
                ownership_ratios.append(normalized_ratio)
            except:
                pass
        
        # 출자목적 처리
        purpose = item.get("invstmnt_purps", "").strip()
        if purpose:
            purposes.append(purpose)
        
        # 최초 취득일 처리
        date_str = item.get("frst_acqs_de", "")
        if date_str and date_str != "-":
            acquisition_dates.append(date_str)
        
        # 평가손익 처리 (만원 단위로 변환)
        profit_loss_str = item.get("eval_pl", "0")
        if profit_loss_str and profit_loss_str != "-":
            try:
                profit_loss = float(str(profit_loss_str).replace(",", "")) * 10000  # 만원 단위로 변환
                profit_losses.append(profit_loss)
            except:
                pass
        
        # 피출자법인명 처리
        company = item.get("inv_prm", "").strip()
        if company:
            companies.append(company)
    
    # 통계 계산
    avg_investment_amount = total_investment_amount / total_count if total_count > 0 else 0
    avg_ownership_ratio = sum(ownership_ratios) / len(ownership_ratios) if ownership_ratios else 0
    total_profit_loss = sum(profit_losses)
    avg_profit_loss = total_profit_loss / len(profit_losses) if profit_losses else 0
    
    # 그룹별 분석
    purpose_groups = _group_by_purpose(items)
    ownership_groups = _group_by_ownership_ratio(ownership_ratios)
    amount_groups = _group_by_amount(investment_amounts)
    period_groups = _group_by_period(acquisition_dates)
    profit_loss_groups = _group_by_profit_loss(profit_losses)
    
    return {
        "basic_stats": {
            "total_count": total_count,
            "total_investment_amount": total_investment_amount,
            "avg_investment_amount": avg_investment_amount,
            "avg_ownership_ratio": avg_ownership_ratio,
            "total_profit_loss": total_profit_loss,
            "avg_profit_loss": avg_profit_loss,
            "profit_count": len([p for p in profit_losses if p > 0]),
            "loss_count": len([p for p in profit_losses if p < 0])
        },
        "purpose_groups": purpose_groups,
        "ownership_groups": ownership_groups,
        "amount_groups": amount_groups,
        "period_groups": period_groups,
        "profit_loss_groups": profit_loss_groups,
        "companies": list(set(companies))[:10]  # 상위 10개 회사만
    }


def _group_by_purpose(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """출자목적별 그룹핑"""
    groups = {}
    
    for item in items:
        purpose = item.get("invstmnt_purps", "기타").strip()
        if not purpose:
            purpose = "기타"
        
        if purpose not in groups:
            groups[purpose] = {
                "count": 0,
                "total_amount": 0,
                "avg_ownership_ratio": 0,
                "ownership_ratios": []
            }
        
        groups[purpose]["count"] += 1
        
        # 금액 처리
        amount_str = item.get("frst_acqs_amount", "0")
        if amount_str and amount_str != "-":
            try:
                amount = float(str(amount_str).replace(",", ""))
                groups[purpose]["total_amount"] += amount
            except:
                pass
        
        # 지분율 처리
        ratio_str = item.get("trmend_blce_irds", "0")
        if ratio_str and ratio_str != "-":
            try:
                ratio = float(str(ratio_str).replace(",", ""))
                normalized_ratio = min(100, max(0, ratio / 1000000))
                groups[purpose]["ownership_ratios"].append(normalized_ratio)
            except:
                pass
    
    # 평균 지분율 계산
    for purpose in groups:
        ratios = groups[purpose]["ownership_ratios"]
        groups[purpose]["avg_ownership_ratio"] = sum(ratios) / len(ratios) if ratios else 0
    
    return groups


def _group_by_ownership_ratio(ratios: List[float]) -> Dict[str, int]:
    """지분율별 그룹핑"""
    groups = {
        "0-25%": 0,
        "25-50%": 0,
        "50%+": 0
    }
    
    for ratio in ratios:
        if ratio < 25:
            groups["0-25%"] += 1
        elif ratio < 50:
            groups["25-50%"] += 1
        else:
            groups["50%+"] += 1
    
    return groups


def _group_by_amount(amounts: List[float]) -> Dict[str, Dict[str, Any]]:
    """금액별 그룹핑"""
    if not amounts:
        return {}
    
    sorted_amounts = sorted(amounts, reverse=True)
    total_count = len(sorted_amounts)
    
    # 상위 25%, 중위 50%, 하위 25%로 분류
    top_25_count = max(1, total_count // 4)
    mid_50_count = max(1, total_count // 2)
    
    top_25 = sorted_amounts[:top_25_count]
    mid_50 = sorted_amounts[top_25_count:top_25_count + mid_50_count]
    bottom_25 = sorted_amounts[top_25_count + mid_50_count:]
    
    return {
        "상위25%": {
            "count": len(top_25),
            "total_amount": sum(top_25),
            "avg_amount": sum(top_25) / len(top_25) if top_25 else 0,
            "min_amount": min(top_25) if top_25 else 0,
            "max_amount": max(top_25) if top_25 else 0
        },
        "중위50%": {
            "count": len(mid_50),
            "total_amount": sum(mid_50),
            "avg_amount": sum(mid_50) / len(mid_50) if mid_50 else 0,
            "min_amount": min(mid_50) if mid_50 else 0,
            "max_amount": max(mid_50) if mid_50 else 0
        },
        "하위25%": {
            "count": len(bottom_25),
            "total_amount": sum(bottom_25),
            "avg_amount": sum(bottom_25) / len(bottom_25) if bottom_25 else 0,
            "min_amount": min(bottom_25) if bottom_25 else 0,
            "max_amount": max(bottom_25) if bottom_25 else 0
        }
    }


def _group_by_period(dates: List[str]) -> Dict[str, int]:
    """기간별 그룹핑 (연도별)"""
    groups = {}
    
    for date_str in dates:
        if len(date_str) >= 4:
            year = date_str[:4]
            groups[year] = groups.get(year, 0) + 1
    
    return dict(sorted(groups.items(), reverse=True))


def _group_by_profit_loss(profit_losses: List[float]) -> Dict[str, Any]:
    """손익별 그룹핑"""
    profit_items = [p for p in profit_losses if p > 0]
    loss_items = [p for p in profit_losses if p < 0]
    neutral_items = [p for p in profit_losses if p == 0]
    
    return {
        "profit": {
            "count": len(profit_items),
            "total_amount": sum(profit_items),
            "avg_amount": sum(profit_items) / len(profit_items) if profit_items else 0
        },
        "loss": {
            "count": len(loss_items),
            "total_amount": sum(loss_items),
            "avg_amount": sum(loss_items) / len(loss_items) if loss_items else 0
        },
        "neutral": {
            "count": len(neutral_items),
            "total_amount": 0,
            "avg_amount": 0
        }
    }


def _format_investment_statistics_text(statistics: Dict[str, Any]) -> str:
    """타법인 출자현황 통계를 LLM용 텍스트로 포맷팅"""
    if not statistics:
        return "통계 데이터가 없습니다."
    
    basic = statistics.get("basic_stats", {})
    purpose_groups = statistics.get("purpose_groups", {})
    ownership_groups = statistics.get("ownership_groups", {})
    amount_groups = statistics.get("amount_groups", {})
    period_groups = statistics.get("period_groups", {})
    profit_loss_groups = statistics.get("profit_loss_groups", {})
    companies = statistics.get("companies", [])
    
    # 금액 포맷팅 함수
    def format_amount(amount):
        if amount >= 100000000:  # 1억 이상
            return f"{amount/100000000:.1f}억원"
        elif amount >= 10000:  # 1만 이상
            return f"{amount/10000:.1f}만원"
        else:
            return f"{amount:,.0f}원"
    
    result = []
    result.append("📊 타법인 출자현황 상세 분석\n")
    
    # 기본 현황
    result.append("🔍 전체 투자 규모")
    result.append(f"- 총 출자 건수: {basic.get('total_count', 0)}건")
    result.append(f"- 총 출자금액: {format_amount(basic.get('total_investment_amount', 0))}")
    result.append(f"- 평균 출자금액: {format_amount(basic.get('avg_investment_amount', 0))}")
    result.append(f"- 총 평가손익: {format_amount(basic.get('total_profit_loss', 0))}")
    result.append(f"- 수익 투자: {basic.get('profit_count', 0)}건, 손실 투자: {basic.get('loss_count', 0)}건")
    result.append("")
    
    # 주요 투자처별 상세 분석 (금액 순)
    if purpose_groups:
        result.append("🏢 주요 투자처별 분석 (금액 순)")
        sorted_purposes = sorted(purpose_groups.items(), key=lambda x: x[1]['total_amount'], reverse=True)
        for i, (purpose, data) in enumerate(sorted_purposes, 1):
            count = data.get('count', 0)
            total_amount = data.get('total_amount', 0)
            avg_ratio = data.get('avg_ownership_ratio', 0)
            percentage = (total_amount / basic.get('total_investment_amount', 1)) * 100 if basic.get('total_investment_amount', 0) > 0 else 0
            result.append(f"{i}. {purpose}: {format_amount(total_amount)} (전체의 {percentage:.1f}%, 평균 지분율: {avg_ratio:.1f}%)")
        result.append("")
    
    # 투자 목적별 전략 분석
    if purpose_groups:
        result.append("🎯 투자 목적별 전략 분석")
        for purpose, data in purpose_groups.items():
            count = data.get('count', 0)
            total_amount = data.get('total_amount', 0)
            avg_ratio = data.get('avg_ownership_ratio', 0)
            percentage = (count / basic.get('total_count', 1)) * 100
            
            # 투자 목적별 전략적 의미 해석
            if "경영참여" in purpose or "지배" in purpose:
                strategy = "계열사 지배 및 경영권 확보"
            elif "투자" in purpose or "수익" in purpose:
                strategy = "수익성 투자 및 포트폴리오 다각화"
            else:
                strategy = "전략적 투자"
            
            result.append(f"- {purpose}: {count}건 ({percentage:.1f}%) - {format_amount(total_amount)}")
            result.append(f"  → 전략: {strategy} (평균 지분율: {avg_ratio:.1f}%)")
        result.append("")
    
    # 리스크 분석
    result.append("⚠️ 리스크 분석")
    
    # 집중도 리스크
    if amount_groups and amount_groups.get("상위25%"):
        top_25_data = amount_groups["상위25%"]
        concentration_ratio = (top_25_data.get('total_amount', 0) / basic.get('total_investment_amount', 1)) * 100 if basic.get('total_investment_amount', 0) > 0 else 0
        result.append(f"- 집중도 리스크: 상위 투자처가 전체의 {concentration_ratio:.1f}% 차지")
        
        if concentration_ratio > 70:
            result.append("  → 경고: 과도한 집중도 (70% 초과)")
        elif concentration_ratio > 50:
            result.append("  → 주의: 높은 집중도 (50% 초과)")
        else:
            result.append("  → 양호: 적절한 분산 투자")
    
    # 손익 리스크
    if profit_loss_groups:
        profit_data = profit_loss_groups.get('profit', {})
        loss_data = profit_loss_groups.get('loss', {})
        total_profit_loss = basic.get('total_profit_loss', 0)
        
        if total_profit_loss > 0:
            result.append(f"- 수익성: 양호 (총 {format_amount(total_profit_loss)} 수익)")
        elif total_profit_loss < 0:
            result.append(f"- 수익성: 주의 (총 {format_amount(abs(total_profit_loss))} 손실)")
        else:
            result.append("- 수익성: 중립 (손익 없음)")
        
        result.append(f"  → 수익 투자: {profit_data.get('count', 0)}건, 손실 투자: {loss_data.get('count', 0)}건")
    
    result.append("")
    
    # 지분율별 분석
    if ownership_groups:
        result.append("📈 지분율별 분석")
        for group, count in ownership_groups.items():
            percentage = (count / basic.get('total_count', 1)) * 100
            result.append(f"- {group}: {count}건 ({percentage:.1f}%)")
        result.append("")
    
    # 기간별 투자 동향
    if period_groups:
        result.append("📅 기간별 투자 동향")
        recent_years = list(period_groups.items())[:3]  # 최근 3년
        for year, count in recent_years:
            result.append(f"- {year}년: {count}건")
        
        # 투자 동향 분석
        if len(recent_years) >= 2:
            current_year_count = recent_years[0][1]
            prev_year_count = recent_years[1][1]
            if current_year_count > prev_year_count:
                result.append("  → 투자 증가 추세")
            elif current_year_count < prev_year_count:
                result.append("  → 투자 감소 추세")
            else:
                result.append("  → 투자 안정 추세")
        result.append("")
    
    # 해외 투자 현황 (간단한 휴리스틱)
    overseas_keywords = ["해외", "overseas", "foreign", "글로벌", "global", "china", "china", "japan", "usa", "usa"]
    overseas_count = 0
    for company in companies:
        if any(keyword in company.lower() for keyword in overseas_keywords):
            overseas_count += 1
    
    if overseas_count > 0:
        result.append("🌏 해외 투자 현황")
        result.append(f"- 해외 투자 건수: {overseas_count}건")
        result.append("- 글로벌 포트폴리오 다각화 추진")
        result.append("")
    
    # 주요 피출자법인 (상세)
    if companies:
        result.append("🏢 주요 피출자법인")
        for i, company in enumerate(companies[:5], 1):  # 상위 5개만
            result.append(f"{i}. {company}")
        if len(companies) > 5:
            result.append(f"... 외 {len(companies) - 5}개")
        result.append("")
    
    # 종합 평가 요약
    result.append("📋 종합 평가 요약")
    result.append(f"- 투자 규모: {format_amount(basic.get('total_investment_amount', 0))} (총 {basic.get('total_count', 0)}건)")
    result.append(f"- 수익성: {format_amount(basic.get('total_profit_loss', 0))}")
    
    # 투자 전략 평가
    if purpose_groups:
        main_purpose = max(purpose_groups.items(), key=lambda x: x[1]['total_amount'])
        result.append(f"- 주요 전략: {main_purpose[0]} 중심 ({format_amount(main_purpose[1]['total_amount'])})")
    
    result.append("")
    
    return "\n".join(result)


# =============================================================================
# 새로운 get_investment_in_other_corp 함수들 (완전 재작성)
# =============================================================================

def _calculate_investment_statistics_new(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """타법인 출자현황 통계 계산 - 실제 DART API 필드명 사용"""
    if not items:
        return {"basic": {"total_count": 0}}
    
    # 기본 통계
    total_count = len(items)
    investment_amounts = []
    profit_losses = []
    ownership_ratios = []
    companies = []
    purposes = []
    acquisition_dates = []
    
    for item in items:
        # 출자금액 처리 (최초취득금액 - frst_acqs_amount)
        amount_str = item.get("frst_acqs_amount", "0")
        if amount_str and amount_str != "-":
            try:
                amount = float(str(amount_str).replace(",", ""))
                investment_amounts.append(amount)
            except:
                pass
        
        # 평가손익 처리 (incrs_dcrs_evl_lstmn - 증가 감소 평가 손액, 만원 단위)
        profit_loss_str = item.get("incrs_dcrs_evl_lstmn", "0")
        if profit_loss_str and profit_loss_str != "-":
            try:
                profit_loss = float(str(profit_loss_str).replace(",", "")) * 10000  # 만원 단위로 변환
                # 이상치 필터링: 1조원 이상의 손익은 제외
                if abs(profit_loss) < 1000000000000:  # 1조원 미만만 허용
                    profit_losses.append(profit_loss)
            except:
                pass
        
        # 지분율 처리 (기초잔고지분율 - bsis_blce_qota_rt)
        ownership_str = item.get("bsis_blce_qota_rt", "0")
        if ownership_str and ownership_str != "-":
            try:
                ownership = float(str(ownership_str).replace(",", ""))
                ownership_ratios.append(ownership)
            except:
                pass
        
        # 피출자법인명 (inv_prm)
        company = item.get("inv_prm", "")
        if company and company != "-":
            companies.append(company)
        
        # 투자목적 (invstmnt_purps)
        purpose = item.get("invstmnt_purps", "")
        if purpose and purpose != "-":
            purposes.append(purpose)
        
        # 취득일자 (frst_acqs_de)
        date_str = item.get("frst_acqs_de", "")
        if date_str and date_str != "-":
            try:
                # YYYY.MM.DD 형식을 YYYY로 변환
                year = date_str.split(".")[0]
                acquisition_dates.append(year)
            except:
                pass
    
    # 기본 통계 계산
    total_investment = sum(investment_amounts)
    avg_investment = total_investment / len(investment_amounts) if investment_amounts else 0
    total_profit_loss = sum(profit_losses)
    avg_ownership = sum(ownership_ratios) / len(ownership_ratios) if ownership_ratios else 0
    
    # 수익/손실 분류
    profit_count = sum(1 for pl in profit_losses if pl > 0)
    loss_count = sum(1 for pl in profit_losses if pl < 0)
    
    # 그룹별 통계 - 동적 계산
    purpose_groups = _group_by_purpose_dynamic(items)
    ownership_groups = _group_by_ownership_ratio_dynamic(ownership_ratios)
    amount_groups = _group_by_amount_dynamic(investment_amounts)
    period_groups = _group_by_period_dynamic(acquisition_dates)
    profit_loss_groups = _group_by_profit_loss_dynamic(profit_losses)
    
    return {
        "basic": {
            "total_count": total_count,
            "total_investment_amount": total_investment,
            "avg_investment_amount": avg_investment,
            "total_profit_loss": total_profit_loss,
            "avg_ownership_ratio": avg_ownership,
            "profit_count": profit_count,
            "loss_count": loss_count
        },
        "purpose_groups": purpose_groups,
        "ownership_groups": ownership_groups,
        "amount_groups": amount_groups,
        "period_groups": period_groups,
        "profit_loss_groups": profit_loss_groups,
        "companies": companies
    }


def _group_by_purpose_dynamic(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """투자목적별 동적 그룹화"""
    groups = {}
    
    for item in items:
        purpose = item.get("invstmnt_purps", "").strip()
        if not purpose or purpose == "-":
            purpose = "기타"
        
        amount_str = item.get("frst_acqs_amount", "0")
        amount = 0
        if amount_str and amount_str != "-":
            try:
                amount = float(str(amount_str).replace(",", ""))
            except:
                pass
        
        ownership_str = item.get("bsis_blce_qota_rt", "0")
        ownership = 0
        if ownership_str and ownership_str != "-":
            try:
                ownership = float(str(ownership_str).replace(",", ""))
            except:
                pass
        
        if purpose not in groups:
            groups[purpose] = {
                "count": 0,
                "total_amount": 0,
                "avg_ownership_ratio": 0,
                "ownership_ratios": []
            }
        
        groups[purpose]["count"] += 1
        groups[purpose]["total_amount"] += amount
        groups[purpose]["ownership_ratios"].append(ownership)
    
    # 평균 지분율 계산
    for purpose, data in groups.items():
        if data["ownership_ratios"]:
            data["avg_ownership_ratio"] = sum(data["ownership_ratios"]) / len(data["ownership_ratios"])
        del data["ownership_ratios"]  # 메모리 절약
    
    return groups


def _group_by_ownership_ratio_dynamic(ownership_ratios: List[float]) -> Dict[str, int]:
    """지분율별 동적 그룹화"""
    if not ownership_ratios:
        return {}
    
    # 동적으로 구간 설정
    ratios = sorted(ownership_ratios)
    n = len(ratios)
    
    if n <= 1:
        return {"전체": n}
    
    # 사분위수로 구간 설정
    q1_idx = n // 4
    q3_idx = 3 * n // 4
    
    q1 = ratios[q1_idx]
    q3 = ratios[q3_idx]
    
    groups = {
        f"0-{q1:.1f}%": 0,
        f"{q1:.1f}-{q3:.1f}%": 0,
        f"{q3:.1f}%+": 0
    }
    
    for ratio in ownership_ratios:
        if ratio <= q1:
            groups[f"0-{q1:.1f}%"] += 1
        elif ratio <= q3:
            groups[f"{q1:.1f}-{q3:.1f}%"] += 1
        else:
            groups[f"{q3:.1f}%+"] += 1
    
    return groups


def _group_by_amount_dynamic(amounts: List[float]) -> Dict[str, Dict[str, Any]]:
    """투자금액별 동적 그룹화"""
    if not amounts:
        return {}
    
    # 동적으로 구간 설정
    amounts_sorted = sorted(amounts, reverse=True)
    n = len(amounts_sorted)
    
    # 상위 25%, 50%, 75% 구간
    top_25_idx = n // 4
    top_50_idx = n // 2
    top_75_idx = 3 * n // 4
    
    groups = {
        "상위25%": {"count": top_25_idx, "total_amount": sum(amounts_sorted[:top_25_idx])},
        "상위50%": {"count": top_50_idx, "total_amount": sum(amounts_sorted[:top_50_idx])},
        "상위75%": {"count": top_75_idx, "total_amount": sum(amounts_sorted[:top_75_idx])},
        "전체": {"count": n, "total_amount": sum(amounts_sorted)}
    }
    
    return groups


def _group_by_period_dynamic(dates: List[str]) -> Dict[str, int]:
    """기간별 동적 그룹화"""
    if not dates:
        return {}
    
    groups = {}
    for date in dates:
        groups[date] = groups.get(date, 0) + 1
    
    # 최신순으로 정렬
    return dict(sorted(groups.items(), key=lambda x: x[0], reverse=True))


def _group_by_profit_loss_dynamic(profit_losses: List[float]) -> Dict[str, Dict[str, Any]]:
    """손익별 동적 그룹화"""
    if not profit_losses:
        return {}
    
    profit_items = [pl for pl in profit_losses if pl > 0]
    loss_items = [pl for pl in profit_losses if pl < 0]
    neutral_items = [pl for pl in profit_losses if pl == 0]
    
    return {
        "profit": {"count": len(profit_items), "total_amount": sum(profit_items)},
        "loss": {"count": len(loss_items), "total_amount": sum(loss_items)},
        "neutral": {"count": len(neutral_items), "total_amount": 0}
    }


def _format_investment_statistics_text_new(statistics: Dict[str, Any]) -> str:
    """새로운 투자 통계 텍스트 포맷팅"""
    basic = statistics.get("basic", {})
    purpose_groups = statistics.get("purpose_groups", {})
    ownership_groups = statistics.get("ownership_groups", {})
    amount_groups = statistics.get("amount_groups", {})
    period_groups = statistics.get("period_groups", {})
    profit_loss_groups = statistics.get("profit_loss_groups", {})
    companies = statistics.get("companies", [])
    
    def format_amount(amount: float) -> str:
        if amount >= 100000000:  # 1억 이상
            return f"{amount/100000000:.1f}억원"
        elif amount >= 10000:  # 1만 이상
            return f"{amount/10000:.1f}만원"
        else:
            return f"{amount:,.0f}원"
    
    result = []
    result.append("📊 타법인 출자현황 상세 분석")
    result.append("")
    
    # 기본 현황
    result.append("🔍 전체 투자 규모")
    result.append(f"- 총 출자 건수: {basic.get('total_count', 0)}건")
    result.append(f"- 총 출자금액: {format_amount(basic.get('total_investment_amount', 0))}")
    result.append(f"- 평균 출자금액: {format_amount(basic.get('avg_investment_amount', 0))}")
    result.append(f"- 총 평가손익: {format_amount(basic.get('total_profit_loss', 0))}")
    result.append(f"- 수익 투자: {basic.get('profit_count', 0)}건, 손실 투자: {basic.get('loss_count', 0)}건")
    result.append("")
    
    # 투자목적별 분석
    if purpose_groups:
        result.append("🎯 투자목적별 분석")
        sorted_purposes = sorted(purpose_groups.items(), key=lambda x: x[1]['total_amount'], reverse=True)
        for purpose, data in sorted_purposes:
            count = data.get('count', 0)
            total_amount = data.get('total_amount', 0)
            avg_ratio = data.get('avg_ownership_ratio', 0)
            percentage = (total_amount / basic.get('total_investment_amount', 1)) * 100 if basic.get('total_investment_amount', 0) > 0 else 0
            result.append(f"- {purpose}: {count}건 ({percentage:.1f}%) - {format_amount(total_amount)} (평균 지분율: {avg_ratio:.1f}%)")
        result.append("")
    
    # 지분율별 분석
    if ownership_groups:
        result.append("📈 지분율별 분석")
        for group, count in ownership_groups.items():
            percentage = (count / basic.get('total_count', 1)) * 100
            result.append(f"- {group}: {count}건 ({percentage:.1f}%)")
        result.append("")
    
    # 기간별 투자 동향
    if period_groups:
        result.append("📅 기간별 투자 동향")
        recent_years = list(period_groups.items())[:5]  # 최근 5년
        for year, count in recent_years:
            result.append(f"- {year}년: {count}건")
        result.append("")
    
    # 주요 피출자법인
    if companies:
        result.append("🏢 주요 피출자법인")
        for i, company in enumerate(companies[:10], 1):  # 상위 10개
            result.append(f"{i}. {company}")
        if len(companies) > 10:
            result.append(f"... 외 {len(companies) - 10}개")
        result.append("")
    
    # 종합 평가
    result.append("📋 종합 평가")
    result.append(f"- 투자 규모: {format_amount(basic.get('total_investment_amount', 0))} (총 {basic.get('total_count', 0)}건)")
    result.append(f"- 수익성: {format_amount(basic.get('total_profit_loss', 0))}")
    
    if purpose_groups:
        main_purpose = max(purpose_groups.items(), key=lambda x: x[1]['total_amount'])
        result.append(f"- 주요 전략: {main_purpose[0]} 중심 ({format_amount(main_purpose[1]['total_amount'])})")
    
    result.append("")
    
    return "\n".join(result)
