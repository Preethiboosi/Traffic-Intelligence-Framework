# Approach

## Why proxy signals instead of conversions?

In media buying, downstream conversion data is often delayed (24–72 hour attribution windows), incomplete, or unavailable entirely for upper-funnel campaigns. Waiting for conversions before evaluating traffic quality is not operationally practical.

Instead, this system evaluates traffic using **behavioral proxy signals** — metrics that correlate with genuine user intent without requiring a purchase or form fill. The logic mirrors how experienced media buyers informally assess vendor quality: Is the CTR believable? Are sessions engaging? Do users bounce immediately?

## Why rule-based scoring?

Rule-based logic was chosen deliberately over a machine learning approach for three reasons:

1. **Explainability.** Every score can be traced back to a specific signal and threshold. This is critical for operational trust — a buyer needs to be able to explain to a vendor or stakeholder why traffic was paused.
2. **No labeled data required.** Training a fraud detection model requires historical examples of confirmed fraud. This POC assumes that data does not exist.
3. **Auditability.** Thresholds live in `config.yaml` and can be adjusted without touching code.

## Scoring design

The composite quality score is the unweighted average of four signals:

- **CTR** catches inflated or dead click patterns at the volume level
- **CVR** captures downstream efficiency — the signal most directly tied to campaign value
- **Bounce rate** captures session-level intent — users who bounce immediately provide no value
- **Session time** captures engagement depth — a proxy for genuine content interaction

These four signals are complementary. A vendor can have a healthy CTR but terrible session behavior, or reasonable bounce rates but zero conversions. Using all four reduces the risk of a single misleading metric driving the decision.

## Recommendation logic

The three-tier output (SCALE / MONITOR / PAUSE) maps directly to how media buyers think about vendor management:

- **SCALE** — increase budget allocation, this vendor is performing
- **MONITOR** — keep running but watch closely, do not expand
- **PAUSE** — stop spend immediately, investigate before resuming

Fraud flags bypass the score entirely and force a PAUSE. This reflects the operational reality that a suspicious vendor should be stopped regardless of how good its engagement metrics look — those metrics may themselves be fraudulent.

## Data design

The sample dataset was constructed to represent a realistic spread of vendor quality:
- Clear performers (FinanceDaily, TravelPlus, CookingCorner)
- Borderline cases (SportzMedia)
- Obvious fraud patterns (MemeWorld — massive spike, near-zero CVR)
- Mixed cases with specific flags (LifestyleNet — spike + zero CVR, BargainSites — high bounce)

This range ensures the dashboard tells a meaningful story and gives a reviewer something to discuss.
