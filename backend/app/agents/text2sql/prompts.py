"""
Prompt Templates for Text-to-SQL Agent

참조: docs/plans/DATA_CLOUD_AGENT.md 섹션 6. Multi-DB/Dialect 대응 설계

각 DB dialect에 따른 SQL 규칙과 프롬프트 템플릿.
"""

from typing import Tuple, Optional, Dict, Any, List


# ========== Dialect Rules (섹션 6) ==========

DIALECT_RULES = {
    "postgres": """
PostgreSQL SQL Rules:
- Use ANSI SQL style with `LIMIT n` and `OFFSET n` for pagination
- Use double quotes (") for identifiers only when necessary (reserved words)
- Use single quotes (') for string literals
- Prefer explicit JOINs with clear ON clauses
- Common functions: COUNT(), SUM(), AVG(), MAX(), MIN(), NOW(), DATE_TRUNC()
- For date operations use: CURRENT_DATE, CURRENT_TIMESTAMP, INTERVAL
""",

    "mysql": """
MySQL SQL Rules:
- Use `LIMIT n` for row limiting
- Use backticks (`) only when you must quote identifiers
- Use single quotes (') for string literals
- Common functions: COUNT(), SUM(), AVG(), NOW(), CURDATE(), DATE_FORMAT()
- For string concatenation use CONCAT()
- IFNULL() for null handling
""",

    "mariadb": """
MariaDB SQL Rules:
- Use `LIMIT n` for row limiting (same as MySQL)
- Use backticks (`) only when you must quote identifiers
- Use single quotes (') for string literals
- Common functions: COUNT(), SUM(), AVG(), NOW(), CURDATE(), DATE_FORMAT()
- For string concatenation use CONCAT()
- IFNULL() or COALESCE() for null handling
""",

    "oracle": """
Oracle SQL Rules:
- DO NOT use LIMIT. Use `FETCH FIRST n ROWS ONLY` or `WHERE ROWNUM <= n`
- Use double quotes (") for identifiers only when necessary
- Use single quotes (') for string literals
- Use NVL() or COALESCE() for null handling
- For date operations use: SYSDATE, TO_DATE(), TO_CHAR()
- String concatenation with || operator
- Common functions: COUNT(), SUM(), AVG(), DECODE(), NVL()
""",

    "clickhouse": """
ClickHouse SQL Rules:
- Use `LIMIT n` for row limiting
- Use backticks (`) or double quotes (") for identifiers
- Use single quotes (') for string literals
- ClickHouse is optimized for aggregation - use GROUP BY efficiently
- Common functions: count(), sum(), avg(), toDate(), toDateTime()
- For NULL handling use: ifNull(), coalesce()
- Date functions: today(), now(), toStartOfDay(), dateDiff()
- Be careful with Nullable types
""",

    "hana": """
SAP HANA SQL Rules:
- Use `LIMIT n` for row limiting
- Use double quotes (") for case-sensitive identifiers
- Use single quotes (') for string literals
- Standard SELECT/FROM/WHERE/GROUP BY/HAVING syntax
- Common functions: COUNT(), SUM(), AVG(), NOW(), CURRENT_DATE
- Avoid non-HANA vendor-specific syntax
""",

    "databricks": """
Databricks (Spark SQL) Rules:
- Use `LIMIT n` for row limiting
- Use backticks (`) for identifiers with special characters
- Use single quotes (') for string literals
- CTE (WITH ...) clauses are fully supported
- Common functions: count(), sum(), avg(), current_date(), date_format()
- For NULL handling use: coalesce(), nvl()
""",

    "generic": """
Generic ANSI SQL Rules:
- Use portable ANSI SQL syntax
- Avoid vendor-specific functions when possible
- Use LIMIT for row limiting (may not work on all databases)
- Prefer explicit JOINs with clear ON clauses
- Use standard aggregate functions: COUNT(), SUM(), AVG(), MAX(), MIN()
"""
}


def get_dialect_rules(dialect: str) -> str:
    """
    Dialect에 따른 SQL 규칙 문자열 반환.
    
    Args:
        dialect: 데이터베이스 방언 (postgres, mysql, mariadb, oracle, clickhouse, hana, databricks, generic)
        
    Returns:
        해당 dialect의 SQL 규칙 문자열
    """
    return DIALECT_RULES.get(dialect, DIALECT_RULES["generic"])


# ========== Planner Prompt ==========

def build_planner_prompt(
    question: str,
    dialect: str,
    dialect_rules: str,
    schema_summary: str
) -> Tuple[str, str]:
    """
    Planner 노드용 프롬프트 생성.
    
    Args:
        question: 사용자 질문
        dialect: DB 방언
        dialect_rules: 방언별 규칙
        schema_summary: 스키마 요약
        
    Returns:
        (system_prompt, user_prompt) 튜플
    """
    system_prompt = f"""You are a database query planner.

Your job is to analyze the user's question and create a JSON query plan.
DO NOT write SQL. Only output a JSON plan.

{dialect_rules}

Important:
- Understand the user's question and the given schema
- Decide which tables and joins are needed
- Decide filters, groupings, aggregations, ordering, and safe row limits
- Always include a reasonable LIMIT (default: 100) for safety
"""

    user_prompt = f"""[Database Dialect]
{dialect}

[User Question]
{question}

[Available Schema]
{schema_summary}

Create a JSON query plan with this structure:
```json
{{
    "tables": ["table1", "table2"],
    "joins": [
        {{"left": "table1.col", "right": "table2.col", "type": "inner"}}
    ],
    "filters": ["description of filter conditions"],
    "aggregations": ["description of aggregations needed"],
    "group_by": ["column1", "column2"],
    "order_by": ["column DESC", "column2 ASC"],
    "limit": 100
}}
```

Respond ONLY with the JSON plan, no explanation.
"""

    return system_prompt, user_prompt


