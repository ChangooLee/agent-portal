"""
RealEstate Agent API Routes

부동산 분석 에이전트 API 엔드포인트.
SSE 스트리밍 지원.
"""

import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/realestate", tags=["RealEstate Analysis"])
api_router = APIRouter(prefix="/api/realestate", tags=["RealEstate Analysis"])


# =============================================================================
# Request/Response Models
# =============================================================================

class RealEstateChatRequest(BaseModel):
    """부동산 분석 채팅 요청"""
    question: str
    session_id: Optional[str] = None
    model: Optional[str] = "claude-opus-4.5"


class RealEstateChatResponse(BaseModel):
    """부동산 분석 채팅 응답"""
    success: bool
    answer: str
    tool_calls: Optional[list] = None
    latency_ms: Optional[float] = None


class HistoryCreateRequest(BaseModel):
    """히스토리 생성 요청"""
    title: str
    messages: list = Field(default_factory=list)
    model_tab: str = "single"
    report: Optional[dict] = None


class HistoryUpdateRequest(BaseModel):
    """히스토리 업데이트 요청"""
    title: Optional[str] = None
    messages: Optional[list] = None
    report: Optional[dict] = None


def _format_sse(event_data: Dict[str, Any]) -> str:
    """SSE 형식으로 데이터 포맷"""
    json_data = json.dumps(event_data, ensure_ascii=False)
    return f"data: {json_data}\n\n"


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health", summary="RealEstate Agent Health Check")
@api_router.get("/health", summary="RealEstate Agent Health Check")
async def health_check():
    """부동산 에이전트 헬스 체크"""
    from app.agents.common.mcp_client_base import create_mcp_client
    
    try:
        client = await create_mcp_client(
            server_name="mcp-kr-realestate",
            service_name="agent-realestate"
        )
        connected = client.is_connected
        tool_count = client.tool_count if connected else 0
        
        return {
            "status": "ok" if connected else "degraded",
            "service": "realestate-agent",
            "mcp_connected": connected,
            "mcp_tools": tool_count
        }
    except Exception as e:
        logger.error(f"RealEstate health check failed: {e}")
        return {
            "status": "error",
            "service": "realestate-agent",
            "mcp_connected": False,
            "error": str(e)
        }


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.post("/chat/single", summary="RealEstate Single Agent Chat (Streaming)")
@api_router.post("/chat/single", summary="RealEstate Single Agent Chat (Streaming)")
async def chat_single_stream(request_data: RealEstateChatRequest):
    """
    부동산 분석 Single Agent 채팅 (SSE 스트리밍).
    
    Single Agent가 MCP 도구를 직접 사용하여 부동산 정보를 분석합니다.
    """
    from app.agents.realestate_agent.single_agent import RealEstateSingleAgent
    
    logger.info(f"RealEstate stream request: {request_data.question[:50]}...")
    
    trace_id = str(uuid.uuid4())
    session_id = request_data.session_id or trace_id
    
    async def event_generator():
        try:
            # Single Agent 인스턴스 생성
            agent = RealEstateSingleAgent(model=request_data.model or "claude-opus-4.5")
            
            # 스트리밍 분석 실행
            async for event in agent.analyze_stream(
                question=request_data.question,
                session_id=session_id
            ):
                yield _format_sse(event)
            
            # 완료 이벤트
            yield _format_sse({"event": "done"})
            
        except Exception as e:
            logger.error(f"RealEstate stream error: {e}", exc_info=True)
            yield _format_sse({
                "event": "error",
                "message": f"분석 중 오류가 발생했습니다: {str(e)}"
            })
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.post("/chat", response_model=RealEstateChatResponse, summary="RealEstate Analysis Chat")
@api_router.post("/chat", response_model=RealEstateChatResponse, summary="RealEstate Analysis Chat")
async def chat(request_data: RealEstateChatRequest):
    """
    부동산 분석 채팅 (동기 응답).
    
    Single Agent 스트림 결과를 누적하여 동기 응답으로 반환합니다.
    """
    from app.agents.realestate_agent.single_agent import RealEstateSingleAgent
    import time
    
    logger.info(f"RealEstate chat request: {request_data.question[:50]}...")
    
    session_id = request_data.session_id or str(uuid.uuid4())
    start_time = time.time()
    
    try:
        agent = RealEstateSingleAgent(model=request_data.model or "claude-opus-4.5")
        
        # 스트림 결과 누적
        answer_parts = []
        tool_calls = []
        
        async for event in agent.analyze_stream(
            question=request_data.question,
            session_id=session_id
        ):
            event_type = event.get("event", "")
            
            if event_type == "content":
                content = event.get("content", "")
                if content:
                    answer_parts.append(content)
            elif event_type == "tool_result":
                tool_calls.append({
                    "tool": event.get("tool"),
                    "display_name": event.get("display_name"),
                    "success": event.get("success")
                })
        
        elapsed_time = (time.time() - start_time) * 1000
        
        return RealEstateChatResponse(
            success=True,
            answer="".join(answer_parts),
            tool_calls=tool_calls if tool_calls else None,
            latency_ms=elapsed_time
        )
        
    except Exception as e:
        logger.error(f"RealEstate chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Model List
# =============================================================================

@router.get("/models", summary="Available Models")
@api_router.get("/models", summary="Available Models")
async def get_models():
    """사용 가능한 모델 목록"""
    return {
        "models": [
            {"id": "claude-opus-4.5", "name": "Claude Opus 4.5", "default": True},
            {"id": "qwen-235b", "name": "Qwen 2.5 235B"},
            {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash"},
        ]
    }


# =============================================================================
# History API
# =============================================================================

from app.services.agent_history_service import realestate_history_service


@router.get("/history", summary="List Chat History")
@api_router.get("/history", summary="List Chat History")
async def list_history(
    limit: int = 50,
    offset: int = 0,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """사용자의 채팅 히스토리 목록 조회"""
    user_id = x_user_id or "anonymous"
    
    try:
        histories = await realestate_history_service.list_history(user_id, limit, offset)
        return {"success": True, "histories": histories, "count": len(histories)}
    except Exception as e:
        logger.error(f"Failed to list history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/search", summary="Search Chat History")
@api_router.get("/history/search", summary="Search Chat History")
async def search_history(
    query: str,
    limit: int = 20,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """채팅 히스토리 검색"""
    user_id = x_user_id or "anonymous"
    
    try:
        histories = await realestate_history_service.search_history(user_id, query, limit)
        return {"success": True, "histories": histories, "count": len(histories)}
    except Exception as e:
        logger.error(f"Failed to search history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{history_id}", summary="Get Chat History")
@api_router.get("/history/{history_id}", summary="Get Chat History")
async def get_history(
    history_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """특정 채팅 히스토리 조회"""
    user_id = x_user_id or "anonymous"
    
    try:
        history = await realestate_history_service.get_history(history_id, user_id)
        if not history:
            raise HTTPException(status_code=404, detail="History not found")
        return {"success": True, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history", summary="Create Chat History")
@api_router.post("/history", summary="Create Chat History")
async def create_history(
    request: HistoryCreateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """새 채팅 히스토리 생성"""
    user_id = x_user_id or "anonymous"
    
    try:
        history = await realestate_history_service.create_history(
            user_id=user_id,
            title=request.title,
            messages=request.messages,
            model_tab=request.model_tab,
            report=request.report
        )
        return {"success": True, "history": history}
    except Exception as e:
        logger.error(f"Failed to create history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/history/{history_id}", summary="Update Chat History")
@api_router.put("/history/{history_id}", summary="Update Chat History")
async def update_history(
    history_id: str,
    request: HistoryUpdateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """채팅 히스토리 업데이트"""
    user_id = x_user_id or "anonymous"
    
    try:
        success = await realestate_history_service.update_history(
            history_id=history_id,
            user_id=user_id,
            title=request.title,
            messages=request.messages,
            report=request.report
        )
        if not success:
            raise HTTPException(status_code=404, detail="History not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{history_id}", summary="Delete Chat History")
@api_router.delete("/history/{history_id}", summary="Delete Chat History")
async def delete_history(
    history_id: str,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
):
    """채팅 히스토리 삭제"""
    user_id = x_user_id or "anonymous"
    
    try:
        success = await realestate_history_service.delete_history(history_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="History not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

