"""
DART Agent API Routes

기업공시분석 에이전트 API 엔드포인트.
SSE 스트리밍 지원.
"""

import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.agent_registry_service import agent_registry, AgentType
from app.services.agent_trace_adapter import agent_trace_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dart", tags=["DART Analysis"])


# =============================================================================
# Request/Response Models
# =============================================================================

class DartChatRequest(BaseModel):
    """DART 채팅 요청"""
    question: str
    session_id: Optional[str] = None
    model: Optional[str] = "qwen-235b"


class DartChatResponse(BaseModel):
    """DART 채팅 응답"""
    success: bool
    answer: str
    intent: Optional[Dict[str, Any]] = None
    tool_calls: Optional[list] = None
    tokens: Optional[Dict[str, int]] = None
    latency_ms: Optional[float] = None


class StreamEvent(BaseModel):
    """SSE 스트림 이벤트"""
    event: str
    data: Optional[Dict[str, Any]] = None


def _format_sse(event_data: Dict[str, Any]) -> str:
    """SSE 형식으로 데이터 포맷"""
    json_data = json.dumps(event_data, ensure_ascii=False)
    return f"data: {json_data}\n\n"


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health", summary="DART Agent Health Check")
async def health_check():
    """DART 에이전트 헬스 체크"""
    from app.agents.dart_agent.mcp_client import MCPHTTPClient
    
    # MCP 연결 테스트
    try:
        client = MCPHTTPClient("http://121.141.60.219:8089/mcp", timeout=10.0)
        connected = await client.connect()
        tool_count = client.tool_count if connected else 0
        await client.disconnect()
        
        return {
            "status": "ok" if connected else "degraded",
            "service": "dart-agent",
            "mcp_connected": connected,
            "mcp_tools": tool_count
        }
    except Exception as e:
        logger.error(f"DART health check failed: {e}")
        return {
            "status": "error",
            "service": "dart-agent",
            "mcp_connected": False,
            "error": str(e)
        }


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.post("/chat", response_model=DartChatResponse, summary="DART Analysis Chat")
async def chat(request_data: DartChatRequest):
    """
    DART 분석 채팅 (동기 응답).
    
    사용자 질문을 분석하고 관련 공시 정보를 조회하여 응답합니다.
    """
    from app.agents.dart_agent.agent import get_dart_agent
    
    logger.info(f"DART chat request: {request_data.question[:50]}...")
    
    trace_id = str(uuid.uuid4())
    session_id = request_data.session_id or trace_id
    
    # 에이전트 레지스트리 등록
    try:
        agent_info = await agent_registry.register_or_get(
            name="dart-agent",
            agent_type=AgentType.DART,
            project_id="default-project",
            description="DART 기업공시분석 에이전트"
        )
    except Exception as e:
        logger.warning(f"Agent registration failed: {e}")
        agent_info = None
    
    # 트레이스 시작
    if agent_info:
        try:
            await agent_trace_adapter.start_trace(
                agent_id=agent_info.get("id", "dart"),
                agent_name="dart-agent",
                agent_type="dart",
                project_id="default-project",
                inputs={"question": request_data.question}
            )
        except Exception as e:
            logger.warning(f"Trace start failed: {e}")
    
    # MCP 연결 확인
    from app.agents.dart_agent.mcp_client import get_opendart_mcp_client
    mcp_client = await get_opendart_mcp_client()
    mcp_connected = await mcp_client.connect()
    
    if not mcp_connected:
        raise HTTPException(
            status_code=503,
            detail="MCP 서버에 연결할 수 없습니다. OpenDART MCP 서버가 오프라인 상태입니다."
        )
    
    try:
        agent = get_dart_agent(model=request_data.model or "qwen-235b")
        result = await agent.analyze(
            question=request_data.question,
            session_id=session_id
        )
        
        # 트레이스 종료
        if agent_info:
            try:
                await agent_trace_adapter.end_trace(
                    trace_id=trace_id,
                    outputs={
                        "answer": result.get("answer", "")[:500],
                        "success": True
                    }
                )
            except Exception as e:
                logger.warning(f"Trace end failed: {e}")
        
        return DartChatResponse(
            success=True,
            answer=result.get("answer", ""),
            intent=result.get("intent"),
            tool_calls=result.get("tool_calls"),
            tokens=result.get("tokens"),
            latency_ms=result.get("total_latency_ms")
        )
        
    except Exception as e:
        logger.error(f"DART chat error: {e}")
        
        if agent_info:
            try:
                await agent_trace_adapter.end_trace(
                    trace_id=trace_id,
                    outputs={"success": False},
                    error=str(e)
                )
            except Exception:
                pass
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream", summary="DART Analysis Chat (Streaming)")
async def chat_stream(request_data: DartChatRequest):
    """
    DART 분석 채팅 (SSE 스트리밍).
    
    분석 진행 상황을 실시간으로 스트리밍합니다.
    """
    from app.agents.dart_agent.agent import get_dart_agent
    
    logger.info(f"DART stream request: {request_data.question[:50]}...")
    
    trace_id = str(uuid.uuid4())
    session_id = request_data.session_id or trace_id
    
    async def event_generator():
        # 에이전트 레지스트리 등록
        agent_info = None
        try:
            agent_info = await agent_registry.register_or_get(
                name="dart-agent",
                agent_type=AgentType.DART,
                project_id="default-project",
                description="DART 기업공시분석 에이전트"
            )
        except Exception as e:
            logger.warning(f"Agent registration failed: {e}")
        
        # 트레이스 시작
        if agent_info:
            try:
                await agent_trace_adapter.start_trace(
                    agent_id=agent_info.get("id", "dart"),
                    agent_name="dart-agent",
                    agent_type="dart",
                    project_id="default-project",
                    inputs={"question": request_data.question}
                )
            except Exception as e:
                logger.warning(f"Trace start failed: {e}")
        
        try:
            # 시작 이벤트
            yield _format_sse({
                "event": "start",
                "trace_id": trace_id,
                "question": request_data.question
            })
            
            # MCP 연결 확인
            from app.agents.dart_agent.mcp_client import get_opendart_mcp_client
            mcp_client = await get_opendart_mcp_client()
            
            yield _format_sse({
                "event": "analyzing",
                "message": "MCP 서버 연결 확인 중..."
            })
            
            mcp_connected = await mcp_client.connect()
            if not mcp_connected:
                yield _format_sse({
                    "event": "error",
                    "error": "MCP 서버에 연결할 수 없습니다. OpenDART MCP 서버가 오프라인 상태입니다. 서버 관리자에게 문의하세요."
                })
                yield _format_sse({
                    "event": "complete",
                    "success": False
                })
                return
            
            yield _format_sse({
                "event": "analyzing",
                "message": "MCP 연결 성공, 분석 시작..."
            })
            
            agent = get_dart_agent(model=request_data.model or "qwen-235b")
            final_answer = ""
            
            async for event in agent.analyze_stream(
                question=request_data.question,
                session_id=session_id
            ):
                # 이벤트 전달
                yield _format_sse(event)
                
                # 최종 답변 저장
                if event.get("event") == "answer":
                    final_answer = event.get("content", "")
                elif event.get("event") == "done":
                    final_answer = event.get("answer", final_answer)
            
            # 트레이스 종료
            if agent_info:
                try:
                    await agent_trace_adapter.end_trace(
                        trace_id=trace_id,
                        outputs={
                            "answer": final_answer[:500],
                            "success": True
                        }
                    )
                except Exception as e:
                    logger.warning(f"Trace end failed: {e}")
                    
        except Exception as e:
            logger.error(f"DART stream error: {e}")
            yield _format_sse({
                "event": "error",
                "error": str(e)
            })
            
            if agent_info:
                try:
                    await agent_trace_adapter.end_trace(
                        trace_id=trace_id,
                        outputs={"success": False},
                        error=str(e)
                    )
                except Exception:
                    pass
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


# =============================================================================
# Tool Information
# =============================================================================

@router.get("/tools", summary="List Available MCP Tools")
async def list_tools():
    """
    사용 가능한 MCP 도구 목록 조회.
    """
    from app.agents.dart_agent.mcp_client import get_opendart_mcp_client
    
    try:
        client = await get_opendart_mcp_client()
        tools = client.get_tools()
        
        return {
            "success": True,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema
                }
                for t in tools
            ],
            "count": len(tools)
        }
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))
