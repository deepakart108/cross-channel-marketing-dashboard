"""Per-channel normalizers: map a raw platform export to the unified schema.

Each function takes a raw pandas DataFrame (as read from the platform's CSV/Excel
export) and returns a DataFrame matching ingest.schema.UNIFIED_COLUMNS.
"""

import pandas as pd

from ingest.schema import UNIFIED_COLUMNS


def _to_unified(rows: pd.DataFrame) -> pd.DataFrame:
    return rows.reindex(columns=UNIFIED_COLUMNS)


def normalize_meta(raw: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def normalize_google_search(raw: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def normalize_tiktok(raw: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def normalize_pinterest(raw: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def normalize_snapchat(raw: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def normalize_programmatic(raw: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def normalize_email(raw: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


NORMALIZERS = {
    "meta": normalize_meta,
    "google_search": normalize_google_search,
    "tiktok": normalize_tiktok,
    "pinterest": normalize_pinterest,
    "snapchat": normalize_snapchat,
    "programmatic": normalize_programmatic,
    "email": normalize_email,
}
