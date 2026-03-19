"""
analytics.py — KPI summaries, trend tables, and dashboard-ready aggregations.

All functions operate on the fully-scored DataFrame produced by the pipeline.
"""

import pandas as pd


def get_executive_summary(df: pd.DataFrame) -> dict:
    """Top-level KPIs from the latest scored data per vendor."""
    latest = df.sort_values("date").groupby("vendor_id").last().reset_index()
    return {
        "total_vendors": int(latest["vendor_id"].nunique()),
        "avg_quality_score": round(float(latest["quality_score"].mean()), 1),
        "vendors_to_scale": int((latest["recommendation"] == "SCALE").sum()),
        "vendors_to_monitor": int((latest["recommendation"] == "MONITOR").sum()),
        "vendors_to_pause": int((latest["recommendation"] == "PAUSE").sum()),
        "active_anomalies": int((latest["flag_severity"] != "none").sum()),
        "date_range_start": df["date"].min().strftime("%Y-%m-%d"),
        "date_range_end": df["date"].max().strftime("%Y-%m-%d"),
    }


def get_vendor_intelligence_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per vendor: latest score, trend direction, recommendation, anomaly status.
    """
    latest = df.sort_values("date").groupby("vendor_id").last().reset_index()
    table = latest[
        ["vendor_id", "vendor_name", "quality_score", "trend_direction",
         "recommendation", "flags", "reason"]
    ].copy()
    table["flags_display"] = table["flags"].apply(
        lambda fs: ", ".join(fs) if fs else "—"
    )
    return table


def get_trend_data(df: pd.DataFrame) -> pd.DataFrame:
    """Daily scores and engagement metrics for trend charts."""
    cols = [
        "date", "vendor_id", "vendor_name", "quality_score", "engagement_index",
        "ctr", "bounce_rate", "avg_session_sec", "avg_scroll_depth",
        "trend_direction", "flags",
    ]
    return df[[c for c in cols if c in df.columns]].copy()


def get_suspicious_traffic(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent flagged row per vendor, for the suspicious traffic section."""
    flagged = df[df["flag_severity"] != "none"].copy()
    if flagged.empty:
        return flagged
    latest_flagged = (
        flagged.sort_values("date")
        .groupby("vendor_id")
        .last()
        .reset_index()
    )
    return latest_flagged[
        ["vendor_id", "vendor_name", "date", "flags", "flag_severity",
         "flag_reason", "quality_score", "recommendation"]
    ]


def get_vendor_drilldown(df: pd.DataFrame, vendor_id: str) -> pd.DataFrame:
    """All historical rows for a specific vendor, sorted by date."""
    return df[df["vendor_id"] == vendor_id].sort_values("date").reset_index(drop=True)


def get_rising_risk_vendors(df: pd.DataFrame) -> pd.DataFrame:
    """Vendors showing declining trends or newly flagged anomalies."""
    latest = df.sort_values("date").groupby("vendor_id").last().reset_index()
    risk = latest[
        (latest["trend_direction"] == "declining")
        | (latest["flag_severity"] != "none")
    ].copy()
    risk["flags_display"] = risk["flags"].apply(
        lambda fs: ", ".join(fs) if fs else "—"
    )
    return risk[
        ["vendor_id", "vendor_name", "quality_score", "trend_direction",
         "flags_display", "recommendation"]
    ].sort_values("quality_score")
