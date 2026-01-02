"""
공통 Agent Chat History Service

모든 에이전트(DART, RealEstate, Health, Legislation)의 채팅 히스토리 관리.
agent_type으로 에이전트별 데이터 분리.
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import aiomysql

logger = logging.getLogger(__name__)


class AgentHistoryService:
    """공통 에이전트 채팅 히스토리 CRUD 서비스"""
    
    def __init__(self, agent_type: str):
        """
        Args:
            agent_type: 에이전트 타입 ('dart', 'realestate', 'health', 'legislation')
        """
        self.agent_type = agent_type
        self.db_host = os.environ.get('MARIADB_HOST', 'mariadb')
        self.db_port = int(os.environ.get('MARIADB_PORT', 3306))
        self.db_user = os.environ.get('MARIADB_USER', 'root')
        self.db_password = os.environ.get('MARIADB_PASSWORD', 'rootpass')
        self.db_name = os.environ.get('MARIADB_DATABASE', 'agent_portal')
    
    @asynccontextmanager
    async def get_connection(self):
        """MariaDB 연결 획득"""
        conn = await aiomysql.connect(
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
            db=self.db_name,
            autocommit=True
        )
        try:
            yield conn
        finally:
            conn.close()
    
    async def list_history(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """사용자의 채팅 히스토리 목록 조회"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT id, user_id, title, model_tab, created_at, updated_at
                    FROM agent_chat_history
                    WHERE agent_type = %s AND user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (self.agent_type, user_id, limit, offset)
                )
                rows = await cur.fetchall()
                
                result = []
                for row in rows:
                    item = dict(row)
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].isoformat()
                    if item.get('updated_at'):
                        item['updated_at'] = item['updated_at'].isoformat()
                    result.append(item)
                
                return result
    
    async def get_history(self, history_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """특정 채팅 히스토리 조회 (레포트 포함)"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT id, user_id, title, messages, report, model_tab, created_at, updated_at
                    FROM agent_chat_history
                    WHERE id = %s AND agent_type = %s AND user_id = %s
                    """,
                    (history_id, self.agent_type, user_id)
                )
                row = await cur.fetchone()
                
                if not row:
                    return None
                
                result = dict(row)
                if result.get('messages'):
                    result['messages'] = json.loads(result['messages'])
                if result.get('report'):
                    result['report'] = json.loads(result['report'])
                if result.get('created_at'):
                    result['created_at'] = result['created_at'].isoformat()
                if result.get('updated_at'):
                    result['updated_at'] = result['updated_at'].isoformat()
                
                return result
    
    async def create_history(
        self,
        user_id: str,
        title: str,
        messages: List[Dict[str, Any]],
        model_tab: str = "single",
        report: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """새 채팅 히스토리 생성"""
        history_id = str(uuid.uuid4())
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO agent_chat_history (id, agent_type, user_id, title, messages, report, model_tab)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        history_id,
                        self.agent_type,
                        user_id, 
                        title, 
                        json.dumps(messages, ensure_ascii=False), 
                        json.dumps(report, ensure_ascii=False) if report else None,
                        model_tab
                    )
                )
        
        return {
            "id": history_id,
            "user_id": user_id,
            "title": title,
            "model_tab": model_tab,
            "created_at": datetime.now().isoformat()
        }
    
    async def update_history(
        self,
        history_id: str,
        user_id: str,
        title: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        report: Optional[Dict[str, Any]] = None
    ) -> bool:
        """채팅 히스토리 업데이트"""
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = %s")
            params.append(title)
        
        if messages is not None:
            updates.append("messages = %s")
            params.append(json.dumps(messages, ensure_ascii=False))
        
        if report is not None:
            updates.append("report = %s")
            params.append(json.dumps(report, ensure_ascii=False))
        
        if not updates:
            return False
        
        params.extend([history_id, self.agent_type, user_id])
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    UPDATE agent_chat_history
                    SET {', '.join(updates)}
                    WHERE id = %s AND agent_type = %s AND user_id = %s
                    """,
                    tuple(params)
                )
                return cur.rowcount > 0
    
    async def delete_history(self, history_id: str, user_id: str) -> bool:
        """채팅 히스토리 삭제"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    DELETE FROM agent_chat_history
                    WHERE id = %s AND agent_type = %s AND user_id = %s
                    """,
                    (history_id, self.agent_type, user_id)
                )
                return cur.rowcount > 0
    
    async def search_history(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """채팅 히스토리 검색 (제목/내용 기반)"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                search_pattern = f"%{query}%"
                await cur.execute(
                    """
                    SELECT id, user_id, title, model_tab, created_at, updated_at
                    FROM agent_chat_history
                    WHERE agent_type = %s AND user_id = %s AND (title LIKE %s OR messages LIKE %s)
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (self.agent_type, user_id, search_pattern, search_pattern, limit)
                )
                rows = await cur.fetchall()
                
                result = []
                for row in rows:
                    item = dict(row)
                    if item.get('created_at'):
                        item['created_at'] = item['created_at'].isoformat()
                    if item.get('updated_at'):
                        item['updated_at'] = item['updated_at'].isoformat()
                    result.append(item)
                
                return result


# 에이전트별 싱글톤 인스턴스
realestate_history_service = AgentHistoryService("realestate")
health_history_service = AgentHistoryService("health")
legislation_history_service = AgentHistoryService("legislation")



