"""Observability API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from app.services.litellm_service import litellm_service
from app.config import get_settings

router = APIRouter(prefix="/observability", tags=["observability"])
settings = get_settings()


@router.get("/usage")
async def get_usage_summary(project_id: Optional[str] = Query(None)):
    """Get usage summary from observability tools (LiteLLM only)"""
    try:
        # LiteLLM usage (OTEL → ClickHouse 기반 모니터링)
        return {
            "litellm": {"status": "active"},
            "status": "ok"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        "litellm": False
    }
    
    # Check LiteLLM
    try:
        await litellm_service.list_models()
        checks["litellm"] = True
    except:
        pass
    
    return {
        "status": "ok" if any(checks.values()) else "degraded",
        "services": checks
    }
