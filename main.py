import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from src.ingestion import load_config, load_data
from src.scorer import compute_scores
from src.recommender import apply_recommendations

st.set_page_config(page_title="Traffic Intelligence", layout="wide")

REC_COLORS = {
    "PAUSE":   "#e74c3c",
    "MONITOR": "#f39c12",
    "SCALE":   "#27ae60",
}

TABLE_STYLES = {
    "PAUSE":   "background-color: #fdd; color: #900",
    "MONITOR": "background-color: #ffd; color: #760",
    "SCALE":   "background-color: #dfd; color: #060",
}

# ── Sidebar ──────────────────────────────────────────────────────────────────

cfg = load_config("config.yaml")
s, f = cfg["scoring"], cfg["fraud_flags"]

with st.sidebar:
    st.header("Data Source")
    uploaded = st.file_uploader("Upload CSV", type="csv")
    st.caption("Leave empty to use the built-in sample dataset.")
    st.divider()
    st.markdown("**Active Thresholds**")
    st.write(f"CTR healthy range: {s['ctr']['min_healthy']:.2%} – {s['ctr']['max_healthy']:.0%}")
    st.write(f"Bounce rate ceiling: {s['bounce_rate_max']:.0%}")
    st.write(f"Session time target: {s['session_time_max']}s")
    st.write(f"Spike threshold: >{f['impression_spike_multiplier']}× historical avg")
    st.write(f"High CTR flag: >{f['high_ctr_threshold']:.0%}")

# ── Load & process data ───────────────────────────────────────────────────────

source = uploaded if uploaded else "data/sample_traffic.csv"

try:
    df = load_data(source)
    df = compute_scores(df, cfg)
    df = apply_recommendations(df, cfg)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# ── Page header ───────────────────────────────────────────────────────────────

st.title("Traffic Intelligence Framework")
st.caption("Vendor traffic quality evaluation for media buying decisions")

if not uploaded:
    st.info("Running on sample data. Upload your own CSV via the sidebar.")

st.divider()

# ── Section 1: Campaign Health Overview ──────────────────────────────────────

st.subheader("Campaign Health Overview")

total     = len(df)
avg_score = df["quality_score"].mean()
n_pause   = int((df["recommendation"] == "PAUSE").sum())
n_scale   = int((df["recommendation"] == "SCALE").sum())
n_flagged = int((df["flags"] != "—").sum())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Vendors Analyzed", total)
c2.metric("Avg Quality Score", f"{avg_score:.1f} / 100")
c3.metric("Flagged", n_flagged, help="Vendors with at least one fraud/anomaly flag")
c4.metric("Pause", n_pause, delta=f"-{n_pause} vendors", delta_color="inverse")
c5.metric("Scale", n_scale, delta=f"+{n_scale} vendors")

st.divider()

# ── Section 2: Vendor Quality Ranking ────────────────────────────────────────

st.subheader("Vendor Quality Ranking")
st.caption("Sorted by quality score. Color indicates recommended action.")

display = df[[
    "vendor_id", "vendor_name", "impressions", "ctr", "cvr",
    "bounce_rate", "quality_score", "flags", "recommendation", "reason"
]].sort_values("quality_score", ascending=False).copy()

display.columns = [
    "Vendor ID", "Vendor", "Impressions", "CTR", "CVR",
    "Bounce Rate", "Quality Score", "Flags", "Action", "Reason"
]
display["CTR"]        = display["CTR"].map("{:.2%}".format)
display["CVR"]        = display["CVR"].map("{:.2%}".format)
display["Bounce Rate"] = display["Bounce Rate"].map("{:.0%}".format)

styled = display.style.map(
    lambda v: TABLE_STYLES.get(v, ""), subset=["Action"]
)
st.dataframe(styled, use_container_width=True, hide_index=True)

st.divider()

# ── Section 3: Quality Score Breakdown ───────────────────────────────────────

st.subheader("Quality Score by Vendor")
st.caption("Bars are broken into four signal components. Each contributes equally to the final score.")

chart_df = df[["vendor_id", "recommendation", "quality_score",
               "ctr_score", "cvr_score", "bounce_score", "session_score"]].copy()
chart_df = chart_df.sort_values("quality_score")
chart_df["color"] = chart_df["recommendation"].map(REC_COLORS)

