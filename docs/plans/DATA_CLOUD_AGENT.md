너는 이 레포지토리에서 LangChain + LangGraph를 사용해
"Text-to-SQL 전용 Plan-and-Execute 에이전트" 아키텍처를 설계·구현해야 하는 시니어 엔지니어다.

구체적인 함수 내용(프롬프트, LLM 세부 파라미터 등)은 나중에 채울 것이고,
지금 단계에서는 **아키텍처/그래프 구조/State 설계 + OTEL(metric/trace) 설계**에 집중해라.

=====================================
1. 전체 목표 & 제약
=====================================

- 목표: 자연어 질문 + DB 연결 정보(connection_id)를 받아
  1) 질의를 이해하고,
  2) 관련 스키마/테이블을 고르고,
  3) DB 방언에 맞는 SQL 후보들을 생성하고,
  4) (선택적으로) 짧은 실행/검증 루프를 돌려,
  5) 최종적으로 "실행 가능한 SQL"과 "간단한 자연어 설명"을 반환하는
     **LangGraph 기반 Text-to-SQL Agent**를 만든다.

- 에이전트 패턴:
  - **Plan-and-Execute** 패턴을 기본으로 한다.
    - 1단계: Planner가 질의와 스키마를 보고 "어떤 테이블/조인/필터/집계를 사용할지" 플랜(JSON) 생성
    - 2단계: Executor가 이 플랜을 바탕으로 SQL 후보를 생성하고, 실행/검증/수정을 담당
  - Execute 단계 안에서만 제한된 형태의 ReAct(Reason ↔ Act) 루프를 허용한다.
    - 예: SQL 실행 → 에러 → 에러 메시지 기반 수정 1~2회.

- DB 타입:
  - PostgreSQL, MySQL, MariaDB, Oracle, ClickHouse, SAP HANA, Databricks, 그 외 generic SQL
  - 각 DB에 대해 **dialect-aware** SQL을 만들 수 있도록 설계해야 한다.
    - LIMIT / FETCH FIRST / ROWNUM, 함수명, 예약어 등.

- 사용 스택:
  - LangChain: LLM, Tool, SQLDatabase 유틸을 필요하면 사용
  - LangGraph: 전체 에이전트 오케스트레이션(StateGraph 기반)
  - LLM:
    - primary: Qwen3 / Qwen-coder 계열 (SQL 생성·플랜용)
    - secondary(optional): gpt-oss 계열 (리뷰/안전성 체크용)
  - 관측성:
    - OpenTelemetry(OTEL) 기반 trace + metrics를 **처음부터 설계에 포함**한다.
    - 각 주요 노드(Planner, Generator, Executor, Repair 등)에 대해 span과 metric을 기록한다.

=====================================
2. 파일 구조 (제안)
=====================================

레포 구조에 맞게 조정하되, 기본 제안은 다음과 같다.

- `agents/text2sql/state.py`
  - 에이전트 State 정의 (TypedDict or pydantic BaseModel)

- `agents/text2sql/nodes.py`
  - LangGraph 노드 함수들
  - (Entry, DialectResolver, SchemaSelector, Planner, SqlGenerator, SqlExecutor, SqlRepair, AnswerFormatter, HumanReview 등)

- `agents/text2sql/graph.py`
  - LangGraph `StateGraph`를 구성하는 코드
  - 노드/엣지 연결, entrypoint, conditional edge, config, persistence 옵션 등

- `agents/text2sql/tools.py`
  - DB 메타데이터 조회/샘플링/실행을 담당하는 LangChain Tool 또는 내부 서비스 래퍼

- `telemetry/otel.py`
  - OpenTelemetry tracer/meter/exporter 초기화
  - OTLP exporter 또는 이미 사용 중인 exporter에 붙인다.

- `agents/text2sql/metrics.py`
  - Text-to-SQL 전용 OTEL metric/span 헬퍼
  - 각 노드에서 사용하는 공통 함수 정의
    - 예: `record_node_duration(node_name, start_time, end_time, attrs)`
    - `inc_counter("text2sql_requests_total", attrs)`
    - `start_span("text2sql.planner", attrs)` 등


