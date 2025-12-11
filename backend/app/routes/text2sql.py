"""
Text-to-SQL API Router

참조: 플랜 Phase 7

POST /api/text2sql/generate - SQL 생성
POST /api/text2sql/generate/stream - SSE 스트리밍 (노드별 진행상황)
"""

import json
import logging
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Text-to-SQL 라우터: /text2sql/*와 /api/text2sql/* 모두 처리
# Single Port Architecture에서 Vite 프록시가 /api/text2sql/*를 /text2sql/*로 리라이트하지만,
# 직접 /api/text2sql/*로 접근하는 경우도 처리하기 위해 두 개의 라우터를 생성
router = APIRouter(prefix="/text2sql", tags=["text2sql"])
api_router = APIRouter(prefix="/api/text2sql", tags=["text2sql"])


# ========== Request/Response Models ==========

class GenerateRequest(BaseModel):
    """SQL 생성 요청"""
    connection_id: str
    question: str
    max_retries: Optional[int] = 2


class GenerateResponse(BaseModel):
    """SQL 생성 응답"""
    success: bool
    sql: Optional[str] = None
    reasoning: Optional[str] = None
    answer_summary: Optional[str] = None
    dialect: Optional[str] = None
    execution_result: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
    needs_human_review: bool = False


class StreamEvent(BaseModel):
    """SSE 이벤트"""
    event: str  # node_start, node_end, sql_generated, error, done
    node: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# ========== Endpoints ==========

@router.post("/generate", response_model=GenerateResponse)
@api_router.post("/generate", response_model=GenerateResponse)
async def generate_sql(request: GenerateRequest):
    """
    자연어 질문으로 SQL 생성.
    
    Args:
        request: 연결 ID와 질문
        
    Returns:
        생성된 SQL과 실행 결과
    """
    try:
        from app.agents.text2sql.graph import text2sql_agent
        from app.services.agent_registry_service import agent_registry
        from app.services.agent_trace_adapter import agent_trace_adapter
        
        trace_id = str(uuid.uuid4())
        
        # 에이전트 레지스트리에 등록
        try:
            agent_info = await agent_registry.register_or_get(
                name="text2sql-agent",
                agent_type="text2sql",
                project_id="default-project",
                description="LangGraph 기반 Text-to-SQL 에이전트"
            )
        except Exception as e:
            logger.warning(f"Agent registration failed: {e}")
            agent_info = None
        
        # 트레이스 시작
        if agent_info:
            try:
                await agent_trace_adapter.start_trace(
                    agent_id=agent_info.get("id", "text2sql"),
                    agent_name="text2sql-agent",
                    agent_type="text2sql",
                    project_id="default-project",
                    inputs={
                        "question": request.question,
                        "connection_id": request.connection_id
                    }
                )
            except Exception as e:
                logger.warning(f"Trace start failed: {e}")
        
        # Agent 실행 (agent_id와 agent_name 전달)
        agent_id = agent_info.get("id", "text2sql-agent") if agent_info else "text2sql-agent"
        agent_name = agent_info.get("name", "Text-to-SQL Agent") if agent_info else "Text-to-SQL Agent"
        
        final_state = await text2sql_agent.run(
            question=request.question,
            connection_id=request.connection_id,
            trace_id=trace_id,
            agent_id=agent_id,
            agent_name=agent_name
        )
        
        # 트레이스 종료
        if agent_info:
            try:
                await agent_trace_adapter.end_trace(
                    trace_id=trace_id,
                    outputs={
                        "sql": final_state.get("chosen_sql"),
                        "success": not final_state.get("execution_error")
                    },
                    error=final_state.get("execution_error")
                )
            except Exception as e:
                logger.warning(f"Trace end failed: {e}")
        
        # 응답 구성
        if final_state.get("execution_error") and final_state.get("needs_human_review"):
            return GenerateResponse(
                success=False,
                error=final_state.get("execution_error"),
                sql=final_state.get("chosen_sql"),
                reasoning=final_state.get("sql_reasoning"),
                dialect=final_state.get("dialect"),
                trace_id=trace_id,
                needs_human_review=True
            )
        
        return GenerateResponse(
            success=True,
            sql=final_state.get("chosen_sql"),
            reasoning=final_state.get("sql_reasoning"),
            answer_summary=final_state.get("answer_summary"),
            dialect=final_state.get("dialect"),
            execution_result=final_state.get("execution_result"),
            trace_id=trace_id,
            needs_human_review=final_state.get("needs_human_review", False)
        )
        
    except Exception as e:
        logger.error(f"Text2SQL generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/stream")
@api_router.post("/generate/stream")
async def generate_sql_stream(request: GenerateRequest):
    """
    자연어 질문으로 SQL 생성 (SSE 스트리밍).
    
    각 노드 실행 후 중간 상태를 이벤트로 전송.
    
    Args:
        request: 연결 ID와 질문
        
    Returns:
        SSE 스트림
    """
    async def event_generator():
        try:
            from app.agents.text2sql.graph import text2sql_agent
            
            trace_id = str(uuid.uuid4())
            
            # 시작 이벤트
            yield _format_sse(StreamEvent(
                event="start",
                data={"trace_id": trace_id, "question": request.question}
            ))
            
            # Agent 실행 (스트리밍)
            final_state = None
            
            async for node_name, state in text2sql_agent.run_stream(
                question=request.question,
                connection_id=request.connection_id,
                trace_id=trace_id
            ):
                final_state = state
                
                # 노드 완료 이벤트
                event_data = {
                    "node": node_name,
                    "dialect": state.get("dialect"),
                    "has_sql": bool(state.get("chosen_sql")),
                    "has_error": bool(state.get("execution_error")),
                    "retry_count": state.get("retry_count", 0)
                }
                
                # SQL이 생성되었으면 포함
                if state.get("chosen_sql") and node_name in ["sql_generator", "sql_repair"]:
                    event_data["sql"] = state.get("chosen_sql")
                
                yield _format_sse(StreamEvent(
                    event="node_complete",
                    node=node_name,
                    data=event_data
                ))
            
            # 완료 이벤트
            if final_state:
                yield _format_sse(StreamEvent(
                    event="done",
                    data={
                        "success": not final_state.get("execution_error"),
                        "sql": final_state.get("chosen_sql"),
                        "answer_summary": final_state.get("answer_summary"),
                        "dialect": final_state.get("dialect"),
                        "trace_id": trace_id,
                        "needs_human_review": final_state.get("needs_human_review", False)
                    }
                ))
            
        except Exception as e:
            logger.error(f"Text2SQL stream error: {e}")
            yield _format_sse(StreamEvent(
                event="error",
                data={"error": str(e)}
            ))
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/health")
@api_router.get("/health")
async def health_check():
    """헬스체크"""
    return {"status": "ok", "service": "text2sql"}


def _format_sse(event: StreamEvent) -> str:
    """SSE 포맷으로 변환."""
    data = json.dumps({
        "event": event.event,
        "node": event.node,
        "data": event.data
    }, ensure_ascii=False)
    return f"data: {data}\n\n"

