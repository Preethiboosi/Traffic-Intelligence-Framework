# Approach

## Why behavioral proxies instead of conversions?

In media buying, downstream conversion data is often delayed, incomplete, or entirely unavailable.

Common scenarios where conversion data cannot be trusted:
- **Upper-funnel campaigns** — brand awareness and reach objectives have no direct conversion signal
- **Attribution lag** — typical attribution windows of 24–72 hours make real-time decisions impossible
- **Publisher restrictions** — some inventory sources do not allow conversion pixel placement
- **Privacy regulations** — GDPR, iOS ATT, and cookie deprecation are eroding cross-site tracking

Waiting for conversions before evaluating vendor quality is not operationally viable. This system evaluates traffic using **behavioral proxy signals** that are available immediately on the landing page: does the traffic bounce? How long do users stay? How far do they scroll? These signals correlate with genuine user intent and can be measured without relying on downstream outcomes.

Conversions remain a useful validation signal where available, and the `future_improvements.md` doc describes how they could be incorporated as an optional layer.

---

## Why rule-based scoring?

Rule-based logic was chosen deliberately over a machine learning approach for three reasons:

1. **Explainability.** Every score and flag can be traced back to a specific signal and threshold. A media buyer can explain to a vendor or stakeholder exactly why traffic was paused — "your CTR is 18%, which exceeds the 15% ceiling for display traffic." This is critical for operational trust and vendor management conversations.

2. **No labeled data required.** Training a fraud detection model requires historical examples of confirmed invalid traffic. This dataset rarely exists in practice, and the quality of synthetic labels is unreliable. Rule-based detection works from first principles.

3. **Configurability.** All thresholds live in `config.yaml`. A non-technical analyst can tighten or relax rules to match their campaign type without touching code. Finance campaigns may tolerate lower CTR than entertainment campaigns; the config makes this adjustable.

---

## Scoring design

The composite quality score is a weighted average of six behavioral signals:

- **CTR legitimacy** — catches the two failure modes: dead traffic (CTR too low to be real) and bot-inflated traffic (CTR too high to be human). Healthy display CTR typically falls in the 0.5%–12% range.
- **Bounce score** — users who exit immediately without scrolling or clicking provide no value. High bounce rate is one of the strongest individual signals of low-quality traffic.
- **Dwell time** — average session duration serves as a proxy for genuine content consumption. A vendor sending users who stay for 3 seconds is not delivering value regardless of CTR.
- **Scroll depth** — scroll engagement on the landing page confirms that users are actively reading, not just loading the page. Very low scroll depth alongside significant clicks is a pattern consistent with incentivized or bot traffic.
- **Repeat visit rate** — some repeat traffic is a healthy signal of audience interest. Suspiciously high rates (>90%) suggest recycled or bot traffic designed to inflate engagement metrics.
- **Trend health** — a vendor's performance relative to its own recent baseline catches gradual deterioration that a single-day snapshot would miss. A vendor declining consistently over two weeks is more actionable than a single bad day.

These six signals are complementary. A vendor can have healthy CTR but terrible session behavior, or reasonable bounce rates but a collapsing trend. Using multiple dimensions reduces the risk of a single misleading metric driving a budget decision.

---

## Recommendation logic

The three-tier output maps directly to how media buyers manage vendors in practice:

- **SCALE** — increase budget allocation, this vendor is performing across all signals
- **MONITOR** — keep running but hold current budget and watch for trend changes
- **PAUSE** — stop spend immediately, investigate before resuming

Severe anomaly flags bypass the composite score and force a PAUSE. This reflects operational reality: a suspicious vendor should be stopped regardless of how its engagement metrics look — those metrics may themselves be fraudulent.

---

## Experiment engine design

The experiment engine is designed to support the most common vendor testing question in media buying: "Is this vendor's traffic better with configuration A or configuration B?"

The engine does not attempt to be a full experimentation platform. It simulates what a real system would produce — variant assignment, behavioral metric comparison, uplift calculation — at a level of fidelity appropriate for a POC and for analyst interpretation. The significance note is explicit: results are directional, not statistically confirmed.

The architecture naturally extends to production-grade tools like GrowthBook or PostHog by replacing the in-memory simulation with a real assignment database and a proper statistical test.

---

## Sample data design

The synthetic dataset was constructed to represent a realistic spread of vendor quality:

- **V001 SportzMedia** — healthy and stable; solid baseline engagement
- **V002 NewsHub** — persistently weak; near-zero CTR, very high bounce
- **V003 LifestyleNet** — mixed but improving over time; tests trend-aware detection
- **V004 TechBlog** — strong performer; long sessions, deep scroll, healthy repeat rate
- **V005 BargainSites** — clearly anomalous; high CTR, impression spike in the middle of the period
- **V006 CookingCorner** — healthy and rising; tests trend health scoring
- **V007 GamingZone** — declining engagement; tests ENGAGEMENT_COLLAPSE detection
- **V008 TravelPlus** — strong early, then sharp collapse at day 25; tests ENGAGEMENT_COLLAPSE

This range ensures charts tell a meaningful story and gives reviewers concrete examples to discuss across all dashboard sections.
