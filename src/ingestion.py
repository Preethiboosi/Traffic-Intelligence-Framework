"""
ingestion.py — Load, validate, and prepare vendor daily traffic data.

Required CSV columns:
    date, vendor_id, vendor_name, impressions, clicks, bounce_rate,
    avg_session_sec, avg_scroll_depth, repeat_visit_rate,
    landing_page_views, impressions_prev_avg

No conversion or CVR data is required or used.
"""

import pandas as pd
import yaml

REQUIRED_COLUMNS = [
    "date",
    "vendor_id",
    "vendor_name",
    "impressions",
    "clicks",
    "bounce_rate",
    "avg_session_sec",
    "avg_scroll_depth",
    "repeat_visit_rate",
    "landing_page_views",
    "impressions_prev_avg",
]

NUMERIC_COLUMNS = [
    "impressions",
    "clicks",
    "bounce_rate",
    "avg_session_sec",
    "avg_scroll_depth",
    "repeat_visit_rate",
    "landing_page_views",
    "impressions_prev_avg",
]


def load_config(path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_data(source) -> pd.DataFrame:
    """
    Load and validate vendor daily traffic CSV.

    Args:
        source: file path (str) or file-like object (e.g., Streamlit UploadedFile)

    Returns:
        Clean, sorted DataFrame ready for feature engineering.
    """
    df = pd.read_csv(source)

    # Validate required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Parse dates
    df["date"] = pd.to_datetime(df["date"])

    # Cast numerics, coerce errors, clip negatives
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(lower=0)

    # If impressions_prev_avg is missing/zero, fall back to current impressions
    df["impressions_prev_avg"] = df["impressions_prev_avg"].where(
        df["impressions_prev_avg"] > 0, df["impressions"]
    )

    # Derive CTR (no CVR — conversion data not required)
    df["ctr"] = (
        df["clicks"] / df["impressions"].replace(0, float("nan"))
    ).fillna(0)

    # Sort for time-series operations downstream
    df = df.sort_values(["vendor_id", "date"]).reset_index(drop=True)

    return df
