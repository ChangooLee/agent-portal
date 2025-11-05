"""RBAC middleware for admin-only access control"""
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import httpx


security = HTTPBearer()


async def get_current_user_role(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    Extract user role from JWT token or session.
    This is a placeholder - integrate with your actual auth system.
    """
    # TODO: 실제 인증 시스템과 통합 필요
    # 현재는 헤더에서 role을 확인하는 간단한 구현
    token = credentials.credentials if credentials else None
    
    # 실제 구현에서는:
    # 1. JWT 토큰 검증
    # 2. 사용자 정보 조회 (Open-WebUI API 또는 세션)
    # 3. 역할 반환
    
    # 임시: 요청 헤더에서 역할 확인
    # 실제로는 Open-WebUI의 인증 시스템과 통합 필요
    return {"role": "admin"}  # Placeholder


def require_admin_role(user_info: dict = None) -> None:
    """
    Check if user has admin role.
    Raises HTTPException if not admin.
    """
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


