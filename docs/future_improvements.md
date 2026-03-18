# Future Improvements

These are the most impactful next steps if this system were to move beyond POC stage.

## Data

- **Connect to real ad traffic logs.** Replace the CSV input with a direct connector to DSP reporting APIs (Google DV360, The Trade Desk, Amazon DSP) or a data warehouse (BigQuery, Snowflake).
- **Session-level data.** Aggregate metrics hide within-vendor variance. Session-level logs would allow flagging specific traffic clusters rather than pausing an entire vendor.
- **Time-series support.** Currently the system evaluates a single snapshot. Tracking scores across reporting periods would enable trend detection — a vendor declining over three weeks is more actionable than a single low score.

## Scoring

- **Signal weighting calibration.** Equal weighting is a reasonable default but not necessarily optimal. If downstream conversion data is available historically, weights can be regressed against actual business outcomes.
- **Peer benchmarking.** Score vendors relative to category benchmarks (e.g., finance vs. entertainment publishers have different typical CTR ranges) rather than fixed global thresholds.
- **Confidence intervals.** A vendor with 500 impressions and a vendor with 500,000 impressions should not be treated with equal confidence. Volume-adjusted scoring would improve accuracy for low-traffic vendors.

## Fraud Detection

- **Statistical anomaly detection.** Replace hard threshold rules with a model (e.g., Isolation Forest) trained on historical vendor behavior. This would catch subtle, gradual fraud patterns that don't cross fixed thresholds.
- **IP and device fingerprinting.** With access to raw impression logs, cluster analysis on IP ranges, user agents, and device IDs would identify coordinated bot traffic that looks clean at the aggregate level.
- **Third-party IVT integration.** Augment internal scoring with signals from IVT measurement vendors (DoubleVerify, Integral Ad Science).

## Operations

- **Automated alerts.** Trigger Slack or email notifications when a vendor crosses into PAUSE territory, rather than requiring a manual dashboard review.
- **Feedback loop.** Allow analysts to mark recommendations as correct or incorrect. Over time, this feedback can be used to calibrate thresholds and improve recommendation accuracy.
- **A/B test support.** When evaluating a new vendor, route a small budget split and use the framework to evaluate quality before committing at scale.
