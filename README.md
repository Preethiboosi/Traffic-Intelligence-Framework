# Traffic Intelligence Framework

A lightweight, local-first POC for evaluating vendor traffic quality in media buying — without relying on downstream conversion data.

Built as a demonstration of three connected layers:
1. **Traffic-quality analytics** — behavioral scoring across 6 engagement signals
2. **Anomaly detection / decisioning** — rule-based fraud flags and SCALE / MONITOR / PAUSE recommendations
3. **Experiment orchestration** — vendor A/B testing with uplift measurement

---

## Problem Statement

Media buyers running programmatic campaigns need to evaluate whether the traffic they are paying for is genuine — but **downstream conversion data is often unavailable**.

Reasons include:
- Upper-funnel campaigns with no direct conversion goal
- Attribution windows of 24–72 hours making real-time decisions impossible
- Publisher-side restrictions on conversion pixel placement
- Privacy regulations limiting cross-site tracking

Without conversion signals, teams fall back on gut feel or crude CTR checks. This framework provides an objective, explainable, behavior-based alternative.

---

## Solution Overview

The system scores vendors using **behavioral proxy signals** measured directly on landing pages:

| Signal | What it captures |
|---|---|
| CTR legitimacy | Whether click-through rates are within plausible ranges |
| Bounce rate | Whether users engage beyond the first page view |
| Dwell time | How long users spend on the landing page |
| Scroll depth | How far users scroll — a proxy for content consumption |
| Repeat visit rate | Whether users return — a healthy engagement signal |
| Trend health | Whether engagement is improving or deteriorating over time |

These signals are combined into a **composite quality score (0–100)**, then augmented with **rule-based anomaly flags** that detect patterns consistent with invalid traffic.

---

## Architecture

```
CSV Upload / Data Warehouse
        │
        ▼
src/ingestion.py          Validate columns, cast types, derive CTR, sort by vendor/date
        │
        ▼
src/feature_engineering.py  Impression spike ratio, 7-day rolling averages,
                             engagement index, trend delta, trend direction
        │
        ▼
src/scorer.py             6 behavioral signal scores → weighted composite quality_score (0–100)
        │
        ▼
src/anomaly.py            Rule-based anomaly flags → flag_severity, flag_reason
        │
        ▼
src/recommender.py        SCALE / MONITOR / PAUSE + plain-English reason
        │
        ▼
src/analytics.py          Executive KPIs, trend tables, vendor intelligence table
        │
        ▼
Streamlit Dashboard       7-section interactive UI (main.py)

src/experiment_engine.py  Parallel: A/B experiment simulation and uplift measurement
sql/                      Reference: how this pipeline would run in a production warehouse
```

All processing is in-memory. No database. No backend API. Runs entirely locally.

---

## Project Structure

```
.
├── main.py                       # Streamlit dashboard (7 sections)
├── config.yaml                   # All scoring thresholds and anomaly rules
├── requirements.txt
├── README.md
├── .gitignore
├── data/
│   ├── sample_vendor_daily.csv   # 8 vendors × 35 days of synthetic behavioral data
│   ├── sample_experiments.csv    # 5 experiment definitions
│   └── sample_event_log.csv      # Mock session-level event log (SQL demo)
├── sql/
│   ├── schema.sql                # Production database schema
│   ├── vendor_metrics.sql        # Daily aggregation query from raw events
│   └── experiment_results.sql    # Experiment result summarization query
├── src/
│   ├── ingestion.py              # Data loading and validation
│   ├── feature_engineering.py    # Rolling averages, trend features, engagement index
│   ├── scorer.py                 # Behavioral signal scoring
│   ├── anomaly.py                # Rule-based anomaly flag detection
│   ├── recommender.py            # SCALE / MONITOR / PAUSE logic
│   ├── experiment_engine.py      # Experiment simulation and uplift calculation
│   ├── analytics.py              # KPI aggregations and dashboard-ready tables
│   └── utils.py                  # Shared formatting utilities
└── docs/
    ├── approach.md               # Product thinking and design tradeoffs
    ├── architecture.md           # Data flow and module responsibilities
    ├── assumptions.md            # Key assumptions and their rationale
    ├── experiment_engine.md      # How the experiment engine works
    └── future_improvements.md    # Production path and integration opportunities
```

---

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3.8+.

---

## Run

```bash
streamlit run main.py
```

The app loads sample data by default. To use your own data, upload a CSV via the sidebar.

---

## CSV Schema

The main vendor daily dataset requires these columns:

