"""
LangGraph Service

Langflow/Flowise/AutoGen 플로우 실행 + 에이전트 모니터링.
에이전트 레지스트리와 트레이스 어댑터를 사용하여 자동 등록 및 추적.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx

from app.services.agent_registry_service import agent_registry, AgentType
from app.services.agent_trace_adapter import agent_trace_adapter

logger = logging.getLogger(__name__)


# Service URLs (Docker internal)
LANGFLOW_BASE_URL = os.getenv("LANGFLOW_URL", "http://langflow:7860")
FLOWISE_BASE_URL = os.getenv("FLOWISE_URL", "http://flowise:3000")


class LangGraphService:
    """
    Langflow/Flowise/AutoGen 플로우 실행 서비스.
    
    에이전트 레지스트리와 트레이스 어댑터를 통해:
    - 플로우 실행 시 자동으로 에이전트 등록
    - 실행 트레이스를 ClickHouse에 저장
    - 모니터링 대시보드에서 통합 조회 가능
    """
    
    def __init__(self):
        self.project_id = os.getenv("DEFAULT_PROJECT_ID", "default-project")
        logger.info("LangGraphService initialized")
    
    async def execute_langflow(
        self,
        flow_id: str,
        inputs: Dict[str, Any],
        tweaks: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Langflow 플로우 실행.
        
        Args:
            flow_id: Langflow 플로우 ID
            inputs: 입력 데이터
            tweaks: 플로우 수정 파라미터
            tags: 태그 목록
            
        Returns:
            실행 결과 + trace_id
        """
        return await self._execute_flow(
            flow_id=flow_id,
            flow_name=f"langflow-{flow_id[:8]}",
            agent_type=AgentType.LANGFLOW,
            base_url=LANGFLOW_BASE_URL,
            inputs=inputs,
            extra_params={"tweaks": tweaks} if tweaks else None,
            tags=tags
        )
    
    async def execute_flowise(
        self,
        chatflow_id: str,
        question: str,
        history: Optional[List[Dict]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Flowise 채트플로우 실행.
        
        Args:
            chatflow_id: Flowise 채트플로우 ID
            question: 사용자 질문
            history: 대화 히스토리
            tags: 태그 목록
            
        Returns:
            실행 결과 + trace_id
        """
        return await self._execute_flow(
            flow_id=chatflow_id,
            flow_name=f"flowise-{chatflow_id[:8]}",
            agent_type=AgentType.FLOWISE,
            base_url=FLOWISE_BASE_URL,
            inputs={"question": question},
            extra_params={"history": history} if history else None,
            tags=tags
        )
    
    async def _execute_flow(
        self,
        flow_id: str,
        flow_name: str,
        agent_type: AgentType,
        base_url: str,
        inputs: Dict[str, Any],
        extra_params: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        공통 플로우 실행 로직.
        
        1. 에이전트 자동 등록
        2. 트레이스 시작
        3. API 호출
        4. 트레이스 종료
        """
        trace_id = None
        agent_info = None
        start_time = datetime.utcnow()
        
        try:
            # 1. 에이전트 자동 등록
            try:
                agent_info = await agent_registry.register_or_get(
                    name=flow_name,
                    agent_type=agent_type,
                    project_id=self.project_id,
                    external_id=flow_id,
                    description=f"{agent_type.value} agent: {flow_id}"
                )
                logger.debug(f"Agent registered: {agent_info['id']} ({flow_name})")
            except Exception as e:
                logger.warning(f"Agent registration failed: {e}")
            
            # 2. 트레이스 시작
            if agent_info:
                try:
                    trace_id = await agent_trace_adapter.start_trace(
                        agent_id=agent_info['id'],
                        agent_name=flow_name,
                        agent_type=agent_type.value,
                        project_id=self.project_id,
                        inputs=inputs,
                        tags=tags or []
                    )
                except Exception as e:
                    logger.warning(f"Trace start failed: {e}")
            
            # 3. API 호출
            result = await self._call_api(
                agent_type=agent_type,
                base_url=base_url,
                flow_id=flow_id,
                inputs=inputs,
                extra_params=extra_params
            )
            
            # 4. 트레이스 종료 (성공)
            if trace_id:
                try:
                    await agent_trace_adapter.end_trace(
                        trace_id=trace_id,
                        outputs=result,
                        cost=result.get('cost', 0),
                        tokens=result.get('total_tokens', 0)
                    )
                except Exception as e:
                    logger.warning(f"Trace end failed: {e}")
            
            return {
                "success": True,
                "result": result,
                "trace_id": trace_id,
                "agent_id": agent_info['id'] if agent_info else None,
                "execution_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
            }
            
        except Exception as e:
            logger.error(f"Flow execution failed: {e}")
            
            # 트레이스 종료 (실패)
            if trace_id:
                try:
                    await agent_trace_adapter.end_trace(
                        trace_id=trace_id,
                        error=str(e)
                    )
                except Exception:
                    pass
            
            return {
                "success": False,
                "error": str(e),
                "trace_id": trace_id,
                "agent_id": agent_info['id'] if agent_info else None,
                "execution_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
            }
    
    async def _call_api(
        self,
        agent_type: AgentType,
        base_url: str,
        flow_id: str,
        inputs: Dict[str, Any],
        extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        실제 API 호출 수행.
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                if agent_type == AgentType.LANGFLOW:
                    return await self._call_langflow(client, base_url, flow_id, inputs, extra_params)
                elif agent_type == AgentType.FLOWISE:
                    return await self._call_flowise(client, base_url, flow_id, inputs, extra_params)
                else:
                    raise ValueError(f"Unsupported agent type: {agent_type}")
                    
            except httpx.TimeoutException:
                raise Exception(f"{agent_type.value} API timeout")
            except httpx.HTTPStatusError as e:
                raise Exception(f"{agent_type.value} API error: {e.response.status_code}")
            except httpx.ConnectError:
                raise Exception(f"{agent_type.value} service not available")
    
    async def _call_langflow(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        flow_id: str,
        inputs: Dict[str, Any],
        extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Langflow API 호출"""
        url = f"{base_url}/api/v1/run/{flow_id}"
        
        payload = {
            "input_value": inputs.get("input_value", inputs.get("question", str(inputs))),
            "output_type": "chat",
            "input_type": "chat",
        }
        
        if extra_params and extra_params.get("tweaks"):
            payload["tweaks"] = extra_params["tweaks"]
        
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Langflow 응답 파싱
        outputs = data.get("outputs", [{}])
        result = outputs[0] if outputs else {}
        
        return {
            "output": result.get("outputs", {}).get("text", result),
            "raw_response": data,
            "cost": 0,  # Langflow doesn't return cost directly
            "total_tokens": 0
        }
    
    async def _call_flowise(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        chatflow_id: str,
        inputs: Dict[str, Any],
        extra_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Flowise API 호출"""
        url = f"{base_url}/api/v1/prediction/{chatflow_id}"
        
        payload = {
            "question": inputs.get("question", str(inputs))
        }
        
        if extra_params and extra_params.get("history"):
            payload["history"] = extra_params["history"]
        
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        return {
            "output": data.get("text", data.get("answer", data)),
            "raw_response": data,
            "cost": 0,
            "total_tokens": data.get("totalTokens", 0)
        }
    
    async def sync_langflow_flows(self) -> List[Dict[str, Any]]:
        """
        Langflow 플로우 목록을 에이전트 레지스트리에 동기화.
        """
        registered = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{LANGFLOW_BASE_URL}/api/v1/flows/")
                response.raise_for_status()
                flows = response.json()
                
                for flow in flows if isinstance(flows, list) else flows.get("flows", []):
                    flow_id = flow.get("id")
                    flow_name = flow.get("name", f"langflow-{flow_id[:8]}")
                    
                    agent = await agent_registry.register_or_get(
                        name=flow_name,
                        agent_type=AgentType.LANGFLOW,
                        project_id=self.project_id,
                        external_id=flow_id,
                        description=flow.get("description", "")
                    )
                    registered.append(agent)
                
                logger.info(f"Synced {len(registered)} Langflow flows")
                
        except Exception as e:
            logger.warning(f"Failed to sync Langflow flows: {e}")
        
        return registered
    
    async def sync_flowise_chatflows(self) -> List[Dict[str, Any]]:
        """
        Flowise 채트플로우 목록을 에이전트 레지스트리에 동기화.
        """
        registered = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{FLOWISE_BASE_URL}/api/v1/chatflows")
                response.raise_for_status()
                chatflows = response.json()
                
                for cf in chatflows if isinstance(chatflows, list) else chatflows.get("chatflows", []):
                    cf_id = cf.get("id")
                    cf_name = cf.get("name", f"flowise-{cf_id[:8]}")
                    
                    agent = await agent_registry.register_or_get(
                        name=cf_name,
                        agent_type=AgentType.FLOWISE,
                        project_id=self.project_id,
                        external_id=cf_id,
                        description=cf.get("description", "")
                    )
                    registered.append(agent)
                
                logger.info(f"Synced {len(registered)} Flowise chatflows")
                
        except Exception as e:
            logger.warning(f"Failed to sync Flowise chatflows: {e}")
        
        return registered


# Singleton
langgraph_service = LangGraphService()
