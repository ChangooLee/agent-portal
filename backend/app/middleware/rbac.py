"""RBAC middleware for admin-only access control"""
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

security = HTTPBearer()


async def get_current_user_role(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """Extract user role from JWT token or session."""
    token = credentials.credentials if credentials else None
    return {"role": "admin"}  # Placeholder


def require_admin_role(user_info: dict = None) -> None:
    """Check if user has admin role."""
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    role = user_info.get("role", "user")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
