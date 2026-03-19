"""
scorer.py — Behavioral quality scoring for vendor traffic.

Computes six signal scores (each 0–100) and a weighted composite quality_score.
No conversion data is required or used.

Scoring signals:
    ctr_score         — CTR within plausible range; penalizes extremes
    bounce_score      — Lower bounce rate = higher score
    dwell_score       — Longer average session = higher score
    scroll_score      — Deeper scroll engagement = higher score
    repeat_visit_score — Healthy repeat rate; penalizes suspiciously high values
    trend_health_score — Improving or stable engagement trend vs recent baseline
"""

import pandas as pd


# ── Individual signal scorers ──────────────────────────────────────────────────

def _ctr_score(ctr: float, min_healthy: float, max_healthy: float) -> float:
    """Score CTR within the healthy window; penalize values outside it."""
    if ctr < min_healthy:
        return max(0.0, (ctr / min_healthy) * 60)
    if ctr <= max_healthy:
        return 100.0
    # Over-ceiling penalty: sharper decline for implausible CTR
    return max(0.0, 100.0 - ((ctr - max_healthy) / max_healthy) * 200)


def _bounce_score(bounce_rate: float, max_healthy: float) -> float:
    """Penalize high bounce rates linearly up to the ceiling."""
    return max(0.0, (1.0 - bounce_rate / max_healthy) * 100)


def _dwell_score(avg_session_sec: float, target_sec: float) -> float:
    """Reward dwell time; capped at 100 once target is reached."""
    return min(100.0, (avg_session_sec / target_sec) * 100)


def _scroll_score(avg_scroll_depth: float, min_healthy: float) -> float:
    """Reward scroll depth; capped at 100 once minimum healthy threshold is met."""
    return min(100.0, (avg_scroll_depth / min_healthy) * 100)


def _repeat_visit_score(
    repeat_visit_rate: float, min_healthy: float, max_suspicious: float
) -> float:
    """
    Some repeat visits signal genuine interest; too many suggest bot or recycled traffic.
    Below min → partial credit. Within range → full score. Above max → declining penalty.
    """
    if repeat_visit_rate < min_healthy:
        return max(0.0, (repeat_visit_rate / min_healthy) * 80)
    if repeat_visit_rate <= max_suspicious:
        return 100.0
    # Over-ceiling penalty
    return max(
        0.0,
        100.0 - ((repeat_visit_rate - max_suspicious) / (1.0 - max_suspicious)) * 100,
    )


def _trend_health_score(trend_delta: float) -> float:
    """
    Convert engagement trend delta to 0–100.
    Flat/improving baseline → high score. Sharp decline → low score.
    """
    if trend_delta >= 0:
        return min(100.0, 70.0 + trend_delta * 100)
    return max(0.0, 70.0 + trend_delta * 200)


# ── Composite scorer ───────────────────────────────────────────────────────────

def compute_scores(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Compute individual signal scores and the weighted composite quality_score.

    Args:
        df:     DataFrame produced by feature_engineering.engineer_features()
        config: Loaded config.yaml dict

    Returns:
        DataFrame with added score columns and quality_score (0–100).
    """
    df = df.copy()
    weights = config["scoring"]["weights"]
    ctr_cfg = config["scoring"]["ctr"]
    bounce_cfg = config["scoring"]["bounce"]
    dwell_cfg = config["scoring"]["dwell"]
    scroll_cfg = config["scoring"]["scroll"]
    rv_cfg = config["scoring"]["repeat_visit"]

    df["ctr_score"] = df["ctr"].apply(
        lambda x: _ctr_score(x, ctr_cfg["min_healthy"], ctr_cfg["max_healthy"])
    )
    df["bounce_score"] = df["bounce_rate"].apply(
        lambda x: _bounce_score(x, bounce_cfg["max_healthy"])
    )
    df["dwell_score"] = df["avg_session_sec"].apply(
        lambda x: _dwell_score(x, dwell_cfg["target_sec"])
    )
    df["scroll_score"] = df["avg_scroll_depth"].apply(
        lambda x: _scroll_score(x, scroll_cfg["min_healthy"])
    )
    df["repeat_visit_score"] = df["repeat_visit_rate"].apply(
        lambda x: _repeat_visit_score(x, rv_cfg["min_healthy"], rv_cfg["max_suspicious"])
    )

    trend_col = df["trend_delta"] if "trend_delta" in df.columns else pd.Series(0.0, index=df.index)
    df["trend_health_score"] = trend_col.apply(_trend_health_score)

    df["quality_score"] = (
        df["ctr_score"]          * weights["ctr"]
        + df["bounce_score"]     * weights["bounce"]
        + df["dwell_score"]      * weights["dwell"]
        + df["scroll_score"]     * weights["scroll"]
        + df["repeat_visit_score"] * weights["repeat_visit"]
        + df["trend_health_score"] * weights["trend_health"]
    ).clip(0, 100).round(1)

    return df
