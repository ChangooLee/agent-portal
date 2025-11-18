"""
LangGraph Service

Langflow/Flowise/AutoGen 플로우 실행 + AgentOps 스팬 기록.
"""

from typing import Dict, Any
from datetime import datetime
import uuid
import json
from app.services.agentops_adapter import agentops_adapter


class LangGraphService:
    """
    LangGraph 플로우 실행 서비스.
    AgentOps 로컬 어댑터와 통합하여 스팬 기록.
    """
    
    def __init__(self):
        self.project_id = "default-project"
    
    async def execute_flow(
        self,
        flow_id: str,
        flow_name: str,
        inputs: Dict[str, Any],
        tags: list = None
    ) -> Dict[str, Any]:
        """
        플로우 실행 + AgentOps 스팬 기록.
        
        Args:
            flow_id: 플로우 ID
            flow_name: 플로우 이름
            inputs: 입력 데이터
            tags: 태그 목록
            
        Returns:
            실행 결과 + trace_id + agentops_url
        """
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        try:
            # 플로우 실행 (실제 구현은 Langflow/Flowise/AutoGen API 호출)
            result = await self._run_flow(flow_id, inputs)
            
            # 성공 스팬 기록
            end_time = datetime.utcnow()
            duration_ns = int((end_time - start_time).total_seconds() * 1_000_000_000)
            
            span_data = {
                "project_id": self.project_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "parent_span_id": None,
                "timestamp": start_time,
                "duration": duration_ns,
                "status_code": "OK",
                "status_message": None,
                "span_name": f"{flow_name}.execution",
                "span_kind": "INTERNAL",
                "service_name": "agent-portal",
                "resource_attributes": json.dumps({"service.name": "agent-portal"}),
                "span_attributes": json.dumps({
                    "flow_id": flow_id,
                    "flow_name": flow_name,
                    "inputs": inputs,
                    "outputs": result,
                    "gen_ai.usage.total_cost": result.get("cost", 0),
                    "gen_ai.usage.prompt_tokens": result.get("prompt_tokens", 0),
                    "gen_ai.usage.completion_tokens": result.get("completion_tokens", 0),
                    "agentops.tags": json.dumps(tags or ["production"])
                })
            }
            
            await agentops_adapter.record_span(span_data)
            
            return {
                "result": result,
                "trace_id": trace_id,
                "agentops_url": f"http://localhost:3004/traces?trace_id={trace_id}"
            }
        
        except Exception as e:
            # 실패 스팬 기록
            end_time = datetime.utcnow()
            duration_ns = int((end_time - start_time).total_seconds() * 1_000_000_000)
            
            span_data = {
                "project_id": self.project_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "parent_span_id": None,
                "timestamp": start_time,
                "duration": duration_ns,
                "status_code": "ERROR",
                "status_message": str(e),
                "span_name": f"{flow_name}.execution",
                "span_kind": "INTERNAL",
                "service_name": "agent-portal",
                "resource_attributes": json.dumps({"service.name": "agent-portal"}),
                "span_attributes": json.dumps({
                    "flow_id": flow_id,
                    "flow_name": flow_name,
                    "inputs": inputs,
                    "error": str(e),
                    "agentops.tags": json.dumps((tags or []) + ["error"])
                })
            }
            
            await agentops_adapter.record_span(span_data)
            
            raise
    
    async def _run_flow(self, flow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        실제 플로우 실행 (Langflow/Flowise/AutoGen API 호출).
        
        TODO: Langflow API 호출 구현
        - POST http://langflow:7860/api/v1/run/{flow_id}
        - 입력 데이터 전달
        - 결과 파싱 (outputs, cost, tokens)
        """
        # Placeholder implementation
        return {
            "outputs": {"message": "Hello from flow"},
            "cost": 0.001,
            "prompt_tokens": 100,
            "completion_tokens": 50
        }


# Singleton
langgraph_service = LangGraphService()

