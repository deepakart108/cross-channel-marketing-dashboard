"""Generate realistic per-platform sample exports for the demo.

Produces one CSV (or XLSX) per channel under data/sample_exports/, using each
platform's actual export column names/format. Metrics are synthetic but
plausible, with a handful of deliberate anomalies baked in so the rules
engine (rules.py) has real signals to catch:

  - Meta:      creative fatigue — frequency climbs > 4, CTR declines (weeks 6-8)
  - Google:    search impression share drops > 10pts WoW with flat spend (week 7)
  - TikTok:    CPA spike > 20% WoW (week 6)
  - Pinterest: CTR underperformance < 0.9% (weeks 5-8, one campaign)
  - Snapchat:  no anomaly — clean baseline for contrast
  - Programmatic: viewability < 50% (one placement, weeks 4-8)
  - Email:     list dilution — send volume up + open rate down (weeks 6-8),
               coinciding with the Meta/TikTok spend increase (cross-channel
               signal), plus an unsubscribe spike in week 7

Run: python3 data/generate_sample_data.py
"""

import datetime
import random
from pathlib import Path

import pandas as pd

random.seed(42)

OUT_DIR = Path(__file__).parent / "sample_exports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_WEEKS = 8
START = datetime.date(2026, 5, 4)  # 8 Mondays leading up to today (2026-07-01)
WEEK_STARTS = [START + datetime.timedelta(weeks=i) for i in range(N_WEEKS)]

# Portfolio-wide paid social spend spike (week index 4, 2026-06-01), applied across
# every social platform so the aggregate crosses the 15% WoW threshold. Feeds the
# acquisition-to-activation-gap story: this spike precedes the email dilution/open-rate
# decline that starts at week index 5.
SOCIAL_SPEND_SPIKE_WEEK = 4
SOCIAL_SPEND_SPIKE_MULTIPLIER = 1.35


def apply_spend_spike(spend, week_index):
    if week_index == SOCIAL_SPEND_SPIKE_WEEK:
        return spend * SOCIAL_SPEND_SPIKE_MULTIPLIER
    return spend


def week_range(i):
    start = WEEK_STARTS[i]
    end = start + datetime.timedelta(days=6)
    return start, end


def jitter(base, pct=0.08):
    return base * (1 + random.uniform(-pct, pct))


# ---------------------------------------------------------------------------
# Meta Ads Manager
# ---------------------------------------------------------------------------
def gen_meta():
    campaigns = ["Prospecting - Broad", "Retargeting - Core Audience", "UGC - Video Creative"]
    rows = []
    for camp in campaigns:
        base_spend = {"Prospecting - Broad": 3200, "Retargeting - Core Audience": 1800, "UGC - Video Creative": 2400}[camp]
        for i in range(N_WEEKS):
            start, end = week_range(i)
            spend = apply_spend_spike(jitter(base_spend), i)
            impressions = int(spend / 0.012)
            frequency = round(jitter(2.1, 0.1), 2)
            ctr = round(jitter(1.4, 0.1), 2)

            # Inject fatigue: UGC creative frequency climbs, CTR decays, weeks 6-8 (index 5-7)
            if camp == "UGC - Video Creative" and i >= 5:
                frequency = round(3.6 + (i - 4) * 0.6, 2)  # 4.2, 4.8, 5.4
                ctr = round(1.3 - (i - 4) * 0.25, 2)       # declining CTR

            clicks = int(impressions * ctr / 100)
            results = int(clicks * random.uniform(0.05, 0.09))
            cost_per_result = round(spend / max(results, 1), 2)
            roas = round(jitter(2.8, 0.15), 2)

            rows.append({
                "Campaign Name": camp,
                "Reporting Starts": start.isoformat(),
                "Reporting Ends": end.isoformat(),
                "Amount Spent (USD)": round(spend, 2),
                "Impressions": impressions,
                "Reach": int(impressions / frequency),
                "Frequency": frequency,
                "Link Clicks": clicks,
                "CTR (Link Click-Through Rate)": ctr,
                "Results": results,
                "Cost per Result": cost_per_result,
                "Purchase ROAS (Return on Ad Spend)": roas,
            })
    pd.DataFrame(rows).to_csv(OUT_DIR / "meta_ads_export.csv", index=False)


