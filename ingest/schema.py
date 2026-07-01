"""Unified schema that every channel's raw export gets normalized into."""

# Columns every row must have, regardless of channel.
CORE_COLUMNS = ["channel", "platform", "campaign_name", "date_range"]

# Columns that only apply to some channels — missing values stay NaN.
OPTIONAL_COLUMNS = [
    "spend", "impressions", "clicks", "ctr",
    "conversions", "cpa", "roas",
    "frequency",                          # Meta, TikTok, Pinterest, Snap
    "avg_position", "search_impression_share",  # Google Search
    "viewability_rate",                   # Programmatic
    "sends", "opens", "open_rate", "ctor", "unsubscribes",  # Mailchimp
]

UNIFIED_COLUMNS = CORE_COLUMNS + OPTIONAL_COLUMNS

CHANNELS = [
    "meta", "google_search", "tiktok", "pinterest",
    "snapchat", "programmatic", "email",
]


def empty_frame():
    """Return an empty DataFrame with the unified schema's columns, in order."""
    import pandas as pd
    return pd.DataFrame(columns=UNIFIED_COLUMNS)
