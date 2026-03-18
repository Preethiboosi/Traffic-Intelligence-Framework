# Architecture

## Overview

The system is a single-pipeline local application. Data flows linearly from input to output with no external dependencies, no database, and no background processes.

```
┌─────────────────────────────────────────────────┐
│                   main.py                        │
│              Streamlit Dashboard                 │
└───────────────────┬─────────────────────────────┘
                    │ calls
        ┌───────────▼────────────┐
        │    src/ingestion.py    │
        │  Load CSV              │
        │  Validate columns      │
        │  Derive CTR, CVR       │
        └───────────┬────────────┘
                    │
        ┌───────────▼────────────┐
        │    src/scorer.py       │
        │  CTR score             │
        │  CVR score             │
        │  Bounce score          │
        │  Session score         │
        │  Composite score       │
        │  Fraud flag detection  │
        └───────────┬────────────┘
                    │
        ┌───────────▼────────────┐
        │   src/recommender.py   │
        │  SCALE / MONITOR /     │
        │  PAUSE + reason text   │
        └───────────┬────────────┘
                    │
        ┌───────────▼────────────┐
        │    main.py renders     │
        │  KPIs, tables, charts, │
        │  drill-down, flags     │
        └────────────────────────┘
```

## Key design decisions

**No database.** Processing is done entirely in-memory using pandas DataFrames. For a POC evaluating tens to hundreds of vendors, this is more than sufficient and eliminates setup friction.

**No backend API.** Streamlit calls the processing functions directly. Adding a REST API layer would add complexity with no benefit at this scope.

**Configuration over code.** Scoring thresholds and flag rules live in `config.yaml`. This means a non-technical analyst can adjust sensitivity without touching the codebase.

**Separation of concerns.** Each module has a single responsibility:
- `ingestion.py` — loading and validating input
- `scorer.py` — computing signals and detecting anomalies
- `recommender.py` — translating scores into decisions
- `main.py` — presentation only

## Scalability path

To move this from POC to production:

1. Replace CSV input with a SQL query or warehouse connector
2. Schedule the pipeline (Airflow, cron, or a simple Python scheduler)
3. Persist output to a database or BI tool rather than rendering in Streamlit
4. Add time-series support to detect trends across reporting periods
5. Replace rule-based fraud detection with a statistical anomaly model trained on historical data
