"""LiteLLM Service for LLM Gateway"""
import httpx
from typing import Optional, Dict, Any
from app.config import get_settings

settings = get_settings()


class LiteLLMService:
    """Service for interacting with LiteLLM gateway"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'LITELLM_HOST', 'http://litellm:4000')
        self.api_key = getattr(settings, 'LITELLM_MASTER_KEY', 'sk-1234')
        
    async def list_models(self) -> Dict[str, Any]:
        """Get list of available models from LiteLLM"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{self.base_url}/v1/models", headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                raise Exception(f"Failed to connect to LiteLLM: {str(e)}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"LiteLLM API error: {e.response.status_code} - {e.response.text}")
    
    async def chat_completion(
        self,
        model: str,
        messages: list,
        stream: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Create a chat completion via LiteLLM (async generator for stream mode)"""
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        # Add metadata for OTEL tracing (agent_id, parent_trace_id, etc.)
        if metadata:
            payload["metadata"] = metadata
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            yield line
            except httpx.RequestError as e:
                raise Exception(f"Failed to connect to LiteLLM: {str(e)}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"LiteLLM API error: {e.response.status_code} - {e.response.text}")
    
    async def chat_completion_sync(
        self,
        model: str,
        messages: list,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a non-streaming chat completion via LiteLLM.
        
        Args:
            model: Model name
            messages: Chat messages
            metadata: Optional metadata for OTEL tracing (agent_id, parent_trace_id, etc.)
                      LiteLLM's OTEL callback stores this in SpanAttributes
                      W3C Trace Context headers (traceparent, tracestate) are also extracted
            **kwargs: Additional LiteLLM parameters
            
        Returns:
            LiteLLM response with choices, usage, etc.
        """
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # W3C Trace Context headers 추출 (metadata에서 traceparent/tracestate)
        # 이렇게 하면 LiteLLM의 OTEL callback이 이 trace의 child로 span을 생성
        if metadata:
            if "traceparent" in metadata:
                headers["traceparent"] = metadata["traceparent"]
            if "tracestate" in metadata:
                headers["tracestate"] = metadata["tracestate"]
        
        # Build payload with metadata for OTEL tracing
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            **kwargs
        }
        
        # Add metadata if provided (LiteLLM stores this in OTEL SpanAttributes)
        if metadata:
            # traceparent/tracestate는 헤더로 보내므로 payload에서 제외
            clean_metadata = {k: v for k, v in metadata.items() if k not in ("traceparent", "tracestate")}
            if clean_metadata:
                payload["metadata"] = clean_metadata
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                raise Exception(f"Failed to connect to LiteLLM: {str(e)}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"LiteLLM API error: {e.response.status_code} - {e.response.text}")


# Singleton instance
litellm_service = LiteLLMService()
