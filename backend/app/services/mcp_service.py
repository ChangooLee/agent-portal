"""
MCP Service

MCP 서버 등록, 조회, 수정, 삭제를 담당하는 서비스.
MariaDB에 MCP 서버 정보를 저장하고, Kong Gateway와 연동합니다.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
import os
import aiomysql
from fastapi import HTTPException

from app.services.kong_service import kong_service
from app.mcp.git_manager import GitManager
from app.mcp.process_manager import process_manager, ProcessStatus
from app.mcp.http_adapter import http_adapter
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
from app.mcp.git_manager import GitManager
from app.mcp.process_manager import process_manager, ProcessStatus
from app.mcp.http_adapter import http_adapter
from app.config import get_settings


class MCPService:
    """MCP 서버 관리 서비스.
    
    Attributes:
        db_host: MariaDB 호스트
        db_port: MariaDB 포트
        db_user: MariaDB 사용자
        db_password: MariaDB 비밀번호
        db_name: MariaDB 데이터베이스명
    """
    
    def __init__(self):
        self.db_host = os.getenv("MARIADB_HOST", "mariadb")
        self.db_port = int(os.getenv("MARIADB_PORT", "3306"))
        self.db_user = os.getenv("MARIADB_USER", "root")
        self.db_password = os.getenv("MARIADB_ROOT_PASSWORD", "root")
        self.db_name = os.getenv("MARIADB_DATABASE", "agent_portal")
        settings = get_settings()
        self.git_manager = GitManager(storage_path=settings.MCP_STORAGE_PATH)
    
    async def _get_connection(self):
        """MariaDB 연결 생성."""
        return await aiomysql.connect(
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
            db=self.db_name,
            charset='utf8mb4',
            autocommit=True
        )
    
    async def _execute_query(
        self,
        query: str,
        params: tuple = (),
        fetch: bool = True
    ) -> List[Dict[str, Any]]:
        """SQL 쿼리 실행.
        
        Args:
            query: SQL 쿼리
            params: 쿼리 파라미터
            fetch: 결과 조회 여부
            
        Returns:
            쿼리 결과 리스트
        """
        conn = await self._get_connection()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                if fetch:
                    result = await cursor.fetchall()
                    return list(result)
                return []
        finally:
            conn.close()
    
    # ==================== CRUD 작업 ====================
    
    async def list_servers(
        self,
        enabled_only: bool = False,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """MCP 서버 목록 조회.
        
        Args:
            enabled_only: 활성화된 서버만 조회
            page: 페이지 번호
            size: 페이지 크기
            
        Returns:
            서버 목록 및 페이지네이션 정보
        """
        offset = (page - 1) * size
        
        # 조건 절
        where_clause = "WHERE 1=1"
        if enabled_only:
            where_clause += " AND enabled = TRUE"
        
        # 총 개수
        count_query = f"SELECT COUNT(*) as total FROM mcp_servers {where_clause}"
        count_result = await self._execute_query(count_query)
        total = count_result[0]['total'] if count_result else 0
        
        # 서버 목록
        list_query = f"""
        SELECT 
            id, name, description, endpoint_url, transport_type,
            auth_type, auth_config, kong_service_id, kong_route_id,
            kong_consumer_id, kong_api_key, enabled, last_health_check,
            health_status, created_by, created_at, updated_at,
            github_url, local_path, command, env_vars, process_pid, process_status
        FROM mcp_servers
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
        servers = await self._execute_query(list_query, (size, offset))
        
        # JSON 필드 파싱
        for server in servers:
            if server.get('auth_config'):
                try:
                    server['auth_config'] = json.loads(server['auth_config'])
                except:
                    pass
            if server.get('env_vars'):
                try:
                    if isinstance(server['env_vars'], str):
                        server['env_vars'] = json.loads(server['env_vars'])
                except:
                    pass
        
        return {
            "servers": [self._filter_kong_info(s) for s in servers],
            "total": total,
            "page": page,
            "size": size
        }
    
    async def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """MCP 서버 상세 조회.
        
        Args:
            server_id: 서버 ID
            
        Returns:
            서버 정보 또는 None
        """
        query = """
        SELECT 
            id, name, description, endpoint_url, transport_type,
            auth_type, auth_config, kong_service_id, kong_route_id,
            kong_consumer_id, kong_api_key, enabled, last_health_check,
            health_status, created_by, created_at, updated_at
        FROM mcp_servers
        WHERE id = %s
        """
        result = await self._execute_query(query, (server_id,))
        
        if not result:
            return None
        
        server = result[0]
        
        # JSON 필드 파싱
        if server.get('auth_config'):
            try:
                server['auth_config'] = json.loads(server['auth_config'])
            except:
                pass
        
        return self._filter_kong_info(server)
    
    async def _get_server_internal(self, server_id: str) -> Optional[Dict[str, Any]]:
        """MCP 서버 상세 조회 (내부용, Kong 정보 포함).
        
        Args:
            server_id: 서버 ID
            
        Returns:
            서버 정보 또는 None (Kong 정보 포함)
        """
        query = """
        SELECT 
            id, name, description, endpoint_url, transport_type,
            auth_type, auth_config, kong_service_id, kong_route_id,
            kong_consumer_id, kong_api_key, enabled, last_health_check,
            health_status, created_by, created_at, updated_at,
            github_url, local_path, command, env_vars, process_pid, process_status
        FROM mcp_servers
        WHERE id = %s
        """
        result = await self._execute_query(query, (server_id,))
        
        if not result:
            return None
        
        server = result[0]
        
        # JSON 필드 파싱
        if server.get('auth_config'):
            try:
                server['auth_config'] = json.loads(server['auth_config'])
            except:
                pass
        
        if server.get('env_vars'):
            try:
                if isinstance(server['env_vars'], str):
                    server['env_vars'] = json.loads(server['env_vars'])
            except:
                pass
        
        return server
    
    def _filter_kong_info(self, server: Dict[str, Any]) -> Dict[str, Any]:
        """Kong 관련 정보를 응답에서 제거.
        
        보안상 사용자에게 Kong 내부 정보를 노출하지 않습니다.
        
        Args:
            server: 서버 정보
            
        Returns:
            Kong 정보가 제거된 서버 정보
        """
        if server is None:
            return None
        
        filtered = dict(server)
        # Kong 관련 필드 제거
        filtered.pop('kong_service_id', None)
        filtered.pop('kong_route_id', None)
        filtered.pop('kong_consumer_id', None)
        filtered.pop('kong_api_key', None)
        return filtered
    
    async def create_server(
        self,
        name: str,
        endpoint_url: str,
        description: Optional[str] = None,
        transport_type: str = "streamable_http",
        auth_type: str = "none",
        auth_config: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """MCP 서버 생성.
        
        모든 MCP 서버는 Kong Gateway를 통해 서비스됩니다.
        Kong Gateway 연동은 필수이며, API Key 인증과 Rate Limiting이 적용됩니다.
        
        Args:
            name: 서버 이름
            endpoint_url: 서버 엔드포인트 URL
            description: 서버 설명
            transport_type: 전송 타입 (streamable_http, sse)
            auth_type: 인증 타입 (none, api_key, bearer)
            auth_config: 인증 설정
            created_by: 생성자 ID
            
        Returns:
            생성된 서버 정보
            
        Raises:
            HTTPException: Kong Gateway 연동 실패 시
        """
        server_id = str(uuid.uuid4())
        
        # Kong Gateway 연동 (필수)
        try:
            kong_info = await kong_service.setup_mcp_server(
                server_id=server_id,
                server_name=name,
                endpoint_url=endpoint_url
            )
        except HTTPException as e:
            raise HTTPException(
                status_code=500,
                detail=f"Kong Gateway 연동 실패: {e.detail}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Kong Gateway 연동 중 오류 발생: {str(e)}"
            )
        
        # DB 저장
        query = """
        INSERT INTO mcp_servers (
            id, name, description, endpoint_url, transport_type,
            auth_type, auth_config, kong_service_id, kong_route_id,
            kong_consumer_id, kong_api_key, enabled, created_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s)
        """
        
        auth_config_json = json.dumps(auth_config) if auth_config else None
        
        await self._execute_query(
            query,
            (
                server_id, name, description, endpoint_url, transport_type,
                auth_type, auth_config_json,
                kong_info.get('kong_service_id'),
                kong_info.get('kong_route_id'),
                kong_info.get('kong_consumer_id'),
                kong_info.get('kong_api_key'),
                created_by
            ),
            fetch=False
        )
        
        return await self.get_server(server_id)
    
    async def update_server(
        self,
        server_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        transport_type: Optional[str] = None,
        auth_type: Optional[str] = None,
        auth_config: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """MCP 서버 수정.
        
        Args:
            server_id: 서버 ID
            name: 서버 이름
            description: 서버 설명
            endpoint_url: 서버 엔드포인트 URL
            transport_type: 전송 타입
            auth_type: 인증 타입
            auth_config: 인증 설정
            enabled: 활성화 여부
            
        Returns:
            수정된 서버 정보
        """
        # 기존 서버 확인
        existing = await self.get_server(server_id)
        if not existing:
            return None
        
        # 업데이트할 필드 구성
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if endpoint_url is not None:
            updates.append("endpoint_url = %s")
            params.append(endpoint_url)
        if transport_type is not None:
            updates.append("transport_type = %s")
            params.append(transport_type)
        if auth_type is not None:
            updates.append("auth_type = %s")
            params.append(auth_type)
        if auth_config is not None:
            updates.append("auth_config = %s")
            params.append(json.dumps(auth_config))
        if enabled is not None:
            updates.append("enabled = %s")
            params.append(enabled)
        
        if not updates:
            return existing
        
        params.append(server_id)
        
        query = f"""
        UPDATE mcp_servers
        SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """
        
        await self._execute_query(query, tuple(params), fetch=False)
        
        # get_server는 이미 필터링된 결과를 반환
        return await self.get_server(server_id)
    
    async def delete_server(self, server_id: str) -> bool:
        """MCP 서버 삭제.
        
        Args:
            server_id: 서버 ID
            
        Returns:
            삭제 성공 여부
        """
        # 기존 서버 확인 (내부용, Kong 정보 포함)
        existing = await self._get_server_internal(server_id)
        if not existing:
            return False
        
        # stdio 서버인 경우 프로세스 정리
        if existing.get('transport_type') == 'stdio':
            try:
                await process_manager.stop_process(server_id)
                await http_adapter.cleanup(server_id)
            except:
                pass
        
        # Kong Gateway 리소스 정리
        if existing.get('kong_service_id'):
            try:
                await kong_service.cleanup_mcp_server(server_id)
            except:
                pass  # Kong 정리 실패해도 DB 삭제 진행
        
        # DB 삭제 (CASCADE로 tools, projects 매핑도 삭제됨)
        query = "DELETE FROM mcp_servers WHERE id = %s"
        await self._execute_query(query, (server_id,), fetch=False)
        
        return True
    
    # ==================== 도구 관리 ====================
    
    async def get_server_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """MCP 서버의 도구 목록 조회.
        
        stdio MCP 서버의 경우 실제 서버에 연결하여 도구 목록을 가져옵니다.
        다른 transport 타입은 DB에서 조회합니다.
        
        Args:
            server_id: 서버 ID
            
        Returns:
            도구 목록
        """
        server = await self._get_server_internal(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        # stdio MCP 서버의 경우 실제 서버에 연결하여 도구 목록 가져오기
        if server.get('transport_type') == 'stdio':
            try:
                # HTTP 어댑터를 통해 실행 중인 프로세스에 연결
                # HTTP 어댑터는 이미 실행 중인 프로세스와 통신할 수 있음
                from app.mcp.http_adapter import http_adapter
                import httpx
                
                # HTTP 어댑터를 직접 사용 (내부 호출)
                from app.mcp.http_adapter import http_adapter
                from fastapi import Request
                from starlette.requests import Request as StarletteRequest
                from starlette.datastructures import Headers, URL
                
                # Get server config
                command = server.get('command')
                local_path = server.get('local_path')
                env_vars = server.get('env_vars')
                
                if not command:
                    raise HTTPException(status_code=400, detail="command not found")
                
                # Parse env_vars
                env = {}
                if env_vars:
                    if isinstance(env_vars, str):
                        env = json.loads(env_vars)
                    else:
                        env = env_vars
                
                # 실행 중인 프로세스의 stdin/stdout을 직접 사용
                from app.mcp.process_manager import process_manager
                existing_process = process_manager.get_process(server_id)
                
                # 프로세스가 process_manager에 없으면 PID로 직접 확인
                if not existing_process:
                    process_pid = server.get('process_pid')
                    if process_pid:
                        # PID로 프로세스 찾기 시도
                        # process_manager의 processes 딕셔너리에서 찾기
                        if hasattr(process_manager, 'processes') and server_id in process_manager.processes:
                            existing_process = process_manager.processes[server_id]
                
                if existing_process and existing_process.returncode is None:
                    logger.info(f"[DEBUG] Using existing process for {server_id}")
                    logger.info(f"[DEBUG] Process PID: {existing_process.pid}, stdin: {existing_process.stdin is not None}, stdout: {existing_process.stdout is not None}")
                    # 실행 중인 프로세스의 stdin/stdout 사용
                    client = await http_adapter.get_client(server_id)
                    
                    if not client.is_connected():
                        import asyncio
                        try:
                            tools = await asyncio.wait_for(
                                client.connect(
                                    command, 
                                    local_path, 
                                    env, 
                                    reuse_existing_process=True,
                                    existing_process=existing_process
                                ),
                                timeout=10.0
                            )
                        except asyncio.TimeoutError:
                            raise HTTPException(status_code=504, detail="Connection timeout")
                    else:
                        import asyncio
                        try:
                            tools = await asyncio.wait_for(
                                client.list_tools(),
                                timeout=5.0
                            )
                        except asyncio.TimeoutError:
                            raise HTTPException(status_code=504, detail="List tools timeout")
                else:
                    # 프로세스가 실행 중이 아니면 새로 시작
                    logger.warning(f"Process {server_id} not running, starting new connection")
                    client = await http_adapter.get_client(server_id)
                    
                    if not client.is_connected():
                        import asyncio
                        try:
                            tools = await asyncio.wait_for(
                                client.connect(command, local_path, env, reuse_existing_process=False),
                                timeout=10.0
                            )
                        except asyncio.TimeoutError:
                            raise HTTPException(status_code=504, detail="Connection timeout")
                    else:
                        import asyncio
                        try:
                            tools = await asyncio.wait_for(
                                client.list_tools(),
                                timeout=5.0
                            )
                        except asyncio.TimeoutError:
                            raise HTTPException(status_code=504, detail="List tools timeout")
                
                # Convert MCP Tool objects to dicts
                import uuid
                from datetime import datetime
                result = []
                for tool in tools:
                    tool_id = str(uuid.uuid4())
                    now = datetime.utcnow()
                    result.append({
                        'id': tool_id,
                        'server_id': server_id,
                        'tool_name': tool.name,
                        'tool_description': tool.description or '',
                        'input_schema': tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                        'discovered_at': now,
                        'updated_at': now
                    })
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to get tools from stdio MCP server {server_id}: {e}", exc_info=True)
                # Fallback to DB
                pass
        
        # DB에서 조회 (기존 로직)
        query = """
        SELECT id, server_id, tool_name, tool_description, input_schema,
               discovered_at, updated_at
        FROM mcp_server_tools
        WHERE server_id = %s
        ORDER BY tool_name
        """
        tools = await self._execute_query(query, (server_id,))
        
        # JSON 필드 파싱
        for tool in tools:
            if tool.get('input_schema'):
                try:
                    tool['input_schema'] = json.loads(tool['input_schema'])
                except:
                    pass
        
        return tools
    
    async def sync_server_tools(
        self,
        server_id: str,
        tools: List[Dict[str, Any]]
    ) -> int:
        """MCP 서버의 도구 목록 동기화.
        
        Args:
            server_id: 서버 ID
            tools: 도구 목록 (name, description, input_schema)
            
        Returns:
            동기화된 도구 수
        """
        # 기존 도구 삭제
        delete_query = "DELETE FROM mcp_server_tools WHERE server_id = %s"
        await self._execute_query(delete_query, (server_id,), fetch=False)
        
        # 새 도구 추가
        insert_query = """
        INSERT INTO mcp_server_tools (id, server_id, tool_name, tool_description, input_schema)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        for tool in tools:
            tool_id = str(uuid.uuid4())
            input_schema_json = json.dumps(tool.get('input_schema')) if tool.get('input_schema') else None
            
            await self._execute_query(
                insert_query,
                (
                    tool_id,
                    server_id,
                    tool['name'],
                    tool.get('description'),
                    input_schema_json
                ),
                fetch=False
            )
        
        return len(tools)
    
    # ==================== 헬스 체크 ====================
    
    async def update_health_status(
        self,
        server_id: str,
        status: str  # 'healthy', 'unhealthy', 'unknown'
    ) -> None:
        """MCP 서버 헬스 상태 업데이트.
        
        Args:
            server_id: 서버 ID
            status: 헬스 상태
        """
        query = """
        UPDATE mcp_servers
        SET health_status = %s, last_health_check = CURRENT_TIMESTAMP
        WHERE id = %s
        """
        await self._execute_query(query, (status, server_id), fetch=False)
    
    # ==================== API Key 관리 ====================
    
    async def regenerate_api_key(self, server_id: str) -> Optional[str]:
        """MCP 서버의 Kong API Key 재발급 (내부 관리용).
        
        Args:
            server_id: 서버 ID
            
        Returns:
            새 API Key 또는 None
        """
        # 기존 서버 확인 (내부용, Kong 정보 포함)
        existing = await self._get_server_internal(server_id)
        if not existing or not existing.get('kong_consumer_id'):
            return None
        
        # Kong에서 새 키 발급
        try:
            new_key = await kong_service.regenerate_api_key(server_id)
        except HTTPException:
            return None
        
        # DB 업데이트
        query = """
        UPDATE mcp_servers
        SET kong_api_key = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """
        await self._execute_query(query, (new_key, server_id), fetch=False)
        
        return new_key
    
    # ==================== 호출 로그 ====================
    
    async def log_call(
        self,
        server_id: str,
        tool_name: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        request_payload: Optional[Dict[str, Any]] = None,
        response_payload: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        latency_ms: Optional[int] = None
    ) -> None:
        """MCP 호출 로그 기록.
        
        Args:
            server_id: 서버 ID
            tool_name: 도구 이름
            user_id: 사용자 ID
            project_id: 프로젝트 ID
            request_payload: 요청 페이로드
            response_payload: 응답 페이로드
            status: 상태 (success, error, timeout)
            error_message: 에러 메시지
            latency_ms: 응답 시간 (밀리초)
        """
        query = """
        INSERT INTO mcp_call_logs (
            server_id, tool_name, user_id, project_id,
            request_payload, response_payload, status, error_message, latency_ms
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        await self._execute_query(
            query,
            (
                server_id,
                tool_name,
                user_id,
                project_id,
                json.dumps(request_payload) if request_payload else None,
                json.dumps(response_payload) if response_payload else None,
                status,
                error_message,
                latency_ms
            ),
            fetch=False
        )
    
    # ==================== 권한 관리 ====================
    
    async def grant_permission(
        self,
        server_id: str,
        permission_type: str,  # 'user' or 'group'
        target_id: str,
        granted_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """MCP 서버 접근 권한 부여.
        
        Args:
            server_id: 서버 ID
            permission_type: 권한 타입 ('user' 또는 'group')
            target_id: 대상 ID (user_id 또는 group_id)
            granted_by: 권한 부여자 ID
            
        Returns:
            생성된 권한 정보
            
        Raises:
            HTTPException: 서버가 존재하지 않거나 중복 권한인 경우
        """
        # 서버 존재 확인
        server = await self.get_server(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        # 권한 타입 검증
        if permission_type not in ('user', 'group'):
            raise HTTPException(status_code=400, detail="permission_type must be 'user' or 'group'")
        
        permission_id = str(uuid.uuid4())
        
        # 중복 체크 및 삽입
        try:
            query = """
            INSERT INTO mcp_server_permissions (id, server_id, permission_type, target_id, granted_by)
            VALUES (%s, %s, %s, %s, %s)
            """
            await self._execute_query(
                query,
                (permission_id, server_id, permission_type, target_id, granted_by),
                fetch=False
            )
        except Exception as e:
            if "Duplicate entry" in str(e) or "uk_server_permission" in str(e):
                raise HTTPException(status_code=409, detail="Permission already exists")
            raise HTTPException(status_code=500, detail=f"Failed to grant permission: {str(e)}")
        
        from datetime import datetime
        return {
            "id": permission_id,
            "server_id": server_id,
            "permission_type": permission_type,
            "target_id": target_id,
            "granted_by": granted_by,
            "granted_at": datetime.now()
        }
    
    async def revoke_permission(self, permission_id: str) -> bool:
        """MCP 서버 접근 권한 회수.
        
        Args:
            permission_id: 권한 ID
            
        Returns:
            삭제 성공 여부
        """
        query = "DELETE FROM mcp_server_permissions WHERE id = %s"
        await self._execute_query(query, (permission_id,), fetch=False)
        return True
    
    async def get_server_permissions(self, server_id: str) -> List[Dict[str, Any]]:
        """MCP 서버의 권한 목록 조회.
        
        Args:
            server_id: 서버 ID
            
        Returns:
            권한 목록
        """
        query = """
        SELECT id, server_id, permission_type, target_id, granted_by, granted_at
        FROM mcp_server_permissions
        WHERE server_id = %s
        ORDER BY granted_at DESC
        """
        return await self._execute_query(query, (server_id,))
    
    async def check_user_permission(
        self,
        server_id: str,
        user_id: str,
        group_ids: List[str] = None
    ) -> bool:
        """사용자의 MCP 서버 접근 권한 확인.
        
        Args:
            server_id: 서버 ID
            user_id: 사용자 ID
            group_ids: 사용자가 속한 그룹 ID 목록
            
        Returns:
            접근 권한 여부
        """
        if group_ids is None:
            group_ids = []
        
        # 사용자 직접 권한 확인
        user_query = """
        SELECT COUNT(*) as count
        FROM mcp_server_permissions
        WHERE server_id = %s AND permission_type = 'user' AND target_id = %s
        """
        user_result = await self._execute_query(user_query, (server_id, user_id))
        if user_result and user_result[0]['count'] > 0:
            return True
        
        # 그룹 권한 확인
        if group_ids:
            placeholders = ','.join(['%s'] * len(group_ids))
            group_query = f"""
            SELECT COUNT(*) as count
            FROM mcp_server_permissions
            WHERE server_id = %s AND permission_type = 'group' AND target_id IN ({placeholders})
            """
            group_result = await self._execute_query(group_query, (server_id, *group_ids))
            if group_result and group_result[0]['count'] > 0:
                return True
        
        return False
    
    async def get_accessible_servers(
        self,
        user_id: str,
        group_ids: List[str] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        """사용자가 접근 가능한 MCP 서버 목록 조회.
        
        Args:
            user_id: 사용자 ID
            group_ids: 사용자가 속한 그룹 ID 목록
            is_admin: 관리자 여부 (True면 모든 서버 반환)
            
        Returns:
            접근 가능한 서버 목록
        """
        if is_admin:
            # 관리자는 모든 서버 접근 가능
            result = await self.list_servers(enabled_only=True)
            return result.get('servers', [])
        
        if group_ids is None:
            group_ids = []
        
        # 사용자 또는 그룹 권한이 있는 서버 조회
        if group_ids:
            placeholders = ','.join(['%s'] * len(group_ids))
            query = f"""
            SELECT DISTINCT s.id, s.name, s.description, s.endpoint_url, 
                   s.transport_type, s.auth_type, s.auth_config,
                   s.enabled, s.last_health_check, s.health_status,
                   s.created_by, s.created_at, s.updated_at
            FROM mcp_servers s
            INNER JOIN mcp_server_permissions p ON s.id = p.server_id
            WHERE s.enabled = TRUE
              AND (
                (p.permission_type = 'user' AND p.target_id = %s)
                OR (p.permission_type = 'group' AND p.target_id IN ({placeholders}))
              )
            ORDER BY s.name
            """
            servers = await self._execute_query(query, (user_id, *group_ids))
        else:
            query = """
            SELECT DISTINCT s.id, s.name, s.description, s.endpoint_url, 
                   s.transport_type, s.auth_type, s.auth_config,
                   s.enabled, s.last_health_check, s.health_status,
                   s.created_by, s.created_at, s.updated_at
            FROM mcp_servers s
            INNER JOIN mcp_server_permissions p ON s.id = p.server_id
            WHERE s.enabled = TRUE
              AND p.permission_type = 'user' AND p.target_id = %s
            ORDER BY s.name
            """
            servers = await self._execute_query(query, (user_id,))
        
        # JSON 필드 파싱 및 Kong 정보 필터링
        result = []
        for server in servers:
            if server.get('auth_config'):
                try:
                    server['auth_config'] = json.loads(server['auth_config'])
                except:
                    pass
            result.append(self._filter_kong_info(server))
        
        return result
    
    # ==================== stdio MCP 서버 관리 ====================
    
    async def create_stdio_server(
        self,
        name: str,
        github_url: str,
        config: Dict[str, Any],
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """GitHub에서 코드를 pull 받아 stdio MCP 서버 생성.
        
        Args:
            name: 서버 이름
            github_url: GitHub 저장소 URL
            config: 설정 딕셔너리 (command, env 등)
            description: 서버 설명
            created_by: 생성자 ID
            
        Returns:
            생성된 서버 정보
            
        Raises:
            HTTPException: 생성 실패 시
        """
        server_id = str(uuid.uuid4())
        
        try:
            # 1. GitHub에서 코드 pull
            logger.info(f"Cloning repository: {github_url}")
            repo_path = await self.git_manager.clone_or_pull(github_url, name)
            
            # 2. 의존성 설치
            logger.info(f"Installing dependencies: {repo_path}")
            await self.git_manager.install_dependencies(repo_path)
            
            # 3. 설정 파싱
            command = config.get("command", "")
            env_vars = config.get("env", {})
            
            if not command:
                raise HTTPException(
                    status_code=400,
                    detail="command is required in config"
                )
            
            # 4. 프로세스 시작
            logger.info(f"Starting process: {command}")
            process_pid = await process_manager.start_process(
                server_id=server_id,
                command=command,
                cwd=str(repo_path),
                env=env_vars
            )
            
            # 5. HTTP 어댑터 엔드포인트 생성
            # 어댑터는 /mcp/adapters/{server_id}로 접근 가능
            adapter_url = f"http://backend:3009/mcp/adapters/{server_id}"
            
            # 6. Kong Gateway에 어댑터 등록
            logger.info(f"Registering with Kong Gateway: {adapter_url}")
            kong_info = await kong_service.setup_mcp_server(
                server_id=server_id,
                server_name=name,
                endpoint_url=adapter_url
            )
            
            # 7. DB 저장
            query = """
            INSERT INTO mcp_servers (
                id, name, description, endpoint_url, transport_type,
                auth_type, auth_config, kong_service_id, kong_route_id,
                kong_consumer_id, kong_api_key, enabled, created_by,
                github_url, local_path, command, env_vars, process_pid, process_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s, %s, %s, %s)
            """
            
            env_vars_json = json.dumps(env_vars) if env_vars else None
            
            await self._execute_query(
                query,
                (
                    server_id, name, description, adapter_url, "stdio",
                    "none", None,  # auth_type, auth_config
                    kong_info.get('kong_service_id'),
                    kong_info.get('kong_route_id'),
                    kong_info.get('kong_consumer_id'),
                    kong_info.get('kong_api_key'),
                    created_by,
                    github_url, str(repo_path), command, env_vars_json,
                    process_pid, "running"
                ),
                fetch=False
            )
            
            logger.info(f"stdio MCP server created successfully: {server_id}")
            return await self.get_server(server_id)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create stdio MCP server: {e}", exc_info=True)
            # Cleanup on failure
            try:
                await process_manager.stop_process(server_id)
            except:
                pass
            try:
                await http_adapter.cleanup(server_id)
            except:
                pass
            try:
                if 'kong_info' in locals():
                    await kong_service.cleanup_mcp_server(server_id)
            except:
                pass
            
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create stdio MCP server: {str(e)}"
            )
    
    async def start_stdio_process(self, server_id: str) -> bool:
        """stdio MCP 서버 프로세스 시작.
        
        Args:
            server_id: 서버 ID
            
        Returns:
            성공 여부
        """
        server = await self._get_server_internal(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        if server.get('transport_type') != 'stdio':
            raise HTTPException(status_code=400, detail="Not a stdio MCP server")
        
        command = server.get('command')
        local_path = server.get('local_path')
        env_vars = server.get('env_vars')
        
        if not command:
            raise HTTPException(status_code=400, detail="command not found")
        
        # Parse env_vars
        env = {}
        if env_vars:
            if isinstance(env_vars, str):
                env = json.loads(env_vars)
            else:
                env = env_vars
        
        try:
            process_pid = await process_manager.start_process(
                server_id=server_id,
                command=command,
                cwd=local_path,
                env=env
            )
            
            # Update DB
            query = """
            UPDATE mcp_servers
            SET process_pid = %s, process_status = 'running', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            await self._execute_query(query, (process_pid, server_id), fetch=False)
            
            return True
        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            # Update status
            query = """
            UPDATE mcp_servers
            SET process_status = 'error', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            await self._execute_query(query, (server_id,), fetch=False)
            raise HTTPException(status_code=500, detail=f"Failed to start process: {str(e)}")
    
    async def stop_stdio_process(self, server_id: str) -> bool:
        """stdio MCP 서버 프로세스 중지.
        
        Args:
            server_id: 서버 ID
            
        Returns:
            성공 여부
        """
        server = await self._get_server_internal(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        if server.get('transport_type') != 'stdio':
            raise HTTPException(status_code=400, detail="Not a stdio MCP server")
        
        try:
            success = await process_manager.stop_process(server_id)
            
            if success:
                # Update DB
                query = """
                UPDATE mcp_servers
                SET process_pid = NULL, process_status = 'stopped', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
                await self._execute_query(query, (server_id,), fetch=False)
            
            return success
        except Exception as e:
            logger.error(f"Failed to stop process: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop process: {str(e)}")
    
    async def restart_stdio_process(self, server_id: str) -> bool:
        """stdio MCP 서버 프로세스 재시작.
        
        Args:
            server_id: 서버 ID
            
        Returns:
            성공 여부
        """
        server = await self._get_server_internal(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        if server.get('transport_type') != 'stdio':
            raise HTTPException(status_code=400, detail="Not a stdio MCP server")
        
        command = server.get('command')
        local_path = server.get('local_path')
        env_vars = server.get('env_vars')
        
        if not command:
            raise HTTPException(status_code=400, detail="command not found")
        
        # Parse env_vars
        env = {}
        if env_vars:
            if isinstance(env_vars, str):
                env = json.loads(env_vars)
            else:
                env = env_vars
        
        try:
            process_pid = await process_manager.restart_process(
                server_id=server_id,
                command=command,
                cwd=local_path,
                env=env
            )
            
            # Update DB
            query = """
            UPDATE mcp_servers
            SET process_pid = %s, process_status = 'running', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            await self._execute_query(query, (process_pid, server_id), fetch=False)
            
            return True
        except Exception as e:
            logger.error(f"Failed to restart process: {e}")
            # Update status
            query = """
            UPDATE mcp_servers
            SET process_status = 'error', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """
            await self._execute_query(query, (server_id,), fetch=False)
            raise HTTPException(status_code=500, detail=f"Failed to restart process: {str(e)}")
    
    async def get_stdio_process_status(self, server_id: str) -> Dict[str, Any]:
        """stdio MCP 서버 프로세스 상태 조회.
        
        Args:
            server_id: 서버 ID
            
        Returns:
            프로세스 상태 정보
        """
        server = await self._get_server_internal(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        if server.get('transport_type') != 'stdio':
            raise HTTPException(status_code=400, detail="Not a stdio MCP server")
        
        status = process_manager.get_process_status(server_id)
        pid = process_manager.get_process_pid(server_id)
        
        return {
            "server_id": server_id,
            "status": status.value,
            "pid": pid,
            "process_status": server.get('process_status', 'stopped')
        }
    
    async def get_stdio_process_logs(
        self,
        server_id: str,
        lines: Optional[int] = None
    ) -> List[str]:
        """stdio MCP 서버 프로세스 로그 조회.
        
        Args:
            server_id: 서버 ID
            lines: 조회할 로그 라인 수 (None이면 전체)
            
        Returns:
            로그 라인 리스트
        """
        server = await self._get_server_internal(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="MCP server not found")
        
        if server.get('transport_type') != 'stdio':
            raise HTTPException(status_code=400, detail="Not a stdio MCP server")
        
        return process_manager.get_logs(server_id, lines)


# Singleton 인스턴스
mcp_service = MCPService()

