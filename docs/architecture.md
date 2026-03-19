# Architecture

## Overview

The system is a modular, single-pipeline local application. Data flows linearly from input to output with clear separation of concerns at each stage.

```
┌──────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard (main.py)              │
│  Executive Overview · Vendor Intelligence · Quality Trends    │
│  Suspicious Traffic · Experiment Engine · Drilldown · Method  │
└──────────────────────────┬───────────────────────────────────┘
                           │ calls pipeline functions
        ┌──────────────────▼─────────────────┐
        │         src/ingestion.py            │
        │  Load CSV or uploaded file          │
        │  Validate required columns          │
        │  Cast types, clip negatives         │
        │  Derive CTR                         │
        │  Sort by vendor_id + date           │
        └──────────────────┬─────────────────┘
                           │
        ┌──────────────────▼─────────────────┐
        │      src/feature_engineering.py     │
        │  Impression spike ratio             │
        │  7-day rolling averages             │
        │  Engagement index (composite)       │
        │  Trend delta (WoW change)           │
        │  Trend direction (improving/stable/ │
        │                   declining)        │
        └──────────────────┬─────────────────┘
                           │
        ┌──────────────────▼─────────────────┐
        │           src/scorer.py             │
        │  CTR score (0–100)                  │
        │  Bounce score (0–100)               │
        │  Dwell score (0–100)                │
        │  Scroll engagement score (0–100)    │
        │  Repeat visit score (0–100)         │
        │  Trend health score (0–100)         │
        │  Weighted composite quality_score   │
        └──────────────────┬─────────────────┘
                           │
        ┌──────────────────▼─────────────────┐
        │           src/anomaly.py            │
        │  IMPRESSION_SPIKE flag              │
        │  HIGH_CTR_ANOMALY flag              │
        │  HIGH_BOUNCE_LOW_DWELL flag         │
        │  ENGAGEMENT_COLLAPSE flag           │
        │  LOW_SCROLL_TRAFFIC flag            │
        │  REPEAT_PATTERN_ANOMALY flag        │
        │  flag_severity: severe/warning/none │
        │  flag_reason: plain English text    │
        └──────────────────┬─────────────────┘
                           │
        ┌──────────────────▼─────────────────┐
        │         src/recommender.py          │
        │  SCALE / MONITOR / PAUSE decision   │
        │  Plain-English reason text          │
        └──────────────────┬─────────────────┘
                           │
        ┌──────────────────▼─────────────────┐
        │          src/analytics.py           │
        │  Executive KPI summary              │
        │  Vendor intelligence table          │
        │  Trend data for charts              │
        │  Suspicious traffic table           │
        │  Vendor drilldown data              │
        │  Rising-risk vendor list            │
        └──────────────────┬─────────────────┘
                           │
                    Dashboard renders

src/experiment_engine.py — parallel path:
    Load experiments CSV
    Assign traffic variants (random by allocation ratio)
    Summarize control vs variant metrics
    Compute uplift
    Generate recommendation text

sql/ — reference artifacts:
    schema.sql            Target warehouse schema
    vendor_metrics.sql    Daily aggregation from raw events
    experiment_results.sql  Experiment comparison query
```

---

## Module responsibilities

| Module | Single responsibility |
|---|---|
| `ingestion.py` | Load, validate, and type-cast raw input data |
| `feature_engineering.py` | Derive time-aware features (rolling averages, trend delta, engagement index) |
| `scorer.py` | Compute per-signal and composite quality scores |
| `anomaly.py` | Detect rule-based anomaly flags and classify severity |
| `recommender.py` | Map score + severity → SCALE / MONITOR / PAUSE + reason |
| `analytics.py` | Aggregate and format data for each dashboard section |
| `experiment_engine.py` | Experiment definition, variant assignment, and result summarization |
| `utils.py` | Shared formatting helpers |
| `main.py` | Presentation only — calls pipeline functions, renders Streamlit UI |

---

## Key design decisions

**No database.** All processing uses pandas DataFrames in memory. For a POC evaluating hundreds of vendor-days, this is sufficient and eliminates setup friction. The `sql/` folder shows exactly how this transitions to a warehouse in production.

**No backend API.** Streamlit calls pipeline functions directly. Adding a REST layer would introduce complexity with no benefit at this scope.

**Configuration over code.** All thresholds, weights, and flag rules live in `config.yaml`. Analysts can tune sensitivity without touching Python.

**Time-aware by design.** The system is built around daily vendor data with rolling windows. Single-snapshot inputs still work (trend features gracefully degrade to neutral), but the architecture is designed to grow with time-series data.

**Separation between scoring and flags.** The quality score and anomaly flags are computed independently. A vendor can have a high score but still be flagged (and paused) due to an impression spike. This mirrors how experienced buyers operate: engagement metrics alone are not sufficient if volume behavior is suspicious.

---

## Scalability path

To move this from POC to production:

1. **Data source:** Replace CSV with a SQL query or warehouse connector (BigQuery, Snowflake, Redshift). The `sql/vendor_metrics.sql` file shows the aggregation query to run daily.
2. **Scheduling:** Wrap the pipeline in Airflow, dbt, or a simple cron job to score vendors automatically each morning.
3. **Persistence:** Write scored output back to `vendor_daily_metrics` table rather than rendering in Streamlit; connect a BI tool (Looker, Metabase) for dashboarding.
4. **Alerting:** Add a notification step when vendors cross into PAUSE territory (Slack webhook, email).
5. **Experimentation:** Replace the in-memory experiment simulation with GrowthBook or PostHog for production-grade assignment, significance testing, and result tracking.
6. **Event instrumentation:** The `sql/schema.sql` and `data/sample_event_log.csv` define the raw event format. Deploying a tag or pixel on landing pages produces this data natively.
