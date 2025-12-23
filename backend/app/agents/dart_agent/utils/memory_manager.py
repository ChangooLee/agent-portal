"""
memory_manager.py
DART 멀티에이전트 시스템을 위한 메모리 관리자 - LangGraph 표준 준수
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langchain_core.messages import BaseMessage, HumanMessage

# count_tokens_approximately 대체
try:
    from langchain_core.messages.utils import count_tokens_approximately
except ImportError:
    def count_tokens_approximately(messages):
        """간단한 토큰 카운트 추정"""
        total = 0
        for msg in messages:
            if hasattr(msg, 'content'):
                total += len(str(msg.content)) // 4
        return total

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


def log_performance(operation: str, duration: float, details: str = ""):
    """성능 로깅 헬퍼 함수"""
    logger.info(f"[PERF] {operation}: {duration:.2f}ms {details}")


# LangGraph 표준 메모리 도구
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    LANGRAPH_AVAILABLE = True
except ImportError:
    LANGRAPH_AVAILABLE = False
    class PostgresSaver:
        pass


# =============================================================================
# 🧠 DART 메모리 관리자 - LangGraph 표준 기반
# =============================================================================

class DartMemoryManager:
    """LangGraph 표준을 준수하는 메모리 관리자"""
    
    def __init__(self, checkpointer, store):
        """
        Args:
            checkpointer: Short-term memory (thread-level persistence)
            store: Long-term memory (user/app-level data)
        """
        self.checkpointer = checkpointer
        self.store = store
        
        # 토큰 제한 설정
        self.token_limits = {
            "master": 10000,
            "financial": 15000,
            "governance": 10000,
            "document": 20000,
            "others": 8000
        }
        
        log_step("DartMemoryManager 초기화", "SUCCESS", "체크포인터와 Store 연결 완료")
    
    # =============================================================================
    # 🧠 Short-term Memory - 체크포인터 활용
    # =============================================================================
    
    def get_messages(self, thread_id: str) -> List[BaseMessage]:
        """대화 메시지 조회"""
        try:
            # 체크포인터에서 직접 조회 (표준 방식)
            from langgraph.checkpoint.base import empty_checkpoint
            
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = self.checkpointer.get(config)
            
            if checkpoint:
                return checkpoint.get("channel_values", {}).get("messages", [])
            return []
            
        except Exception as e:
            log_step("메시지 조회", "ERROR", f"조회 실패: {e}")
            return []
    
    async def intelligent_trim_messages(self, messages: List[BaseMessage], 
                                      agent_type: str, max_tokens: Optional[int] = None) -> List[BaseMessage]:
        """메시지 트림 - 중요도 기반"""
        if max_tokens is None:
            max_tokens = self.get_token_limit(agent_type)
        try:
            from langchain_core.messages import ToolMessage as LCToolMessage
            
            current_tokens = count_tokens_approximately(messages)
            
            if current_tokens <= max_tokens:
                return messages
            
            # 중요도 기반 메시지 분류
            important_messages = []
            tool_messages = []
            regular_messages = []
            
            for i, message in enumerate(messages):
                # 도구 호출/결과는 최우선 보존
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    important_messages.append(message)
                elif isinstance(message, LCToolMessage):
                    important_messages.append(message)
                elif "분석" in str(message.content) or "결과" in str(message.content):
                    tool_messages.append(message)
                else:
                    regular_messages.append(message)
            
            # 중요 메시지 우선 보존
            trimmed = []
            remaining_tokens = max_tokens
            
            for msg in important_messages:
                msg_tokens = count_tokens_approximately([msg])
                if msg_tokens <= remaining_tokens:
                    trimmed.append(msg)
                    remaining_tokens -= msg_tokens
            
            for msg in tool_messages:
                msg_tokens = count_tokens_approximately([msg])
                if msg_tokens <= remaining_tokens:
                    trimmed.append(msg)
                    remaining_tokens -= msg_tokens
            
            for msg in reversed(regular_messages):
                msg_tokens = count_tokens_approximately([msg])
                if msg_tokens <= remaining_tokens:
                    trimmed.insert(len(important_messages) + len([m for m in trimmed if m in tool_messages]), msg)
                    remaining_tokens -= msg_tokens
            
            log_step("메시지 트림", "SUCCESS", f"원본: {len(messages)}개 → {len(trimmed)}개")
            return trimmed
            
        except Exception as e:
            log_step("메시지 트림", "ERROR", f"오류: {e}")
            return messages[-10:] if len(messages) > 10 else messages
    
    async def delete_messages(self, messages: List[BaseMessage], 
                            indices: List[int]) -> List[BaseMessage]:
        """메시지 삭제"""
        try:
            return [msg for i, msg in enumerate(messages) if i not in indices]
        except Exception as e:
            log_step("메시지 삭제", "ERROR", f"오류: {e}")
            return messages
    
    async def summarize_messages(self, messages: List[BaseMessage], llm) -> str:
        """메시지 요약"""
        try:
            if not messages:
                return "대화 내용이 없습니다."
            
            summary_prompt = f"""다음 대화를 간단히 요약해주세요:
            
