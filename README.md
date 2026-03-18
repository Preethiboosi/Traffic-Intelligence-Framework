# Traffic Intelligence Framework

A lightweight POC for evaluating vendor traffic quality in media buying campaigns.
Built to help operations and media buying teams decide which vendors to scale, monitor, or pause.

---

## Problem Statement

Media buyers running programmatic campaigns have limited visibility into whether the traffic they are paying for is genuine. Standard metrics like impressions and clicks are easily inflated. Without downstream conversion data — which is often delayed or unavailable — teams rely on gut feel or crude CTR checks.

This tool evaluates vendor traffic using behavioral proxy signals and flags patterns consistent with low-quality or fraudulent traffic, giving buyers an objective, explainable basis for budget decisions.

---

## POC Objective

Demonstrate a complete, working evaluation pipeline that:
- ingests vendor-level traffic data
- scores each vendor across multiple engagement signals
- detects suspicious traffic patterns using rule-based logic
- produces a clear SCALE / MONITOR / PAUSE recommendation with reasoning
- presents everything in a simple, analyst-friendly dashboard

---

## Architecture

```
CSV input (vendor traffic data)
        │
        ▼
   Ingestion & Validation      src/ingestion.py
   Derive CTR, CVR
        │
        ▼
   Quality Scoring             src/scorer.py
   CTR · CVR · Bounce · Session
        │
        ▼
   Fraud Flag Detection        src/scorer.py
   IMPRESSION_SPIKE · ZERO_CVR · HIGH_CTR
        │
        ▼
   Recommendation Engine       src/recommender.py
   SCALE / MONITOR / PAUSE + reason
        │
        ▼
   Streamlit Dashboard         main.py
```

All processing is in-memory. No database. No backend API. Runs entirely locally.

---

## Project Structure

```
├── main.py                   # Streamlit dashboard
├── config.yaml               # Scoring thresholds and flag rules
├── requirements.txt
├── .gitignore
├── data/
│   └── sample_traffic.csv    # Sample vendor traffic dataset
├── src/
│   ├── ingestion.py          # Data loading and validation
│   ├── scorer.py             # Quality scoring and fraud flag detection
│   └── recommender.py        # Recommendation engine
└── docs/
    ├── approach.md
    ├── architecture.md
    ├── assumptions.md
    └── future_improvements.md
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

The app loads the sample dataset by default. To use your own data, upload a CSV via the sidebar.

**Required CSV columns:**

| Column | Description |
|---|---|
| `vendor_id` | Unique vendor identifier |
| `vendor_name` | Display name |
| `impressions` | Total impressions served |
| `clicks` | Total clicks recorded |
| `conversions` | Downstream conversions (0 if unavailable) |
| `bounce_rate` | Share of sessions with no engagement (0–1) |
| `avg_session_sec` | Average session duration in seconds |
| `impressions_prev_avg` | Historical baseline impression volume (for spike detection) |

---

## Scoring Logic

The quality score is a 0–100 composite of four signals, weighted equally.

| Signal | Measures | Scoring method |
|---|---|---|
| **CTR Score** | Click-through rate validity | 100 within healthy range (0.01%–10%). Penalized outside. |
| **CVR Score** | Conversion efficiency | Normalized against the best vendor in the dataset. |
| **Bounce Score** | Session intent | Penalized linearly as bounce rate approaches the 85% ceiling. |
| **Session Score** | Dwell time / engagement depth | Normalized against a 120-second target. |

All thresholds are configurable in `config.yaml`.

---

## Fraud Flags

Fraud flags are independent of the quality score. Any active flag triggers a PAUSE recommendation.

| Flag | Condition | Interpretation |
|---|---|---|
| `IMPRESSION_SPIKE` | Impressions > 3× historical average | Sudden volume burst — inconsistent with organic traffic |
| `ZERO_CVR` | 500+ clicks, 0 conversions | High engagement volume with no downstream value |
| `HIGH_CTR` | CTR > 15% | Abnormal click rate for display — likely inflated |

---

## Recommendation Logic

| Action | Condition |
|---|---|
| **SCALE** | Score ≥ 70 and no active flags |
| **MONITOR** | Score 40–69 and no active flags |
| **PAUSE** | Score < 40, or any active flag |

Each recommendation includes a plain-language reason explaining the decision.

---

## Dashboard

The dashboard has six sections:

1. **Campaign Health Overview** — top-level KPIs: avg score, vendors to pause, vendors to scale
2. **Vendor Quality Ranking** — full table sorted by score with recommendation and reasoning
3. **Quality Score by Vendor** — horizontal bar chart, color-coded by recommendation
4. **Suspicious Traffic Analysis** — flagged vendors with flag definitions
5. **Vendor Drill-down** — per-vendor signal breakdown and recommendation context
6. **Scoring Methodology** — inline explanation of how the score is computed

---

## Assumptions

See [`docs/assumptions.md`](docs/assumptions.md) for the full list.

Key assumptions:
- Data is vendor-aggregated, not session-level
- Conversion data may be zero for some vendors — handled via ZERO_CVR flag
- Historical impression baseline (`impressions_prev_avg`) is provided externally
- All signals are treated as equally important (equal weighting)

---

## Limitations

- Uses synthetic data, not real ad traffic logs
- Rule-based fraud detection only — no statistical anomaly modeling
- Aggregate-level analysis — cannot identify individual bot sessions
- No time-series analysis — scores reflect a single reporting period
- No conversion attribution — CVR uses raw counts, not attributed conversions

---

## Future Improvements

See [`docs/future_improvements.md`](docs/future_improvements.md).
