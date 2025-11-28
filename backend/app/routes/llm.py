"""LLM Management API Routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.llm_management_service import (
    llm_management_service,
    AddModelRequest,
    UpdateModelRequest,
    LiteLLMParams,
    ModelInfo
)

router = APIRouter(prefix="/llm", tags=["LLM Management"])


# Request/Response models for API documentation
class ProviderResponse(BaseModel):
    """LLM Provider information"""
    id: str
    name: str
    description: str
    color: str
    prefix: str
    requires_api_key: bool
    default_api_base: Optional[str] = None
    requires_api_version: Optional[bool] = None
    custom_llm_provider: Optional[str] = None


class ModelResponse(BaseModel):
    """LLM Model information"""
    model_id: Optional[str] = None
    model_name: str
    provider: str
    model: str
    api_base: Optional[str] = None
    max_tokens: Optional[int] = None
    input_cost_per_token: Optional[float] = None
    output_cost_per_token: Optional[float] = None
    mode: Optional[str] = None
    db_model: bool = False


class TestModelResponse(BaseModel):
    """Model test result"""
    success: bool
    model: str
    response: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class AddModelRequestBody(BaseModel):
    """Request body for adding a new model"""
    model_name: str = Field(..., description="Display name for the model (e.g., 'GPT-4 Turbo')")
    litellm_params: LiteLLMParams = Field(..., description="LiteLLM parameters")
    model_info: Optional[ModelInfo] = Field(None, description="Optional model metadata")


class UpdateModelRequestBody(BaseModel):
    """Request body for updating a model"""
    model_name: Optional[str] = Field(None, description="New display name")
    litellm_params: Optional[LiteLLMParams] = Field(None, description="Updated LiteLLM parameters")
    model_info: Optional[ModelInfo] = Field(None, description="Updated model metadata")


@router.get("/providers", response_model=List[ProviderResponse])
async def get_providers():
    """
    Get list of supported LLM providers.
    
    Returns a list of all LLM providers that can be configured,
    including their required parameters and default values.
    """
    try:
        providers = await llm_management_service.get_providers()
        return providers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(
    provider: Optional[str] = Query(None, description="Filter by provider ID")
):
    """
    Get list of all configured LLM models.
    
    Returns models from both config file and database.
    Use the provider parameter to filter by specific provider.
    """
    try:
        models = await llm_management_service.list_models()
        
        # Filter by provider if specified
        if provider:
            models = [m for m in models if m.get("provider") == provider]
        
        return {"models": models, "total": len(models)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}")
async def get_model(model_id: str):
    """
    Get details of a specific model.
    
    Returns full model configuration including litellm_params.
    """
    try:
        model = await llm_management_service.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
        return model
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models")
async def add_model(request: AddModelRequestBody):
    """
    Add a new LLM model.
    
    Creates a new model configuration in the LiteLLM database.
    The model will be immediately available for use via the LLM gateway.
    
    **Important**: Use official model names from providers.
    For example: `openrouter/qwen/qwen3-235b-a22b-2507` not just `qwen`.
    """
    try:
        # Convert to internal request format
        add_request = AddModelRequest(
            model_name=request.model_name,
            litellm_params=request.litellm_params,
            model_info=request.model_info
        )
        result = await llm_management_service.add_model(add_request)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/models/{model_id}")
async def update_model(model_id: str, request: UpdateModelRequestBody):
    """
    Update an existing model.
    
    Modifies model configuration in the LiteLLM database.
    Only DB-stored models can be updated; config file models cannot be modified.
    """
    try:
        # Convert to internal request format
        update_request = UpdateModelRequest(
            model_name=request.model_name,
            litellm_params=request.litellm_params,
            model_info=request.model_info
        )
        result = await llm_management_service.update_model(model_id, update_request)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    """
    Delete a model.
    
    Removes model from the LiteLLM database.
    Only DB-stored models can be deleted; config file models cannot be removed.
    """
    try:
        result = await llm_management_service.delete_model(model_id)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/models/{model_id}/test", response_model=TestModelResponse)
async def test_model(model_id: str):
    """
    Test a model connection.
    
    Sends a simple test request to verify the model is working.
    Returns success status, response, and token usage.
    """
    try:
        result = await llm_management_service.test_model(model_id)
        return result
    except Exception as e:
        return TestModelResponse(
            success=False,
            model=model_id,
            error=str(e)
        )


@router.get("/health")
async def get_health():
    """
    Get health status of LLM models.
    
    Returns overall health status from LiteLLM.
    """
    try:
        health = await llm_management_service.get_model_health()
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

