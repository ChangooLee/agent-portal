-- Data Cloud Schema for Agent Portal
-- Zero Copy Database Connector (Salesforce Data Cloud 스타일)
-- Created: 2025-11-27

USE agent_portal;

-- 데이터베이스 연결 정보
CREATE TABLE IF NOT EXISTS db_connections (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    db_type ENUM('mariadb', 'postgresql', 'mysql', 'oracle', 'sap_hana', 'mssql', 'clickhouse') NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    database_name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password_encrypted TEXT NOT NULL,  -- Fernet 암호화 저장
    extra_config JSON,  -- SSL, charset, timeout, SSH 터널 등 추가 설정
    -- Kong Gateway 연동
    kong_service_id VARCHAR(36),
    kong_route_id VARCHAR(36),
    kong_consumer_id VARCHAR(36),
    kong_api_key VARCHAR(255),
    -- 상태 관리
    enabled BOOLEAN DEFAULT TRUE,
    health_status ENUM('unknown', 'healthy', 'unhealthy') DEFAULT 'unknown',
    last_health_check TIMESTAMP NULL,
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    -- 인덱스
    INDEX idx_db_type (db_type),
    INDEX idx_enabled (enabled),
    INDEX idx_health_status (health_status)
);

-- 스키마 메타데이터 캐시 (SQLAlchemy 리플렉션 결과)
CREATE TABLE IF NOT EXISTS db_schema_cache (
    id VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL,
    schema_name VARCHAR(255),  -- PostgreSQL의 경우 스키마명 (public 등)
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(100),
    character_maximum_length INT,
    numeric_precision INT,
    numeric_scale INT,
    is_nullable BOOLEAN DEFAULT TRUE,
    is_primary_key BOOLEAN DEFAULT FALSE,
    is_foreign_key BOOLEAN DEFAULT FALSE,
    foreign_key_ref VARCHAR(500),  -- schema.table.column 형식
    column_default TEXT,
    column_comment TEXT,
    ordinal_position INT,
    -- 비즈니스 용어 매핑
    business_term VARCHAR(255),
    -- 캐시 관리
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    -- 인덱스
    INDEX idx_connection_table (connection_id, table_name),
    INDEX idx_schema_table (schema_name, table_name),
    UNIQUE KEY uk_column (connection_id, schema_name, table_name, column_name)
);

-- 테이블 메타데이터 캐시
CREATE TABLE IF NOT EXISTS db_table_cache (
    id VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL,
    schema_name VARCHAR(255),
    table_name VARCHAR(255) NOT NULL,
    table_type ENUM('table', 'view', 'materialized_view') DEFAULT 'table',
    table_comment TEXT,
    row_count BIGINT,  -- 추정 행 수
    data_size BIGINT,  -- 추정 데이터 크기 (bytes)
    -- 캐시 관리
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    -- 인덱스
    INDEX idx_connection (connection_id),
    UNIQUE KEY uk_table (connection_id, schema_name, table_name)
);

-- 비즈니스 용어집 (Data Cloud 스타일 용어 매핑)
CREATE TABLE IF NOT EXISTS db_business_terms (
    id VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL,
    technical_name VARCHAR(255) NOT NULL,  -- 테이블명 또는 컬럼명
    technical_type ENUM('table', 'column') NOT NULL,
    parent_table VARCHAR(255),  -- 컬럼인 경우 소속 테이블
    business_name VARCHAR(255) NOT NULL,   -- 비즈니스 용어 (예: CUST_TX_DVSN_CD → 고객 거래 분류 코드)
    description TEXT,
    examples TEXT,  -- 예시 값들
    data_domain VARCHAR(100),  -- 데이터 도메인 (금액, 코드, 일자 등)
    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    -- 인덱스
    INDEX idx_connection (connection_id),
    INDEX idx_technical_name (technical_name),
    UNIQUE KEY uk_term (connection_id, technical_type, technical_name, parent_table)
);

-- 권한 관리 (MCP와 동일 패턴)
CREATE TABLE IF NOT EXISTS db_connection_permissions (
    id VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL,
    permission_type ENUM('user', 'group') NOT NULL,
    target_id VARCHAR(36) NOT NULL,  -- user_id 또는 group_id
    permission_level ENUM('read', 'write', 'admin') DEFAULT 'read',  -- 읽기/쓰기/관리 권한
    granted_by VARCHAR(36),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    -- 인덱스
    INDEX idx_connection (connection_id),
    INDEX idx_target (permission_type, target_id),
    UNIQUE KEY uk_permission (connection_id, permission_type, target_id)
);

-- 쿼리 실행 로그 (감사 및 분석용)
CREATE TABLE IF NOT EXISTS db_query_logs (
    id VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    query_text TEXT NOT NULL,
    query_type ENUM('select', 'insert', 'update', 'delete', 'other') DEFAULT 'select',
    execution_time_ms INT,
    rows_affected INT,
    status ENUM('success', 'error') DEFAULT 'success',
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    -- 인덱스
    INDEX idx_connection_user (connection_id, user_id),
    INDEX idx_executed_at (executed_at),
    INDEX idx_status (status)
);

-- 저장된 쿼리 (자주 사용하는 쿼리 저장)
CREATE TABLE IF NOT EXISTS db_saved_queries (
    id VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    query_text TEXT NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,  -- 공개 여부
    created_by VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    -- 인덱스
    INDEX idx_connection (connection_id),
    INDEX idx_created_by (created_by),
    INDEX idx_public (is_public)
);

