"""
AgentOps 세션 관리 서비스

AgentOps Self-Hosted의 Supabase 인증을 통해 서비스 계정 세션을 생성하고 관리합니다.
이 세션은 AgentOps Dashboard 프록시에서 사용됩니다.
"""
import os
import time
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentOpsSession:
    """AgentOps 세션 정보"""
    session_cookie: str
    expires_at: float  # Unix timestamp
    user_id: str


class AgentOpsSessionService:
    """
    AgentOps 세션 관리 서비스.
    
    Supabase를 통해 서비스 계정으로 로그인하고 세션 쿠키를 캐싱합니다.
    세션이 만료되면 자동으로 갱신합니다.
    
    Attributes:
        supabase_url: Supabase API URL
        agentops_api_url: AgentOps API URL
        service_email: 서비스 계정 이메일
        service_password: 서비스 계정 비밀번호
    """
    
    def __init__(self):
        # 환경 변수에서 설정 로드
        # Supabase Kong Gateway URL (포트 55321은 Kong Gateway)
        self.supabase_url = os.getenv("AGENTOPS_SUPABASE_URL", "http://host.docker.internal:55321")
        self.agentops_api_url = os.getenv("AGENTOPS_API_URL", "http://host.docker.internal:8003")
        self.service_email = os.getenv("AGENTOPS_SERVICE_EMAIL", "admin@agent-portal.local")
        self.service_password = os.getenv("AGENTOPS_SERVICE_PASSWORD", "agentops-admin-password")
        self.supabase_anon_key = os.getenv(
            "AGENTOPS_SUPABASE_ANON_KEY", 
            "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"
        )
        
        # 세션 캐시
        self._session: Optional[AgentOpsSession] = None
        self._session_refresh_margin = 300  # 만료 5분 전에 갱신
    
    async def get_session_cookie(self) -> Optional[str]:
        """
        유효한 세션 쿠키를 반환합니다.
        
        세션이 없거나 만료되면 자동으로 갱신합니다.
        
        Returns:
            세션 쿠키 문자열 또는 None (로그인 실패 시)
        """
        # 세션이 없거나 만료 임박 시 갱신
        if self._session is None or self._is_session_expiring():
            await self._refresh_session()
        
        if self._session:
            return self._session.session_cookie
        return None
    
    def _is_session_expiring(self) -> bool:
        """세션이 만료 임박인지 확인"""
        if self._session is None:
            return True
        return time.time() > (self._session.expires_at - self._session_refresh_margin)
    
    async def _refresh_session(self) -> None:
        """
        Supabase를 통해 새 세션을 생성합니다.
        
        1. Supabase Auth API로 로그인
        2. AgentOps API의 /auth/session 엔드포인트로 세션 쿠키 획득
        """
        try:
            # 1단계: Supabase Auth로 로그인하여 access_token 획득
            access_token = await self._supabase_login()
            if not access_token:
                logger.error("Failed to get Supabase access token")
                return
            
            # 2단계: AgentOps API로 세션 쿠키 획득
            session_cookie = await self._get_agentops_session(access_token)
            if not session_cookie:
                logger.error("Failed to get AgentOps session cookie")
                return
            
            # 세션 캐시 업데이트 (30분 유효)
            self._session = AgentOpsSession(
                session_cookie=session_cookie,
                expires_at=time.time() + 1800,  # 30분
                user_id="service-account"
            )
            
            logger.info("AgentOps session refreshed successfully")
            
        except Exception as e:
            logger.error(f"Failed to refresh AgentOps session: {e}")
            self._session = None
    
    async def _supabase_login(self) -> Optional[str]:
        """
        Supabase Auth API로 로그인하여 access_token을 획득합니다.
        
        Returns:
            access_token 문자열 또는 None
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.supabase_url}/auth/v1/token?grant_type=password",
                    headers={
                        "apikey": self.supabase_anon_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "email": self.service_email,
                        "password": self.service_password
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                else:
                    logger.error(f"Supabase login failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Supabase login error: {e}")
            return None
    
    async def _get_agentops_session(self, access_token: str) -> Optional[str]:
        """
        AgentOps API의 /auth/session 엔드포인트로 세션 쿠키를 획득합니다.
        
        Args:
            access_token: Supabase access token
            
        Returns:
            세션 쿠키 문자열 또는 None
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # AgentOps auth/session 엔드포인트 호출
                # access_token을 URL-encoded body로 전송
                response = await client.post(
                    f"{self.agentops_api_url}/auth/session",
                    content=f"access_token={access_token}",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                )
                
                if response.status_code == 200:
                    # Set-Cookie 헤더에서 세션 쿠키 추출
                    cookies = response.cookies
                    # agentops_session 쿠키 찾기
                    for cookie in response.headers.get_list("set-cookie"):
                        if "agentops_session=" in cookie:
                            # 쿠키 값만 추출
                            cookie_value = cookie.split(";")[0]
                            return cookie_value
                    
                    # 쿠키가 없으면 전체 쿠키 헤더 반환
                    if response.cookies:
                        cookie_str = "; ".join([f"{k}={v}" for k, v in response.cookies.items()])
                        return cookie_str
                    
                    logger.warning("No session cookie in response")
                    return None
                else:
                    logger.error(f"AgentOps session failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"AgentOps session error: {e}")
            return None
    
    async def logout(self) -> None:
        """세션을 만료시킵니다."""
        self._session = None
        logger.info("AgentOps session cleared")


# Singleton 인스턴스
agentops_session_service = AgentOpsSessionService()

