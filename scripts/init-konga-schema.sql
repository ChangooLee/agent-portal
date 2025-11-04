-- Konga Complete Database Schema
-- Execute: psql -U konga -d konga -f init-konga-schema.sql

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

CREATE TABLE IF NOT EXISTS konga_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    data TEXT,
    "createdUserId" INTEGER,
    "updatedUserId" INTEGER,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_konga_users_username ON konga_users(username);
CREATE INDEX IF NOT EXISTS idx_konga_users_email ON konga_users(email);
