"""
Agent Registry Service

에이전트 등록, 조회, 수정, 삭제를 담당하는 서비스.
Text2SQL, Langflow, Flowise, AutoGen 등 다양한 에이전트를 통합 관리.
"""

import os
import uuid
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

import aiomysql

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """에이전트 유형"""
    TEXT2SQL = "text2sql"
    LANGFLOW = "langflow"
    FLOWISE = "flowise"
    DART = "dart"
    CUSTOM = "custom"


class AgentStatus(str, Enum):
    """에이전트 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class AgentRegistryService:
    """
    에이전트 레지스트리 서비스.
    
    모든 에이전트(Text2SQL, Langflow, Flowise, Custom)를
    통합 관리하고 모니터링 대상으로 등록.
    """
    
    def __init__(self):
        self.db_host = os.getenv("MARIADB_HOST", "mariadb")
        self.db_port = int(os.getenv("MARIADB_PORT", "3306"))
        self.db_user = os.getenv("MARIADB_USER", "root")
        self.db_password = os.getenv("MARIADB_ROOT_PASSWORD", "rootpass")
        self.db_name = os.getenv("MARIADB_DATABASE", "agent_portal")
        self._pool: Optional[aiomysql.Pool] = None
        logger.info("AgentRegistryService initialized")
    
    async def _get_pool(self) -> aiomysql.Pool:
        """커넥션 풀 획득"""
        if self._pool is None or self._pool.closed:
            self._pool = await aiomysql.create_pool(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                db=self.db_name,
                charset='utf8mb4',
                autocommit=True,
                minsize=1,
                maxsize=10
            )
        return self._pool
    
    async def register_or_get(
        self,
        name: str,
        agent_type: AgentType,
        project_id: str = "default-project",
        external_id: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        에이전트 등록 또는 기존 에이전트 조회.
        
        동일한 name + project_id 조합이 있으면 기존 에이전트 반환,
        없으면 새로 생성.
        
        Args:
            name: 에이전트 이름
            agent_type: 에이전트 유형 (text2sql, langflow, flowise, custom)
            project_id: 프로젝트 ID
            external_id: 외부 시스템 ID (flow_id, chatflow_id 등)
            description: 설명
            config: 설정 JSON
            
        Returns:
            에이전트 정보 딕셔너리
        """
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 기존 에이전트 조회
                await cur.execute("""
                    SELECT * FROM agents 
                    WHERE name = %s AND project_id = %s
                """, (name, project_id))
                
                existing = await cur.fetchone()
                
                if existing:
                    # last_used_at 업데이트
                    await cur.execute("""
                        UPDATE agents SET last_used_at = NOW() WHERE id = %s
                    """, (existing['id'],))
                    
                    logger.debug(f"Existing agent found: {existing['id']}")
                    return self._row_to_dict(existing)
                
                # 새 에이전트 생성
                agent_id = str(uuid.uuid4())
                config_json = json.dumps(config) if config else None
                
                await cur.execute("""
                    INSERT INTO agents (id, name, type, project_id, external_id, 
                                       description, config, monitoring_enabled, 
                                       status, last_used_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, 'active', NOW())
                """, (agent_id, name, agent_type.value, project_id, 
                      external_id, description, config_json))
                
                logger.info(f"New agent registered: {agent_id} ({name})")
                
                return {
                    'id': agent_id,
                    'name': name,
                    'type': agent_type.value,
                    'project_id': project_id,
                    'external_id': external_id,
                    'description': description,
                    'config': config,
                    'monitoring_enabled': True,
                    'status': 'active',
                    'created_at': datetime.now().isoformat(),
                    'last_used_at': datetime.now().isoformat()
                }
    
    async def get_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """ID로 에이전트 조회"""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM agents WHERE id = %s", (agent_id,))
                row = await cur.fetchone()
                return self._row_to_dict(row) if row else None
    
    async def get_by_external_id(
        self, 
        external_id: str, 
        agent_type: Optional[AgentType] = None
    ) -> Optional[Dict[str, Any]]:
        """외부 ID로 에이전트 조회 (Langflow flow_id 등)"""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                if agent_type:
                    await cur.execute("""
                        SELECT * FROM agents 
                        WHERE external_id = %s AND type = %s
                    """, (external_id, agent_type.value))
                else:
                    await cur.execute("""
                        SELECT * FROM agents WHERE external_id = %s
                    """, (external_id,))
                
                row = await cur.fetchone()
                return self._row_to_dict(row) if row else None
    
    async def list_agents(
        self,
        project_id: Optional[str] = None,
        agent_type: Optional[AgentType] = None,
        status: Optional[AgentStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """에이전트 목록 조회"""
        pool = await self._get_pool()
        
        conditions = []
        params = []
        
        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)
        if agent_type:
            conditions.append("type = %s")
            params.append(agent_type.value)
        if status:
            conditions.append("status = %s")
            params.append(status.value)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(f"""
                    SELECT * FROM agents 
                    WHERE {where_clause}
                    ORDER BY COALESCE(last_used_at, '1970-01-01') DESC, created_at DESC
                    LIMIT %s OFFSET %s
                """, (*params, limit, offset))
                
                rows = await cur.fetchall()
                return [self._row_to_dict(row) for row in rows]
    
    async def update_agent(
        self,
        agent_id: str,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        monitoring_enabled: Optional[bool] = None,
        status: Optional[AgentStatus] = None
    ) -> Optional[Dict[str, Any]]:
        """에이전트 정보 업데이트"""
        pool = await self._get_pool()
        
        updates = []
        params = []
        
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if config is not None:
            updates.append("config = %s")
            params.append(json.dumps(config))
        if monitoring_enabled is not None:
            updates.append("monitoring_enabled = %s")
            params.append(monitoring_enabled)
        if status is not None:
            updates.append("status = %s")
            params.append(status.value)
        
        if not updates:
            return await self.get_by_id(agent_id)
        
        params.append(agent_id)
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(f"""
                    UPDATE agents SET {", ".join(updates)} WHERE id = %s
                """, tuple(params))
                
                return await self.get_by_id(agent_id)
    
    async def update_last_used(self, agent_id: str) -> None:
        """last_used_at 업데이트"""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    UPDATE agents SET last_used_at = NOW() WHERE id = %s
                """, (agent_id,))
    
    async def delete_agent(self, agent_id: str) -> bool:
        """에이전트 삭제 (soft delete - status를 inactive로)"""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    UPDATE agents SET status = 'inactive' WHERE id = %s
                """, (agent_id,))
                return cur.rowcount > 0
    
    async def get_agent_count(
        self,
        project_id: Optional[str] = None,
        agent_type: Optional[AgentType] = None
    ) -> int:
        """에이전트 수 조회"""
        pool = await self._get_pool()
        
        conditions = ["status = 'active'"]
        params = []
        
        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)
        if agent_type:
            conditions.append("type = %s")
            params.append(agent_type.value)
        
        where_clause = " AND ".join(conditions)
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"""
                    SELECT COUNT(*) FROM agents WHERE {where_clause}
                """, tuple(params))
                result = await cur.fetchone()
                return result[0] if result else 0
    
    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """DB 행을 딕셔너리로 변환"""
        if not row:
            return None
        
        result = dict(row)
        
        # JSON 필드 파싱
        if result.get('config'):
            try:
                result['config'] = json.loads(result['config'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        # datetime을 ISO 문자열로 변환
        for key in ['created_at', 'updated_at', 'last_used_at']:
            if key in result and result[key]:
                if isinstance(result[key], datetime):
                    result[key] = result[key].isoformat()
        
        # boolean 변환
        if 'monitoring_enabled' in result:
            result['monitoring_enabled'] = bool(result['monitoring_enabled'])
        
        return result


# Singleton instance
agent_registry = AgentRegistryService()

