-- =============================================================================
-- Traffic Intelligence Framework — Database Schema
-- =============================================================================
-- This schema represents how the system would be deployed in a production
-- data warehouse (BigQuery, Snowflake, Redshift, or Postgres).
-- In the POC, data is CSV-based; these schemas define the target architecture.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- Raw event log
-- Populated by pixel/tag instrumentation on landing pages.
-- One row per user interaction event.
-- ---------------------------------------------------------------------------
CREATE TABLE raw_events (
    event_id            UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    event_timestamp     TIMESTAMP       NOT NULL,
    session_id          VARCHAR(64)     NOT NULL,
    user_id             VARCHAR(64),                        -- nullable for anonymous users
    vendor_id           VARCHAR(32)     NOT NULL,
    vendor_name         VARCHAR(128),
    event_type          VARCHAR(32)     NOT NULL,           -- 'impression' | 'click' | 'scroll' | 'session_end'
    page_url            TEXT,
    scroll_pct          FLOAT,                              -- 0.0–1.0; null if not a scroll event
    session_sec_elapsed FLOAT,                             -- seconds since session start
    referrer_url        TEXT,
    user_agent          TEXT,
    is_bot_suspected    BOOLEAN         DEFAULT FALSE,
    created_at          TIMESTAMP       DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- Daily vendor aggregates
-- Materialized from raw_events via vendor_metrics.sql (scheduled daily).
-- This is the primary input table for the scoring pipeline.
-- ---------------------------------------------------------------------------
CREATE TABLE vendor_daily_metrics (
    id                      SERIAL          PRIMARY KEY,
    date                    DATE            NOT NULL,
    vendor_id               VARCHAR(32)     NOT NULL,
    vendor_name             VARCHAR(128),
    impressions             BIGINT,
    clicks                  BIGINT,
    ctr                     FLOAT,
    bounce_rate             FLOAT,
    avg_session_sec         FLOAT,
    avg_scroll_depth        FLOAT,
    repeat_visit_rate       FLOAT,
    landing_page_views      BIGINT,
    impressions_prev_avg    FLOAT,                          -- 7-day rolling average impressions
    quality_score           FLOAT,
    recommendation          VARCHAR(16),                    -- 'SCALE' | 'MONITOR' | 'PAUSE'
    flags                   TEXT[],                         -- array of active flag names
    flag_severity           VARCHAR(16),                    -- 'severe' | 'warning' | 'none'
    created_at              TIMESTAMP       DEFAULT NOW(),
    UNIQUE (date, vendor_id)
);


-- ---------------------------------------------------------------------------
-- Experiment definitions
-- One row per experiment configured by the media buying team.
-- ---------------------------------------------------------------------------
CREATE TABLE experiments (
    experiment_id           VARCHAR(32)     PRIMARY KEY,
    experiment_name         VARCHAR(256)    NOT NULL,
    start_date              DATE            NOT NULL,
    end_date                DATE            NOT NULL,
    status                  VARCHAR(16)     NOT NULL,       -- 'active' | 'paused' | 'completed'
    vendor_id               VARCHAR(32)     NOT NULL,
    control_allocation      FLOAT           NOT NULL,       -- fraction of traffic → control
    variant_allocation      FLOAT           NOT NULL,       -- fraction of traffic → variant
    primary_metric          VARCHAR(64)     NOT NULL,       -- metric being optimized
    created_at              TIMESTAMP       DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- Experiment traffic assignment log
-- Records which session was assigned to which variant.
-- Written at assignment time (real-time or batch).
-- ---------------------------------------------------------------------------
CREATE TABLE experiment_assignments (
    id              SERIAL          PRIMARY KEY,
    experiment_id   VARCHAR(32)     NOT NULL REFERENCES experiments(experiment_id),
    session_id      VARCHAR(64)     NOT NULL,
    vendor_id       VARCHAR(32)     NOT NULL,
    variant         VARCHAR(16)     NOT NULL,               -- 'control' | 'variant'
    assigned_at     TIMESTAMP       NOT NULL,
    date            DATE            NOT NULL
);


-- ---------------------------------------------------------------------------
-- Experiment result summaries
-- Pre-aggregated comparison table; recomputed at experiment close or on demand.
-- ---------------------------------------------------------------------------
CREATE TABLE experiment_results (
    id                      SERIAL          PRIMARY KEY,
    experiment_id           VARCHAR(32)     NOT NULL REFERENCES experiments(experiment_id),
    metric                  VARCHAR(64)     NOT NULL,
    control_mean            FLOAT,
    variant_mean            FLOAT,
    uplift_pct              FLOAT,
    sample_size_control     INTEGER,
    sample_size_variant     INTEGER,
    is_primary              BOOLEAN         DEFAULT FALSE,
    computed_at             TIMESTAMP       DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- Indexes for common query patterns
-- ---------------------------------------------------------------------------
CREATE INDEX idx_vendor_daily_date       ON vendor_daily_metrics(date);
CREATE INDEX idx_vendor_daily_vendor     ON vendor_daily_metrics(vendor_id);
CREATE INDEX idx_vendor_daily_vendor_date ON vendor_daily_metrics(vendor_id, date);
CREATE INDEX idx_raw_events_vendor_ts    ON raw_events(vendor_id, event_timestamp);
CREATE INDEX idx_raw_events_session      ON raw_events(session_id);
CREATE INDEX idx_exp_assignments_exp     ON experiment_assignments(experiment_id, date);
CREATE INDEX idx_exp_assignments_session ON experiment_assignments(session_id);
