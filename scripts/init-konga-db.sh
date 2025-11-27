#!/bin/bash
# Konga Database Initialization Script
# This script manually creates Konga database schema when auto-migration fails
# Usage: ./init-konga-db.sh

set -e

DB_HOST="${DB_HOST:-konga-db}"
DB_USER="${DB_USER:-konga}"
DB_PASSWORD="${DB_PASSWORD:-kongapass}"
DB_DATABASE="${DB_DATABASE:-konga}"

echo "Initializing Konga database schema..."

export PGPASSWORD="$DB_PASSWORD"

psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_DATABASE" << 'SQL'
-- Drop existing tables for clean reinstall (comment out if not needed)
-- DROP TABLE IF EXISTS konga_snapshots CASCADE;
-- DROP TABLE IF EXISTS konga_connections CASCADE;
-- DROP TABLE IF EXISTS konga_settings CASCADE;
-- DROP TABLE IF EXISTS konga_users CASCADE;

-- Create users table with all required columns (camelCase)
CREATE TABLE IF NOT EXISTS konga_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    "firstName" VARCHAR(255),
    "lastName" VARCHAR(255),
    "nodeId" VARCHAR(255),
    "node" VARCHAR(255),
    "activationToken" VARCHAR(255),
    "createdUserId" INTEGER,
    "updatedUserId" INTEGER,
    admin BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

-- Create connections table
CREATE TABLE IF NOT EXISTS konga_connections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    host VARCHAR(255),
    port INTEGER,
    data TEXT,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

-- Create snapshots table
CREATE TABLE IF NOT EXISTS konga_snapshots (
    id SERIAL PRIMARY KEY,
    "connectionId" INTEGER REFERENCES konga_connections(id) ON DELETE CASCADE,
    "userId" INTEGER REFERENCES konga_users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    "kongaVersion" VARCHAR(50),
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_konga_users_username ON konga_users(username);
CREATE INDEX IF NOT EXISTS idx_konga_users_email ON konga_users(email);
CREATE INDEX IF NOT EXISTS idx_konga_connections_name ON konga_connections(name);
CREATE INDEX IF NOT EXISTS idx_konga_snapshots_connection_id ON konga_snapshots("connectionId");
CREATE INDEX IF NOT EXISTS idx_konga_snapshots_user_id ON konga_snapshots("userId");

-- Display created tables
\dt
SQL

echo "Konga database schema initialization completed."
echo "You can now start Konga with: docker compose up -d konga"


