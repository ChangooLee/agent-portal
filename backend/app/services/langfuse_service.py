"""Langfuse Service for LLM Observability"""
from typing import Optional, Dict, Any
from app.config import get_settings
import httpx

settings = get_settings()

# Optional import for Langfuse
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None


class LangfuseService:
    """Service for interacting with Langfuse"""
    
    def __init__(self):
        self.base_url = settings.LANGFUSE_INTERNAL_URL
        self.public_key = settings.LANGFUSE_PUBLIC_KEY
        self.secret_key = settings.LANGFUSE_SECRET_KEY
        
        # Initialize Langfuse client if keys are provided and module is available
        if LANGFUSE_AVAILABLE and self.public_key and self.secret_key:
            self.client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.base_url
            )
        else:
            self.client = None
    
    async def get_usage_summary(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get usage summary from Langfuse API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/public/usage"
                if project_id:
                    url += f"?project_id={project_id}"
                
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "total_traces": 0,
                        "total_tokens": 0,
                        "total_cost": 0.0,
                        "error": "Langfuse API not available"
                    }
        except Exception as e:
            return {
                "total_traces": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "error": str(e)
            }
    
    def create_trace(self, name: str, **kwargs):
        """Create a trace in Langfuse"""
        if self.client:
            return self.client.trace(name=name, **kwargs)
        return None
    
    def create_span(self, trace_id: str, name: str, **kwargs):
        """Create a span in Langfuse"""
        if self.client:
            return self.client.span(trace_id=trace_id, name=name, **kwargs)
        return None


# Singleton instance
langfuse_service = LangfuseService()
