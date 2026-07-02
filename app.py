"""Flask dashboard for the Cross-Channel Marketing Performance Dashboard.
Run: python3 app.py  →  open http://localhost:5000
"""

import json
import os
import re
import threading

from dotenv import load_dotenv
from flask import Flask, jsonify
from jinja2 import Environment
from markupsafe import Markup, escape

import dashboard_data
from rag import generate_insight, retrieve_context
from rules import run_rules

load_dotenv()

app = Flask(__name__)

# How many distinct (rule, campaign) flags get a full RAG insight card. Rules
# fire once per week a condition holds, so the same campaign can appear many
# times — dedupe to one card per campaign/rule and cap the count so the feed
# stays "curated, not chatty" per the spec, rather than one card per week.
MAX_INSIGHTS = 12

_cache = {}
# Building the dashboard means ~12 sequential Claude calls (a minute-plus) —
# far past gunicorn's default 30s worker timeout. Warm it in a background
# thread at process start so it's usually ready before a real visitor hits
# "/", and guard with a lock so a request arriving mid-warmup doesn't kick
# off a second, concurrent build against the same API quota. `_building` is
# tracked separately from `_cache` so /api/status can tell "a refresh is in
# progress" apart from "the old cached dashboard is still sitting there."
_build_lock = threading.Lock()
_building = False


def markdown_bold(text):
    escaped = str(escape(text))
    bolded = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return Markup(bolded)