fig = px.bar(
    chart_df,
    x="quality_score",
    y="vendor_id",
    orientation="h",
    color="recommendation",
    color_discrete_map=REC_COLORS,
    text="quality_score",
    labels={"quality_score": "Quality Score (0–100)", "vendor_id": "Vendor"},
    hover_data={"ctr_score": True, "cvr_score": True,
                "bounce_score": True, "session_score": True,
                "recommendation": False, "quality_score": False},
)
fig.update_traces(textposition="outside")
fig.update_layout(xaxis_range=[0, 110], height=380, legend_title="Action")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Section 4: Suspicious Traffic ────────────────────────────────────────────

st.subheader("Suspicious Traffic Analysis")

flagged = df[df["flags"] != "—"][[
    "vendor_id", "vendor_name", "impressions", "ctr", "flags", "recommendation", "reason"
]].copy()

if flagged.empty:
    st.success("No suspicious traffic patterns detected across all vendors.")
else:
    st.warning(f"{len(flagged)} vendor(s) flagged for suspicious patterns.")

    flagged.columns = ["Vendor ID", "Vendor", "Impressions", "CTR", "Flags", "Action", "Reason"]
    flagged["CTR"] = flagged["CTR"].map("{:.2%}".format)

    styled_flags = flagged.style.map(
        lambda v: TABLE_STYLES.get(v, ""), subset=["Action"]
    )
    st.dataframe(styled_flags, use_container_width=True, hide_index=True)

    with st.expander("Flag definitions"):
        st.markdown("""
| Flag | Trigger | What it means |
|---|---|---|
| `IMPRESSION_SPIKE` | Volume > 3× historical average | Sudden traffic burst — may indicate bot activity or incentivized traffic |
| `ZERO_CVR` | 500+ clicks with 0 conversions | Clicks are not translating downstream — possible click fraud |
| `HIGH_CTR` | CTR > 15% | Abnormal engagement rate for display traffic — likely inflated |
        """)

st.divider()

# ── Section 5: Vendor Drill-down ─────────────────────────────────────────────

st.subheader("Vendor Drill-down")

vendor_options = df["vendor_id"] + " — " + df["vendor_name"]
selected_label = st.selectbox("Select a vendor", vendor_options.tolist())
selected_id    = selected_label.split(" — ")[0]
row = df[df["vendor_id"] == selected_id].iloc[0]

action_color = REC_COLORS.get(row["recommendation"], "#999")
st.markdown(
    f"**Recommendation:** "
    f"<span style='color:{action_color}; font-weight:bold'>{row['recommendation']}</span> — "
    f"{row['reason']}",
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Quality Score",  f"{row['quality_score']:.1f} / 100")
c2.metric("Flags",          row["flags"])
c3.metric("Impressions",    f"{int(row['impressions']):,}")
c4.metric("Conversions",    int(row["conversions"]))

c5, c6, c7, c8 = st.columns(4)
c5.metric("CTR Score",     f"{row['ctr_score']:.1f}",     help=f"Raw CTR: {row['ctr']:.2%}")
c6.metric("CVR Score",     f"{row['cvr_score']:.1f}",     help=f"Raw CVR: {row['cvr']:.2%}")
c7.metric("Bounce Score",  f"{row['bounce_score']:.1f}",  help=f"Bounce rate: {row['bounce_rate']:.0%}")
c8.metric("Session Score", f"{row['session_score']:.1f}", help=f"Avg session: {row['avg_session_sec']}s")

st.divider()

# ── Section 6: Scoring Methodology ───────────────────────────────────────────

with st.expander("How is the quality score computed?"):
    st.markdown("""
**Quality Score = average of four signal scores (each 0–100)**

| Signal | What it measures | How it's scored |
|---|---|---|
| **CTR Score** | Click-through rate validity | 100 if within healthy range (0.01%–10%). Penalized proportionally outside that range. |
| **CVR Score** | Conversion efficiency | Normalized against the best-performing vendor in the current dataset. |
| **Bounce Score** | Session intent | `(1 − bounce_rate / 0.85) × 100`. High bounce = low score. |
| **Session Score** | Dwell time / engagement depth | `(avg_session_sec / 120) × 100`, capped at 100. |

**Fraud flags** are applied independently. A vendor with any active flag is automatically recommended for **PAUSE**, regardless of score.

**Recommendation thresholds** (configurable in `config.yaml`):
- **SCALE** — score ≥ 70 and no flags
- **MONITOR** — score 40–69
- **PAUSE** — score < 40 or any flag active
    """)
