def _recommend(row, pause_below, scale_above):
    has_flags = row["flags"] != "—"
    score = row["quality_score"]
    if score < pause_below or has_flags:
        return "PAUSE"
    elif score >= scale_above:
        return "SCALE"
    else:
        return "MONITOR"


def _reason(row):
    rec   = row["recommendation"]
    flags = row["flags"]

    if rec == "PAUSE":
        if "IMPRESSION_SPIKE" in flags and "ZERO_CVR" in flags:
            return "Volume spike with zero conversions — likely invalid traffic"
        if "HIGH_CTR" in flags and "ZERO_CVR" in flags:
            return "Abnormal CTR with zero conversions — click fraud pattern"
        if "IMPRESSION_SPIKE" in flags:
            return "Abnormal impression spike relative to historical average"
        if "ZERO_CVR" in flags:
            return "High click volume yielding zero conversions — no downstream value"
        if "HIGH_CTR" in flags:
            return "CTR exceeds healthy range — potential bot or incentivized traffic"
        return "Quality score below acceptable threshold — poor overall engagement"

    if rec == "MONITOR":
        return "Acceptable engagement but not consistently strong — watch for trend"

    return "Strong engagement across all signals — safe to increase budget allocation"


def apply_recommendations(df, cfg):
    r = cfg["recommendations"]
    result = df.copy()
    result["recommendation"] = result.apply(
        lambda row: _recommend(row, r["pause_below_score"], r["scale_above_score"]),
        axis=1
    )
    result["reason"] = result.apply(_reason, axis=1)
    return result
