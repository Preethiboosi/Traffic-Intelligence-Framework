# Assumptions

## Data

- **Vendor-level aggregation.** The input data represents aggregated metrics per vendor per reporting period, not individual session logs. This is the most common format available from DSPs and reporting APIs.
- **Conversions may be zero.** Not all vendors or placements generate measurable downstream conversions, especially in upper-funnel campaigns. The system handles this explicitly via the `ZERO_CVR` flag rather than penalizing all vendors equally.
- **Historical baseline is provided.** The `impressions_prev_avg` field is assumed to come from a prior reporting period or rolling average computed upstream. In a production system, this would be derived from a time-series data store.
- **CTR and CVR are derived fields.** They are computed from raw impression, click, and conversion counts during ingestion. Source data is trusted as-is.

## Scoring

- **Equal signal weighting.** All four quality signals (CTR, CVR, bounce rate, session time) contribute equally to the composite score. In a real system, weights should be calibrated against downstream business outcomes.
- **CVR is relative, not absolute.** CVR score is normalized against the best-performing vendor in the current dataset. This makes it robust to campaigns with inherently low conversion rates.
- **Session time target is approximate.** The 120-second target for a "full-quality" session is a reasonable heuristic for display advertising. It should be adjusted based on campaign type.

## Fraud Detection

- **Flags are independent of the quality score.** A vendor can score well on engagement signals but still be flagged for suspicious volume patterns. The recommendation engine treats any active flag as grounds for PAUSE.
- **Thresholds are intentionally conservative.** The defaults in `config.yaml` are designed to minimize false negatives (missing real fraud) rather than false positives.
- **No IP-level or session-level analysis.** This POC operates on aggregated data. Identifying individual bot IPs or session fingerprints requires raw log access.

## General

- **Single reporting period.** The system evaluates one snapshot of data at a time. Trend analysis across periods is not included at POC stage.
- **No external data enrichment.** Domain reputation, publisher categorization, and third-party IVT scores are not incorporated.