=====================================
3. State 설계 (SqlAgentState)
=====================================

`SqlAgentState`를 하나 정의하고, LangGraph `StateGraph`의 state로 사용하라.

필수 필드:

- `question: str`
  - 사용자의 자연어 질문 (한국어/영어 혼합 가능)

- `connection_id: str`
  - Data Cloud 쪽에서 사용하는 DB 연결 식별자

- `dialect: Literal["postgres", "mysql", "mariadb", "oracle", "clickhouse", "hana", "databricks", "generic"] | None`
  - DialectResolver 노드에서 채우는 값

- `schema_summary: str | None`
  - Planner/Generator에게 넘겨줄 스키마 요약 문자열
  - (테이블 목록, 컬럼, PK/FK, 코멘트, 샘플 컬럼 등)

- `schema_graph: dict | None`
  - (선택) 테이블/관계 정보를 JSON 그래프 형태로 보존하고 싶으면 사용
  - `{ "tables": [...], "relations": [...] }` 구조

- `plan: dict | None`
  - Planner LLM이 만든 JSON 플랜
  - 예: `{"tables": [...], "joins": [...], "filters": [...], "aggregations": [...], "group_by": [...], "order_by": [...], "limit": 100}`

- `candidate_sql: list[str]`
  - SqlGenerator가 쌓아가는 SQL 후보 리스트

- `chosen_sql: str | None`
  - 최종적으로 채택된 SQL

- `sql_reasoning: str | None`
  - 선택: SQL 생성 시 LLM의 reasoning 텍스트(디버깅용)

- `execution_result: list[dict] | None`
  - (선택) 실행 후 결과. 이 에이전트는 “쿼리 생성”이 주 역할이므로
    - 최소한 `row_count` 정도만 저장하고,
    - 실제 데이터는 상위 서비스에서 관리해도 된다.

- `execution_error: str | None`
  - SQL 실행 중 마지막 에러 메시지 (있다면)

- `retry_count: int`
  - SQL 수정 재시도 횟수

- `max_retries: int`
  - 설정값 (예: 1 또는 2)

- `needs_human_review: bool`
  - Human-in-the-loop 단계로 보내야 하는지 여부

- `answer_summary: str | None`
  - (선택) 결과를 바탕으로 만든 자연어 요약

OTEL 관련 필드(선택이지만 권장):

- `trace_id: str | None`
  - 상위 HTTP/API 레이어에서 들어온 trace_id를 그대로 받아서 넘기거나,
    이 그래프에서 새로 생성한 trace_id를 저장할 때 사용.
  - 이 값은 OTEL tracer와 연동할 때 span attribute로 같이 실어준다.

- `metrics_tags: dict[str, str] | None`
  - metrics 공통 태그를 담는 용도
  - 예: `{"service": "agent-portal", "component": "text2sql", "dialect": "postgres"}`

이 State 정의만 정확히 만들어두면, 나머지 노드는 State를 입력/출력으로 삼는 순수 함수로 구성하면 된다.


=====================================
4. LangGraph 노드 설계
=====================================

각 노드는 `SqlAgentState`를 입력/출력으로 받는 함수이며,
LangGraph `StateGraph`의 노드로 연결된다.
각 노드는 OTEL span/metric을 기록해야 한다.

[노드 목록]

1) `entry_node`
   - 책임:
     - 초기 state를 구성하고, 기본값 세팅
       - `retry_count = 0`
       - `max_retries = 설정값` (예: 1 또는 2)
       - `needs_human_review = False`
       - `metrics_tags`에 기본 태그 설정:
         - `{"component": "text2sql", "phase": "entry"}`
       - 상위 레이어에서 trace_id가 들어왔으면 state에 반영
     - OTEL:
       - span 이름: `"text2sql.entry"`
       - metric:
         - Counter `text2sql_requests_total` 증가
           - attributes: `{"dialect": "unknown", "source": "api", ...}`

   - 출력:
     - 다음 노드인 `dialect_resolver`로 넘김

