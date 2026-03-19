# Future Improvements

These are the highest-value next steps if this system were to move from POC to production.

---

## Data Pipeline

**Connect to live ad traffic data.**
Replace CSV input with direct connectors to DSP reporting APIs (Google DV360, The Trade Desk, Amazon DSP, Xandr). Most platforms expose daily impression, click, and engagement metrics via REST APIs. The `sql/vendor_metrics.sql` file shows how the aggregation would work once raw event data is available.

**Event-level instrumentation.**
Deploy a JavaScript pixel or server-side tag on landing pages to capture raw session events (impression, click, scroll, session_end). This feeds the `raw_events` table defined in `sql/schema.sql` and enables much richer behavioral analysis than daily aggregates. The `data/sample_event_log.csv` file shows the target event format.

**Data warehouse integration.**
Schedule the daily aggregation pipeline (`sql/vendor_metrics.sql`) as a dbt model or Airflow DAG. Write scored vendor data back to `vendor_daily_metrics`. Connect a BI tool (Looker, Metabase, Tableau) for broader team access.

**Session-level analysis.**
Aggregate-level data hides within-vendor variance. A vendor with an acceptable average session time may have a bimodal distribution: half of sessions are 0 seconds (bots) and half are 180 seconds (real users). Session-level logs make this visible.

---

## Scoring

**Signal weight calibration.**
Default equal-ish weighting is a reasonable starting point but not necessarily optimal. If conversion data is available historically (even partially), run a regression against business outcomes to calibrate weights. A vendor with a 3% CTR but no downstream value should weight dwell time and scroll depth more heavily.

**Peer benchmarking.**
Score vendors relative to category benchmarks rather than fixed global thresholds. Finance publishers typically have lower CTR than entertainment publishers. Adjusting the healthy CTR range by vertical reduces false anomalies and improves score comparability.

**Volume-adjusted confidence.**
A vendor with 500 impressions and one with 500,000 impressions should not be treated with equal confidence. Add credibility intervals or minimum sample size requirements before generating a SCALE recommendation. A low-volume vendor with a perfect score is less reliable than a high-volume vendor with an 80.

---

## Anomaly Detection

**Statistical anomaly detection.**
Replace hard threshold rules with a model trained on historical vendor behavior. Isolation Forest, Local Outlier Factor, or a simple z-score approach would catch subtle, gradual fraud patterns that don't cross fixed thresholds. The advantage of these methods is self-calibrating sensitivity — a threshold that makes sense for one vendor may not apply to another.

**IP and device fingerprinting.**
With access to raw impression logs, cluster analysis on IP ranges, user agents, device IDs, and timing patterns would identify coordinated bot traffic that looks clean at the aggregate level.

**Third-party IVT integration.**
Augment internal scoring with signals from IVT measurement vendors (DoubleVerify, Integral Ad Science, HUMAN). Their invalid traffic classifications can serve as additional input features or as validation for rule-based flags.

---

## Experimentation

**Production-grade experiment management.**
Replace the in-memory simulation with [GrowthBook](https://www.growthbook.io) or [PostHog](https://posthog.com). Both are open-source, support session-level assignment, provide statistically valid significance testing, and include experiment management UIs.

**Formal significance testing.**
Add a frequentist t-test or Bayesian posterior comparison to the experiment summary. Even a simple implementation using `scipy.stats.ttest_ind` would add meaningful rigor to the uplift calculations. Correct for multiple comparisons when testing more than one metric simultaneously.

**Guardrail metrics.**
Define secondary metric guardrails that automatically flag an experiment as harmful. If a CTR experiment significantly worsens bounce rate or session time, it should be flagged for review regardless of the primary metric result.

---

## Operations

**Automated alerts.**
Send Slack or email notifications when a vendor crosses into PAUSE territory, when a new severe flag appears, or when an engagement trend shows a significant decline. This removes the need for manual dashboard monitoring and makes the system operationally useful.

**Feedback loop.**
Allow analysts to mark recommendations as correct or incorrect (thumbs up/down in the dashboard). Over time, this feedback can calibrate thresholds, identify edge cases, and validate anomaly detection accuracy.

**Audit trail.**
Log every recommendation with the input data, config version, and timestamp. In regulated environments (financial services, healthcare), being able to explain and reproduce a historical recommendation is a compliance requirement.

**Multi-period scoring.**
Introduce a rolling quality score that weights recent days more heavily than older data. A vendor that had two bad weeks followed by three good weeks should not be evaluated the same as a vendor consistently performing well. Exponentially-weighted moving averages would address this.
