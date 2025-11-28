"""Chat API endpoints"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio
from app.services.litellm_service import litellm_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "gpt-3.5-turbo"
    stream: bool = True
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat completions via LiteLLM"""
    try:
        # Convert messages to LiteLLM format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        # Stream response from LiteLLM
        async def generate():
            try:
                full_response = ""
                async for line in litellm_service.chat_completion(
                    model=request.model,
                    messages=messages,
                    stream=True,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ):
                    # LiteLLM returns Server-Sent Events format
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            # Extract content from delta
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_response += content
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
                    yield line
                
                # End with completion message
                yield f"data: {json.dumps({'done': True, 'full_response': full_response})}\n\n"
                    
            except Exception as e:
                error_msg = f"Error during streaming: {str(e)}"
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                raise
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/completions")
async def chat_completion(request: ChatRequest):
    """Non-streaming chat completions via LiteLLM"""
    try:
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        response = await litellm_service.chat_completion_sync(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