2) `dialect_resolver`
   - 책임:
     - `connection_id`를 사용해 내부 Data Cloud 메타데이터/엔진 정보를 조회
     - SQLAlchemy `engine.dialect.name` 또는 저장된 메타 정보 기준으로 dialect 매핑:
       - postgresql → "postgres"
       - mysql/mariadb → "mysql"/"mariadb"
       - oracle → "oracle"
       - clickhouse → "clickhouse"
       - hana → "hana"
       - databricks / spark → "databricks"
       - 기타 → "generic"
     - dialect에 따라 **프롬프트에 들어갈 규칙 문자열**도 만든다 (예: Oracle은 LIMIT 금지, ROWNUM/ FETCH FIRST 사용 등).
   - OTEL:
     - span 이름: `"text2sql.dialect_resolver"`
     - attributes:
       - `connection_id`, 결정된 `dialect`
     - metric:
       - Counter `text2sql_dialect_resolved_total` 증가
         - attrs: `{"dialect": "...", "success": true/false}`

   - 출력:
     - `state.dialect` 채움
     - 필요 시 `state.metrics_tags["dialect"]`도 업데이트

3) `schema_selector`
   - 책임:
     - `connection_id`를 사용해 스키마 메타데이터를 조회하는 Tool 호출
       - 예: `get_schema(connection_id, include_tables=None, max_tables=N)`
       - DB가 커질 수 있으므로, 전 테이블이 아니라 뷰/주요 테이블 위주로 요약
     - 질의/스키마를 한 번 LLM에 보내 "**관련 있을 것 같은 테이블 subset**"만 고르게 할 수도 있다.
       - 이 부분은 처음엔 단순하게 "모든 테이블 요약"으로 시작해도 된다.
   - OTEL:
     - span 이름: `"text2sql.schema_selector"`
     - attributes:
       - `dialect`, `table_count`, `connection_id`
     - metrics:
       - Histogram `text2sql_schema_fetch_latency_ms`
       - Histogram `text2sql_schema_table_count`

   - 출력:
     - `state.schema_summary`에 문자열 형태로 스키마 요약 저장
     - (선택) `state.schema_graph`에 JSON 형태로 저장

4) `planner_node` (Plan 단계)
   - 책임:
     - Plan-and-Execute 패턴의 Planner.
     - 입력:
       - `question`, `schema_summary`, `dialect`, `db_name`, (선택) `schema_graph`
     - LLM (primary: Qwen3 계열)을 사용해 JSON 플랜 생성:
       - 어떤 테이블을 쓸지
       - 어떤 조인 관계를 쓸지
       - 어떤 필터/집계를 적용할지
       - 어떤 group_by / order_by / limit을 사용할지 (자연어 형태도 괜찮음)
     - 출력:
       - `state.plan`에 JSON으로 저장
   - 특징:
     - 여기서는 **SQL을 쓰지 않는다.** 오직 플랜만.

   - OTEL:
     - span 이름: `"text2sql.planner"`
     - attributes:
       - `dialect`, `has_schema_summary`, `llm_model` (planner에 사용한 모델명)
     - metrics:
       - Histogram `text2sql_planning_latency_ms`
       - Histogram `text2sql_planning_tokens_prompt`
       - Histogram `text2sql_planning_tokens_completion`
       - Counter `text2sql_planning_errors_total` (예외 발생 시)

5) `sql_generator_node` (Execute 단계 1)
   - 책임:
     - Planner가 만든 `state.plan` + `schema_summary` + `dialect` 정보를 바탕으로
       **SQL 후보들을 생성**한다.
     - 내부 패턴:
       - Qwen3 / Qwen-coder에
         - `<reasoning>` + `<sql>` 태그 포맷으로 결과를 요청해,
           - reasoning은 디버깅용
           - SQL만 실제 후보로 저장
     - 동작:
       - 온도/프롬프트를 조금씩 다르게 해서 `k`개 후보를 생성 (예: 2~3개)
       - 각 후보를 `state.candidate_sql` 리스트에 push
       - 마지막 생성된 SQL을 `state.chosen_sql`로 초기 설정
       - reasoning은 `state.sql_reasoning`에 저장

   - OTEL:
     - span 이름: `"text2sql.generator"`
     - attributes:
       - `dialect`, `candidate_count`, `llm_model`
     - metrics:
       - Histogram `text2sql_generation_latency_ms`
       - Histogram `text2sql_generation_tokens_prompt`
       - Histogram `text2sql_generation_tokens_completion`
       - Histogram `text2sql_candidate_count`
       - Counter `text2sql_generation_errors_total` (예외 시)

   - 출력:
     - `state.candidate_sql`, `state.chosen_sql`, `state.sql_reasoning` 업데이트

