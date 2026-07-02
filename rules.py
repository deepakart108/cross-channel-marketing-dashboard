"""Domain-expert rules engine.

Each rule is a plain function: prepped unified DataFrame -> list[Flag].
A rule returns a Flag for every row that trips its threshold; the AI layer
(rag.py) only narrates flags this module already produced — it never decides
which thresholds matter.
"""

from dataclasses import dataclass, field

import pandas as pd

from ingest.load import load_directory

SOCIAL_PLATFORMS = {"meta", "tiktok", "pinterest", "snapchat"}
MATERIALITY_THRESHOLD = 0.15

# Columns that need a "previous week, same campaign" value for WoW comparisons.
_SHIFT_COLUMNS = ["ctr", "cpa", "spend", "sends", "open_rate", "search_impression_share"]


@dataclass
class Flag:
    rule_id: str
    channel: str
    platform: str
    campaign_name: str
    period: str
    what_happened: str
    materiality: float = 0.0
    metrics: dict = field(default_factory=dict)


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["period_start"] = pd.to_datetime(df["date_range"].str[:10])
    df = df.sort_values(["platform", "campaign_name", "period_start"]).reset_index(drop=True)
    grouped = df.groupby(["platform", "campaign_name"], group_keys=False)
    for col in _SHIFT_COLUMNS:
        df[f"prev_{col}"] = grouped[col].shift(1)
    return df


def rule_fatigue(df):
    """1. frequency > 4 AND CTR declining week-over-week -> creative fatigue."""
    hits = df[df["platform"].isin(SOCIAL_PLATFORMS) & (df["frequency"] > 4) & (df["ctr"] < df["prev_ctr"])]
    return [
        Flag(
            rule_id="fatigue", channel=row.channel, platform=row.platform,
            campaign_name=row.campaign_name, period=row.date_range,
            what_happened=(
                f"Frequency reached {row.frequency:.1f} while CTR fell from "
                f"{row.prev_ctr:.2f}% to {row.ctr:.2f}% — creative fatigue."
            ),
            metrics={"frequency": row.frequency, "ctr": row.ctr, "prev_ctr": row.prev_ctr},
        )
        for row in hits.itertuples()
    ]


def rule_search_ctr_underperformance(df):
    """2. Google Search CTR < 3% -> underperforming ad copy or targeting mismatch."""
    hits = df[(df["platform"] == "google_search") & (df["ctr"] < 3.0)]
    return [
        Flag(
            rule_id="search_ctr_underperformance", channel=row.channel, platform=row.platform,
            campaign_name=row.campaign_name, period=row.date_range,
            what_happened=f"Search CTR is {row.ctr:.2f}%, below the 3% benchmark.",
            metrics={"ctr": row.ctr},
        )
        for row in hits.itertuples()
    ]


def rule_social_ctr_underperformance(df):
    """3. Meta/TikTok/Pinterest/Snap CTR < 0.9% -> creative or audience issue."""
    hits = df[df["platform"].isin(SOCIAL_PLATFORMS) & (df["ctr"] < 0.9)]
    return [
        Flag(
            rule_id="social_ctr_underperformance", channel=row.channel, platform=row.platform,
            campaign_name=row.campaign_name, period=row.date_range,
            what_happened=f"{row.platform.title()} CTR is {row.ctr:.2f}%, below the 0.9% floor.",
            metrics={"ctr": row.ctr},
        )
        for row in hits.itertuples()
    ]


def rule_cpa_spike(df):
    """4. CPA up > 20% WoW on any paid channel -> flag, cross-check freq/CTR for likely cause."""
    paid = df[df["cpa"].notna() & df["prev_cpa"].notna()].copy()
    paid["pct_change"] = (paid["cpa"] - paid["prev_cpa"]) / paid["prev_cpa"]
    hits = paid[paid["pct_change"] > 0.20]
    flags = []
    for row in hits.itertuples():
        causes = []
        if pd.notna(row.frequency) and row.frequency > 4:
            causes.append("rising frequency")
        if pd.notna(row.prev_ctr) and pd.notna(row.ctr) and row.ctr < row.prev_ctr:
            causes.append("declining CTR")
        cause_text = f" (alongside {', '.join(causes)})" if causes else ""
        flags.append(Flag(
            rule_id="cpa_spike", channel=row.channel, platform=row.platform,
            campaign_name=row.campaign_name, period=row.date_range,
            what_happened=(
                f"CPA rose {row.pct_change * 100:.0f}% week-over-week, from "
                f"${row.prev_cpa:.2f} to ${row.cpa:.2f}{cause_text}."
            ),
            metrics={"cpa": row.cpa, "prev_cpa": row.prev_cpa, "pct_change": row.pct_change},
        ))
    return flags


def rule_email_list_dilution(df):
    """5. Send volume up + open rate down in the same period -> possible list dilution."""
    hits = df[
        (df["platform"] == "mailchimp") & df["prev_sends"].notna()
        & (df["sends"] > df["prev_sends"] * 1.1) & (df["open_rate"] < df["prev_open_rate"])
    ]
    return [
        Flag(
            rule_id="email_list_dilution", channel=row.channel, platform=row.platform,
            campaign_name=row.campaign_name, period=row.date_range,
            what_happened=(
                f"Send volume rose from {row.prev_sends:.0f} to {row.sends:.0f} while open rate "
                f"fell from {row.prev_open_rate:.1f}% to {row.open_rate:.1f}% — possible list dilution."
            ),
            metrics={"sends": row.sends, "prev_sends": row.prev_sends, "open_rate": row.open_rate},
        )
        for row in hits.itertuples()
    ]


