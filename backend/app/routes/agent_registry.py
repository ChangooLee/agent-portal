"""
Agent Registry API Routes

에이전트 등록, 조회, 트레이스 시작/종료 API.
Langflow, Flowise, Text2SQL, AutoGen 등 모든 에이전트가 사용.
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Query

from app.services.agent_registry_service import (
    agent_registry, AgentType, AgentStatus
)
from app.services.agent_trace_adapter import agent_trace_adapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agent-registry"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AgentRegisterRequest(BaseModel):
    """에이전트 등록 요청"""
    name: str = Field(..., description="에이전트 이름")
    type: str = Field(..., description="에이전트 유형 (text2sql, langflow, flowise, custom)")
    project_id: str = Field("default-project", description="프로젝트 ID")
    external_id: Optional[str] = Field(None, description="외부 시스템 ID (flow_id 등)")
    description: Optional[str] = Field(None, description="설명")
    config: Optional[Dict[str, Any]] = Field(None, description="에이전트 설정")


class AgentResponse(BaseModel):
    """에이전트 응답"""
    id: str
    name: str
    type: str
    project_id: str
    external_id: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    monitoring_enabled: bool = True
    status: str = "active"
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None


class AgentListResponse(BaseModel):
    """에이전트 목록 응답"""
    agents: List[AgentResponse]
    total: int


class TraceStartRequest(BaseModel):
    """트레이스 시작 요청"""
    inputs: Optional[Dict[str, Any]] = Field(None, description="입력 데이터")
    tags: Optional[List[str]] = Field(None, description="태그")


class TraceStartResponse(BaseModel):
    """트레이스 시작 응답"""
    trace_id: str
    agent_id: str
    agent_name: str


class TraceEndRequest(BaseModel):
    """트레이스 종료 요청"""
    trace_id: str = Field(..., description="트레이스 ID")
    outputs: Optional[Dict[str, Any]] = Field(None, description="출력 데이터")
    error: Optional[str] = Field(None, description="에러 메시지")
    cost: float = Field(0.0, description="총 비용")
    tokens: int = Field(0, description="총 토큰 수")


class TraceEndResponse(BaseModel):
    """트레이스 종료 응답"""
    success: bool
    trace_id: str
    duration_ms: Optional[float] = None


class AgentUpdateRequest(BaseModel):
    """에이전트 업데이트 요청"""
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    monitoring_enabled: Optional[bool] = None
    status: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/register", response_model=AgentResponse)
async def register_agent(request: AgentRegisterRequest):
    """
    에이전트 등록 또는 기존 에이전트 조회.
    
    동일한 name + project_id가 있으면 기존 에이전트 반환.
    Langflow, Flowise, Text2SQL 등이 첫 실행 시 자동 호출.
    """
    try:
        agent_type = AgentType(request.type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent type: {request.type}. "
                   f"Valid types: {[t.value for t in AgentType]}"
        )
    
    try:
        agent = await agent_registry.register_or_get(
            name=request.name,
            agent_type=agent_type,
            project_id=request.project_id,
            external_id=request.external_id,
            description=request.description,
            config=request.config
        )
        return AgentResponse(**agent)
    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=AgentListResponse)
async def list_agents(
    project_id: Optional[str] = Query(None, description="프로젝트 ID 필터"),
    type: Optional[str] = Query(None, description="에이전트 유형 필터"),
    status: Optional[str] = Query(None, description="상태 필터 (active/inactive)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """에이전트 목록 조회"""
    try:
        agent_type = AgentType(type) if type else None
    except ValueError:
        agent_type = None
    
    try:
        agent_status = AgentStatus(status) if status else None
    except ValueError:
        agent_status = None
    
    try:
        agents = await agent_registry.list_agents(
            project_id=project_id,
            agent_type=agent_type,
            status=agent_status,
            limit=limit,
            offset=offset
        )
        
        total = await agent_registry.get_agent_count(
            project_id=project_id,
            agent_type=agent_type
        )
        
        return AgentListResponse(
            agents=[AgentResponse(**a) for a in agents],
            total=total
        )
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """에이전트 상세 조회"""
    agent = await agent_registry.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, request: AgentUpdateRequest):
    """에이전트 정보 업데이트"""
    try:
        status = AgentStatus(request.status) if request.status else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    agent = await agent_registry.update_agent(
        agent_id=agent_id,
        description=request.description,
        config=request.config,
        monitoring_enabled=request.monitoring_enabled,
        status=status
    )
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse(**agent)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """에이전트 삭제 (soft delete)"""
    success = await agent_registry.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "message": f"Agent {agent_id} deactivated"}


@router.post("/{agent_id}/trace/start", response_model=TraceStartResponse)
async def start_trace(agent_id: str, request: TraceStartRequest):
    """
    에이전트 트레이스 시작.
    
    반환된 trace_id를 LLM 호출 시 metadata.parent_trace_id로 전달하면
    에이전트 트레이스와 LLM 트레이스가 연결됨.
    """
    agent = await agent_registry.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.get('monitoring_enabled', True):
        raise HTTPException(
            status_code=400, 
            detail="Monitoring is disabled for this agent"
        )
    
    trace_id = await agent_trace_adapter.start_trace(
        agent_id=agent_id,
        agent_name=agent['name'],
        agent_type=agent['type'],
        project_id=agent['project_id'],
        inputs=request.inputs,
        tags=request.tags
    )
    
    # last_used_at 업데이트
    await agent_registry.update_last_used(agent_id)
    
    return TraceStartResponse(
        trace_id=trace_id,
        agent_id=agent_id,
        agent_name=agent['name']
    )


@router.post("/{agent_id}/trace/end", response_model=TraceEndResponse)
async def end_trace(agent_id: str, request: TraceEndRequest):
    """에이전트 트레이스 종료"""
    # 활성 트레이스 확인
    active_trace = agent_trace_adapter.get_active_trace(request.trace_id)
    if not active_trace:
        raise HTTPException(
            status_code=404,
            detail=f"Active trace not found: {request.trace_id}"
        )
    
    if active_trace['agent_id'] != agent_id:
        raise HTTPException(
            status_code=400,
            detail="Trace does not belong to this agent"
        )
    
    success = await agent_trace_adapter.end_trace(
        trace_id=request.trace_id,
        outputs=request.outputs,
        error=request.error,
        cost=request.cost,
        tokens=request.tokens
    )
    
    return TraceEndResponse(
        success=success,
        trace_id=request.trace_id
    )


@router.get("/stats/summary")
async def get_agent_stats_summary(
    project_id: Optional[str] = Query(None, description="프로젝트 ID")
):
    """에이전트 통계 요약"""
    try:
        total = await agent_registry.get_agent_count(project_id=project_id)
        
        # 유형별 카운트
        type_counts = {}
        for agent_type in AgentType:
            count = await agent_registry.get_agent_count(
                project_id=project_id,
                agent_type=agent_type
            )
            if count > 0:
                type_counts[agent_type.value] = count
        
        return {
            "total_agents": total,
            "active_traces": agent_trace_adapter.get_active_traces_count(),
            "by_type": type_counts
        }
    except Exception as e:
        logger.error(f"Failed to get agent stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

