"""Application configuration"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Server
    APP_NAME: str = "Agent Portal BFF"
    DEBUG: bool = False
    
    # Kong Admin
    KONG_ADMIN_INTERNAL_URL: str = "http://konga:1337"
    KONG_ADMIN_PROXY_BASE: str = "/embed/kong-admin"
    
    # Observability
    OBSERVABILITY_ENABLED: bool = True
    HELICONE_PROXY_BASE: str = "/embed/helicone"
    LANGFUSE_PROXY_BASE: str = "/embed/langfuse"
    SECURITY_PROXY_BASE: str = "/embed/security"
    
    # Helicone
    HELICONE_INTERNAL_URL: str = "http://helicone:8787"
    
    # Langfuse
    LANGFUSE_INTERNAL_URL: str = "http://langfuse:3000"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "http://langfuse:3000"
    
    # LiteLLM
    LITELLM_HOST: str = "http://litellm:4000"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # Default workspace filter
    DEFAULT_WORKSPACE_FILTER: str = "ws_default"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

