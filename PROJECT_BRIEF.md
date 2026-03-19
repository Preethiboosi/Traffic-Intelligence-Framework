# Traffic Intelligence Framework — Project Brief & Analysis

**Prepared for:** Deck creation and demo walkthrough
**Role applied:** Software Engineer — Experimentation & Conversion Optimization, Benchmark IT Solutions
**Candidate:** Preethi Reddy

---

## 1. What the Assignment Asked For

The assignment describes a digital media company that:
- Purchases traffic from third-party vendors and routes it to client landing pages (vehicle detail pages for automotive dealerships)
- Is evaluated by agency clients on **lead quality and form conversions**
- But **cannot see conversions** — it does not control the landing pages and gets no downstream data
- Suffers from inconsistent, unscalable manual vendor checks
- Needs a system that runs **continuously**, not as a one-time report

**Three explicit asks:**
1. A **Traffic Intelligence Framework** — score vendor traffic quality using behavioral proxies
2. An **Experiment Engine** — randomized traffic tests, traffic distribution, result collection
3. **Actionable output** — clear media buying recommendations

**Success criteria from the assignment:**
- Identify the top 20% of traffic sources
- Those sources produce higher engagement
- Media buying decisions become data-driven

---

## 2. What Was Built — Module by Module

### Data Pipeline

| Module | What It Does |
|---|---|
| `src/ingestion.py` | Loads vendor daily CSV, validates columns, derives CTR — **no conversion field required** |
| `src/feature_engineering.py` | Computes 7-day rolling averages, engagement index, trend delta (week-over-week), trend direction per vendor |
| `src/scorer.py` | Scores 6 behavioral signals (CTR, bounce, dwell, scroll, repeat visit, trend health) → weighted composite score 0–100 |
| `src/anomaly.py` | 6 rule-based fraud flags independent of the score (see below) |
| `src/recommender.py` | Maps score + anomaly severity → **SCALE / MONITOR / PAUSE** + plain-English reason |
| `src/analytics.py` | Aggregates data for each dashboard section (KPIs, trend tables, vendor intelligence) |
| `src/experiment_engine.py` | A/B variant assignment, behavioral outcome comparison, uplift calculation, recommendation |

### Scoring Signals (Zero Conversion Dependency)

| Signal | Weight | What It Detects |
|---|---|---|
| CTR Legitimacy | 20% | Too low = dead traffic; too high = bot-inflated |
| Bounce Score | 20% | Users leaving immediately = low intent |
| Dwell Time | 20% | Session length as proxy for content engagement |
| Scroll Depth | 20% | How far users read — strongest engagement signal |
| Repeat Visit Rate | 10% | Genuine interest vs recycled/bot traffic |
| Trend Health | 10% | Is quality improving or deteriorating over time? |

### Anomaly Flags (Independent of Score)

| Flag | Trigger | Severity |
|---|---|---|
| IMPRESSION_SPIKE | Impressions > 3× historical average | Severe → PAUSE |
| HIGH_CTR_ANOMALY | CTR > 15% | Severe → PAUSE |
| HIGH_BOUNCE_LOW_DWELL | Bounce > 85% AND session < 10s | Severe → PAUSE |
| ENGAGEMENT_COLLAPSE | Engagement drops >30% vs recent baseline | Severe → PAUSE |
| LOW_SCROLL_TRAFFIC | Scroll < 10% with > 100 clicks | Warning → MONITOR |
| REPEAT_PATTERN_ANOMALY | Repeat visit rate > 95% | Warning → MONITOR |

### Experiment Engine

- Define experiments with vendor ID, date range, traffic split (control/variant %)
- Randomly assign vendor traffic rows to control or variant
- Compare all behavioral metrics across groups
- Compute uplift: `(variant - control) / control × 100`
- Output plain-English recommendation per experiment

### Dashboard (7 Tabs)

1. **Executive Overview** — Vendor count, avg score, SCALE/MONITOR/PAUSE breakdown, active experiments
2. **Vendor Intelligence Table** — Latest score, trend direction, recommendation, active flags per vendor
3. **Quality Trend Analysis** — Score and engagement over time; rising-risk vendor table
4. **Suspicious Traffic Analysis** — Flagged vendors with plain-English explanations
5. **Experiment Engine** — Experiment registry, run simulation, control vs variant comparison, uplift chart
6. **Vendor Drilldown** — Full history per vendor with anomaly markers on score chart
7. **Methodology** — Scoring logic, anomaly rules, experiment assumptions, pipeline diagram

