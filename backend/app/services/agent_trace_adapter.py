"""
Agent Trace Adapter

에이전트 트레이스 시작/종료를 관리하고 OTEL Collector 또는 ClickHouse에 저장.
LLM 호출과 연결할 수 있도록 parent_trace_id를 제공.
"""

import os
import uuid
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import httpx
import aiomysql

logger = logging.getLogger(__name__)


class AgentTraceAdapter:
    """
    에이전트 트레이스 어댑터.
    
    에이전트 실행의 시작과 종료를 추적하고,
    하위 LLM 호출과 연결할 수 있도록 trace_id를 관리.
    """
    
    def __init__(self):
        # MariaDB 설정 (트레이스 메타데이터 저장)
        self.db_host = os.getenv("MARIADB_HOST", "mariadb")
        self.db_port = int(os.getenv("MARIADB_PORT", "3306"))
        self.db_user = os.getenv("MARIADB_USER", "root")
        self.db_password = os.getenv("MARIADB_ROOT_PASSWORD", "rootpass")
        self.db_name = os.getenv("MARIADB_DATABASE", "agent_portal")
        
        # OTEL Collector 설정 (HTTP endpoint)
        self.otel_endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://monitoring-otel-collector:4318"
        )
        
        # ClickHouse 설정 (직접 삽입용)
        self.clickhouse_host = os.getenv("CLICKHOUSE_HOST", "monitoring-clickhouse")
        self.clickhouse_port = int(os.getenv("CLICKHOUSE_HTTP_PORT", "8123"))
        self.clickhouse_database = os.getenv("CLICKHOUSE_DATABASE", "otel_2")
        
        self._pool: Optional[aiomysql.Pool] = None
        self._active_traces: Dict[str, Dict[str, Any]] = {}
        
        logger.info("AgentTraceAdapter initialized")
    
    async def _get_pool(self) -> aiomysql.Pool:
        """MariaDB 커넥션 풀 획득"""
        if self._pool is None or self._pool.closed:
            self._pool = await aiomysql.create_pool(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                db=self.db_name,
                charset='utf8mb4',
                autocommit=True,
                minsize=1,
                maxsize=10
            )
        return self._pool
    
    async def start_trace(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        project_id: str = "default-project",
        inputs: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None
    ) -> str:
        """
        에이전트 트레이스 시작.
        
        Args:
            agent_id: 에이전트 ID
            agent_name: 에이전트 이름
            agent_type: 에이전트 유형
            project_id: 프로젝트 ID
            inputs: 입력 데이터
            tags: 태그 목록
            
        Returns:
            trace_id: 생성된 트레이스 ID (LLM 호출 시 parent_trace_id로 사용)
        """
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        start_time = datetime.utcnow()
        
        # 활성 트레이스에 저장
        self._active_traces[trace_id] = {
            'agent_id': agent_id,
            'agent_name': agent_name,
            'agent_type': agent_type,
            'project_id': project_id,
            'span_id': span_id,
            'start_time': start_time,
            'inputs': inputs,
            'tags': tags or []
        }
        
        logger.info(f"Trace started: {trace_id} for agent {agent_name}")
        return trace_id
    
    async def end_trace(
        self,
        trace_id: str,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        cost: float = 0.0,
        tokens: int = 0
    ) -> bool:
        """
        에이전트 트레이스 종료.
        
        Args:
            trace_id: 시작 시 반환된 트레이스 ID
            outputs: 출력 데이터
            error: 에러 메시지 (있는 경우)
            cost: 총 비용
            tokens: 총 토큰 수
            
        Returns:
            성공 여부
        """
        if trace_id not in self._active_traces:
            logger.warning(f"Trace not found: {trace_id}")
            return False
        
        trace_data = self._active_traces.pop(trace_id)
        end_time = datetime.utcnow()
        duration_ns = int((end_time - trace_data['start_time']).total_seconds() * 1_000_000_000)
        
        status_code = "ERROR" if error else "OK"
        
        # 스팬 데이터 구성
        span_data = {
            'trace_id': trace_id,
            'span_id': trace_data['span_id'],
            'parent_span_id': '',
            'project_id': trace_data['project_id'],
            'agent_id': trace_data['agent_id'],
            'agent_name': trace_data['agent_name'],
            'agent_type': trace_data['agent_type'],
            'span_name': f"{trace_data['agent_name']}.execution",
            'span_kind': 'INTERNAL',
            'service_name': f"agent-{trace_data['agent_type']}",
            'start_time': trace_data['start_time'],
            'end_time': end_time,
            'duration_ns': duration_ns,
            'status_code': status_code,
            'status_message': error,
            'inputs': trace_data['inputs'],
            'outputs': outputs,
            'cost': cost,
            'tokens': tokens,
            'tags': trace_data['tags']
        }
        
        # ClickHouse에 직접 저장
        success = await self._save_to_clickhouse(span_data)
        
        # MariaDB agent_sessions 테이블에도 저장 (기존 호환성)
        await self._save_to_mariadb(span_data)
        
        logger.info(f"Trace ended: {trace_id}, status={status_code}, duration={duration_ns/1_000_000}ms")
        return success
    
    async def _save_to_clickhouse(self, span_data: Dict[str, Any]) -> bool:
        """ClickHouse에 스팬 저장"""
        try:
            # otel_traces 테이블에 맞는 형식으로 변환
            resource_attrs = {
                'service.name': span_data['service_name'],
                'project_id': span_data['project_id']
            }
            
            span_attrs = {
                'agent.id': span_data['agent_id'],
                'agent.name': span_data['agent_name'],
                'agent.type': span_data['agent_type'],
                'metadata.agent_id': span_data['agent_id'],
                'metadata.agent_name': span_data['agent_name'],
                'gen_ai.usage.total_cost': str(span_data['cost']),
                'gen_ai.usage.total_tokens': str(span_data['tokens'])
            }
            
            if span_data['inputs']:
                span_attrs['agent.inputs'] = json.dumps(span_data['inputs'])[:1000]
            if span_data['outputs']:
                span_attrs['agent.outputs'] = json.dumps(span_data['outputs'])[:1000]
            if span_data['tags']:
                span_attrs['agent.tags'] = json.dumps(span_data['tags'])
            
            # ClickHouse INSERT 쿼리
            query = f"""
            INSERT INTO {self.clickhouse_database}.otel_traces (
                Timestamp,
                TraceId,
                SpanId,
                ParentSpanId,
                TraceState,
                SpanName,
                SpanKind,
                ServiceName,
                ResourceAttributes,
                ScopeName,
                ScopeVersion,
                SpanAttributes,
                Duration,
                StatusCode,
                StatusMessage,
                Events.Timestamp,
                Events.Name,
                Events.Attributes,
                Links.TraceId,
                Links.SpanId,
                Links.TraceState,
                Links.Attributes
            ) VALUES (
                '{span_data['start_time'].strftime('%Y-%m-%d %H:%M:%S.%f')}',
                '{span_data['trace_id']}',
                '{span_data['span_id']}',
                '{span_data['parent_span_id']}',
                '',
                '{span_data['span_name']}',
                '{span_data['span_kind']}',
                '{span_data['service_name']}',
                {self._format_map(resource_attrs)},
                'agent-portal',
                '1.0.0',
                {self._format_map(span_attrs)},
                {span_data['duration_ns']},
                '{span_data['status_code']}',
                '{span_data.get('status_message') or ''}',
                [],
                [],
                [],
                [],
                [],
                [],
                []
            )
            """
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"http://{self.clickhouse_host}:{self.clickhouse_port}/",
                    params={"query": query, "user": "default", "password": "password"}
                )
                
                if response.status_code == 200:
                    logger.debug(f"Span saved to ClickHouse: {span_data['trace_id']}")
                    return True
                else:
                    logger.error(f"ClickHouse insert failed: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to save span to ClickHouse: {e}")
            return False
    
    async def _save_to_mariadb(self, span_data: Dict[str, Any]) -> None:
        """MariaDB agent_sessions에 저장 (기존 호환성)"""
        try:
            pool = await self._get_pool()
            
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO agent_sessions (
                            session_id, project_id, agent_name, status,
                            start_time, end_time, duration, tags,
                            total_cost, total_tokens, error_message
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            end_time = VALUES(end_time),
                            duration = VALUES(duration),
                            status = VALUES(status),
                            total_cost = VALUES(total_cost),
                            total_tokens = VALUES(total_tokens),
                            error_message = VALUES(error_message)
                    """, (
                        span_data['trace_id'],
                        span_data['project_id'],
                        span_data['agent_name'],
                        'error' if span_data['status_code'] == 'ERROR' else 'completed',
                        span_data['start_time'],
                        span_data['end_time'],
                        span_data['duration_ns'] // 1_000_000,  # ms
                        json.dumps(span_data['tags']),
                        span_data['cost'],
                        span_data['tokens'],
                        span_data.get('status_message')
                    ))
                    
        except Exception as e:
            logger.error(f"Failed to save to MariaDB: {e}")
    
    def _format_map(self, d: Dict[str, Any]) -> str:
        """ClickHouse Map 형식으로 변환"""
        if not d:
            return "map()"
        
        pairs = []
        for k, v in d.items():
            # 값을 문자열로 변환하고 이스케이프
            v_str = str(v).replace("'", "\\'")
            pairs.append(f"'{k}', '{v_str}'")
        
        return f"map({', '.join(pairs)})"
    
    def get_active_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """활성 트레이스 조회"""
        return self._active_traces.get(trace_id)
    
    def get_active_traces_count(self) -> int:
        """활성 트레이스 수 조회"""
        return len(self._active_traces)


# Singleton instance
agent_trace_adapter = AgentTraceAdapter()

