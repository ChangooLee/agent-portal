-- AgentOps 데이터 저장 (ClickHouse 대신 MariaDB 사용)
-- OpenTelemetry Traces 테이블 (ClickHouse otel_traces 대체)

CREATE TABLE IF NOT EXISTS otel_traces (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    span_id VARCHAR(32) NOT NULL,
    parent_span_id VARCHAR(32),
    timestamp DATETIME(6) NOT NULL,
    duration BIGINT NOT NULL COMMENT 'Duration in nanoseconds',
    status_code VARCHAR(20) NOT NULL COMMENT 'OK, ERROR',
    status_message TEXT,
    trace_state TEXT,
    span_name VARCHAR(255),
    span_kind VARCHAR(50),
    service_name VARCHAR(255),
    scope_name VARCHAR(255),
    scope_version VARCHAR(255),
    resource_attributes JSON,
    span_attributes JSON,
    event_timestamps JSON,
    event_names JSON,
    event_attributes JSON,
    link_trace_ids JSON,
    link_span_ids JSON,
    link_trace_states JSON,
    link_attributes JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trace_id (trace_id),
    INDEX idx_project_id (project_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_span_name (span_name),
    INDEX idx_status_code (status_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Trace Summary View (성능 최적화용)
CREATE TABLE IF NOT EXISTS trace_summaries (
    trace_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL,
    service_name VARCHAR(255),
    root_span_name VARCHAR(255),
    start_time DATETIME(6) NOT NULL,
    end_time DATETIME(6),
    duration BIGINT COMMENT 'Duration in nanoseconds',
    span_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    tags JSON,
    total_cost DECIMAL(10, 6) DEFAULT 0,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    cache_read_input_tokens INT DEFAULT 0,
    reasoning_tokens INT DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_project_id (project_id),
    INDEX idx_start_time (start_time),
    INDEX idx_root_span_name (root_span_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

