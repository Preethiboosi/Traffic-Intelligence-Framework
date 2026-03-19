"""
main.py — Traffic Intelligence Framework Dashboard

Run with:  streamlit run main.py

Seven sections:
    1. Executive Overview
    2. Vendor Intelligence Table
    3. Quality Trend Analysis
    4. Suspicious Traffic Analysis
    5. Experiment Engine
    6. Vendor Drilldown
    7. Methodology
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.ingestion import load_config, load_data
from src.feature_engineering import engineer_features
from src.scorer import compute_scores
from src.anomaly import detect_anomalies
from src.recommender import apply_recommendations
from src.analytics import (
    get_executive_summary,
    get_vendor_intelligence_table,
    get_trend_data,
    get_suspicious_traffic,
    get_vendor_drilldown,
    get_rising_risk_vendors,
)
from src.experiment_engine import (
    load_experiments,
    run_experiment_simulation,
    summarize_experiment_results,
    get_experiment_recommendation,
)

# ── Page setup ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Traffic Intelligence Framework",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

REC_COLORS = {
    "PAUSE":   "#EF4444",
    "MONITOR": "#F59E0B",
    "SCALE":   "#10B981",
}

TABLE_STYLES = {
    "PAUSE":   "background-color: #FEE2E2; color: #991B1B",
    "MONITOR": "background-color: #FEF3C7; color: #92400E",
    "SCALE":   "background-color: #D1FAE5; color: #065F46",
}

SEVERITY_COLORS = {
    "severe":  "#EF4444",
    "warning": "#F59E0B",
    "none":    "#10B981",
}

# ── Load config ────────────────────────────────────────────────────────────────

config = load_config()

# ── Sidebar ────────────────────────────────────────────────────────────────────

st.sidebar.title("Traffic Intelligence")
st.sidebar.markdown("*Behavioral analytics for media buyers*")
st.sidebar.divider()

uploaded_file = st.sidebar.file_uploader(
    "Upload vendor daily CSV",
    type="csv",
    help="Leave empty to use built-in sample data.",
)

DEFAULT_DATA = "data/sample_vendor_daily.csv"
DEFAULT_EXPERIMENTS = "data/sample_experiments.csv"


def run_pipeline(source) -> pd.DataFrame:
    df = load_data(source)
    df = engineer_features(df)
    df = compute_scores(df, config)
    df = detect_anomalies(df, config)
    df = apply_recommendations(df, config)
    return df


try:
    if uploaded_file:
        df = run_pipeline(uploaded_file)
        st.sidebar.success(f"Custom data loaded — {len(df):,} rows.")
    else:
        df = run_pipeline(DEFAULT_DATA)
        st.sidebar.info("Using sample data.")
except Exception as exc:
    st.error(f"Pipeline error: {exc}")
    st.stop()

try:
    experiments_df = load_experiments(DEFAULT_EXPERIMENTS)
except Exception:
    experiments_df = pd.DataFrame()

rules = config["anomaly_rules"]
rec_rules = config["recommendation_rules"]

with st.sidebar.expander("Active Thresholds"):
    st.caption(f"Impression spike:  {rules['impression_spike_multiple']}×")
    st.caption(f"High CTR:          {rules['high_ctr_threshold']:.0%}")
    st.caption(f"High bounce:       {rules['high_bounce_threshold']:.0%}")
    st.caption(f"Low dwell:         {rules['low_dwell_threshold_sec']}s")
    st.caption(f"Scale min score:   {rec_rules['scale_min_score']}")
    st.caption(f"Monitor min score: {rec_rules['monitor_min_score']}")

# ── Helper: safe flags display ─────────────────────────────────────────────────

def flags_str(flags) -> str:
    if isinstance(flags, list):
        return ", ".join(flags) if flags else "—"
    return str(flags) if flags else "—"


# ── Tabs ───────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Executive Overview",
    "Vendor Intelligence",
    "Quality Trends",
    "Suspicious Traffic",
    "Experiment Engine",
    "Vendor Drilldown",
    "Methodology",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Executive Overview
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.header("Executive Overview")

    kpi = get_executive_summary(df)
    active_exp = (
        int((experiments_df["status"] == "active").sum())
        if not experiments_df.empty else 0
    )

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Vendors",         kpi["total_vendors"])
    c2.metric("Avg Score",       f"{kpi['avg_quality_score']:.1f}")
    c3.metric("Scale",           kpi["vendors_to_scale"])
    c4.metric("Monitor",         kpi["vendors_to_monitor"])
    c5.metric("Pause",           kpi["vendors_to_pause"])
    c6.metric("Anomalies",       kpi["active_anomalies"])
    c7.metric("Active Exps",     active_exp)

    st.caption(
        f"Data range: {kpi['date_range_start']} → {kpi['date_range_end']}"
    )
    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Score Distribution")
        latest = df.sort_values("date").groupby("vendor_id").last().reset_index()
        fig_hist = px.histogram(
            latest,
            x="quality_score",
            color="recommendation",
            color_discrete_map=REC_COLORS,
            nbins=15,
            labels={"quality_score": "Quality Score (0–100)", "count": "Vendors"},
        )
        fig_hist.add_vline(
            x=rec_rules["scale_min_score"], line_dash="dash", line_color="#10B981",
            annotation_text="Scale", annotation_position="top right",
        )
        fig_hist.add_vline(
            x=rec_rules["monitor_min_score"], line_dash="dash", line_color="#F59E0B",
            annotation_text="Monitor", annotation_position="top right",
        )
        fig_hist.update_layout(height=320, showlegend=True, legend_title="Action")
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_right:
        st.subheader("Recommendation Breakdown")
        summary = (
            latest.groupby("recommendation")
            .agg(vendors=("vendor_id", "count"), avg_score=("quality_score", "mean"))
            .reset_index()
        )
        summary["avg_score"] = summary["avg_score"].round(1)
        summary.columns = ["Recommendation", "Vendors", "Avg Score"]
        st.dataframe(summary, use_container_width=True, hide_index=True)

        st.subheader("Anomaly Status")
        anomaly_summary = (
            latest.groupby("flag_severity")
            .agg(vendors=("vendor_id", "count"))
            .reset_index()
        )
        anomaly_summary.columns = ["Severity", "Vendors"]
        st.dataframe(anomaly_summary, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Vendor Intelligence Table
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.header("Vendor Intelligence Table")
    st.caption("Latest snapshot per vendor — score, trend, recommendation, and anomaly status.")

    table = get_vendor_intelligence_table(df)
    display = table[
        ["vendor_name", "quality_score", "trend_direction", "recommendation",
         "flags_display", "reason"]
    ].copy()
    display.columns = ["Vendor", "Score", "Trend", "Action", "Flags", "Reason"]

    styled = display.style.map(
        lambda v: TABLE_STYLES.get(v, ""), subset=["Action"]
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Score Comparison")

    latest = df.sort_values("date").groupby("vendor_id").last().reset_index()
    fig_bar = px.bar(
        latest.sort_values("quality_score"),
        x="quality_score",
        y="vendor_name",
        color="recommendation",
        color_discrete_map=REC_COLORS,
        orientation="h",
        text="quality_score",
        labels={"quality_score": "Quality Score (0–100)", "vendor_name": "Vendor"},
    )
    fig_bar.add_vline(
        x=rec_rules["scale_min_score"], line_dash="dash", line_color="#10B981",
        annotation_text="Scale threshold",
    )
    fig_bar.add_vline(
        x=rec_rules["monitor_min_score"], line_dash="dash", line_color="#F59E0B",
        annotation_text="Monitor threshold",
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(xaxis_range=[0, 115], height=420, legend_title="Action")
    st.plotly_chart(fig_bar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Quality Trend Analysis
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.header("Quality Trend Analysis")

    vendor_options = sorted(df["vendor_name"].unique().tolist())
    selected_vendors = st.multiselect(
        "Select vendors to display",
        vendor_options,
        default=vendor_options,
        key="trend_vendor_select",
    )

    trend_df = get_trend_data(df)
    filtered = trend_df[trend_df["vendor_name"].isin(selected_vendors)]

    st.subheader("Quality Score Over Time")
    fig_score = px.line(
        filtered,
        x="date",
        y="quality_score",
        color="vendor_name",
        labels={"quality_score": "Quality Score", "date": "Date", "vendor_name": "Vendor"},
    )
    fig_score.add_hline(
        y=rec_rules["scale_min_score"], line_dash="dash", line_color="#10B981",
        annotation_text="Scale threshold",
    )
    fig_score.add_hline(
        y=rec_rules["monitor_min_score"], line_dash="dash", line_color="#F59E0B",
        annotation_text="Monitor threshold",
    )
    fig_score.update_layout(height=380)
    st.plotly_chart(fig_score, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Engagement Index Over Time")
        if "engagement_index" in filtered.columns:
            fig_eng = px.line(
                filtered,
                x="date",
                y="engagement_index",
                color="vendor_name",
                labels={"engagement_index": "Engagement Index (0–1)",
                        "date": "Date", "vendor_name": "Vendor"},
            )
            fig_eng.update_layout(height=300)
            st.plotly_chart(fig_eng, use_container_width=True)

    with col_right:
        st.subheader("Bounce Rate Over Time")
        fig_bounce = px.line(
            filtered,
            x="date",
            y="bounce_rate",
            color="vendor_name",
            labels={"bounce_rate": "Bounce Rate", "date": "Date",
                    "vendor_name": "Vendor"},
        )
        fig_bounce.add_hline(
            y=rules["high_bounce_threshold"], line_dash="dash", line_color="#EF4444",
            annotation_text="Bounce flag threshold",
        )
        fig_bounce.update_layout(height=300)
        st.plotly_chart(fig_bounce, use_container_width=True)

    st.divider()
    st.subheader("Rising Risk Vendors")
    risk_df = get_rising_risk_vendors(df)
    if risk_df.empty:
        st.success("No rising-risk vendors detected.")
    else:
        risk_df.columns = [
            "Vendor ID", "Vendor", "Score", "Trend", "Flags", "Action"
        ]
        st.dataframe(risk_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Suspicious Traffic Analysis
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.header("Suspicious Traffic Analysis")
    st.caption("Vendors with active anomaly flags based on rule-based behavioral detection.")

    suspicious = get_suspicious_traffic(df)

    if suspicious.empty:
        st.success("No suspicious traffic detected in the current dataset.")
    else:
        for _, row in suspicious.iterrows():
            severity = row["flag_severity"]
            badge = "🔴 SEVERE" if severity == "severe" else "🟡 WARNING"
            with st.expander(
                f"{badge} — **{row['vendor_name']}**  |  "
                f"Score: {row['quality_score']:.0f}  |  "
                f"Last flagged: {row['date'].strftime('%Y-%m-%d')}"
            ):
                st.markdown(f"**Active flags:** `{flags_str(row['flags'])}`")
                st.markdown(f"**Explanation:** {row['flag_reason']}")
                st.markdown(f"**Recommendation:** **{row['recommendation']}**")

        st.divider()
        st.subheader("Full Anomaly History")
        all_flagged = df[df["flag_severity"] != "none"][
            ["date", "vendor_name", "flags", "flag_severity",
             "quality_score", "recommendation"]
        ].copy()
        all_flagged["flags"] = all_flagged["flags"].apply(flags_str)
        all_flagged = all_flagged.sort_values("date", ascending=False)
        all_flagged.columns = [
            "Date", "Vendor", "Flags", "Severity", "Score", "Action"
        ]
        st.dataframe(all_flagged, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Experiment Engine
# ══════════════════════════════════════════════════════════════════════════════

with tab5:
    st.header("Experiment Engine")
    st.caption(
        "Lightweight A/B experiment simulation for vendor traffic testing. "
        "Results are directional — no formal significance testing is applied in this POC."
    )

    if experiments_df.empty:
        st.warning("No experiment data found. Check `data/sample_experiments.csv`.")
    else:
        st.subheader("Experiment Registry")
        exp_display = experiments_df.copy()
        exp_display["start_date"] = exp_display["start_date"].dt.strftime("%Y-%m-%d")
        exp_display["end_date"] = exp_display["end_date"].dt.strftime("%Y-%m-%d")
        st.dataframe(exp_display, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Run Simulation")

        exp_names = experiments_df["experiment_name"].tolist()
        selected_exp_name = st.selectbox("Select experiment", exp_names)
        exp_row = experiments_df[
            experiments_df["experiment_name"] == selected_exp_name
        ].iloc[0]

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown(f"**Vendor:** `{exp_row['vendor_id']}`")
            st.markdown(f"**Status:** {exp_row['status'].upper()}")
            st.markdown(
                f"**Period:** {exp_row['start_date'].strftime('%Y-%m-%d')} → "
                f"{exp_row['end_date'].strftime('%Y-%m-%d')}"
            )
        with col_right:
            st.markdown(f"**Primary metric:** `{exp_row['primary_metric']}`")
            st.markdown(
                f"**Traffic split:** "
                f"{exp_row['control_allocation']:.0%} control / "
                f"{exp_row['variant_allocation']:.0%} variant"
            )

        if st.button("Run Simulation", type="primary"):
            exp_dict = exp_row.to_dict()
            exp_dict["vendor_ids"] = [exp_dict["vendor_id"]]

            assigned = run_experiment_simulation(df, exp_dict)

            if assigned.empty:
                st.warning(
                    "No matching traffic data for this experiment's vendor and date range. "
                    "Try a different experiment or ensure the vendor exists in your dataset."
                )
            else:
                summary = summarize_experiment_results(
                    assigned, exp_dict["primary_metric"]
                )
                recommendation = get_experiment_recommendation(
                    summary, exp_dict["primary_metric"]
                )

                st.subheader("Control vs Variant")
                st.dataframe(summary, use_container_width=True, hide_index=True)

                st.subheader("Outcome")
                st.info(recommendation)

                st.subheader("Uplift by Metric")
                summary["direction"] = summary["uplift_pct"].apply(
                    lambda x: "positive" if x > 0 else "negative"
                )
                fig_uplift = px.bar(
                    summary,
                    x="metric",
                    y="uplift_pct",
                    color="direction",
                    color_discrete_map={
                        "positive": "#10B981",
                        "negative": "#EF4444",
                    },
                    labels={"uplift_pct": "Uplift % (variant vs control)",
                            "metric": "Metric"},
                    text="uplift_pct",
                )
                fig_uplift.add_hline(y=0, line_color="gray", line_dash="dash")
                fig_uplift.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig_uplift.update_layout(showlegend=False, height=320)
                st.plotly_chart(fig_uplift, use_container_width=True)

                st.caption(config["experiment_defaults"]["significance_note"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Vendor Drilldown
# ══════════════════════════════════════════════════════════════════════════════

with tab6:
    st.header("Vendor Drilldown")

    vendor_options = sorted(df["vendor_name"].unique().tolist())
    selected_vendor = st.selectbox(
        "Select vendor", vendor_options, key="drilldown_vendor_select"
    )

    vendor_id = df[df["vendor_name"] == selected_vendor]["vendor_id"].iloc[0]
    vendor_df = get_vendor_drilldown(df, vendor_id)
    latest_row = vendor_df.iloc[-1]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest Score",     f"{latest_row['quality_score']:.1f} / 100")
    c2.metric("Recommendation",   latest_row["recommendation"])
    c3.metric("Trend Direction",  latest_row.get("trend_direction", "—"))
    c4.metric("Active Flags",     len(latest_row["flags"]) if latest_row["flags"] else 0)

    st.markdown(f"**Reason:** {latest_row['reason']}")
    st.divider()

    # Score trend with anomaly markers
    st.subheader("Quality Score History")
    fig_trend = px.line(
        vendor_df,
        x="date",
        y="quality_score",
        labels={"quality_score": "Quality Score", "date": "Date"},
    )
    fig_trend.add_hline(
        y=rec_rules["scale_min_score"], line_dash="dash", line_color="#10B981",
        annotation_text="Scale",
    )
    fig_trend.add_hline(
        y=rec_rules["monitor_min_score"], line_dash="dash", line_color="#F59E0B",
        annotation_text="Monitor",
    )
    anomaly_days = vendor_df[vendor_df["flag_severity"] != "none"]
    if not anomaly_days.empty:
        fig_trend.add_scatter(
            x=anomaly_days["date"],
            y=anomaly_days["quality_score"],
            mode="markers",
            marker=dict(color="#EF4444", size=10, symbol="x"),
            name="Anomaly detected",
        )
    fig_trend.update_layout(height=350)
    st.plotly_chart(fig_trend, use_container_width=True)

    # Engagement metrics 2×2 grid
    st.subheader("Engagement Metrics")
    col_a, col_b = st.columns(2)
    metric_pairs = [
        ("bounce_rate",      "Bounce Rate",       col_a),
        ("avg_session_sec",  "Avg Session (s)",   col_b),
        ("avg_scroll_depth", "Avg Scroll Depth",  col_a),
        ("ctr",              "CTR",               col_b),
    ]
    for col_name, label, container in metric_pairs:
        if col_name in vendor_df.columns:
            fig_m = px.line(
                vendor_df, x="date", y=col_name,
                labels={"date": "Date", col_name: label},
            )
            fig_m.update_layout(height=220, margin=dict(t=30, b=20))
            container.plotly_chart(fig_m, use_container_width=True)

    # Anomaly history
    st.subheader("Anomaly History")
    anomaly_hist = vendor_df[vendor_df["flag_severity"] != "none"][
        ["date", "flags", "flag_severity", "flag_reason", "quality_score"]
    ].copy()
    if anomaly_hist.empty:
        st.success("No anomalies detected for this vendor.")
    else:
        anomaly_hist["flags"] = anomaly_hist["flags"].apply(flags_str)
        anomaly_hist.columns = ["Date", "Flags", "Severity", "Reason", "Score"]
        st.dataframe(anomaly_hist, use_container_width=True, hide_index=True)

    # Full historical data
    with st.expander("Full Historical Data"):
        hist_display = vendor_df[[
            "date", "impressions", "clicks", "ctr", "bounce_rate",
            "avg_session_sec", "avg_scroll_depth", "repeat_visit_rate",
            "quality_score", "recommendation",
        ]].copy()
        hist_display["ctr"] = hist_display["ctr"].map("{:.2%}".format)
        hist_display["bounce_rate"] = hist_display["bounce_rate"].map("{:.1%}".format)
        hist_display["avg_scroll_depth"] = hist_display["avg_scroll_depth"].map("{:.1%}".format)
        hist_display["repeat_visit_rate"] = hist_display["repeat_visit_rate"].map("{:.1%}".format)
        st.dataframe(hist_display, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — Methodology
# ══════════════════════════════════════════════════════════════════════════════

with tab7:
    st.header("Methodology")

    st.subheader("Quality Score Calculation")
    st.markdown(
        "The composite quality score (0–100) is a weighted average of six "
        "behavioral signals. **No conversion or CVR data is used.**"
    )
    weights = config["scoring"]["weights"]
    method_df = pd.DataFrame([
        {
            "Signal":      "CTR Legitimacy",
            "Weight":      f"{weights['ctr']:.0%}",
            "Description": "Click-through rate within plausible range (0.5%–12%). "
                           "Penalizes extremely low (dead traffic) or high (bot-inflated) CTR.",
        },
        {
            "Signal":      "Bounce Score",
            "Weight":      f"{weights['bounce']:.0%}",
            "Description": "Inverse of bounce rate. High bounce = low score. "
                           f"Penalized linearly up to the {rules['high_bounce_threshold']:.0%} ceiling.",
        },
        {
            "Signal":      "Dwell Score",
            "Weight":      f"{weights['dwell']:.0%}",
            "Description": f"Average session time vs {config['scoring']['dwell']['target_sec']}s target. "
                           "Longer dwell = deeper content engagement.",
        },
        {
            "Signal":      "Scroll Engagement",
            "Weight":      f"{weights['scroll']:.0%}",
            "Description": f"Average scroll depth on landing pages. "
                           f"Benchmark: {config['scoring']['scroll']['min_healthy']:.0%} minimum for engaged sessions.",
        },
        {
            "Signal":      "Repeat Visit Score",
            "Weight":      f"{weights['repeat_visit']:.0%}",
            "Description": "Healthy repeat rate signals genuine interest. "
                           "Penalizes suspiciously high rates (possible bot recycling).",
        },
        {
            "Signal":      "Trend Health",
            "Weight":      f"{weights['trend_health']:.0%}",
            "Description": "Week-over-week change in the engagement index (rolling 7-day). "
                           "Improving or stable trend → high score. Sharp decline → low score.",
        },
    ])
    st.dataframe(method_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Anomaly Detection Rules")
    severe_flags = set(rules.get("severe_flags", []))
    anomaly_df = pd.DataFrame([
        {
            "Flag":      "IMPRESSION_SPIKE",
            "Trigger":   f"Impressions > {rules['impression_spike_multiple']}× historical average",
            "Severity":  "Severe",
            "Meaning":   "Sudden volume burst inconsistent with organic traffic patterns.",
        },
        {
            "Flag":      "HIGH_CTR_ANOMALY",
            "Trigger":   f"CTR > {rules['high_ctr_threshold']:.0%}",
            "Severity":  "Severe",
            "Meaning":   "Implausibly high click-through rate — likely click inflation or bot traffic.",
        },
        {
            "Flag":      "HIGH_BOUNCE_LOW_DWELL",
            "Trigger":   f"Bounce > {rules['high_bounce_threshold']:.0%} AND session < {rules['low_dwell_threshold_sec']}s",
            "Severity":  "Severe",
            "Meaning":   "Users are exiting immediately after landing — exit fraud or irrelevant targeting.",
        },
        {
            "Flag":      "ENGAGEMENT_COLLAPSE",
            "Trigger":   f"Engagement index drops >{rules.get('engagement_collapse_threshold', 0.30):.0%} vs baseline",
            "Severity":  "Severe",
            "Meaning":   "Sharp quality deterioration vs recent history — warrants immediate investigation.",
        },
        {
            "Flag":      "LOW_SCROLL_TRAFFIC",
            "Trigger":   f"Scroll depth < {rules['low_scroll_threshold']:.0%} with >100 clicks",
            "Severity":  "Warning",
            "Meaning":   "Significant clicks but negligible content engagement — traffic may be incentivized.",
        },
        {
            "Flag":      "REPEAT_PATTERN_ANOMALY",
            "Trigger":   f"Repeat visit rate > {rules.get('repeat_pattern_max', 0.95):.0%}",
            "Severity":  "Warning",
            "Meaning":   "Unrealistically uniform repeat behavior — possible bot or recycled traffic.",
        },
    ])
    st.dataframe(anomaly_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Recommendation Logic")
    st.markdown(f"""
