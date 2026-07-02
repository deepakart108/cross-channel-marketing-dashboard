"""Load and normalize every raw export in a directory into one unified DataFrame.

Filenames map to a channel key by prefix — this matches how data/sample_exports/
is laid out and is the convention new exports should follow when dropped in.
"""

from pathlib import Path

import pandas as pd

from ingest.normalize import normalize_file

FILENAME_TO_CHANNEL = {
    "meta_ads_export": "meta",
    "google_search_export": "google_search",
    "tiktok_ads_export": "tiktok",
    "pinterest_ads_export": "pinterest",
    "snapchat_ads_export": "snapchat",
    "programmatic_dsp_export": "programmatic",
    "mailchimp_export": "email",
}

DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data" / "sample_exports"


def load_directory(data_dir=DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Normalize every recognized export file in data_dir and concatenate the results."""
    data_dir = Path(data_dir)
    frames = []
    for path in sorted(data_dir.iterdir()):
        channel = FILENAME_TO_CHANNEL.get(path.stem)
        if channel is None:
            continue
        frames.append(normalize_file(path, channel))
    return pd.concat(frames, ignore_index=True)
