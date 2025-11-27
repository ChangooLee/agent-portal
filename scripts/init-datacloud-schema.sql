-- Data Cloud 스키마 초기화
-- Agent Portal Data Cloud 커넥터용 테이블

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
    extra_config JSON,  -- SSL, charset, timeout 등 추가 설정
    kong_service_id VARCHAR(36),
    kong_route_id VARCHAR(36),
    kong_consumer_id VARCHAR(36),
    kong_api_key VARCHAR(255),
    enabled BOOLEAN DEFAULT TRUE,
    health_status ENUM('unknown', 'healthy', 'unhealthy') DEFAULT 'unknown',
    last_health_check TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_db_type (db_type),
    INDEX idx_enabled (enabled),
    INDEX idx_health_status (health_status)
);

-- 스키마 메타데이터 캐시 (SQLAlchemy 리플렉션 결과 저장)
CREATE TABLE IF NOT EXISTS db_schema_cache (
    id VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL,
    schema_name VARCHAR(255),  -- PostgreSQL의 schema, Oracle의 owner 등
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
    ordinal_position INT,  -- 컬럼 순서
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    INDEX idx_connection_table (connection_id, table_name),
    INDEX idx_schema_table (schema_name, table_name)
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
    data_size_bytes BIGINT,  -- 추정 데이터 크기
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    UNIQUE KEY uk_connection_schema_table (connection_id, schema_name, table_name),
    INDEX idx_connection (connection_id)
);

-- 비즈니스 용어집 (기술명 ↔ 비즈니스명 매핑)
CREATE TABLE IF NOT EXISTS db_business_terms (
    id VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL,
    term_type ENUM('table', 'column') NOT NULL,
    schema_name VARCHAR(255),
    table_name VARCHAR(255),
    column_name VARCHAR(255),  -- term_type='column'일 때만 사용
    technical_name VARCHAR(255) NOT NULL,  -- 원본 기술명
    business_name VARCHAR(255) NOT NULL,   -- 비즈니스 용어
    description TEXT,
    examples TEXT,  -- 예시 값들
    created_by VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    UNIQUE KEY uk_term (connection_id, term_type, schema_name, table_name, column_name),
    INDEX idx_connection (connection_id),
    INDEX idx_business_name (business_name)
);

-- 권한 관리 (사용자/그룹별 DB 연결 접근 권한)
CREATE TABLE IF NOT EXISTS db_connection_permissions (
    id VARCHAR(36) PRIMARY KEY,
    connection_id VARCHAR(36) NOT NULL,
    permission_type ENUM('user', 'group') NOT NULL,
    target_id VARCHAR(36) NOT NULL,  -- user_id 또는 group_id
    access_level ENUM('read', 'write', 'admin') DEFAULT 'read',  -- 읽기/쓰기/관리
    granted_by VARCHAR(36),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    UNIQUE KEY uk_connection_permission (connection_id, permission_type, target_id),
    INDEX idx_target (permission_type, target_id)
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
    status ENUM('success', 'error') NOT NULL,
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_id) REFERENCES db_connections(id) ON DELETE CASCADE,
    INDEX idx_connection_user (connection_id, user_id),
    INDEX idx_executed_at (executed_at),
    INDEX idx_status (status)
);