def rule_cross_channel_acquisition_gap(df):
    """6. Paid social spend spikes, then email open rate drops within 1-2 weeks ->
    acquisition-to-activation gap. There's no subscriber-source column in the unified
    schema, so this approximates "new-subscriber activation" with portfolio-wide paid
    social spend vs. the email channel's open-rate trend.
    """
    social_by_week = df[df["channel"] == "paid_social"].groupby("period_start")["spend"].sum()
    prior = social_by_week.shift(1)
    spike_weeks = set(social_by_week[prior.notna() & (social_by_week > prior * 1.15)].index)

    flags = []
    for row in df[df["platform"] == "mailchimp"].itertuples():
        if pd.isna(row.prev_open_rate) or row.open_rate >= row.prev_open_rate:
            continue
        lookback = {row.period_start - pd.Timedelta(weeks=w) for w in (1, 2)}
        if lookback & spike_weeks:
            flags.append(Flag(
                rule_id="cross_channel_acquisition_gap", channel=row.channel, platform=row.platform,
                campaign_name=row.campaign_name, period=row.date_range,
                what_happened=(
                    "Paid social spend spiked 1-2 weeks prior and email open rate is now "
                    f"declining ({row.prev_open_rate:.1f}% -> {row.open_rate:.1f}%) — possible "
                    "acquisition-to-activation gap."
                ),
                metrics={"open_rate": row.open_rate, "prev_open_rate": row.prev_open_rate},
            ))
    return flags


def rule_programmatic_viewability(df):
    """7. viewability_rate < 50% -> inventory quality issue."""
    hits = df[(df["channel"] == "programmatic") & (df["viewability_rate"] < 0.50)]
    return [
        Flag(
            rule_id="programmatic_viewability", channel=row.channel, platform=row.platform,
            campaign_name=row.campaign_name, period=row.date_range,
            what_happened=f"Viewability is {row.viewability_rate * 100:.0f}%, below the 50% floor.",
            metrics={"viewability_rate": row.viewability_rate},
        )
        for row in hits.itertuples()
    ]


def rule_search_impression_share_drop(df):
    """8. Search impression share drops > 10pts WoW with flat spend -> more
    competition or a Quality Score drop.
    """
    hits = df[
        (df["platform"] == "google_search")
        & df["prev_search_impression_share"].notna()
        & ((df["prev_search_impression_share"] - df["search_impression_share"]) > 10)
        & df["prev_spend"].notna()
        & ((df["spend"] - df["prev_spend"]).abs() / df["prev_spend"] < 0.05)
    ]
    return [
        Flag(
            rule_id="search_impression_share_drop", channel=row.channel, platform=row.platform,
            campaign_name=row.campaign_name, period=row.date_range,
            what_happened=(
                f"Search impression share dropped from {row.prev_search_impression_share:.1f}% "
                f"to {row.search_impression_share:.1f}% on flat spend — likely rising competition "
                "or a Quality Score drop."
            ),
            metrics={
                "search_impression_share": row.search_impression_share,
                "prev_search_impression_share": row.prev_search_impression_share,
            },
        )
        for row in hits.itertuples()
    ]


def rule_unsubscribe_spike(df):
    """9. Unsubscribe rate > 2x trailing average -> content/frequency mismatch."""
    mail = df[df["platform"] == "mailchimp"].copy()
    mail["trailing_avg_unsub"] = mail["unsubscribes"].shift(1).expanding().mean()
    hits = mail[mail["trailing_avg_unsub"].notna() & (mail["unsubscribes"] > mail["trailing_avg_unsub"] * 2)]
    return [
        Flag(
            rule_id="unsubscribe_spike", channel=row.channel, platform=row.platform,
            campaign_name=row.campaign_name, period=row.date_range,
            what_happened=(
                f"Unsubscribes hit {row.unsubscribes:.0f}, over 2x the trailing average of "
                f"{row.trailing_avg_unsub:.0f} — likely a content or send-cadence mismatch."
            ),
            metrics={"unsubscribes": row.unsubscribes, "trailing_avg_unsub": row.trailing_avg_unsub},
        )
        for row in hits.itertuples()
    ]


RULES = [
    rule_fatigue,
    rule_search_ctr_underperformance,
    rule_social_ctr_underperformance,
    rule_cpa_spike,
    rule_email_list_dilution,
    rule_cross_channel_acquisition_gap,
    rule_programmatic_viewability,
    rule_search_impression_share_drop,
    rule_unsubscribe_spike,
]


def _apply_materiality(flags: list[Flag], df: pd.DataFrame) -> list[Flag]:
    """10. Only surface flags whose campaign represents > 15% of its platform's
    total spend (sends, for email) across the ingested window — keeps the feed
    to campaigns that actually move the needle rather than every minor blip.
    """
    kept = []
    for platform, group in df.groupby("platform"):
        volume_col = "sends" if platform == "mailchimp" else "spend"
        totals = group.groupby("campaign_name")[volume_col].sum()
        channel_total = totals.sum()
        for flag in [f for f in flags if f.platform == platform]:
            materiality = totals.get(flag.campaign_name, 0) / channel_total if channel_total else 0.0
            flag.materiality = round(materiality, 3)
            if materiality > MATERIALITY_THRESHOLD:
                kept.append(flag)
    return kept


def run_rules(unified_df: pd.DataFrame = None) -> list[Flag]:
    df = _prep(unified_df if unified_df is not None else load_directory())
    raw_flags = [flag for rule in RULES for flag in rule(df)]
    flags = _apply_materiality(raw_flags, df)
    return sorted(flags, key=lambda f: f.materiality, reverse=True)


if __name__ == "__main__":
    for flag in run_rules():
        print(
            f"[{flag.rule_id}] {flag.platform}/{flag.campaign_name} ({flag.period}) "
            f"materiality={flag.materiality}\n  {flag.what_happened}\n"
        )
