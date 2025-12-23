# DART Agent Utils 가이드

`agent/dart_agent/utils/` 하위 모듈들의 역할과 사용법을 설명합니다.

---

## ⚠️ 핵심 아키텍처 원칙 (CRITICAL)

### 에이전트와 MCP 서버의 디커플링

**대원칙: 에이전트는 MCP 도구만 이용해야 합니다.**

에이전트와 MCP 서버는 완전히 분리되어야 하며, 서로의 영역을 침범해서는 안 됩니다.

#### 금지 사항 (NEVER DO)

```python
# ❌ 에이전트가 직접 파일 시스템 접근
tree = ET.parse("/data/mcp/mcp-opendart/.../CORPCODE.xml")

# ❌ 에이전트가 MCP 서버의 캐시 파일 직접 읽기
with open("/data/mcp/.../cache/data.json") as f:
    data = json.load(f)

# ❌ 에이전트가 MCP 서버의 내부 모듈 직접 import
from mcp_opendart.utils.corp_code_search import search_corporations
```

#### 올바른 방법 (ALWAYS DO)

```python
# ✅ MCP 도구를 통한 데이터 접근
result = await mcp_client.call_tool(
    "get_corporation_code_by_name", 
    {"corp_name": "현대자동차"}
)

# ✅ MCP 응답만 파싱
if result.get("status") == "000":
    items = result.get("items", [])
    corp_code = items[0].get("corp_code")
```

#### 역할 분리

| 구성 요소 | 역할 | 접근 가능 리소스 |
|-----------|------|------------------|
| **에이전트** | MCP 도구 호출, LLM 상호작용, 결과 분석 | MCP API만 |
| **MCP 서버** | 데이터 조회, 캐시 관리, 외부 API 호출 | 파일, 캐시, 외부 API |

#### MCP 응답에 문제가 있는 경우

1. **MCP 서버 코드 수정**: `/data/mcp/mcp-opendart/` 내의 도구 구현 수정
2. **agent-platform 코드 참조**: `/Users/lchangoo/Workspace/agent-platform/agent/dart_agent`
3. **에이전트 코드에서 우회 금지**: 직접 리소스 접근으로 문제 해결하지 않음

---

## ⚠️ 하드코딩 지양 원칙 (NO HARDCODING)

### 필드명 하드코딩 금지

MCP 응답의 필드명은 서버마다 다를 수 있습니다. 특정 필드명에 의존하지 마세요.

```python
# ❌ 하드코딩된 필드명
corp_code = item.get("corp_code")
corp_name = item.get("corp_name")

# ✅ 헬퍼 함수로 여러 필드명 지원
def get_item_corp_code(item: Dict[str, Any]) -> str:
    """여러 필드명 형식 지원"""
    return item.get("corporation_code") or item.get("corp_code", "")

def get_item_corp_name(item: Dict[str, Any]) -> str:
    """여러 필드명 형식 지원"""
    return item.get("corporation_name") or item.get("corp_name", "")

corp_code = get_item_corp_code(item)
corp_name = get_item_corp_name(item)
```

### 경로 하드코딩 금지

```python
# ❌ 하드코딩된 경로
corpcode_path = "/data/mcp/mcp-opendart/.../CORPCODE.xml"

# ✅ 환경변수 또는 설정 사용
import os
mcp_storage_path = os.environ.get("MCP_STORAGE_PATH", "/data/mcp")
```

### 정규식 패턴 하드코딩 최소화

```python
# ❌ 매직 넘버, 하드코딩된 패턴
if "005380" in stock_code:  # 현대자동차?

# ✅ 명시적 조건 사용
if stock_code and stock_code.strip():  # 상장기업 여부 확인
```

### LLM 프롬프트 하드코딩 지양

프롬프트는 `prompt_templates/` 디렉토리에서 관리합니다.

```python
# ❌ 인라인 프롬프트
prompt = "당신은 금융 분석 전문가입니다..."

# ✅ PromptBuilder 사용
from .utils.prompt_templates import PromptBuilder
prompt_builder = PromptBuilder()
system_prompt = prompt_builder.build_system_prompt(domain="financial")
```

### 하드코딩 허용 예외

- 상수 정의 (`MAX_RETRIES = 3`)
- 기본값 (`timeout: float = 30.0`)
- 테스트 데이터
- 에러 메시지 (단, 다국어 지원 시 분리 필요)

---

## 목차

