"""Static dashboard rendering helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wealthgrabber.snapshots import (
    default_dashboard_path,
    get_dashboard_latest_path,
    write_latest_copy,
)


def render_dashboard_html(snapshot: dict[str, Any]) -> str:
    """Render single-file dashboard HTML using embedded snapshot data."""
    # Embed snapshot data as inert JSON instead of executable JS text so
    # browser parsing is not affected by HTML entity escaping.
    data_json = json.dumps(snapshot).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>wealthgrabber dashboard</title>
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; margin: 0; background: #0b1020; color: #ecf0ff; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px; }}
    .muted {{ color: #9fb0e0; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); gap: 12px; margin: 18px 0 24px; }}
    .card {{ background: #111a33; border: 1px solid #28345f; border-radius: 12px; padding: 14px; }}
    .label {{ font-size: 12px; color: #9fb0e0; text-transform: uppercase; letter-spacing: .06em; }}
    .value {{ font-size: 24px; font-weight: 700; margin-top: 8px; }}
    .grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }}
    .panel {{ background: #111a33; border: 1px solid #28345f; border-radius: 12px; padding: 14px; margin-bottom: 16px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #22315e; padding: 8px; text-align: left; }}
    select, input {{ background: #0e1731; color: #ecf0ff; border: 1px solid #30467e; border-radius: 8px; padding: 8px; }}
    .row {{ display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }}
    .bar {{ height: 18px; background: linear-gradient(90deg, #2dd4bf, #3b82f6); border-radius: 99px; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>wealthgrabber dashboard</h1>
    <p class=\"muted\" id=\"meta\"></p>

    <div class=\"cards\">
      <div class=\"card\"><div class=\"label\">Portfolio Value</div><div class=\"value\" id=\"totalValue\"></div></div>
      <div class=\"card\"><div class=\"label\">Book Value</div><div class=\"value\" id=\"bookValue\"></div></div>
      <div class=\"card\"><div class=\"label\">P&L</div><div class=\"value\" id=\"pnlValue\"></div></div>
      <div class=\"card\"><div class=\"label\">Activity Records</div><div class=\"value\" id=\"activityCount\"></div></div>
    </div>

    <div class=\"grid\">
      <div>
        <div class=\"panel\">
          <h3>Positions</h3>
          <div class=\"row\">
            <input id=\"symbolFilter\" placeholder=\"Filter symbol or name\" />
            <select id=\"accountFilter\"><option value=\"\">All accounts</option></select>
          </div>
          <table>
            <thead><tr><th>Symbol</th><th>Name</th><th>Account</th><th>Market Value</th><th>P&L</th></tr></thead>
            <tbody id=\"positionsBody\"></tbody>
          </table>
        </div>

        <div class=\"panel\">
          <h3>Recent Activities</h3>
          <table>
            <thead><tr><th>Date</th><th>Type</th><th>Description</th><th>Account</th><th>Amount</th></tr></thead>
            <tbody id=\"activitiesBody\"></tbody>
          </table>
        </div>
      </div>

      <div>
        <div class=\"panel\">
          <h3>Allocation by Symbol</h3>
          <div id=\"allocation\"></div>
        </div>
      </div>
    </div>
  </div>

<script id="snapshot-data" type="application/json">{data_json}</script>
<script>
const snapshot = JSON.parse(document.getElementById('snapshot-data').textContent || '{{}}');
const money = (n, ccy = (snapshot.meta?.base_currency || 'CAD')) => `${{Number(n || 0).toLocaleString(undefined, {{maximumFractionDigits: 2, minimumFractionDigits: 2}})}} ${{ccy || snapshot.meta?.base_currency || 'CAD'}}`;

const positions = snapshot.positions || [];
const activities = snapshot.activities || [];

function bySymbolAllocation(rows) {{
  const total = rows.reduce((sum, r) => sum + Number(r.market_value || 0), 0);
  const map = new Map();
  rows.forEach((r) => map.set(r.symbol, (map.get(r.symbol) || 0) + Number(r.market_value || 0)));
  return [...map.entries()].sort((a,b) => b[1] - a[1]).slice(0, 12).map(([symbol, value]) => ({{symbol, value, pct: total ? (value / total) * 100 : 0}}));
}}

function renderAllocation() {{
  const container = document.getElementById('allocation');
  container.innerHTML = '';
  bySymbolAllocation(positions).forEach((item) => {{
    const row = document.createElement('div');
    row.style.marginBottom = '10px';
    row.innerHTML = `<div style=\"display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px\"><span>${{item.symbol}}</span><span>${{item.pct.toFixed(1)}}%</span></div><div class=\"bar\" style=\"width:${{Math.max(3, item.pct)}}%\"></div>`;
    container.appendChild(row);
  }});
}}

function renderPositions() {{
  const q = document.getElementById('symbolFilter').value.toLowerCase().trim();
  const account = document.getElementById('accountFilter').value;
  const body = document.getElementById('positionsBody');
  body.innerHTML = '';

  positions
    .filter((p) => !q || `${{(p.symbol||'')}} ${{(p.name||'')}}`.toLowerCase().includes(q))
    .filter((p) => !account || (p.account_label || '') === account)
    .sort((a,b) => Number(b.market_value || 0) - Number(a.market_value || 0))
    .slice(0, 200)
    .forEach((p) => {{
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${{p.symbol || ''}}</td><td>${{p.name || ''}}</td><td>${{p.account_label || ''}}</td><td>${{money(p.market_value, p.currency)}}</td><td>${{money(p.pnl, p.currency)}}</td>`;
      body.appendChild(tr);
    }});
}}

function renderActivities() {{
  const body = document.getElementById('activitiesBody');
  body.innerHTML = '';
  activities.slice(0, 100).forEach((a) => {{
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${{a.date || ''}}</td><td>${{a.activity_type || ''}}</td><td>${{a.description || ''}}</td><td>${{a.account_label || ''}}</td><td>${{a.sign || ''}}${{money(a.amount, a.currency)}}</td>`;
    body.appendChild(tr);
  }});
}}

function init() {{
  const totals = snapshot.totals || {{}};
  document.getElementById('meta').textContent = `Generated: ${{snapshot.generated_at || 'N/A'}} · Schema: ${{snapshot.schema_version || 'N/A'}}`;
  document.getElementById('totalValue').textContent = money(totals.portfolio_value);
  document.getElementById('bookValue').textContent = money(totals.book_value);
  document.getElementById('pnlValue').textContent = money(totals.pnl);
  document.getElementById('activityCount').textContent = String(activities.length);

  const accounts = [...new Set(positions.map((p) => p.account_label).filter(Boolean))].sort();
  const accountFilter = document.getElementById('accountFilter');
  accounts.forEach((label) => {{
    const opt = document.createElement('option');
    opt.value = label;
    opt.textContent = label;
    accountFilter.appendChild(opt);
  }});

  document.getElementById('symbolFilter').addEventListener('input', renderPositions);
  document.getElementById('accountFilter').addEventListener('change', renderPositions);

  renderAllocation();
  renderPositions();
  renderActivities();
}}

init();
</script>
</body>
</html>
"""


def write_dashboard(snapshot: dict[str, Any], out_path: Path | None = None) -> Path:
    """Write dashboard HTML and return path."""
    path = out_path or default_dashboard_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dashboard_html(snapshot), encoding="utf-8")
    if out_path is None:
        write_latest_copy(path, get_dashboard_latest_path())
    return path
