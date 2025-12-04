"""
Tools for Text-to-SQL Agent

참조: docs/plans/DATA_CLOUD_AGENT.md 섹션 4 (schema_selector, sql_executor)

DB 메타데이터 조회, SQL 실행 등의 Tool 함수들.
Multi-DB 지원: MariaDB, MySQL, PostgreSQL, ClickHouse, Oracle, SAP HANA, Databricks
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


async def get_db_type(connection_id: str) -> str:
    """
    connection_id로 DB 타입 조회.
    
    Returns:
        DB 타입 (mariadb, mysql, postgresql, clickhouse, oracle, hana, databricks 등)
    """
    try:
        from app.services.datacloud_service import datacloud_service
        
        conn_info = await datacloud_service.get_connection_by_id(connection_id)
        if conn_info:
            return conn_info.get("db_type", "generic").lower()
        return "generic"
    except Exception as e:
        logger.warning(f"Failed to get db_type for {connection_id}: {e}")
        return "generic"


async def get_schema(
    connection_id: str,
    include_tables: Optional[List[str]] = None,
    max_tables: int = 20
) -> Dict[str, Any]:
    """
    DB 스키마 메타데이터 조회.
    
    Args:
        connection_id: DB 연결 식별자
        include_tables: 포함할 테이블 목록 (None이면 전체)
        max_tables: 최대 테이블 수
        
    Returns:
        스키마 메타데이터
    """
    try:
        from app.services.datacloud_service import datacloud_service
        
        schema = await datacloud_service.get_schema_metadata(connection_id)
        
        if not schema or "error" in schema:
            return {"error": schema.get("error", "Failed to fetch schema")}
        
        tables = schema.get("tables", [])
        
        # 특정 테이블만 포함
        if include_tables:
            tables = [t for t in tables if t.get("name") in include_tables]
        
        # 최대 테이블 수 제한
        tables = tables[:max_tables]
        
        return {
            "tables": tables,
            "table_count": len(tables)
        }
        
    except Exception as e:
        logger.error(f"get_schema error: {e}")
        return {"error": str(e)}


async def execute_sql_safe(
    connection_id: str,
    sql: str,
    limit: int = 10,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    SQL 안전 실행 (LIMIT 추가).
    
    Args:
        connection_id: DB 연결 식별자
        sql: 실행할 SQL
        limit: 결과 제한 (기본 10행)
        dry_run: True면 실행 없이 검증만
        
    Returns:
        실행 결과 또는 에러
    """
    try:
        from app.services.datacloud_service import datacloud_service
        
        # SQL 검증 (DML/DDL 차단)
        if not _is_safe_sql(sql):
            return {
                "success": False,
                "error": "Only SELECT queries are allowed"
            }
        
        # DB 타입 조회
        db_type = await get_db_type(connection_id)
        
        # LIMIT이 없으면 DB 타입에 맞게 추가
        sql_with_limit = _ensure_limit(sql, limit, db_type)
        
        if dry_run:
            # 검증만 수행 (EXPLAIN)
            return {
                "success": True,
                "sql": sql_with_limit,
                "dry_run": True
            }
        
        # 실제 실행
        result = await datacloud_service.execute_query(
            connection_id=connection_id,
            query=sql_with_limit,
            user_id="text2sql-agent",  # Agent 실행 시 user_id
            max_rows=limit
        )
        
        if result.get("error"):
            return {
                "success": False,
                "error": result.get("error"),
                "sql": sql_with_limit
            }
        
        rows = result.get("rows", [])
        
        return {
            "success": True,
            "rows": rows,
            "row_count": len(rows),
            "sql": sql_with_limit
        }
        
    except Exception as e:
        logger.error(f"execute_sql_safe error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_sample_rows(
    connection_id: str,
    table_name: str,
    limit: int = 3
) -> Dict[str, Any]:
    """
    테이블의 샘플 데이터 조회.
    
    Args:
        connection_id: DB 연결 식별자
        table_name: 테이블 이름
        limit: 샘플 행 수
        
    Returns:
        샘플 데이터
    """
    try:
        from app.services.datacloud_service import datacloud_service
        
        # DB 타입 조회
        db_type = await get_db_type(connection_id)
        
        # DB 타입에 맞는 샘플 쿼리 생성
        sql = _build_sample_query(table_name, limit, db_type)
        
        result = await datacloud_service.execute_query(
            connection_id=connection_id,
            query=sql,
            user_id="text2sql-agent",  # Agent 실행 시 user_id
            max_rows=limit
        )
        
        if result.get("error"):
            return {"error": result.get("error")}
        
        return {
            "table": table_name,
            "rows": result.get("rows", []),
            "row_count": len(result.get("rows", []))
        }
        
    except Exception as e:
        logger.error(f"get_sample_rows error: {e}")
        return {"error": str(e)}


def _is_safe_sql(sql: str) -> bool:
    """SQL이 안전한지 검증 (SELECT만 허용)."""
    sql_upper = sql.strip().upper()
    
    # SELECT 또는 WITH (CTE)로 시작해야 함
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False
    
    # 위험한 키워드 차단
    dangerous_keywords = [
        "INSERT ", "UPDATE ", "DELETE ", "DROP ", "CREATE ",
        "ALTER ", "TRUNCATE ", "GRANT ", "REVOKE ", "EXEC ",
        "EXECUTE ", "MERGE ", "CALL "
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False
    
    return True


def _ensure_limit(sql: str, limit: int, db_type: str = "generic") -> str:
    """
    SQL에 LIMIT이 없으면 DB 타입에 맞게 추가.
    
    Args:
        sql: 원본 SQL
        limit: 행 제한
        db_type: DB 타입 (oracle은 FETCH FIRST 사용)
        
    Returns:
        LIMIT이 추가된 SQL
    """
    sql_upper = sql.strip().upper()
    
    # 이미 행 제한이 있으면 그대로 반환
    if "LIMIT " in sql_upper:
        return sql
    if "FETCH FIRST" in sql_upper or "FETCH NEXT" in sql_upper:
        return sql
    if "ROWNUM" in sql_upper:
        return sql
    
    # 세미콜론 제거
    sql = sql.rstrip(";").strip()
    
    # Oracle은 FETCH FIRST 사용
    if db_type == "oracle":
        return f"{sql} FETCH FIRST {limit} ROWS ONLY"
    
    # 나머지 DB는 LIMIT 사용
    return f"{sql} LIMIT {limit}"


def _build_sample_query(table_name: str, limit: int, db_type: str = "generic") -> str:
    """
    DB 타입에 맞는 샘플 조회 쿼리 생성.
    
    Args:
        table_name: 테이블 이름
        limit: 행 제한
        db_type: DB 타입
        
    Returns:
        샘플 조회 SQL
    """
    # 테이블명 검증
    safe_table_name = _quote_identifier(table_name)
    
    if db_type == "oracle":
        return f"SELECT * FROM {safe_table_name} FETCH FIRST {limit} ROWS ONLY"
    else:
        return f"SELECT * FROM {safe_table_name} LIMIT {limit}"


def _quote_identifier(name: str) -> str:
    """식별자 이스케이프 (간단한 버전)."""
    # SQL 인젝션 방지를 위한 기본 검증
    if not name.replace("_", "").replace(".", "").isalnum():
        raise ValueError(f"Invalid identifier: {name}")
    return name