# ---------------------------------------------------------------------------
# Google Ads (Search)
# ---------------------------------------------------------------------------
def gen_google_search():
    campaigns = ["Brand - Exact Match", "Non-Brand - Category Terms", "Competitor Conquesting"]
    rows = []
    for camp in campaigns:
        base_spend = {"Brand - Exact Match": 900, "Non-Brand - Category Terms": 4100, "Competitor Conquesting": 1500}[camp]
        impr_share = 68.0
        for i in range(N_WEEKS):
            start, end = week_range(i)
            spend = jitter(base_spend, 0.05)
            clicks = int(spend / jitter(2.10))
            impressions = int(clicks / jitter(0.055))
            ctr = round(clicks / impressions * 100, 2)

            # Inject: search CTR underperformance < 3%, Competitor Conquesting, weeks 6-8 (index 5-7)
            # — conquesting terms/copy resonate less than owned brand/category terms.
            if camp == "Competitor Conquesting" and i >= 5:
                ctr = round(random.uniform(1.8, 2.6), 2)
                clicks = int(impressions * ctr / 100)

            conversions = int(clicks * random.uniform(0.06, 0.1))
            cost_per_conv = round(spend / max(conversions, 1), 2)
            conv_rate = round(conversions / clicks * 100, 2)

            # Inject: impression share drop > 10pts WoW with flat spend, week 7 (index 6)
            if camp == "Non-Brand - Category Terms" and i == 6:
                impr_share = round(impr_share - 14.5, 1)
                spend = base_spend  # flat spend, no obvious cause from budget change
            elif camp == "Non-Brand - Category Terms":
                impr_share = round(jitter(68.0, 0.03), 1)
            else:
                impr_share = round(jitter(74.0, 0.04), 1)

            rows.append({
                "Campaign": camp,
                "Week Start": start.isoformat(),
                "Week End": end.isoformat(),
                "Cost": round(spend, 2),
                "Clicks": clicks,
                "Impr.": impressions,
                "CTR": ctr,
                "Conversions": conversions,
                "Cost / conv.": cost_per_conv,
                "Conv. rate": conv_rate,
                "Search impr. share": impr_share,
            })
    pd.DataFrame(rows).to_csv(OUT_DIR / "google_search_export.csv", index=False)


# ---------------------------------------------------------------------------
# TikTok Ads Manager
# ---------------------------------------------------------------------------
def gen_tiktok():
    campaigns = ["Spark Ads - Creator Partnership", "In-Feed - Core Prospecting"]
    rows = []
    for camp in campaigns:
        base_spend = {"Spark Ads - Creator Partnership": 2600, "In-Feed - Core Prospecting": 3400}[camp]
        prev_cpa = None
        for i in range(N_WEEKS):
            start, end = week_range(i)
            spend = apply_spend_spike(jitter(base_spend, 0.06), i)
            frequency = round(jitter(2.3, 0.1), 2)
            ctr = round(jitter(1.1, 0.1), 2)
            impressions = int(spend / 0.009)
            clicks = int(impressions * ctr / 100)
            conversions = int(clicks * random.uniform(0.04, 0.07))

            # Inject: CPA spike > 20% WoW, week 6 (index 5), In-Feed campaign
            if camp == "In-Feed - Core Prospecting" and i == 5:
                conversions = int(conversions * 0.55)  # same spend, fewer conversions -> CPA spike

            cpa = round(spend / max(conversions, 1), 2)
            prev_cpa = cpa

            rows.append({
                "Campaign Name": camp,
                "By Day (Week Start)": start.isoformat(),
                "By Day (Week End)": end.isoformat(),
                "Cost": round(spend, 2),
                "Impressions": impressions,
                "Clicks": clicks,
                "CTR": ctr,
                "Conversion": conversions,
                "Cost per Conversion": cpa,
                "Frequency": frequency,
            })
    pd.DataFrame(rows).to_csv(OUT_DIR / "tiktok_ads_export.csv", index=False)


# ---------------------------------------------------------------------------
# Pinterest Ads Manager
# ---------------------------------------------------------------------------
def gen_pinterest():
    campaigns = ["Idea Pins - Awareness", "Shopping Ads - Catalog Sales"]
    rows = []
    for camp in campaigns:
        base_spend = {"Idea Pins - Awareness": 1400, "Shopping Ads - Catalog Sales": 2100}[camp]
        for i in range(N_WEEKS):
            start, _ = week_range(i)
            spend = apply_spend_spike(jitter(base_spend, 0.07), i)
            frequency = round(jitter(2.0, 0.1), 2)
            impressions = int(spend / 0.007)

            # Inject: CTR underperformance < 0.9%, Idea Pins, weeks 5-8 (index 4-7)
            if camp == "Idea Pins - Awareness" and i >= 4:
                ctr = round(random.uniform(0.55, 0.85), 2)
            else:
                ctr = round(jitter(1.1, 0.1), 2)

            clicks = int(impressions * ctr / 100)
            conversions = int(clicks * random.uniform(0.03, 0.06))
            cpa = round(spend / max(conversions, 1), 2)

            rows.append({
                "Campaign name": camp,
                "Date": start.isoformat(),
                "Spend": round(spend, 2),
                "Impressions": impressions,
                "Clicks": clicks,
                "CTR": ctr,
                "Conversions": conversions,
                "CPA": cpa,
                "Frequency": frequency,
            })
    pd.DataFrame(rows).to_csv(OUT_DIR / "pinterest_ads_export.csv", index=False)


