"""
feature_engineering.py — Rolling averages, trend features, and engagement index.

All features are derived from behavioral signals only (no conversion data).
"""

import pandas as pd
import numpy as np


def add_impression_spike_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """Compute ratio of current impressions to historical baseline."""
    df = df.copy()
    df["impression_spike_ratio"] = (
        df["impressions"] / df["impressions_prev_avg"].replace(0, float("nan"))
    ).fillna(1.0)
    return df


def add_rolling_features(df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """Add 7-day rolling averages for core behavioral metrics per vendor."""
    metrics = [
        "ctr",
        "bounce_rate",
        "avg_session_sec",
        "avg_scroll_depth",
        "repeat_visit_rate",
    ]

    result_parts = []
    for _vendor_id, group in df.groupby("vendor_id", sort=False):
        group = group.copy().sort_values("date")
        for metric in metrics:
            group[f"{metric}_roll7"] = (
                group[metric].rolling(window=window, min_periods=1).mean()
            )
        result_parts.append(group)

    return (
        pd.concat(result_parts)
        .sort_values(["vendor_id", "date"])
        .reset_index(drop=True)
    )


def add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-vendor engagement index, trend delta, and trend direction.

    Engagement index: weighted composite of dwell, inverse bounce, and scroll.
    Trend delta: week-over-week change in 7-day rolling engagement.
    Trend direction: improving / stable / declining.
    """
    result_parts = []
    for _vendor_id, group in df.groupby("vendor_id", sort=False):
        group = group.copy().sort_values("date")

        # Engagement index: 0–1 composite behavioral signal
        engagement = (
            (group["avg_session_sec"] / 120).clip(0, 1) * 0.40
            + (1 - group["bounce_rate"]).clip(0, 1) * 0.30
            + group["avg_scroll_depth"].clip(0, 1) * 0.30
        )

        roll7 = engagement.rolling(window=7, min_periods=1).mean()
        lag7 = roll7.shift(7)

        trend_delta = (
            (roll7 - lag7) / lag7.replace(0, float("nan"))
        ).fillna(0)

        trend_direction = trend_delta.apply(
            lambda x: "improving" if x > 0.05 else ("declining" if x < -0.05 else "stable")
        )

        group["engagement_index"] = engagement.values
        group["trend_delta"] = trend_delta.values
        group["trend_direction"] = trend_direction.values
        result_parts.append(group)

    return (
        pd.concat(result_parts)
        .sort_values(["vendor_id", "date"])
        .reset_index(drop=True)
    )


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full feature engineering pipeline."""
    df = add_impression_spike_ratio(df)
    df = add_rolling_features(df)
    df = add_trend_features(df)
    return df
