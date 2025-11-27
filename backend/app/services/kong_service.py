"""
Kong Gateway Service

Kong Admin API를 통해 Service, Route, Plugin, Consumer를 관리하는 서비스.
MCP 서버 등록 시 Kong Gateway에 자동으로 보안 설정을 적용합니다.
"""

from typing import Dict, Any, Optional, List
import httpx
from fastapi import HTTPException
import uuid
import os


class KongService:
    """Kong Admin API를 통해 Gateway 리소스를 관리하는 서비스 클래스.
    
    Attributes:
        admin_url: Kong Admin API URL
        timeout: HTTP 요청 타임아웃 (초)
    """
    
    def __init__(self):
        # Kong Admin API URL (Docker 내부 네트워크)
        self.admin_url = os.getenv("KONG_ADMIN_URL", "http://kong:8001")
        self.timeout = 30.0
    
    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Kong Admin API 요청 헬퍼 메서드.
        
        Args:
            method: HTTP 메서드 (GET, POST, PUT, DELETE 등)
            path: API 경로 (예: /services)
            json_data: 요청 바디 (선택적)
            
        Returns:
            API 응답 딕셔너리
            
        Raises:
            HTTPException: API 호출 실패 시
        """
        url = f"{self.admin_url}{path}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data
                )
                
                # 204 No Content (DELETE 성공)
                if response.status_code == 204:
                    return {"success": True}
                
                # 404 Not Found (리소스 없음)
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail=f"Kong Admin API timeout: {path}"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Kong Admin API error: {e.response.text}"
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Kong Admin API unavailable. Please ensure Kong is running."
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Kong Admin API error: {str(e)}"
            )
    
    # ==================== Service 관리 ====================
    
    async def create_service(
        self,
        name: str,
        url: str,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Kong Service 생성.
        
        Args:
            name: 서비스 이름 (고유)
            url: 업스트림 URL
            tags: 태그 목록 (선택적)
            
        Returns:
            생성된 서비스 정보
        """
        data = {
            "name": name,
            "url": url,
        }
        if tags:
            data["tags"] = tags
        
        return await self._request("POST", "/services", data)
    
    async def get_service(self, name_or_id: str) -> Optional[Dict[str, Any]]:
        """Kong Service 조회.
        
        Args:
            name_or_id: 서비스 이름 또는 ID
            
        Returns:
            서비스 정보 또는 None
        """
        return await self._request("GET", f"/services/{name_or_id}")
    
    async def delete_service(self, name_or_id: str) -> bool:
        """Kong Service 삭제.
        
        Args:
            name_or_id: 서비스 이름 또는 ID
            
        Returns:
            삭제 성공 여부
        """
        result = await self._request("DELETE", f"/services/{name_or_id}")
        return result is not None
    
    # ==================== Route 관리 ====================
    
    async def create_route(
        self,
        service_name_or_id: str,
        name: str,
        paths: List[str],
        methods: Optional[List[str]] = None,
        strip_path: bool = True
    ) -> Dict[str, Any]:
        """Kong Route 생성.
        
        Args:
            service_name_or_id: 연결할 서비스 이름 또는 ID
            name: 라우트 이름 (고유)
            paths: 경로 목록 (예: ["/mcp/my-server"])
            methods: HTTP 메서드 목록 (선택적, 기본값: 모든 메서드)
            strip_path: 경로 제거 여부 (기본값: True)
            
        Returns:
            생성된 라우트 정보
        """
        data = {
            "name": name,
            "paths": paths,
            "strip_path": strip_path,
        }
        if methods:
            data["methods"] = methods
        
        return await self._request(
            "POST",
            f"/services/{service_name_or_id}/routes",
            data
        )
    
    async def get_route(self, name_or_id: str) -> Optional[Dict[str, Any]]:
        """Kong Route 조회.
        
        Args:
            name_or_id: 라우트 이름 또는 ID
            
        Returns:
            라우트 정보 또는 None
        """
        return await self._request("GET", f"/routes/{name_or_id}")
    
    async def delete_route(self, name_or_id: str) -> bool:
        """Kong Route 삭제.
        
        Args:
            name_or_id: 라우트 이름 또는 ID
            
        Returns:
            삭제 성공 여부
        """
        result = await self._request("DELETE", f"/routes/{name_or_id}")
        return result is not None
    
    # ==================== Consumer 관리 ====================
    
    async def create_consumer(
        self,
        username: str,
        custom_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Kong Consumer 생성.
        
        Args:
            username: 사용자명 (고유)
            custom_id: 커스텀 ID (선택적)
            tags: 태그 목록 (선택적)
            
        Returns:
            생성된 Consumer 정보
        """
        data = {"username": username}
        if custom_id:
            data["custom_id"] = custom_id
        if tags:
            data["tags"] = tags
        
        return await self._request("POST", "/consumers", data)
    
    async def get_consumer(self, username_or_id: str) -> Optional[Dict[str, Any]]:
        """Kong Consumer 조회.
        
        Args:
            username_or_id: 사용자명 또는 ID
            
        Returns:
            Consumer 정보 또는 None
        """
        return await self._request("GET", f"/consumers/{username_or_id}")
    
    async def delete_consumer(self, username_or_id: str) -> bool:
        """Kong Consumer 삭제.
        
        Args:
            username_or_id: 사용자명 또는 ID
            
        Returns:
            삭제 성공 여부
        """
        result = await self._request("DELETE", f"/consumers/{username_or_id}")
        return result is not None
    
    # ==================== API Key (Key-Auth) 관리 ====================
    
    async def create_api_key(
        self,
        consumer_username_or_id: str,
        key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Consumer에 API Key 생성.
        
        Args:
            consumer_username_or_id: Consumer 사용자명 또는 ID
            key: API 키 (선택적, 미지정 시 자동 생성)
            
        Returns:
            생성된 API Key 정보
        """
        data = {}
        if key:
            data["key"] = key
        
        return await self._request(
            "POST",
            f"/consumers/{consumer_username_or_id}/key-auth",
            data if data else None
        )
    
    async def list_api_keys(
        self,
        consumer_username_or_id: str
    ) -> List[Dict[str, Any]]:
        """Consumer의 API Key 목록 조회.
        
        Args:
            consumer_username_or_id: Consumer 사용자명 또는 ID
            
        Returns:
            API Key 목록
        """
        result = await self._request(
            "GET",
            f"/consumers/{consumer_username_or_id}/key-auth"
        )
        return result.get("data", []) if result else []
    
    async def delete_api_key(
        self,
        consumer_username_or_id: str,
        key_id: str
    ) -> bool:
        """Consumer의 API Key 삭제.
        
        Args:
            consumer_username_or_id: Consumer 사용자명 또는 ID
            key_id: API Key ID
            
        Returns:
            삭제 성공 여부
        """
        result = await self._request(
            "DELETE",
            f"/consumers/{consumer_username_or_id}/key-auth/{key_id}"
        )
        return result is not None
    
    # ==================== Plugin 관리 ====================
    
    async def enable_key_auth(
        self,
        service_name_or_id: str,
        key_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Service에 Key-Auth 플러그인 활성화.
        
        Args:
            service_name_or_id: 서비스 이름 또는 ID
            key_names: API 키 헤더 이름 목록 (기본값: ["apikey"])
            
        Returns:
            생성된 플러그인 정보
        """
        data = {
            "name": "key-auth",
            "config": {
                "key_names": key_names or ["apikey"],
                "key_in_header": True,
                "key_in_query": True,
                "key_in_body": False,
                "hide_credentials": True,
            }
        }
        
        return await self._request(
            "POST",
            f"/services/{service_name_or_id}/plugins",
            data
        )
    
    async def enable_rate_limiting(
        self,
        service_name_or_id: str,
        minute: int = 60,
        hour: Optional[int] = None,
        day: Optional[int] = None
    ) -> Dict[str, Any]:
        """Service에 Rate-Limiting 플러그인 활성화.
        
        Args:
            service_name_or_id: 서비스 이름 또는 ID
            minute: 분당 요청 제한 (기본값: 60)
            hour: 시간당 요청 제한 (선택적)
            day: 일당 요청 제한 (선택적)
            
        Returns:
            생성된 플러그인 정보
        """
        config = {"minute": minute}
        if hour:
            config["hour"] = hour
        if day:
            config["day"] = day
        
        data = {
            "name": "rate-limiting",
            "config": config
        }
        
        return await self._request(
            "POST",
            f"/services/{service_name_or_id}/plugins",
            data
        )
    
    async def list_plugins(
        self,
        service_name_or_id: str
    ) -> List[Dict[str, Any]]:
        """Service의 플러그인 목록 조회.
        
        Args:
            service_name_or_id: 서비스 이름 또는 ID
            
        Returns:
            플러그인 목록
        """
        result = await self._request(
            "GET",
            f"/services/{service_name_or_id}/plugins"
        )
        return result.get("data", []) if result else []
    
    async def delete_plugin(self, plugin_id: str) -> bool:
        """플러그인 삭제.
        
        Args:
            plugin_id: 플러그인 ID
            
        Returns:
            삭제 성공 여부
        """
        result = await self._request("DELETE", f"/plugins/{plugin_id}")
        return result is not None
    
    # ==================== MCP 서버 등록 헬퍼 ====================
    
    async def setup_mcp_server(
        self,
        server_id: str,
        server_name: str,
        endpoint_url: str,
        rate_limit_minute: int = 120
    ) -> Dict[str, Any]:
        """MCP 서버를 Kong Gateway에 등록하고 보안 설정 적용.
        
        이 메서드는 다음 작업을 수행합니다:
        1. Kong Service 생성 (업스트림: MCP 서버)
        2. Kong Route 생성 (경로: /mcp/{server_id})
        3. Key-Auth 플러그인 활성화
        4. Rate-Limiting 플러그인 활성화
        5. Consumer 생성 및 API Key 발급
        
        Args:
            server_id: MCP 서버 ID (UUID)
            server_name: MCP 서버 이름
            endpoint_url: MCP 서버 엔드포인트 URL
            rate_limit_minute: 분당 요청 제한 (기본값: 120)
            
        Returns:
            Kong 리소스 정보 (service_id, route_id, consumer_id, api_key)
        """
        # 서비스 이름 (Kong에서 고유해야 함)
        service_name = f"mcp-{server_id}"
        route_name = f"mcp-route-{server_id}"
        consumer_name = f"mcp-consumer-{server_id}"
        
        try:
            # 1. Service 생성
            service = await self.create_service(
                name=service_name,
                url=endpoint_url,
                tags=["mcp", server_name]
            )
            
            # 2. Route 생성
            route = await self.create_route(
                service_name_or_id=service["id"],
                name=route_name,
                paths=[f"/mcp/{server_id}"],
                methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                strip_path=True
            )
            
            # 3. Key-Auth 플러그인 활성화
            await self.enable_key_auth(service["id"])
            
            # 4. Rate-Limiting 플러그인 활성화
            await self.enable_rate_limiting(
                service["id"],
                minute=rate_limit_minute
            )
            
            # 5. Consumer 생성
            consumer = await self.create_consumer(
                username=consumer_name,
                custom_id=server_id,
                tags=["mcp"]
            )
            
            # 6. API Key 발급
            api_key_result = await self.create_api_key(consumer["id"])
            
            return {
                "kong_service_id": service["id"],
                "kong_route_id": route["id"],
                "kong_consumer_id": consumer["id"],
                "kong_api_key": api_key_result["key"],
            }
            
        except HTTPException:
            # 실패 시 생성된 리소스 정리
            await self.cleanup_mcp_server(server_id)
            raise
    
    async def cleanup_mcp_server(self, server_id: str) -> None:
        """MCP 서버의 Kong 리소스 정리.
        
        Args:
            server_id: MCP 서버 ID
        """
        service_name = f"mcp-{server_id}"
        route_name = f"mcp-route-{server_id}"
        consumer_name = f"mcp-consumer-{server_id}"
        
        # 순서 중요: Route → Service → Consumer
        try:
            await self.delete_route(route_name)
        except:
            pass
        
        try:
            await self.delete_service(service_name)
        except:
            pass
        
        try:
            await self.delete_consumer(consumer_name)
        except:
            pass
    
    async def regenerate_api_key(self, server_id: str) -> str:
        """MCP 서버의 API Key 재발급.
        
        Args:
            server_id: MCP 서버 ID
            
        Returns:
            새로운 API Key
        """
        consumer_name = f"mcp-consumer-{server_id}"
        
        # 기존 키 삭제
        existing_keys = await self.list_api_keys(consumer_name)
        for key in existing_keys:
            await self.delete_api_key(consumer_name, key["id"])
        
        # 새 키 발급
        api_key_result = await self.create_api_key(consumer_name)
        return api_key_result["key"]
    
    async def health_check(self) -> Dict[str, Any]:
        """Kong Gateway 상태 확인.
        
        Returns:
            Kong 상태 정보
        """
        try:
            result = await self._request("GET", "/status")
            return {
                "status": "healthy",
                "details": result
            }
        except HTTPException as e:
            return {
                "status": "unhealthy",
                "error": e.detail
            }
    
    # ==================== Gateway 관리 API ====================
    
    async def list_services(self) -> List[Dict[str, Any]]:
        """모든 Kong Service 목록 조회.
        
        Returns:
            Service 목록 (각 서비스에 플러그인 정보 포함)
        """
        result = await self._request("GET", "/services")
        services = result.get("data", []) if result else []
        
        # 각 서비스에 플러그인 정보 추가
        for service in services:
            try:
                plugins = await self.list_plugins(service["id"])
                service["plugins"] = [p["name"] for p in plugins]
            except:
                service["plugins"] = []
        
        return services
    
    async def list_all_consumers(self) -> List[Dict[str, Any]]:
        """모든 Kong Consumer 목록 조회 (API Key 포함, 마스킹).
        
        Returns:
            Consumer 목록 (API Key는 마스킹 처리)
        """
        result = await self._request("GET", "/consumers")
        consumers = result.get("data", []) if result else []
        
        # 각 Consumer에 API Key 정보 추가 (마스킹)
        for consumer in consumers:
            try:
                api_keys = await self.list_api_keys(consumer["id"])
                consumer["api_keys"] = []
                for key in api_keys:
                    # API Key 마스킹: 마지막 4자리만 표시
                    original_key = key.get("key", "")
                    if len(original_key) > 4:
                        masked_key = "*" * (len(original_key) - 4) + original_key[-4:]
                    else:
                        masked_key = "****"
                    consumer["api_keys"].append({
                        "id": key.get("id"),
                        "key_masked": masked_key,
                        "created_at": key.get("created_at")
                    })
            except:
                consumer["api_keys"] = []
        
        return consumers
    
    async def list_routes(self) -> List[Dict[str, Any]]:
        """모든 Kong Route 목록 조회.
        
        Returns:
            Route 목록
        """
        result = await self._request("GET", "/routes")
        return result.get("data", []) if result else []
    
    async def list_all_plugins(self) -> List[Dict[str, Any]]:
        """모든 Kong Plugin 목록 조회.
        
        Returns:
            Plugin 목록
        """
        result = await self._request("GET", "/plugins")
        return result.get("data", []) if result else []


# Singleton 인스턴스
kong_service = KongService()

