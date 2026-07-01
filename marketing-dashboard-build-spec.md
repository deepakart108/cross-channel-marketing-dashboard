# AI Cross-Channel Marketing Performance Dashboard — Build Spec

## Project Summary
A web app that ingests exported performance data from multiple marketing channels (paid social, paid search, programmatic, email), normalizes it into a unified schema, runs it through a domain-expert rules engine, and uses Claude (grounded via RAG on official platform documentation) to generate prioritized, cross-channel insights and recommended next steps — replicating and automating the manual weekly/quarterly reporting process used at marketing agencies.

**Architecture pattern:** Same as prior shipped projects — ingest → normalize → rules engine → AI-enrich (RAG-grounded) → dashboard. Consistent with Mailchimp Brand Voice RAG Chatbot and Competitive Content Intelligence Dashboard.

---

## Stack
- **Backend:** Python / Flask
- **AI layer:** Claude API (Sonnet)
- **Vector store:** Pinecone (RAG over platform documentation)
- **Frontend:** Dark-theme dashboard, charts via Chart.js or Plotly
- **Hosting:** Railway
- **Repo:** GitHub, documented same as prior projects (README, architecture diagram, live link)

---

## Channels in Scope
- Meta (Facebook/Instagram) Ads
- Google Ads (Search)
- TikTok Ads
- Pinterest Ads
- Snapchat Ads
- Programmatic/DSP (generic schema, optional)
- Email (Mailchimp)

---

## Unified Data Schema

| Field | Applies To | Notes |
|---|---|---|
| channel, platform, campaign_name, date_range | All | Required for every row |
| spend, impressions, clicks, ctr | Meta, Google Search, TikTok, Pinterest, Snap, Programmatic | Standard paid metrics |
| conversions, cpa, roas | All paid | |
| frequency | Meta, TikTok, Pinterest, Snap | Fatigue signal — not applicable to Search |
| avg_position / search_impression_share | Google Search only | |
| viewability_rate | Programmatic | |
| sends, opens, open_rate, ctor, unsubscribes | Mailchimp/email | |

**Ingestion approach:** drag-and-drop CSV/Excel exports per platform (not live API pull — mirrors how real Marketing Ops teams actually work day to day, avoids Meta/TikTok API app-review overhead).

---

## Rules Engine (Domain-Expert Logic)

Goal: encode marketing domain knowledge as deterministic if/then rules *before* AI narrates anything. AI explains conclusions the rules engine already reached — it does not invent them. This is the core differentiator vs. "paste a CSV into ChatGPT."

Starter rule set (expand during build):

1. **Meta/TikTok/Pinterest/Snap fatigue:** IF frequency > 4 AND CTR trending down week-over-week → flag "creative fatigue," recommend creative refresh.
2. **Search CTR underperformance:** IF Google Search CTR < 3% for the campaign's stated objective → flag "underperforming ad copy or targeting mismatch."
3. **Social CTR underperformance:** IF Meta/TikTok/Pinterest/Snap CTR < 0.9% → flag "creative or audience issue."
4. **CPA spike:** IF CPA increases >20% week-over-week on any paid channel → flag and cross-check against frequency/CTR to suggest likely cause.
5. **Email list dilution:** IF open_rate drops AND send volume increased in the same period → flag "possible list quality dilution from recent paid-driven signups," cross-reference against paid channel spend increases in the same window.
6. **Cross-channel signal:** IF paid social spend/conversions spike AND email engagement from new subscribers drops within 1-2 weeks → flag "acquisition-to-activation gap," recommend welcome series review.
7. **Programmatic viewability:** IF viewability_rate < 50% → flag "inventory quality issue," recommend placement review.
8. **Search impression share:** IF search_impression_share drops >10 points WoW with flat spend → flag "increased competition or Quality Score drop."
9. **Unsubscribe spike:** IF unsubscribe rate > 2x trailing average → flag "content/frequency mismatch," recommend send cadence review.
10. **Materiality threshold:** Only surface flags where the underlying metric move affects >15% of spend-weighted outcomes — prevents noise, keeps output "curated, not chatty."

---

## RAG Layer (Platform Documentation Grounding)

Purpose: ground AI-generated insight narration in each platform's actual published benchmarks/best practices, not general model knowledge (which may be outdated or generic).

**Sources to ingest (pull relevant sections only, not full certification courses):**
- Meta Blueprint — frequency/fatigue guidance, relevance/quality ranking docs
- Google Skillshop — Quality Score, impression share, CTR benchmark guidance
- Pinterest Business / Academy — ad performance benchmarks
- TikTok For Business — creative fatigue and frequency guidance
- Snapchat for Business — ad benchmarks
- Mailchimp — open rate / CTOR / list health benchmarks (reuse existing RAG corpus from Brand Voice project if overlapping)

**Pipeline:** same as Mailchimp Brand Voice Assistant — chunk docs → embed → store in Pinecone → retrieve relevant chunks at insight-generation time → Claude synthesizes rule output + retrieved doc context into narrative insight with citation of which guidance informed it.

---

## Insight & Next-Steps Output Layer

Each triggered rule becomes a structured insight card with:
- **What happened** (plain-language description of the flagged pattern)
- **Why it matters** (business impact, cross-channel connection if applicable)
- **Recommended next step** (specific, actionable — not generic "optimize your campaign")
- **Source grounding** (which platform guidance informed the recommendation, from RAG layer)

This "recommended next step" layer is the key differentiator — most dashboards stop at "what happened."

---

## Dashboard Layout (Wireframe Description)

1. **Top summary bar:** total spend, blended CPA, blended ROAS, total conversions — all channels combined
2. **Channel breakdown section:** per-channel cards (spend, CTR, CPA, trend arrows)
3. **Insight feed (main panel):** prioritized list of triggered rules as insight cards (highest materiality first)
4. **Trend charts:** spend and CPA over time per channel (line charts), channel mix (pie/bar)
5. **Recommended actions panel:** consolidated list of next steps across all triggered insights, sortable by priority

---

## Data Source for Build/Demo
Use a hybrid approach:
- Pull real/realistic sample data (Kaggle marketing datasets, Google Analytics Demo Account/GA4 sample data) for the normalization and cleaning layer — demonstrates handling messy real-world exports
- If the real data tells a flat/boring story, layer in 1-2 synthetic anomalies (e.g., a deliberate frequency-driven fatigue spike, a deliberate email dilution pattern) so the insight engine has something meaningful to catch for demo purposes

---

## Portfolio Positioning
Pitch line for resume/interviews: *"Built a cross-channel marketing performance system that normalizes exports from 6+ ad platforms and email, applies a domain-expert rules engine grounded in each platform's own official guidance via RAG, and generates prioritized, actionable insights — replacing manual weekly reporting with an auditable, repeatable pipeline."*

Differentiators to emphasize over "just use ChatGPT":
- Repeatable pipeline vs. one-off prompt
- Consistent rule-based thresholds vs. whatever the model emphasizes that session
- RAG-grounded in official platform docs, not general training knowledge
- Auditable — every insight traces back to a specific rule + source document
