"""Observability API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from app.services.litellm_service import litellm_service
from app.services.langfuse_service import langfuse_service
import httpx
from app.config import get_settings

router = APIRouter(prefix="/observability", tags=["observability"])
settings = get_settings()


@router.get("/usage")
async def get_usage_summary(project_id: Optional[str] = Query(None)):
    """Get usage summary from observability tools"""
    try:
        # Get Langfuse summary
        langfuse_summary = await langfuse_service.get_usage_summary(project_id)
        
        # Try to get Helicone summary
        helicone_summary = await get_helicone_summary()
        
        return {
            "langfuse": langfuse_summary,
            "helicone": helicone_summary,
            "status": "ok"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_helicone_summary() -> Dict[str, Any]:
    """Get summary from Helicone"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Helicone API endpoint - adjust based on actual API
            url = f"{settings.HELICONE_INTERNAL_URL}/api/v1/metrics"
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "error": "Helicone API not available"
                }
    except Exception as e:
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "error": str(e)
        }


@router.get("/models")
async def get_models():
    """Get available models from LiteLLM"""
    try:
        models_data = await litellm_service.list_models()
        return {
            "models": models_data.get("data", []),
            "status": "ok"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def observability_health():
    """Health check for observability services"""
    checks = {
        "litellm": False,
        "langfuse": False,
        "helicone": False
    }
    
    # Check LiteLLM
    try:
        await litellm_service.list_models()
        checks["litellm"] = True
    except:
        pass
    
    # Check Langfuse
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.LANGFUSE_INTERNAL_URL}/api/public/health")
            if response.status_code == 200:
                checks["langfuse"] = True
    except:
        pass
    
    # Check Helicone
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.HELICONE_INTERNAL_URL}/health")
            if response.status_code == 200:
                checks["helicone"] = True
    except:
        pass
    
    return {
        "status": "ok" if any(checks.values()) else "degraded",
        "services": checks
    }
