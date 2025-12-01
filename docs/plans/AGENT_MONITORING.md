# 에이전트 모니터링 자동 등록 시스템

## 아키텍처

```
[Agent Endpoint] → [Agent Registry] → [Trace Start]
       ↓                                    ↓
[LLM Call via LiteLLM] ←→ [Child Span with parent_trace_id]
       ↓                                    ↓
[Response] → [Trace End] → [ClickHouse/MariaDB]
       ↓
[Monitoring Dashboard] → [Overview: Agent Usage] + [New: Agent Detail Tab]
```

## 1. 에이전트 레지스트리 테이블 (MariaDB)

[backend/app/services/agent_registry_service.py](backend/app/services/agent_registry_service.py) (신규)

```sql
CREATE TABLE agents (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type ENUM('vanna', 'langflow', 'flowise', 'autogen', 'custom') NOT NULL,
    project_id VARCHAR(255) DEFAULT 'default-project',
    external_id VARCHAR(255),  -- Langflow flow_id, Flowise chatflow_id
    config JSON,
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    UNIQUE KEY (name, project_id),
    INDEX idx_external (external_id)
);
```

## 2. 에이전트 등록 API

[backend/app/routes/agent_registry.py](backend/app/routes/agent_registry.py) (신규)

| Endpoint | Method | 용도 |

|----------|--------|------|

| `/agents/register` | POST | 에이전트 등록 (Langflow/Flowise/Vanna 호출) |

| `/agents/{agent_id}` | GET | 에이전트 상세 |

| `/agents` | GET | 에이전트 목록 |

| `/agents/{agent_id}/trace/start` | POST | 트레이스 시작 (trace_id 반환) |

| `/agents/{agent_id}/trace/end` | POST | 트레이스 종료 |

## 3. 에이전트 트레이스 어댑터

[backend/app/services/agent_trace_adapter.py](backend/app/services/agent_trace_adapter.py) (신규 - 기존 agentops_adapter 대체)

- OTEL Collector로 스팬 전송 (HTTP/gRPC)
- 또는 ClickHouse 직접 삽입
- parent_trace_id로 LLM 호출과 연결

## 4. 각 에이전트별 자동 등록 구현

### 4.1 Vanna Agent

[backend/app/services/vanna_agent_service.py](backend/app/services/vanna_agent_service.py) 수정

```python
async def generate_sql(self, connection_id, question, connection_info):
    # 1. 에이전트 자동 등록 (없으면 생성)
    agent = await agent_registry.register_or_get(
        name=f"vanna-{connection_id}",
        type="vanna",
        external_id=connection_id
    )
    
    # 2. 트레이스 시작
    trace_id = await agent_trace.start_trace(agent.id, {"question": question})
    
    # 3. LLM 호출 (metadata에 trace_id 전달)
    result = await llm_service.chat_completion_sync(
        ...,
        metadata={"parent_trace_id": trace_id, "agent_id": agent.id}
    )
    
    # 4. 트레이스 종료
    await agent_trace.end_trace(trace_id, {"sql": result.sql})
```

### 4.2 Langflow/Flowise

[backend/app/services/langgraph_service.py](backend/app/services/langgraph_service.py) 수정

- `_run_flow()` 실제 API 호출 구현
- Langflow: `POST http://langflow:7860/api/v1/run/{flow_id}`
- Flowise: `POST http://flowise:3000/api/v1/prediction/{chatflow_id}`
- 플로우 실행 전 자동 등록

### 4.3 AutoGen

[backend/app/routes/autogen.py](backend/app/routes/autogen.py) (신규 또는 확장)

- AutoGen Studio API 연동
- 에이전트 생성 시 자동 등록

## 5. LiteLLM 메타데이터 연결

[backend/app/services/litellm_service.py](backend/app/services/litellm_service.py) 수정

```python
async def chat_completion_sync(self, model, messages, metadata=None, **kwargs):
    payload = {
        "model": model,
        "messages": messages,
        "metadata": {
            "agent_id": metadata.get("agent_id") if metadata else None,
            "parent_trace_id": metadata.get("parent_trace_id") if metadata else None,
            **metadata or {}
        },
        **kwargs
    }
```

LiteLLM의 OTEL 콜백이 metadata를 SpanAttributes에 저장하여 에이전트 트레이스와 연결.

## 6. 모니터링 어댑터 개선

[backend/app/services/monitoring_adapter.py](backend/app/services/monitoring_adapter.py) 수정

```python
async def get_agent_detail_stats(self, agent_id: str, ...):
    """개별 에이전트 상세 통계"""
    query = f"""
    SELECT ...
    FROM otel_traces
    WHERE SpanAttributes['metadata.agent_id'] = '{agent_id}'
    """
```

## 7. 모니터링 UI 개선

### 7.1 기존 Agent Usage 활용

[webui/src/routes/(app)/admin/monitoring/+page.svelte](webui/src/routes/\\(app)/admin/monitoring/+page.svelte)

- 테이블에 "상세" 버튼 추가 → 에이전트 상세 페이지로 이동

### 7.2 신규 에이전트 상세 탭

[webui/src/routes/(app)/admin/monitoring/agents/[agent_id]/+page.svelte](webui/src/routes/(app)/admin/monitoring/agents/[agent_id]/+page.svelte) (신규)

- 개별 에이전트 메트릭 (호출수, 비용, 에러율)
- 해당 에이전트의 트레이스 목록
- 시간별 사용량 차트
- 하위 LLM 호출 연결 표시

