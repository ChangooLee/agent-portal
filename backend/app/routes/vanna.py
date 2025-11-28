"""
Vanna AI Text-to-SQL API Routes.

This module provides endpoints for natural language to SQL conversion
using the Vanna AI agent framework with LiteLLM backend.

Endpoints:
- POST /vanna/generate_sql - Generate SQL from natural language (non-streaming)
- POST /vanna/chat_sse - Generate SQL with SSE streaming
- POST /vanna/train - Train agent with schema and business terms
- DELETE /vanna/cache/{connection_id} - Invalidate agent cache
"""

import json
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.services.vanna_agent_service import vanna_agent_service
from app.services.datacloud_service import datacloud_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vanna", tags=["vanna"])


# ========== Request/Response Models ==========

class GenerateSqlRequest(BaseModel):
    """Request model for SQL generation."""
    connection_id: str = Field(..., description="Database connection ID")
    question: str = Field(..., description="Natural language question")
    refresh_schema: bool = Field(False, description="Refresh schema before generation")


class GenerateSqlResponse(BaseModel):
    """Response model for SQL generation."""
    success: bool
    sql: str = ""
    error: Optional[str] = None
    model: str = "unknown"
    tokens_used: int = 0
    execution_time_ms: int = 0


class TrainAgentRequest(BaseModel):
    """Request model for agent training."""
    connection_id: str = Field(..., description="Database connection ID")
    refresh_schema: bool = Field(True, description="Refresh schema from database")


class TrainAgentResponse(BaseModel):
    """Response model for agent training."""
    success: bool
    message: str
    tables_count: int = 0
    terms_count: int = 0


class ChatSseRequest(BaseModel):
    """Request model for SSE chat."""
    connection_id: str = Field(..., description="Database connection ID")
    question: str = Field(..., description="Natural language question")


# ========== Endpoints ==========

@router.post("/generate_sql", response_model=GenerateSqlResponse)
async def generate_sql(request: GenerateSqlRequest):
    """
    Generate SQL from natural language question.
    
    This endpoint uses the Vanna AI agent to convert natural language
    questions into SQL queries based on the database schema.
    
    - Uses cached schema and business terms
    - Integrates with LiteLLM for LLM calls
    - Returns generated SQL with metadata
    """
    try:
        # Get connection info
        connection_info = await datacloud_service.get_connection_by_id(request.connection_id)
        if not connection_info:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Refresh schema if requested
        if request.refresh_schema:
            schema = await datacloud_service.get_schema_metadata(
                request.connection_id, refresh=True
            )
            terms = await datacloud_service.get_business_terms(request.connection_id)
            
            # Train agent with fresh data
            await vanna_agent_service.get_or_create_agent(
                request.connection_id, connection_info
            )
            await vanna_agent_service.train_agent(
                request.connection_id, schema, terms
            )
        else:
            # Lazy load schema if not cached
            if request.connection_id not in vanna_agent_service._schema_cache:
                schema = await datacloud_service.get_schema_metadata(request.connection_id)
                terms = await datacloud_service.get_business_terms(request.connection_id)
                
                await vanna_agent_service.get_or_create_agent(
                    request.connection_id, connection_info
                )
                await vanna_agent_service.train_agent(
                    request.connection_id, schema, terms
                )
        
        # Generate SQL
        result = await vanna_agent_service.generate_sql(
            connection_id=request.connection_id,
            question=request.question,
            connection_info=connection_info,
        )
        
        return GenerateSqlResponse(
            success=result.success,
            sql=result.sql,
            error=result.error,
            model=result.model,
            tokens_used=result.tokens_used,
            execution_time_ms=result.execution_time_ms,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat_sse")
async def chat_sse(request: ChatSseRequest):
    """
    Generate SQL with Server-Sent Events streaming.
    
    This endpoint provides real-time streaming of the SQL generation
    process, allowing the frontend to display progressive results.
    
    Response format (SSE):
    - type: "start" - Generation started
    - type: "content" - Partial content delta
    - type: "complete" - Final SQL and metadata
    - type: "error" - Error occurred
    """
    try:
        # Get connection info
        connection_info = await datacloud_service.get_connection_by_id(request.connection_id)
        if not connection_info:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Lazy load schema if not cached
        if request.connection_id not in vanna_agent_service._schema_cache:
            schema = await datacloud_service.get_schema_metadata(request.connection_id)
            terms = await datacloud_service.get_business_terms(request.connection_id)
            
            await vanna_agent_service.get_or_create_agent(
                request.connection_id, connection_info
            )
            await vanna_agent_service.train_agent(
                request.connection_id, schema, terms
            )
        
        async def event_generator():
            """Generate SSE events."""
            try:
                async for chunk in vanna_agent_service.generate_sql_stream(
                    connection_id=request.connection_id,
                    question=request.question,
                    connection_info=connection_info,
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"SSE generation failed: {e}")
                error_data = {
                    "type": "error",
                    "data": {"message": str(e)},
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SSE endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train", response_model=TrainAgentResponse)
async def train_agent(request: TrainAgentRequest):
    """
    Train Vanna agent with database schema and business terms.
    
    This endpoint refreshes the agent's knowledge with the latest
    schema metadata and business terms from the database connection.
    """
    try:
        # Get connection info
        connection_info = await datacloud_service.get_connection_by_id(request.connection_id)
        if not connection_info:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Get schema (refresh if requested)
        schema = await datacloud_service.get_schema_metadata(
            request.connection_id, refresh=request.refresh_schema
        )
        
        if "error" in schema:
            raise HTTPException(status_code=500, detail=schema["error"])
        
        # Get business terms
        terms = await datacloud_service.get_business_terms(request.connection_id)
        
        # Create/update agent
        await vanna_agent_service.get_or_create_agent(
            request.connection_id, connection_info, force_refresh=True
        )
        
        # Train agent
        success = await vanna_agent_service.train_agent(
            request.connection_id, schema, terms
        )
        
        tables_count = len(schema.get("tables", []))
        terms_count = len(terms)
        
        return TrainAgentResponse(
            success=success,
            message=f"Agent trained with {tables_count} tables and {terms_count} business terms",
            tables_count=tables_count,
            terms_count=terms_count,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/{connection_id}")
async def invalidate_cache(connection_id: str):
    """
    Invalidate cached agent and schema for a connection.
    
    Call this when connection settings or schema changes.
    """
    try:
        vanna_agent_service.invalidate_cache(connection_id)
        return {"success": True, "message": f"Cache invalidated for {connection_id}"}
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for Vanna service."""
    return {
        "status": "healthy",
        "service": "vanna",
        "cached_connections": len(vanna_agent_service._agents),
    }

