"""
AgentOps Adapter Service

ClickHouse 쿼리를 MariaDB로 변환하는 어댑터.
AgentOps API 호출 없이 로컬 DB만 사용.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import aiomysql
import json
import os
from app.config import get_settings

settings = get_settings()

# 환경 변수에서 직접 읽기 (Docker 환경에서 더 안정적)
MARIADB_ROOT_PASSWORD = os.getenv('MARIADB_ROOT_PASSWORD', settings.MARIADB_ROOT_PASSWORD)
MARIADB_DATABASE = os.getenv('MARIADB_DATABASE', settings.MARIADB_DATABASE)


class AgentOpsAdapter:
    """
    AgentOps ClickHouse 쿼리를 MariaDB로 변환하는 어댑터.
    AgentOps API 호출 없이 로컬 DB만 사용.
    """
    
    def __init__(self):
        self.pool = None
    
    async def get_pool(self):
        """MariaDB 연결 풀 가져오기"""
        if not self.pool:
            self.pool = await aiomysql.create_pool(
                host='mariadb',
                port=3306,
                user='root',
                password=MARIADB_ROOT_PASSWORD,
                db=MARIADB_DATABASE,
                autocommit=True,
                charset='utf8mb4'
            )
        return self.pool
    
    async def _execute_query(self, query: str, params: tuple) -> List[Dict[str, Any]]:
        """SQL 쿼리 실행 헬퍼 메서드.
        
        Args:
            query: SQL 쿼리 문자열
            params: 쿼리 파라미터
            
        Returns:
            쿼리 결과 리스트
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                result = await cursor.fetchall()
                return result
    
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
        트레이스 목록 조회 (TraceSummaryModel 대체).
        AgentOps /api/v4/traces/ 엔드포인트 호환.
        """
        pool = await self.get_pool()
        offset = (page - 1) * size
        
        # 검색 조건
        search_clause = ""
        search_params = []
        if search:
            search_clause = """
            AND (trace_id LIKE %s 
                 OR root_span_name LIKE %s 
                 OR JSON_SEARCH(tags, 'one', %s) IS NOT NULL)
            """
            search_pattern = f"%{search}%"
            search_params = [search_pattern, search_pattern, search_pattern]
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 총 개수
                count_query = f"""
                SELECT COUNT(*) as total
                FROM trace_summaries
                WHERE project_id = %s
                  AND start_time >= %s
                  AND start_time <= %s
                  {search_clause}
                """
                await cursor.execute(count_query, [project_id, start_time, end_time] + search_params)
                total_result = await cursor.fetchone()
                total = total_result['total'] if total_result else 0
                
                # 트레이스 목록
                list_query = f"""
                SELECT 
                    trace_id,
                    service_name,
                    root_span_name as span_name,
                    start_time,
                    duration,
                    span_count,
                    error_count,
                    tags,
                    total_cost
                FROM trace_summaries
                WHERE project_id = %s
                  AND start_time >= %s
                  AND start_time <= %s
                  {search_clause}
                ORDER BY start_time DESC
                LIMIT %s OFFSET %s
                """
                await cursor.execute(
                    list_query,
                    [project_id, start_time, end_time] + search_params + [size, offset]
                )
                traces = await cursor.fetchall()
                
                return {
                    "traces": traces,
                    "total": total,
                    "page": page,
                    "size": size
                }
    
    async def get_trace_detail(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        트레이스 상세 조회 (TraceModel 대체).
        모든 스팬 반환.
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                SELECT *
                FROM otel_traces
                WHERE trace_id = %s
                ORDER BY timestamp ASC
                """
                await cursor.execute(query, (trace_id,))
                spans = await cursor.fetchall()
                
                if not spans:
                    return None
                
                return {
                    "trace_id": trace_id,
                    "project_id": spans[0]['project_id'],
                    "spans": spans
                }
    
    async def get_metrics(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        메트릭 집계 (TraceListMetricsModel 대체).
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                SELECT 
                    COUNT(DISTINCT trace_id) as trace_count,
                    SUM(span_count) as span_count,
                    SUM(error_count) as error_count,
                    SUM(total_cost) as total_cost,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    SUM(cache_read_input_tokens) as cache_read_input_tokens,
                    SUM(reasoning_tokens) as reasoning_tokens
                FROM trace_summaries
                WHERE project_id = %s
                  AND start_time >= %s
                  AND start_time <= %s
                """
                await cursor.execute(query, (project_id, start_time, end_time))
                metrics = await cursor.fetchone()
                
                return metrics if metrics else {}
    
    async def record_span(self, span_data: Dict[str, Any]):
        """
        스팬 기록 (Langflow/Flowise/AutoGen 실행 시 호출).
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # otel_traces 삽입
                insert_query = """
                INSERT INTO otel_traces (
                    project_id, trace_id, span_id, parent_span_id,
                    timestamp, duration, status_code, status_message,
                    span_name, span_kind, service_name,
                    resource_attributes, span_attributes
                ) VALUES (
                    %(project_id)s, %(trace_id)s, %(span_id)s, %(parent_span_id)s,
                    %(timestamp)s, %(duration)s, %(status_code)s, %(status_message)s,
                    %(span_name)s, %(span_kind)s, %(service_name)s,
                    %(resource_attributes)s, %(span_attributes)s
                )
                """
                await cursor.execute(insert_query, span_data)
                
                # trace_summaries 업데이트 (집계)
                await self._update_trace_summary(conn, span_data['trace_id'])
    
    async def _update_trace_summary(self, conn, trace_id: str):
        """
        트레이스 요약 업데이트 (집계).
        """
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = """
            INSERT INTO trace_summaries (
                trace_id, project_id, service_name, root_span_name,
                start_time, end_time, duration, span_count, error_count,
                tags, total_cost, prompt_tokens, completion_tokens
            )
            SELECT 
                trace_id,
                ANY_VALUE(project_id) as project_id,
                ANY_VALUE(service_name) as service_name,
                (SELECT span_name FROM otel_traces WHERE trace_id = t.trace_id ORDER BY timestamp ASC LIMIT 1) as root_span_name,
                MIN(timestamp) as start_time,
                MAX(TIMESTAMPADD(MICROSECOND, duration/1000, timestamp)) as end_time,
                TIMESTAMPDIFF(MICROSECOND, MIN(timestamp), MAX(TIMESTAMPADD(MICROSECOND, duration/1000, timestamp))) * 1000 as duration,
                COUNT(*) as span_count,
                SUM(CASE WHEN status_code = 'ERROR' THEN 1 ELSE 0 END) as error_count,
                JSON_EXTRACT(ANY_VALUE(span_attributes), '$.\"agentops.tags\"') as tags,
                SUM(CAST(JSON_UNQUOTE(JSON_EXTRACT(span_attributes, '$.\"gen_ai.usage.total_cost\"')) AS DECIMAL(10,6))) as total_cost,
                SUM(CAST(JSON_UNQUOTE(JSON_EXTRACT(span_attributes, '$.\"gen_ai.usage.prompt_tokens\"')) AS UNSIGNED)) as prompt_tokens,
                SUM(CAST(JSON_UNQUOTE(JSON_EXTRACT(span_attributes, '$.\"gen_ai.usage.completion_tokens\"')) AS UNSIGNED)) as completion_tokens
            FROM otel_traces t
            WHERE trace_id = %s
            GROUP BY trace_id
            ON DUPLICATE KEY UPDATE
                end_time = VALUES(end_time),
                duration = VALUES(duration),
                span_count = VALUES(span_count),
                error_count = VALUES(error_count),
                total_cost = VALUES(total_cost),
                prompt_tokens = VALUES(prompt_tokens),
                completion_tokens = VALUES(completion_tokens),
                updated_at = CURRENT_TIMESTAMP
            """
            await cursor.execute(query, (trace_id,))


    async def get_session_replay(self, trace_id: str) -> Dict[str, Any]:
        """
        세션 리플레이 데이터 생성.
        스팬을 시간순 이벤트로 변환.
        """
        trace_detail = await self.get_trace_detail(trace_id)
        if not trace_detail:
            return None
        
        spans = trace_detail.get('spans', [])
        
        # 스팬을 시간순으로 정렬
        sorted_spans = sorted(spans, key=lambda s: s['timestamp'])
        
        # 이벤트로 변환
        events = []
        start_time = None
        
        for span in sorted_spans:
            timestamp = datetime.fromisoformat(span['timestamp'].replace('Z', '+00:00'))
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
        
        total_duration = int((datetime.fromisoformat(sorted_spans[-1]['timestamp'].replace('Z', '+00:00')) - start_time).total_seconds() * 1000) if sorted_spans else 0
        
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
        
        if 'model' in attrs or 'prompt' in attrs:
            return 'llm_call'
        elif 'tool_name' in attrs:
            return 'tool_use'
        elif span.get('status_code') == 'ERROR':
            return 'error'
        elif 'decision' in attrs:
            return 'decision'
        else:
            return 'span_start'
    
    def _extract_event_data(self, span: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        """이벤트 타입별 데이터 추출"""
        attrs = span.get('span_attributes', {})
        
        if event_type == 'llm_call':
            return {
                'model': attrs.get('model', 'unknown'),
                'prompt': attrs.get('prompt', ''),
                'response': attrs.get('response', ''),
                'prompt_tokens': attrs.get('prompt_tokens', 0),
                'completion_tokens': attrs.get('completion_tokens', 0),
                'total_tokens': attrs.get('total_tokens', 0),
                'cost': attrs.get('cost', 0.0),
                'latency': span.get('duration', 0)
            }
        elif event_type == 'tool_use':
            return {
                'tool_name': attrs.get('tool_name', 'unknown'),
                'input': attrs.get('input', {}),
                'output': attrs.get('output', {}),
                'duration': span.get('duration', 0),
                'status': 'success' if span.get('status_code') != 'ERROR' else 'error'
            }
        elif event_type == 'error':
            return {
                'error_type': attrs.get('error_type', 'UnknownError'),
                'error_message': span.get('status_message', 'Unknown error'),
                'stack_trace': attrs.get('stack_trace'),
                'span_id': span['span_id']
            }
        elif event_type == 'decision':
            return {
                'decision_type': attrs.get('decision_type', 'unknown'),
                'reasoning': attrs.get('reasoning', ''),
                'selected_option': attrs.get('selected_option', ''),
                'alternatives': attrs.get('alternatives', [])
            }
        else:
            return {
                'span_id': span['span_id'],
                'span_name': span['span_name'],
                'status': span.get('status_code', 'UNSET')
            }
    
    async def get_trace_timeline(self, trace_id: str) -> Dict[str, Any]:
        """
        트레이스 타임라인 생성 (계층 구조 포함).
        """
        from datetime import timedelta
        
        trace_detail = await self.get_trace_detail(trace_id)
        if not trace_detail:
            return None
        
        spans = trace_detail.get('spans', [])
        
        # 스팬을 트리 구조로 변환
        span_nodes = self._build_span_tree(spans)
        
        # 타임라인 정보 계산
        start_times = [datetime.fromisoformat(s['timestamp'].replace('Z', '+00:00')) for s in spans]
        start_time = min(start_times) if start_times else datetime.now()
        end_times = [datetime.fromisoformat(s['timestamp'].replace('Z', '+00:00')) + timedelta(milliseconds=s['duration']) for s in spans]
        end_time = max(end_times) if end_times else start_time
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
            timestamp = datetime.fromisoformat(span['timestamp'].replace('Z', '+00:00'))
            
            node = {
                'span_id': span['span_id'],
                'parent_span_id': span.get('parent_span_id'),
                'span_name': span['span_name'],
                'start_time': int(timestamp.timestamp() * 1000),
                'end_time': int(timestamp.timestamp() * 1000) + span['duration'],
                'duration': span['duration'],
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
                    timestamp = datetime.fromisoformat(span['timestamp'].replace('Z', '+00:00'))
                    child = {
                        'span_id': span['span_id'],
                        'parent_span_id': span.get('parent_span_id'),
                        'span_name': span['span_name'],
                        'start_time': int(timestamp.timestamp() * 1000),
                        'end_time': int(timestamp.timestamp() * 1000) + span['duration'],
                        'duration': span['duration'],
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
        pool = await self.get_pool()
        
        # 시간 간격별 그룹화
        if interval == 'hour':
            time_format = '%Y-%m-%d %H:00:00'
        elif interval == 'week':
            time_format = '%Y-%U'
        else:  # day
            time_format = '%Y-%m-%d'
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = f"""
                SELECT 
                    DATE_FORMAT(start_time, %s) as timestamp,
                    SUM(total_cost) as cost
                FROM trace_summaries
                WHERE project_id = %s
                  AND start_time >= %s
                  AND start_time <= %s
                GROUP BY DATE_FORMAT(start_time, %s)
                ORDER BY timestamp ASC
                """
                await cursor.execute(query, [time_format, project_id, start_time, end_time, time_format])
                results = await cursor.fetchall()
                
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
        pool = await self.get_pool()
        
        if interval == 'hour':
            time_format = '%Y-%m-%d %H:00:00'
        elif interval == 'week':
            time_format = '%Y-%U'
        else:
            time_format = '%Y-%m-%d'
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = f"""
                SELECT 
                    DATE_FORMAT(start_time, %s) as timestamp,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    0 as cache_hits
                FROM trace_summaries
                WHERE project_id = %s
                  AND start_time >= %s
                  AND start_time <= %s
                GROUP BY DATE_FORMAT(start_time, %s)
                ORDER BY timestamp ASC
                """
                await cursor.execute(query, [time_format, project_id, start_time, end_time, time_format])
                results = await cursor.fetchall()
                
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
        pool = await self.get_pool()
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                SELECT 
                    start_time as timestamp,
                    CAST(duration / 1000000 AS UNSIGNED) as duration,
                    CASE WHEN error_count > 0 THEN 'error' ELSE 'success' END as status
                FROM trace_summaries
                WHERE project_id = %s
                  AND start_time >= %s
                  AND start_time <= %s
                ORDER BY start_time ASC
                """
                await cursor.execute(query, [project_id, start_time, end_time])
                results = await cursor.fetchall()
                
                return [
                    {
                        'timestamp': r['timestamp'].isoformat(),
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
        """에이전트 플로우 그래프 데이터"""
        # 샘플 데이터 반환 (실제 구현 시 스팬 분석 필요)
        return {
            'nodes': [
                {
                    'id': 'agent-1',
                    'label': 'Main Agent',
                    'type': 'agent',
                    'position': {'x': 100, 'y': 100},
                    'data': {
                        'agent_name': 'Main Agent',
                        'total_calls': 150,
                        'total_cost': 2.5,
                        'avg_duration': 250
                    }
                },
                {
                    'id': 'tool-1',
                    'label': 'Search Tool',
                    'type': 'tool',
                    'position': {'x': 300, 'y': 100},
                    'data': {
                        'agent_name': 'Search Tool',
                        'total_calls': 75,
                        'total_cost': 0.5,
                        'avg_duration': 100
                    }
                },
                {
                    'id': 'llm-1',
                    'label': 'GPT-4',
                    'type': 'llm',
                    'position': {'x': 200, 'y': 250},
                    'data': {
                        'agent_name': 'GPT-4',
                        'total_calls': 200,
                        'total_cost': 5.0,
                        'avg_duration': 500
                    }
                }
            ],
            'edges': [
                {
                    'id': 'e1',
                    'source': 'agent-1',
                    'target': 'tool-1',
                    'animated': True,
                    'data': {
                        'message_count': 75,
                        'total_tokens': 5000
                    }
                },
                {
                    'id': 'e2',
                    'source': 'agent-1',
                    'target': 'llm-1',
                    'animated': True,
                    'data': {
                        'message_count': 150,
                        'total_tokens': 15000
                    }
                }
            ]
        }
    
    async def get_agent_usage_stats(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        에이전트별 사용량 통계 조회.
        
        Args:
            project_id: 프로젝트 ID
            start_time: 시작 시간
            end_time: 종료 시간
        
        Returns:
            에이전트별 통계 리스트
        """
        query = """
        SELECT 
            COALESCE(service_name, 'Unknown Agent') as agent_name,
            COUNT(DISTINCT trace_id) as event_count,
            COALESCE(SUM(CAST(JSON_EXTRACT(span_attributes, '$.llm.usage.total_tokens') AS UNSIGNED)), 0) as total_tokens,
            COALESCE(SUM(CAST(JSON_EXTRACT(span_attributes, '$.llm.cost') AS DECIMAL(10, 6))), 0) as total_cost,
            COALESCE(AVG(duration / 1000000), 0) as avg_latency_ms,
            COUNT(CASE WHEN status_code = 'ERROR' THEN 1 END) as error_count,
            COUNT(DISTINCT trace_id) - COUNT(CASE WHEN status_code = 'ERROR' THEN 1 END) as success_count
        FROM otel_traces
        WHERE project_id = %s
            AND timestamp >= %s
            AND timestamp <= %s
        GROUP BY agent_name
        ORDER BY total_tokens DESC
        """
        
        result = await self._execute_query(query, (project_id, start_time, end_time))
        
        agent_stats = []
        for row in result:
            event_count = row['event_count'] or 0
            success_count = row['success_count'] or 0
            success_rate = (success_count / event_count * 100) if event_count > 0 else 100.0
            
            agent_stats.append({
                'agent_name': row['agent_name'],
                'total_tokens': row['total_tokens'] or 0,
                'total_cost': float(row['total_cost']) if row['total_cost'] else 0.0,
                'event_count': event_count,
                'avg_latency': round(row['avg_latency_ms'], 2) if row['avg_latency_ms'] else 0.0,
                'error_count': row['error_count'] or 0,
                'success_rate': round(success_rate, 1)
            })
        
        return agent_stats


# Singleton
agentops_adapter = AgentOpsAdapter()

