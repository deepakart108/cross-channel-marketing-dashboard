"""Per-channel normalizers: map a raw platform export to the unified schema.

Each function takes a raw pandas DataFrame (as read from the platform's CSV/Excel
export) and returns a DataFrame matching ingest.schema.UNIFIED_COLUMNS.
"""

import pandas as pd

from ingest.schema import UNIFIED_COLUMNS


def _to_unified(rows: pd.DataFrame) -> pd.DataFrame:
    return rows.reindex(columns=UNIFIED_COLUMNS)


def _date_range(start, end=None) -> str:
    start = str(start)
    return start if end is None else f"{start} to {end}"


def normalize_meta(raw: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame({
        "channel": "paid_social",
        "platform": "meta",
        "campaign_name": raw["Campaign Name"],
        "date_range": [
            _date_range(s, e) for s, e in zip(raw["Reporting Starts"], raw["Reporting Ends"])
        ],
        "spend": raw["Amount Spent (USD)"],
        "impressions": raw["Impressions"],
        "clicks": raw["Link Clicks"],
        "ctr": raw["CTR (Link Click-Through Rate)"],
        "conversions": raw["Results"],
        "cpa": raw["Cost per Result"],
        "roas": raw["Purchase ROAS (Return on Ad Spend)"],
        "frequency": raw["Frequency"],
    })
    return _to_unified(rows)


def normalize_google_search(raw: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame({
        "channel": "paid_search",
        "platform": "google_search",
        "campaign_name": raw["Campaign"],
        "date_range": [
            _date_range(s, e) for s, e in zip(raw["Week Start"], raw["Week End"])
        ],
        "spend": raw["Cost"],
        "impressions": raw["Impr."],
        "clicks": raw["Clicks"],
        "ctr": raw["CTR"],
        "conversions": raw["Conversions"],
        "cpa": raw["Cost / conv."],
        "search_impression_share": raw["Search impr. share"],
    })
    return _to_unified(rows)


def normalize_tiktok(raw: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame({
        "channel": "paid_social",
        "platform": "tiktok",
        "campaign_name": raw["Campaign Name"],
        "date_range": [
            _date_range(s, e)
            for s, e in zip(raw["By Day (Week Start)"], raw["By Day (Week End)"])
        ],
        "spend": raw["Cost"],
        "impressions": raw["Impressions"],
        "clicks": raw["Clicks"],
        "ctr": raw["CTR"],
        "conversions": raw["Conversion"],
        "cpa": raw["Cost per Conversion"],
        "frequency": raw["Frequency"],
    })
    return _to_unified(rows)


def normalize_pinterest(raw: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame({
        "channel": "paid_social",
        "platform": "pinterest",
        "campaign_name": raw["Campaign name"],
        "date_range": [_date_range(d) for d in raw["Date"]],
        "spend": raw["Spend"],
        "impressions": raw["Impressions"],
        "clicks": raw["Clicks"],
        "ctr": raw["CTR"],
        "conversions": raw["Conversions"],
        "cpa": raw["CPA"],
        "frequency": raw["Frequency"],
    })
    return _to_unified(rows)


def normalize_snapchat(raw: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame({
        "channel": "paid_social",
        "platform": "snapchat",
        "campaign_name": raw["Campaign Name"],
        "date_range": [_date_range(d) for d in raw["Start Date"]],
        "spend": raw["Spend"],
        "impressions": raw["Impressions"],
        "clicks": raw["Swipes"],
        "ctr": raw["Swipe Rate"],
        "conversions": raw["Conversions"],
        "cpa": raw["Cost Per Conversion"],
        "frequency": raw["Frequency"],
    })
    return _to_unified(rows)


def normalize_programmatic(raw: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame({
        "channel": "programmatic",
        "platform": raw["DSP"],
        "campaign_name": raw["Campaign"],
        "date_range": [_date_range(d) for d in raw["Date"]],
        "spend": raw["Spend"],
        "impressions": raw["Impressions"],
        "clicks": raw["Clicks"],
        "ctr": raw["CTR"],
        "conversions": raw["Conversions"],
        "cpa": raw["CPA"],
        "viewability_rate": raw["Viewability Rate"],
    })
    return _to_unified(rows)


def normalize_email(raw: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame({
        "channel": "email",
        "platform": "mailchimp",
        "campaign_name": raw["Campaign Title"],
        "date_range": [_date_range(d) for d in raw["Send Time"]],
        "clicks": raw["Clicks"],
        "sends": raw["Emails Sent"],
        "opens": raw["Opens"],
        "open_rate": raw["Open Rate"],
        "ctor": raw["CTOR"],
        "unsubscribes": raw["Unsubscribes"],
    })
    return _to_unified(rows)


NORMALIZERS = {
    "meta": normalize_meta,
    "google_search": normalize_google_search,
    "tiktok": normalize_tiktok,
    "pinterest": normalize_pinterest,
    "snapchat": normalize_snapchat,
    "programmatic": normalize_programmatic,
    "email": normalize_email,
}


def read_export(path) -> pd.DataFrame:
    """Read a raw platform export (.csv or .xlsx) into a DataFrame."""
    path = str(path)
    if path.endswith(".xlsx"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def normalize_file(path, channel: str) -> pd.DataFrame:
    """Read + normalize a single raw export file for a given channel key."""
    raw = read_export(path)
    return NORMALIZERS[channel](raw)
