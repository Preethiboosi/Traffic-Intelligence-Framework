"""
experiment_engine.py — Lightweight experiment engine for vendor traffic A/B testing.

Supports:
    - Loading experiment definitions from CSV
    - Creating in-memory experiment configs
    - Assigning traffic rows to control / variant groups
    - Summarizing behavioral outcomes per variant
    - Uplift calculation and plain-English recommendation

This is a POC-level, in-memory engine. No backend service or database required.
Results are directional — no formal statistical significance testing is implemented.
"""

import pandas as pd
import numpy as np


BEHAVIORAL_METRICS = [
    "ctr",
    "bounce_rate",
    "avg_session_sec",
    "avg_scroll_depth",
    "repeat_visit_rate",
]

# Metrics where lower values are better (used for recommendation logic)
LOWER_IS_BETTER = {"bounce_rate"}


def load_experiments(path: str) -> pd.DataFrame:
    """Load experiment definitions from CSV."""
    df = pd.read_csv(path, parse_dates=["start_date", "end_date"])
    return df


def create_experiment(
    experiment_id: str,
    experiment_name: str,
    vendor_ids: list,
    start_date: str,
    end_date: str,
    primary_metric: str,
    control_allocation: float = 0.5,
    status: str = "active",
) -> dict:
    """
    Define a new experiment configuration.

    Args:
        experiment_id:       Unique identifier (e.g., 'EXP001')
        experiment_name:     Human-readable name
        vendor_ids:          List of vendor IDs participating in the experiment
        start_date:          ISO date string or datetime
        end_date:            ISO date string or datetime
        primary_metric:      Metric to optimize (must be in BEHAVIORAL_METRICS)
        control_allocation:  Fraction of traffic assigned to control (default 0.5)
        status:              'active', 'paused', or 'completed'

    Returns:
        Experiment configuration dict.
    """
    assert 0 < control_allocation < 1, "control_allocation must be between 0 and 1"
    assert primary_metric in BEHAVIORAL_METRICS, (
        f"primary_metric must be one of: {BEHAVIORAL_METRICS}"
    )
    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment_name,
        "vendor_ids": vendor_ids,
        "start_date": start_date,
        "end_date": end_date,
        "primary_metric": primary_metric,
        "control_allocation": control_allocation,
        "variant_allocation": round(1.0 - control_allocation, 2),
        "status": status,
    }


def assign_variant(
    traffic_df: pd.DataFrame, experiment: dict, seed: int = 42
) -> pd.DataFrame:
    """
    Filter traffic to experiment scope and randomly assign rows to control/variant.

    Args:
        traffic_df:  Fully-scored vendor daily DataFrame
        experiment:  Experiment config dict (from create_experiment or CSV row)
        seed:        Random seed for reproducibility

    Returns:
        Filtered DataFrame with 'variant' and 'experiment_id' columns added.
    """
    rng = np.random.default_rng(seed)

    vendor_ids = experiment.get("vendor_ids") or [experiment.get("vendor_id")]
    if isinstance(vendor_ids, str):
        vendor_ids = [v.strip() for v in vendor_ids.split("|")]

    start = pd.to_datetime(experiment["start_date"])
    end = pd.to_datetime(experiment["end_date"])

    mask = (
        traffic_df["vendor_id"].isin(vendor_ids)
        & (traffic_df["date"] >= start)
        & (traffic_df["date"] <= end)
    )
    filtered = traffic_df[mask].copy()

    if filtered.empty:
        return filtered

    control_alloc = float(experiment["control_allocation"])
    filtered["variant"] = rng.choice(
        ["control", "variant"],
        size=len(filtered),
        p=[control_alloc, 1.0 - control_alloc],
    )
    filtered["experiment_id"] = experiment["experiment_id"]

    return filtered


def run_experiment_simulation(
    traffic_df: pd.DataFrame, experiment: dict, seed: int = 42
) -> pd.DataFrame:
    """
    Simulate an experiment by assigning variants to matching traffic rows.

    Returns the assigned DataFrame (one row per vendor-day with variant label).
    """
    return assign_variant(traffic_df, experiment, seed=seed)


