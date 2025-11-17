"""Agents API routes - Langflow/Flowise/AutoGen flow management"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Literal
import httpx

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Langflow internal URL (Docker service name)
LANGFLOW_BASE_URL = "http://langflow:7860"


@router.get("/flows")
async def get_flows(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Number of flows to return"),
    search: str = Query("", description="Search query for flow name/description")
) -> Dict[str, Any]:
    """Get flows list from Langflow.
    
    Proxies Langflow's /api/v1/flows endpoint to retrieve flow list with pagination.
    
    Args:
        offset: Starting index for pagination
        limit: Number of flows to return
        search: Search query for filtering flows
        
    Returns:
        Flows list with pagination info from Langflow
        
    Raises:
        HTTPException: 504 for timeout, 502 for Langflow errors, 500 for unexpected errors
    """
    try:
        params = {
            "skip": offset,
            "limit": limit
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{LANGFLOW_BASE_URL}/api/v1/flows/",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            # Apply search filter if provided
            flows = data if isinstance(data, list) else data.get("flows", [])
            
            if search:
                search_lower = search.lower()
                flows = [
                    flow for flow in flows
                    if search_lower in flow.get("name", "").lower() or
                       search_lower in flow.get("description", "").lower()
                ]
            
            # Return paginated results
            total = len(flows)
            paginated_flows = flows[offset:offset + limit] if search else flows
            
            return {
                "flows": paginated_flows,
                "total": total,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total
            }
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Langflow API timeout"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Langflow API error: {e.response.status_code} - {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch flows: {str(e)}"
        )


@router.get("/flows/{flow_id}")
async def get_flow_detail(flow_id: str) -> Dict[str, Any]:
    """Get flow detail by ID from Langflow.
    
    Proxies Langflow's /api/v1/flows/{flow_id} endpoint.
    
    Args:
        flow_id: Flow UUID
        
    Returns:
        Flow detail with complete JSON data
        
    Raises:
        HTTPException: 404 if flow not found, 504 for timeout, 502 for Langflow errors
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{LANGFLOW_BASE_URL}/api/v1/flows/{flow_id}"
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Langflow API timeout"
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Flow {flow_id} not found"
            )
        raise HTTPException(
            status_code=502,
            detail=f"Langflow API error: {e.response.status_code} - {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch flow detail: {str(e)}"
        )


@router.delete("/flows/{flow_id}")
async def delete_flow(flow_id: str) -> Dict[str, Any]:
    """Delete flow by ID from Langflow.
    
    Proxies Langflow's DELETE /api/v1/flows/{flow_id} endpoint.
    
    Args:
        flow_id: Flow UUID to delete
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 404 if flow not found, 504 for timeout, 502 for Langflow errors
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{LANGFLOW_BASE_URL}/api/v1/flows/{flow_id}"
            )
            response.raise_for_status()
            return {"success": True, "message": f"Flow {flow_id} deleted successfully"}
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Langflow API timeout"
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Flow {flow_id} not found"
            )
        raise HTTPException(
            status_code=502,
            detail=f"Langflow API error: {e.response.status_code} - {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete flow: {str(e)}"
        )

