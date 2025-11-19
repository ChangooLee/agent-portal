"""
AgentOps API Routes

AgentOps 대시보드 호환 API 엔드포인트.
로컬 MariaDB 기반, API 키 불필요.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from app.services.agentops_adapter import agentops_adapter

router = APIRouter(prefix="/api/agentops", tags=["AgentOps"])


@router.get("/traces")
async def get_traces(
    project_id: str = Query(..., description="Project ID"),
    start_time: datetime = Query(..., description="Start time (ISO 8601)"),
    end_time: datetime = Query(..., description="End time (ISO 8601)"),
    search: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size")
):
    """
    트레이스 목록 조회 (AgentOps API 호환).
    
    Returns:
        {
            "traces": [...],
            "total": int,
            "page": int,
            "size": int
        }
    """
    try:
        result = await agentops_adapter.get_traces(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
            search=search,
            page=page,
            size=size
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch traces: {str(e)}")


@router.get("/traces/{trace_id}")
async def get_trace_detail(trace_id: str):
    """
    트레이스 상세 조회 (AgentOps API 호환).
    
    Returns:
        {
            "trace_id": str,
            "project_id": str,
            "spans": [...]
        }
    """
    try:
        result = await agentops_adapter.get_trace_detail(trace_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trace detail: {str(e)}")


@router.get("/metrics")
async def get_metrics(
    project_id: str = Query(..., description="Project ID"),
    start_time: datetime = Query(..., description="Start time (ISO 8601)"),
    end_time: datetime = Query(..., description="End time (ISO 8601)")
):
    """
    메트릭 집계 조회 (AgentOps API 호환).
    
    Returns:
        {
            "trace_count": int,
            "span_count": int,
            "error_count": int,
            "total_cost": float,
            "prompt_tokens": int,
            "completion_tokens": int,
            "cache_read_input_tokens": int,
            "reasoning_tokens": int,
            "avg_duration": float,
            "p50_duration": float,
            "p95_duration": float,
            "p99_duration": float
        }
    """
    try:
        result = await agentops_adapter.get_metrics(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")


@router.get("/replay/{trace_id}")
async def get_session_replay(trace_id: str):
    """
    세션 리플레이 데이터 조회.
    스팬을 시간순 이벤트로 변환하여 반환.
    
    Returns:
        {
            "trace_id": str,
            "events": [...],
            "timeline": [...],
            "total_duration": int,
            "start_time": int
        }
    """
    try:
        result = await agentops_adapter.get_session_replay(trace_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch session replay: {str(e)}")


@router.get("/timeline/{trace_id}")
async def get_trace_timeline(trace_id: str):
    """
    트레이스 타임라인 조회 (계층 구조 포함).
    
    Returns:
        {
            "trace_id": str,
            "spans": [...],
            "total_duration": int,
            "critical_path": [...],
            "start_time": int,
            "end_time": int
        }
    """
    try:
        result = await agentops_adapter.get_trace_timeline(trace_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trace timeline: {str(e)}")


@router.get("/analytics/cost-trend")
async def get_cost_trend(
    project_id: str = Query(..., description="Project ID"),
    start_time: datetime = Query(..., description="Start time (ISO 8601)"),
    end_time: datetime = Query(..., description="End time (ISO 8601)"),
    interval: str = Query("day", description="Time interval (hour/day/week)")
):
    """
    비용 추이 데이터 조회.
    
    Returns:
        [
            {
                "timestamp": str,
                "cost": float
            },
            ...
        ]
    """
    try:
        result = await agentops_adapter.get_cost_trend(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cost trend: {str(e)}")


@router.get("/analytics/token-usage")
async def get_token_usage(
    project_id: str = Query(..., description="Project ID"),
    start_time: datetime = Query(..., description="Start time (ISO 8601)"),
    end_time: datetime = Query(..., description="End time (ISO 8601)"),
    interval: str = Query("day", description="Time interval (hour/day/week)")
):
    """
    토큰 사용량 추이 조회.
    
    Returns:
        [
            {
                "timestamp": str,
                "prompt_tokens": int,
                "completion_tokens": int,
                "cache_hits": int
            },
            ...
        ]
    """
    try:
        result = await agentops_adapter.get_token_usage(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch token usage: {str(e)}")


@router.get("/analytics/performance")
async def get_performance_metrics(
    project_id: str = Query(..., description="Project ID"),
    start_time: datetime = Query(..., description="Start time (ISO 8601)"),
    end_time: datetime = Query(..., description="End time (ISO 8601)")
):
    """
    성능 메트릭 조회 (레이턴시 분포).
    
    Returns:
        [
            {
                "timestamp": str,
                "duration": int,
                "status": str
            },
            ...
        ]
    """
    try:
        result = await agentops_adapter.get_performance_metrics(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance metrics: {str(e)}")


@router.get("/analytics/agent-flow")
async def get_agent_flow_graph(
    project_id: str = Query(..., description="Project ID"),
    trace_id: Optional[str] = Query(None, description="Specific trace ID"),
    start_time: Optional[datetime] = Query(None, description="Start time (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO 8601)")
):
    """
    에이전트 플로우 그래프 조회.
    
    Returns:
        {
            "nodes": [...],
            "edges": [...]
        }
    """
    try:
        result = await agentops_adapter.get_agent_flow_graph(
            project_id=project_id,
            trace_id=trace_id,
            start_time=start_time,
            end_time=end_time
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch agent flow graph: {str(e)}")


@router.get("/agents/usage")
async def get_agent_usage_stats(
    project_id: str = Query(..., description="Project ID"),
    start_time: datetime = Query(..., description="Start time (ISO 8601)"),
    end_time: datetime = Query(..., description="End time (ISO 8601)")
):
    """
    에이전트별 사용량 통계 조회.
    
    Returns:
        [{
            "agent_name": str,
            "total_tokens": int,
            "total_cost": float,
            "event_count": int,
            "avg_latency": float,
            "error_count": int,
            "success_rate": float
        }]
    """
    try:
        result = await agentops_adapter.get_agent_usage_stats(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch agent usage stats: {str(e)}")

