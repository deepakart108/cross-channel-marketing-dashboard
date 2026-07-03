"""The dashboard's HTML template, shared by the local dev server (app.py) and
the static site generator (generate_static_site.py). The `live` flag toggles
the refresh button/polling JS, which only make sense against a running
server, not the static export.
"""

import re

from jinja2 import Environment
from markupsafe import Markup, escape


def markdown_bold(text):
    escaped = str(escape(text))
    bolded = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return Markup(bolded)


def make_environment():
    env = Environment(autoescape=True)
    env.filters["markdown_bold"] = markdown_bold
    return env


DASHBOARD_TEMPLATE = """
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
  .note { color: var(--muted); font-size: 0.78rem; margin-bottom: 20px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; display: inline-block; }
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
  .insight-card { border-left: 3px solid var(--accent); padding: 12px 16px; margin-bottom: 14px; border-radius: 0 8px 8px 0; background: #171a28; }
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
  {% if live %}
  <button class="refresh-btn" onclick="refresh()">Refresh insights</button>
  {% else %}
  <div class="note">Static snapshot &mdash; generated {{ generated_at }} from synthetic demo data by <code>generate_static_site.py</code>. See the <a href="https://github.com/deepakart108/cross-channel-marketing-dashboard" style="color:inherit;">GitHub repo</a> for the full pipeline (ingest &rarr; rules engine &rarr; RAG-grounded Claude insights).</div>
  {% endif %}

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

{% if live %}
function refresh() {
  const btn = document.querySelector('.refresh-btn');
  btn.disabled = true;
  btn.textContent = 'Refreshing… (regenerates AI insights, ~60-90s)';
  fetch('/api/refresh', {method: 'POST'}).then(() => location.reload());
}
{% endif %}
</script>
</body>
</html>
"""
