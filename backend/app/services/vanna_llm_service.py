"""
LiteLLM-based LlmService for Vanna AI Integration.

This module provides a custom implementation of Vanna's LlmService interface
that routes all LLM calls through the existing LiteLLM proxy.
"""

import sys
import os
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

# Add Vanna to Python path (works in Docker and local development)
_vanna_paths = [
    '/app/libs/vanna/src',  # Docker container path
    os.path.join(os.path.dirname(__file__), '../../../libs/vanna/src'),  # Local development path
]
for _path in _vanna_paths:
    if os.path.exists(_path) and _path not in sys.path:
        sys.path.insert(0, os.path.abspath(_path))
        break

from vanna.core.llm import LlmService, LlmRequest, LlmResponse, LlmStreamChunk
from vanna.core.tool import ToolCall, ToolSchema
from app.services.litellm_service import litellm_service

logger = logging.getLogger(__name__)


class LiteLLMVannaService(LlmService):
    """
    Vanna LlmService implementation backed by LiteLLM Proxy.
    
    This service wraps the existing LiteLLM infrastructure to provide
    LLM capabilities to Vanna agents for Text-to-SQL generation.
    
    Args:
        model: Model name to use (default: from TEXT_TO_SQL_MODEL env or gpt-4o-mini)
        temperature: Sampling temperature (default: 0.0 for deterministic SQL)
        max_tokens: Maximum tokens for response (default: 500)
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 500,
    ) -> None:
        self.model = model or os.environ.get('TEXT_TO_SQL_MODEL', 'gpt-4o-mini')
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info(f"LiteLLMVannaService initialized with model: {self.model}")
    
    async def send_request(self, request: LlmRequest) -> LlmResponse:
        """
        Send a non-streaming request to LiteLLM and return the response.
        
        Args:
            request: LlmRequest containing messages and tool definitions
            
        Returns:
            LlmResponse with content, tool_calls, and usage info
        """
        messages = self._build_messages(request)
        tools_payload = self._build_tools_payload(request.tools) if request.tools else None
        
        try:
            kwargs = {
                "temperature": self.temperature,
                "max_tokens": request.max_tokens or self.max_tokens,
            }
            
            if tools_payload:
                kwargs["tools"] = tools_payload
                kwargs["tool_choice"] = "auto"
            
            result = await litellm_service.chat_completion_sync(
                model=self.model,
                messages=messages,
                **kwargs
            )
            
            # Parse response
            choices = result.get("choices", [])
            if not choices:
                return LlmResponse(content=None, tool_calls=None, finish_reason=None)
            
            choice = choices[0]
            message = choice.get("message", {})
            content = message.get("content")
            tool_calls = self._extract_tool_calls(message)
            finish_reason = choice.get("finish_reason")
            
            # Usage info
            usage = result.get("usage", {})
            usage_dict = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            } if usage else None
            
            return LlmResponse(
                content=content,
                tool_calls=tool_calls or None,
                finish_reason=finish_reason,
                usage=usage_dict,
            )
            
        except Exception as e:
            logger.error(f"LiteLLM request failed: {e}")
            raise
    
    async def stream_request(
        self, request: LlmRequest
    ) -> AsyncGenerator[LlmStreamChunk, None]:
        """
        Stream a request to LiteLLM.
        
        Emits LlmStreamChunk for text deltas as they arrive.
        Tool calls are accumulated and emitted in a final chunk.
        """
        messages = self._build_messages(request)
        tools_payload = self._build_tools_payload(request.tools) if request.tools else None
        
        kwargs = {
            "temperature": self.temperature,
            "max_tokens": request.max_tokens or self.max_tokens,
        }
        
        if tools_payload:
            kwargs["tools"] = tools_payload
            kwargs["tool_choice"] = "auto"
        
        try:
            # Tool call builders
            tc_builders: Dict[int, Dict[str, Optional[str]]] = {}
            last_finish: Optional[str] = None
            
            async for line in litellm_service.chat_completion(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            ):
                # Parse SSE data
                if not line.startswith("data:"):
                    continue
                    
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                
                choices = event.get("choices", [])
                if not choices:
                    continue
                
                choice = choices[0]
                delta = choice.get("delta", {})
                
                # Text content
                content_piece = delta.get("content")
                if content_piece:
                    yield LlmStreamChunk(content=content_piece)
                
                # Tool calls
                tool_calls_delta = delta.get("tool_calls")
                if tool_calls_delta:
                    for tc in tool_calls_delta:
                        idx = tc.get("index", 0)
                        b = tc_builders.setdefault(
                            idx, {"id": None, "name": None, "arguments": ""}
                        )
                        if tc.get("id"):
                            b["id"] = tc["id"]
                        fn = tc.get("function", {})
                        if fn.get("name"):
                            b["name"] = fn["name"]
                        if fn.get("arguments"):
                            b["arguments"] = (b["arguments"] or "") + fn["arguments"]
                
                last_finish = choice.get("finish_reason", last_finish)
            
            # Emit final tool calls
            final_tool_calls: List[ToolCall] = []
            for b in tc_builders.values():
                if not b.get("name"):
                    continue
                args_raw = b.get("arguments") or "{}"
                try:
                    args_dict = json.loads(args_raw)
                except Exception:
                    args_dict = {"_raw": args_raw}
                final_tool_calls.append(
                    ToolCall(
                        id=b.get("id") or "tool_call",
                        name=b["name"] or "tool",
                        arguments=args_dict,
                    )
                )
            
            if final_tool_calls:
                yield LlmStreamChunk(
                    tool_calls=final_tool_calls,
                    finish_reason=last_finish
                )
            else:
                yield LlmStreamChunk(finish_reason=last_finish or "stop")
                
        except Exception as e:
            logger.error(f"LiteLLM stream request failed: {e}")
            raise
    
    async def validate_tools(self, tools: List[ToolSchema]) -> List[str]:
        """
        Validate tool schemas.
        
        Returns a list of error messages if any tools are invalid.
        """
        errors: List[str] = []
        for t in tools:
            if not t.name or len(t.name) > 64:
                errors.append(f"Invalid tool name: {t.name!r}")
            if not t.description:
                errors.append(f"Tool {t.name} missing description")
        return errors
    
    # ========== Internal helpers ==========
    
    def _build_messages(self, request: LlmRequest) -> List[Dict[str, Any]]:
        """Convert LlmRequest messages to LiteLLM format."""
        messages: List[Dict[str, Any]] = []
        
        # Add system prompt
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        
        # Add conversation messages
        for m in request.messages:
            msg: Dict[str, Any] = {"role": m.role, "content": m.content}
            
            if m.role == "tool" and m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            elif m.role == "assistant" and m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        }
                    }
                    for tc in m.tool_calls
                ]
            
            messages.append(msg)
        
        return messages
    
    def _build_tools_payload(
        self, tools: Optional[List[ToolSchema]]
    ) -> Optional[List[Dict[str, Any]]]:
        """Convert ToolSchema list to LiteLLM tools format."""
        if not tools:
            return None
        
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            }
            for t in tools
        ]
    
    def _extract_tool_calls(self, message: Dict[str, Any]) -> List[ToolCall]:
        """Extract tool calls from LiteLLM response message."""
        tool_calls: List[ToolCall] = []
        
        for tc in message.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            args_raw = fn.get("arguments", "{}")
            
            try:
                args_dict = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except Exception:
                args_dict = {"_raw": args_raw}
            
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", "tool_call"),
                    name=fn.get("name", "tool"),
                    arguments=args_dict,
                )
            )
        
        return tool_calls


# Factory function to create service instance
def create_litellm_vanna_service(
    model: Optional[str] = None,
    **kwargs
) -> LiteLLMVannaService:
    """
    Factory function to create a LiteLLMVannaService instance.
    
    Args:
        model: Optional model override
        **kwargs: Additional configuration options
        
    Returns:
        Configured LiteLLMVannaService instance
    """
    return LiteLLMVannaService(model=model, **kwargs)

