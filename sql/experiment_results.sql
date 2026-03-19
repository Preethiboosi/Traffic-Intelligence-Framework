-- =============================================================================
-- experiment_results.sql
-- =============================================================================
-- Summarizes experiment outcomes by experiment, vendor, and variant.
-- Computes per-metric uplift for control vs variant comparison.
--
-- Run at experiment close or on a scheduled basis during active experiments.
-- Output: rows suitable for INSERT INTO experiment_results
-- =============================================================================


-- Step 1: Join experiment assignments to session behavioral data
WITH assigned_sessions AS (
    SELECT
        ea.experiment_id,
        ea.session_id,
        ea.vendor_id,
        ea.variant,
        ea.date,
        e.primary_metric,
        e.experiment_name
    FROM experiment_assignments ea
    JOIN experiments e
      ON ea.experiment_id = e.experiment_id
    WHERE e.status IN ('active', 'completed')
),


-- Step 2: Compute session-level behavioral metrics from raw events
session_metrics AS (
    SELECT
        s.session_id,
        -- CTR proxy: at least one click in the session
        SUM(CASE WHEN re.event_type = 'click'      THEN 1 ELSE 0 END)  AS clicks,
        SUM(CASE WHEN re.event_type = 'impression' THEN 1 ELSE 0 END)  AS impressions,
        MAX(re.session_sec_elapsed)                                     AS session_duration_sec,
        MAX(re.scroll_pct)                                              AS max_scroll_depth,
        CASE
            WHEN MAX(re.scroll_pct) < 0.10
             AND SUM(CASE WHEN re.event_type = 'click' THEN 1 ELSE 0 END) = 0
            THEN 1 ELSE 0
        END                                                             AS is_bounce
    FROM raw_events re
    JOIN (SELECT DISTINCT session_id FROM assigned_sessions) s
      ON re.session_id = s.session_id
    GROUP BY s.session_id
),


-- Step 3: User repeat visit flag — was this user seen in multiple sessions?
user_repeat AS (
    SELECT
        re.user_id,
        ea.vendor_id,
        ea.date,
        COUNT(DISTINCT re.session_id) > 1 AS is_repeat_visitor
    FROM raw_events re
    JOIN experiment_assignments ea
      ON re.session_id = ea.session_id
    WHERE re.user_id IS NOT NULL
    GROUP BY re.user_id, ea.vendor_id, ea.date
),


-- Step 4: Combine assignment info with session behavioral metrics
enriched AS (
    SELECT
        a.experiment_id,
        a.experiment_name,
        a.vendor_id,
        a.variant,
        a.primary_metric,
        sm.clicks,
        sm.impressions,
        sm.session_duration_sec                     AS avg_session_sec,
        sm.max_scroll_depth                         AS avg_scroll_depth,
        sm.is_bounce,
        COALESCE(ur.is_repeat_visitor, FALSE)       AS is_repeat_visitor
    FROM assigned_sessions a
    LEFT JOIN session_metrics  sm ON a.session_id  = sm.session_id
    LEFT JOIN user_repeat      ur ON a.vendor_id   = ur.vendor_id
                                  AND a.date        = ur.date
),


-- Step 5: Per-variant metric averages
variant_stats AS (
    SELECT
        experiment_id,
        experiment_name,
        vendor_id,
        variant,
        primary_metric,
        COUNT(*)                                                            AS sample_size,
        -- CTR (session-level: did session generate a click?)
        ROUND(AVG(CASE WHEN clicks > 0 THEN 1.0 ELSE 0.0 END)::NUMERIC, 6) AS ctr,
        -- Bounce rate
        ROUND(AVG(is_bounce)::NUMERIC, 4)                                   AS bounce_rate,
        -- Avg session seconds
        ROUND(AVG(avg_session_sec)
              FILTER (WHERE avg_session_sec > 0)::NUMERIC, 2)               AS avg_session_sec,
        -- Avg scroll depth
        ROUND(AVG(avg_scroll_depth)
              FILTER (WHERE avg_scroll_depth IS NOT NULL)::NUMERIC, 4)      AS avg_scroll_depth,
        -- Repeat visit rate
        ROUND(AVG(CASE WHEN is_repeat_visitor THEN 1.0 ELSE 0.0 END)::NUMERIC, 4)
                                                                            AS repeat_visit_rate
    FROM enriched
    GROUP BY experiment_id, experiment_name, vendor_id, variant, primary_metric
),


-- Step 6: Pivot control and variant side by side
control_side  AS (SELECT * FROM variant_stats WHERE variant = 'control'),
variant_side  AS (SELECT * FROM variant_stats WHERE variant = 'variant')


-- Step 7: Final comparison with uplift percentages
SELECT
    c.experiment_id,
    c.experiment_name,
    c.vendor_id,
    c.primary_metric,

    -- CTR comparison
    c.ctr                                                                   AS control_ctr,
    v.ctr                                                                   AS variant_ctr,
    ROUND(((v.ctr - c.ctr) / NULLIF(c.ctr, 0) * 100)::NUMERIC, 2)        AS ctr_uplift_pct,

    -- Bounce rate comparison (lower is better)
    c.bounce_rate                                                           AS control_bounce_rate,
    v.bounce_rate                                                           AS variant_bounce_rate,
    ROUND(((v.bounce_rate - c.bounce_rate) / NULLIF(c.bounce_rate, 0) * 100)::NUMERIC, 2)
                                                                            AS bounce_uplift_pct,

    -- Avg session seconds comparison
    c.avg_session_sec                                                       AS control_avg_session_sec,
    v.avg_session_sec                                                       AS variant_avg_session_sec,
    ROUND(((v.avg_session_sec - c.avg_session_sec) / NULLIF(c.avg_session_sec, 0) * 100)::NUMERIC, 2)
                                                                            AS session_uplift_pct,

    -- Avg scroll depth comparison
    c.avg_scroll_depth                                                      AS control_avg_scroll_depth,
    v.avg_scroll_depth                                                      AS variant_avg_scroll_depth,
    ROUND(((v.avg_scroll_depth - c.avg_scroll_depth) / NULLIF(c.avg_scroll_depth, 0) * 100)::NUMERIC, 2)
                                                                            AS scroll_uplift_pct,

    -- Repeat visit rate comparison
    c.repeat_visit_rate                                                     AS control_repeat_visit_rate,
    v.repeat_visit_rate                                                     AS variant_repeat_visit_rate,
    ROUND(((v.repeat_visit_rate - c.repeat_visit_rate) / NULLIF(c.repeat_visit_rate, 0) * 100)::NUMERIC, 2)
                                                                            AS repeat_uplift_pct,

    -- Sample sizes
    c.sample_size                                                           AS sample_size_control,
    v.sample_size                                                           AS sample_size_variant

FROM control_side c
JOIN variant_side v
  ON  c.experiment_id = v.experiment_id
  AND c.vendor_id     = v.vendor_id
ORDER BY c.experiment_id, c.vendor_id;
