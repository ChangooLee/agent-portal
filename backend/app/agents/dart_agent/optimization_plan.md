# DART 멀티에이전트 시스템 개발 가이드

## 🎯 핵심 철학
**"에이전트는 데이터 수집기, LLM은 분석가"**

데이터 드리븐 멀티에이전트 시스템으로 할루시네이션을 방지하고 실제 데이터 기반 분석을 보장

## 📊 비판적 현실 인식

### 🚨 시스템 문제 패턴 (실패 중심 분석)
1. **데이터 수집 실패**: 0개 레코드 수집 상황 발생
2. **MCP 도구 오류**: 인덱스 오류 등 도구 호출 실패
3. **메모리 관리 문제**: 에이전트 소멸자 오류
4. **프로세스 안정성**: 워커 프로세스 비정상 종료
5. **도구 추적 누락**: 실제 호출과 추적 결과 불일치

### ⚠️ 잘못된 접근 방식 (금지 사항)
❌ **성급한 성공 판단**: 로그 메시지만으로 성공 판단  
❌ **에이전트 LLM 분석**: 서브 에이전트가 분석/판단 수행  
❌ **하드코딩된 응답**: 시스템 프롬프트 기반 가짜 응답  
❌ **할루시네이션 허용**: 도구 결과 없이 추측으로 응답  

## 🚀 올바른 개발 원칙

### 1. 에이전트 역할 분리 원칙
```python
# ❌ 잘못된 에이전트 (분석/판단 수행)
class WrongFinancialAgent:
    async def analyze(self, context):
        data = await self.collect_data()
        # 🚨 금지: 에이전트가 LLM으로 분석/판단
        analysis = await self.llm.analyze(data)  # ❌
        return {"risk_level": "HIGH", "recommendation": "..."}  # ❌

# ✅ 올바른 에이전트 (데이터 수집만)
class CorrectFinancialAgent:
    async def analyze_with_context(self, context):
        # ✅ 허용: MCP 도구 호출 및 데이터 수집
        financial_data = await self.collect_financial_data()
        financial_ratios = await self.collect_financial_ratios()
        
        # ✅ 허용: 원본 데이터 정리 및 구조화
        return AgentResult(
            agent_type="data_collection",
            data={
                "financial_statements": financial_data,
                "financial_ratios": financial_ratios
            },
            metadata={"tools_used": ["get_single_acnt", "get_single_index"]},
            analysis=None  # 🔑 분석 없음
        )
```

### 2. 마스터 LLM 분석 원칙
```python
# ✅ 올바른 마스터 에이전트
class DartMasterAgent:
    async def _integrate_results_with_llm_analysis(self, agent_results):
        # 1. 에이전트들로부터 원본 데이터 수집
        collected_data = {}
        for agent_name, result in agent_results.items():
            collected_data[agent_name] = result.data  # 원본 데이터만
        
        # 2. 마스터 LLM에 데이터 전달하여 종합 분석
        analysis_prompt = f"""
        수집된 원본 데이터를 바탕으로 종합 분석을 수행하세요:
        
        사용자 질문: {self.user_question}
        수집된 데이터: {collected_data}
        
        다음 형식으로 JSON 응답하세요:
        {{
            "analysis_summary": "데이터 기반 분석 요약",
            "key_findings": ["실제 데이터에서 발견된 사실들"],
            "risk_assessment": {{"overall_risk": "HIGH/MEDIUM/LOW"}}
        }}
        """
        
        # 3. 마스터 LLM이 모든 분석과 판단 수행
        return await self.llm.ainvoke([HumanMessage(content=analysis_prompt)])
```

### 3. 비판적 분석 및 검증 원칙

#### A. 로그 분석 방법론
```python
class CriticalLogAnalyzer:
    def analyze_system_health(self, logs):
        """
        비판적 로그 분석 - 실패 중심 접근:
        1. 🚨 오류/실패 우선 검토
        2. ⚠️ 성능 경고 분석  
        3. 📊 실제 데이터 수집 결과 검증
        4. 🔍 메모리/시스템 안정성 확인
        """
        
        # 1. 실패 지표 우선 검토
        failures = [
            "총 0개 레코드 수집",  # 데이터 수집 실패
            "list index out of range",  # MCP 도구 오류
            "메모리 누수 패턴",  # 메모리 관리 문제
            "Worker exited with code 1",  # 프로세스 종료
            "tools_used: []"  # 도구 추적 실패
        ]
        
        # 2. 성공 메시지는 의심하고 검증
        success_claims = [
            "데이터 수집 완료",  # 실제 결과 확인 필요
            "도구 실행 완료",  # 실제 오류 발생 가능
            "분석 완료"  # 할루시네이션 가능성
        ]
        
        return self.verify_actual_results(logs)
```

