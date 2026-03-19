"""
anomaly.py — Rule-based anomaly flag detection for vendor traffic.

Flags are computed independently from the quality score.
Severity drives recommendation: severe → PAUSE, warning → MONITOR.

Available flags:
    IMPRESSION_SPIKE       — volume spike vs historical baseline (severe)
    HIGH_CTR_ANOMALY       — implausibly high click-through rate (severe)
    HIGH_BOUNCE_LOW_DWELL  — exits immediately after landing (severe)
    ENGAGEMENT_COLLAPSE    — sharp deterioration vs recent baseline (severe)
    LOW_SCROLL_TRAFFIC     — significant clicks but negligible scroll (warning)
    REPEAT_PATTERN_ANOMALY — suspiciously uniform or extreme repeat rate (warning)
"""

import pandas as pd


def detect_anomalies(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Detect anomaly flags for each vendor-day row.

    Adds columns:
        flags          — list of active flag names
        flag_severity  — 'severe', 'warning', or 'none'
        flag_reason    — plain-English explanation of all active flags
    """
    rules = config["anomaly_rules"]
    severe_flags = set(rules.get("severe_flags", []))

    df = df.copy()
    flag_lists = []
    flag_reasons = []

    for _, row in df.iterrows():
        flags = []
        reasons = []

        # ── IMPRESSION_SPIKE ───────────────────────────────────────────────────
        spike_ratio = row.get("impression_spike_ratio", 1.0)
        if spike_ratio > rules["impression_spike_multiple"]:
            flags.append("IMPRESSION_SPIKE")
            reasons.append(
                f"Impressions are {spike_ratio:.1f}× the historical baseline "
                f"({int(row['impressions']):,} vs avg {int(row['impressions_prev_avg']):,})."
            )

        # ── HIGH_CTR_ANOMALY ───────────────────────────────────────────────────
        if row["ctr"] > rules["high_ctr_threshold"]:
            flags.append("HIGH_CTR_ANOMALY")
            reasons.append(
                f"CTR of {row['ctr']:.1%} exceeds the plausible ceiling of "
                f"{rules['high_ctr_threshold']:.0%}, suggesting click inflation."
            )

        # ── HIGH_BOUNCE_LOW_DWELL ──────────────────────────────────────────────
        if (
            row["bounce_rate"] > rules["high_bounce_threshold"]
            and row["avg_session_sec"] < rules["low_dwell_threshold_sec"]
        ):
            flags.append("HIGH_BOUNCE_LOW_DWELL")
            reasons.append(
                f"Bounce rate {row['bounce_rate']:.0%} with avg session only "
                f"{row['avg_session_sec']:.0f}s — traffic is exiting immediately after landing."
            )

        # ── LOW_SCROLL_TRAFFIC ─────────────────────────────────────────────────
        if (
            row["avg_scroll_depth"] < rules["low_scroll_threshold"]
            and row["clicks"] > 100
        ):
            flags.append("LOW_SCROLL_TRAFFIC")
            reasons.append(
                f"Avg scroll depth {row['avg_scroll_depth']:.0%} despite "
                f"{int(row['clicks']):,} clicks — users are not engaging with page content."
            )

        # ── ENGAGEMENT_COLLAPSE ────────────────────────────────────────────────
        trend_delta = row.get("trend_delta", 0.0)
        if trend_delta < -rules.get("engagement_collapse_threshold", 0.30):
            flags.append("ENGAGEMENT_COLLAPSE")
            reasons.append(
                f"Engagement index dropped {abs(trend_delta):.0%} vs recent baseline — "
                f"sharp quality deterioration detected."
            )

        # ── REPEAT_PATTERN_ANOMALY ─────────────────────────────────────────────
        if row["repeat_visit_rate"] > rules.get("repeat_pattern_max", 0.95):
            flags.append("REPEAT_PATTERN_ANOMALY")
            reasons.append(
                f"Repeat visit rate {row['repeat_visit_rate']:.0%} is unrealistically high — "
                f"possible bot or recycled traffic pattern."
            )

        flag_lists.append(flags)
        flag_reasons.append(
            " ".join(reasons) if reasons else "No anomalies detected."
        )

    df["flags"] = flag_lists
    df["flag_severity"] = df["flags"].apply(
        lambda fs: (
            "severe" if any(f in severe_flags for f in fs)
            else ("warning" if fs else "none")
        )
    )
    df["flag_reason"] = flag_reasons

    return df
