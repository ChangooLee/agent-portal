"""FastAPI BFF Application"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routes with explicit error handling
try:
    from app.routes import embed, kong_admin, chat, observability, news
    logger.info("✅ Old routes imported successfully")
except Exception as e:
    logger.error(f"❌ Old routes import failed: {e}")
    raise

try:
    from app.routes import proxy, agents, monitoring, projects, teams, mcp, gateway, datacloud, llm, vanna, agent_registry
    logger.info("✅ New routes (proxy, agents, monitoring, projects, teams, mcp, gateway, datacloud, llm, vanna, agent_registry) imported successfully")
except Exception as e:
    logger.error(f"❌ New routes import failed: {e}")
    import traceback
    traceback.print_exc()
    raise

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
    expose_headers=["*"],
)

# Private Network Access middleware (Chrome's CORS policy for localhost from external IP)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class PrivateNetworkAccessMiddleware(BaseHTTPMiddleware):
    """Add Access-Control-Allow-Private-Network header for Chrome's Private Network Access policy."""
    async def dispatch(self, request: StarletteRequest, call_next):
        # Handle preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response

app.add_middleware(PrivateNetworkAccessMiddleware)

# Include routers
app.include_router(embed.router)
app.include_router(kong_admin.router)
app.include_router(chat.router)
app.include_router(observability.router)
app.include_router(news.router)
app.include_router(proxy.router)
app.include_router(agents.router)
app.include_router(monitoring.router)
app.include_router(projects.router)
app.include_router(teams.router)
app.include_router(mcp.router)
app.include_router(gateway.router)
app.include_router(datacloud.router)
app.include_router(llm.router)
app.include_router(vanna.router)
app.include_router(agent_registry.router)

# Debug: 라우터 등록 확인
import logging
logger = logging.getLogger(__name__)
logger.info(f"Total routes registered: {len(app.routes)}")
monitoring_routes = [r for r in app.routes if hasattr(r, 'path') and 'monitoring' in r.path.lower()]
logger.info(f"Monitoring routes: {len(monitoring_routes)}")


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
            "security": settings.SECURITY_PROXY_BASE,
        }
    }

