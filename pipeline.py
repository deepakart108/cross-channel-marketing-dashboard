"""The full ingest -> rules -> RAG pipeline, run once to produce everything
the dashboard needs. Shared by the local dev server (app.py) and the static
site generator (generate_static_site.py) — there's no live-refresh use case
that needs this to run per-request, so it's just a plain function.
"""

import time

import dashboard_data
from rag import generate_insight, retrieve_context
from rules import run_rules

# How many distinct (rule, campaign) flags get a full RAG insight card. Rules
# fire once per week a condition holds, so the same campaign can appear many
# times — dedupe to one card per campaign/rule and cap the count so the feed
# stays "curated, not chatty" per the spec, rather than one card per week.
MAX_INSIGHTS = 12


def _dedupe_latest(flags):
    """Keep only the most recent occurrence of each (rule, platform, campaign)."""
    best = {}
    for flag in flags:
        key = (flag.rule_id, flag.platform, flag.campaign_name)
        period_start = flag.period[:10]
        if key not in best or period_start > best[key][0]:
            best[key] = (period_start, flag)
    return [flag for _, flag in best.values()]


def build_dashboard():
    df = dashboard_data.load_data()
    flags = _dedupe_latest(run_rules(df))
    flags = sorted(flags, key=lambda f: f.materiality, reverse=True)[:MAX_INSIGHTS]
    print(f"[build] data+rules ready, {len(flags)} flags", flush=True)

    insights = []
    for i, flag in enumerate(flags, 1):
        t0 = time.time()
        try:
            chunks = retrieve_context(flag)
            insights.append(generate_insight(flag, chunks))
            print(f"[build] flag {i}/{len(flags)} ({flag.rule_id}) ok in {time.time() - t0:.1f}s", flush=True)
        except Exception as e:
            insights.append({
                "rule_id": flag.rule_id, "channel": flag.channel, "platform": flag.platform,
                "campaign_name": flag.campaign_name, "period": flag.period,
                "materiality": flag.materiality, "what_happened": flag.what_happened,
                "why_it_matters": "", "recommended_next_step": "",
                "source_grounding": f"(insight generation failed: {e})",
            })
            print(f"[build] flag {i}/{len(flags)} ({flag.rule_id}) FAILED in {time.time() - t0:.1f}s: {e!r}", flush=True)

    return {
        "summary": dashboard_data.summary_stats(df),
        "channels": dashboard_data.channel_breakdown(df),
        "insights": insights,
        "charts": {
            "spend_trend": dashboard_data.spend_trend_chart(df),
            "cpa_trend": dashboard_data.cpa_trend_chart(df),
            "channel_mix": dashboard_data.channel_mix_chart(df),
        },
    }