| Recommendation | Condition |
|---|---|
| **SCALE** | Score ≥ {rec_rules['scale_min_score']} **and** no active anomaly flags |
| **MONITOR** | Score ≥ {rec_rules['monitor_min_score']}, or warning-only flags |
| **PAUSE** | Score < {rec_rules['monitor_min_score']}, or any severe anomaly flag |

Each recommendation includes a plain-English reason explaining the decision.
Thresholds are fully configurable in `config.yaml`.
""")

    st.divider()
    st.subheader("Experiment Engine")
    st.markdown(f"""
- Traffic rows are randomly assigned to **control** or **variant** using the configured allocation ratio.
- Variants represent different creatives, landing pages, bid strategies, or targeting setups.
- Behavioral outcomes (CTR, bounce, session time, scroll depth, repeat rate) are compared across groups.
- Uplift is computed as: `(variant_mean − control_mean) / control_mean × 100`.
- For **bounce rate**, a negative uplift means the variant performs *better*.
- {config["experiment_defaults"]["significance_note"]}
""")

    st.divider()
    st.subheader("Data Pipeline")
    st.code("""
CSV Upload / Data Warehouse
        │
        ▼
ingestion.py      — validate columns, cast types, derive CTR, sort by vendor/date
        │
        ▼
feature_engineering.py  — impression spike ratio, 7-day rolling averages,
                           engagement index, trend delta, trend direction
        │
        ▼
scorer.py         — 6 behavioral signal scores → weighted composite quality_score
        │
        ▼
anomaly.py        — rule-based flag detection → flag_severity, flag_reason
        │
        ▼
recommender.py    — SCALE / MONITOR / PAUSE + plain-English reason
        │
        ▼
analytics.py      — executive KPIs, trend tables, vendor intelligence table
        │
        ▼
Streamlit Dashboard (main.py)  — 7-section interactive UI
""", language="text")

    st.caption(
        "See `docs/architecture.md` for the full system overview and scalability path. "
        "See `sql/` for how this pipeline would be implemented in a production warehouse."
    )