| Column | Type | Description |
|---|---|---|
| `date` | date | Reporting date (YYYY-MM-DD) |
| `vendor_id` | string | Unique vendor identifier |
| `vendor_name` | string | Display name |
| `impressions` | int | Total impressions served |
| `clicks` | int | Total clicks recorded |
| `bounce_rate` | float (0–1) | Share of sessions with no engagement |
| `avg_session_sec` | float | Average session duration in seconds |
| `avg_scroll_depth` | float (0–1) | Average scroll depth on landing pages |
| `repeat_visit_rate` | float (0–1) | Share of sessions from returning users |
| `landing_page_views` | int | Sessions with at least one page view |
| `impressions_prev_avg` | float | Historical average impressions (for spike detection) |

**No conversion data required.**

---

## Scoring Methodology

The composite quality score is a configurable weighted average of six signals:

| Signal | Default Weight | Scoring Method |
|---|---|---|
| CTR Legitimacy | 20% | 100 within 0.5%–12% range; penalized outside |
| Bounce Score | 20% | `(1 − bounce_rate / 0.75) × 100` |
| Dwell Score | 20% | `(avg_session_sec / 120) × 100`, capped at 100 |
| Scroll Engagement | 20% | `(avg_scroll_depth / 0.30) × 100`, capped at 100 |
| Repeat Visit Score | 10% | Full score in healthy range; penalizes extremes |
| Trend Health | 10% | Based on week-over-week engagement index change |

All weights and thresholds are configurable in `config.yaml`.

---

## Anomaly Detection

Flags are applied independently from the quality score. Severe flags force a PAUSE.

| Flag | Trigger | Severity |
|---|---|---|
| `IMPRESSION_SPIKE` | Impressions > 3× historical average | Severe |
| `HIGH_CTR_ANOMALY` | CTR > 15% | Severe |
| `HIGH_BOUNCE_LOW_DWELL` | Bounce > 85% AND session < 10s | Severe |
| `ENGAGEMENT_COLLAPSE` | Engagement index drops >30% vs baseline | Severe |
| `LOW_SCROLL_TRAFFIC` | Scroll depth < 10% with >100 clicks | Warning |
| `REPEAT_PATTERN_ANOMALY` | Repeat visit rate > 95% | Warning |

---

## Experiment Engine

The experiment engine supports vendor-level A/B testing without a backend service:

- Define experiments with control/variant traffic allocation
- Randomly assign vendor traffic rows to control or variant groups
- Compare behavioral outcomes: CTR, bounce rate, session time, scroll depth, repeat rate
- Compute uplift percentages and generate plain-English recommendations

See [`docs/experiment_engine.md`](docs/experiment_engine.md) for full details.

---

## SQL / Analytics Layer

The `sql/` folder demonstrates how this pipeline would operate in a production warehouse:

- `schema.sql` — table schemas for raw events, vendor metrics, and experiment tracking
- `vendor_metrics.sql` — daily aggregation from session-level events
- `experiment_results.sql` — control vs variant comparison with uplift calculation

The SQL layer connects to `data/sample_event_log.csv`, which shows the raw event format that would feed the pipeline via a tag or pixel.

---

## Dashboard Sections

1. **Executive Overview** — KPIs: vendors, avg score, scale/monitor/pause counts, active experiments
2. **Vendor Intelligence Table** — latest score, trend direction, recommendation, and flags per vendor
3. **Quality Trend Analysis** — score and engagement over time; rising-risk vendor table
4. **Suspicious Traffic Analysis** — flagged vendors with plain-English explanations
5. **Experiment Engine** — experiment registry, simulation, control vs variant comparison, uplift chart
6. **Vendor Drilldown** — full historical view per vendor with anomaly markers
7. **Methodology** — scoring logic, anomaly rules, experiment assumptions, pipeline diagram

---

## Limitations

- Uses synthetic data, not real ad traffic logs
- Rule-based anomaly detection only — no statistical modeling
- Aggregate-level analysis — cannot identify individual bot sessions
- Experiment results are directional only — no formal significance testing
- No external data enrichment (IVT vendors, domain reputation)

---

## Future Improvements

See [`docs/future_improvements.md`](docs/future_improvements.md).

Key next steps:
- Connect to DSP APIs or a data warehouse (BigQuery, Snowflake) for live data
- Add Isolation Forest or similar for statistical anomaly detection
- Integrate GrowthBook or PostHog for production-grade experiment significance testing
- Schedule the pipeline via Airflow or dbt
- Add automated alerts for PAUSE-threshold crossings