def summarize_experiment_results(
    assigned_df: pd.DataFrame, primary_metric: str
) -> pd.DataFrame:
    """
    Compare control vs variant behavioral metrics and compute uplift.

    Args:
        assigned_df:     Output of run_experiment_simulation()
        primary_metric:  The metric this experiment is optimizing

    Returns:
        Summary DataFrame with one row per metric.
    """
    if assigned_df.empty:
        return pd.DataFrame()

    metrics = [m for m in BEHAVIORAL_METRICS if m in assigned_df.columns]

    rows = []
    for metric in metrics:
        control_vals = assigned_df[assigned_df["variant"] == "control"][metric].dropna()
        variant_vals = assigned_df[assigned_df["variant"] == "variant"][metric].dropna()

        ctrl_mean = float(control_vals.mean()) if len(control_vals) > 0 else 0.0
        var_mean = float(variant_vals.mean()) if len(variant_vals) > 0 else 0.0

        uplift = (
            ((var_mean - ctrl_mean) / ctrl_mean * 100) if ctrl_mean != 0 else 0.0
        )

        rows.append({
            "metric":              metric,
            "control_mean":        round(ctrl_mean, 4),
            "variant_mean":        round(var_mean, 4),
            "uplift_pct":          round(uplift, 2),
            "sample_size_control": int(len(control_vals)),
            "sample_size_variant": int(len(variant_vals)),
            "is_primary":          metric == primary_metric,
        })

    return pd.DataFrame(rows)


def get_experiment_recommendation(
    summary_df: pd.DataFrame, primary_metric: str
) -> str:
    """
    Generate a plain-English recommendation based on experiment primary metric uplift.

    Note: Results are directional only — no formal significance testing.
    """
    if summary_df.empty:
        return "Insufficient data to draw conclusions from this experiment."

    primary = summary_df[summary_df["metric"] == primary_metric]
    if primary.empty:
        return f"Primary metric '{primary_metric}' not found in results."

    uplift = float(primary.iloc[0]["uplift_pct"])
    ctrl_mean = float(primary.iloc[0]["control_mean"])
    var_mean = float(primary.iloc[0]["variant_mean"])
    n_ctrl = int(primary.iloc[0]["sample_size_control"])
    n_var = int(primary.iloc[0]["sample_size_variant"])

    low_sample = n_ctrl < 10 or n_var < 10
    sample_note = (
        f" (Note: small sample sizes — control n={n_ctrl}, variant n={n_var}.)"
        if low_sample else f" (n={n_ctrl} control / {n_var} variant)"
    )

    is_lower_better = primary_metric in LOWER_IS_BETTER

    # For bounce_rate: lower variant mean = improvement = negative uplift
    if is_lower_better:
        if uplift < -5:
            return (
                f"Variant reduced {primary_metric} from {ctrl_mean:.3f} to {var_mean:.3f} "
                f"({abs(uplift):.1f}% improvement). Consider scaling variant traffic.{sample_note}"
            )
        if uplift > 5:
            return (
                f"Variant worsened {primary_metric} by {uplift:.1f}% ({ctrl_mean:.3f} → {var_mean:.3f}). "
                f"Do not scale variant — revert to control.{sample_note}"
            )
        return (
            f"No meaningful difference in {primary_metric} ({uplift:.1f}% change). "
            f"Extend experiment window or increase traffic volume.{sample_note}"
        )

    # For positive metrics: higher variant mean = improvement = positive uplift
    if uplift > 5:
        return (
            f"Variant improved {primary_metric} by {uplift:.1f}% "
            f"({ctrl_mean:.3f} → {var_mean:.3f}). Recommend scaling variant.{sample_note}"
        )
    if uplift < -5:
        return (
            f"Variant underperformed control on {primary_metric} by {abs(uplift):.1f}%. "
            f"Continue with control, investigate variant setup.{sample_note}"
        )
    return (
        f"Results are inconclusive — {primary_metric} difference is {uplift:.1f}%. "
        f"Extend experiment window or increase traffic volume.{sample_note}"
    )
