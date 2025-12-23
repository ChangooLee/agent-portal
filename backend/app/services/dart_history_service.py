"""
DART Chat History Service

사용자별 DART 채팅 히스토리 관리 서비스.
MariaDB의 dart_chat_history 테이블 사용.
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


class DartHistoryService:
    """DART 채팅 히스토리 CRUD 서비스"""
    
    def __init__(self):
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
                    FROM dart_chat_history
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset)
                )
                rows = await cur.fetchall()
                
                # datetime을 ISO 문자열로 변환
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
        """특정 채팅 히스토리 조회"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """
                    SELECT id, user_id, title, messages, model_tab, created_at, updated_at
                    FROM dart_chat_history
                    WHERE id = %s AND user_id = %s
                    """,
                    (history_id, user_id)
                )
                row = await cur.fetchone()
                
                if not row:
                    return None
                
                result = dict(row)
                if result.get('messages'):
                    result['messages'] = json.loads(result['messages'])
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
        model_tab: str
    ) -> Dict[str, Any]:
        """새 채팅 히스토리 생성"""
        history_id = str(uuid.uuid4())
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO dart_chat_history (id, user_id, title, messages, model_tab)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (history_id, user_id, title, json.dumps(messages, ensure_ascii=False), model_tab)
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
        messages: Optional[List[Dict[str, Any]]] = None
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
        
        if not updates:
            return False
        
        params.extend([history_id, user_id])
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    UPDATE dart_chat_history
                    SET {', '.join(updates)}
                    WHERE id = %s AND user_id = %s
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
                    DELETE FROM dart_chat_history
                    WHERE id = %s AND user_id = %s
                    """,
                    (history_id, user_id)
                )
                return cur.rowcount > 0
    
    async def search_history(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """채팅 히스토리 검색 (제목 기반)"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                search_pattern = f"%{query}%"
                await cur.execute(
                    """
                    SELECT id, user_id, title, model_tab, created_at, updated_at
                    FROM dart_chat_history
                    WHERE user_id = %s AND (title LIKE %s OR messages LIKE %s)
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (user_id, search_pattern, search_pattern, limit)
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


# 싱글톤 인스턴스
dart_history_service = DartHistoryService()

