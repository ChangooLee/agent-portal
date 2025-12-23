-- Migration script to add stdio MCP server fields
-- Run this if the table already exists

-- Add stdio-related columns to mcp_servers table
ALTER TABLE mcp_servers 
ADD COLUMN IF NOT EXISTS github_url VARCHAR(500) COMMENT 'GitHub 저장소 URL',
ADD COLUMN IF NOT EXISTS local_path VARCHAR(500) COMMENT '로컬 저장 경로',
ADD COLUMN IF NOT EXISTS command TEXT COMMENT '실행 명령어',
ADD COLUMN IF NOT EXISTS env_vars JSON COMMENT '환경 변수',
ADD COLUMN IF NOT EXISTS process_pid INT COMMENT '프로세스 PID',
ADD COLUMN IF NOT EXISTS process_status ENUM('stopped', 'starting', 'running', 'error') DEFAULT 'stopped';

-- Update transport_type enum to include 'stdio'
-- Note: MariaDB doesn't support ALTER ENUM directly, so we need to recreate
-- This is a simplified version - in production, you may need to handle existing data
ALTER TABLE mcp_servers 
MODIFY COLUMN transport_type ENUM('streamable_http', 'sse', 'stdio') DEFAULT 'streamable_http';

-- Create mcp_process_logs table if it doesn't exist
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


