"""
Vanna Agent Service for Text-to-SQL Integration.

This module provides a service that manages Vanna agents per database connection,
enabling natural language to SQL conversion with schema awareness and streaming support.
"""

import sys
import os
import logging
import json
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

# Agent monitoring imports
from app.services.agent_registry_service import agent_registry, AgentType
from app.services.agent_trace_adapter import agent_trace_adapter

# Add Vanna to Python path (works in Docker and local development)
_vanna_paths = [
    '/app/libs/vanna/src',  # Docker container path
    os.path.join(os.path.dirname(__file__), '../../../libs/vanna/src'),  # Local development path
]
for _path in _vanna_paths:
    if os.path.exists(_path) and _path not in sys.path:
        sys.path.insert(0, os.path.abspath(_path))
        break

logger = logging.getLogger(__name__)


@dataclass
class VannaConfig:
    """Configuration for Vanna agent instance."""
    connection_id: str
    connection_name: str
    db_type: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 500
    dialect: str = "SQL"


@dataclass
class TextToSqlResult:
    """Result of Text-to-SQL generation."""
    success: bool
    sql: str = ""
    error: Optional[str] = None
    model: str = "unknown"
    tokens_used: int = 0
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class VannaAgentService:
    """
    Service for managing Vanna agents per database connection.
    
    Provides Text-to-SQL capabilities with:
    - Schema-aware SQL generation
    - Business term integration
    - Streaming response support
    - Connection-specific agent caching
    - Dynamic model selection from LiteLLM
    """
    
    # Model preference order for Text-to-SQL (best to fallback)
    MODEL_PREFERENCES = [
        'gpt-4',
        'gpt-4o',
        'gpt-4o-mini',
        'claude-3-5-sonnet',
        'claude-3-sonnet',
        'gpt-3.5-turbo',
        'qwen-235b',
    ]
    
    def __init__(self):
        """Initialize the Vanna Agent Service."""
        self._agents: Dict[str, Any] = {}  # Cache of agents by connection_id
        self._schema_cache: Dict[str, Dict] = {}  # Schema cache by connection_id
        self._terms_cache: Dict[str, List[Dict]] = {}  # Business terms cache
        self._available_models: Optional[List[str]] = None  # Cached available models
        self._selected_model: Optional[str] = None  # Selected model for Text-to-SQL
        
        # Default model from environment (fallback if auto-detection fails)
        self._env_model = os.environ.get('TEXT_TO_SQL_MODEL')
        
        logger.info("VannaAgentService initialized")
    
    async def _get_available_models(self) -> List[str]:
        """
        Fetch available models from LiteLLM proxy.
        
        Returns:
            List of available model IDs
        """
        if self._available_models is not None:
            return self._available_models
        
        try:
            from app.services.litellm_service import litellm_service
            models_response = await litellm_service.list_models()
            self._available_models = [
                m.get('id') for m in models_response.get('data', [])
                if m.get('id')
            ]
            logger.info(f"Available LiteLLM models: {self._available_models}")
            return self._available_models
        except Exception as e:
            logger.warning(f"Failed to fetch LiteLLM models: {e}")
            self._available_models = []
            return []
    
    async def _select_best_model(self) -> str:
        """
        Select the best available model for Text-to-SQL.
        
        Priority:
        1. TEXT_TO_SQL_MODEL environment variable (if set and available)
        2. First match from MODEL_PREFERENCES list
        3. First available model
        4. Fallback to 'gpt-3.5-turbo' (may fail if not configured)
        
        Returns:
            Selected model ID
        """
        if self._selected_model is not None:
            return self._selected_model
        
        available = await self._get_available_models()
        
        # 1. Check environment variable
        if self._env_model and self._env_model in available:
            self._selected_model = self._env_model
            logger.info(f"Using TEXT_TO_SQL_MODEL from env: {self._selected_model}")
            return self._selected_model
        
        # 2. Find first preferred model that's available
        for preferred in self.MODEL_PREFERENCES:
            if preferred in available:
                self._selected_model = preferred
                logger.info(f"Auto-selected Text-to-SQL model: {self._selected_model}")
                return self._selected_model
        
        # 3. Use first available model
        if available:
            self._selected_model = available[0]
            logger.info(f"Using first available model: {self._selected_model}")
            return self._selected_model
        
        # 4. Fallback (will likely fail, but better than nothing)
        self._selected_model = self._env_model or 'gpt-3.5-turbo'
        logger.warning(f"No models available, falling back to: {self._selected_model}")
        return self._selected_model
    
    @property
    def default_model(self) -> str:
        """Get the default model (for sync access). Use _select_best_model() for async."""
        return self._selected_model or self._env_model or 'gpt-3.5-turbo'
    
    def invalidate_model_cache(self) -> None:
        """Invalidate cached model list (call when LiteLLM config changes)."""
        self._available_models = None
        self._selected_model = None
        logger.info("Model cache invalidated")
    
    async def get_or_create_agent(
        self,
        connection_id: str,
        connection_info: Dict[str, Any],
        force_refresh: bool = False
    ) -> Any:
        """
        Get or create a Vanna agent for a specific database connection.
        
        Args:
            connection_id: Database connection ID
            connection_info: Connection metadata (name, db_type, etc.)
            force_refresh: Force recreation of the agent
            
        Returns:
            Configured Vanna agent instance
        """
        if not force_refresh and connection_id in self._agents:
            return self._agents[connection_id]
        
        # Select best available model from LiteLLM
        selected_model = await self._select_best_model()
        
        # Create new agent with LiteLLM backend
        from app.services.vanna_llm_service import LiteLLMVannaService
        
        config = VannaConfig(
            connection_id=connection_id,
            connection_name=connection_info.get('name', 'Unknown'),
            db_type=connection_info.get('db_type', 'postgresql'),
            model=selected_model,
        )
        
        # Create LLM service
        llm_service = LiteLLMVannaService(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        
        # Store agent configuration (simplified - full Agent creation if needed)
        agent_wrapper = {
            'config': config,
            'llm_service': llm_service,
            'schema': None,
            'terms': [],
            'created_at': datetime.now(),
        }
        
        self._agents[connection_id] = agent_wrapper
        logger.info(f"Created Vanna agent for connection: {connection_id}")
        
        return agent_wrapper
    
    async def train_agent(
        self,
        connection_id: str,
        schema: Dict[str, Any],
        business_terms: Optional[List[Dict]] = None
    ) -> bool:
        """
        Train agent with schema and business terms.
        
        Args:
            connection_id: Database connection ID
            schema: Database schema metadata
            business_terms: Optional list of business terms
            
        Returns:
            True if training successful
        """
        if connection_id not in self._agents:
            logger.warning(f"Agent not found for connection: {connection_id}")
            return False
        
        agent_wrapper = self._agents[connection_id]
        
        # Store schema and terms
        agent_wrapper['schema'] = schema
        agent_wrapper['terms'] = business_terms or []
        
        # Cache for quick access
        self._schema_cache[connection_id] = schema
        self._terms_cache[connection_id] = business_terms or []
        
        logger.info(f"Trained agent for connection {connection_id} with "
                   f"{len(schema.get('tables', []))} tables, "
                   f"{len(business_terms or [])} business terms")
        
        return True
    
    async def generate_sql(
        self,
        connection_id: str,
        question: str,
        connection_info: Optional[Dict[str, Any]] = None,
    ) -> TextToSqlResult:
        """
        Generate SQL from natural language question.
        
        This method integrates with DataCloud's schema and business terms
        to provide context-aware SQL generation.
        
        Agent Monitoring:
        - Auto-registers as vanna agent if not exists
        - Starts/ends trace for monitoring
        - Includes agent_id in LLM metadata for trace linking
        
        Args:
            connection_id: Database connection ID
            question: Natural language question
            connection_info: Optional connection info for lazy agent creation
            
        Returns:
            TextToSqlResult with generated SQL or error
        """
        start_time = datetime.now()
        trace_id = None
        agent_info = None
        
        try:
            # 1. Auto-register vanna agent (single agent for all Text-to-SQL)
            agent_name = "vanna-text-to-sql"
            try:
                agent_info = await agent_registry.register_or_get(
                    name=agent_name,
                    agent_type=AgentType.VANNA,
                    external_id=None,  # No external_id - single agent for all connections
                    description="Vanna Text-to-SQL Agent for Data Cloud"
                )
                logger.debug(f"Vanna agent registered: {agent_info['id']}")
            except Exception as e:
                logger.warning(f"Agent registration failed (continuing without monitoring): {e}")
            
            # 2. Start trace for monitoring
            if agent_info:
                try:
                    trace_id = await agent_trace_adapter.start_trace(
                        agent_id=agent_info['id'],
                        agent_name=agent_name,
                        agent_type='vanna',
                        project_id=agent_info.get('project_id', 'default-project'),
                        inputs={'question': question, 'connection_id': connection_id}
                    )
                except Exception as e:
                    logger.warning(f"Trace start failed (continuing): {e}")
            
            # Lazy agent creation if not exists
            if connection_id not in self._agents:
                if connection_info:
                    await self.get_or_create_agent(connection_id, connection_info)
                else:
                    return TextToSqlResult(
                        success=False,
                        error="Agent not initialized. Provide connection_info or call get_or_create_agent first."
                    )
            
            agent_wrapper = self._agents[connection_id]
            llm_service = agent_wrapper['llm_service']
            schema = agent_wrapper.get('schema') or self._schema_cache.get(connection_id)
            terms = agent_wrapper.get('terms') or self._terms_cache.get(connection_id, [])
            
            # Build prompt
            schema_context = self._build_schema_context(schema) if schema else ""
            terms_context = self._build_terms_context(terms)
            
            system_prompt = self._build_system_prompt(agent_wrapper['config'].db_type)
            user_prompt = self._build_user_prompt(question, schema_context, terms_context)
            
            # Create LLM request
            from vanna.core.llm import LlmRequest, LlmMessage
            from vanna.core.user import User
            
            # Create a default user for the request
            default_user = User(id="text-to-sql-user")
            
            # Add agent metadata for trace linking
            metadata = {}
            if agent_info and trace_id:
                metadata = {
                    'agent_id': agent_info['id'],
                    'agent_name': agent_name,
                    'parent_trace_id': trace_id,
                }
            
            request = LlmRequest(
                system_prompt=system_prompt,
                messages=[
                    LlmMessage(role="user", content=user_prompt)
                ],
                max_tokens=agent_wrapper['config'].max_tokens,
                user=default_user,
                metadata=metadata,
            )
            
            # Send request
            response = await llm_service.send_request(request)
            
            # Extract SQL from response
            sql = self._extract_sql(response.content or "")
            
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            tokens_used = response.usage.get('total_tokens', 0) if response.usage else 0
            # Cost is stored in metadata due to Vanna's usage dict expecting int values
            cost_used = response.metadata.get('cost', 0.0) if response.metadata else 0.0
            
            # 3. End trace with success
            if trace_id:
                try:
                    await agent_trace_adapter.end_trace(
                        trace_id=trace_id,
                        outputs={'sql': sql},
                        tokens=tokens_used,
                        cost=cost_used  # Pass LLM cost to trace
                    )
                except Exception as e:
                    logger.warning(f"Trace end failed: {e}")
            
            return TextToSqlResult(
                success=True,
                sql=sql,
                model=agent_wrapper['config'].model,
                tokens_used=tokens_used,
                execution_time_ms=execution_time_ms,
                metadata={
                    'finish_reason': response.finish_reason,
                    'connection_id': connection_id,
                    'agent_id': agent_info['id'] if agent_info else None,
                    'trace_id': trace_id,
                }
            )
            
        except Exception as e:
            logger.error(f"SQL generation failed for connection {connection_id}: {e}")
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # End trace with error
            if trace_id:
                try:
                    await agent_trace_adapter.end_trace(
                        trace_id=trace_id,
                        error=str(e)
                    )
                except Exception:
                    pass
            
            return TextToSqlResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
    
    async def generate_sql_stream(
        self,
        connection_id: str,
        question: str,
        connection_info: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate SQL with streaming response.
        
        Yields SSE-compatible chunks as the LLM generates the response.
        
        Args:
            connection_id: Database connection ID
            question: Natural language question
            connection_info: Optional connection info
            
        Yields:
            Dict chunks with type and data fields
        """
        request_id = str(uuid.uuid4())
        
        try:
            # Lazy agent creation
            if connection_id not in self._agents:
                if connection_info:
                    await self.get_or_create_agent(connection_id, connection_info)
                else:
                    yield {
                        "type": "error",
                        "data": {"message": "Agent not initialized"},
                        "request_id": request_id,
                    }
                    return
            
            agent_wrapper = self._agents[connection_id]
            llm_service = agent_wrapper['llm_service']
            schema = agent_wrapper.get('schema') or self._schema_cache.get(connection_id)
            terms = agent_wrapper.get('terms') or self._terms_cache.get(connection_id, [])
            
            # Build prompts
            schema_context = self._build_schema_context(schema) if schema else ""
            terms_context = self._build_terms_context(terms)
            system_prompt = self._build_system_prompt(agent_wrapper['config'].db_type)
            user_prompt = self._build_user_prompt(question, schema_context, terms_context)
            
            # Create LLM request
            from vanna.core.llm import LlmRequest, LlmMessage
            from vanna.core.user import User
            
            # Create a default user for the request
            default_user = User(id="text-to-sql-stream-user")
            
            request = LlmRequest(
                system_prompt=system_prompt,
                messages=[
                    LlmMessage(role="user", content=user_prompt)
                ],
                max_tokens=agent_wrapper['config'].max_tokens,
                user=default_user,
            )
            
            # Stream response
            yield {
                "type": "start",
                "data": {"message": "Generating SQL..."},
                "request_id": request_id,
            }
            
            full_content = ""
            async for chunk in llm_service.stream_request(request):
                if chunk.content:
                    full_content += chunk.content
                    yield {
                        "type": "content",
                        "data": {"delta": chunk.content},
                        "request_id": request_id,
                    }
                
                if chunk.finish_reason:
                    # Extract clean SQL
                    sql = self._extract_sql(full_content)
                    yield {
                        "type": "complete",
                        "data": {
                            "sql": sql,
                            "raw_response": full_content,
                            "finish_reason": chunk.finish_reason,
                        },
                        "request_id": request_id,
                    }
                    
        except Exception as e:
            logger.error(f"Streaming SQL generation failed: {e}")
            yield {
                "type": "error",
                "data": {"message": str(e)},
                "request_id": request_id,
            }
    
    def invalidate_cache(self, connection_id: str) -> None:
        """
        Invalidate cached agent and schema for a connection.
        
        Args:
            connection_id: Database connection ID
        """
        if connection_id in self._agents:
            del self._agents[connection_id]
        if connection_id in self._schema_cache:
            del self._schema_cache[connection_id]
        if connection_id in self._terms_cache:
            del self._terms_cache[connection_id]
        
        logger.info(f"Invalidated cache for connection: {connection_id}")
    
    # ========== Internal helpers ==========
    
    def _build_system_prompt(self, db_type: str) -> str:
        """Build system prompt for SQL generation."""
        dialect_map = {
            'postgresql': 'PostgreSQL',
            'mysql': 'MySQL',
            'mariadb': 'MySQL/MariaDB',
            'clickhouse': 'ClickHouse',
            'sqlite': 'SQLite',
        }
        dialect = dialect_map.get(db_type, 'SQL')
        
        return f"""당신은 {dialect} 전문가입니다. 사용자의 자연어 질문을 주어진 데이터베이스 스키마에 맞는 SQL 쿼리로 변환합니다.

규칙:
1. SELECT 쿼리만 생성합니다 (INSERT, UPDATE, DELETE 금지)
2. 안전을 위해 LIMIT 100을 기본으로 추가합니다
3. 컬럼명과 테이블명은 정확하게 사용합니다
4. 비즈니스 용어가 있으면 참고하여 올바른 컬럼을 선택합니다
5. SQL만 반환하고 설명은 하지 않습니다
6. SQL 코드 블록(```)은 사용하지 않습니다"""
    
    def _build_user_prompt(
        self,
        question: str,
        schema_context: str,
        terms_context: str
    ) -> str:
        """Build user prompt with context."""
        return f"""### 데이터베이스 스키마
{schema_context if schema_context else "스키마 정보 없음"}

### 비즈니스 용어집
{terms_context}

### 사용자 질문
{question}

### 생성할 SQL 쿼리 (SELECT만 가능, LIMIT 100 포함)"""
    
    def _build_schema_context(self, schema: Dict[str, Any]) -> str:
        """Convert schema to text context for LLM."""
        if not schema:
            return ""
        
        lines = []
        tables = schema.get("tables", [])
        
        # Limit to 20 tables to stay within token limits
        for table in tables[:20]:
            table_name = table.get("name", "unknown")
            columns = table.get("columns", [])
            
            col_defs = []
            for col in columns[:30]:  # Max 30 columns per table
                col_name = col.get("name", "")
                col_type = col.get("type", "")
                pk = " (PK)" if col.get("primary_key") or col.get("is_primary_key") else ""
                fk = " (FK)" if col.get("foreign_key") or col.get("is_foreign_key") else ""
                col_defs.append(f"  - {col_name}: {col_type}{pk}{fk}")
            
            lines.append(f"테이블: {table_name}")
            lines.extend(col_defs)
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_terms_context(self, terms: List[Dict[str, Any]]) -> str:
        """Convert business terms to text context."""
        if not terms:
            return "등록된 비즈니스 용어가 없습니다."
        
        lines = []
        for term in terms[:50]:  # Max 50 terms
            tech = term.get("technical_name", "")
            biz = term.get("business_name", "")
            desc = term.get("description", "")
            lines.append(f"- {tech} = {biz}" + (f" ({desc})" if desc else ""))
        
        return "\n".join(lines)
    
    def _extract_sql(self, llm_response: str) -> str:
        """Extract clean SQL from LLM response."""
        sql = llm_response.strip()
        
        # Remove markdown code blocks
        if sql.startswith("```sql"):
            sql = sql[6:]
        elif sql.startswith("```"):
            sql = sql[3:]
        
        if sql.endswith("```"):
            sql = sql[:-3]
        
        sql = sql.strip()
        
        # Ensure LIMIT is present for safety
        sql_upper = sql.upper()
        if "LIMIT" not in sql_upper and sql_upper.startswith("SELECT"):
            sql = sql.rstrip(";") + " LIMIT 100"
        
        return sql


# Singleton instance
vanna_agent_service = VannaAgentService()

