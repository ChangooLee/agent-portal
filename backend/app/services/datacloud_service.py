"""
Data Cloud Service - Zero Copy 데이터베이스 커넥터 서비스

Salesforce Data Cloud 스타일의 데이터베이스 연결 및 메타데이터 관리 서비스.
SQLAlchemy 스키마 리플렉션을 활용하여 데이터 복제 없이 실시간으로 DB 스키마/메타 조회.

라이선스:
- SQLAlchemy: MIT License
- aiomysql: MIT License  
- asyncpg: Apache 2.0
- clickhouse-connect: Apache 2.0
- cryptography: Apache 2.0/BSD
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import aiomysql
from cryptography.fernet import Fernet

from app.services.kong_service import kong_service

logger = logging.getLogger(__name__)

# 암호화 키 (환경변수에서 가져오거나 생성)
ENCRYPTION_KEY = os.environ.get('DATACLOUD_ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    # 개발용 기본 키 (프로덕션에서는 반드시 환경변수로 설정)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    logger.warning("DATACLOUD_ENCRYPTION_KEY not set, using generated key")

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


class DataCloudService:
    """Data Cloud 커넥터 서비스 - Zero Copy 데이터베이스 연결 관리"""
    
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
    
    def encrypt_password(self, password: str) -> str:
        """비밀번호 암호화 (Fernet)"""
        return fernet.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted: str) -> str:
        """비밀번호 복호화 (Fernet)"""
        return fernet.decrypt(encrypted.encode()).decode()
    
    async def create_connection(
        self,
        name: str,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        description: Optional[str] = None,
        extra_config: Optional[Dict] = None,
        register_kong: bool = True
    ) -> Dict[str, Any]:
        """새 DB 연결 생성"""
        connection_id = str(uuid.uuid4())
        password_encrypted = self.encrypt_password(password)
        
        kong_service_id = None
        kong_route_id = None
        kong_consumer_id = None
        kong_api_key = None
        
        if register_kong:
            try:
                kong_result = await kong_service.setup_mcp_server(
                    name=f"datacloud-{name}",
                    upstream_url=f"http://{host}:{port}",
                    enable_key_auth=True,
                    enable_rate_limiting=True,
                    rate_limit_minute=100
                )
                kong_service_id = kong_result.get('service_id')
                kong_route_id = kong_result.get('route_id')
                kong_consumer_id = kong_result.get('consumer_id')
                kong_api_key = kong_result.get('api_key')
            except Exception as e:
                logger.warning(f"Kong registration failed for {name}: {e}")
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO db_connections 
                    (id, name, description, db_type, host, port, database_name, 
                     username, password_encrypted, extra_config,
                     kong_service_id, kong_route_id, kong_consumer_id, kong_api_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    connection_id, name, description, db_type, host, port, database_name,
                    username, password_encrypted, 
                    json.dumps(extra_config) if extra_config else None,
                    kong_service_id, kong_route_id, kong_consumer_id, kong_api_key
                ))
        
        from datetime import datetime
        now = datetime.now().isoformat()
        
        return {
            'id': connection_id,
            'name': name,
            'description': description,
            'db_type': db_type,
            'host': host,
            'port': port,
            'database_name': database_name,
            'username': username,
            'enabled': True,
            'health_status': 'unknown',
            'last_health_check': None,
            'created_at': now,
            'updated_at': now,
            'extra_config': extra_config
        }
    
    async def list_connections(self, include_disabled: bool = False) -> List[Dict]:
        """모든 DB 연결 목록 조회"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                if include_disabled:
                    await cur.execute("""
                        SELECT id, name, description, db_type, host, port, 
                               database_name, username, extra_config, enabled, 
                               health_status, last_health_check, created_at, updated_at
                        FROM db_connections ORDER BY name
                    """)
                else:
                    await cur.execute("""
                        SELECT id, name, description, db_type, host, port, 
                               database_name, username, extra_config, enabled, 
                               health_status, last_health_check, created_at, updated_at
                        FROM db_connections WHERE enabled = TRUE ORDER BY name
                    """)
                rows = await cur.fetchall()
        
        connections = []
        for row in rows:
            conn_dict = dict(row)
            if conn_dict.get('extra_config'):
                conn_dict['extra_config'] = json.loads(conn_dict['extra_config'])
            for key in ['last_health_check', 'created_at', 'updated_at']:
                if conn_dict.get(key):
                    conn_dict[key] = conn_dict[key].isoformat()
            connections.append(conn_dict)
        
        return connections
    
    async def get_connection_by_id(self, connection_id: str) -> Optional[Dict]:
        """ID로 연결 정보 조회"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT id, name, description, db_type, host, port, database_name,
                           username, password_encrypted, extra_config, enabled, 
                           health_status, last_health_check, created_at, updated_at
                    FROM db_connections WHERE id = %s
                """, (connection_id,))
                row = await cur.fetchone()
        
        if not row:
            return None
        
        conn_dict = dict(row)
        if conn_dict.get('extra_config'):
            conn_dict['extra_config'] = json.loads(conn_dict['extra_config'])
        for key in ['last_health_check', 'created_at', 'updated_at']:
            if conn_dict.get(key):
                conn_dict[key] = conn_dict[key].isoformat()
        
        return conn_dict
    
    async def update_connection(
        self,
        connection_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        extra_config: Optional[Dict] = None,
        enabled: Optional[bool] = None
    ) -> bool:
        """연결 정보 수정"""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if host is not None:
            updates.append("host = %s")
            params.append(host)
        if port is not None:
            updates.append("port = %s")
            params.append(port)
        if database_name is not None:
            updates.append("database_name = %s")
            params.append(database_name)
        if username is not None:
            updates.append("username = %s")
            params.append(username)
        if password is not None:
            updates.append("password_encrypted = %s")
            params.append(self.encrypt_password(password))
        if extra_config is not None:
            updates.append("extra_config = %s")
            params.append(json.dumps(extra_config))
        if enabled is not None:
            updates.append("enabled = %s")
            params.append(enabled)
        
        if not updates:
            return False
        
        params.append(connection_id)
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                query = f"UPDATE db_connections SET {', '.join(updates)} WHERE id = %s"
                await cur.execute(query, params)
                return cur.rowcount > 0
    
    async def delete_connection(self, connection_id: str) -> bool:
        """연결 삭제"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT kong_service_id, kong_consumer_id
                    FROM db_connections WHERE id = %s
                """, (connection_id,))
                row = await cur.fetchone()
        
        if not row:
            return False
        
        if row.get('kong_service_id'):
            try:
                await kong_service.delete_service(row['kong_service_id'])
            except Exception as e:
                logger.warning(f"Failed to delete Kong service: {e}")
        
        if row.get('kong_consumer_id'):
            try:
                await kong_service.delete_consumer(row['kong_consumer_id'])
            except Exception as e:
                logger.warning(f"Failed to delete Kong consumer: {e}")
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM db_connections WHERE id = %s", (connection_id,))
                return cur.rowcount > 0
    
    async def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """DB 연결 테스트"""
        conn_info = await self.get_connection_by_id(connection_id)
        if not conn_info:
            return {'success': False, 'error': 'Connection not found'}
        
        db_type = conn_info['db_type']
        host = conn_info['host']
        port = conn_info['port']
        database_name = conn_info['database_name']
        username = conn_info['username']
        password = self.decrypt_password(conn_info['password_encrypted'])
        
        start_time = datetime.now()
        success = False
        error_msg = None
        server_version = None
        
        try:
            if db_type in ('mariadb', 'mysql'):
                test_conn = await aiomysql.connect(
                    host=host, port=port, user=username, 
                    password=password, db=database_name, connect_timeout=10
                )
                async with test_conn.cursor() as cur:
                    await cur.execute("SELECT VERSION()")
                    result = await cur.fetchone()
                    server_version = result[0] if result else 'Unknown'
                test_conn.close()
                success = True
                
            elif db_type == 'postgresql':
                import asyncpg
                test_conn = await asyncpg.connect(
                    host=host, port=port, user=username, 
                    password=password, database=database_name, timeout=10
                )
                server_version = str(test_conn.get_server_version())
                await test_conn.close()
                success = True
                
            elif db_type == 'clickhouse':
                import clickhouse_connect
                client = clickhouse_connect.get_client(
                    host=host, port=port, username=username, 
                    password=password, database=database_name
                )
                result = client.query("SELECT version()")
                server_version = result.first_row[0] if result.first_row else 'Unknown'
                client.close()
                success = True
                
            else:
                error_msg = f"Unsupported database type: {db_type}"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Connection test failed for {connection_id}: {e}")
        
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        health_status = 'healthy' if success else 'unhealthy'
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    UPDATE db_connections 
                    SET health_status = %s, last_health_check = NOW()
                    WHERE id = %s
                """, (health_status, connection_id))
        
        return {
            'success': success,
            'latency_ms': latency_ms,
            'server_version': server_version,
            'error': error_msg,
            'health_status': health_status
        }
    
    async def get_schema_metadata(
        self, connection_id: str, refresh: bool = False
    ) -> Dict[str, Any]:
        """DB 스키마 메타데이터 조회"""
        conn_info = await self.get_connection_by_id(connection_id)
        if not conn_info:
            return {'error': 'Connection not found'}
        
        if not refresh:
            cached = await self._get_cached_schema(connection_id)
            if cached:
                return cached
        
        try:
            schema_data = await self._fetch_schema_from_db(conn_info)
            await self._save_schema_cache(connection_id, schema_data)
            return schema_data
        except Exception as e:
            logger.error(f"Schema fetch failed for {connection_id}: {e}")
            return {'error': str(e)}
    
    async def _get_cached_schema(self, connection_id: str) -> Optional[Dict]:
        """캐시된 스키마 조회"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT schema_name, table_name, table_type, table_comment, row_count
                    FROM db_table_cache WHERE connection_id = %s
                    ORDER BY schema_name, table_name
                """, (connection_id,))
                tables = await cur.fetchall()
                
                if not tables:
                    return None
                
                await cur.execute("""
                    SELECT schema_name, table_name, column_name, data_type, 
                           is_nullable, is_primary_key, is_foreign_key, column_comment
                    FROM db_schema_cache WHERE connection_id = %s
                    ORDER BY schema_name, table_name, ordinal_position
                """, (connection_id,))
                columns = await cur.fetchall()
        
        result = {'tables': []}
        table_map = {}
        
        for t in tables:
            table_key = f"{t['schema_name']}.{t['table_name']}"
            table_data = {
                'schema': t['schema_name'],
                'name': t['table_name'],
                'type': t['table_type'],
                'comment': t['table_comment'],
                'row_count': t['row_count'],
                'columns': []
            }
            result['tables'].append(table_data)
            table_map[table_key] = table_data
        
        for c in columns:
            table_key = f"{c['schema_name']}.{c['table_name']}"
            if table_key in table_map:
                table_map[table_key]['columns'].append({
                    'name': c['column_name'],
                    'type': c['data_type'],
                    'nullable': bool(c['is_nullable']),
                    'primary_key': bool(c['is_primary_key']),
                    'foreign_key': bool(c['is_foreign_key']),
                    'comment': c['column_comment']
                })
        
        return result
    
    async def _fetch_schema_from_db(self, conn_info: Dict) -> Dict[str, Any]:
        """SQLAlchemy 리플렉션으로 스키마 조회"""
        from sqlalchemy import create_engine, inspect
        
        db_type = conn_info['db_type']
        host = conn_info['host']
        port = conn_info['port']
        database_name = conn_info['database_name']
        username = conn_info['username']
        password = self.decrypt_password(conn_info['password_encrypted'])
        
        if db_type in ('mariadb', 'mysql'):
            url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database_name}"
        elif db_type == 'postgresql':
            url = f"postgresql://{username}:{password}@{host}:{port}/{database_name}"
        elif db_type == 'clickhouse':
            url = f"clickhouse://{username}:{password}@{host}:{port}/{database_name}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        engine = create_engine(url, pool_pre_ping=True)
        inspector = inspect(engine)
        
        result = {'tables': []}
        
        try:
            schemas = inspector.get_schema_names()
        except:
            schemas = [None]
        
        for schema in schemas:
            if schema in ('information_schema', 'pg_catalog', 'pg_toast'):
                continue
            
            try:
                table_names = inspector.get_table_names(schema=schema)
            except:
                table_names = inspector.get_table_names()
            
            for table_name in table_names:
                try:
                    columns = inspector.get_columns(table_name, schema=schema)
                    pk = inspector.get_pk_constraint(table_name, schema=schema)
                    fks = inspector.get_foreign_keys(table_name, schema=schema)
                    
                    pk_columns = pk.get('constrained_columns', []) if pk else []
                    fk_columns = set()
                    for fk in fks:
                        fk_columns.update(fk.get('constrained_columns', []))
                    
                    try:
                        table_comment = inspector.get_table_comment(table_name, schema=schema)
                        table_comment_text = table_comment.get('text') if table_comment else None
                    except:
                        table_comment_text = None
                    
                    table_data = {
                        'schema': schema,
                        'name': table_name,
                        'type': 'table',
                        'comment': table_comment_text,
                        'columns': []
                    }
                    
                    for col in columns:
                        col_data = {
                            'name': col['name'],
                            'type': str(col['type']),
                            'nullable': col.get('nullable', True),
                            'primary_key': col['name'] in pk_columns,
                            'foreign_key': col['name'] in fk_columns,
                            'comment': col.get('comment'),
                            'default': str(col.get('default')) if col.get('default') else None
                        }
                        table_data['columns'].append(col_data)
                    
                    result['tables'].append(table_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to inspect table {table_name}: {e}")
        
        engine.dispose()
        return result
    
    async def _save_schema_cache(self, connection_id: str, schema_data: Dict) -> None:
        """스키마 캐시 저장"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM db_table_cache WHERE connection_id = %s", 
                    (connection_id,)
                )
                await cur.execute(
                    "DELETE FROM db_schema_cache WHERE connection_id = %s", 
                    (connection_id,)
                )
                
                for table in schema_data.get('tables', []):
                    table_id = str(uuid.uuid4())
                    await cur.execute("""
                        INSERT INTO db_table_cache 
                        (id, connection_id, schema_name, table_name, table_type, table_comment)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (table_id, connection_id, table.get('schema'), table['name'], 
                          table.get('type', 'table'), table.get('comment')))
                    
                    for idx, col in enumerate(table.get('columns', [])):
                        col_id = str(uuid.uuid4())
                        await cur.execute("""
                            INSERT INTO db_schema_cache 
                            (id, connection_id, schema_name, table_name, column_name, 
                             data_type, is_nullable, is_primary_key, is_foreign_key, 
                             column_comment, ordinal_position)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (col_id, connection_id, table.get('schema'), table['name'], 
                              col['name'], col.get('type'), col.get('nullable', True), 
                              col.get('primary_key', False), col.get('foreign_key', False), 
                              col.get('comment'), idx + 1))
    
    async def execute_query(
        self,
        connection_id: str,
        query: str,
        user_id: str,
        max_rows: int = 1000
    ) -> Dict[str, Any]:
        """SQL 쿼리 실행"""
        conn_info = await self.get_connection_by_id(connection_id)
        if not conn_info:
            return {'success': False, 'error': 'Connection not found'}
        
        query_upper = query.strip().upper()
        if query_upper.startswith('SELECT'):
            query_type = 'select'
        elif query_upper.startswith('INSERT'):
            query_type = 'insert'
        elif query_upper.startswith('UPDATE'):
            query_type = 'update'
        elif query_upper.startswith('DELETE'):
            query_type = 'delete'
        else:
            query_type = 'other'
        
        db_type = conn_info['db_type']
        host = conn_info['host']
        port = conn_info['port']
        database_name = conn_info['database_name']
        username = conn_info['username']
        password = self.decrypt_password(conn_info['password_encrypted'])
        
        start_time = datetime.now()
        success = False
        error_msg = None
        rows = []
        columns = []
        rows_affected = 0
        
        try:
            if db_type in ('mariadb', 'mysql'):
                test_conn = await aiomysql.connect(
                    host=host, port=port, user=username, 
                    password=password, db=database_name
                )
                async with test_conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query)
                    
                    if query_type == 'select':
                        rows = await cur.fetchmany(max_rows)
                        rows = [dict(r) for r in rows]
                        if rows:
                            columns = list(rows[0].keys())
                        rows_affected = len(rows)
                    else:
                        rows_affected = cur.rowcount
                        await test_conn.commit()
                
                test_conn.close()
                success = True
                
            elif db_type == 'postgresql':
                import asyncpg
                test_conn = await asyncpg.connect(
                    host=host, port=port, user=username, 
                    password=password, database=database_name
                )
                
                if query_type == 'select':
                    records = await test_conn.fetch(query)
                    if records:
                        columns = list(records[0].keys())
                        rows = [dict(r) for r in records[:max_rows]]
                    rows_affected = len(rows)
                else:
                    result = await test_conn.execute(query)
                    rows_affected = int(result.split()[-1]) if result else 0
                
                await test_conn.close()
                success = True
                
            elif db_type == 'clickhouse':
                import clickhouse_connect
                client = clickhouse_connect.get_client(
                    host=host, port=port, username=username, 
                    password=password, database=database_name
                )
                
                if query_type == 'select':
                    result = client.query(query)
                    columns = result.column_names
                    rows = [dict(zip(columns, row)) for row in result.result_rows[:max_rows]]
                    rows_affected = len(rows)
                else:
                    client.command(query)
                    rows_affected = 0
                
                client.close()
                success = True
                
            else:
                error_msg = f"Unsupported database type: {db_type}"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query execution failed: {e}")
        
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        log_id = str(uuid.uuid4())
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO db_query_logs 
                    (id, connection_id, user_id, query_text, query_type, 
                     execution_time_ms, rows_affected, status, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (log_id, connection_id, user_id, query[:5000], query_type, 
                      execution_time_ms, rows_affected, 
                      'success' if success else 'error', error_msg))
        
        for row in rows:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
        
        return {
            'success': success,
            'columns': columns,
            'rows': rows,
            'rows_affected': rows_affected,
            'execution_time_ms': execution_time_ms,
            'error': error_msg
        }
    
    async def add_business_term(
        self,
        connection_id: str,
        term_type: str,
        technical_name: str,
        business_name: str,
        schema_name: Optional[str] = None,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        description: Optional[str] = None,
        examples: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """비즈니스 용어 추가"""
        term_id = str(uuid.uuid4())
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO db_business_terms 
                    (id, connection_id, term_type, schema_name, table_name, column_name,
                     technical_name, business_name, description, examples, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    business_name = VALUES(business_name),
                    description = VALUES(description),
                    examples = VALUES(examples),
                    updated_at = NOW()
                """, (term_id, connection_id, term_type, schema_name, table_name, 
                      column_name, technical_name, business_name, description, 
                      examples, created_by))
        
        return {'id': term_id, 'technical_name': technical_name, 'business_name': business_name}
    
    async def get_business_terms(self, connection_id: str) -> List[Dict]:
        """비즈니스 용어집 조회"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT id, term_type, schema_name, table_name, column_name,
                           technical_name, business_name, description, examples
                    FROM db_business_terms WHERE connection_id = %s
                    ORDER BY term_type, table_name, column_name
                """, (connection_id,))
                rows = await cur.fetchall()
        
        return [dict(r) for r in rows]
    
    async def grant_permission(
        self,
        connection_id: str,
        permission_type: str,
        target_id: str,
        access_level: str = 'read',
        granted_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """권한 부여"""
        perm_id = str(uuid.uuid4())
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO db_connection_permissions 
                    (id, connection_id, permission_type, target_id, access_level, granted_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    access_level = VALUES(access_level),
                    granted_by = VALUES(granted_by),
                    granted_at = NOW()
                """, (perm_id, connection_id, permission_type, target_id, 
                      access_level, granted_by))
        
        return {
            'id': perm_id,
            'connection_id': connection_id,
            'permission_type': permission_type,
            'target_id': target_id,
            'access_level': access_level,
            'granted_at': datetime.now().isoformat()
        }
    
    async def revoke_permission(self, permission_id: str) -> bool:
        """권한 회수"""
        async with self.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM db_connection_permissions WHERE id = %s", 
                    (permission_id,)
                )
                return cur.rowcount > 0
    
    async def get_connection_permissions(self, connection_id: str) -> List[Dict]:
        """연결의 권한 목록 조회"""
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT id, permission_type, target_id, access_level, 
                           granted_by, granted_at
                    FROM db_connection_permissions WHERE connection_id = %s
                    ORDER BY permission_type, target_id
                """, (connection_id,))
                rows = await cur.fetchall()
        
        result = []
        for r in rows:
            d = dict(r)
            if d.get('granted_at'):
                d['granted_at'] = d['granted_at'].isoformat()
            result.append(d)
        
        return result
    
    async def check_user_permission(
        self,
        connection_id: str,
        user_id: str,
        group_ids: List[str],
        required_level: str = 'read'
    ) -> bool:
        """사용자 권한 확인"""
        level_order = {'read': 1, 'write': 2, 'admin': 3}
        required = level_order.get(required_level, 1)
        
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT access_level FROM db_connection_permissions
                    WHERE connection_id = %s AND permission_type = 'user' 
                    AND target_id = %s
                """, (connection_id, user_id))
                row = await cur.fetchone()
                if row and level_order.get(row['access_level'], 0) >= required:
                    return True
                
                if group_ids:
                    placeholders = ','.join(['%s'] * len(group_ids))
                    await cur.execute(f"""
                        SELECT MAX(CASE access_level 
                            WHEN 'admin' THEN 3 
                            WHEN 'write' THEN 2 
                            ELSE 1 END) as max_level
                        FROM db_connection_permissions
                        WHERE connection_id = %s AND permission_type = 'group' 
                        AND target_id IN ({placeholders})
                    """, [connection_id] + group_ids)
                    row = await cur.fetchone()
                    if row and row['max_level'] and row['max_level'] >= required:
                        return True
        
        return False

    async def generate_sql_from_natural_language(
        self,
        connection_id: str,
        question: str
    ) -> Dict[str, Any]:
        """
        자연어 질문을 SQL로 변환 (Text-to-SQL)
        
        Vanna AI 에이전트를 사용하여 스키마 인식 SQL 생성.
        
        1. 연결 정보 조회
        2. Vanna 에이전트에 스키마/용어집 학습 (캐시)
        3. Vanna를 통해 SQL 생성
        """
        from app.services.vanna_agent_service import vanna_agent_service
        
        try:
            # 1. 연결 정보 조회
            connection_info = await self.get_connection_by_id(connection_id)
            if not connection_info:
                return {"success": False, "error": "Connection not found", "sql": ""}
            
            # 2. 스키마가 캐시에 없으면 로드 및 학습
            if connection_id not in vanna_agent_service._schema_cache:
                schema = await self.get_schema_metadata(connection_id, refresh=False)
                if not schema or "tables" not in schema:
                    return {"success": False, "error": "스키마 정보를 가져올 수 없습니다.", "sql": ""}
                
                terms = await self.get_business_terms(connection_id)
                
                # Vanna 에이전트 생성 및 학습
                await vanna_agent_service.get_or_create_agent(connection_id, connection_info)
                await vanna_agent_service.train_agent(connection_id, schema, terms)
            
            # 3. Vanna를 통해 SQL 생성
            result = await vanna_agent_service.generate_sql(
                connection_id=connection_id,
                question=question,
                connection_info=connection_info,
            )
            
            return {
                "success": result.success,
                "sql": result.sql,
                "error": result.error,
                "model": result.model,
                "tokens_used": result.tokens_used
            }
            
        except Exception as e:
            logger.error(f"Text-to-SQL 생성 실패: {e}")
            return {"success": False, "error": str(e), "sql": ""}

    def _build_schema_context(self, schema: Dict[str, Any]) -> str:
        """스키마 정보를 텍스트 컨텍스트로 변환"""
        lines = []
        tables = schema.get("tables", [])
        
        # 최대 20개 테이블만 포함 (토큰 제한)
        for table in tables[:20]:
            table_name = table.get("name", "unknown")
            columns = table.get("columns", [])
            
            col_defs = []
            for col in columns[:30]:  # 테이블당 최대 30개 컬럼
                col_name = col.get("name", "")
                col_type = col.get("type", "")
                pk = " (PK)" if col.get("is_primary_key") else ""
                fk = " (FK)" if col.get("is_foreign_key") else ""
                col_defs.append(f"  - {col_name}: {col_type}{pk}{fk}")
            
            lines.append(f"테이블: {table_name}")
            lines.extend(col_defs)
            lines.append("")
        
        return "\n".join(lines)

    def _build_terms_context(self, terms: List[Dict[str, Any]]) -> str:
        """비즈니스 용어집을 텍스트 컨텍스트로 변환"""
        if not terms:
            return "등록된 비즈니스 용어가 없습니다."
        
        lines = []
        for term in terms[:50]:  # 최대 50개 용어
            tech = term.get("technical_name", "")
            biz = term.get("business_name", "")
            desc = term.get("description", "")
            lines.append(f"- {tech} = {biz}" + (f" ({desc})" if desc else ""))
        
        return "\n".join(lines)


# Singleton
datacloud_service = DataCloudService()
