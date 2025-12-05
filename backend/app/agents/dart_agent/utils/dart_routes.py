"""
dart_routes.py
DART 분석 서비스 API 라우터 정의
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import json
import time

from models.models import StreamingChatRequest
from agent.dart_agent.dart_agent import DartAgent
from utils.common_transformer import generate_streaming_response, create_error_response
from connection.mcp_direct_client import MCPManager
from utils.logger import log_step
from fastapi.responses import StreamingResponse


# =============================================================================
# 📋 DART 특화 모델
# =============================================================================



def create_dart_router(dart_agent: DartAgent, mcp_manager: MCPManager) -> APIRouter:
    """DART 분석 서비스 API 라우터 생성"""
    router = APIRouter(prefix="/dart_v2", tags=["DART Analysis"])

    @router.post("/chat/stream")
    async def dart_chat_stream(request: StreamingChatRequest):
        """DART 분석 스트리밍 채팅 엔드포인트 - SSE 최적화"""
        log_step("DART 스트리밍 채팅 요청", "START", f"메시지: {request.input_value[:50]}...")
        
        try:
            from fastapi.responses import StreamingResponse
            import json
            
            if not dart_agent:
                raise HTTPException(status_code=503, detail="DART 에이전트가 초기화되지 않았습니다")
            
            # thread_id 처리: chat_id가 있으면 사용, 없으면 기존 방식
            if request.chat_id:
                thread_id = str(request.chat_id)
            else:
                thread_id = None

            async def generate_stream():
                try:
                    # 에이전트 스트림을 SSE 형식으로 변환
                    async for chunk in generate_streaming_response(
                        dart_agent.process_chat_request_stream(request.input_value, thread_id, request.user_email)
                    ):
                        # SSE 형식으로 데이터 전송
                        yield f"data: {chunk}\n\n"
                            
                except Exception as e:
                    log_step("DART 스트리밍", "ERROR", f"스트림 생성 중 오류: {e}")
                    error_chunk = create_error_response(str(e))
                    yield f"data: {error_chunk}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream",
                    "X-Accel-Buffering": "no",
                    "Content-Encoding": "identity",  # 추가: 압축 방지
                }
            )
            
        except Exception as e:
            log_step("DART 스트리밍 채팅 요청", "FAIL", f"오류: {e}")
            raise HTTPException(status_code=500, detail=f"DART 스트리밍 처리 중 오류: {e}")

    @router.get("/health")
    async def dart_health_check() -> Dict[str, Any]:
        """DART 서비스 상태 확인"""
        log_step("DART 헬스체크", "START")
        try:
            agent_status = "initialized" if dart_agent else "not_initialized"
            mcp_status = "connected" if mcp_manager else "not_connected"
            health_data = {
                "service": "dart_analysis",
                "status": "healthy" if dart_agent and mcp_manager else "unhealthy",
                "agent_status": agent_status,
                "mcp_status": mcp_status,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "version": "4.0.0",
            }
            log_step(
                "DART 헬스체크",
                "SUCCESS",
                f"에이전트: {agent_status}, MCP: {mcp_status}",
            )
            return health_data
        except Exception as e:
            log_step("DART 헬스체크", "FAIL", f"오류: {e}")
            return {
                "service": "dart_analysis",
                "status": "error",
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

    # =============================================================================
    # 🧠 DART v3 - 메모리 관리 기능 포함
    # =============================================================================
    
    @router.post("/chat/stream/memory")
    async def dart_v3_chat_stream(request: StreamingChatRequest):
        """DART v3 분석 스트리밍 채팅 엔드포인트 - 메모리 관리 기능 포함"""
        log_step("DART v3 스트리밍 채팅 요청", "START", f"메시지: {request.input_value[:50]}...")
        
        try:
            from fastapi.responses import StreamingResponse
            import json
            
            if not dart_agent:
                raise HTTPException(status_code=503, detail="DART 에이전트가 초기화되지 않았습니다")
            
            # thread_id 처리: chat_id가 있으면 사용, 없으면 기존 방식
            if request.chat_id:
                thread_id = str(request.chat_id)
            else:
                thread_id = None

            async def generate_stream():
                try:
                    # 메모리 네임스페이스 초기화
                    if hasattr(dart_agent, '_ensure_ns'):
                        await dart_agent._ensure_ns(thread_id=thread_id, checkpoint_ns="mem_main")
                    
                    # 메모리 관리 기능이 포함된 에이전트 스트림을 SSE 형식으로 변환
                    async for chunk in generate_streaming_response(
                        dart_agent.process_chat_request_stream_with_memory(request.input_value, thread_id, request.user_email)
                    ):
                        # SSE 형식으로 데이터 전송
                        yield f"data: {chunk}\n\n"
                            
                except Exception as e:
                    log_step("DART v3 스트리밍", "ERROR", f"스트림 생성 중 오류: {e}")
                    error_chunk = create_error_response(str(e))
                    yield f"data: {error_chunk}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream",
                    "X-Accel-Buffering": "no",
                    "Content-Encoding": "identity",  # 추가: 압축 방지
                }
            )
            
        except Exception as e:
            log_step("DART v3 스트리밍 채팅 요청", "FAIL", f"오류: {e}")
            raise HTTPException(status_code=500, detail=f"DART v3 스트리밍 처리 중 오류: {e}")

    return router
