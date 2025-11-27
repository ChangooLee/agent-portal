"""
Data Cloud API Router

Salesforce Data Cloud 스타일의 데이터베이스 커넥터 API.
Zero Copy 방식으로 DB 스키마/메타데이터 조회 및 실시간 쿼리 실행.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.datacloud_service import datacloud_service

router = APIRouter(prefix="/datacloud", tags=["datacloud"])


# ==================== Pydantic Models ====================

class DBConnectionCreate(BaseModel):
    """DB 연결 생성 요청"""
    name: str = Field(..., description="연결 이름")
    description: Optional[str] = Field(None, description="설명")
    db_type: str = Field(..., description="DB 타입 (mariadb, postgresql, mysql, oracle, sap_hana, mssql, clickhouse)")
    host: str = Field(..., description="호스트 주소")
    port: int = Field(..., description="포트 번호")
    database_name: str = Field(..., description="데이터베이스 이름")
    username: str = Field(..., description="사용자 이름")
    password: str = Field(..., description="비밀번호")
    extra_config: Optional[Dict[str, Any]] = Field(None, description="추가 설정 (SSL, charset 등)")
    enabled: Optional[bool] = Field(True, description="활성화 여부")


class DBConnectionUpdate(BaseModel):
    """DB 연결 업데이트 요청"""
    name: Optional[str] = None
    description: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class DBConnectionResponse(BaseModel):
    """DB 연결 응답"""
    id: str
    name: str
    description: Optional[str]
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    enabled: bool
    health_status: str
    last_health_check: Optional[str]
    created_at: str
    updated_at: str


class TestConnectionResult(BaseModel):
    """연결 테스트 결과"""
    success: bool
    message: str
    latency_ms: int


class SchemaMetadataResponse(BaseModel):
    """스키마 메타데이터 응답"""
    database: Optional[str]
    db_type: Optional[str]
    tables: List[Dict[str, Any]]
    table_count: int
    from_cache: Optional[bool] = False
    refreshed_at: Optional[str] = None


class QueryRequest(BaseModel):
    """쿼리 실행 요청"""
    query: str = Field(..., description="실행할 SQL 쿼리")
    limit: Optional[int] = Field(1000, description="결과 제한 (기본 1000)")


class QueryResponse(BaseModel):
    """쿼리 실행 결과"""
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: int


class BusinessTermCreate(BaseModel):
    """비즈니스 용어 생성 요청"""
    technical_name: str = Field(..., description="기술 이름 (테이블/컬럼명)")
    technical_type: str = Field(..., description="타입 (table, column)")
    parent_table: Optional[str] = Field(None, description="부모 테이블 (컬럼인 경우)")
    business_name: str = Field(..., description="비즈니스 용어")
    description: Optional[str] = Field(None, description="설명")


class PermissionRequest(BaseModel):
    """권한 요청"""
    permission_type: str = Field(..., description="권한 타입 (user, group)")
    target_id: str = Field(..., description="대상 ID (user_id 또는 group_id)")
    permission_level: Optional[str] = Field("read", description="권한 레벨 (read, write, admin)")


# ==================== Connection CRUD Endpoints ====================

@router.get("/connections", response_model=List[DBConnectionResponse])
async def list_connections(enabled_only: bool = Query(False, description="활성화된 연결만")):
    """DB 연결 목록 조회"""
    connections = await datacloud_service.list_connections(enabled_only=enabled_only)
    return [_format_connection(c) for c in connections]


@router.post("/connections", response_model=DBConnectionResponse)
async def create_connection(data: DBConnectionCreate):
    """새 DB 연결 생성"""
    try:
        connection = await datacloud_service.create_connection(data.model_dump())
        return _format_connection(connection)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}", response_model=DBConnectionResponse)
async def get_connection(connection_id: str):
    """DB 연결 상세 조회"""
    connection = await datacloud_service.get_connection(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _format_connection(connection)


@router.put("/connections/{connection_id}", response_model=DBConnectionResponse)
async def update_connection(connection_id: str, data: DBConnectionUpdate):
    """DB 연결 업데이트"""
    connection = await datacloud_service.update_connection(
        connection_id, 
        {k: v for k, v in data.model_dump().items() if v is not None}
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _format_connection(connection)


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """DB 연결 삭제"""
    deleted = await datacloud_service.delete_connection(connection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"message": "Connection deleted successfully"}


# ==================== Connection Test ====================

@router.post("/connections/{connection_id}/test", response_model=TestConnectionResult)
async def test_connection(connection_id: str):
    """연결 테스트"""
    result = await datacloud_service.test_connection(connection_id)
    return result


@router.post("/connections/test-new", response_model=TestConnectionResult)
async def test_new_connection(data: DBConnectionCreate):
    """새 연결 테스트 (저장 전)"""
    import time
    start_time = time.time()
    
    try:
        # 임시 연결 생성
        temp_connection = {
            'id': 'temp',
            'db_type': data.db_type,
            'host': data.host,
            'port': data.port,
            'database_name': data.database_name,
            'username': data.username,
            'password_encrypted': datacloud_service.encrypt_password(data.password)
        }
        
        # SQLAlchemy 테스트
        if data.db_type == 'clickhouse':
            result = await datacloud_service._test_clickhouse_connection(temp_connection)
        else:
            result = await datacloud_service._test_sqlalchemy_connection(temp_connection)
        
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            **result,
            "latency_ms": latency_ms
        }
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "message": str(e),
            "latency_ms": latency_ms
        }


# ==================== Schema Metadata ====================

@router.get("/connections/{connection_id}/schema", response_model=SchemaMetadataResponse)
async def get_schema_metadata(
    connection_id: str,
    refresh: bool = Query(False, description="캐시 새로고침")
):
    """스키마 메타데이터 조회 (SQLAlchemy 리플렉션)"""
    try:
        schema_data = await datacloud_service.get_schema_metadata(connection_id, refresh=refresh)
        return schema_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}/tables")
async def get_tables(connection_id: str):
    """테이블 목록만 조회"""
    try:
        schema_data = await datacloud_service.get_schema_metadata(connection_id)
        return {
            "tables": [
                {
                    "name": t["name"],
                    "type": t.get("type", "table"),
                    "comment": t.get("comment"),
                    "column_count": len(t.get("columns", []))
                }
                for t in schema_data.get("tables", [])
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}/tables/{table_name}")
async def get_table_details(connection_id: str, table_name: str):
    """테이블 상세 정보 조회"""
    try:
        schema_data = await datacloud_service.get_schema_metadata(connection_id)
        for table in schema_data.get("tables", []):
            if table["name"] == table_name:
                return table
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Query Execution ====================

@router.post("/connections/{connection_id}/query", response_model=QueryResponse)
async def execute_query(
    connection_id: str,
    request: QueryRequest,
    user_id: str = Query("anonymous", description="사용자 ID")
):
    """쿼리 실행 (Zero Copy - 실시간)"""
    try:
        result = await datacloud_service.execute_query(
            connection_id,
            request.query,
            user_id,
            limit=request.limit or 1000
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Business Terms ====================

@router.get("/connections/{connection_id}/terms")
async def get_business_terms(connection_id: str):
    """비즈니스 용어 목록 조회"""
    terms = await datacloud_service.get_business_terms(connection_id)
    return {"terms": terms}


@router.post("/connections/{connection_id}/terms")
async def add_business_term(connection_id: str, data: BusinessTermCreate):
    """비즈니스 용어 추가"""
    try:
        result = await datacloud_service.add_business_term(
            connection_id,
            data.technical_name,
            data.technical_type,
            data.business_name,
            parent_table=data.parent_table,
            description=data.description
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Permissions ====================

@router.post("/connections/{connection_id}/permissions")
async def grant_permission(
    connection_id: str,
    data: PermissionRequest,
    granted_by: str = Query("admin", description="권한 부여자")
):
    """권한 부여"""
    try:
        result = await datacloud_service.grant_permission(
            connection_id,
            data.permission_type,
            data.target_id,
            data.permission_level or 'read',
            granted_by
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================

def _format_connection(connection: Dict[str, Any]) -> Dict[str, Any]:
    """연결 정보 포맷팅"""
    return {
        "id": connection["id"],
        "name": connection["name"],
        "description": connection.get("description"),
        "db_type": connection["db_type"],
        "host": connection["host"],
        "port": connection["port"],
        "database_name": connection["database_name"],
        "username": connection["username"],
        "enabled": connection.get("enabled", True),
        "health_status": connection.get("health_status", "unknown"),
        "last_health_check": str(connection["last_health_check"]) if connection.get("last_health_check") else None,
        "created_at": str(connection["created_at"]),
        "updated_at": str(connection["updated_at"])
    }

