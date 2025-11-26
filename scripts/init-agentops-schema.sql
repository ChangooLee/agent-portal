-- AgentOps Schema for MariaDB
-- OpenTelemetry 트레이스 데이터 저장

USE agent_portal;

-- otel_traces: OpenTelemetry 트레이스 원본 데이터
CREATE TABLE IF NOT EXISTS otel_traces (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trace_id VARCHAR(32) NOT NULL,
    span_id VARCHAR(16) NOT NULL,
    parent_span_id VARCHAR(16),
    service_name VARCHAR(255),
    span_name VARCHAR(255),
    span_kind VARCHAR(50),
    timestamp DATETIME NOT NULL,
    duration BIGINT,  -- 마이크로초 단위
    status_code VARCHAR(50),
    status_message TEXT,
    span_attributes LONGTEXT,  -- JSON
    resource_attributes LONGTEXT,  -- JSON
    project_id VARCHAR(255) NOT NULL DEFAULT 'default-project',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trace_id (trace_id),
    INDEX idx_span_id (span_id),
    INDEX idx_project_id (project_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_service_name (service_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- trace_summaries: 트레이스 요약 정보 (집계 테이블)
CREATE TABLE IF NOT EXISTS trace_summaries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trace_id VARCHAR(32) NOT NULL UNIQUE,
    project_id VARCHAR(255) NOT NULL DEFAULT 'default-project',
    service_name VARCHAR(255),
    root_span_name VARCHAR(255),
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration BIGINT,  -- 마이크로초 단위
    span_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    tags JSON,  -- 태그 배열
    total_cost DECIMAL(10, 6) DEFAULT 0.0,  -- USD
    total_tokens INT DEFAULT 0,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    model_name VARCHAR(255),
    status VARCHAR(50),  -- success, error, pending
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_trace_id (trace_id),
    INDEX idx_project_id (project_id),
    INDEX idx_start_time (start_time),
    INDEX idx_service_name (service_name),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- agent_sessions: 에이전트 세션 정보 (AgentOps SDK 연동)
CREATE TABLE IF NOT EXISTS agent_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    project_id VARCHAR(255) NOT NULL DEFAULT 'default-project',
    agent_name VARCHAR(255),
    status VARCHAR(50),  -- running, success, fail, indeterminate
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration BIGINT,  -- 밀리초 단위
    tags JSON,
    total_cost DECIMAL(10, 6) DEFAULT 0.0,
    total_tokens INT DEFAULT 0,
    error_message TEXT,
    replay_url VARCHAR(512),  -- AgentOps 리플레이 URL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_project_id (project_id),
    INDEX idx_start_time (start_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- llm_calls: LLM 호출 로그 (비용/토큰 추적)
CREATE TABLE IF NOT EXISTS llm_calls (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trace_id VARCHAR(32),
    span_id VARCHAR(16),
    session_id VARCHAR(64),
    project_id VARCHAR(255) NOT NULL DEFAULT 'default-project',
    model_name VARCHAR(255),
    provider VARCHAR(100),  -- openai, anthropic, openrouter 등
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0.0,  -- USD
    latency BIGINT,  -- 밀리초 단위
    status VARCHAR(50),
    error_message TEXT,
    timestamp DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trace_id (trace_id),
    INDEX idx_session_id (session_id),
    INDEX idx_project_id (project_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_model_name (model_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 샘플 데이터 삽입 (테스트용)
-- 현재 시간을 기준으로 최근 7일 데이터 생성
INSERT INTO trace_summaries (
    trace_id, project_id, service_name, root_span_name, 
    start_time, end_time, duration, span_count, error_count, 
    total_cost, total_tokens, prompt_tokens, completion_tokens, 
    model_name, status
) VALUES
    ('trace1234567890abcdef1234', 'default-project', 'chat-api', 'POST /chat/completions', 
     DATE_SUB(NOW(), INTERVAL 1 HOUR), DATE_SUB(NOW(), INTERVAL 1 HOUR) + INTERVAL 2 SECOND, 2000000, 5, 0,
     0.015, 1500, 1000, 500, 'qwen-235b', 'success'),
    ('trace1234567890abcdef2345', 'default-project', 'langflow-agent', 'Execute Flow', 
     DATE_SUB(NOW(), INTERVAL 2 HOUR), DATE_SUB(NOW(), INTERVAL 2 HOUR) + INTERVAL 5 SECOND, 5000000, 12, 0,
     0.045, 4200, 3000, 1200, 'gpt-4', 'success'),
    ('trace1234567890abcdef3456', 'default-project', 'chat-api', 'POST /chat/completions', 
     DATE_SUB(NOW(), INTERVAL 3 HOUR), DATE_SUB(NOW(), INTERVAL 3 HOUR) + INTERVAL 1 SECOND, 1000000, 3, 1,
     0.008, 800, 600, 200, 'qwen-235b', 'error'),
    ('trace1234567890abcdef4567', 'default-project', 'flowise-agent', 'Chat Flow', 
     DATE_SUB(NOW(), INTERVAL 6 HOUR), DATE_SUB(NOW(), INTERVAL 6 HOUR) + INTERVAL 3 SECOND, 3000000, 8, 0,
     0.025, 2800, 2000, 800, 'gpt-3.5-turbo', 'success'),
    ('trace1234567890abcdef5678', 'default-project', 'chat-api', 'POST /chat/completions', 
     DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY) + INTERVAL 2 SECOND, 2000000, 5, 0,
     0.012, 1200, 800, 400, 'qwen-235b', 'success');

-- 샘플 LLM 호출 데이터
INSERT INTO llm_calls (
    trace_id, project_id, model_name, provider,
    prompt_tokens, completion_tokens, total_tokens,
    cost, latency, status, timestamp
) VALUES
    ('trace1234567890abcdef1234', 'default-project', 'qwen-235b', 'openrouter', 1000, 500, 1500, 0.015, 1800, 'success', DATE_SUB(NOW(), INTERVAL 1 HOUR)),
    ('trace1234567890abcdef2345', 'default-project', 'gpt-4', 'openrouter', 3000, 1200, 4200, 0.045, 4500, 'success', DATE_SUB(NOW(), INTERVAL 2 HOUR)),
    ('trace1234567890abcdef3456', 'default-project', 'qwen-235b', 'openrouter', 600, 200, 800, 0.008, 900, 'error', DATE_SUB(NOW(), INTERVAL 3 HOUR)),
    ('trace1234567890abcdef4567', 'default-project', 'gpt-3.5-turbo', 'openrouter', 2000, 800, 2800, 0.025, 2800, 'success', DATE_SUB(NOW(), INTERVAL 6 HOUR)),
    ('trace1234567890abcdef5678', 'default-project', 'qwen-235b', 'openrouter', 800, 400, 1200, 0.012, 1700, 'success', DATE_SUB(NOW(), INTERVAL 1 DAY));

-- 샘플 세션 데이터
INSERT INTO agent_sessions (
    session_id, project_id, agent_name, status,
    start_time, end_time, duration,
    total_cost, total_tokens
) VALUES
    ('session1234567890abcdef12', 'default-project', 'Langflow Agent', 'success',
     DATE_SUB(NOW(), INTERVAL 1 HOUR), DATE_SUB(NOW(), INTERVAL 1 HOUR) + INTERVAL 10 SECOND, 10000,
     0.08, 6500),
    ('session1234567890abcdef23', 'default-project', 'Flowise Agent', 'success',
     DATE_SUB(NOW(), INTERVAL 3 HOUR), DATE_SUB(NOW(), INTERVAL 3 HOUR) + INTERVAL 8 SECOND, 8000,
     0.05, 4200),
    ('session1234567890abcdef34', 'default-project', 'AutoGen Agent', 'fail',
     DATE_SUB(NOW(), INTERVAL 5 HOUR), DATE_SUB(NOW(), INTERVAL 5 HOUR) + INTERVAL 2 SECOND, 2000,
     0.01, 800);

SELECT 'AgentOps schema created successfully!' as status;