# ========== SQL Generator Prompt ==========

def build_generator_prompt(
    question: str,
    dialect: str,
    dialect_rules: str,
    schema_summary: str,
    plan: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    SQL Generator 노드용 프롬프트 생성.
    
    Args:
        question: 사용자 질문
        dialect: DB 방언
        dialect_rules: 방언별 규칙
        schema_summary: 스키마 요약
        plan: Planner가 생성한 쿼리 플랜 (선택)
        
    Returns:
        (system_prompt, user_prompt) 튜플
    """
    system_prompt = f"""You are a senior data engineer responsible for writing correct and efficient SQL queries.

Requirements:
- ONLY write a single SELECT query (or WITH ... SELECT for CTEs)
- DO NOT use INSERT, UPDATE, DELETE, MERGE, DROP, TRUNCATE, ALTER, CREATE or any DDL/DML
- Follow the database dialect rules exactly
- Prefer explicit JOINs with clear ON clauses
- Use table aliases when joining multiple tables
- Never invent tables or columns that are not present in the schema
- If the question is ambiguous, choose the most reasonable interpretation
- Always include a LIMIT (or dialect-equivalent) for safety

{dialect_rules}
"""

    plan_text = ""
    if plan:
        import json
        plan_text = f"""
[Query Plan]
{json.dumps(plan, ensure_ascii=False, indent=2)}
"""

    user_prompt = f"""[Database Dialect]
{dialect}

[User Question]
{question}

[Available Schema]
{schema_summary}
{plan_text}

Generate the SQL query. Use this exact format:

<reasoning>
(Step-by-step reasoning for the query)
</reasoning>
<sql>
SELECT ...
</sql>
"""

    return system_prompt, user_prompt


# ========== SQL Repair Prompt ==========

def build_repair_prompt(
    question: str,
    dialect: str,
    dialect_rules: str,
    schema_summary: str,
    previous_sql: str,
    error_message: str
) -> Tuple[str, str]:
    """
    SQL Repair 노드용 프롬프트 생성.
    
    Args:
        question: 사용자 질문
        dialect: DB 방언
        dialect_rules: 방언별 규칙
        schema_summary: 스키마 요약
        previous_sql: 이전에 생성한 SQL
        error_message: 실행 에러 메시지
        
    Returns:
        (system_prompt, user_prompt) 튜플
    """
    system_prompt = f"""You are a senior data engineer responsible for fixing SQL errors.

Requirements:
- Fix the SQL query based on the error message
- Follow the database dialect rules exactly
- ONLY write a single SELECT query
- DO NOT use INSERT, UPDATE, DELETE, or any DDL/DML

{dialect_rules}
"""

    user_prompt = f"""[Database Dialect]
{dialect}

[User Question]
{question}

[Available Schema]
{schema_summary}

[Previous SQL]
{previous_sql}

[Error Message]
{error_message}

Fix the SQL query. Use this exact format:

<reasoning>
(Explanation of what was wrong and how to fix it)
</reasoning>
<sql>
SELECT ...
</sql>
"""

    return system_prompt, user_prompt


# ========== Answer Formatter Prompt ==========

def build_answer_prompt(
    question: str,
    sql: str,
    result: Optional[List[Dict[str, Any]]],
    dialect: str
) -> Tuple[str, str]:
    """
    Answer Formatter 노드용 프롬프트 생성.
    
    Args:
        question: 사용자 질문
        sql: 생성된 SQL
        result: 실행 결과 (샘플 데이터)
        dialect: DB 방언
        
    Returns:
        (system_prompt, user_prompt) 튜플
    """
    system_prompt = """You are a helpful data analyst assistant.

Your job is to:
1. Briefly summarize what the SQL query does
2. Explain the results in natural language
3. Use Korean for the summary

Keep the response concise and helpful.
"""

    result_text = ""
    if result:
        import json
        # 샘플 결과 (최대 5행)
        sample = result[:5]
        result_text = f"""
[Query Results (Sample)]
{json.dumps(sample, ensure_ascii=False, indent=2)}
Total rows returned: {len(result)}
"""
    else:
        result_text = "[Query Results]\nNo results or query not executed."

    user_prompt = f"""[User Question]
{question}

[Generated SQL]
```sql
{sql}
```

[Database Type]
{dialect}
{result_text}

Please provide a brief Korean summary of:
1. What the query does
2. The results (if available)
"""

    return system_prompt, user_prompt