#### B. 데이터 수집 검증
```python
class DataCollectionValidator:
    def validate_agent_results(self, agent_result):
        """
        에이전트 결과 검증:
        - 실제 도구 호출 여부 확인
        - 수집된 레코드 수 검증 (0개 = 실패)
        - 원본 데이터 변조 여부 확인
        - 분석/판단 포함 여부 검사 (금지)
        """
        
        # 1. 데이터 수집 실패 검증
        if not agent_result.data or len(agent_result.data) == 0:
            raise DataCollectionFailure("0개 레코드 수집 - 명확한 실패")
        
        # 2. 분석 포함 여부 검사
        if hasattr(agent_result, 'analysis') and agent_result.analysis:
            raise AnalysisViolation("에이전트가 분석 수행 - 역할 위반")
        
        # 3. 도구 사용 추적 검증
        if not agent_result.metadata.get("tools_used"):
            raise ToolTrackingFailure("도구 사용 추적 실패")
        
        return True
```

### 4. 시스템 안정성 보장

#### A. 메모리 관리 원칙
```python
# ❌ 문제가 있는 소멸자 패턴
class ProblematicAgent:
    def __del__(self):
        # 🚨 오류: 정의되지 않은 변수 참조
        if hasattr(self, 'undefined_var'):
            del undefined_var  # ❌ 잘못된 접근

# ✅ 올바른 소멸자 패턴
class StableAgent:
    def __del__(self):
        try:
            # ✅ 올바른 속성 정리
            if hasattr(self, 'agent_executor'):
                self.agent_executor = None
            if hasattr(self, 'llm_with_tools'):
                self.llm_with_tools = None
            if hasattr(self, 'checkpointer'):
                self.checkpointer = None
        except Exception:
            # 소멸자에서는 예외를 무시
            pass
```

#### B. MCP 도구 오류 처리 원칙
```python
class RobustMCPHandler:
    async def call_mcp_tool(self, tool_name: str, params: dict):
        """
        MCP 도구 호출 시 오류 처리:
        - 인덱스 오류 등 예외 처리
        - 재시도 메커니즘
        - 대체 도구 자동 선택
        """
        try:
            result = await self.mcp_client.call_tool(tool_name, params)
            
            # 결과 검증
            if not result or len(result) == 0:
                raise DataCollectionFailure(f"{tool_name}: 0개 레코드 반환")
            
            return result
            
        except IndexError as e:
            # 인덱스 오류 처리
            self.logger.error(f"MCP 도구 {tool_name} 인덱스 오류: {e}")
            return await self.try_alternative_tool(tool_name, params)
            
        except Exception as e:
            self.logger.error(f"MCP 도구 {tool_name} 실행 실패: {e}")
            raise ToolExecutionFailure(f"{tool_name} 실행 실패: {e}")
```

## 📊 성공 지표 (비판적 기준)

### 1. 실제 데이터 수집 성공률
- **측정 기준**: 수집된 레코드 수 > 0, MCP 도구 오류 < 5%
- **목표**: 실제 데이터 수집 성공률 95% 이상

### 2. 시스템 안정성
- **측정 기준**: 소멸자 오류 0건, 워커 프로세스 정상 유지
- **목표**: 메모리 누수 0건, 프로세스 안정성 99.9%

### 3. 분석 품질 (할루시네이션 방지)
- **측정 기준**: 모든 분석이 수집된 데이터 기반, 추측성 응답 금지
- **목표**: 100% 데이터 기반 분석, 할루시네이션 0%

### 4. 도구 추적 정확성
- **측정 기준**: 로그와 최종 응답의 도구 목록 일치
- **목표**: 실제 사용된 도구 100% 추적

## 🛠️ 개발 우선순위 (실패 해결 중심)

### Phase 1: 시스템 안정성 확보
1. **메모리 관리 개선** - 소멸자 오류 해결
2. **MCP 도구 오류 처리** - 인덱스 오류 해결
3. **프로세스 안정화** - 워커 프로세스 종료 방지
4. **도구 추적 시스템 개선** - 정확한 추적

### Phase 2: 데이터 수집 보장
1. **데이터 수집 실패 해결** - 실제 데이터 수집 보장
2. **에이전트 역할 분리 완성** - 분석 기능 완전 제거
3. **마스터 LLM 분석 강화** - 모든 분석을 마스터 LLM으로 이관
4. **데이터 검증 시스템 구축** - 수집 결과 실시간 검증

### Phase 3: 품질 보장
1. **비판적 로그 분석 시스템** - 실패 우선 모니터링
2. **할루시네이션 방지 체계** - 데이터 기반 응답 강제
3. **성능 모니터링 강화** - 응답시간 개선
4. **사용자 피드백 반영** - 실제 사용성 개선

## 🔄 지속적 품질 관리

### 1. 실패 중심 모니터링
- **일일**: 로그 실패 패턴 분석
- **주간**: 데이터 수집 실패율 리포트
- **월간**: 시스템 안정성 종합 평가

### 2. 비판적 성과 평가
- **성공 메시지 의심**: "완료" 로그의 실제 결과 검증
- **데이터 기반 판단**: 추측이 아닌 실제 수치 기반 평가
- **보수적 접근**: 문제가 해결되기 전까지는 실패로 간주

### 3. 개발 원칙 준수
- **비판적 사고**: 성급한 성공 판단 금지
- **로그 분석**: 실패 부분 우선 검토 방법론
- **데이터 검증**: 실제 결과 확인 절차