6) `sql_executor_node`
   - 책임:
     - `state.chosen_sql`을 실제 DB에 **LIMIT가 포함된 안전 모드**로 실행해 본다.
     - 별도의 내부 Tool/서비스 사용:
       - `execute_sql(connection_id, sql, dry_run=True, limit=LIMIT_FOR_VALIDATION)`
     - 두 가지 Path:
       - 성공:
         - `state.execution_result`에 row_count 또는 sample rows 저장
         - `state.execution_error = None`
       - 실패(Exception or DB error):
         - `state.execution_error`에 에러 메시지 문자열 저장

   - OTEL:
     - span 이름: `"text2sql.executor"`
     - attributes:
       - `dialect`, `connection_id`, `has_limit`, `row_count`, `error_type`
     - metrics:
       - Histogram `text2sql_execution_latency_ms`
       - Histogram `text2sql_execution_row_count`
       - Counter `text2sql_execution_errors_total`
       - Counter `text2sql_requests_success_total` (성공 시)

   - 출력:
     - `state.execution_result`, `state.execution_error` 업데이트

7) `sql_repair_node`
   - 책임:
     - `state.execution_error`가 있을 때만 호출되는 노드.
     - Plan-and-Execute의 “재계획/수정” 단계.
     - LLM에게 다음 정보를 주고 수정된 SQL을 요청:
       - 질문
       - dialect 규칙
       - 스키마 요약
       - 이전 후보 SQL들 (`candidate_sql`)
       - 마지막 `chosen_sql`
       - `execution_error` 메시지
     - 새로운 SQL을 생성하여:
       - `state.chosen_sql`을 새 SQL로 업데이트
       - `state.candidate_sql`에 추가
       - `state.retry_count += 1`

   - OTEL:
     - span 이름: `"text2sql.repair"`
     - attributes:
       - `dialect`, `retry_count`, `error_type`, `llm_model`
     - metrics:
       - Counter `text2sql_retries_total` (retry 수행 시)
       - Histogram `text2sql_repair_latency_ms`
       - Histogram `text2sql_repair_tokens_prompt`
       - Histogram `text2sql_repair_tokens_completion`

   - 출력:
     - 수정된 SQL이 담긴 state

8) `answer_formatter_node`
   - 책임:
     - 최종 SQL(`chosen_sql`)과 (있다면) `execution_result`를 기반으로
       - 간단한 한글 요약 (`answer_summary`)
       - 필요한 경우, DB별 튜닝 팁/주의사항을 텍스트로 함께 생성
     - 이 노드는 실제로 LangGraph 그래프의 최종 output을 구성하는 역할을 한다.

   - OTEL:
     - span 이름: `"text2sql.answer_formatter"`
     - attributes:
       - `dialect`, `has_result`, `needs_human_review`
     - metrics:
       - Histogram `text2sql_total_latency_ms` (가능하면 entry에서 시작한 시간과의 차이 측정)
       - Counter `text2sql_answer_built_total`

   - 출력:
     - `state.answer_summary` 채움
     - 그래프 반환 값으로 `(sql, answer_summary, meta)` 형태를 리턴하도록 설계

9) `human_review_node` (선택)
   - 책임:
     - `needs_human_review == True` 인 경우만 진입.
     - 실제 구현 시에는:
       - 이 노드는 바로 종료하고, 상위 레이어에서 “사람이 봐야 하는 상태”로 표시만 해도 된다.

   - OTEL:
     - span 이름: `"text2sql.human_review"`
     - metrics:
       - Counter `text2sql_human_review_total`
       - attributes:
         - `reason`: 예) `"max_retries_exceeded"`, `"schema_missing"`, `"security_flag"`

   - 출력:
     - 별도 없음. 상위에서 state를 보고 처리.


