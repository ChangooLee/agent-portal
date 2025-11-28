"""LLM Management Service for LiteLLM Admin API"""
import httpx
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


# Pydantic models for request/response
class LiteLLMParams(BaseModel):
    """LiteLLM model parameters"""
    model: str = Field(..., description="Model identifier (e.g., openrouter/qwen/qwen3-235b)")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    api_base: Optional[str] = Field(None, description="Base URL for the API")
    api_version: Optional[str] = Field(None, description="API version (for Azure)")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens")
    rpm: Optional[int] = Field(None, description="Requests per minute limit")
    tpm: Optional[int] = Field(None, description="Tokens per minute limit")
    input_cost_per_token: Optional[float] = Field(None, description="Input cost per token")
    output_cost_per_token: Optional[float] = Field(None, description="Output cost per token")


class ModelInfo(BaseModel):
    """Model metadata"""
    id: Optional[str] = None
    mode: Optional[str] = None
    description: Optional[str] = None


class AddModelRequest(BaseModel):
    """Request to add a new model"""
    model_name: str = Field(..., description="Display name for the model")
    litellm_params: LiteLLMParams
    model_info: Optional[ModelInfo] = None


class UpdateModelRequest(BaseModel):
    """Request to update an existing model"""
    model_name: Optional[str] = None
    litellm_params: Optional[LiteLLMParams] = None
    model_info: Optional[ModelInfo] = None


# Provider definitions
LLM_PROVIDERS = [
    {
        "id": "openai",
        "name": "OpenAI",
        "description": "GPT-4, GPT-3.5-turbo, and other OpenAI models",
        "color": "#10a37f",
        "prefix": "openai/",
        "requires_api_key": True,
        "default_api_base": "https://api.openai.com/v1"
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "description": "Claude 3, Claude 2, and other Anthropic models",
        "color": "#d97757",
        "prefix": "anthropic/",
        "requires_api_key": True,
        "default_api_base": "https://api.anthropic.com"
    },
    {
        "id": "azure",
        "name": "Azure OpenAI",
        "description": "Azure-hosted OpenAI models",
        "color": "#0078d4",
        "prefix": "azure/",
        "requires_api_key": True,
        "requires_api_version": True
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "description": "Access 100+ models through OpenRouter",
        "color": "#6366f1",
        "prefix": "openrouter/",
        "requires_api_key": True,
        "default_api_base": "https://openrouter.ai/api/v1"
    },
    {
        "id": "google",
        "name": "Google AI (Gemini)",
        "description": "Gemini Pro, Gemini Ultra, and other Google models",
        "color": "#4285f4",
        "prefix": "gemini/",
        "requires_api_key": True
    },
    {
        "id": "vertex_ai",
        "name": "Google Vertex AI",
        "description": "Vertex AI hosted models including Gemini",
        "color": "#34a853",
        "prefix": "vertex_ai/",
        "requires_api_key": True
    },
    {
        "id": "bedrock",
        "name": "AWS Bedrock",
        "description": "Amazon Bedrock hosted models",
        "color": "#ff9900",
        "prefix": "bedrock/",
        "requires_api_key": True
    },
    {
        "id": "groq",
        "name": "Groq",
        "description": "Ultra-fast inference with Groq LPU",
        "color": "#f55036",
        "prefix": "groq/",
        "requires_api_key": True,
        "default_api_base": "https://api.groq.com/openai/v1"
    },
    {
        "id": "together_ai",
        "name": "Together AI",
        "description": "Open-source models hosted on Together",
        "color": "#0ea5e9",
        "prefix": "together_ai/",
        "requires_api_key": True,
        "default_api_base": "https://api.together.xyz/v1"
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "description": "Mistral, Mixtral, and other Mistral models",
        "color": "#ff7000",
        "prefix": "mistral/",
        "requires_api_key": True,
        "default_api_base": "https://api.mistral.ai/v1"
    },
    {
        "id": "cohere",
        "name": "Cohere",
        "description": "Command, Embed, and other Cohere models",
        "color": "#d18ee2",
        "prefix": "cohere/",
        "requires_api_key": True
    },
    {
        "id": "ollama",
        "name": "Ollama (Local)",
        "description": "Locally hosted models via Ollama",
        "color": "#ffffff",
        "prefix": "ollama/",
        "requires_api_key": False,
        "default_api_base": "http://localhost:11434"
    },
    {
        "id": "vllm",
        "name": "vLLM",
        "description": "High-throughput serving with vLLM",
        "color": "#8b5cf6",
        "prefix": "openai/",
        "requires_api_key": False,
        "custom_llm_provider": "vllm"
    },
    {
        "id": "huggingface",
        "name": "Hugging Face",
        "description": "Models from Hugging Face Hub",
        "color": "#ffcc00",
        "prefix": "huggingface/",
        "requires_api_key": True
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "description": "DeepSeek Coder and Chat models",
        "color": "#0066ff",
        "prefix": "deepseek/",
        "requires_api_key": True,
        "default_api_base": "https://api.deepseek.com/v1"
    },
    {
        "id": "fireworks_ai",
        "name": "Fireworks AI",
        "description": "Fast inference for open models",
        "color": "#ef4444",
        "prefix": "fireworks_ai/",
        "requires_api_key": True
    }
]


