# Experiment Engine

## Purpose

The experiment engine provides a lightweight way to test vendor traffic configurations against each other using behavioral metrics. It answers the question: **"Is this vendor's traffic better with setup A or setup B?"**

In a media buying context, experiments might compare:
- Two different creative formats served by the same vendor
- Two bid strategies (e.g., CPM floor A vs floor B)
- Two landing page designs for the same vendor's traffic
- A new vendor's targeting configuration vs the current baseline

---

## Concepts

### Experiment
An experiment defines a test to run. Key fields:

| Field | Description |
|---|---|
| `experiment_id` | Unique identifier (e.g., `EXP001`) |
| `experiment_name` | Human-readable description of what is being tested |
| `vendor_id` | The vendor whose traffic participates in the experiment |
| `start_date / end_date` | Date range for traffic eligibility |
| `primary_metric` | The main behavioral signal being optimized |
| `control_allocation` | Fraction of traffic assigned to control (e.g., `0.5` = 50%) |
| `variant_allocation` | Remaining fraction assigned to variant |
| `status` | `active`, `paused`, or `completed` |

### Variant Assignment
Traffic rows matching the experiment's vendor and date range are randomly assigned to `control` or `variant` using the configured allocation ratio. Assignment uses a seeded random number generator for reproducibility.

### Primary Metric
The metric the experiment is designed to optimize. Must be one of:
- `ctr` — click-through rate
- `bounce_rate` — session bounce rate (lower is better)
- `avg_session_sec` — average session duration
- `avg_scroll_depth` — average scroll depth
- `repeat_visit_rate` — returning visitor rate

### Uplift
Uplift measures the variant's performance relative to control:

```
uplift_pct = (variant_mean - control_mean) / control_mean × 100
```

For `bounce_rate`, a **negative** uplift means the variant performs better (lower bounce).

---

## Implementation

### `create_experiment()`
Defines an in-memory experiment configuration dict. For the POC, experiments can also be loaded from `data/sample_experiments.csv`.

### `assign_variant()`
Filters the traffic DataFrame to the experiment's vendor and date range, then randomly assigns each row to `control` or `variant`.

### `run_experiment_simulation()`
Wraps `assign_variant()`. Returns the filtered, labeled DataFrame for further analysis.

### `summarize_experiment_results()`
Aggregates mean values for all behavioral metrics by variant. Returns a comparison DataFrame with:
- `metric` — metric name
- `control_mean` — average for control group
- `variant_mean` — average for variant group
- `uplift_pct` — relative change (%)
- `sample_size_control / variant` — number of rows per group
- `is_primary` — whether this is the primary metric

### `get_experiment_recommendation()`
Generates a plain-English recommendation based on the primary metric uplift:
- Uplift > 5% (in the favorable direction) → recommend scaling variant
- Uplift < -5% (in the unfavorable direction) → recommend reverting to control
- Within ±5% → inconclusive, extend window or increase traffic

---

## Limitations

**No formal statistical testing.** The engine computes directional uplift but does not calculate p-values, confidence intervals, or apply multiple-comparison corrections. Results should be treated as directional signals, not confirmed findings.

**Row-level assignment.** Variants are assigned at the vendor-day aggregation level, not at the session or user level. This is a simplification appropriate for the data granularity. Production systems would assign at the session level to prevent contamination.

**Small samples are common.** With daily vendor data and short experiment windows, sample sizes per variant are often small (< 30 rows). Results from small samples are highly variable and should not drive large budget decisions.

**Seed-based reproducibility.** Assignment uses a fixed seed (`seed=42` by default) so the same experiment always produces the same results on the same data. Changing the seed produces a different random split.

---

## Production Path

To move the experiment engine to production:

1. **Real assignment database.** Replace the in-memory simulation with a live assignment table (see `sql/schema.sql` → `experiment_assignments`). Write assignment records when sessions start.

2. **Session-level assignment.** Assign variants at the session or user level using a consistent hash (e.g., `murmurhash(user_id + experiment_id) % 100 < control_pct`). This prevents day-level contamination.

3. **Statistical significance.** Implement a proper significance test (frequentist t-test or Bayesian posterior comparison). Libraries like `scipy.stats` or `pymc` are lightweight options.

4. **Experiment management UI.** Tools like [GrowthBook](https://www.growthbook.io) or [PostHog](https://posthog.com) provide hosted experiment management with statistical testing, feature flags, and result tracking.

5. **Guardrail metrics.** Add secondary metric guardrails that automatically flag an experiment as harmful if non-primary metrics degrade beyond a threshold (e.g., a CTR experiment that significantly increases bounce rate).

---

## Example: Running a Simulation

```python
from src.experiment_engine import create_experiment, run_experiment_simulation, \
    summarize_experiment_results, get_experiment_recommendation

experiment = create_experiment(
    experiment_id="EXP006",
    experiment_name="SportzMedia Video vs Static Creative",
    vendor_ids=["V001"],
    start_date="2026-02-09",
    end_date="2026-02-23",
    primary_metric="avg_session_sec",
    control_allocation=0.5,
)

assigned = run_experiment_simulation(scored_df, experiment)
summary = summarize_experiment_results(assigned, "avg_session_sec")
recommendation = get_experiment_recommendation(summary, "avg_session_sec")

print(recommendation)
```
