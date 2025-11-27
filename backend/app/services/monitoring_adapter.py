"""
Monitoring Adapter Service

ClickHouse에서 OTEL 트레이스 데이터를 조회하는 어댑터.
LiteLLM → OTEL Collector → ClickHouse 파이프라인에서 저장된 데이터 조회.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
import json
import os
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ClickHouse 설정
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'monitoring-clickhouse')
CLICKHOUSE_PORT = os.getenv('CLICKHOUSE_HTTP_PORT', '8123')
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', 'password')
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'otel_2')


class MonitoringAdapter:
    """
    Monitoring ClickHouse 어댑터.
    OTEL Collector가 저장한 트레이스 데이터를 ClickHouse에서 조회.
    """
    
    def __init__(self):
        self.base_url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/"
    
    async def _execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """ClickHouse 쿼리 실행 헬퍼 메서드.
        
        Args:
            query: SQL 쿼리 문자열
            params: 쿼리 파라미터 (선택적)
            
        Returns:
            쿼리 결과 리스트
        """
        headers = {
            "X-ClickHouse-User": CLICKHOUSE_USER,
            "X-ClickHouse-Key": CLICKHOUSE_PASSWORD,
        }
        
        # JSONEachRow 형식으로 결과 반환
        full_query = f"{query} FORMAT JSONEachRow"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    content=full_query
                )
                response.raise_for_status()
                
                # JSONEachRow 파싱
                result = []
                for line in response.text.strip().split('\n'):
                    if line:
                        result.append(json.loads(line))
                return result
        except httpx.HTTPStatusError as e:
            error_text = str(e.response.text) if e.response else ""
            # 테이블이 없거나 컬럼이 없는 경우 등 ClickHouse 에러 처리
            if any(err in error_text for err in ["UNKNOWN_TABLE", "does not exist", "UNKNOWN_IDENTIFIER", "Unknown expression"]):
                logger.warning(f"ClickHouse schema issue, returning empty result: {error_text[:200]}")
                return []
            raise
    
    async def get_traces(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """
        트레이스 목록 조회.
        LLM/Agent 호출만 필터링 (auth, postgres 등 내부 호출 제외).
        """
        offset = (page - 1) * size
        
        # 검색 조건
        search_clause = ""
        if search:
            search_clause = f"AND (TraceId LIKE '%{search}%' OR SpanName LIKE '%{search}%')"
        
        # LLM/Agent 호출만 필터링하는 조건
        # - 토큰이 있는 LLM 호출만 표시 (실제 LLM API 호출)
        # - Agent 빌더 (langflow, flowise, autogen) 호출
        # - 토큰이 없는 내부 호출 제외
        llm_filter = """
          AND (
            -- 토큰이 있는 LLM 호출 (실제 API 호출)
            toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens']) > 0
            -- Agent 빌더 호출
            OR SpanName LIKE '%langflow%'
            OR SpanName LIKE '%flowise%'
            OR SpanName LIKE '%autogen%'
            OR ServiceName LIKE '%langflow%'
            OR ServiceName LIKE '%flowise%'
            OR ServiceName LIKE '%autogen%'
          )
        """
        
        # 총 개수
        count_query = f"""
        SELECT count(DISTINCT TraceId) as total
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE ResourceAttributes['project_id'] = '{project_id}'
          AND Timestamp >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
          AND Timestamp <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'
          {llm_filter}
          {search_clause}
        """
        count_result = await self._execute_query(count_query)
        total = count_result[0]['total'] if count_result else 0
        
        # 트레이스 목록 (집계)
        # Note: LiteLLM stores cost in metadata.usage_object as Python dict format
        # Pattern: 'cost': 1.605e-05 - use extractAll with simpler regex
        # If cost is null (streaming mode), calculate from tokens
        list_query = f"""
        SELECT 
            TraceId as trace_id,
            any(ServiceName) as service_name,
            any(SpanName) as span_name,
            min(Timestamp) as start_time,
            sum(Duration) / 1000000 as duration,
            count() as span_count,
            countIf(StatusCode = 'ERROR') as error_count,
            sum(
                greatest(
                    -- Extract cost from metadata.usage_object using extractAll
                    toFloat64OrZero(extractAll(SpanAttributes['metadata.usage_object'], 'cost.: ([0-9.eE-]+)')[1]),
                    -- Fallback: calculate from tokens (OpenRouter qwen pricing)
                    (toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens']) * 0.000000072) +
                    (toUInt64OrZero(SpanAttributes['gen_ai.usage.completion_tokens']) * 0.000000464)
                )
            ) as total_cost,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens'])) as prompt_tokens,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.completion_tokens'])) as completion_tokens
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE ResourceAttributes['project_id'] = '{project_id}'
          AND Timestamp >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
          AND Timestamp <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'
          {llm_filter}
          {search_clause}
        GROUP BY TraceId
        ORDER BY start_time DESC
        LIMIT {size} OFFSET {offset}
        """
        traces = await self._execute_query(list_query)
        
        return {
            "traces": traces,
            "total": total,
            "page": page,
            "size": size
        }
    
    async def get_trace_detail(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        트레이스 상세 조회 (모든 스팬 반환).
        Duration은 나노초에서 밀리초로 변환하여 반환.
        """
        query = f"""
        SELECT 
            TraceId as trace_id,
            SpanId as span_id,
            ParentSpanId as parent_span_id,
            SpanName as span_name,
            ServiceName as service_name,
            Timestamp as timestamp,
            Duration / 1000000 as duration,
            StatusCode as status_code,
            StatusMessage as status_message,
            SpanAttributes as span_attributes,
            ResourceAttributes as resource_attributes,
            project_id
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE TraceId = '{trace_id}'
        ORDER BY Timestamp ASC
        """
        spans = await self._execute_query(query)
        
        if not spans:
            return None
        
        return {
            "trace_id": trace_id,
            "project_id": spans[0].get('project_id', ''),
            "spans": spans
        }
    
    async def get_metrics(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        메트릭 집계.
        LLM/Agent 호출만 집계 (auth, postgres 등 내부 호출 제외).
        """
        # LLM/Agent 호출만 필터링하는 조건
        llm_filter = """
          AND (
            SpanName = 'Received Proxy Server Request'
            OR SpanName LIKE '%litellm%'
            OR SpanName LIKE '%langflow%'
            OR SpanName LIKE '%flowise%'
            OR SpanName LIKE '%autogen%'
            OR SpanName LIKE '%agent%'
            OR SpanName LIKE '%chat%'
            OR SpanName LIKE '%completion%'
            OR SpanAttributes['gen_ai.usage.prompt_tokens'] != ''
          )
        """
        
        # Note: LiteLLM stores cost in multiple places, or calculate from tokens
        query = f"""
        SELECT 
            count(DISTINCT TraceId) as trace_count,
            count() as span_count,
            countIf(StatusCode = 'ERROR') as error_count,
            -- LLM 호출 건수: prompt_tokens가 있는 트레이스
            countDistinctIf(TraceId, SpanAttributes['gen_ai.usage.prompt_tokens'] != '') as llm_call_count,
            -- Agent 호출 건수: langflow, flowise, autogen 관련 트레이스
            countDistinctIf(TraceId, 
                SpanName LIKE '%langflow%' 
                OR SpanName LIKE '%flowise%' 
                OR SpanName LIKE '%autogen%'
                OR SpanName LIKE '%agent%'
            ) as agent_call_count,
            sum(
                greatest(
                    -- Extract cost from metadata.usage_object using extractAll
                    toFloat64OrZero(extractAll(SpanAttributes['metadata.usage_object'], 'cost.: ([0-9.eE-]+)')[1]),
                    -- Fallback: calculate from tokens (OpenRouter qwen pricing)
                    (toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens']) * 0.000000072) +
                    (toUInt64OrZero(SpanAttributes['gen_ai.usage.completion_tokens']) * 0.000000464)
                )
            ) as total_cost,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens'])) as prompt_tokens,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.completion_tokens'])) as completion_tokens,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.cache_read_input_tokens'])) as cache_read_input_tokens,
            sum(toUInt64OrZero(SpanAttributes['llm.usage.reasoning_tokens'])) as reasoning_tokens,
            avg(Duration) / 1000000 as avg_duration,
            quantile(0.5)(Duration) / 1000000 as p50_duration,
            quantile(0.95)(Duration) / 1000000 as p95_duration,
            quantile(0.99)(Duration) / 1000000 as p99_duration
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE ResourceAttributes['project_id'] = '{project_id}'
          AND Timestamp >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
          AND Timestamp <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'
          {llm_filter}
        """
        result = await self._execute_query(query)
        
        return result[0] if result else {
            "trace_count": 0,
            "span_count": 0,
            "error_count": 0,
            "llm_call_count": 0,
            "agent_call_count": 0,
            "total_cost": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cache_read_input_tokens": 0,
            "reasoning_tokens": 0,
            "avg_duration": 0.0,
            "p50_duration": 0.0,
            "p95_duration": 0.0,
            "p99_duration": 0.0
        }
    
    async def get_session_replay(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 리플레이 데이터 생성.
        스팬을 시간순 이벤트로 변환.
        """
        trace_detail = await self.get_trace_detail(trace_id)
        if not trace_detail:
            return None
        
        spans = trace_detail.get('spans', [])
        if not spans:
            return None
        
        # 스팬을 시간순으로 정렬
        sorted_spans = sorted(spans, key=lambda s: s['timestamp'])
        
        # 이벤트로 변환
        events = []
        start_time = None
        
        for span in sorted_spans:
            timestamp_str = span['timestamp']
            # ClickHouse DateTime64 형식 처리
            if isinstance(timestamp_str, str):
                # 나노초 제거
                if '.' in timestamp_str:
                    timestamp_str = timestamp_str.split('.')[0]
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', ''))
            else:
                timestamp = timestamp_str
            
            if start_time is None:
                start_time = timestamp
            
            relative_time = int((timestamp - start_time).total_seconds() * 1000)
            
            # 이벤트 타입 추론
            event_type = self._infer_event_type(span)
            
            events.append({
                'timestamp': timestamp.isoformat(),
                'relative_time': relative_time,
                'type': event_type,
                'span_id': span['span_id'],
                'span_name': span['span_name'],
                'data': self._extract_event_data(span, event_type)
            })
        
        # 마지막 스팬의 종료 시간 계산
        last_span = sorted_spans[-1]
        last_timestamp_str = last_span['timestamp']
        if isinstance(last_timestamp_str, str):
            if '.' in last_timestamp_str:
                last_timestamp_str = last_timestamp_str.split('.')[0]
            last_timestamp = datetime.fromisoformat(last_timestamp_str.replace('Z', ''))
        else:
            last_timestamp = last_timestamp_str
        
        duration_ns = int(last_span.get('duration', 0) or 0)
        total_duration = int((last_timestamp - start_time).total_seconds() * 1000) + int(duration_ns / 1000000)
        
        return {
            'trace_id': trace_id,
            'events': events,
            'timeline': [e['relative_time'] for e in events],
            'total_duration': total_duration,
            'start_time': int(start_time.timestamp() * 1000) if start_time else 0
        }
    
    def _infer_event_type(self, span: Dict[str, Any]) -> str:
        """스팬에서 이벤트 타입 추론"""
        attrs = span.get('span_attributes', {})
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except:
                attrs = {}
        
        span_name = span.get('span_name', '').lower()
        
        # LLM 호출 감지
        if 'gen_ai' in str(attrs) or 'llm' in span_name or 'chat' in span_name:
            return 'llm_call'
        elif 'tool' in span_name:
            return 'tool_use'
        elif span.get('status_code') == 'ERROR':
            return 'error'
        elif 'decision' in str(attrs):
            return 'decision'
        else:
            return 'span_start'
    
    def _extract_event_data(self, span: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        """이벤트 타입별 데이터 추출"""
        attrs = span.get('span_attributes', {})
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except:
                attrs = {}
        
        duration_ns = int(span.get('duration', 0) or 0)
        duration_ms = duration_ns / 1000000 if duration_ns else 0
        
        if event_type == 'llm_call':
            return {
                'model': attrs.get('gen_ai.response.model', attrs.get('llm.model', 'unknown')),
                'prompt': attrs.get('gen_ai.prompt', ''),
                'response': attrs.get('gen_ai.completion', ''),
                'prompt_tokens': int(attrs.get('gen_ai.usage.prompt_tokens', 0)),
                'completion_tokens': int(attrs.get('gen_ai.usage.completion_tokens', 0)),
                'total_tokens': int(attrs.get('gen_ai.usage.total_tokens', 0)),
                'cost': float(attrs.get('gen_ai.usage.cost', 0.0)),
                'latency': duration_ms
            }
        elif event_type == 'tool_use':
            return {
                'tool_name': attrs.get('tool.name', span.get('span_name', 'unknown')),
                'input': attrs.get('tool.input', {}),
                'output': attrs.get('tool.output', {}),
                'duration': duration_ms,
                'status': 'success' if span.get('status_code') != 'ERROR' else 'error'
            }
        elif event_type == 'error':
            return {
                'error_type': attrs.get('error.type', 'UnknownError'),
                'error_message': span.get('status_message', 'Unknown error'),
                'stack_trace': attrs.get('error.stack_trace'),
                'span_id': span['span_id']
            }
        elif event_type == 'decision':
            return {
                'decision_type': attrs.get('decision.type', 'unknown'),
                'reasoning': attrs.get('decision.reasoning', ''),
                'selected_option': attrs.get('decision.selected', ''),
                'alternatives': attrs.get('decision.alternatives', [])
            }
        else:
            return {
                'span_id': span['span_id'],
                'span_name': span['span_name'],
                'status': span.get('status_code', 'UNSET'),
                'duration': duration_ms
            }
    
    async def get_trace_timeline(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        트레이스 타임라인 생성 (계층 구조 포함).
        """
        trace_detail = await self.get_trace_detail(trace_id)
        if not trace_detail:
            return None
        
        spans = trace_detail.get('spans', [])
        if not spans:
            return None
        
        # 스팬을 트리 구조로 변환
        span_nodes = self._build_span_tree(spans)
        
        # 타임라인 정보 계산
        timestamps = []
        end_timestamps = []
        
        for span in spans:
            timestamp_str = span['timestamp']
            if isinstance(timestamp_str, str):
                if '.' in timestamp_str:
                    timestamp_str = timestamp_str.split('.')[0]
                ts = datetime.fromisoformat(timestamp_str.replace('Z', ''))
            else:
                ts = timestamp_str
            timestamps.append(ts)
            
            duration_ns = span.get('duration', 0)
            end_timestamps.append(ts + timedelta(microseconds=duration_ns / 1000))
        
        start_time = min(timestamps) if timestamps else datetime.now()
        end_time = max(end_timestamps) if end_timestamps else start_time
        total_duration = int((end_time - start_time).total_seconds() * 1000)
        
        # 크리티컬 패스 계산 (가장 긴 경로)
        critical_path = self._calculate_critical_path(span_nodes)
        
        return {
            'trace_id': trace_id,
            'spans': span_nodes,
            'total_duration': total_duration,
            'critical_path': critical_path,
            'start_time': int(start_time.timestamp() * 1000),
            'end_time': int(end_time.timestamp() * 1000)
        }
    
    def _build_span_tree(self, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """스팬을 계층 구조로 변환"""
        span_map = {s['span_id']: s for s in spans}
        roots = []
        
        for span in spans:
            timestamp_str = span['timestamp']
            if isinstance(timestamp_str, str):
                if '.' in timestamp_str:
                    timestamp_str = timestamp_str.split('.')[0]
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', ''))
            else:
                timestamp = timestamp_str
            
            duration_ns = int(span.get('duration', 0) or 0)
            duration_ms = duration_ns / 1000000 if duration_ns else 0
            
            node = {
                'span_id': span['span_id'],
                'parent_span_id': span.get('parent_span_id'),
                'span_name': span['span_name'],
                'start_time': int(timestamp.timestamp() * 1000),
                'end_time': int(timestamp.timestamp() * 1000) + int(duration_ms),
                'duration': duration_ms,
                'status': span.get('status_code', 'UNSET'),
                'children': [],
                'attributes': span.get('span_attributes', {}),
                'depth': 0,
                'is_critical_path': False
            }
            
            if not span.get('parent_span_id'):
                roots.append(node)
        
        # 계층 구조 구축
        def attach_children(node, depth=0):
            node['depth'] = depth
            for span in spans:
                if span.get('parent_span_id') == node['span_id']:
                    timestamp_str = span['timestamp']
                    if isinstance(timestamp_str, str):
                        if '.' in timestamp_str:
                            timestamp_str = timestamp_str.split('.')[0]
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', ''))
                    else:
                        timestamp = timestamp_str
                    
                    duration_ns = span.get('duration', 0)
                    duration_ms = duration_ns / 1000000 if duration_ns else 0
                    
                    child = {
                        'span_id': span['span_id'],
                        'parent_span_id': span.get('parent_span_id'),
                        'span_name': span['span_name'],
                        'start_time': int(timestamp.timestamp() * 1000),
                        'end_time': int(timestamp.timestamp() * 1000) + int(duration_ms),
                        'duration': duration_ms,
                        'status': span.get('status_code', 'UNSET'),
                        'children': [],
                        'attributes': span.get('span_attributes', {}),
                        'depth': depth + 1,
                        'is_critical_path': False
                    }
                    node['children'].append(child)
                    attach_children(child, depth + 1)
        
        for root in roots:
            attach_children(root)
        
        return roots
    
    def _calculate_critical_path(self, span_nodes: List[Dict[str, Any]]) -> List[str]:
        """크리티컬 패스 계산 (가장 긴 경로)"""
        def find_longest_path(node):
            if not node['children']:
                return [node['span_id']], node['duration']
            
            longest_path = []
            max_duration = 0
            
            for child in node['children']:
                path, duration = find_longest_path(child)
                if duration > max_duration:
                    max_duration = duration
                    longest_path = path
            
            return [node['span_id']] + longest_path, node['duration'] + max_duration
        
        critical_path = []
        max_duration = 0
        
        for root in span_nodes:
            path, duration = find_longest_path(root)
            if duration > max_duration:
                max_duration = duration
                critical_path = path
        
        # 크리티컬 패스 마킹
        def mark_critical(node):
            if node['span_id'] in critical_path:
                node['is_critical_path'] = True
            for child in node['children']:
                mark_critical(child)
        
        for root in span_nodes:
            mark_critical(root)
        
        return critical_path
    
    async def get_cost_trend(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = 'day'
    ) -> List[Dict[str, Any]]:
        """비용 추이 데이터"""
        # 시간 간격별 그룹화
        if interval == 'hour':
            time_format = "formatDateTime(Timestamp, '%Y-%m-%d %H:00:00')"
        elif interval == 'week':
            time_format = "formatDateTime(Timestamp, '%Y-%W')"
        else:  # day
            time_format = "formatDateTime(Timestamp, '%Y-%m-%d')"
        
        query = f"""
        SELECT 
            {time_format} as timestamp,
            sum(toFloat64OrZero(SpanAttributes['gen_ai.usage.cost'])) as cost
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE ResourceAttributes['project_id'] = '{project_id}'
          AND Timestamp >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
          AND Timestamp <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'
        GROUP BY timestamp
        ORDER BY timestamp ASC
        """
        results = await self._execute_query(query)
        
        return [
            {
                'timestamp': r['timestamp'],
                'cost': float(r['cost'] or 0)
            }
            for r in results
        ]
    
    async def get_token_usage(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = 'day'
    ) -> List[Dict[str, Any]]:
        """토큰 사용량 추이"""
        if interval == 'hour':
            time_format = "formatDateTime(Timestamp, '%Y-%m-%d %H:00:00')"
        elif interval == 'week':
            time_format = "formatDateTime(Timestamp, '%Y-%W')"
        else:
            time_format = "formatDateTime(Timestamp, '%Y-%m-%d')"
        
        query = f"""
        SELECT 
            {time_format} as timestamp,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens'])) as prompt_tokens,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.completion_tokens'])) as completion_tokens,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.cache_read_input_tokens'])) as cache_hits
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE ResourceAttributes['project_id'] = '{project_id}'
          AND Timestamp >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
          AND Timestamp <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'
        GROUP BY timestamp
        ORDER BY timestamp ASC
        """
        results = await self._execute_query(query)
        
        return [
            {
                'timestamp': r['timestamp'],
                'prompt_tokens': int(r['prompt_tokens'] or 0),
                'completion_tokens': int(r['completion_tokens'] or 0),
                'cache_hits': int(r['cache_hits'] or 0)
            }
            for r in results
        ]
    
    async def get_performance_metrics(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """성능 메트릭 (레이턴시 분포)"""
        query = f"""
        SELECT 
            TraceId as trace_id,
            min(Timestamp) as timestamp,
            sum(Duration) / 1000000 as duration,
            if(countIf(StatusCode = 'ERROR') > 0, 'error', 'success') as status
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE ResourceAttributes['project_id'] = '{project_id}'
          AND Timestamp >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
          AND Timestamp <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'
        GROUP BY TraceId
        ORDER BY timestamp ASC
        """
        results = await self._execute_query(query)
        
        return [
            {
                'timestamp': r['timestamp'],
                'duration': int(r['duration'] or 0),
                'status': r['status']
            }
            for r in results
        ]
    
    async def get_agent_flow_graph(
        self,
        project_id: str,
        trace_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        에이전트 플로우 그래프 데이터.
        실제 호출 흐름을 표현:
        [Client] → [Input Guardrail] → [LiteLLM Proxy] → [LLM Provider] → [Output Guardrail]
                                              ↓
                                       [Agent Builder]
                                              ↓
                                         [MCP Tools]
        
        가드레일 모니터링:
        - Input Guardrail: 입력 검증 (PII 감지, 프롬프트 인젝션 방지)
        - Output Guardrail: 출력 검증 (유해 콘텐츠 필터링, 형식 검증)
        - 가드레일 차단 시 StatusCode = 'Error' 또는 특정 패턴으로 감지
        """
        where_clause = f"project_id = '{project_id}'"
        if trace_id:
            where_clause += f" AND TraceId = '{trace_id}'"
        if start_time and end_time:
            where_clause += f" AND Timestamp >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'"
            where_clause += f" AND Timestamp <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        # 각 단계별 통계 조회 (가드레일 포함)
        query = f"""
        SELECT 
            CASE 
                WHEN SpanName = 'Received Proxy Server Request' THEN 'Client Request'
                WHEN SpanName = 'proxy_pre_call' THEN 'Input Guardrail'
                WHEN SpanName = 'litellm_request' THEN 'LiteLLM Proxy'
                WHEN SpanName = 'raw_gen_ai_request' THEN 'LLM Provider'
                WHEN SpanName LIKE '%langflow%' OR ServiceName LIKE '%langflow%' THEN 'Langflow Agent'
                WHEN SpanName LIKE '%flowise%' OR ServiceName LIKE '%flowise%' THEN 'Flowise Agent'
                WHEN SpanName LIKE '%autogen%' OR ServiceName LIKE '%autogen%' THEN 'AutoGen Agent'
                WHEN SpanName LIKE '%mcp%' OR SpanAttributes['metadata.mcp_tool_call_metadata'] != '' THEN 'MCP Tools'
                WHEN SpanName = 'batch_write_to_db' THEN 'Output Guardrail'
                ELSE NULL
            END as stage,
            count(DISTINCT TraceId) as call_count,
            avg(Duration) / 1000000 as avg_latency_ms,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens'])) as total_prompt_tokens,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.completion_tokens'])) as total_completion_tokens,
            sum(
                greatest(
                    toFloat64OrZero(extractAll(SpanAttributes['metadata.usage_object'], 'cost.: ([0-9.eE-]+)')[1]),
                    (toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens']) * 0.000000072) +
                    (toUInt64OrZero(SpanAttributes['gen_ai.usage.completion_tokens']) * 0.000000464)
                )
            ) as total_cost,
            countIf(StatusCode = 'Error') as error_count,
            countIf(SpanAttributes['metadata.applied_guardrails'] != '[]' AND SpanAttributes['metadata.applied_guardrails'] != '') as guardrail_applied_count
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE {where_clause}
        GROUP BY stage
        HAVING stage IS NOT NULL
        ORDER BY 
            CASE stage
                WHEN 'Client Request' THEN 1
                WHEN 'Input Guardrail' THEN 2
                WHEN 'LiteLLM Proxy' THEN 3
                WHEN 'LLM Provider' THEN 4
                WHEN 'Langflow Agent' THEN 5
                WHEN 'Flowise Agent' THEN 5
                WHEN 'AutoGen Agent' THEN 5
                WHEN 'MCP Tools' THEN 6
                WHEN 'Output Guardrail' THEN 7
                ELSE 8
            END
        """
        results = await self._execute_query(query)
        
        # 노드 생성 (각 단계)
        nodes = []
        stage_colors = {
            'Client Request': '#3B82F6',      # blue
            'Input Guardrail': '#F97316',     # orange (가드레일)
            'LiteLLM Proxy': '#10B981',       # green
            'LLM Provider': '#8B5CF6',        # purple
            'Langflow Agent': '#F59E0B',      # amber
            'Flowise Agent': '#F59E0B',       # amber
            'AutoGen Agent': '#F59E0B',       # amber
            'MCP Tools': '#EC4899',           # pink
            'Output Guardrail': '#F97316',    # orange (가드레일)
        }
        
        for i, r in enumerate(results):
            stage = r['stage']
            total_tokens = int(r['total_prompt_tokens'] or 0) + int(r['total_completion_tokens'] or 0)
            error_count = int(r['error_count'] or 0)
            guardrail_applied = int(r['guardrail_applied_count'] or 0)
            
            nodes.append({
                'id': f'stage-{i}',
                'label': stage,
                'type': 'stage',
                'position': {'x': 100 + i * 200, 'y': 150},
                'data': {
                    'stage_name': stage,
                    'call_count': int(r['call_count'] or 0),
                    'avg_latency_ms': round(float(r['avg_latency_ms'] or 0), 1),
                    'total_tokens': total_tokens,
                    'prompt_tokens': int(r['total_prompt_tokens'] or 0),
                    'completion_tokens': int(r['total_completion_tokens'] or 0),
                    'total_cost': float(r['total_cost'] or 0),
                    'error_count': error_count,
                    'guardrail_applied': guardrail_applied,
                    'color': stage_colors.get(stage, '#6B7280'),
                    'is_guardrail': 'Guardrail' in stage
                }
            })
        
        # 엣지 생성 (순차적 흐름)
        edges = []
        for i in range(len(nodes) - 1):
            source_node = nodes[i]
            target_node = nodes[i + 1]
            
            # 가드레일 차단 여부 표시
            blocked = target_node['data']['error_count'] > 0 and 'Guardrail' in target_node['data']['stage_name']
            
            edges.append({
                'id': f'e{i}',
                'source': source_node['id'],
                'target': target_node['id'],
                'animated': not blocked,
                'data': {
                    'label': f"{target_node['data']['call_count']} calls",
                    'blocked': blocked
                }
            })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    async def get_guardrail_stats(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        가드레일 통계 조회.
        
        가드레일 유형:
        - Input Guardrail: 입력 검증 (proxy_pre_call 단계)
        - Output Guardrail: 출력 검증 (batch_write_to_db 단계)
        - Cost Guardrail: 비용 제한 초과
        - Rate Limit: 요청 빈도 제한
        
        감지 방법:
        - StatusCode = 'Error': 가드레일 차단
        - metadata.applied_guardrails: 적용된 가드레일 목록
        - 특정 에러 메시지 패턴
        """
        query = f"""
        SELECT 
            -- 전체 요청 수
            count(DISTINCT TraceId) as total_requests,
            
            -- 가드레일 적용된 요청 수
            countDistinctIf(TraceId, SpanAttributes['metadata.applied_guardrails'] != '[]' AND SpanAttributes['metadata.applied_guardrails'] != '') as guardrail_applied,
            
            -- 가드레일에 의해 차단된 요청 수 (Error 상태)
            countDistinctIf(TraceId, StatusCode = 'Error') as blocked_requests,
            
            -- 입력 가드레일 통계
            countIf(SpanName = 'proxy_pre_call') as input_guardrail_checks,
            countIf(SpanName = 'proxy_pre_call' AND StatusCode = 'Error') as input_guardrail_blocks,
            
            -- 출력 가드레일 통계 (batch_write_to_db에서 에러 발생 시)
            countIf(SpanName = 'batch_write_to_db') as output_guardrail_checks,
            countIf(SpanName = 'batch_write_to_db' AND StatusCode = 'Error') as output_guardrail_blocks,
            
            -- 비용 관련 (토큰 사용량)
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens'])) as total_prompt_tokens,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.completion_tokens'])) as total_completion_tokens,
            
            -- 평균 응답 시간 (가드레일 포함)
            avg(Duration) / 1000000 as avg_latency_ms
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE ResourceAttributes['project_id'] = '{project_id}'
          AND Timestamp >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
          AND Timestamp <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'
        """
        result = await self._execute_query(query)
        
        if not result:
            return {
                'total_requests': 0,
                'guardrail_applied': 0,
                'blocked_requests': 0,
                'block_rate': 0.0,
                'input_guardrail': {'checks': 0, 'blocks': 0, 'block_rate': 0.0},
                'output_guardrail': {'checks': 0, 'blocks': 0, 'block_rate': 0.0},
                'token_usage': {'prompt': 0, 'completion': 0, 'total': 0},
                'avg_latency_ms': 0.0
            }
        
        r = result[0]
        total_requests = int(r['total_requests'] or 0)
        blocked_requests = int(r['blocked_requests'] or 0)
        
        input_checks = int(r['input_guardrail_checks'] or 0)
        input_blocks = int(r['input_guardrail_blocks'] or 0)
        
        output_checks = int(r['output_guardrail_checks'] or 0)
        output_blocks = int(r['output_guardrail_blocks'] or 0)
        
        prompt_tokens = int(r['total_prompt_tokens'] or 0)
        completion_tokens = int(r['total_completion_tokens'] or 0)
        
        return {
            'total_requests': total_requests,
            'guardrail_applied': int(r['guardrail_applied'] or 0),
            'blocked_requests': blocked_requests,
            'block_rate': round((blocked_requests / total_requests * 100) if total_requests > 0 else 0, 2),
            'input_guardrail': {
                'checks': input_checks,
                'blocks': input_blocks,
                'block_rate': round((input_blocks / input_checks * 100) if input_checks > 0 else 0, 2)
            },
            'output_guardrail': {
                'checks': output_checks,
                'blocks': output_blocks,
                'block_rate': round((output_blocks / output_checks * 100) if output_checks > 0 else 0, 2)
            },
            'token_usage': {
                'prompt': prompt_tokens,
                'completion': completion_tokens,
                'total': prompt_tokens + completion_tokens
            },
            'avg_latency_ms': round(float(r['avg_latency_ms'] or 0), 1)
        }
    
    async def get_agent_usage_stats(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        에이전트별 사용량 통계 조회.
        Agent 호출만 필터링 (langflow, flowise, autogen 등).
        LiteLLM 프록시 호출은 제외 (LLM 호출은 별도 집계).
        """
        # Agent 호출만 필터링 (LiteLLM 프록시 제외)
        agent_filter = """
          AND (
            SpanName LIKE '%langflow%'
            OR SpanName LIKE '%flowise%'
            OR SpanName LIKE '%autogen%'
            OR SpanName LIKE '%agent%'
            OR ServiceName LIKE '%langflow%'
            OR ServiceName LIKE '%flowise%'
            OR ServiceName LIKE '%autogen%'
          )
          AND ServiceName != 'litellm-proxy'
        """
        
        query = f"""
        SELECT 
            ServiceName as agent_name,
            count(DISTINCT TraceId) as event_count,
            sum(toUInt64OrZero(SpanAttributes['gen_ai.usage.total_tokens'])) as total_tokens,
            sum(
                greatest(
                    -- Extract cost from metadata.usage_object using extractAll
                    toFloat64OrZero(extractAll(SpanAttributes['metadata.usage_object'], 'cost.: ([0-9.eE-]+)')[1]),
                    -- Fallback: calculate from tokens (OpenRouter qwen pricing)
                    (toUInt64OrZero(SpanAttributes['gen_ai.usage.prompt_tokens']) * 0.000000072) +
                    (toUInt64OrZero(SpanAttributes['gen_ai.usage.completion_tokens']) * 0.000000464)
                )
            ) as total_cost,
            avg(Duration) / 1000000 as avg_latency_ms,
            countIf(StatusCode = 'ERROR') as error_count
        FROM {CLICKHOUSE_DATABASE}.otel_traces
        WHERE ResourceAttributes['project_id'] = '{project_id}'
          AND Timestamp >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
          AND Timestamp <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'
          {agent_filter}
        GROUP BY agent_name
        ORDER BY event_count DESC
        """
        results = await self._execute_query(query)
        
        agent_stats = []
        for row in results:
            event_count = int(row['event_count'] or 0)
            error_count = int(row['error_count'] or 0)
            success_count = event_count - error_count
            success_rate = (success_count / event_count * 100) if event_count > 0 else 100.0
            
            agent_stats.append({
                'agent_name': row['agent_name'] or 'Unknown Agent',
                'total_tokens': int(row['total_tokens'] or 0),
                'total_cost': float(row['total_cost'] or 0),
                'event_count': event_count,
                'avg_latency': round(float(row['avg_latency_ms'] or 0), 2),
                'error_count': error_count,
                'success_rate': round(success_rate, 1)
            })
        
        return agent_stats


# Singleton
monitoring_adapter = MonitoringAdapter()
