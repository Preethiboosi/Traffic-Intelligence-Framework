-- =============================================================================
-- vendor_metrics.sql
-- =============================================================================
-- Aggregates raw event data into daily vendor behavioral metrics.
-- Designed to run as a scheduled job (e.g., dbt model, Airflow task,
-- BigQuery scheduled query, or Snowflake task) once per day.
--
-- Output: rows suitable for INSERT INTO vendor_daily_metrics
-- =============================================================================


-- Step 1: Session-level behavioral aggregation
-- One row per session — computes whether session bounced and its depth.
WITH session_stats AS (
    SELECT
        session_id,
        vendor_id,
        DATE(MIN(event_timestamp))                                      AS event_date,
        SUM(CASE WHEN event_type = 'impression' THEN 1 ELSE 0 END)     AS impressions,
        SUM(CASE WHEN event_type = 'click'      THEN 1 ELSE 0 END)     AS clicks,
        MAX(scroll_pct)                                                 AS max_scroll_depth,
        MAX(session_sec_elapsed)                                        AS session_duration_sec,
        -- Bounce: no meaningful scroll and no click recorded
        CASE
            WHEN MAX(scroll_pct) < 0.10
             AND SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END) = 0
            THEN 1 ELSE 0
        END                                                             AS is_bounce
    FROM raw_events
    WHERE
        NOT is_bot_suspected
        AND event_timestamp >= CURRENT_DATE - INTERVAL '1 day'  -- yesterday only
        AND event_timestamp <  CURRENT_DATE
    GROUP BY session_id, vendor_id
),


-- Step 2: User-level visit frequency for repeat visit rate
-- A "repeat visitor" is a user_id seen in more than one session for the same vendor/day.
user_visits AS (
    SELECT
        vendor_id,
        DATE(event_timestamp)           AS event_date,
        user_id,
        COUNT(DISTINCT session_id)      AS session_count
    FROM raw_events
    WHERE
        user_id IS NOT NULL
        AND event_timestamp >= CURRENT_DATE - INTERVAL '1 day'
        AND event_timestamp <  CURRENT_DATE
    GROUP BY vendor_id, DATE(event_timestamp), user_id
),

repeat_visitor_stats AS (
    SELECT
        vendor_id,
        event_date,
        COUNT(*) FILTER (WHERE session_count > 1)   AS repeat_visitors,
        COUNT(*)                                     AS total_visitors
    FROM user_visits
    GROUP BY vendor_id, event_date
),


-- Step 3: 7-day impression rolling average for spike detection baseline
-- Looks back at the vendor_daily_metrics table (prior days already aggregated).
impression_baseline AS (
    SELECT
        vendor_id,
        date,
        AVG(impressions) OVER (
            PARTITION BY vendor_id
            ORDER BY date
            ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
        ) AS impressions_prev_avg
    FROM vendor_daily_metrics
    WHERE date >= CURRENT_DATE - INTERVAL '8 days'
),


-- Step 4: Vendor name lookup
vendor_names AS (
    SELECT DISTINCT vendor_id, vendor_name
    FROM raw_events
    WHERE vendor_name IS NOT NULL
),


-- Step 5: Final daily aggregation
daily_agg AS (
    SELECT
        s.event_date                                                        AS date,
        s.vendor_id,
        vn.vendor_name,
        SUM(s.impressions)                                                  AS impressions,
        SUM(s.clicks)                                                       AS clicks,
        -- CTR
        CASE
            WHEN SUM(s.impressions) > 0
            THEN ROUND(SUM(s.clicks)::NUMERIC / SUM(s.impressions), 6)
            ELSE 0
        END                                                                 AS ctr,
        -- Bounce rate
        ROUND(AVG(s.is_bounce)::NUMERIC, 4)                                AS bounce_rate,
        -- Average session duration (exclude zero-duration sessions)
        ROUND(AVG(s.session_duration_sec)
              FILTER (WHERE s.session_duration_sec > 0)::NUMERIC, 1)       AS avg_session_sec,
        -- Average max scroll depth
        ROUND(AVG(s.max_scroll_depth)::NUMERIC, 4)                         AS avg_scroll_depth,
        -- Repeat visit rate
        CASE
            WHEN MAX(rv.total_visitors) > 0
            THEN ROUND(MAX(rv.repeat_visitors)::NUMERIC / MAX(rv.total_visitors), 4)
            ELSE 0
        END                                                                 AS repeat_visit_rate,
        -- Landing page views (sessions with at least one impression)
        COUNT(DISTINCT s.session_id)
            FILTER (WHERE s.impressions > 0)                                AS landing_page_views,
        -- 7-day baseline for spike detection
        COALESCE(MAX(ib.impressions_prev_avg), SUM(s.impressions))         AS impressions_prev_avg
    FROM session_stats s
    LEFT JOIN repeat_visitor_stats rv
           ON s.vendor_id = rv.vendor_id AND s.event_date = rv.event_date
    LEFT JOIN impression_baseline ib
           ON s.vendor_id = ib.vendor_id AND s.event_date = ib.date
    LEFT JOIN vendor_names vn
           ON s.vendor_id = vn.vendor_id
    GROUP BY s.event_date, s.vendor_id, vn.vendor_name
)


-- Final SELECT — insert this into vendor_daily_metrics via your pipeline
SELECT
    date,
    vendor_id,
    vendor_name,
    impressions,
    clicks,
    ctr,
    bounce_rate,
    avg_session_sec,
    avg_scroll_depth,
    repeat_visit_rate,
    landing_page_views,
    impressions_prev_avg
FROM daily_agg
ORDER BY date, vendor_id;


-- To materialize as a daily INSERT:
-- INSERT INTO vendor_daily_metrics
--     (date, vendor_id, vendor_name, impressions, clicks, ctr,
--      bounce_rate, avg_session_sec, avg_scroll_depth,
--      repeat_visit_rate, landing_page_views, impressions_prev_avg)
-- SELECT ...
-- ON CONFLICT (date, vendor_id) DO UPDATE SET ...;
