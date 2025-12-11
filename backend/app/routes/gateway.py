"""
Gateway Management API

Kong Gateway 관리 API 엔드포인트.
Services, Consumers, Routes, Plugins 목록 조회 및 상태 확인.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.kong_service import kong_service
from app.services.mcp_service import mcp_service
from app.services.datacloud_service import datacloud_service


router = APIRouter(prefix="/gateway", tags=["gateway"])
api_router = APIRouter(prefix="/api/gateway", tags=["gateway"])


# ==================== Response 모델 ====================

class KongServiceResponse(BaseModel):
    """Kong Service 응답."""
    id: str
    name: str
    host: Optional[str] = None
    port: Optional[int] = None
    path: Optional[str] = None
    protocol: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    plugins: Optional[List[str]] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class KongConsumerResponse(BaseModel):
    """Kong Consumer 응답."""
    id: str
    username: str
    custom_id: Optional[str] = None
    tags: Optional[List[str]] = None
    api_keys: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[int] = None


class KongRouteResponse(BaseModel):
    """Kong Route 응답."""
    id: str
    name: Optional[str] = None
    paths: Optional[List[str]] = None
    methods: Optional[List[str]] = None
    protocols: Optional[List[str]] = None
    service: Optional[Dict[str, Any]] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class KongPluginResponse(BaseModel):
    """Kong Plugin 응답."""
    id: str
    name: str
    enabled: bool
    service: Optional[Dict[str, Any]] = None
    route: Optional[Dict[str, Any]] = None
    consumer: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    created_at: Optional[int] = None


class GatewayStatusResponse(BaseModel):
    """Gateway 상태 응답."""
    status: str
    kong_status: Dict[str, Any]
    services_count: int
    consumers_count: int
    routes_count: int
    plugins_count: int


class GatewayOverviewResponse(BaseModel):
    """Gateway 개요 응답."""
    services: List[Dict[str, Any]]
    consumers: List[Dict[str, Any]]
    mcp_servers: List[Dict[str, Any]]
    datacloud_connections: List[Dict[str, Any]]
    stats: Dict[str, int]


# ==================== API 엔드포인트 ====================

@router.get("/status", response_model=GatewayStatusResponse)
@api_router.get("/status", response_model=GatewayStatusResponse)
async def get_gateway_status():
    """Kong Gateway 상태 조회.
    
    Returns:
        Gateway 상태 정보 (Kong 상태, 리소스 수)
    """
    # Kong 상태 확인
    kong_status = await kong_service.health_check()
    
    # 리소스 수 조회
    try:
        services = await kong_service.list_services()
        services_count = len(services)
    except:
        services_count = 0
    
    try:
        consumers = await kong_service.list_all_consumers()
        consumers_count = len(consumers)
    except:
        consumers_count = 0
    
    try:
        routes = await kong_service.list_routes()
        routes_count = len(routes)
    except:
        routes_count = 0
    
    try:
        plugins = await kong_service.list_all_plugins()
        plugins_count = len(plugins)
    except:
        plugins_count = 0
    
    return GatewayStatusResponse(
        status=kong_status.get("status", "unknown"),
        kong_status=kong_status,
        services_count=services_count,
        consumers_count=consumers_count,
        routes_count=routes_count,
        plugins_count=plugins_count
    )


@router.get("/overview", response_model=GatewayOverviewResponse)
@api_router.get("/overview", response_model=GatewayOverviewResponse)
async def get_gateway_overview():
    """Gateway 개요 조회.
    
    Kong Services, Consumers, MCP Servers를 한 번에 조회합니다.
    
    Returns:
        Gateway 개요 정보
    """
    # Kong Services 조회
    try:
        services = await kong_service.list_services()
    except Exception as e:
        services = []
    
    # Kong Consumers 조회 (API Key 마스킹)
    try:
        consumers = await kong_service.list_all_consumers()
    except Exception as e:
        consumers = []
    
    # MCP Servers 조회
    try:
        mcp_result = await mcp_service.list_servers(page=1, size=100)
        mcp_servers = mcp_result.get("servers", [])
    except Exception as e:
        mcp_servers = []
    
    # Data Cloud Connections 조회
    try:
        datacloud_connections = await datacloud_service.list_connections()
    except Exception as e:
        datacloud_connections = []
    
    # 통계
    healthy_datacloud = len([c for c in datacloud_connections if c.get("health_status") == "healthy"])
    stats = {
        "services_count": len(services),
        "consumers_count": len(consumers),
        "mcp_servers_count": len(mcp_servers),
        "active_mcp_count": len([s for s in mcp_servers if s.get("enabled")]),
        "datacloud_count": len(datacloud_connections),
        "datacloud_healthy_count": healthy_datacloud
    }
    
    return GatewayOverviewResponse(
        services=services,
        consumers=consumers,
        mcp_servers=mcp_servers,
        datacloud_connections=datacloud_connections,
        stats=stats
    )


@router.get("/services", response_model=List[Dict[str, Any]])
@api_router.get("/services", response_model=List[Dict[str, Any]])
async def list_kong_services():
    """Kong Services 목록 조회.
    
    Returns:
        Kong Service 목록 (플러그인 정보 포함)
    """
    try:
        services = await kong_service.list_services()
        return services
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Kong services: {str(e)}"
        )


@router.get("/consumers", response_model=List[Dict[str, Any]])
@api_router.get("/consumers", response_model=List[Dict[str, Any]])
async def list_kong_consumers():
    """Kong Consumers 목록 조회.
    
    API Key는 마스킹 처리됩니다.
    
    Returns:
        Kong Consumer 목록 (API Key 마스킹)
    """
    try:
        consumers = await kong_service.list_all_consumers()
        return consumers
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Kong consumers: {str(e)}"
        )


@router.get("/routes", response_model=List[Dict[str, Any]])
@api_router.get("/routes", response_model=List[Dict[str, Any]])
async def list_kong_routes():
    """Kong Routes 목록 조회.
    
    Returns:
        Kong Route 목록
    """
    try:
        routes = await kong_service.list_routes()
        return routes
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Kong routes: {str(e)}"
        )


@router.get("/plugins", response_model=List[Dict[str, Any]])
@api_router.get("/plugins", response_model=List[Dict[str, Any]])
async def list_kong_plugins():
    """Kong Plugins 목록 조회.
    
    Returns:
        Kong Plugin 목록
    """
    try:
        plugins = await kong_service.list_all_plugins()
        return plugins
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Kong plugins: {str(e)}"
        )


