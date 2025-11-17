"""FastAPI BFF Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routes import embed, kong_admin, chat, observability, news, proxy, agents

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Agent Portal Backend for Frontend (BFF) - Chat, Observability, and Admin Tools",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(embed.router)
app.include_router(kong_admin.router)
app.include_router(chat.router)
app.include_router(observability.router)
app.include_router(news.router)
app.include_router(proxy.router)
app.include_router(agents.router)


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
            "chat": "/chat/stream",
            "observability": "/observability/usage",
            "models": "/observability/models",
            "kong_admin": settings.KONG_ADMIN_PROXY_BASE,
            "helicone": settings.HELICONE_PROXY_BASE,
            "langfuse": settings.LANGFUSE_PROXY_BASE,
            "security": settings.SECURITY_PROXY_BASE,
        }
    }