class LLMManagementService:
    """Service for managing LLM models via LiteLLM Admin API"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'LITELLM_HOST', 'http://litellm:4000')
        self.api_key = getattr(settings, 'LITELLM_MASTER_KEY', 'sk-1234')
    
    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for LiteLLM API calls"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_providers(self) -> List[Dict[str, Any]]:
        """Get list of supported LLM providers"""
        return LLM_PROVIDERS
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """Get list of configured models from LiteLLM"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/model/info",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                
                # Transform response to consistent format
                models = []
                if "data" in data:
                    for model in data["data"]:
                        models.append(self._transform_model_info(model))
                
                return models
        except httpx.TimeoutException:
            logger.error("Timeout connecting to LiteLLM")
            raise Exception("LiteLLM connection timeout")
        except httpx.HTTPStatusError as e:
            logger.error(f"LiteLLM API error: {e.response.status_code}")
            raise Exception(f"LiteLLM API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            raise
    
    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific model"""
        models = await self.list_models()
        for model in models:
            if model.get("model_id") == model_id or model.get("model_name") == model_id:
                return model
        return None
    
    async def add_model(self, request: AddModelRequest) -> Dict[str, Any]:
        """Add a new model to LiteLLM"""
        try:
            payload = {
                "model_name": request.model_name,
                "litellm_params": request.litellm_params.model_dump(exclude_none=True)
            }
            
            if request.model_info:
                payload["model_info"] = request.model_info.model_dump(exclude_none=True)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/model/new",
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise Exception("LiteLLM connection timeout")
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Failed to add model: {error_detail}")
            raise Exception(f"Failed to add model: {error_detail}")
        except Exception as e:
            logger.error(f"Error adding model: {e}")
            raise
    
    async def update_model(self, model_id: str, request: UpdateModelRequest) -> Dict[str, Any]:
        """Update an existing model"""
        try:
            payload = {}
            
            if request.model_name:
                payload["model_name"] = request.model_name
            
            if request.litellm_params:
                payload["litellm_params"] = request.litellm_params.model_dump(exclude_none=True)
            
            if request.model_info:
                payload["model_info"] = request.model_info.model_dump(exclude_none=True)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    f"{self.base_url}/model/{model_id}/update",
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise Exception("LiteLLM connection timeout")
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            raise Exception(f"Failed to update model: {error_detail}")
        except Exception as e:
            logger.error(f"Error updating model: {e}")
            raise
    
    async def delete_model(self, model_id: str) -> Dict[str, Any]:
        """Delete a model from LiteLLM"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/model/delete",
                    headers=self._get_headers(),
                    json={"id": model_id}
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise Exception("LiteLLM connection timeout")
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            raise Exception(f"Failed to delete model: {error_detail}")
        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            raise
    
    async def test_model(self, model_id: str) -> Dict[str, Any]:
        """Test a model connection by making a simple completion request"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self._get_headers(),
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": "Say 'test' in one word."}],
                        "max_tokens": 10
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "model": model_id,
                    "response": result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "usage": result.get("usage", {})
                }
        except httpx.TimeoutException:
            return {
                "success": False,
                "model": model_id,
                "error": "Connection timeout"
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "model": model_id,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            return {
                "success": False,
                "model": model_id,
                "error": str(e)
            }
    
    async def get_model_health(self) -> Dict[str, Any]:
        """Get health status of all models"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error getting model health: {e}")
            return {"healthy": False, "error": str(e)}
    
    def _transform_model_info(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Transform LiteLLM model info to consistent format"""
        litellm_params = model.get("litellm_params", {})
        model_info = model.get("model_info", {})
        
        # Extract provider from model string
        model_str = litellm_params.get("model", "")
        provider = self._extract_provider(model_str)
        
        return {
            "model_id": model.get("model_info", {}).get("id") or model.get("model_name"),
            "model_name": model.get("model_name"),
            "provider": provider,
            "model": model_str,
            "api_base": litellm_params.get("api_base"),
            "max_tokens": model_info.get("max_tokens") or litellm_params.get("max_tokens"),
            "input_cost_per_token": model_info.get("input_cost_per_token"),
            "output_cost_per_token": model_info.get("output_cost_per_token"),
            "mode": model_info.get("mode"),
            "created_at": model_info.get("created_at"),
            "updated_at": model_info.get("updated_at"),
            "db_model": model_info.get("db_model", False),
            "litellm_params": litellm_params,
            "model_info": model_info
        }
    
    def _extract_provider(self, model_str: str) -> str:
        """Extract provider name from model string"""
        for provider in LLM_PROVIDERS:
            if model_str.startswith(provider["prefix"]):
                return provider["id"]
        
        # Check for common patterns
        if "/" in model_str:
            return model_str.split("/")[0]
        
        return "unknown"


# Singleton instance
llm_management_service = LLMManagementService()

