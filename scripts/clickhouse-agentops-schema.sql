-- AgentOps ClickHouse Schema Migration
-- This script recreates the otel_traces table with AgentOps-compatible schema
-- Key difference: project_id is a MATERIALIZED column extracted from ResourceAttributes

-- Step 1: Backup existing data (if any)
-- DROP TABLE IF EXISTS otel_2.otel_traces_backup;
-- CREATE TABLE otel_2.otel_traces_backup AS otel_2.otel_traces;

-- Step 2: Drop existing table and related views
DROP VIEW IF EXISTS otel_2.otel_traces_trace_id_ts_mv;
DROP VIEW IF EXISTS otel_2.otel_traces_project_idx;
DROP TABLE IF EXISTS otel_2.otel_traces_trace_id_ts;
DROP TABLE IF EXISTS otel_2.otel_traces;

-- Step 3: Create AgentOps-compatible otel_traces table
-- Key: project_id is MATERIALIZED from ResourceAttributes['agentops.project.id']
CREATE TABLE otel_2.otel_traces (
    `Timestamp` DateTime64(9) CODEC(Delta(8), ZSTD(1)),
    `project_id` String MATERIALIZED ResourceAttributes['agentops.project.id'],
    `TraceId` String CODEC(ZSTD(1)),
    `SpanId` String CODEC(ZSTD(1)),
    `ParentSpanId` String CODEC(ZSTD(1)),
    `TraceState` String CODEC(ZSTD(1)),
    `SpanName` LowCardinality(String) CODEC(ZSTD(1)),
    `SpanKind` LowCardinality(String) CODEC(ZSTD(1)),
    `ServiceName` LowCardinality(String) CODEC(ZSTD(1)),
    `ResourceAttributes` Map(LowCardinality(String), String) CODEC(ZSTD(1)),
    `ScopeName` String CODEC(ZSTD(1)),
    `ScopeVersion` String CODEC(ZSTD(1)),
    `SpanAttributes` Map(LowCardinality(String), String) CODEC(ZSTD(1)),
    `Duration` UInt64 CODEC(ZSTD(1)),
    `StatusCode` LowCardinality(String) CODEC(ZSTD(1)),
    `StatusMessage` String CODEC(ZSTD(1)),
    `Events.Timestamp` Array(DateTime64(9)) CODEC(ZSTD(1)),
    `Events.Name` Array(LowCardinality(String)) CODEC(ZSTD(1)),
    `Events.Attributes` Array(Map(LowCardinality(String), String)) CODEC(ZSTD(1)),
    `Links.TraceId` Array(String) CODEC(ZSTD(1)),
    `Links.SpanId` Array(String) CODEC(ZSTD(1)),
    `Links.TraceState` Array(String) CODEC(ZSTD(1)),
    `Links.Attributes` Array(Map(LowCardinality(String), String)) CODEC(ZSTD(1)),
    INDEX idx_trace_id TraceId TYPE bloom_filter(0.001) GRANULARITY 16,
    INDEX idx_span_id SpanId TYPE bloom_filter(0.01) GRANULARITY 32,
    INDEX idx_project_id project_id TYPE bloom_filter(0.001) GRANULARITY 16
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(Timestamp)
ORDER BY (project_id, Timestamp)
SETTINGS index_granularity = 8192;

-- Step 4: Create supporting table for trace ID timestamps
CREATE TABLE otel_2.otel_traces_trace_id_ts (
    `TraceId` String CODEC(ZSTD(1)),
    `Start` DateTime CODEC(Delta(4), ZSTD(1)),
    `End` DateTime CODEC(Delta(4), ZSTD(1)),
    INDEX idx_trace_id TraceId TYPE bloom_filter(0.01) GRANULARITY 1
) ENGINE = MergeTree()
PARTITION BY toDate(Start)
ORDER BY (TraceId, Start)
TTL toDate(Start) + toIntervalHour(12)
SETTINGS index_granularity = 8192, ttl_only_drop_parts = 1;

-- Step 5: Create materialized view for trace ID timestamps
CREATE MATERIALIZED VIEW otel_2.otel_traces_trace_id_ts_mv
TO otel_2.otel_traces_trace_id_ts
AS SELECT
    TraceId,
    min(Timestamp) AS Start,
    max(Timestamp) AS End
FROM otel_2.otel_traces
WHERE TraceId != ''
GROUP BY TraceId;

-- Step 6: Create materialized view for project index
CREATE MATERIALIZED VIEW otel_2.otel_traces_project_idx
(
    `Timestamp` DateTime64(9),
    `TraceId` String,
    `SpanId` String,
    `project_id` String
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(Timestamp)
ORDER BY (project_id, TraceId, SpanId)
SETTINGS index_granularity = 8192
AS SELECT
    Timestamp,
    TraceId,
    SpanId,
    ResourceAttributes['agentops.project.id'] AS project_id
FROM otel_2.otel_traces
WHERE ResourceAttributes['agentops.project.id'] != '';


