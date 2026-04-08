# Wealthgrabber Viewing Experience Opportunities

This note translates the current CLI/data model into practical ways to make wealth data easier to explore.

## What we have today (good foundation)

The current architecture is already friendly for building richer UX:

- **Clean data layer:** account/activity/position fetchers return dataclasses (`AccountData`, `ActivityData`, `PositionData`).
- **Renderer layer:** output is separated via formatter protocol (table/json/csv).
- **CLI already exports structured data:** `--format json` exists for all three domains.

That means we can build a UI without rewriting API/auth logic.

## Product directions (ranked)

### 1) Fastest win: “Web view” command (recommended)

Add a command like `wealthgrabber dashboard` that:

1. Calls existing `get_*_data()` functions.
2. Writes a single normalized JSON snapshot.
3. Serves a local static web page (no cloud required) with charts/tables.

**Why this is strong**
- Reuses almost all backend code.
- Keeps privacy/local-first promise.
- Gives a modern visual experience quickly.

**What to show first**
- Net worth summary cards.
- Allocation pie by symbol/account.
- P&L leaderboard (best/worst positions).
- Activity timeline (deposits, buys, sells, dividends).

### 2) “Recording overlay” timeline mode

Since you mentioned a “recording lay on top,” add snapshot history:

- New command: `wealthgrabber snapshot save` (append timestamped JSON file).
- Dashboard can scrub through snapshots with a time slider.
- Show deltas: value change, allocation drift, realized vs unrealized trend.

This turns a downloader into a personal finance replay tool.

### 3) Existing-CLI enhancement path (no web app yet)

If we want zero UI stack initially, extend CLI output:

- Add `--format markdown` for readable reports.
- Add `wealthgrabber report weekly` to output “top movers + dividends + account change”.
- Add `wealthgrabber export all --out data/` for one-shot account/activity/asset bundles.

This gives immediate utility and prepares data contracts for a dashboard later.

## Proposed implementation roadmap

### Phase 0: stabilize data contract

Create one shared envelope schema for exports:

```json
{
  "generated_at": "ISO-8601",
  "accounts": [],
  "activities": [],
  "positions": [],
  "totals": {
    "portfolio_value": 0,
    "book_value": 0,
    "pnl": 0
  }
}
```

### Phase 1: dashboard MVP

- Add `wealthgrabber dashboard --open`.
- Build tiny frontend (e.g., HTMX/Alpine/Chart.js or React/Vite).
- Read only local JSON file (no backend server besides static file hosting).

### Phase 2: history + “story mode”

- Add snapshot storage (`~/.wealthgrabber/snapshots/*.json`).
- Add compare mode: “today vs last week/month.”
- Add annotated events (manual notes: “bonus deposited”, “market dip”).

### Phase 3: advanced insights

- Dividend income cadence chart.
- Concentration/risk alerts.
- Cash-flow heatmap from activities.
- Rebalancing suggestions (informational only).

## Technical notes for this repository

- Best insertion point for new UX command: `src/wealthgrabber/cli.py` (new `dashboard` command).
- Reuse retrieval functions from `accounts.py`, `activities.py`, `assets.py`; avoid duplicate API calls where possible.
- Keep formatter protocol as-is; treat dashboard export as a separate serializer module (e.g., `snapshot.py`).

## Suggested immediate next step

Implement **`wealthgrabber export all --format json --out snapshot.json`** first, then build a minimal browser page that reads this file.

This creates a low-risk bridge from “downloader CLI” to “visual wealth experience.”
