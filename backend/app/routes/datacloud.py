"""
Data Cloud API Router - Zero Copy 데이터베이스 커넥터 API

Salesforce Data Cloud 스타일의 데이터베이스 연결 관리 API.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.datacloud_service import datacloud_service

router = APIRouter(prefix="/datacloud", tags=["datacloud"])


# =====================
# Pydantic Models
# =====================

class ConnectionCreateRequest(BaseModel):
    """DB 연결 생성 요청"""
    name: str = Field(..., description="연결 이름")
    db_type: str = Field(..., description="DB 타입 (mariadb, postgresql, mysql, clickhouse)")
    host: str = Field(..., description="호스트 주소")
    port: int = Field(..., description="포트 번호")
    database_name: str = Field(..., description="데이터베이스 이름")
    username: str = Field(..., description="사용자 이름")
    password: str = Field(..., description="비밀번호")
    description: Optional[str] = Field(None, description="설명")
    extra_config: Optional[Dict[str, Any]] = Field(None, description="추가 설정 (SSL 등)")
    register_kong: bool = Field(True, description="Kong Gateway 등록 여부")


class ConnectionUpdateRequest(BaseModel):
    """DB 연결 수정 요청"""
    name: Optional[str] = None
    description: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class ConnectionResponse(BaseModel):
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
    created_at: Optional[str]
    updated_at: Optional[str]
    extra_config: Optional[Dict[str, Any]]


class ConnectionTestResult(BaseModel):
    """연결 테스트 결과"""
    success: bool
    latency_ms: Optional[int]
    server_version: Optional[str]
    error: Optional[str]
    health_status: str


class QueryRequest(BaseModel):
    """쿼리 실행 요청"""
    query: str = Field(..., description="SQL 쿼리")
    max_rows: int = Field(1000, description="최대 반환 행 수")


class QueryResult(BaseModel):
    """쿼리 실행 결과"""
    success: bool
    columns: List[str]
    rows: List[Dict[str, Any]]
    rows_affected: int
    execution_time_ms: int
    error: Optional[str]


class BusinessTermRequest(BaseModel):
    """비즈니스 용어 추가 요청"""
    term_type: str = Field(..., description="용어 타입 (table, column)")
    technical_name: str = Field(..., description="기술명")
    business_name: str = Field(..., description="비즈니스명")
    schema_name: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    description: Optional[str] = None
    examples: Optional[str] = None


class PermissionRequest(BaseModel):
    """권한 부여 요청"""
    permission_type: str = Field(..., description="권한 타입 (user, group)")
    target_id: str = Field(..., description="대상 ID")
    access_level: str = Field("read", description="접근 수준 (read, write, admin)")


# =====================
# Connection CRUD
# =====================

@router.get("/connections", response_model=List[ConnectionResponse])
async def list_connections(
    include_disabled: bool = Query(False, description="비활성 연결 포함 여부")
):
    """모든 DB 연결 목록 조회"""
    connections = await datacloud_service.list_connections(include_disabled)
    return connections


@router.post("/connections", response_model=ConnectionResponse)
async def create_connection(request: ConnectionCreateRequest):
    """새 DB 연결 생성"""
    try:
        result = await datacloud_service.create_connection(
            name=request.name,
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database_name=request.database_name,
            username=request.username,
            password=request.password,
            description=request.description,
            extra_config=request.extra_config,
            register_kong=request.register_kong
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
async def get_connection(connection_id: str):
    """특정 DB 연결 조회"""
    conn = await datacloud_service.get_connection_by_id(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # 비밀번호 제외
    conn.pop('password_encrypted', None)
    return conn


@router.put("/connections/{connection_id}")
async def update_connection(connection_id: str, request: ConnectionUpdateRequest):
    """DB 연결 수정"""
    success = await datacloud_service.update_connection(
        connection_id=connection_id,
        name=request.name,
        description=request.description,
        host=request.host,
        port=request.port,
        database_name=request.database_name,
        username=request.username,
        password=request.password,
        extra_config=request.extra_config,
        enabled=request.enabled
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Connection not found or no changes")
    
    return {"success": True, "message": "Connection updated"}


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """DB 연결 삭제"""
    success = await datacloud_service.delete_connection(connection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return {"success": True, "message": "Connection deleted"}


# =====================
# Connection Test
# =====================

@router.post("/connections/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(connection_id: str):
    """DB 연결 테스트"""
    result = await datacloud_service.test_connection(connection_id)
    return result


# =====================
# Schema Metadata
# =====================

@router.get("/connections/{connection_id}/schema")
async def get_schema(
    connection_id: str,
    refresh: bool = Query(False, description="캐시 무시하고 새로 조회")
):
    """DB 스키마 메타데이터 조회"""
    result = await datacloud_service.get_schema_metadata(connection_id, refresh)
    
    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])
    
    return result


# =====================
# Query Execution
# =====================

@router.post("/connections/{connection_id}/query", response_model=QueryResult)
async def execute_query(
    connection_id: str,
    request: QueryRequest,
    user_id: str = Query("anonymous", description="실행 사용자 ID")
):
    """SQL 쿼리 실행 (Zero Copy)"""
    result = await datacloud_service.execute_query(
        connection_id=connection_id,
        query=request.query,
        user_id=user_id,
        max_rows=request.max_rows
    )
    return result


# =====================
# Business Terms
# =====================

@router.get("/connections/{connection_id}/terms")
async def get_business_terms(connection_id: str):
    """비즈니스 용어집 조회"""
    terms = await datacloud_service.get_business_terms(connection_id)
    return {"terms": terms}


@router.post("/connections/{connection_id}/terms")
async def add_business_term(connection_id: str, request: BusinessTermRequest):
    """비즈니스 용어 추가"""
    result = await datacloud_service.add_business_term(
        connection_id=connection_id,
        term_type=request.term_type,
        technical_name=request.technical_name,
        business_name=request.business_name,
        schema_name=request.schema_name,
        table_name=request.table_name,
        column_name=request.column_name,
        description=request.description,
        examples=request.examples
    )
    return result


# =====================
# Permissions
# =====================

@router.get("/connections/{connection_id}/permissions")
async def get_permissions(connection_id: str):
    """연결 권한 목록 조회"""
    permissions = await datacloud_service.get_connection_permissions(connection_id)
    return {"permissions": permissions}


@router.post("/connections/{connection_id}/permissions")
async def grant_permission(
    connection_id: str,
    request: PermissionRequest,
    granted_by: str = Query("admin", description="권한 부여자 ID")
):
    """권한 부여"""
    result = await datacloud_service.grant_permission(
        connection_id=connection_id,
        permission_type=request.permission_type,
        target_id=request.target_id,
        access_level=request.access_level,
        granted_by=granted_by
    )
    return result


@router.delete("/permissions/{permission_id}")
async def revoke_permission(permission_id: str):
    """권한 회수"""
    success = await datacloud_service.revoke_permission(permission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    return {"success": True, "message": "Permission revoked"}


# =====================
# Statistics
# =====================

@router.get("/stats")
async def get_stats():
    """Data Cloud 통계"""
    connections = await datacloud_service.list_connections(include_disabled=True)
    
    total = len(connections)
    enabled = sum(1 for c in connections if c.get('enabled'))
    healthy = sum(1 for c in connections if c.get('health_status') == 'healthy')
    
    db_types = {}
    for c in connections:
        db_type = c.get('db_type', 'unknown')
        db_types[db_type] = db_types.get(db_type, 0) + 1
    
    return {
        "total_connections": total,
        "enabled_connections": enabled,
        "healthy_connections": healthy,
        "by_db_type": db_types
    }
