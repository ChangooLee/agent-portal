"""
dart_routes_v3.py
DART v3 분석 서비스 API 라우터 정의 - 메모리 관리 기능 포함
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import json
import time

from models.models import StreamingChatRequest
from app.agents.dart_agent.dart_agent import DartAgent
from utils.common_transformer import generate_streaming_response, create_error_response
from connection.mcp_direct_client import MCPManager
from utils.logger import log_step
from fastapi.responses import StreamingResponse


# =============================================================================
# 📋 DART v3 특화 모델
# =============================================================================



def create_dart_v3_router(dart_agent: DartAgent, mcp_manager: MCPManager) -> APIRouter:
    """DART v3 분석 서비스 API 라우터 생성 - 메모리 관리 기능 포함"""
    router = APIRouter(prefix="/dart_v3", tags=["DART Analysis v3"])

    @router.post("/chat/stream")
    async def dart_v3_chat_stream(request: StreamingChatRequest):
        """DART v3 분석 스트리밍 채팅 엔드포인트 - 기본 스트리밍"""
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
                    # 에이전트 스트림을 SSE 형식으로 변환
                    async for chunk in generate_streaming_response(
                        dart_agent.process_chat_request_stream(request.input_value, thread_id, request.user_email)
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

    @router.post("/chat/stream/memory")
    async def dart_v3_chat_stream_memory(request: StreamingChatRequest):
        """DART v3 분석 스트리밍 채팅 엔드포인트 - 메모리 관리 기능 포함"""
        log_step("DART v3 메모리 스트리밍 채팅 요청", "START", f"메시지: {request.input_value[:50]}...")
        
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
                    log_step("DART v3 메모리 스트리밍", "ERROR", f"스트림 생성 중 오류: {e}")
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
            log_step("DART v3 메모리 스트리밍 채팅 요청", "FAIL", f"오류: {e}")
            raise HTTPException(status_code=500, detail=f"DART v3 메모리 스트리밍 처리 중 오류: {e}")

    @router.get("/health")
    async def dart_v3_health_check() -> Dict[str, Any]:
        """DART v3 서비스 상태 확인"""
        log_step("DART v3 헬스체크", "START")
        try:
            agent_status = "initialized" if dart_agent else "not_initialized"
            mcp_status = "connected" if mcp_manager else "not_connected"
            health_data = {
                "service": "dart_analysis_v3",
                "status": "healthy" if dart_agent and mcp_manager else "unhealthy",
                "agent_status": agent_status,
                "mcp_status": mcp_status,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "version": "4.1.0",
                "features": {
                    "memory_management": True,
                    "streaming": True,
                    "state_graph": True
                }
            }
            log_step(
                "DART v3 헬스체크",
                "SUCCESS",
                f"에이전트: {agent_status}, MCP: {mcp_status}",
            )
            return health_data
        except Exception as e:
            log_step("DART v3 헬스체크", "FAIL", f"오류: {e}")
            return {
                "service": "dart_analysis_v3",
                "status": "error",
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

        @router.get("/memory/user/{user_email}")
        async def get_user_memory(user_email: str):
            """사용자 장기 메모리 조회"""
            try:
                if not dart_agent or not hasattr(dart_agent, 'memory_manager') or not dart_agent.memory_manager:
                    raise HTTPException(status_code=503, detail="메모리 매니저가 초기화되지 않았습니다")
                
                # 사용자 메모리 조회
                user_context = await dart_agent.memory_manager.get_user_context(user_email)
                analysis_patterns = await dart_agent.memory_manager.search_analysis_patterns(user_email)
                
                return {
                    "user_email": user_email,
                    "user_context": user_context,
                    "analysis_patterns": analysis_patterns,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                
            except Exception as e:
                log_step("사용자 메모리 조회", "ERROR", f"오류: {e}")
                raise HTTPException(status_code=500, detail=f"사용자 메모리 조회 중 오류: {e}")

        @router.delete("/memory/thread/{thread_id}")
        async def delete_thread_memory(thread_id: str):
            """대화 메모리 삭제"""
            try:
                if not dart_agent or not hasattr(dart_agent, 'memory_manager') or not dart_agent.memory_manager:
                    raise HTTPException(status_code=503, detail="메모리 매니저가 초기화되지 않았습니다")
                
                # 세션 메모리 삭제
                await dart_agent.memory_manager.clear_session_memory(thread_id)
                
                return {
                    "thread_id": thread_id,
                    "status": "deleted",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                
            except Exception as e:
                log_step("대화 메모리 삭제", "ERROR", f"오류: {e}")
                raise HTTPException(status_code=500, detail=f"대화 메모리 삭제 중 오류: {e}")

        @router.get("/memory/thread/{thread_id}")
        async def get_thread_memory(thread_id: str):
            """대화 메모리 조회"""
            try:
                if not dart_agent or not hasattr(dart_agent, 'memory_manager') or not dart_agent.memory_manager:
                    raise HTTPException(status_code=503, detail="메모리 매니저가 초기화되지 않았습니다")
                
                # 대화 메시지 조회
                messages = dart_agent.memory_manager.get_messages(thread_id)
                session_data = await dart_agent.memory_manager.get_session_data(thread_id)
                
                return {
                    "thread_id": thread_id,
                    "message_count": len(messages),
                    "messages": [{"role": type(msg).__name__, "content": str(msg.content)[:200] + "..." if len(str(msg.content)) > 200 else str(msg.content)} for msg in messages[-10:]],  # 최근 10개만
                    "session_data": session_data,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                
            except Exception as e:
                log_step("대화 메모리 조회", "ERROR", f"오류: {e}")
                raise HTTPException(status_code=500, detail=f"대화 메모리 조회 중 오류: {e}")

        return router