_env = Environment(autoescape=True)
_env.filters["markdown_bold"] = markdown_bold


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

    insights = []
    for flag in flags:
        try:
            chunks = retrieve_context(flag)
            insights.append(generate_insight(flag, chunks))
        except Exception as e:
            insights.append({
                "rule_id": flag.rule_id, "channel": flag.channel, "platform": flag.platform,
                "campaign_name": flag.campaign_name, "period": flag.period,
                "materiality": flag.materiality, "what_happened": flag.what_happened,
                "why_it_matters": "", "recommended_next_step": "",
                "source_grounding": f"(insight generation failed: {e})",
            })

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


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cross-Channel Marketing Performance Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<style>
  :root {
    --bg: #0f1117; --card: #1a1d2e; --border: #2a2d3e;
    --text: #e4e6f1; --muted: #8b8fa8; --accent: #6c63ff;
    --good: #2ecc71; --bad: #ff5c5c;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 24px; }
  h1 { font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }
  .subtitle { color: var(--muted); font-size: 0.85rem; margin-bottom: 20px; }
  .refresh-btn { background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 8px 16px; font-size: 0.8rem; cursor: pointer; margin-bottom: 20px; }
  .refresh-btn:disabled { opacity: 0.5; cursor: wait; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }
  .grid-2 { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 20px; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .card h2 { font-size: 0.85rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 14px; }
  .stat { font-size: 1.7rem; font-weight: 700; }
  .channel-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; }
  .channel-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px; border-top: 3px solid; }
  .channel-card .name { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; margin-bottom: 8px; }
  .channel-card .spend { font-size: 1.1rem; font-weight: 700; margin-bottom: 4px; }
  .channel-card .metric { font-size: 0.8rem; color: var(--muted); }
  .trend-up { color: var(--bad); } .trend-down { color: var(--good); }
  .insight-list { max-height: 640px; overflow-y: auto; }
  .insight-card { border-left: 3px solid var(--accent); background: #14172400; padding: 12px 16px; margin-bottom: 14px; border-radius: 0 8px 8px 0; background: #171a28; }
  .insight-card .meta-row { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; margin-bottom: 6px; }
  .insight-card .what { font-weight: 600; margin-bottom: 6px; }
  .insight-card .why { font-size: 0.85rem; color: #c7c9dd; margin-bottom: 6px; }
  .insight-card .next-step { font-size: 0.85rem; background: #22263a; border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; }
  .insight-card .source { font-size: 0.7rem; color: var(--muted); font-style: italic; }
  .actions-list { list-style: none; }
  .actions-list li { font-size: 0.82rem; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .actions-list li:last-child { border-bottom: none; }
  .actions-list .tag { color: var(--muted); font-size: 0.7rem; text-transform: uppercase; margin-right: 6px; }
  .chart { width: 100%; height: 300px; }
</style>
</head>
<body>
  <h1>Cross-Channel Marketing Performance Dashboard</h1>
  <div class="subtitle">Meta &middot; Google Search &middot; TikTok &middot; Pinterest &middot; Snapchat &middot; Programmatic &middot; Mailchimp</div>
  <button class="refresh-btn" onclick="refresh()">Refresh insights</button>

  <div class="grid-4">
    <div class="card"><h2>Total Spend</h2><div class="stat">${{ "%.0f"|format(summary.total_spend) }}</div></div>
    <div class="card"><h2>Blended CPA</h2><div class="stat">${{ "%.2f"|format(summary.blended_cpa) }}</div></div>
    <div class="card"><h2>Blended ROAS</h2><div class="stat">{{ "%.2f"|format(summary.blended_roas) }}x</div></div>
    <div class="card"><h2>Conversions</h2><div class="stat">{{ "%.0f"|format(summary.total_conversions) }}</div></div>
  </div>

  <div class="card" style="margin-bottom:20px;">
    <h2>Channel Breakdown</h2>
    <div class="channel-cards">
      {% for c in channels %}
      <div class="channel-card" style="border-top-color: {{ c.color }};">
        <div class="name">{{ c.platform }}</div>
        <div class="spend">${{ "%.0f"|format(c.spend) if c.spend else "—" }}</div>
        <div class="metric">
          {% if c.ctr %}CTR {{ "%.2f"|format(c.ctr) }}% &middot; {% endif %}
          {{ c.metric_label }} {{ c.metric_value }}
          <span class="{{ 'trend-up' if c.trend == 'up' and not c.trend_good else ('trend-down' if c.trend == 'down' and c.trend_good else '') }}">
            {% if c.trend == 'up' %}&#9650;{% elif c.trend == 'down' %}&#9660;{% endif %}
          </span>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <h2>Insight Feed</h2>
      <div class="insight-list">
        {% for i in insights %}
        <div class="insight-card">
          <div class="meta-row">{{ i.rule_id.replace('_', ' ') }} &middot; {{ i.platform }} / {{ i.campaign_name }} &middot; materiality {{ "%.2f"|format(i.materiality) }}</div>
          <div class="what">{{ i.what_happened }}</div>
          {% if i.why_it_matters %}<div class="why">{{ i.why_it_matters|markdown_bold }}</div>{% endif %}
          {% if i.recommended_next_step %}<div class="next-step"><strong>Next step:</strong> {{ i.recommended_next_step|markdown_bold }}</div>{% endif %}
          <div class="source">{{ i.source_grounding }}</div>
        </div>
        {% endfor %}
      </div>
    </div>
    <div class="card">
      <h2>Recommended Actions</h2>
      <ul class="actions-list">
        {% for i in insights %}
        {% if i.recommended_next_step %}
        <li><span class="tag">{{ i.platform }}</span>{{ i.recommended_next_step|markdown_bold }}</li>
        {% endif %}
        {% endfor %}
      </ul>
    </div>
  </div>

  <div class="grid-3">
    <div class="card"><h2>Spend Over Time</h2><div id="chart-spend" class="chart"></div></div>
    <div class="card"><h2>CPA Over Time</h2><div id="chart-cpa" class="chart"></div></div>
    <div class="card"><h2>Channel Mix (Total Spend)</h2><div id="chart-mix" class="chart"></div></div>
  </div>

<script>
const charts = {{ charts_json }};
const opts = {responsive: true, displayModeBar: false};
Plotly.newPlot('chart-spend', charts.spend_trend.data, charts.spend_trend.layout, opts);
Plotly.newPlot('chart-cpa', charts.cpa_trend.data, charts.cpa_trend.layout, opts);
Plotly.newPlot('chart-mix', charts.channel_mix.data, charts.channel_mix.layout, opts);

function refresh() {
  const btn = document.querySelector('.refresh-btn');
  btn.disabled = true;
  btn.textContent = 'Refreshing… (regenerates AI insights, ~60-90s)';
  fetch('/api/refresh', {method: 'POST'}).then(pollUntilReady);
}

function pollUntilReady() {
  fetch('/api/status').then(r => r.json()).then(data => {
    if (data.ready) location.reload();
    else setTimeout(pollUntilReady, 3000);
  });
}
</script>
</body>
</html>
"""


def _build_in_background():
    global _building
    if not _build_lock.acquire(blocking=False):
        return  # a build is already running — don't start a second one
    _building = True
    try:
        _cache["dashboard"] = build_dashboard()
    finally:
        _building = False
        _build_lock.release()


# Warm the cache once at process start so most visitors never see the
# "building" placeholder below.
threading.Thread(target=_build_in_background, daemon=True).start()

BUILDING_TEMPLATE = """
<!DOCTYPE html>
<html><head><meta http-equiv="refresh" content="5">
<style>
  body { background: #0f1117; color: #e4e6f1; font-family: -apple-system, sans-serif;
         display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
  .box { text-align: center; }
  .box h1 { font-size: 1.2rem; margin-bottom: 8px; }
  .box p { color: #8b8fa8; font-size: 0.85rem; }
</style></head>
<body><div class="box">
  <h1>Building the dashboard…</h1>
  <p>Running the rules engine and generating AI insight cards (~60-90s on first load). This page refreshes automatically.</p>
</div></body></html>
"""


@app.route("/")
def index():
    if "dashboard" not in _cache:
        # Always spawn a thread rather than building inline — the lock makes
        # a redundant spawn a cheap no-op, but building on the request thread
        # itself would block this worker for the full ~60-90s, which is
        # exactly the gunicorn-worker-timeout bug this design avoids.
        threading.Thread(target=_build_in_background, daemon=True).start()
        return BUILDING_TEMPLATE
    data = _cache["dashboard"]
    tmpl = _env.from_string(HTML_TEMPLATE)
    return tmpl.render(
        summary=data["summary"],
        channels=data["channels"],
        insights=data["insights"],
        charts_json=Markup(json.dumps(data["charts"])),
    )


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    threading.Thread(target=_build_in_background, daemon=True).start()
    return jsonify({"ok": True, "status": "building"})


@app.route("/api/status")
def api_status():
    return jsonify({"ready": "dashboard" in _cache and not _building})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
