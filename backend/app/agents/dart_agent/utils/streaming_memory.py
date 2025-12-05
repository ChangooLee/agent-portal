"""
streaming_memory.py
스트리밍 중 메모리 관리를 위한 핸들러
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import log_step, log_performance
from .memory_manager import DartMemoryManager


class StreamingMemoryHandler:
    """스트리밍 중 메모리 관리를 위한 핸들러"""
    
    def __init__(self, memory_manager: DartMemoryManager):
        self.memory_manager = memory_manager
        self.streaming_context: Dict[str, Any] = {}
        self.chunk_stats = {
            "total_chunks": 0,
            "tool_calls": 0,
            "tool_results": 0,
            "agent_responses": 0,
            "errors": 0
        }
    
    async def handle_streaming_chunk(self, chunk: Dict[str, Any], 
                                   agent_type: str, thread_id: str) -> Dict[str, Any]:
        """스트리밍 청크 처리 및 메모리 관리"""
        try:
            self.chunk_stats["total_chunks"] += 1
            
            # 청크 타입별 처리
            chunk_type = chunk.get("type", "unknown")
            
            if chunk_type == "tool_call":
                await self._handle_tool_call_chunk(chunk, agent_type, thread_id)
                self.chunk_stats["tool_calls"] += 1
                
            elif chunk_type == "tool_result":
                await self._handle_tool_result_chunk(chunk, agent_type, thread_id)
                self.chunk_stats["tool_results"] += 1
                
            elif chunk_type == "agent_response":
                await self._handle_agent_response_chunk(chunk, agent_type, thread_id)
                self.chunk_stats["agent_responses"] += 1
                
            elif chunk_type == "error":
                await self._handle_error_chunk(chunk, agent_type, thread_id)
                self.chunk_stats["errors"] += 1
                
            elif chunk_type == "progress":
                await self._handle_progress_chunk(chunk, agent_type, thread_id)
                
            elif chunk_type == "start":
                await self._handle_start_chunk(chunk, agent_type, thread_id)
                
            elif chunk_type == "end":
                await self._handle_end_chunk(chunk, agent_type, thread_id)
            
            # 청크를 스트리밍 컨텍스트에 저장
            self._update_streaming_context(chunk, agent_type, thread_id)
            
            return chunk
            
        except Exception as e:
            log_step("스트리밍 청크 처리", "ERROR", f"청크 처리 실패: {str(e)}")
            return chunk
    
    async def _handle_tool_call_chunk(self, chunk: Dict[str, Any], 
                                    agent_type: str, thread_id: str):
        """도구 호출 청크 처리"""
        try:
            tool_name = chunk.get("tool_name", "unknown")
            content = chunk.get("content", "")
            
            # 도구 호출을 스트리밍 컨텍스트에 저장
            self.streaming_context[f"{agent_type}_tool_call"] = {
                "tool_name": tool_name,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            # 토큰 사용량 추적
            if self.memory_manager:
                await self.memory_manager.update_token_usage(
                    thread_id, agent_type, response_tokens=len(content.split())
                )
            
            log_step("도구 호출 청크 처리", "INFO", f"tool: {tool_name}, agent: {agent_type}")
            
        except Exception as e:
            log_step("도구 호출 청크 처리", "ERROR", f"처리 실패: {str(e)}")
    
    async def _handle_tool_result_chunk(self, chunk: Dict[str, Any], 
                                      agent_type: str, thread_id: str):
        """도구 결과 청크 처리 - Store API 활용"""
        try:
            tool_name = chunk.get("tool_name", "unknown")
            content = chunk.get("content", "")
            
            # 중요한 결과만 메모리에 저장
            if len(content) > 100:  # 100자 이상의 결과만 저장
                await self.memory_manager.save_tool_result(
                    thread_id, agent_type, tool_name, content
                )
                
                # Store API로 실시간 데이터 저장
                if self.memory_manager and self.memory_manager.store:
                    tool_data = {
                        "agent_type": agent_type,
                        "tool_name": tool_name,
                        "result": content,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    namespace = ("session", thread_id)
                    key = f"tool_result_{int(time.time())}"
                    await self.memory_manager.store.aput(namespace, key, tool_data)
            
            # 도구 결과를 스트리밍 컨텍스트에 저장
            self.streaming_context[f"{agent_type}_tool_result"] = {
                "tool_name": tool_name,
                "content": content[:200] + "..." if len(content) > 200 else content,
                "timestamp": datetime.now().isoformat()
            }
            
            # 토큰 사용량 추적
            if self.memory_manager:
                await self.memory_manager.update_token_usage(
                    thread_id, agent_type, response_tokens=len(content.split())
                )
            
            log_step("도구 결과 청크 처리", "INFO", f"tool: {tool_name}, agent: {agent_type}")
            
        except Exception as e:
            log_step("도구 결과 청크 처리", "ERROR", f"처리 실패: {str(e)}")
    
    async def _handle_agent_response_chunk(self, chunk: Dict[str, Any], 
                                         agent_type: str, thread_id: str):
        """에이전트 응답 청크 처리 - Store API 활용"""
        try:
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            
            # 토큰 사용량 추적
            if self.memory_manager:
                await self.memory_manager.update_token_usage(
                    thread_id, agent_type, response_tokens=len(content.split())
                )
                
                # Store API로 분석 결과 저장
                if self.memory_manager.store:
                    analysis_data = {
                        "agent_type": agent_type,
                        "response": content,
                        "metadata": metadata,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    namespace = ("session", thread_id)
                    key = f"analysis_{int(time.time())}"
                    await self.memory_manager.store.aput(namespace, key, analysis_data)
            
            # 에이전트 응답을 스트리밍 컨텍스트에 저장
            self.streaming_context[f"{agent_type}_response"] = {
                "content": content[:500] + "..." if len(content) > 500 else content,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }
            
            log_step("에이전트 응답 청크 처리", "INFO", f"agent: {agent_type}, 길이: {len(content)}")
            
        except Exception as e:
            log_step("에이전트 응답 청크 처리", "ERROR", f"처리 실패: {str(e)}")
    
    async def _handle_error_chunk(self, chunk: Dict[str, Any], 
                                agent_type: str, thread_id: str):
        """에러 청크 처리"""
        try:
            error_content = chunk.get("content", "Unknown error")
            
            # 에러를 스트리밍 컨텍스트에 저장
            self.streaming_context[f"{agent_type}_error"] = {
                "error": error_content,
                "timestamp": datetime.now().isoformat()
            }
            
            # 에러를 메모리에 저장 (디버깅용)
            if self.memory_manager:
                await self.memory_manager.save_context_memory(
                    thread_id, f"{agent_type}_error", {
                        "error": error_content,
                        "agent_type": agent_type,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            log_step("에러 청크 처리", "ERROR", f"agent: {agent_type}, error: {error_content}")
            
        except Exception as e:
            log_step("에러 청크 처리", "ERROR", f"처리 실패: {str(e)}")
    
    async def _handle_progress_chunk(self, chunk: Dict[str, Any], 
                                   agent_type: str, thread_id: str):
        """진행 상황 청크 처리"""
        try:
            content = chunk.get("content", "")
            
            # 진행 상황을 스트리밍 컨텍스트에 저장
            self.streaming_context[f"{agent_type}_progress"] = {
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            log_step("진행 상황 청크 처리", "INFO", f"agent: {agent_type}, progress: {content[:50]}...")
            
        except Exception as e:
            log_step("진행 상황 청크 처리", "ERROR", f"처리 실패: {str(e)}")
    
    async def _handle_start_chunk(self, chunk: Dict[str, Any], 
                                agent_type: str, thread_id: str):
        """시작 청크 처리"""
        try:
            content = chunk.get("content", "")
            
            # 시작 정보를 스트리밍 컨텍스트에 저장
            self.streaming_context[f"{agent_type}_start"] = {
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            log_step("시작 청크 처리", "INFO", f"agent: {agent_type}, start: {content[:50]}...")
            
        except Exception as e:
            log_step("시작 청크 처리", "ERROR", f"처리 실패: {str(e)}")
    
    async def _handle_end_chunk(self, chunk: Dict[str, Any], 
                              agent_type: str, thread_id: str):
        """종료 청크 처리"""
        try:
            content = chunk.get("content", "")
            
            # 종료 정보를 스트리밍 컨텍스트에 저장
            self.streaming_context[f"{agent_type}_end"] = {
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            log_step("종료 청크 처리", "INFO", f"agent: {agent_type}, end: {content[:50]}...")
            
        except Exception as e:
            log_step("종료 청크 처리", "ERROR", f"처리 실패: {str(e)}")
    
    def _update_streaming_context(self, chunk: Dict[str, Any], 
                                agent_type: str, thread_id: str):
        """스트리밍 컨텍스트 업데이트"""
        try:
            # 스트리밍 컨텍스트에 청크 추가
            if "streaming_chunks" not in self.streaming_context:
                self.streaming_context["streaming_chunks"] = []
            
            self.streaming_context["streaming_chunks"].append({
                "agent_type": agent_type,
                "thread_id": thread_id,
                "chunk": chunk,
                "timestamp": datetime.now().isoformat()
            })
            
            # 최대 100개 청크만 유지 (메모리 절약)
            if len(self.streaming_context["streaming_chunks"]) > 100:
                self.streaming_context["streaming_chunks"] = self.streaming_context["streaming_chunks"][-100:]
            
        except Exception as e:
            log_step("스트리밍 컨텍스트 업데이트", "ERROR", f"업데이트 실패: {str(e)}")
    
    async def finalize_streaming_session(self, thread_id: str, 
                                       final_result: Dict[str, Any]) -> None:
        """스트리밍 세션 완료 시 메모리 정리 및 데이터 통합"""
        try:
            if self.memory_manager:
                # 최종 결과 저장
                await self.memory_manager.save_analysis_result(
                    thread_id,
                    final_result.get("corp_code", "unknown"),
                    final_result
                )
                
                # 스트리밍 컨텍스트 저장
                await self.memory_manager.save_context_memory(
                    thread_id, "streaming_context", self.streaming_context
                )
                
                # Store API로 세션 데이터 수집 및 통합
                if self.memory_manager.store:
                    namespace = ("session", thread_id)
                    session_data = await self.memory_manager.store.asearch(namespace)
                    
                    # 최종 분석 결과 저장
                    await self.memory_manager.save_analysis_result(
                        thread_id, 
                        final_result.get("corp_code", "unknown"),
                        {
                            **final_result,
                            "session_data": session_data,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
            
            # 통계 로깅
            log_step("스트리밍 세션 완료", "SUCCESS", 
                    f"thread_id: {thread_id}, 통계: {self.chunk_stats}")
            
            # 스트리밍 컨텍스트 정리
            self.streaming_context.clear()
            self.chunk_stats = {
                "total_chunks": 0,
                "tool_calls": 0,
                "tool_results": 0,
                "agent_responses": 0,
                "errors": 0
            }
            
        except Exception as e:
            log_step("스트리밍 세션 완료", "ERROR", f"정리 실패: {str(e)}")
    
    def get_streaming_stats(self) -> Dict[str, Any]:
        """스트리밍 통계 조회"""
        return {
            **self.chunk_stats,
            "streaming_context_size": len(self.streaming_context),
            "memory_manager_available": self.memory_manager is not None
        }
    
    def get_streaming_context(self) -> Dict[str, Any]:
        """스트리밍 컨텍스트 조회"""
        return self.streaming_context.copy()
    
    def clear_streaming_context(self):
        """스트리밍 컨텍스트 초기화"""
        self.streaming_context.clear()
        self.chunk_stats = {
            "total_chunks": 0,
            "tool_calls": 0,
            "tool_results": 0,
            "agent_responses": 0,
            "errors": 0
        }