### SQL Layer (Production Thinking)

| File | Purpose |
|---|---|
| `sql/schema.sql` | Warehouse schemas: raw_events, vendor_daily_metrics, experiments, assignment log, results |
| `sql/vendor_metrics.sql` | Daily aggregation CTE from raw session events → vendor_daily_metrics |
| `sql/experiment_results.sql` | Control vs variant comparison with uplift for all behavioral metrics |

### Sample Data

- `data/sample_vendor_daily.csv` — **10 vendors × 35 days = 350 rows** with realistic patterns
- `data/sample_experiments.csv` — 5 experiments (active / paused / completed)
- `data/sample_event_log.csv` — Mock session event log (illustrates the raw instrumentation layer)

---

## 3. Alignment Analysis — Assignment vs What Was Built

### ✅ Strong Matches

| Assignment Requirement | What Was Built | Notes |
|---|---|---|
| No conversion data dependency | Zero CVR fields anywhere in the codebase | Core constraint respected end-to-end |
| Behavioral proxy signals | 6 signals: CTR, bounce, dwell, scroll, repeat, trend | Directly maps to the VDP engagement problem |
| Experiment Engine with randomized traffic testing | `src/experiment_engine.py` — assign variants, collect results, compute uplift | Satisfies all three stated sub-requirements |
| Traffic distribution across experiments | Control/variant split with configurable allocation % | Configurable in experiment definition |
| Result collection | `summarize_experiment_results()` — per-metric comparison table | Covers all 5 behavioral metrics |
| Continuously operating (not one-time) | 35-day time-series data, rolling averages, trend health score | Built for daily operation, not snapshot |
| Clear media buying recommendations | SCALE / MONITOR / PAUSE with plain-English reason | Directly usable by non-technical buyers |
| Fraud / non-human traffic detection | 6 anomaly flags, severity classification | Impression spikes, CTR anomalies, engagement collapse |
| Scalable (not manual) | Fully automated pipeline, config-driven thresholds | One CSV in → full analysis out |
| Identify top 20% traffic sources | Vendors ranked by score; top scorers get SCALE recommendation | In sample data: 5/10 vendors score SCALE |
| SQL / data pipeline thinking | 3 SQL files showing warehouse schema and aggregation queries | Demonstrates production architecture thinking |
| Explainable to non-technical teams | Plain-English flag reasons, score breakdown, methodology tab | Analyst-friendly throughout |

### ⚠️ Gaps to Note Honestly

| Gap | Why It Exists | How to Address in Next Phase |
|---|---|---|
| No GrowthBook / PostHog integration | POC is local-first; integration would require accounts/infra | Referenced in `docs/future_improvements.md`; can demo the concept and explain the integration path |
| JS/TypeScript not used | JD mentions JS/TS but the POC is Python — acceptable for a data/analytics POC | If questioned: the scoring pipeline and SQL artifacts are language-agnostic; JS would be used for the event tag/instrumentation layer |
| No actual event instrumentation (pixel/tag) | Requires a live web environment | `data/sample_event_log.csv` + `sql/schema.sql` define exactly what the tag would produce |
| Experiment scheduling is simulated | Engine runs on existing data rather than scheduling future tests | Architecture is correct; scheduling would be added via Airflow/cron in production |
| "Session replay" not implemented | Not feasible in a Python POC | PostHog handles this natively — mention as integration point |
| Automotive/VDP context not explicit | Sample data uses generic vendor names | Trivial to rename: VDP vendors for auto clients. The logic is identical |
| No formal statistical significance | POC gives directional uplift only | Noted explicitly in methodology tab; scipy.stats.ttest_ind would add this in one function |

### Overall Verdict

**The project is well-aligned with the assignment.** Every core requirement from the assignment brief is addressed:
- ✅ No conversion dependency
- ✅ Behavioral scoring using engagement proxies
- ✅ Experiment Engine with traffic distribution and result collection
- ✅ Continuously operational (time-series architecture)
- ✅ Clear recommendations for media buying team
- ✅ SQL showing production pipeline thinking

