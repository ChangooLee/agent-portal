-- MCP Gateway Schema
-- Agent Portal MCP 서버 관리를 위한 MariaDB 스키마

-- MCP 서버 테이블
CREATE TABLE IF NOT EXISTS mcp_servers (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    endpoint_url VARCHAR(500) NOT NULL,
    transport_type ENUM('streamable_http', 'sse', 'stdio') DEFAULT 'streamable_http',
    auth_type ENUM('none', 'api_key', 'bearer') DEFAULT 'none',
    auth_config JSON COMMENT '인증 설정 (api_key, bearer token 등)',
    -- Kong Gateway 연동 정보
    kong_service_id VARCHAR(36) COMMENT 'Kong Service ID',
    kong_route_id VARCHAR(36) COMMENT 'Kong Route ID',
    kong_consumer_id VARCHAR(36) COMMENT 'Kong Consumer ID',
    kong_api_key VARCHAR(255) COMMENT 'Kong에서 발급된 API Key',
    -- 상태 관리
    enabled BOOLEAN DEFAULT TRUE,
    last_health_check TIMESTAMP NULL COMMENT '마지막 연결 테스트 시간',
    health_status ENUM('unknown', 'healthy', 'unhealthy') DEFAULT 'unknown',
    -- stdio MCP 서버 관련 필드
    github_url VARCHAR(500) COMMENT 'GitHub 저장소 URL',
    local_path VARCHAR(500) COMMENT '로컬 저장 경로',
    command TEXT COMMENT '실행 명령어',
    env_vars JSON COMMENT '환경 변수',
    process_pid INT COMMENT '프로세스 PID',
    process_status ENUM('stopped', 'starting', 'running', 'error') DEFAULT 'stopped',
    -- 메타데이터
    created_by VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- 인덱스
    INDEX idx_name (name),
    INDEX idx_enabled (enabled),
    INDEX idx_transport_type (transport_type),
    INDEX idx_created_by (created_by)
);

-- MCP 서버 도구 테이블 (MCP 서버가 제공하는 도구 목록)
CREATE TABLE IF NOT EXISTS mcp_server_tools (
    id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    tool_description TEXT,
    input_schema JSON COMMENT 'JSON Schema for tool input',
    -- 메타데이터
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- 외래 키
    FOREIGN KEY (server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE,
    -- 인덱스
    INDEX idx_server_id (server_id),
    INDEX idx_tool_name (tool_name),
    UNIQUE KEY uk_server_tool (server_id, tool_name)
);

-- MCP 서버 프로젝트 매핑 테이블 (어떤 프로젝트에서 어떤 MCP 서버를 사용할 수 있는지)
CREATE TABLE IF NOT EXISTS mcp_server_projects (
    server_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (server_id, project_id),
    FOREIGN KEY (server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- MCP 서버 권한 테이블 (사용자/그룹별 접근 권한)
CREATE TABLE IF NOT EXISTS mcp_server_permissions (
    id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL,
    permission_type ENUM('user', 'group') NOT NULL COMMENT 'user: 개별 사용자, group: 그룹',
    target_id VARCHAR(36) NOT NULL COMMENT 'user_id 또는 group_id (WebUI)',
    granted_by VARCHAR(36) COMMENT '권한 부여자 user_id',
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 외래 키
    FOREIGN KEY (server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE,
    -- 유니크 제약 (동일 서버에 동일 타입/타겟 중복 방지)
    UNIQUE KEY uk_server_permission (server_id, permission_type, target_id),
    -- 인덱스
    INDEX idx_server_id (server_id),
    INDEX idx_permission_type (permission_type),
    INDEX idx_target_id (target_id)
);

-- MCP 호출 로그 테이블 (선택적: 디버깅 및 모니터링용)
CREATE TABLE IF NOT EXISTS mcp_call_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    user_id VARCHAR(36),
    project_id VARCHAR(36),
    -- 요청/응답 정보
    request_payload JSON,
    response_payload JSON,
    status ENUM('success', 'error', 'timeout') NOT NULL,
    error_message TEXT,
    -- 성능 메트릭
    latency_ms INT COMMENT '응답 시간 (밀리초)',
    -- 타임스탬프
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 인덱스
    INDEX idx_server_id (server_id),
    INDEX idx_tool_name (tool_name),
    INDEX idx_user_id (user_id),
    INDEX idx_project_id (project_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    -- 외래 키
    FOREIGN KEY (server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE
);

-- MCP 프로세스 로그 테이블 (stdio 프로세스 로그 저장)
CREATE TABLE IF NOT EXISTS mcp_process_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL,
    log_level ENUM('info', 'warning', 'error', 'debug') DEFAULT 'info',
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_server_id (server_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE
);

-- 예시 MCP 서버 삽입 (테스트용)
-- INSERT INTO mcp_servers (id, name, description, endpoint_url, transport_type, auth_type)
-- VALUES (
--     UUID(),
--     'Example MCP Server',
--     'Example MCP server for testing',
--     'http://localhost:8080/mcp',
--     'streamable_http',
--     'none'
-- );

