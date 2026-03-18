import pandas as pd
import yaml

REQUIRED_COLUMNS = [
    "vendor_id", "vendor_name", "impressions", "clicks",
    "conversions", "bounce_rate", "avg_session_sec", "impressions_prev_avg"
]


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def load_data(source):
    df = pd.read_csv(source)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["impressions"] = df["impressions"].clip(lower=0)
    df["clicks"]      = df["clicks"].clip(lower=0)
    df["conversions"] = df["conversions"].clip(lower=0)

    df["ctr"] = df["clicks"] / df["impressions"].replace(0, float("nan"))
    df["cvr"] = df["conversions"] / df["clicks"].replace(0, float("nan"))
    df["ctr"] = df["ctr"].fillna(0)
    df["cvr"] = df["cvr"].fillna(0)

    return df
