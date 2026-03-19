"""
recommender.py — Map quality score and anomaly flags to SCALE / MONITOR / PAUSE.

Decision logic:
    PAUSE   — severe anomaly flag active, OR score below monitor threshold
    SCALE   — score >= scale threshold AND no active flags
    MONITOR — everything else (acceptable score, warning flags only)
"""

import pandas as pd


def _recommend(
    score: float, flag_severity: str, scale_min: float, monitor_min: float
) -> str:
    if flag_severity == "severe":
        return "PAUSE"
    if score >= scale_min and flag_severity == "none":
        return "SCALE"
    if score >= monitor_min:
        return "MONITOR"
    return "PAUSE"


def _reason(
    recommendation: str, score: float, flags: list, flag_reason: str
) -> str:
    if recommendation == "PAUSE":
        if flags:
            return (
                f"Severe anomalies detected: {', '.join(flags)}. {flag_reason}"
            )
        return (
            f"Quality score {score:.0f}/100 is below the minimum threshold "
            f"for continued spend. Review engagement signals before resuming."
        )
    if recommendation == "SCALE":
        return (
            f"Score {score:.0f}/100 with no anomaly flags — traffic quality is "
            f"strong and consistent. Safe to increase budget allocation."
        )
    # MONITOR
    if flags:
        return (
            f"Score {score:.0f}/100 is acceptable, but warning flags are active: "
            f"{', '.join(flags)}. Monitor closely before expanding spend."
        )
    return (
        f"Score {score:.0f}/100 is acceptable but not exceptional. "
        f"Continue monitoring for trend changes before scaling."
    )


def apply_recommendations(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Apply SCALE / MONITOR / PAUSE recommendation to each row."""
    df = df.copy()
    rules = config["recommendation_rules"]
    scale_min = rules["scale_min_score"]
    monitor_min = rules["monitor_min_score"]

    df["recommendation"] = df.apply(
        lambda r: _recommend(
            r["quality_score"], r["flag_severity"], scale_min, monitor_min
        ),
        axis=1,
    )
    df["reason"] = df.apply(
        lambda r: _reason(
            r["recommendation"], r["quality_score"], r["flags"], r["flag_reason"]
        ),
        axis=1,
    )

    return df