- [프롬프트 템플릿](#프롬프트-템플릿)
- [메모리 관리](#메모리-관리)
- [메시지 처리](#메시지-처리)
- [스트리밍 유틸리티](#스트리밍-유틸리티)
- [데이터 변환](#데이터-변환)

## 프롬프트 템플릿

### 구조

```
utils/prompt_templates/
├── __init__.py
├── prompt_builder.py          # 프롬프트 조합기
├── base_prompt.py             # 공통 프롬프트 템플릿
├── domain_specific.py         # 도메인별 특화 템플릿
├── financial_tools.py          # 재무 도구 설명
├── governance_tools.py         # 지배구조 도구 설명
├── capital_change_tools.py     # 자본변동 도구 설명
├── debt_funding_tools.py       # 부채자금조달 도구 설명
├── business_structure_tools.py # 사업구조 도구 설명
├── overseas_business_tools.py # 해외사업 도구 설명
├── legal_compliance_tools.py   # 법적컴플라이언스 도구 설명
├── executive_audit_tools.py   # 임원감사 도구 설명
└── document_analysis_tools.py  # 문서 분석 도구 설명
```

### PromptBuilder

**위치**: `utils/prompt_templates/prompt_builder.py`

프롬프트 조합기로 공통 템플릿과 도메인별 특화 부분을 조합합니다.

```python
from app.agents.dart_agent.utils.prompt_templates import PromptBuilder

prompt_builder = PromptBuilder()

# System Prompt 생성 (에이전트 초기화용)
system_prompt = prompt_builder.build_system_prompt(domain="financial")

# User Request Prompt 생성 (실행 시)
user_prompt = prompt_builder.build_user_request_prompt(
    context=analysis_context,
    domain="financial",
    tools_info=tools_description
)
```

**주요 메서드**:
- `build_system_prompt(domain)`: 에이전트 초기화용 System Prompt 생성
- `build_user_request_prompt(context, domain, tools_info)`: 실행 시 User Prompt 생성
- `_get_tools_description(domain)`: 도메인별 도구 설명 가져오기

### BasePromptTemplate

**위치**: `utils/prompt_templates/base_prompt.py`

공통 프롬프트 템플릿으로 모든 에이전트가 공유하는 부분을 제공합니다:

- 핵심 원칙
- 기업 정보
- 경고 사항
- 작업 지시사항
- 문서 분석 워크플로우 (해당 시)

### DomainSpecificTemplates

**위치**: `utils/prompt_templates/domain_specific.py`

각 에이전트별 특화된 분석 요청 및 도구 설명을 제공합니다:

- 도메인별 역할 설명
- 도메인별 분석 지침
- 도구 섹션 헤더

### 도구별 프롬프트 파일

각 에이전트의 도구 설명을 별도 파일로 관리합니다:

- `financial_tools.py`: 재무 도구 설명 (8개)
- `governance_tools.py`: 지배구조 도구 설명 (8개)
- `capital_change_tools.py`: 자본변동 도구 설명 (11개)
- `debt_funding_tools.py`: 부채자금조달 도구 설명 (15개)
- `business_structure_tools.py`: 사업구조 도구 설명 (17개)
- `overseas_business_tools.py`: 해외사업 도구 설명 (4개)
- `legal_compliance_tools.py`: 법적컴플라이언스 도구 설명 (7개)
- `executive_audit_tools.py`: 임원감사 도구 설명 (9개)
- `document_analysis_tools.py`: 문서 분석 도구 설명 (3개)

**사용 예시**:

```python
from app.agents.dart_agent.utils.prompt_templates.financial_tools import get_financial_tools_description

tools_description = get_financial_tools_description()
# 도구 설명 문자열 반환
```

## 메모리 관리

### DartMemoryManager

**위치**: `utils/memory_manager.py`

LangGraph 표준을 준수하는 메모리 관리자입니다.

**주요 기능**:
- 단기 메모리 (Checkpointer): 대화 히스토리, 도구 호출 기록
- 장기 메모리 (Store API): 사용자 프로필, 분석 패턴
- 메시지 트림: 중요도 기반 메시지 트림

**사용 예시**:

```python
from app.agents.dart_agent.utils.memory_manager import DartMemoryManager

memory_manager = DartMemoryManager(checkpointer, store)

# 메시지 조회
messages = memory_manager.get_messages(thread_id)

# 메시지 트림
trimmed_messages = await memory_manager.intelligent_trim_messages(
    messages, 
    agent_type="financial",
    max_tokens=15000
)
```

### MemoryTypes

**위치**: `utils/memory_types.py`

메모리 관련 데이터 구조를 정의합니다:

- `AnalysisCache`: 분석 결과 캐시
- `TokenUsage`: 토큰 사용량 추적
- `MemoryConfig`: 메모리 관리 설정

## 메시지 처리

### MessageGenerator

**위치**: `utils/message_generator.py`

LLM 기반 동적 메시지 생성기입니다. 경량 모델(google/gemma-3-27b-it)을 활용합니다.

**주요 메서드**:
- `generate_progress_message(action, context)`: 진행 상황 메시지 생성
- `generate_error_message(error_type, context)`: 오류 메시지 생성
- `generate_agent_introduction(question_type, context)`: 에이전트 소개 메시지 생성

**사용 예시**:

```python
from app.agents.dart_agent.utils.message_generator import MessageGenerator

message_generator = MessageGenerator()

progress_msg = await message_generator.generate_progress_message(
    action="single_agent_analysis",
    context={
        "user_question": "한화생명의 재무제표를 분석해줘",
        "corp_name": "한화생명",
        "agents": ["재무 분석"]
    }
)
```

### MessageRefiner

**위치**: `utils/message_refiner.py` 및 `message_refiner.py`

사용자 친화적 메시지로 변환하는 메시지 정제 시스템입니다.

**주요 메서드**:
- `refine(technical_message, message_type)`: 기술적 메시지를 사용자 친화적으로 변환
- `get_action_message(tool_name)`: 도구 호출 액션 메시지 반환

**사용 예시**:

```python
from app.agents.dart_agent.message_refiner import MessageRefiner

message_refiner = MessageRefiner()

# 도구명 정제
display_name = message_refiner.refine("get_single_acnt", "tool_call")
# → "재무제표 조회"

# 액션 메시지
action_msg = message_refiner.get_action_message("get_single_acnt")
# → "공시 목록을 검색하고 있습니다"
```

## 스트리밍 유틸리티

### StreamAccumulator

**위치**: `utils/stream_utils.py`

LangGraph stream 이벤트 누적/조립기입니다.

**주요 기능**:
- 메시지 버퍼링 및 재조립
- 도구 호출/결과 추적
- 최근 값 보관

**사용 예시**:

```python
from app.agents.dart_agent.utils.stream_utils import StreamAccumulator

accumulator = StreamAccumulator()

for event in stream:
    result = accumulator.feed(event)
    if result:
        # 완성된 메시지 처리
        print(result["final_message"])
```

### StreamingMemory

**위치**: `utils/streaming_memory.py`

스트리밍 중 메모리 관리를 위한 유틸리티입니다.

## 데이터 변환

### DartTransformer

**위치**: `dart_transformer.py` 및 `utils/dart_transformer.py`

DART API 응답을 LLM이 이해하기 쉬운 형태로 변환합니다.

**주요 기능**:
- 재무제표 데이터 변환
- 재무지표 데이터 변환
- 타법인 출자현황 개선 (동적 그룹핑)
- 통계 데이터 변환

**사용 예시**:

```python
from app.agents.dart_agent.dart_transformer import transform_dart_result

# 도구 결과 변환
transformed_result = transform_dart_result(
    tool_name="get_single_acnt",
    result_data=raw_data
)
```

### DartTypes

**위치**: `dart_types.py` 및 `utils/dart_types.py`

공통 데이터 구조를 정의합니다:

- `AnalysisContext`: 분석 컨텍스트
- `AgentResult`: 에이전트 분석 결과
- `IntentClassificationResult`: 의도 분류 결과
- `AnalysisScope/Domain/Depth`: 분석 분류 Enum
- `RiskLevel`: 리스크 수준 Enum

**사용 예시**:

```python
from app.agents.dart_agent.dart_types import (
    AnalysisContext,
    AgentResult,
    create_analysis_context,
    AnalysisScope,
    AnalysisDomain,
    AnalysisDepth,
    RiskLevel
)

# 분석 컨텍스트 생성
context = create_analysis_context(
    corp_code="00126380",
    corp_name="한화생명",
    user_question="재무제표를 분석해줘",
    classification=classification_result
)

# AgentResult 생성
agent_result = AgentResult(
    agent_name="FinancialAgent",
    analysis_type="financial_analysis",
    risk_level=RiskLevel.LOW,
    key_findings=["..."],
    supporting_data={...},
    execution_time=1.5
)
```

## 개선 가이드라인

### 프롬프트 템플릿 수정

1. **공통 부분**: `BasePromptTemplate` 수정
2. **도메인 특화**: `DomainSpecificTemplates` 수정
3. **도구 설명**: 각 `*_tools.py` 파일 수정

### 메모리 관리 최적화

- 토큰 제한 설정 조정
- 메시지 트림 전략 개선
- 캐시 정리 정책 수립

### 메시지 생성 개선

- LLM 모델 변경 (필요 시)
- 메시지 톤 및 스타일 조정
- 에러 메시지 개선

## 주의사항

1. **프롬프트 일관성**: 모든 에이전트가 일관된 프롬프트 구조를 유지해야 함
2. **도구 설명 정확성**: 도구 설명이 실제 MCP 도구와 일치해야 함
3. **메모리 효율성**: 토큰 제한을 적절히 설정하여 메모리 사용량 관리
4. **메시지 품질**: 사용자 친화적이고 명확한 메시지 생성

## 관련 파일

- `app/agents/dart_agent/utils/prompt_templates/`: 프롬프트 템플릿 디렉토리
- `app/agents/dart_agent/utils/memory_manager.py`: 메모리 관리자
- `app/agents/dart_agent/utils/message_generator.py`: 메시지 생성기
- `app/agents/dart_agent/message_refiner.py`: 메시지 정제 시스템
- `app/agents/dart_agent/utils/stream_utils.py`: 스트리밍 유틸리티
- `app/agents/dart_agent/dart_transformer.py`: 데이터 변환 유틸리티
- `app/agents/dart_agent/dart_types.py`: 공통 데이터 구조

