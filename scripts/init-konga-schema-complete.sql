-- Konga Complete Database Schema
-- This script creates all tables with correct column names based on Konga's Sails.js Waterline ORM
-- Konga uses camelCase for column names

-- Drop existing tables if they exist (for clean reinstall)
DROP TABLE IF EXISTS konga_snapshots CASCADE;
DROP TABLE IF EXISTS konga_connections CASCADE;
DROP TABLE IF EXISTS konga_settings CASCADE;
DROP TABLE IF EXISTS konga_users CASCADE;

-- Create users table with camelCase columns
CREATE TABLE konga_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    "firstName" VARCHAR(255),
    "lastName" VARCHAR(255),
    "nodeId" VARCHAR(255),
    admin BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

-- Create connections table
CREATE TABLE konga_connections (
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
CREATE TABLE konga_snapshots (
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
CREATE TABLE konga_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_konga_users_username ON konga_users(username);
CREATE INDEX idx_konga_users_email ON konga_users(email);
CREATE INDEX idx_konga_connections_name ON konga_connections(name);
CREATE INDEX idx_konga_snapshots_connection_id ON konga_snapshots("connectionId");
CREATE INDEX idx_konga_snapshots_user_id ON konga_snapshots("userId");