=====================================
5. 그래프(상태 전이) 설계
=====================================

LangGraph `StateGraph[SqlAgentState]`로 다음과 같이 구성하라.

노드 연결(기본 흐름):

1. `entry_node`  →  `dialect_resolver`
2. `dialect_resolver`  →  `schema_selector`
3. `schema_selector`  →  `planner_node`
4. `planner_node`  →  `sql_generator_node`
5. `sql_generator_node`  →  `sql_executor_node`
6. `sql_executor_node`  →  분기:
   - if `execution_error is None`:
       → `answer_formatter_node`
   - else if `retry_count < max_retries`:
       → `sql_repair_node`
   - else:
       → `human_review_node` (또는 직접 `answer_formatter_node`에서 “에러 발생” 응답)

7. `sql_repair_node`  →  `sql_executor_node` (루프)

그래프 구조 관점에서 보면,
**Plan-and-Execute + 짧은 ReAct 루프(sql_repair_node ↔ sql_executor_node)** 패턴이다.

- Plan: `planner_node`
- Execute: `sql_generator_node` → `sql_executor_node`
- 재계획/수정: `sql_repair_node` → 다시 `sql_executor_node`

각 노드 전이 자체는 OTEL에서 하나의 상위 trace 안에 여러 span으로 녹아들도록 한다.
entry에서 span을 시작하고, 각 노드 함수에서 `tracer.start_as_current_span("text2sql.xxx")`를 사용하는 구조를 권장한다.


=====================================
6. Multi-DB/Dialect 대응 설계
=====================================