The gaps are genuine but minor — they are implementation details (PostHog integration, scheduling) not architectural gaps. The system design is sound.

---

## 4. How the Project Maps to the Resume

| Resume Skill | Used in This Project |
|---|---|
| Python, FastAPI, Pandas | Core scoring pipeline is Python + Pandas |
| React / Next.js dashboards (Capital One) | Dashboard skills translated to Streamlit for fast POC delivery |
| Real-time anomaly monitoring (Capital One) | Directly parallel to the fraud flag detection system |
| PostgreSQL / BigQuery (GCP) | SQL artifacts written for warehouse deployment (BigQuery-compatible syntax) |
| LLM APIs (Claude, OpenAI) | Plain-English recommendation text generation mirrors the "intelligent automation" work at Capital One |
| Event-driven microservices (Kafka, Zomato) | Sample event log + SQL schema show equivalent event instrumentation design |
| CI/CD, GitHub Actions | Clean commit history with meaningful messages; repo structured for team use |

---

## 5. What to Improve in the Next Phase

These are ranked by impact for the interview / demo:

### High Priority (Do Before Demo)
1. **Add a "Top 20% Vendors" callout** in the Executive Overview tab — the assignment literally says "identify the top 20% traffic sources." Add a metric card or highlight table showing this explicitly.
2. **Mention PostHog/GrowthBook by name** in the Experiment Engine tab with a one-line note on how it would plug in. This shows awareness of the tools the JD specifically asks for.
3. **Add automotive context** to the sample data — rename vendors to feel like VDP/auto traffic sources (e.g., "AutoNation DSP", "DealerSocket Network") so the demo tells the right industry story.

### Medium Priority (Strengthen the Story)
4. **Add a "Budget Allocation Recommendation" summary** — e.g., "Based on current scores, allocate 65% of budget to SCALE vendors." This bridges scoring to the media buying decision more explicitly.
5. **Add a simple statistical note** to experiment results — even just reporting standard deviation alongside the mean makes it look more rigorous.
6. **Add the event instrumentation diagram** — a simple visual showing: Browser Tag → raw_events → Daily Aggregation → Scoring Pipeline. This answers "how does data get in?" which will definitely be asked.

### Lower Priority (Nice to Have)
7. **Create a short demo script** — 3-minute walkthrough: start with Executive Overview, pick one suspicious vendor, show the drilldown, run an experiment, explain methodology.
8. **Add one more "improving" vendor** that crosses from MONITOR to SCALE during the 35-day window — shows the system catching a positive trend, not just negative ones.

---

## 6. Project Summary for Deck Creation

**One-line pitch:**
A lightweight, continuously-operating Traffic Intelligence Framework that scores vendor traffic quality using behavioral engagement signals — no conversion data required — and includes an experiment engine for A/B testing vendor configurations.

**Three core capabilities:**

**1. Traffic Quality Scoring**
Every vendor gets a daily behavioral quality score (0–100) based on CTR, bounce rate, dwell time, scroll depth, repeat visit rate, and engagement trend. Scores update daily and detect whether quality is improving or declining over time. No conversion or form-fill data is used.

**2. Anomaly & Fraud Detection**
Six rule-based flags detect patterns consistent with invalid traffic — impression spikes, implausible CTR, immediate exits, engagement collapse, and bot-like repeat patterns. Severe flags automatically force a PAUSE recommendation regardless of score.

**3. Experiment Engine**
A/B tests can be defined per vendor, with configurable traffic splits. The engine randomly assigns daily traffic to control or variant groups and compares behavioral outcomes (CTR, bounce, session time, scroll depth). Uplift is calculated and a plain-English recommendation is generated per experiment.

**Output for media buyers:**
- SCALE — increase budget, quality is confirmed strong
- MONITOR — hold budget, watch for changes
- PAUSE — stop spend, anomaly or low quality detected

Every recommendation includes a plain-English explanation. All thresholds are configurable without touching code.

**Tech stack:** Python, Pandas, Streamlit, Plotly, PyYAML
**Production path:** SQL schema + aggregation queries included; integrates with BigQuery/Snowflake, dbt, Airflow, and GrowthBook/PostHog for production deployment.
