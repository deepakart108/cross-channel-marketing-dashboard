"""Flask dashboard for the Cross-Channel Marketing Performance Dashboard.
Run: python3 app.py  →  open http://localhost:5000
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string

load_dotenv()

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cross-Channel Marketing Performance Dashboard</title>
<style>
  :root {
    --bg: #0f1117;
    --card: #1a1d2e;
    --border: #2a2d3e;
    --text: #e4e6f1;
    --muted: #8b8fa8;
    --accent: #6c63ff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 24px; }
  h1 { font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }
  .subtitle { color: var(--muted); font-size: 0.85rem; margin-bottom: 28px; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }
  .grid-2 { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 20px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .card h2 { font-size: 0.95rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 14px; }
  .stat { font-size: 1.8rem; font-weight: 700; }
  .placeholder { color: var(--muted); font-size: 0.9rem; padding: 40px 0; text-align: center; }
</style>
</head>
<body>
  <h1>Cross-Channel Marketing Performance Dashboard</h1>
  <div class="subtitle">Meta &middot; Google Search &middot; TikTok &middot; Pinterest &middot; Snapchat &middot; Programmatic &middot; Mailchimp</div>

  <div class="grid-4">
    <div class="card"><h2>Total Spend</h2><div class="stat">&mdash;</div></div>
    <div class="card"><h2>Blended CPA</h2><div class="stat">&mdash;</div></div>
    <div class="card"><h2>Blended ROAS</h2><div class="stat">&mdash;</div></div>
    <div class="card"><h2>Conversions</h2><div class="stat">&mdash;</div></div>
  </div>

  <div class="grid-2">
    <div class="card">
      <h2>Insight Feed</h2>
      <div class="placeholder">No channel data ingested yet. Drop exports into data/sample_exports/.</div>
    </div>
    <div class="card">
      <h2>Recommended Actions</h2>
      <div class="placeholder">Insights will populate this panel once flags are generated.</div>
    </div>
  </div>

  <div class="card">
    <h2>Channel Breakdown</h2>
    <div class="placeholder">Per-channel cards go here.</div>
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
