"""LLM Client for Slide Studio (via LiteLLM)"""
from typing import List, Dict, Any, Optional
from app.services.litellm_service import litellm_service
from app.services.slide_studio.config import slide_studio_config
from app.services.slide_studio.orchestrator.metrics import start_llm_call_span, get_trace_headers


class SlideLLMClient:
    """Client for LLM calls (via LiteLLM)"""
    
    def __init__(self, model: Optional[str] = None):
        self.model = model or slide_studio_config.LLM_MODEL
    
    async def generate_slide_content(
        self,
        slide_plan,
        system_prompt: str,
        user_prompt: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate slide content using LLM.
        
        Args:
            slide_plan: SlidePlan object
            system_prompt: System prompt
            user_prompt: User prompt
            trace_id: Parent trace ID for monitoring
            **kwargs: Additional parameters
            
        Returns:
            LLM response as dict
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get trace headers for context propagation
        trace_headers = get_trace_headers()
        
        try:
            # Use start_llm_call_span to record LLM call
            with start_llm_call_span(
                node_name="slide_builder",
                model=self.model,
                messages=messages,
                parent_trace_id=trace_id
            ) as (span, record_result):
                response = await litellm_service.chat_completion_sync(
                    model=self.model,
                    messages=messages,
                    trace_headers=trace_headers,
                    metadata={"parent_trace_id": trace_id} if trace_id else {},
                    **kwargs
                )
                record_result(response)
                return response
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")
    
    async def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform a chat completion with JSON response format.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            trace_id: Parent trace ID for monitoring
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            LLM response as dict
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get trace headers for context propagation
        trace_headers = get_trace_headers()
        
        # Determine node name from context (theme_selector, deck_planner, etc.)
        node_name = kwargs.pop("node_name", "slide_studio")
        
        try:
            # Use start_llm_call_span to record LLM call
            with start_llm_call_span(
                node_name=node_name,
                model=self.model,
                messages=messages,
                parent_trace_id=trace_id
            ) as (span, record_result):
                # Use response_format for JSON mode
                response = await litellm_service.chat_completion_sync(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    trace_headers=trace_headers,
                    metadata={"parent_trace_id": trace_id} if trace_id else {},
                    **kwargs
                )
                record_result(response)
                return response
        except Exception as e:
            raise Exception(f"LLM JSON call failed: {str(e)}")


# Singleton instance
slide_llm_client = SlideLLMClient()
