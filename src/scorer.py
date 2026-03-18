"""
Scoring logic — each signal produces a sub-score from 0 to 100.
The composite quality score is the unweighted average of all four signals.

Signals:
  ctr_score     — penalizes CTR that is too low (dead traffic) or too high (bot-inflated)
  cvr_score     — rewards vendors that drive downstream conversions relative to the dataset
  bounce_score  — penalizes high bounce rates, which indicate low-intent sessions
  session_score — rewards longer dwell time as a proxy for genuine user engagement
"""


def _ctr_score(ctr, ctr_min, ctr_max):
    if ctr_min <= ctr <= ctr_max:
        return 100.0
    elif ctr < ctr_min:
        return max(0.0, (ctr / ctr_min) * 100)
    else:
        return max(0.0, 100 - ((ctr - ctr_max) / ctr_max) * 100)


def _cvr_score(cvr, max_cvr):
    if max_cvr == 0:
        return 50.0
    return min(100.0, (cvr / max_cvr) * 100)


def _bounce_score(bounce_rate, bounce_max):
    return max(0.0, min(100.0, (1 - bounce_rate / bounce_max) * 100))


def _session_score(avg_session_sec, session_max):
    return min(100.0, (avg_session_sec / session_max) * 100)


def _detect_flags(row, cfg):
    f = cfg["fraud_flags"]
    flags = []
    if row["impressions"] > f["impression_spike_multiplier"] * row["impressions_prev_avg"]:
        flags.append("IMPRESSION_SPIKE")
    if row["clicks"] >= f["zero_cvr_click_threshold"] and row["conversions"] == 0:
        flags.append("ZERO_CVR")
    if row["ctr"] > f["high_ctr_threshold"]:
        flags.append("HIGH_CTR")
    return ", ".join(flags) if flags else "—"


def compute_scores(df, cfg):
    s = cfg["scoring"]
    ctr_min     = s["ctr"]["min_healthy"]
    ctr_max     = s["ctr"]["max_healthy"]
    bounce_max  = s["bounce_rate_max"]
    session_max = s["session_time_max"]
    max_cvr     = df["cvr"].max()

    result = df.copy()
    result["ctr_score"]     = result["ctr"].apply(lambda v: _ctr_score(v, ctr_min, ctr_max)).round(1)
    result["cvr_score"]     = result["cvr"].apply(lambda v: _cvr_score(v, max_cvr)).round(1)
    result["bounce_score"]  = result["bounce_rate"].apply(lambda v: _bounce_score(v, bounce_max)).round(1)
    result["session_score"] = result["avg_session_sec"].apply(lambda v: _session_score(v, session_max)).round(1)

    result["quality_score"] = (
        result[["ctr_score", "cvr_score", "bounce_score", "session_score"]].mean(axis=1)
    ).round(1)

    result["flags"] = result.apply(lambda row: _detect_flags(row, cfg), axis=1)
    return result
