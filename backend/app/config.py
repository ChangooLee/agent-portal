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
    
    # Environment
    ENVIRONMENT: str = "local"  # local, development, production
    
    # MariaDB
    MARIADB_ROOT_PASSWORD: str = "rootpass"
    MARIADB_DATABASE: str = "agent_portal"
    
    # News Data
    # 로컬 PC: /Users/lchangoo/Workspace/mcp-naver-news/src/data
    # 개발 서버: 환경 변수로 설정 (NEWS_DATA_PATH_DEV)
    # Docker: /data/news (볼륨 마운트)
    NEWS_DATA_PATH: str = "/data/news"  # Docker volume mount path
    NEWS_DATA_PATH_DEV: str = ""  # Development server path (set via env var)
    NEWS_DATA_PATH_LOCAL: str = "/Users/lchangoo/Workspace/mcp-naver-news/src/data"  # Local PC path
    
    def get_news_data_path(self) -> str:
        """환경에 따른 뉴스 데이터 경로 반환.
        
        Returns:
            뉴스 데이터 경로
        """
        if self.ENVIRONMENT == "local":
            return self.NEWS_DATA_PATH_LOCAL
        elif self.ENVIRONMENT == "development" and self.NEWS_DATA_PATH_DEV:
            return self.NEWS_DATA_PATH_DEV
        else:
            return self.NEWS_DATA_PATH
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

