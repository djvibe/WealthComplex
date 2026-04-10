# Front-End Delivery Strategy for Wealthgrabber

This strategy builds on the prior research in `docs/view-experience-opportunities.md` and turns it into an execution plan for a practical, local-first visual product.

## 1) Product goals

- Keep the CLI as the trusted data ingestion/authentication layer.
- Add a visual interface for fast scanning, filtering, and trend exploration.
- Preserve privacy by default (local files / local web server only).
- Avoid large rewrites by reusing existing `get_*_data()` patterns.

## 2) Recommended delivery approach

### Stage A — Single command + local dashboard (MVP)

Ship a new CLI command family focused on a dashboard feed:

- `wealthgrabber export all`
- `wealthgrabber dashboard --open`
- `wealthgrabber dashboard --snapshot ~/.wealthgrabber/exports/YYYY/MM/DD/<timestamp>.json --open`

MVP UI capabilities:

- Summary cards: portfolio value, total P&L, daily/period change (if available).
- Positions table with search + filters (account, symbol, gain/loss buckets).
- Allocation chart(s): by account and by symbol.
- Activity timeline with type filters (buy/sell/dividend/deposit/withdrawal).

Why this first:

- Fastest path to value.
- Uses current architecture with minimal changes.
- Lets us validate UX before committing to heavier stack decisions.

### Stage B — Historical snapshots + time navigation

Add periodic snapshot recording and a timeline viewer:

- `wealthgrabber snapshot save`
- `wealthgrabber snapshot list`
- `wealthgrabber dashboard --history ~/.wealthgrabber`

UI additions:

- Time slider / period picker.
- Delta views (today vs 7/30/90 days).
- Trend charts (portfolio value, account contribution, allocation drift).

### Stage C — Insights and workflows

After history is stable, add guidance-oriented screens:

- Income/dividend cadence.
- Concentration alerts.
- Contribution and withdrawal flow charts.
- Rebalancing “what changed” explainers.

## 3) Front-end stack options (pragmatic ranking)

### Option 1 (recommended now): React + TypeScript + Vite + Chart.js

- Pros: strong component ecosystem, great table/chart libraries, easy filtering UX.
- Cons: highest initial front-end complexity.
- Fit: best if we expect this UI to grow into a primary product surface.

### Option 2: HTMX + Alpine + Chart.js (lightweight)

- Pros: very small footprint, fast to ship simple interactive pages.
- Cons: can get harder to maintain for richer stateful dashboards.
- Fit: best if we want “good enough dashboard” quickly with minimal frontend tooling.

### Option 3: Tauri desktop wrapper (phase after web MVP)

- Pros: desktop app feel, local-first packaging, reuse web UI.
- Cons: packaging and release overhead.
- Fit: ideal if users explicitly want a native desktop app after web UX proves out.

## 4) Data contract recommendation

Define and version one canonical snapshot schema consumed by any UI:

```json
{
  "schema_version": "1.0",
  "generated_at": "ISO-8601",
  "accounts": [],
  "activities": [],
  "positions": [],
  "totals": {
    "portfolio_value": 0,
    "book_value": 0,
    "pnl": 0
  },
  "meta": {
    "base_currency": "USD",
    "source": "wealthgrabber"
  }
}
```

Guidelines:

- Backward-compatible changes are additive.
- Breaking changes require `schema_version` bump.
- Keep fields denormalized where helpful for UI filtering/search.

## 5) UX information architecture

Recommended screens:

1. **Overview**
   - Total value, P&L, allocation, recent activity summary.
2. **Positions**
   - Sortable/filterable grid + per-position detail panel.
3. **Activities**
   - Timeline table + calendar/aggregation chart.
4. **Accounts**
   - Account-level breakdown, contribution to performance.
5. **History**
   - Date range selector, trend and comparison views.

Cross-screen UX rules:

- Persistent global filters (date range, account, asset class).
- URL-encoded filters for shareable local views.
- Fast search-first interactions.

## 6) Delivery plan (suggested timeline)

### Sprint 1

- Implement `export all` command + schema v1 serializer.
- Build static dashboard shell that reads one snapshot file.
- Add overview cards + positions table + basic chart.

### Sprint 2

- Add snapshot persistence commands and history loading.
- Add activity timeline + date filters.
- Add compare mode (current vs selected prior snapshot).

### Sprint 3

- Add insight cards/alerts and polish interactions.
- Evaluate optional Tauri packaging for desktop distribution.

## 7) Risks and mitigations

- **Risk:** Schema churn breaks UI.
  - **Mitigation:** explicit versioning + snapshot fixtures in tests.
- **Risk:** Too many frontend choices delay shipping.
  - **Mitigation:** lock MVP stack now, revisit after adoption feedback.
- **Risk:** Data volume affects browser performance.
  - **Mitigation:** pre-aggregate in CLI export, virtualized tables, chart sampling.

## 8) Concrete “start now” recommendation

Build the MVP with:

1. `export all` JSON contract.
2. Local web dashboard reading that JSON.
3. Dated snapshot/export history in the next increment.

This keeps momentum high, gives you the visual exploration workflow you want (filters + graphs + screens), and avoids risky rewrites of the existing CLI foundation.