## 8. 구현 순서

1. DB 스키마 생성 (`agents` 테이블)
2. `agent_registry_service.py` 구현
3. `agent_trace_adapter.py` 구현 (OTEL 연동)
4. `agent_registry.py` API 라우터 구현
5. `vanna_agent_service.py` 수정 (자동 등록 + 트레이스)
6. `langgraph_service.py` 수정 (실제 API 호출 + 자동 등록)
7. `litellm_service.py` 수정 (metadata 전달)
8. `monitoring_adapter.py` 수정 (agent_id 기반 쿼리)
9. UI: Agent Usage 테이블에 상세 링크 추가
10. UI: 에이전트 상세 페이지 구현

## 9. 문서 업데이트

### 9.1 업데이트 대상 문서

| 문서 | 업데이트 내용 |

|------|-------------|

| [AGENTS.md](AGENTS.md) | 에이전트 모니터링 아키텍처, API 레퍼런스 추가 |

| [docs/SERVICE-DATABASE-STATUS.md](docs/SERVICE-DATABASE-STATUS.md) | `agents` 테이블 스키마 추가 |

| [.cursor/rules/monitoring-development.mdc](.cursor/rules/monitoring-development.mdc) | 에이전트 트레이스 패턴 추가 |

| [.cursor/learnings/bug-fixes.md](.cursor/learnings/bug-fixes.md) | 구현 중 발견한 이슈 기록 |

### 9.2 신규 문서

| 문서 | 내용 |

|------|------|

| [docs/AGENT_MONITORING.md](docs/AGENT_MONITORING.md) | 에이전트 모니터링 설정 가이드, API 사용법 |

| [docs/AGENT_INTEGRATION_GUIDE.md](docs/AGENT_INTEGRATION_GUIDE.md) | Langflow/Flowise/AutoGen 연동 가이드 |

## 10. 테스트 절차

### 10.1 단위 테스트

| 테스트 항목 | 검증 내용 |

|------------|----------|

| 에이전트 등록 API | POST /agents/register 정상 동작 |

| 트레이스 시작/종료 | trace_id 생성 및 ClickHouse 저장 확인 |

| 메타데이터 전달 | LiteLLM 호출 시 agent_id, parent_trace_id 포함 여부 |

### 10.2 통합 테스트 (브라우저)

**Step 1: Vanna Agent 테스트**

```
1. Data Cloud > ClickHouse 쿼리 버튼 클릭
2. "otel_traces에서 최근 10건 조회해줘" 입력
3. SQL 생성 실행
4. 모니터링 > Overview > Agent Usage에 "vanna-{connection_id}" 표시 확인
5. 상세 페이지에서 트레이스 확인
```

**Step 2: Langflow Agent 테스트** (Langflow 실행 시)

```
1. Langflow에서 플로우 생성/실행
2. 모니터링 > Agent Usage에 langflow 에이전트 표시 확인
3. 하위 LLM 호출과 연결 확인
```

**Step 3: 모니터링 메트릭 검증**

```
1. ClickHouse에서 직접 쿼리로 트레이스 확인
   SELECT * FROM otel_2.otel_traces 
   WHERE SpanAttributes['metadata.agent_id'] != ''
   ORDER BY Timestamp DESC LIMIT 10
2. Agent Usage 통계와 실제 데이터 일치 여부 확인
```

### 10.3 테스트 체크리스트

- [ ] 에이전트 자동 등록 동작 확인
- [ ] 트레이스 시작/종료 ClickHouse 저장 확인
- [ ] LLM 호출에 parent_trace_id 연결 확인
- [ ] Agent Usage 통계 정확성 확인
- [ ] 에이전트 상세 페이지 데이터 표시 확인
- [ ] 에러 케이스 (에이전트 실패 시) 트레이스 기록 확인

## 11. 테스트 후 개선 계획 수립

### 11.1 성능 분석

테스트 완료 후 아래 항목 측정:

- 에이전트 등록 API 응답 시간
- 트레이스 저장 지연 시간
- 모니터링 대시보드 로딩 시간

### 11.2 개선 후보 항목

| 우선순위 | 항목 | 설명 |

|---------|------|------|

| P1 | 캐싱 | 자주 조회되는 에이전트 정보 Redis 캐싱 |

| P1 | 인덱스 최적화 | ClickHouse 쿼리 성능 개선 |

| P2 | 대시보드 개선 | 실시간 WebSocket 업데이트 |

| P2 | 알림 시스템 | 에이전트 에러율 임계치 알림 |

| P3 | 에이전트 비교 | 여러 에이전트 성능 비교 차트 |

### 11.3 피드백 반영 프로세스

```
1. 테스트 결과 문서화 (.cursor/learnings/)
2. 성능 병목 지점 식별
3. 개선 우선순위 결정
4. 다음 스프린트 TODO 생성
5. Git commit/push
```

## 12. 최종 산출물

- [ ] `agents` 테이블 스키마
- [ ] Backend 서비스 4개 (registry, trace, langgraph 수정, litellm 수정)
- [ ] API 엔드포인트 5개
- [ ] UI 페이지 1개 (에이전트 상세)
- [ ] UI 컴포넌트 수정 1개 (Agent Usage 테이블)
- [ ] 문서 2개 (AGENT_MONITORING.md, AGENT_INTEGRATION_GUIDE.md)
- [ ] 기존 문서 업데이트 4개