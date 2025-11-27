-- Konga Database Schema Initialization
-- This SQL script creates Konga database schema
-- Konga uses camelCase for column names (quoted identifiers)

-- Create users table with camelCase columns (Konga format)
CREATE TABLE IF NOT EXISTS konga_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    "firstName" VARCHAR(255),
    "lastName" VARCHAR(255),
    "node_id" VARCHAR(255),
    node VARCHAR(255),
    "activationToken" VARCHAR(255),
    "createdUserId" INTEGER,
    "updatedUserId" INTEGER,
    admin BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

-- Create kong nodes table (connections)
CREATE TABLE IF NOT EXISTS konga_kong_nodes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) DEFAULT 'default',
    "kong_admin_url" VARCHAR(255),
    "kong_api_key" VARCHAR(255),
    "kong_version" VARCHAR(50),
    "health_check_details" TEXT,
    "health_checks" BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

-- Create snapshots table
CREATE TABLE IF NOT EXISTS konga_kong_snapshots (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    "kong_node_id" INTEGER REFERENCES konga_kong_nodes(id) ON DELETE CASCADE,
    "kong_node_name" VARCHAR(255),
    "kong_version" VARCHAR(50),
    data TEXT,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

-- Create settings table
CREATE TABLE IF NOT EXISTS konga_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

-- Create api health checks table
CREATE TABLE IF NOT EXISTS konga_api_health_checks (
    id SERIAL PRIMARY KEY,
    "api_id" VARCHAR(255),
    "kong_node_id" INTEGER REFERENCES konga_kong_nodes(id) ON DELETE CASCADE,
    "health_check_endpoint" VARCHAR(255),
    "notification_endpoint" VARCHAR(255),
    active BOOLEAN DEFAULT TRUE,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_konga_users_username ON konga_users(username);
CREATE INDEX IF NOT EXISTS idx_konga_users_email ON konga_users(email);
CREATE INDEX IF NOT EXISTS idx_konga_kong_nodes_name ON konga_kong_nodes(name);
