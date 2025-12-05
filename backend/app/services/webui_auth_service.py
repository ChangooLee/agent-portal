"""
WebUI Auth Service

WebUI의 사용자 및 그룹 정보를 조회하는 서비스.
Backend BFF에서 WebUI의 API를 호출하여 인증/권한 정보를 가져옵니다.
"""

from typing import Dict, Any, Optional, List
import httpx
import os
from fastapi import HTTPException


class WebUIAuthService:
    """WebUI 인증/그룹 연동 서비스.
    
    WebUI의 사용자 및 그룹 API를 호출하여 정보를 조회합니다.
    
    Attributes:
        webui_url: WebUI API 기본 URL
    """
    
    def __init__(self):
        # WebUI Backend URL (Docker 네트워크 내부)
        self.webui_url = os.getenv("WEBUI_API_URL", "http://open-webui:8080")
    
    async def get_users(self, token: str) -> List[Dict[str, Any]]:
        """WebUI 사용자 목록 조회.
        
        Args:
            token: WebUI 인증 토큰
            
        Returns:
            사용자 목록
            
        Raises:
            HTTPException: API 호출 실패 시
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.webui_url}/api/v1/users/",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="WebUI API timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"WebUI API error: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get users from WebUI: {str(e)}"
            )
    
    async def get_groups(self, token: str) -> List[Dict[str, Any]]:
        """WebUI 그룹 목록 조회.
        
        Args:
            token: WebUI 인증 토큰
            
        Returns:
            그룹 목록
            
        Raises:
            HTTPException: API 호출 실패 시
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.webui_url}/api/v1/groups/",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="WebUI API timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"WebUI API error: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get groups from WebUI: {str(e)}"
            )
    
    async def get_group_by_id(self, token: str, group_id: str) -> Optional[Dict[str, Any]]:
        """WebUI 그룹 상세 조회.
        
        Args:
            token: WebUI 인증 토큰
            group_id: 그룹 ID
            
        Returns:
            그룹 정보 또는 None
            
        Raises:
            HTTPException: API 호출 실패 시
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.webui_url}/api/v1/groups/id/{group_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="WebUI API timeout")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"WebUI API error: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get group from WebUI: {str(e)}"
            )
    
    async def get_user_groups(self, token: str, user_id: str) -> List[str]:
        """사용자가 속한 그룹 ID 목록 조회.
        
        모든 그룹을 조회한 후, 해당 사용자가 포함된 그룹을 필터링합니다.
        
        Args:
            token: WebUI 인증 토큰
            user_id: 사용자 ID
            
        Returns:
            그룹 ID 목록
        """
        groups = await self.get_groups(token)
        user_group_ids = []
        
        for group in groups:
            user_ids = group.get('user_ids', [])
            if user_id in user_ids:
                user_group_ids.append(group['id'])
        
        return user_group_ids
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """WebUI 토큰 검증 및 사용자 정보 조회.
        
        Args:
            token: WebUI 인증 토큰
            
        Returns:
            사용자 정보 또는 None
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.webui_url}/api/v1/auths/",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 401:
                    return None
                response.raise_for_status()
                return response.json()
        except Exception:
            return None
    
    async def get_current_user_info(
        self,
        token: str
    ) -> Optional[Dict[str, Any]]:
        """현재 사용자 정보 및 그룹 조회.
        
        Args:
            token: WebUI 인증 토큰
            
        Returns:
            사용자 정보 (id, name, email, role, group_ids 포함) 또는 None
        """
        user = await self.verify_token(token)
        if not user:
            return None
        
        user_id = user.get('id')
        if user_id:
            group_ids = await self.get_user_groups(token, user_id)
            user['group_ids'] = group_ids
        else:
            user['group_ids'] = []
        
        return user


# Singleton 인스턴스
webui_auth_service = WebUIAuthService()