{chr(10).join([f"- {msg.content}" for msg in messages if hasattr(msg, 'content')])}

요약:"""
            
            response = await llm.ainvoke([HumanMessage(content=summary_prompt)])
            return response.content if hasattr(response, "content") else str(response)
            
        except Exception as e:
            log_step("메시지 요약", "ERROR", f"오류: {e}")
            return "요약 생성 실패"
    
    # =============================================================================
    # 🧠 Long-term Memory - Store API 활용
    # =============================================================================
    
    async def save_user_data(self, user_id: str, data_type: str, data: Dict[str, Any]) -> None:
        """사용자별 데이터 저장"""
        try:
            if not self.store:
                log_step("사용자 데이터 저장", "WARNING", "Store가 없음")
                return
            
            namespace = ("user", user_id)
            await self.store.aput(namespace, data_type, data)
            log_step("사용자 데이터 저장", "SUCCESS", f"user_id: {user_id}, type: {data_type}")
            
        except Exception as e:
            log_step("사용자 데이터 저장", "ERROR", f"오류: {e}")
    
    async def get_user_data(self, user_id: str, data_type: str) -> Dict[str, Any]:
        """사용자별 데이터 조회"""
        try:
            if not self.store:
                return {}
            
            namespace = ("user", user_id)
            result = await self.store.aget(namespace, data_type)
            return result if result else {}
            
        except Exception as e:
            log_step("사용자 데이터 조회", "ERROR", f"오류: {e}")
            return {}
    
    async def save_tool_result(self, thread_id: str, agent_type: str, 
                              tool_name: str, tool_result: str) -> None:
        """도구 결과 저장"""
        try:
            if not self.store:
                return
            
            namespace = ("session", thread_id)
            key = f"tool_{agent_type}_{tool_name}_{int(time.time())}"
            data = {
                "agent_type": agent_type,
                "tool_name": tool_name,
                "result": tool_result[:500],
                "timestamp": datetime.now().isoformat()
            }
            await self.store.aput(namespace, key, data)
            
        except Exception as e:
            log_step("도구 결과 저장", "ERROR", f"오류: {e}")
    
    async def save_analysis_result(self, thread_id: str, corp_code: str, 
                                  analysis_result: Dict[str, Any]) -> None:
        """분석 결과 저장"""
        try:
            if not self.store:
                return
            
            namespace = ("analysis", thread_id)
            key = f"{corp_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            await self.store.aput(namespace, key, analysis_result)
            
        except Exception as e:
            log_step("분석 결과 저장", "ERROR", f"오류: {e}")
    
    async def get_previous_analysis(self, thread_id: str, corp_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """이전 분석 결과 조회"""
        try:
            if not self.store:
                return []
            
            namespace = ("analysis", thread_id)
            results = await self.store.asearch(namespace)
            
            if corp_code and corp_code != "any":
                results = [r for r in results if corp_code in r.get("key", "")]
            
            return results[:3]
            
        except Exception as e:
            log_step("이전 분석 조회", "ERROR", f"오류: {e}")
            return []
    
    async def save_context_memory(self, thread_id: str, context_key: str, 
                                 context_data: Dict[str, Any]) -> None:
        """컨텍스트 메모리 저장"""
        try:
            if not self.store:
                return
            
            namespace = ("context", thread_id)
            await self.store.aput(namespace, context_key, context_data)
            
        except Exception as e:
            log_step("컨텍스트 메모리 저장", "ERROR", f"오류: {e}")
    
    async def search_user_data(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """사용자 데이터 검색"""
        try:
            if not self.store:
                return []
            
            namespace = ("user", user_id)
            results = await self.store.asearch(namespace, query)
            return results
            
        except Exception as e:
            log_step("사용자 데이터 검색", "ERROR", f"오류: {e}")
            return []
    
    async def list_user_data_keys(self, user_id: str) -> List[str]:
        """사용자 데이터 키 목록"""
        try:
            if not self.store:
                return []
            
            namespace = ("user", user_id)
            keys = await self.store.alist(namespace)
            return keys
            
        except Exception as e:
            log_step("키 목록 조회", "ERROR", f"오류: {e}")
            return []
    
    async def delete_user_data(self, user_id: str, data_type: str) -> bool:
        """사용자 데이터 삭제"""
        try:
            if not self.store:
                return False
            
            namespace = ("user", user_id)
            await self.store.adelete(namespace, data_type)
            log_step("사용자 데이터 삭제", "SUCCESS", f"user_id: {user_id}, type: {data_type}")
            return True
            
        except Exception as e:
            log_step("사용자 데이터 삭제", "ERROR", f"오류: {e}")
            return False
    
    async def save_app_data(self, data_type: str, data: Dict[str, Any]) -> None:
        """애플리케이션 레벨 데이터 저장"""
        try:
            if not self.store:
                return
            
            namespace = ("app", "global")
            await self.store.aput(namespace, data_type, data)
            log_step("앱 데이터 저장", "SUCCESS", f"type: {data_type}")
            
        except Exception as e:
            log_step("앱 데이터 저장", "ERROR", f"오류: {e}")
    
    async def get_app_data(self, data_type: str) -> Dict[str, Any]:
        """애플리케이션 레벨 데이터 조회"""
        try:
            if not self.store:
                return {}
            
            namespace = ("app", "global")
            result = await self.store.aget(namespace, data_type)
            return result if result else {}
            
        except Exception as e:
            log_step("앱 데이터 조회", "ERROR", f"오류: {e}")
            return {}
    
    # =============================================================================
    # 🧠 토큰 관리
    # =============================================================================
    
    async def update_token_usage(self, thread_id: str, agent_type: str, 
                                response_tokens: int = 0):
        """토큰 사용량 업데이트 - Store에 저장"""
        try:
            if not self.store:
                return
            
            namespace = ("session", thread_id)
            key = f"token_usage_{agent_type}"
            
            # 기존 사용량 조회
            existing = await self.store.aget(namespace, key) or {"total": 0}
            existing["total"] = existing.get("total", 0) + response_tokens
            existing["last_updated"] = datetime.now().isoformat()
            
            # 업데이트
            await self.store.aput(namespace, key, existing)
            
            # 경고 로깅
            limit = self.token_limits.get(agent_type, self.token_limits["others"])
            if existing["total"] > limit * 0.8:
                log_step("토큰 경고", "WARNING", f"{agent_type}: {existing['total']}/{limit}")
            
        except Exception as e:
            log_step("토큰 업데이트", "ERROR", f"오류: {e}")
    
    def get_token_limit(self, agent_type: str) -> int:
        """에이전트별 토큰 제한"""
        return self.token_limits.get(agent_type.lower(), self.token_limits["others"])