- `dialect_resolver` 노드에서 dialect에 따라 다음과 같은 규칙 문자열을 만든다.
  - PostgreSQL:
    - ANSI SQL, `LIMIT <n>`, `OFFSET <n>`
    - 더블쿼트(")는 식별자에만 사용, 문자열은 싱글쿼트(')
  - MySQL / MariaDB:
    - `LIMIT <n>`, `LIMIT <offset>, <n>`
    - 백틱(`)은 식별자에만 사용
  - Oracle:
    - 절대 `LIMIT` 쓰지 말 것
    - `FETCH FIRST <n> ROWS ONLY` 또는 `ROWNUM <= n` 사용
  - ClickHouse:
    - `LIMIT <n>` 필수
    - 대용량 집계에 적합, 하지만 여기서는 가능한 ANSI 스타일 유지
  - SAP HANA:
    - 일반적인 SELECT/FROM/GROUP BY 문법
    - `LIMIT <n>` 지원, 다른 DB-specific 문법은 피함
  - Databricks (Spark SQL):
    - `LIMIT`, `OFFSET`, `WITH` CTE 지원
    - 대부분 PostgreSQL 비슷한 ANSI SQL 스타일로 작성
  - 기타:
    - 가능한 ANSI SQL로 작성, vendor-specific 함수는 지양

- 이 규칙 문자열은 Planner/Generator 노드의 system prompt 일부로 항상 들어가게 설계해라.
- 동시에, OTEL metric의 tag에도 dialect를 반드시 포함시켜서,
  - 대시보드에서 dialect별 성공/실패율과 latency를 쉽게 모니터링할 수 있게 한다.


=====================================
7. LangGraph 그래프 구성 코드 (개략도)
=====================================

실제 코드는 네가 작성하되, 구조는 다음과 같이 맞춘다.

- `build_text2sql_graph()` 함수 하나를 만든다.
  - 내부에서:

    - `from langgraph.graph import StateGraph, END`
    - `graph = StateGraph(SqlAgentState)`

    - 노드 등록:
      - `graph.add_node("entry", entry_node)`
      - `graph.add_node("dialect_resolver", dialect_resolver)`
      - `graph.add_node("schema_selector", schema_selector)`
      - `graph.add_node("planner", planner_node)`
      - `graph.add_node("sql_generator", sql_generator_node)`
      - `graph.add_node("sql_executor", sql_executor_node)`
      - `graph.add_node("sql_repair", sql_repair_node)`
      - `graph.add_node("answer_formatter", answer_formatter_node)`
      - (선택) `graph.add_node("human_review", human_review_node)`

    - 엣지 연결:
      - `graph.set_entry_point("entry")`
      - 직선 경로 엣지:
        - `graph.add_edge("entry", "dialect_resolver")`
        - `graph.add_edge("dialect_resolver", "schema_selector")`
        - `graph.add_edge("schema_selector", "planner")`
        - `graph.add_edge("planner", "sql_generator")`
        - `graph.add_edge("sql_generator", "sql_executor")`

      - `sql_executor`에서의 조건부 엣지:
        - LangGraph의 conditional edge 패턴을 사용하여,
          - `if state.execution_error is None` → "answer_formatter"
          - `elif state.retry_count < state.max_retries` → "sql_repair"
          - else → "human_review" 또는 바로 END

      - `graph.add_edge("sql_repair", "sql_executor")`
      - `graph.add_edge("answer_formatter", END)`

    - 마지막에:
      - `app = graph.compile()` 형태로 LangGraph 앱 객체를 리턴

- OTEL과의 통합:
  - 각 노드 함수 안에서 `telemetry/otel.py`의 tracer/meter를 사용해 span을 열고 metric을 기록한다.
  - 필요하다면 LangGraph middleware(예: node-level hook)를 사용해
    모든 노드 호출에 공통 span을 여는 래퍼를 만들 수도 있다.


=====================================
8. LangChain/LangGraph + OTEL 통합 고려사항
=====================================

- LangChain 쪽에서 이미 `SQLDatabaseToolkit`이나 `create_sql_agent` 등을 쓰고 있다면,
  - 그걸 그대로 쓰지 말고,
  - **해당 툴이 하는 일(스키마 조회, 쿼리 실행, double-check)**을
    위에 정의한 node/tool 함수로 분해해서 LangGraph 안으로 녹여라.

- LLM 호출 부분은 공통 유틸/래퍼 함수를 하나 만든 뒤,
  - Planner/Generator/Repair 노드에서 공통으로 사용하도록 설계하라.
  - primary_model(Qwen3 계열) / secondary_model(gpt-oss 계열)을 선택적으로 쓸 수 있게 해두면 좋다
    (예: 리뷰/안전성 체크 전용으로 secondary 사용).

- 이 LLM 래퍼에서도 OTEL metric을 함께 수집한다.
  - 예:
    - Counter `text2sql_llm_calls_total`
    - Histogram `text2sql_llm_latency_ms`
    - Histogram `text2sql_llm_tokens_prompt`, `text2sql_llm_tokens_completion`

- 향후 확장:
  - Semantic layer(비즈니스 뷰)에 대한 별도 Planner를 추가하거나,
  - “메타 쿼리(어떤 데이터가 있는지)”를 위한 Router 노드를 추가하는 것도 가능하도록,
    지금 그래프를 너무 타이트하게 만들지 말고 node 이름과 역할을 일반화해두라.
  - OTEL metric 이름/태그도 재사용 가능한 형태로 설계해라.

=====================================
9. 최종 정리

- 이 작업에서 네가 해야 할 일은
  - SqlAgentState 설계 (OTEL 관련 trace_id/metrics_tags까지 포함)
  - 위에서 정의한 8~9개 LangGraph 노드의 시그니처/책임 정리
  - Plan-and-Execute 패턴에 맞는 그래프(노드/엣지/조건부 분기) 구성
  - Dialect-aware SQL 생성을 고려한 dialect_resolver 설계
  - 각 노드/LLM 호출에 대해 OpenTelemetry 기반 trace + metric을 남기는 구조 설계
- LLM 프롬프트/파라미터/세부 구현은 나중에 채울 것이므로,
  - 지금은 **아키텍처와 그래프 구조, OTEL 관측성 설계가 깨끗하고 확장 가능하게 설계되어 있는지**에 집중해라.
