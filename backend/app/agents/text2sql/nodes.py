"""
LangGraph Nodes for Text-to-SQL Agent

참조: docs/plans/DATA_CLOUD_AGENT.md 섹션 4. LangGraph 노드 설계

9개 노드 함수:
1. entry_node - 초기 state 구성
2. dialect_resolver - dialect 매핑
3. schema_selector - 스키마 메타데이터 조회
4. planner_node - JSON 플랜 생성
5. sql_generator_node - SQL 후보 생성
6. sql_executor_node - SQL 실행 검증
7. sql_repair_node - 에러 기반 SQL 수정
8. answer_formatter_node - 최종 응답 생성
9. human_review_node - Human-in-the-loop 처리
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional

from .state import SqlAgentState, Dialect
from .prompts import (
    get_dialect_rules,
    build_planner_prompt,
    build_generator_prompt,
    build_repair_prompt,
    build_answer_prompt
)
from .metrics import (
    start_span,
    end_span,
    start_agent_span,
    start_llm_call_span,
    get_trace_headers,
    record_counter,
    record_histogram
)

logger = logging.getLogger(__name__)


# ========== 1. Entry Node ==========

async def entry_node(state: SqlAgentState) -> SqlAgentState:
    """
    초기 state 구성 및 기본값 설정.
    
    책임:
    - retry_count = 0
    - max_retries = 설정값
    - needs_human_review = False
    - metrics_tags에 기본 태그 설정
    - entry_carrier 설정 (다른 노드들의 parent)
    
    OTEL:
    - span: "text2sql.entry" (parent: root span)
    - metric: text2sql_requests_total 증가
    """
    with start_agent_span(state, "text2sql.entry", {
        "question_length": len(state.get("question", ""))
    }, is_entry=True):
        # 기본값 설정 (이미 create_initial_state에서 설정되었을 수 있음)
        if state.get("retry_count") is None:
            state["retry_count"] = 0
        if state.get("max_retries") is None:
            state["max_retries"] = int(os.getenv("TEXT2SQL_MAX_RETRIES", "2"))
        if state.get("needs_human_review") is None:
            state["needs_human_review"] = False
        if state.get("start_time") is None:
            state["start_time"] = time.time()
        if state.get("candidate_sql") is None:
            state["candidate_sql"] = []
        
        # metrics_tags 설정
        state["metrics_tags"] = {
            "service": "agent-portal",
            "component": "text2sql",
            "phase": "entry",
            "connection_id": state.get("connection_id", "unknown")
        }
        
        # Counter 기록
        record_counter("text2sql_requests_total", {
            "dialect": "unknown",
            "source": "api"
        })
        
        logger.info(f"Entry node: question='{state['question'][:50]}...', connection_id={state['connection_id']}")
        
        return state


# ========== 2. Dialect Resolver ==========

async def dialect_resolver(state: SqlAgentState) -> SqlAgentState:
    """
    connection_id를 사용해 dialect 매핑.
    
    책임:
    - Data Cloud 메타데이터에서 DB 타입 조회
    - SQLAlchemy engine.dialect.name 기준으로 매핑
    - dialect에 따른 규칙 문자열 생성
    
    OTEL:
    - span: "text2sql.dialect_resolver" (parent: entry_node)
    - metric: text2sql_dialect_resolved_total
    """
    with start_agent_span(state, "text2sql.dialect_resolver"):
        try:
            # Data Cloud 서비스에서 연결 정보 조회
            from app.services.datacloud_service import datacloud_service
            
            connection = await datacloud_service.get_connection_by_id(state["connection_id"])
            
            if not connection:
                state["execution_error"] = f"Connection not found: {state['connection_id']}"
                state["needs_human_review"] = True
                state["human_review_reason"] = "connection_not_found"
                return state
            
            # DB 타입에서 dialect 매핑
            db_type = connection.get("db_type", "generic").lower()
            
            dialect_map = {
                "postgresql": "postgres",
                "postgres": "postgres",
                "mysql": "mysql",
                "mariadb": "mariadb",
                "oracle": "oracle",
                "clickhouse": "clickhouse",
                "hana": "hana",
                "sap_hana": "hana",
                "databricks": "databricks",
                "spark": "databricks",
            }
            
            dialect: Dialect = dialect_map.get(db_type, "generic")
            state["dialect"] = dialect
            
            # Dialect 규칙 문자열 생성
            state["dialect_rules"] = get_dialect_rules(dialect)
            
            # metrics_tags 업데이트
            if state.get("metrics_tags"):
                state["metrics_tags"]["dialect"] = dialect
                state["metrics_tags"]["phase"] = "dialect_resolved"
            
            # Counter 기록
            record_counter("text2sql_dialect_resolved_total", {
                "dialect": dialect,
                "success": "true"
            })
            
            logger.info(f"Dialect resolved: {db_type} -> {dialect}")
            
            return state
            
        except Exception as e:
            logger.error(f"Dialect resolver error: {e}")
            record_counter("text2sql_dialect_resolved_total", {
                "dialect": "unknown",
                "success": "false"
            })
            state["execution_error"] = str(e)
            return state


# ========== 3. Schema Selector ==========

async def schema_selector(state: SqlAgentState) -> SqlAgentState:
    """
    스키마 메타데이터 조회.
    
    책임:
    - connection_id로 스키마 조회
    - 스키마를 프롬프트용 문자열로 포맷
    
    OTEL:
    - span: "text2sql.schema_selector" (parent: dialect_resolver)
    - metric: text2sql_schema_fetch_latency_ms, text2sql_schema_table_count
    """
    with start_agent_span(state, "text2sql.schema_selector"):
        start_time = time.time()
        
        try:
            from app.services.datacloud_service import datacloud_service
            
            # 스키마 메타데이터 조회
            schema = await datacloud_service.get_schema_metadata(state["connection_id"])
            
            if not schema or "error" in schema:
                state["execution_error"] = schema.get("error", "Failed to fetch schema")
                state["needs_human_review"] = True
                state["human_review_reason"] = "schema_fetch_failed"
                return state
            
            # 스키마를 프롬프트용 문자열로 변환
            tables = schema.get("tables", [])
            
            schema_lines = []
            for table in tables[:20]:  # 최대 20개 테이블
                table_name = table.get("name", "unknown")
                columns = table.get("columns", [])
                
                col_defs = []
                for col in columns[:30]:  # 테이블당 최대 30개 컬럼
                    col_name = col.get("name", "")
                    col_type = col.get("type", "")
                    pk = " (PK)" if col.get("primary_key") or col.get("is_primary_key") else ""
                    fk = " (FK)" if col.get("foreign_key") or col.get("is_foreign_key") else ""
                    col_defs.append(f"  - {col_name}: {col_type}{pk}{fk}")
                
                schema_lines.append(f"Table: {table_name}")
                schema_lines.extend(col_defs)
                schema_lines.append("")
            
            state["schema_summary"] = "\n".join(schema_lines)
            state["schema_graph"] = {
                "tables": [t.get("name") for t in tables],
                "table_count": len(tables)
            }
            
            # Latency 기록
            latency_ms = (time.time() - start_time) * 1000
            record_histogram("text2sql_schema_fetch_latency_ms", latency_ms, {
                "dialect": state.get("dialect", "unknown")
            })
            record_histogram("text2sql_schema_table_count", len(tables), {
                "dialect": state.get("dialect", "unknown")
            })
            
            logger.info(f"Schema selected: {len(tables)} tables")
            
            return state
            
        except Exception as e:
            logger.error(f"Schema selector error: {e}")
            state["execution_error"] = str(e)
            return state


# ========== 4. Planner Node ==========

async def planner_node(state: SqlAgentState) -> SqlAgentState:
    """
    Plan-and-Execute 패턴의 Planner.
    
    책임:
    - question, schema_summary, dialect 정보로 JSON 플랜 생성
    - 어떤 테이블/조인/필터/집계를 사용할지 결정
    - SQL은 쓰지 않고 플랜만 생성
    
    OTEL:
    - span: "text2sql.planner" (parent: schema_selector)
    - metric: text2sql_planning_latency_ms, tokens
    - LLM 호출도 같은 TraceId로 연결
    """
    with start_agent_span(state, "text2sql.planner", {
        "has_schema": bool(state.get("schema_summary"))
    }) as span:
        start_time = time.time()
        
        try:
            from app.services.litellm_service import litellm_service
            
            # 프롬프트 구성
            system_prompt, user_prompt = build_planner_prompt(
                question=state["question"],
                dialect=state.get("dialect", "generic"),
                dialect_rules=state.get("dialect_rules", ""),
                schema_summary=state.get("schema_summary", "")
            )
            
            # LLM 호출 (LLM call span으로 감싸서 트리 구조 유지)
            model = os.getenv("TEXT2SQL_MODEL_PRIMARY", "qwen-235b")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # LLM 호출 span 생성 (planner 노드의 child)
            with start_llm_call_span(state, "planner", model, messages) as (llm_span, record_llm_result):
                response = await litellm_service.chat_completion_sync(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000,
                    metadata={
                        "agent_id": "text2sql",
                        "node": "planner",
                        "trace_id": state.get("trace_id")
                    }
                )
                # LLM 응답 정보를 span에 기록
                record_llm_result(response)
            
            # 응답 파싱
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # JSON 추출
            plan = _extract_json(content)
            state["plan"] = plan
            
            # Span에 결과 기록
            if span and hasattr(span, 'set_attribute'):
                span.set_attribute("plan_created", plan is not None)
            
            # 토큰 사용량 집계
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            # 누적 토큰 업데이트
            state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + prompt_tokens
            state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + completion_tokens
            state["total_tokens"] = state.get("total_tokens", 0) + prompt_tokens + completion_tokens
            state["llm_model"] = model  # 사용된 모델 저장
            
            # Latency 및 토큰 기록
            latency_ms = (time.time() - start_time) * 1000
            record_histogram("text2sql_planning_latency_ms", latency_ms, {
                "dialect": state.get("dialect", "unknown"),
                "model": model
            })
            record_histogram("text2sql_planning_tokens_prompt", prompt_tokens, {})
            record_histogram("text2sql_planning_tokens_completion", completion_tokens, {})
            
            logger.info(f"Plan created (tokens: {prompt_tokens}+{completion_tokens}): {json.dumps(plan)[:100]}...")
            
            return state
            
        except Exception as e:
            logger.error(f"Planner error: {e}")
            record_counter("text2sql_planning_errors_total", {
                "dialect": state.get("dialect", "unknown")
            })
            # 플랜 실패해도 계속 진행 (Generator가 직접 SQL 생성)
            state["plan"] = None
            return state


# ========== 5. SQL Generator Node ==========

async def sql_generator_node(state: SqlAgentState) -> SqlAgentState:
    """
    SQL 후보 생성.
    
    책임:
    - plan + schema_summary + dialect로 SQL 생성
    - <reasoning> + <sql> 태그 포맷 사용
    - 여러 후보 생성 (온도 다르게)
    
    OTEL:
    - span: "text2sql.generator" (parent: planner)
    - metric: text2sql_generation_latency_ms, candidate_count
    - LLM 호출도 같은 TraceId로 연결
    """
    with start_agent_span(state, "text2sql.generator", {
        "has_plan": bool(state.get("plan"))
    }) as span:
        start_time = time.time()
        
        try:
            from app.services.litellm_service import litellm_service
            
            model = os.getenv("TEXT2SQL_MODEL_PRIMARY", "qwen-235b")
            candidates = []
            reasoning = ""
            
            # 온도별로 후보 생성 (2개)
            temperatures = [0.0, 0.3]
            
            for idx, temp in enumerate(temperatures):
                system_prompt, user_prompt = build_generator_prompt(
                    question=state["question"],
                    dialect=state.get("dialect", "generic"),
                    dialect_rules=state.get("dialect_rules", ""),
                    schema_summary=state.get("schema_summary", ""),
                    plan=state.get("plan")
                )
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                # LLM 호출 span 생성 (generator 노드의 child)
                with start_llm_call_span(state, f"generator_{idx}", model, messages) as (llm_span, record_llm_result):
                    if llm_span and hasattr(llm_span, 'set_attribute'):
                        llm_span.set_attribute("llm.temperature", temp)
                    
                    response = await litellm_service.chat_completion_sync(
                        model=model,
                        messages=messages,
                        temperature=temp,
                        max_tokens=2000,
                        metadata={
                            "agent_id": "text2sql",
                            "node": "generator",
                            "temperature": temp,
                            "trace_id": state.get("trace_id")
                        }
                    )
                    # LLM 응답 정보를 span에 기록
                    record_llm_result(response)
                
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # 토큰 사용량 누적
                usage = response.get("usage", {})
                state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
                state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
                state["total_tokens"] = state.get("total_tokens", 0) + usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                
                # SQL 추출
                sql = _extract_sql(content)
                if sql and sql not in candidates:
                    candidates.append(sql)
                    
                # 첫 번째 응답의 reasoning 저장
                if not reasoning:
                    reasoning = _extract_reasoning(content)
            
            if not candidates:
                state["execution_error"] = "No SQL candidates generated"
                return state
            
            state["candidate_sql"] = candidates
            state["chosen_sql"] = candidates[0]  # 첫 번째를 기본 선택
            state["sql_reasoning"] = reasoning
            
            # Span에 결과 기록
            if span and hasattr(span, 'set_attribute'):
                span.set_attribute("candidate_count", len(candidates))
                span.set_attribute("sql_length", len(candidates[0]) if candidates else 0)
            
            # Latency 및 후보 수 기록
            latency_ms = (time.time() - start_time) * 1000
            record_histogram("text2sql_generation_latency_ms", latency_ms, {
                "dialect": state.get("dialect", "unknown"),
                "model": model
            })
            record_histogram("text2sql_candidate_count", len(candidates), {
                "dialect": state.get("dialect", "unknown")
            })
            
            # 토큰 Histogram 기록 (generator 노드에서 사용한 총 토큰)
            total_gen_prompt = state.get("total_prompt_tokens", 0)
            total_gen_completion = state.get("total_completion_tokens", 0)
            record_histogram("text2sql_generation_tokens_prompt", total_gen_prompt, {
                "dialect": state.get("dialect", "unknown")
            })
            record_histogram("text2sql_generation_tokens_completion", total_gen_completion, {
                "dialect": state.get("dialect", "unknown")
            })
            
            logger.info(f"Generated {len(candidates)} SQL candidates (tokens: {total_gen_prompt}+{total_gen_completion})")
            
            return state
            
        except Exception as e:
            logger.error(f"SQL generator error: {e}")
            record_counter("text2sql_generation_errors_total", {
                "dialect": state.get("dialect", "unknown")
            })
            state["execution_error"] = str(e)
            return state


# ========== 6. SQL Executor Node ==========

async def sql_executor_node(state: SqlAgentState) -> SqlAgentState:
    """
    SQL 실행 검증.
    
    책임:
    - chosen_sql을 LIMIT 포함하여 실행
    - 성공: execution_result에 row_count 저장
    - 실패: execution_error에 에러 메시지 저장
    
    OTEL:
    - span: "text2sql.executor" (parent: generator)
    - metric: text2sql_execution_latency_ms, row_count
    """
    with start_agent_span(state, "text2sql.executor", {
        "retry_count": state.get("retry_count", 0)
    }) as span:
        start_time = time.time()
        
        try:
            from .tools import execute_sql_safe
            
            sql = state.get("chosen_sql")
            if not sql:
                state["execution_error"] = "No SQL to execute"
                return state
            
            # 안전 모드로 실행 (LIMIT 추가)
            result = await execute_sql_safe(
                connection_id=state["connection_id"],
                sql=sql,
                limit=10,
                dry_run=False
            )
            
            if result.get("success"):
                state["execution_result"] = result.get("rows", [])
                state["execution_error"] = None
                
                row_count = result.get("row_count", 0)
                
                # Span에 결과 기록
                if span and hasattr(span, 'set_attribute'):
                    span.set_attribute("row_count", row_count)
                    span.set_attribute("success", True)
                
                # 성공 기록
                record_counter("text2sql_requests_success_total", {
                    "dialect": state.get("dialect", "unknown")
                })
                record_histogram("text2sql_execution_row_count", row_count, {
                    "dialect": state.get("dialect", "unknown")
                })
                
                logger.info(f"SQL executed successfully: {row_count} rows")
            else:
                state["execution_error"] = result.get("error", "Unknown execution error")
                state["execution_result"] = None
                
                # Span에 에러 기록
                if span and hasattr(span, 'set_attribute'):
                    span.set_attribute("success", False)
                    span.set_attribute("error", state["execution_error"][:200])
                
                record_counter("text2sql_execution_errors_total", {
                    "dialect": state.get("dialect", "unknown"),
                    "error_type": "sql_error"
                })
                
                logger.warning(f"SQL execution failed: {state['execution_error']}")
            
            # Latency 기록
            latency_ms = (time.time() - start_time) * 1000
            record_histogram("text2sql_execution_latency_ms", latency_ms, {
                "dialect": state.get("dialect", "unknown"),
                "success": str(result.get("success", False)).lower()
            })
            
            return state
            
        except Exception as e:
            logger.error(f"SQL executor error: {e}")
            state["execution_error"] = str(e)
            record_counter("text2sql_execution_errors_total", {
                "dialect": state.get("dialect", "unknown"),
                "error_type": "exception"
            })
            return state


# ========== 7. SQL Repair Node ==========

async def sql_repair_node(state: SqlAgentState) -> SqlAgentState:
    """
    에러 기반 SQL 수정.
    
    책임:
    - execution_error가 있을 때만 호출
    - 에러 메시지를 바탕으로 SQL 수정
    - retry_count 증가
    
    OTEL:
    - span: "text2sql.repair" (parent: executor)
    - metric: text2sql_retries_total, repair_latency_ms
    """
    with start_agent_span(state, "text2sql.repair", {
        "retry_count": state.get("retry_count", 0),
        "error_type": state.get("execution_error", "")[:50] if state.get("execution_error") else None
    }):
        start_time = time.time()
        
        try:
            from app.services.litellm_service import litellm_service
            
            model = os.getenv("TEXT2SQL_MODEL_PRIMARY", "qwen-235b")
            
            system_prompt, user_prompt = build_repair_prompt(
                question=state["question"],
                dialect=state.get("dialect", "generic"),
                dialect_rules=state.get("dialect_rules", ""),
                schema_summary=state.get("schema_summary", ""),
                previous_sql=state.get("chosen_sql", ""),
                error_message=state.get("execution_error", "")
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # LLM 호출 span 생성 (repair 노드의 child)
            with start_llm_call_span(state, "repair", model, messages) as (llm_span, record_llm_result):
                if llm_span and hasattr(llm_span, 'set_attribute'):
                    llm_span.set_attribute("retry_count", state.get("retry_count", 0))
                
                response = await litellm_service.chat_completion_sync(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2000,
                    metadata={
                        "agent_id": "text2sql",
                        "node": "repair",
                        "retry_count": state.get("retry_count", 0),
                        "trace_id": state.get("trace_id")
                    }
                )
                # LLM 응답 정보를 span에 기록
                record_llm_result(response)
            
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 토큰 사용량 누적
            usage = response.get("usage", {})
            state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
            state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
            state["total_tokens"] = state.get("total_tokens", 0) + usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            
            # 수정된 SQL 추출
            new_sql = _extract_sql(content)
            
            if new_sql:
                # 후보에 추가
                if state.get("candidate_sql") is None:
                    state["candidate_sql"] = []
                state["candidate_sql"].append(new_sql)
                state["chosen_sql"] = new_sql
                state["execution_error"] = None  # 에러 초기화
            
            # retry_count 증가
            state["retry_count"] = state.get("retry_count", 0) + 1
            
            # Counter 기록
            record_counter("text2sql_retries_total", {
                "dialect": state.get("dialect", "unknown"),
                "retry_count": str(state["retry_count"])
            })
            
            # Latency 기록
            latency_ms = (time.time() - start_time) * 1000
            record_histogram("text2sql_repair_latency_ms", latency_ms, {
                "dialect": state.get("dialect", "unknown")
            })
            record_histogram("text2sql_repair_tokens_prompt", usage.get("prompt_tokens", 0), {})
            record_histogram("text2sql_repair_tokens_completion", usage.get("completion_tokens", 0), {})
            
            logger.info(f"SQL repaired (retry {state['retry_count']}, tokens: +{usage.get('total_tokens', 0)})")
            
            return state
            
        except Exception as e:
            logger.error(f"SQL repair error: {e}")
            state["retry_count"] = state.get("retry_count", 0) + 1
            return state


# ========== 8. Answer Formatter Node ==========

async def answer_formatter_node(state: SqlAgentState) -> SqlAgentState:
    """
    최종 응답 생성.
    
    책임:
    - chosen_sql과 execution_result로 자연어 요약 생성
    - 그래프의 최종 output 구성
    
    OTEL:
    - span: "text2sql.answer_formatter" (parent: executor)
    - metric: text2sql_total_latency_ms, answer_built_total
    """
    with start_agent_span(state, "text2sql.answer_formatter", {
        "has_result": bool(state.get("execution_result"))
    }):
        try:
            from app.services.litellm_service import litellm_service
            
            # 에러가 있으면 에러 응답
            if state.get("execution_error"):
                state["answer_summary"] = f"SQL 생성/실행 중 오류가 발생했습니다: {state['execution_error']}"
                return state
            
            model = os.getenv("TEXT2SQL_MODEL_PRIMARY", "qwen-235b")
            
            system_prompt, user_prompt = build_answer_prompt(
                question=state["question"],
                sql=state.get("chosen_sql", ""),
                result=state.get("execution_result"),
                dialect=state.get("dialect", "generic")
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # LLM 호출 span 생성 (answer_formatter 노드의 child)
            with start_llm_call_span(state, "answer", model, messages) as (llm_span, record_llm_result):
                response = await litellm_service.chat_completion_sync(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=500,
                    metadata={
                        "agent_id": "text2sql",
                        "node": "answer_formatter",
                        "trace_id": state.get("trace_id")
                    }
                )
                # LLM 응답 정보를 span에 기록
                record_llm_result(response)
            
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            state["answer_summary"] = content.strip()
            
            # 토큰 사용량 누적
            usage = response.get("usage", {})
            state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
            state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
            state["total_tokens"] = state.get("total_tokens", 0) + usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            
            # Total latency 기록
            if state.get("start_time"):
                total_latency_ms = (time.time() - state["start_time"]) * 1000
                record_histogram("text2sql_total_latency_ms", total_latency_ms, {
                    "dialect": state.get("dialect", "unknown"),
                    "success": "true"
                })
            
            # 토큰 histogram 기록
            record_histogram("text2sql_llm_tokens_total", state.get("total_tokens", 0), {
                "dialect": state.get("dialect", "unknown")
            })
            
            record_counter("text2sql_answer_built_total", {
                "dialect": state.get("dialect", "unknown")
            })
            
            logger.info(f"Answer formatted (total tokens: {state.get('total_tokens', 0)})")
            
            return state
            
        except Exception as e:
            logger.error(f"Answer formatter error: {e}")
            state["answer_summary"] = f"응답 생성 중 오류: {e}"
            return state


# ========== 9. Human Review Node ==========

async def human_review_node(state: SqlAgentState) -> SqlAgentState:
    """
    Human-in-the-loop 처리.
    
    책임:
    - needs_human_review == True일 때 진입
    - 상위 레이어에서 처리할 수 있도록 상태만 설정
    
    OTEL:
    - span: "text2sql.human_review" (parent: executor or repair)
    - metric: text2sql_human_review_total
    """
    with start_agent_span(state, "text2sql.human_review", {
        "reason": state.get("human_review_reason", "unknown")
    }):
        state["needs_human_review"] = True
        
        if not state.get("human_review_reason"):
            if state.get("retry_count", 0) >= state.get("max_retries", 2):
                state["human_review_reason"] = "max_retries_exceeded"
            else:
                state["human_review_reason"] = "unknown"
        
        # 에러 응답 설정
        if not state.get("answer_summary"):
            state["answer_summary"] = (
                f"자동 처리가 어려워 사람의 검토가 필요합니다. "
                f"(사유: {state['human_review_reason']})"
            )
        
        record_counter("text2sql_human_review_total", {
            "reason": state.get("human_review_reason", "unknown"),
            "dialect": state.get("dialect", "unknown")
        })
        
        logger.warning(f"Human review required: {state['human_review_reason']}")
        
        return state


# ========== Helper Functions ==========

def _extract_json(content: str) -> Optional[Dict[str, Any]]:
    """LLM 응답에서 JSON 추출."""
    import re
    
    # ```json ... ``` 블록 추출
    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # { ... } 직접 추출
    json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None


def _extract_sql(content: str) -> Optional[str]:
    """LLM 응답에서 SQL 추출."""
    import re
    
    # <sql> 태그 추출
    sql_match = re.search(r'<sql>\s*(.*?)\s*</sql>', content, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    
    # ```sql ... ``` 블록 추출
    sql_match = re.search(r'```sql\s*(.*?)\s*```', content, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
    
    # SELECT로 시작하는 문장 추출
    sql_match = re.search(r'(SELECT\s+.*?)(?:;|$)', content, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    
    return None


def _extract_reasoning(content: str) -> Optional[str]:
    """LLM 응답에서 reasoning 추출."""
    import re
    
    # <reasoning> 태그 추출
    reasoning_match = re.search(r'<reasoning>\s*(.*?)\s*</reasoning>', content, re.DOTALL | re.IGNORECASE)
    if reasoning_match:
        return reasoning_match.group(1).strip()
    
    return None

