# Assumptions

## Data

**Vendor-level daily aggregation.**
The primary input is aggregated metrics per vendor per day, not individual session logs. This is the most practical format for media buying teams — it matches what DSP reporting APIs and ad servers typically export. Session-level analysis requires raw log access, which is noted in `future_improvements.md`.

**No conversion data required.**
The system is designed to operate without downstream conversion or form-fill data. Conversions are neither a required column nor a scoring signal. This is a deliberate design choice, not a limitation to work around. Conversion data, where available, could be added as an optional enrichment layer.

**Historical baseline is provided.**
The `impressions_prev_avg` column is assumed to represent a prior rolling average, computed upstream (e.g., a 7-day rolling average from the previous week). In the POC, this column is provided in the CSV. In production, it would be derived from the `vendor_daily_metrics` table using a window function (see `sql/vendor_metrics.sql`). If this column is zero or missing, the system falls back to current-day impressions, which disables spike detection for that row.

**CTR is derived, not provided.**
Click-through rate is computed from impression and click counts during ingestion. Source data is trusted as-is — no deduplication or fraud filtering is applied before ingestion.

**Data is sorted by vendor and date.**
The pipeline requires rows sorted by `(vendor_id, date)` for rolling window calculations. This is enforced during ingestion.

---

## Scoring

**Configurable weighting.**
Default weights (20% / 20% / 20% / 20% / 10% / 10%) reflect a reasonable starting point for display advertising. The right weights depend on campaign type, advertiser goals, and historical performance data. They are fully adjustable in `config.yaml`.

**Engagement index is directional, not absolute.**
The engagement index (used for trend health scoring) is a composite of session time, inverse bounce rate, and scroll depth. It is designed to detect relative change over time, not to represent an absolute quality level. A vendor with a consistently low engagement index but a stable or improving trend will score higher on trend health than a vendor with a high but rapidly declining index.

**Rolling features require sufficient history.**
Trend features use a 7-day rolling window. Vendors with fewer than 7 days of data will have trend features computed from whatever data exists (using `min_periods=1`). Trend health scores for vendors with very short history should be interpreted cautiously.

**Session time target is approximate.**
The 120-second benchmark for a "full-quality" session is a reasonable heuristic for display advertising landing pages. It should be adjusted based on campaign type: longer-form content (articles, whitepapers) warrants a higher target; quick-decision pages (pricing, sign-up) may warrant a lower one.

---

## Anomaly Detection

**Flags are independent of the composite score.**
A vendor can score well on engagement signals but still be flagged for suspicious volume patterns. The recommendation engine treats any severe flag as grounds for PAUSE, regardless of score. This reflects operational reality: fraud can make engagement metrics look clean.

**Thresholds are intentionally conservative.**
Default thresholds are designed to minimize false negatives (missed fraud) over false positives (unnecessarily pausing clean vendors). In a live environment with real stakes, the threshold calibration should be validated against historical data.

**No session-level analysis.**
This system operates on daily aggregates. Detecting individual bot IPs, coordinated click patterns, or device fingerprinting requires raw session log access. The SQL schema and event log sample demonstrate what that raw data would look like.

**Trend delta requires prior history.**
The ENGAGEMENT_COLLAPSE flag depends on the trend delta, which requires at least 14 days of data to be meaningful (7-day rolling baseline + 7-day lag). On shorter histories, this flag may not trigger even when engagement has genuinely collapsed.

---

## Experiments

**Variant assignment is random at the row (vendor-day) level.**
In a real system, variant assignment would happen at the session or user level to prevent cross-contamination. The POC assigns entire vendor-day rows to control or variant, which is a simplification appropriate for the data granularity available.

**Results are directional, not statistically confirmed.**
No formal hypothesis testing (p-values, confidence intervals, multiple-comparison correction) is implemented. Uplift percentages indicate direction and magnitude but do not confirm statistical significance.

**Experiment date ranges must overlap with available data.**
The simulation filters traffic by experiment date range and vendor ID. If the uploaded dataset does not cover the experiment period, the simulation will return no results.

---

## General

**Local-first, no external dependencies.**
The system runs entirely on a local machine with no external API calls, database connections, or cloud dependencies. This is appropriate for a POC and interview demonstration.

**No data enrichment.**
Domain reputation, publisher categorization, and third-party IVT (invalid traffic) scores are not incorporated. These would be meaningful additions in a production system.
