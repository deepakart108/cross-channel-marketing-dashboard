"""Aggregate the unified DataFrame into the numbers the dashboard renders:
summary bar stats, per-channel breakdown cards, and Plotly trend charts.
"""

import pandas as pd
import plotly.graph_objects as go

from ingest.load import load_directory

CHART_COLORS = {
    "meta": "#6c63ff", "google_search": "#4285F4", "tiktok": "#25F4EE",
    "pinterest": "#E60023", "snapchat": "#FFFC00", "mailchimp": "#FFE01B",
    "Generic DSP": "#8b8fa8",
}


def load_data() -> pd.DataFrame:
    df = load_directory()
    df["period_start"] = pd.to_datetime(df["date_range"].str[:10])
    return df


def summary_stats(df: pd.DataFrame) -> dict:
    total_spend = df["spend"].sum(skipna=True)
    total_conversions = df["conversions"].sum(skipna=True)
    blended_cpa = total_spend / total_conversions if total_conversions else 0

    # Only Meta reports ROAS in this schema (real per-platform exports vary in
    # revenue attribution support) — blend it spend-weighted over the rows
    # that report it, rather than pretending every channel has a revenue figure.
    roas_rows = df[df["roas"].notna()]
    blended_roas = (
        (roas_rows["spend"] * roas_rows["roas"]).sum() / roas_rows["spend"].sum()
        if not roas_rows.empty else 0
    )

    return {
        "total_spend": total_spend,
        "blended_cpa": blended_cpa,
        "blended_roas": blended_roas,
        "total_conversions": total_conversions,
    }


def channel_breakdown(df: pd.DataFrame) -> list[dict]:
    cards = []
    for platform, group in df.groupby("platform"):
        group = group.sort_values("period_start")
        is_email = platform == "mailchimp"

        if is_email:
            weekly = group.groupby("period_start")["open_rate"].mean()
            metric_label, metric_fmt = "Open Rate", "{:.1f}%"
            higher_is_better = True
        else:
            weekly_spend = group.groupby("period_start")["spend"].sum()
            weekly_conv = group.groupby("period_start")["conversions"].sum()
            weekly = weekly_spend / weekly_conv.replace(0, pd.NA)
            metric_label, metric_fmt = "CPA", "${:,.2f}"
            higher_is_better = False

        trend = "flat"
        if len(weekly) >= 2 and pd.notna(weekly.iloc[-1]) and pd.notna(weekly.iloc[-2]):
            if weekly.iloc[-1] > weekly.iloc[-2]:
                trend = "up"
            elif weekly.iloc[-1] < weekly.iloc[-2]:
                trend = "down"
        trend_good = trend == "flat" or (trend == "up") == higher_is_better

        cards.append({
            "platform": platform,
            "channel": group["channel"].iloc[0],
            "spend": group["spend"].sum(skipna=True),
            "ctr": group["ctr"].mean(skipna=True) if not is_email else None,
            "metric_label": metric_label,
            "metric_value": metric_fmt.format(weekly.iloc[-1]) if len(weekly) and pd.notna(weekly.iloc[-1]) else "—",
            "trend": trend,
            "trend_good": trend_good,
            "color": CHART_COLORS.get(platform, "#8b8fa8"),
        })
    return sorted(cards, key=lambda c: c["spend"], reverse=True)


_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e4e6f1", family="-apple-system, sans-serif"),
    margin=dict(l=40, r=20, t=20, b=40),
    legend=dict(orientation="h", y=-0.2),
)
_AXIS = dict(gridcolor="#2a2d3e", zerolinecolor="#2a2d3e")
_DATE_AXIS = dict(**_AXIS, tickformat="%b %d", dtick=7 * 24 * 60 * 60 * 1000)


def spend_trend_chart(df: pd.DataFrame) -> dict:
    fig = go.Figure()
    for platform, group in df.groupby("platform"):
        if platform == "mailchimp":
            continue  # email has no spend column populated — would just plot a flat 0 line
        weekly = group.groupby("period_start")["spend"].sum().sort_index()
        fig.add_trace(go.Scatter(
            x=weekly.index, y=weekly.values, mode="lines+markers", name=platform,
            line=dict(color=CHART_COLORS.get(platform, "#8b8fa8")),
        ))
    fig.update_layout(**_LAYOUT, xaxis=_DATE_AXIS, yaxis=dict(**_AXIS, title="Spend ($)"))
    return json_safe(fig)


def cpa_trend_chart(df: pd.DataFrame) -> dict:
    fig = go.Figure()
    for platform, group in df.groupby("platform"):
        if platform == "mailchimp":
            continue
        weekly_spend = group.groupby("period_start")["spend"].sum()
        weekly_conv = group.groupby("period_start")["conversions"].sum()
        weekly_cpa = (weekly_spend / weekly_conv.replace(0, pd.NA)).sort_index()
        fig.add_trace(go.Scatter(
            x=weekly_cpa.index, y=weekly_cpa.values, mode="lines+markers", name=platform,
            line=dict(color=CHART_COLORS.get(platform, "#8b8fa8")),
        ))
    fig.update_layout(**_LAYOUT, xaxis=_DATE_AXIS, yaxis=dict(**_AXIS, title="CPA ($)"))
    return json_safe(fig)


def channel_mix_chart(df: pd.DataFrame) -> dict:
    totals = df.groupby("platform")["spend"].sum(numeric_only=True).sort_values(ascending=False)
    fig = go.Figure(go.Bar(
        x=totals.index, y=totals.values,
        marker_color=[CHART_COLORS.get(p, "#8b8fa8") for p in totals.index],
    ))
    fig.update_layout(**_LAYOUT, xaxis=_AXIS, yaxis=dict(**_AXIS, title="Total Spend ($)"))
    return json_safe(fig)


def json_safe(fig: go.Figure) -> dict:
    import json
    return json.loads(fig.to_json())
