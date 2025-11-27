-- Project Management Schema
-- Agent Portal 프로젝트/팀 관리를 위한 MariaDB 스키마

-- 프로젝트 테이블
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_created_by (created_by)
);

-- 팀 테이블
CREATE TABLE IF NOT EXISTS teams (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_created_by (created_by)
);

-- 팀-프로젝트 매핑 테이블
CREATE TABLE IF NOT EXISTS team_projects (
    team_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, project_id),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 사용자-팀 매핑 테이블 (역할 포함)
CREATE TABLE IF NOT EXISTS team_members (
    team_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    role ENUM('owner', 'admin', 'member', 'viewer') DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, user_id),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_role (role)
);

-- 기본 프로젝트 삽입 (현재 하드코딩된 project_id)
INSERT INTO projects (id, name, description, created_by)
VALUES ('8c59e361-3727-418c-bc68-086b69f7598b', 'Default Project', 'Default project for LLM monitoring', NULL)
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- 기본 팀 삽입
INSERT INTO teams (id, name, description, created_by)
VALUES ('default-team', 'Default Team', 'Default team with access to all projects', NULL)
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- 기본 팀에 기본 프로젝트 할당
INSERT INTO team_projects (team_id, project_id)
VALUES ('default-team', '8c59e361-3727-418c-bc68-086b69f7598b')
ON DUPLICATE KEY UPDATE assigned_at = CURRENT_TIMESTAMP;