# ---------------------------------------------------------------------------
# Snapchat Ads Manager — clean baseline, no injected anomaly
# ---------------------------------------------------------------------------
def gen_snapchat():
    campaigns = ["Snap Ads - Prospecting", "Story Ads - Retargeting"]
    rows = []
    for camp in campaigns:
        base_spend = {"Snap Ads - Prospecting": 1100, "Story Ads - Retargeting": 800}[camp]
        for i in range(N_WEEKS):
            start, _ = week_range(i)
            spend = apply_spend_spike(jitter(base_spend, 0.08), i)
            frequency = round(jitter(2.4, 0.1), 2)
            impressions = int(spend / 0.01)
            swipe_rate = round(jitter(1.0, 0.12), 2)
            swipes = int(impressions * swipe_rate / 100)
            conversions = int(swipes * random.uniform(0.03, 0.05))
            cpa = round(spend / max(conversions, 1), 2)

            rows.append({
                "Campaign Name": camp,
                "Start Date": start.isoformat(),
                "Spend": round(spend, 2),
                "Impressions": impressions,
                "Swipes": swipes,
                "Swipe Rate": swipe_rate,
                "Conversions": conversions,
                "Cost Per Conversion": cpa,
                "Frequency": frequency,
            })
    pd.DataFrame(rows).to_csv(OUT_DIR / "snapchat_ads_export.csv", index=False)


# ---------------------------------------------------------------------------
# Programmatic / DSP — generic schema
# ---------------------------------------------------------------------------
def gen_programmatic():
    placements = ["Display - Contextual Network", "CTV - Streaming Inventory"]
    rows = []
    for placement in placements:
        base_spend = {"Display - Contextual Network": 2800, "CTV - Streaming Inventory": 3600}[placement]
        for i in range(N_WEEKS):
            start, _ = week_range(i)
            spend = jitter(base_spend, 0.06)
            impressions = int(spend / 0.006)
            ctr = round(jitter(0.35, 0.15), 2)
            clicks = int(impressions * ctr / 100)
            conversions = int(clicks * random.uniform(0.02, 0.05))
            cpa = round(spend / max(conversions, 1), 2)

            # Inject: viewability < 50%, Display placement, weeks 4-8 (index 3-7)
            if placement == "Display - Contextual Network" and i >= 3:
                viewability = round(random.uniform(0.38, 0.47), 2)
            else:
                viewability = round(jitter(0.68, 0.08), 2)

            rows.append({
                "Campaign": placement,
                "Date": start.isoformat(),
                "DSP": "Generic DSP",
                "Spend": round(spend, 2),
                "Impressions": impressions,
                "Clicks": clicks,
                "CTR": ctr,
                "Viewable Impressions": int(impressions * viewability),
                "Viewability Rate": viewability,
                "Conversions": conversions,
                "CPA": cpa,
            })
    pd.DataFrame(rows).to_excel(OUT_DIR / "programmatic_dsp_export.xlsx", index=False)


# ---------------------------------------------------------------------------
# Mailchimp — email
# ---------------------------------------------------------------------------
def gen_email():
    rows = []
    base_sends = 42000
    base_open_rate = 24.5
    for i in range(N_WEEKS):
        start, _ = week_range(i)
        sends = base_sends
        open_rate = base_open_rate
        unsub_rate = 0.15

        # Inject: list dilution — send volume up + open rate down, weeks 6-8 (index 5-7),
        # coinciding with the Meta/TikTok spend increases used for other channels' anomalies.
        if i >= 5:
            sends = int(base_sends * (1 + 0.35 * (i - 4)))
            open_rate = round(base_open_rate - 3.2 * (i - 4), 1)
        else:
            sends = int(jitter(base_sends, 0.05))
            open_rate = round(jitter(base_open_rate, 0.05), 1)

        # Inject: unsubscribe spike (> 2x trailing average) in week 7 (index 6)
        if i == 6:
            unsub_rate = 0.42
        else:
            unsub_rate = round(jitter(0.15, 0.2), 2)

        opens = int(sends * open_rate / 100)
        click_rate = round(jitter(2.8, 0.1), 2)
        clicks = int(sends * click_rate / 100)
        ctor = round(clicks / opens * 100, 2)
        unsubscribes = int(sends * unsub_rate / 100)

        rows.append({
            "Campaign Title": "Weekly Newsletter",
            "Send Time": start.isoformat(),
            "Emails Sent": sends,
            "Opens": opens,
            "Open Rate": open_rate,
            "Clicks": clicks,
            "Click Rate": click_rate,
            "CTOR": ctor,
            "Unsubscribes": unsubscribes,
        })
    pd.DataFrame(rows).to_csv(OUT_DIR / "mailchimp_export.csv", index=False)


if __name__ == "__main__":
    gen_meta()
    gen_google_search()
    gen_tiktok()
    gen_pinterest()
    gen_snapchat()
    gen_programmatic()
    gen_email()
    print(f"Wrote sample exports to {OUT_DIR}")
