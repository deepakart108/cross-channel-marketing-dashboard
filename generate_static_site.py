"""Run the full pipeline once and render the dashboard to a static HTML file
for GitHub Pages (docs/index.html). No server, no live API calls at view
time — Plotly renders the embedded chart JSON entirely client-side.

Run: python3 generate_static_site.py
"""

import datetime
import json
from pathlib import Path

from dotenv import load_dotenv
from markupsafe import Markup

from pipeline import build_dashboard
from templates import DASHBOARD_TEMPLATE, make_environment

load_dotenv()

OUT_PATH = Path(__file__).parent / "docs" / "index.html"


def main():
    OUT_PATH.parent.mkdir(exist_ok=True)
    data = build_dashboard()

    env = make_environment()
    tmpl = env.from_string(DASHBOARD_TEMPLATE)
    html = tmpl.render(
        live=False,
        generated_at=datetime.date.today().isoformat(),
        summary=data["summary"],
        channels=data["channels"],
        insights=data["insights"],
        charts_json=Markup(json.dumps(data["charts"])),
    )

    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"\nWrote static dashboard to {OUT_PATH}")


if __name__ == "__main__":
    main()
