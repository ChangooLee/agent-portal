"""FastAPI BFF Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routes import embed, kong_admin

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Agent Portal Backend for Frontend (BFF) - Proxy for observability and admin tools",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(embed.router, tags=["embed"])
app.include_router(kong_admin.router, tags=["kong-admin"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "endpoints": {
            "kong_admin": settings.KONG_ADMIN_PROXY_BASE,
            "helicone": settings.HELICONE_PROXY_BASE,
            "langfuse": settings.LANGFUSE_PROXY_BASE,
            "security": settings.SECURITY_PROXY_BASE,
        }
    }
