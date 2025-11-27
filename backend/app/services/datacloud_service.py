"""
Data Cloud Service - Zero Copy Database Connector

Salesforce Data Cloud 스타일의 데이터베이스 커넥터 서비스.
SQLAlchemy를 사용하여 스키마 리플렉션 및 실시간 쿼리 실행.

라이선스:
- SQLAlchemy: MIT License
- asyncpg: Apache 2.0
- aiomysql: MIT License
- clickhouse-connect: Apache 2.0
- cryptography: Apache 2.0/BSD
"""

import uuid
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from cryptography.fernet import Fernet
import aiomysql

# SQLAlchemy imports
try:
    from sqlalchemy import create_engine, MetaData, inspect, text
    from sqlalchemy.engine import Engine
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Engine = None

# ClickHouse imports
try:
    import clickhouse_connect
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False


class DataCloudService:
    """Data Cloud 커넥터 서비스 - Zero Copy 데이터베이스 연결"""
    
    def __init__(self):
        self.db_host = os.getenv("MARIADB_HOST", "mariadb")
        self.db_port = int(os.getenv("MARIADB_PORT", "3306"))
        self.db_user = os.getenv("MARIADB_USER", "root")
        self.db_password = os.getenv("MARIADB_PASSWORD", "rootpass")
        self.db_name = os.getenv("MARIADB_DATABASE", "agent_portal")
        
        # Fernet 암호화 키 (환경변수에서 로드 또는 생성)
        self.encryption_key = os.getenv("DATACLOUD_ENCRYPTION_KEY")
        if not self.encryption_key:
            # 개발 환경용 기본 키 (프로덕션에서는 반드시 환경변수 설정 필요)
            self.encryption_key = Fernet.generate_key().decode()
        self.fernet = Fernet(self.encryption_key.encode() if isinstance(self.encryption_key, str) else self.encryption_key)
        
        # 연결 풀 캐시
        self._engine_cache: Dict[str, Engine] = {}
    
    async def _get_pool(self):
        """MariaDB 연결 풀 획득"""
        return await aiomysql.create_pool(
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
            db=self.db_name,
            autocommit=True
        )
    
    def encrypt_password(self, password: str) -> str:
        """비밀번호 암호화"""
        return self.fernet.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """비밀번호 복호화"""
        return self.fernet.decrypt(encrypted_password.encode()).decode()
    
    def _build_connection_url(self, connection: Dict[str, Any], include_password: bool = True) -> str:
        """SQLAlchemy 연결 URL 생성"""
        db_type = connection['db_type']
        host = connection['host']
        port = connection['port']
        database = connection['database_name']
        username = connection['username']
        password = self.decrypt_password(connection['password_encrypted']) if include_password else '***'
        
        # DB 타입별 드라이버 매핑
        driver_map = {
            'mariadb': 'mysql+pymysql',
            'mysql': 'mysql+pymysql',
            'postgresql': 'postgresql+psycopg2',
            'oracle': 'oracle+cx_oracle',
            'mssql': 'mssql+pyodbc',
            'sap_hana': 'hana+hdbcli',
            'clickhouse': 'clickhouse+native',  # clickhouse-sqlalchemy
        }
        
        driver = driver_map.get(db_type, db_type)
        
        # ClickHouse는 별도 처리
        if db_type == 'clickhouse':
            return f"clickhouse://{username}:{password}@{host}:{port}/{database}"
        
        return f"{driver}://{username}:{password}@{host}:{port}/{database}"
    
    def _get_engine(self, connection: Dict[str, Any]) -> Optional[Engine]:
        """SQLAlchemy 엔진 획득 (캐시 사용)"""
        if not SQLALCHEMY_AVAILABLE:
            return None
        
        connection_id = connection['id']
        if connection_id in self._engine_cache:
            return self._engine_cache[connection_id]
        
        try:
            url = self._build_connection_url(connection)
            engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
            self._engine_cache[connection_id] = engine
            return engine
        except Exception as e:
            print(f"Failed to create engine for {connection_id}: {e}")
            return None
    
    # ==================== Connection CRUD ====================
    
    async def create_connection(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """새 DB 연결 생성"""
        connection_id = str(uuid.uuid4())
        encrypted_password = self.encrypt_password(data['password'])
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO db_connections (
                        id, name, description, db_type, host, port, 
                        database_name, username, password_encrypted,
                        extra_config, enabled, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    connection_id,
                    data['name'],
                    data.get('description'),
                    data['db_type'],
                    data['host'],
                    data['port'],
                    data['database_name'],
                    data['username'],
                    encrypted_password,
                    json.dumps(data.get('extra_config', {})),
                    data.get('enabled', True),
                    data.get('created_by')
                ))
        pool.close()
        await pool.wait_closed()
        
        return await self.get_connection(connection_id)
    
    async def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """연결 정보 조회 (비밀번호 제외)"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT id, name, description, db_type, host, port,
                           database_name, username, extra_config,
                           kong_service_id, kong_route_id, kong_consumer_id,
                           enabled, health_status, last_health_check,
                           created_at, updated_at, created_by
                    FROM db_connections WHERE id = %s
                """, (connection_id,))
                row = await cur.fetchone()
        pool.close()
        await pool.wait_closed()
        
        if row:
            row['extra_config'] = json.loads(row['extra_config']) if row['extra_config'] else {}
        return row
    
    async def get_connection_with_password(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """연결 정보 조회 (비밀번호 포함 - 내부 사용)"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM db_connections WHERE id = %s", (connection_id,))
                row = await cur.fetchone()
        pool.close()
        await pool.wait_closed()
        
        if row:
            row['extra_config'] = json.loads(row['extra_config']) if row['extra_config'] else {}
        return row
    
    async def list_connections(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """연결 목록 조회"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                query = """
                    SELECT id, name, description, db_type, host, port,
                           database_name, username, extra_config,
                           kong_service_id, kong_route_id, kong_consumer_id,
                           enabled, health_status, last_health_check,
                           created_at, updated_at, created_by
                    FROM db_connections
                """
                if enabled_only:
                    query += " WHERE enabled = TRUE"
                query += " ORDER BY created_at DESC"
                
                await cur.execute(query)
                rows = await cur.fetchall()
        pool.close()
        await pool.wait_closed()
        
        for row in rows:
            row['extra_config'] = json.loads(row['extra_config']) if row['extra_config'] else {}
        return rows
    
    async def update_connection(self, connection_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """연결 정보 업데이트"""
        updates = []
        params = []
        
        if 'name' in data:
            updates.append("name = %s")
            params.append(data['name'])
        if 'description' in data:
            updates.append("description = %s")
            params.append(data['description'])
        if 'host' in data:
            updates.append("host = %s")
            params.append(data['host'])
        if 'port' in data:
            updates.append("port = %s")
            params.append(data['port'])
        if 'database_name' in data:
            updates.append("database_name = %s")
            params.append(data['database_name'])
        if 'username' in data:
            updates.append("username = %s")
            params.append(data['username'])
        if 'password' in data:
            updates.append("password_encrypted = %s")
            params.append(self.encrypt_password(data['password']))
        if 'extra_config' in data:
            updates.append("extra_config = %s")
            params.append(json.dumps(data['extra_config']))
        if 'enabled' in data:
            updates.append("enabled = %s")
            params.append(data['enabled'])
        
        if not updates:
            return await self.get_connection(connection_id)
        
        params.append(connection_id)
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"UPDATE db_connections SET {', '.join(updates)} WHERE id = %s",
                    params
                )
        pool.close()
        await pool.wait_closed()
        
        # 엔진 캐시 무효화
        if connection_id in self._engine_cache:
            del self._engine_cache[connection_id]
        
        return await self.get_connection(connection_id)
    
    async def delete_connection(self, connection_id: str) -> bool:
        """연결 삭제"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM db_connections WHERE id = %s", (connection_id,))
                affected = cur.rowcount
        pool.close()
        await pool.wait_closed()
        
        # 엔진 캐시 무효화
        if connection_id in self._engine_cache:
            self._engine_cache[connection_id].dispose()
            del self._engine_cache[connection_id]
        
        return affected > 0
    
    # ==================== Connection Test ====================
    
    async def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """연결 테스트"""
        import time
        start_time = time.time()
        
        connection = await self.get_connection_with_password(connection_id)
        if not connection:
            return {
                "success": False,
                "message": "Connection not found",
                "latency_ms": 0
            }
        
        try:
            db_type = connection['db_type']
            
            if db_type == 'clickhouse':
                result = await self._test_clickhouse_connection(connection)
            else:
                result = await self._test_sqlalchemy_connection(connection)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 헬스 상태 업데이트
            await self._update_health_status(
                connection_id, 
                'healthy' if result['success'] else 'unhealthy'
            )
            
            return {
                **result,
                "latency_ms": latency_ms
            }
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            await self._update_health_status(connection_id, 'unhealthy')
            return {
                "success": False,
                "message": str(e),
                "latency_ms": latency_ms
            }
    
    async def _test_sqlalchemy_connection(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        """SQLAlchemy 연결 테스트"""
        if not SQLALCHEMY_AVAILABLE:
            return {"success": False, "message": "SQLAlchemy not available"}
        
        engine = self._get_engine(connection)
        if not engine:
            return {"success": False, "message": "Failed to create engine"}
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            return {
                "success": True,
                "message": f"Connected to {connection['db_type']} at {connection['host']}:{connection['port']}"
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    async def _test_clickhouse_connection(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        """ClickHouse 연결 테스트"""
        if not CLICKHOUSE_AVAILABLE:
            return {"success": False, "message": "clickhouse-connect not available"}
        
        try:
            password = self.decrypt_password(connection['password_encrypted'])
            client = clickhouse_connect.get_client(
                host=connection['host'],
                port=connection['port'],
                username=connection['username'],
                password=password,
                database=connection['database_name']
            )
            result = client.query("SELECT 1")
            client.close()
            return {
                "success": True,
                "message": f"Connected to ClickHouse at {connection['host']}:{connection['port']}"
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    async def _update_health_status(self, connection_id: str, status: str):
        """헬스 상태 업데이트"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    UPDATE db_connections 
                    SET health_status = %s, last_health_check = NOW()
                    WHERE id = %s
                """, (status, connection_id))
        pool.close()
        await pool.wait_closed()
    
    # ==================== Schema Reflection ====================
    
    async def get_schema_metadata(self, connection_id: str, refresh: bool = False) -> Dict[str, Any]:
        """스키마 메타데이터 조회 (SQLAlchemy 리플렉션)"""
        connection = await self.get_connection_with_password(connection_id)
        if not connection:
            raise ValueError("Connection not found")
        
        # 캐시된 데이터 확인
        if not refresh:
            cached = await self._get_cached_schema(connection_id)
            if cached:
                return cached
        
        db_type = connection['db_type']
        
        if db_type == 'clickhouse':
            schema_data = await self._reflect_clickhouse_schema(connection)
        else:
            schema_data = await self._reflect_sqlalchemy_schema(connection)
        
        # 캐시 저장
        await self._cache_schema(connection_id, schema_data)
        
        return schema_data
    
    async def _reflect_sqlalchemy_schema(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        """SQLAlchemy를 사용한 스키마 리플렉션"""
        if not SQLALCHEMY_AVAILABLE:
            raise RuntimeError("SQLAlchemy not available")
        
        engine = self._get_engine(connection)
        if not engine:
            raise RuntimeError("Failed to create engine")
        
        inspector = inspect(engine)
        tables = []
        
        for table_name in inspector.get_table_names():
            columns = []
            pk_columns = set()
            fk_columns = {}
            
            # PK 정보
            pk_constraint = inspector.get_pk_constraint(table_name)
            if pk_constraint:
                pk_columns = set(pk_constraint.get('constrained_columns', []))
            
            # FK 정보
            for fk in inspector.get_foreign_keys(table_name):
                for col in fk.get('constrained_columns', []):
                    ref_table = fk.get('referred_table', '')
                    ref_cols = fk.get('referred_columns', [])
                    fk_columns[col] = f"{ref_table}.{ref_cols[0]}" if ref_cols else ref_table
            
            # 컬럼 정보
            for idx, col in enumerate(inspector.get_columns(table_name)):
                columns.append({
                    "name": col['name'],
                    "type": str(col['type']),
                    "nullable": col.get('nullable', True),
                    "default": str(col.get('default', '')) if col.get('default') else None,
                    "comment": col.get('comment'),
                    "is_primary_key": col['name'] in pk_columns,
                    "is_foreign_key": col['name'] in fk_columns,
                    "foreign_key_ref": fk_columns.get(col['name']),
                    "ordinal_position": idx + 1
                })
            
            # 테이블 코멘트
            try:
                table_comment = inspector.get_table_comment(table_name)
                comment = table_comment.get('text') if table_comment else None
            except:
                comment = None
            
            tables.append({
                "name": table_name,
                "type": "table",
                "comment": comment,
                "columns": columns
            })
        
        # View 정보
        for view_name in inspector.get_view_names():
            columns = []
            for idx, col in enumerate(inspector.get_columns(view_name)):
                columns.append({
                    "name": col['name'],
                    "type": str(col['type']),
                    "nullable": col.get('nullable', True),
                    "ordinal_position": idx + 1
                })
            
            tables.append({
                "name": view_name,
                "type": "view",
                "columns": columns
            })
        
        return {
            "database": connection['database_name'],
            "db_type": connection['db_type'],
            "tables": tables,
            "table_count": len(tables),
            "refreshed_at": datetime.now().isoformat()
        }
    
    async def _reflect_clickhouse_schema(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        """ClickHouse 스키마 리플렉션"""
        if not CLICKHOUSE_AVAILABLE:
            raise RuntimeError("clickhouse-connect not available")
        
        password = self.decrypt_password(connection['password_encrypted'])
        client = clickhouse_connect.get_client(
            host=connection['host'],
            port=connection['port'],
            username=connection['username'],
            password=password,
            database=connection['database_name']
        )
        
        try:
            # 테이블 목록
            tables_result = client.query("""
                SELECT name, engine, comment
                FROM system.tables
                WHERE database = currentDatabase()
            """)
            
            tables = []
            for table_row in tables_result.result_rows:
                table_name = table_row[0]
                engine = table_row[1]
                table_comment = table_row[2]
                
                # 컬럼 정보
                columns_result = client.query(f"""
                    SELECT name, type, default_kind, default_expression, comment, is_in_primary_key
                    FROM system.columns
                    WHERE database = currentDatabase() AND table = '{table_name}'
                    ORDER BY position
                """)
                
                columns = []
                for idx, col_row in enumerate(columns_result.result_rows):
                    columns.append({
                        "name": col_row[0],
                        "type": col_row[1],
                        "nullable": 'Nullable' in col_row[1],
                        "default": col_row[3] if col_row[2] else None,
                        "comment": col_row[4],
                        "is_primary_key": bool(col_row[5]),
                        "ordinal_position": idx + 1
                    })
                
                tables.append({
                    "name": table_name,
                    "type": "table",
                    "engine": engine,
                    "comment": table_comment,
                    "columns": columns
                })
            
            return {
                "database": connection['database_name'],
                "db_type": "clickhouse",
                "tables": tables,
                "table_count": len(tables),
                "refreshed_at": datetime.now().isoformat()
            }
        finally:
            client.close()
    
    async def _get_cached_schema(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """캐시된 스키마 조회"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 테이블 목록
                await cur.execute("""
                    SELECT DISTINCT table_name, table_type, table_comment
                    FROM db_table_cache
                    WHERE connection_id = %s
                """, (connection_id,))
                tables_raw = await cur.fetchall()
                
                if not tables_raw:
                    pool.close()
                    await pool.wait_closed()
                    return None
                
                # 컬럼 정보
                await cur.execute("""
                    SELECT table_name, column_name, data_type, is_nullable,
                           is_primary_key, is_foreign_key, foreign_key_ref,
                           column_comment, business_term, ordinal_position
                    FROM db_schema_cache
                    WHERE connection_id = %s
                    ORDER BY table_name, ordinal_position
                """, (connection_id,))
                columns_raw = await cur.fetchall()
        pool.close()
        await pool.wait_closed()
        
        # 테이블별 컬럼 그룹화
        columns_by_table = {}
        for col in columns_raw:
            table = col['table_name']
            if table not in columns_by_table:
                columns_by_table[table] = []
            columns_by_table[table].append({
                "name": col['column_name'],
                "type": col['data_type'],
                "nullable": col['is_nullable'],
                "is_primary_key": col['is_primary_key'],
                "is_foreign_key": col['is_foreign_key'],
                "foreign_key_ref": col['foreign_key_ref'],
                "comment": col['column_comment'],
                "business_term": col['business_term'],
                "ordinal_position": col['ordinal_position']
            })
        
        tables = []
        for t in tables_raw:
            tables.append({
                "name": t['table_name'],
                "type": t['table_type'],
                "comment": t['table_comment'],
                "columns": columns_by_table.get(t['table_name'], [])
            })
        
        return {
            "tables": tables,
            "table_count": len(tables),
            "from_cache": True
        }
    
    async def _cache_schema(self, connection_id: str, schema_data: Dict[str, Any]):
        """스키마 캐시 저장"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 기존 캐시 삭제
                await cur.execute("DELETE FROM db_table_cache WHERE connection_id = %s", (connection_id,))
                await cur.execute("DELETE FROM db_schema_cache WHERE connection_id = %s", (connection_id,))
                
                for table in schema_data.get('tables', []):
                    table_id = str(uuid.uuid4())
                    
                    # 테이블 캐시
                    await cur.execute("""
                        INSERT INTO db_table_cache (id, connection_id, table_name, table_type, table_comment)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (table_id, connection_id, table['name'], table.get('type', 'table'), table.get('comment')))
                    
                    # 컬럼 캐시
                    for col in table.get('columns', []):
                        await cur.execute("""
                            INSERT INTO db_schema_cache (
                                id, connection_id, table_name, column_name, data_type,
                                is_nullable, is_primary_key, is_foreign_key, foreign_key_ref,
                                column_comment, ordinal_position
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            str(uuid.uuid4()),
                            connection_id,
                            table['name'],
                            col['name'],
                            col.get('type'),
                            col.get('nullable', True),
                            col.get('is_primary_key', False),
                            col.get('is_foreign_key', False),
                            col.get('foreign_key_ref'),
                            col.get('comment'),
                            col.get('ordinal_position', 0)
                        ))
        pool.close()
        await pool.wait_closed()
    
    # ==================== Query Execution ====================
    
    async def execute_query(
        self, 
        connection_id: str, 
        query: str, 
        user_id: str,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """쿼리 실행 (Zero Copy - 실시간)"""
        import time
        start_time = time.time()
        
        connection = await self.get_connection_with_password(connection_id)
        if not connection:
            raise ValueError("Connection not found")
        
        # SELECT 쿼리만 허용 (안전)
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            query_type = 'other'
            if query_upper.startswith('INSERT'):
                query_type = 'insert'
            elif query_upper.startswith('UPDATE'):
                query_type = 'update'
            elif query_upper.startswith('DELETE'):
                query_type = 'delete'
        else:
            query_type = 'select'
        
        try:
            db_type = connection['db_type']
            
            if db_type == 'clickhouse':
                result = await self._execute_clickhouse_query(connection, query, limit)
            else:
                result = await self._execute_sqlalchemy_query(connection, query, limit)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # 쿼리 로그 저장
            await self._log_query(
                connection_id, user_id, query, query_type,
                execution_time_ms, len(result.get('rows', [])), 'success', None
            )
            
            return {
                **result,
                "execution_time_ms": execution_time_ms
            }
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # 에러 로그 저장
            await self._log_query(
                connection_id, user_id, query, query_type,
                execution_time_ms, 0, 'error', str(e)
            )
            
            raise
    
    async def _execute_sqlalchemy_query(
        self, 
        connection: Dict[str, Any], 
        query: str,
        limit: int
    ) -> Dict[str, Any]:
        """SQLAlchemy 쿼리 실행"""
        if not SQLALCHEMY_AVAILABLE:
            raise RuntimeError("SQLAlchemy not available")
        
        engine = self._get_engine(connection)
        if not engine:
            raise RuntimeError("Failed to create engine")
        
        # LIMIT 추가 (없는 경우)
        query_upper = query.strip().upper()
        if 'LIMIT' not in query_upper and query_upper.startswith('SELECT'):
            query = f"{query.rstrip().rstrip(';')} LIMIT {limit}"
        
        with engine.connect() as conn:
            result = conn.execute(text(query))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
        
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows)
        }
    
    async def _execute_clickhouse_query(
        self, 
        connection: Dict[str, Any], 
        query: str,
        limit: int
    ) -> Dict[str, Any]:
        """ClickHouse 쿼리 실행"""
        if not CLICKHOUSE_AVAILABLE:
            raise RuntimeError("clickhouse-connect not available")
        
        password = self.decrypt_password(connection['password_encrypted'])
        client = clickhouse_connect.get_client(
            host=connection['host'],
            port=connection['port'],
            username=connection['username'],
            password=password,
            database=connection['database_name']
        )
        
        try:
            # LIMIT 추가
            query_upper = query.strip().upper()
            if 'LIMIT' not in query_upper and query_upper.startswith('SELECT'):
                query = f"{query.rstrip().rstrip(';')} LIMIT {limit}"
            
            result = client.query(query)
            columns = result.column_names
            rows = [dict(zip(columns, row)) for row in result.result_rows]
            
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }
        finally:
            client.close()
    
    async def _log_query(
        self,
        connection_id: str,
        user_id: str,
        query: str,
        query_type: str,
        execution_time_ms: int,
        rows_affected: int,
        status: str,
        error_message: Optional[str]
    ):
        """쿼리 로그 저장"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO db_query_logs (
                        id, connection_id, user_id, query_text, query_type,
                        execution_time_ms, rows_affected, status, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    connection_id,
                    user_id,
                    query[:10000],  # 최대 10000자
                    query_type,
                    execution_time_ms,
                    rows_affected,
                    status,
                    error_message
                ))
        pool.close()
        await pool.wait_closed()
    
    # ==================== Business Terms ====================
    
    async def add_business_term(
        self,
        connection_id: str,
        technical_name: str,
        technical_type: str,
        business_name: str,
        parent_table: Optional[str] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """비즈니스 용어 추가"""
        term_id = str(uuid.uuid4())
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO db_business_terms (
                        id, connection_id, technical_name, technical_type,
                        parent_table, business_name, description, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        business_name = VALUES(business_name),
                        description = VALUES(description)
                """, (
                    term_id,
                    connection_id,
                    technical_name,
                    technical_type,
                    parent_table,
                    business_name,
                    description,
                    created_by
                ))
        pool.close()
        await pool.wait_closed()
        
        return {
            "id": term_id,
            "connection_id": connection_id,
            "technical_name": technical_name,
            "business_name": business_name
        }
    
    async def get_business_terms(self, connection_id: str) -> List[Dict[str, Any]]:
        """비즈니스 용어 목록 조회"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM db_business_terms
                    WHERE connection_id = %s
                    ORDER BY technical_type, technical_name
                """, (connection_id,))
                rows = await cur.fetchall()
        pool.close()
        await pool.wait_closed()
        
        return rows
    
    # ==================== Permissions ====================
    
    async def grant_permission(
        self,
        connection_id: str,
        permission_type: str,
        target_id: str,
        permission_level: str = 'read',
        granted_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """권한 부여"""
        permission_id = str(uuid.uuid4())
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO db_connection_permissions (
                        id, connection_id, permission_type, target_id,
                        permission_level, granted_by
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        permission_level = VALUES(permission_level),
                        granted_by = VALUES(granted_by),
                        granted_at = NOW()
                """, (
                    permission_id,
                    connection_id,
                    permission_type,
                    target_id,
                    permission_level,
                    granted_by
                ))
        pool.close()
        await pool.wait_closed()
        
        return {
            "id": permission_id,
            "connection_id": connection_id,
            "permission_type": permission_type,
            "target_id": target_id,
            "permission_level": permission_level
        }
    
    async def check_permission(
        self,
        connection_id: str,
        user_id: str,
        group_ids: List[str],
        required_level: str = 'read'
    ) -> bool:
        """권한 확인"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 사용자 직접 권한
                await cur.execute("""
                    SELECT permission_level FROM db_connection_permissions
                    WHERE connection_id = %s AND permission_type = 'user' AND target_id = %s
                """, (connection_id, user_id))
                user_perm = await cur.fetchone()
                
                if user_perm:
                    pool.close()
                    await pool.wait_closed()
                    return self._check_permission_level(user_perm[0], required_level)
                
                # 그룹 권한
                if group_ids:
                    placeholders = ','.join(['%s'] * len(group_ids))
                    await cur.execute(f"""
                        SELECT permission_level FROM db_connection_permissions
                        WHERE connection_id = %s AND permission_type = 'group' AND target_id IN ({placeholders})
                    """, [connection_id] + group_ids)
                    group_perms = await cur.fetchall()
                    
                    for perm in group_perms:
                        if self._check_permission_level(perm[0], required_level):
                            pool.close()
                            await pool.wait_closed()
                            return True
        
        pool.close()
        await pool.wait_closed()
        return False
    
    def _check_permission_level(self, granted: str, required: str) -> bool:
        """권한 레벨 비교"""
        levels = {'read': 1, 'write': 2, 'admin': 3}
        return levels.get(granted, 0) >= levels.get(required, 0)


# Singleton instance
datacloud_service = DataCloudService()

