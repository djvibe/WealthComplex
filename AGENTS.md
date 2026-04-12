# wealthgrabber - Agent Guide

This document contains context, conventions, and instructions for AI agents working on the `wealthgrabber` codebase.


## Project Overview
`wealthgrabber` is a Python CLI application for wealth management operations. It appears to interface with external services using `ws-api` and `requests`, and handles authentication securely via `keyring`.

Recent product additions extend the CLI into a local-first portfolio viewing tool:
- Unified JSON export via `wealthgrabber export all`
- Static dashboard HTML generation via `wealthgrabber dashboard`
- Automatic timestamped snapshot persistence for `list`, `activities`, and `assets`
- Historical portfolio analysis via `wealthgrabber analyze`

### Architecture
- **Root**: `src/wealthgrabber`
- **Entry Point**: `src/wealthgrabber/cli.py` (exposed as `wealthgrabber` script)
- **Authentication**: `src/wealthgrabber/auth.py`
- **Core Logic**: `src/wealthgrabber/accounts.py`, `activities.py`, `assets.py`
- **Export Contract**: `src/wealthgrabber/exporting.py`
- **Dashboard Renderer**: `src/wealthgrabber/dashboard.py`
- **Snapshot Persistence**: `src/wealthgrabber/snapshots.py`
- **Historical Analysis**: `src/wealthgrabber/analyze.py`
- **Dependencies**: Managed via `uv` (standard `pyproject.toml`).

## Development Environment
- **Package Manager**: `uv`
- **Python Version**: >=3.12
- **Linux Keyring**: Prefer `keyring.backends.SecretService.Keyring` via the system GNOME Secret Service backend. Do not add or document plaintext keyring fallbacks as the default path.

### Key Commands
- **Install/Sync**: `uv sync`
- **Run App**: `uv run wealthgrabber --help` or `uv run python -m wealthgrabber`
- **Locate Package**: `uv run python -c "import wealthgrabber; print(wealthgrabber.__file__)"`
- **Preferred Secure Run**:
  `PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring UV_CACHE_DIR=/tmp/uv-cache uv run wealthgrabber --help`

## Testing & Quality
- **Test Runner**: `pytest`
- **Coverage**: `pytest-cov` is configured.
- **Commands**:
    - Run all tests: `uv run pytest`
    - Run specific test: `uv run pytest tests/test_auth.py`
    - Check types (recommended): `uv run mypy .`
    - Lint/Format (recommended): `uv run ruff check .`

## Conventions
- **Style**: Modern Python (3.12+). Use type hints for all function signatures.
- **CLI Framework**: `typer` is used for command-line interactions.
- **Imports**: Absolute imports from `wealthgrabber` package (e.g., `from wealthgrabber.auth import ...`).
- **Async**: Use `async`/`await` where I/O bound operations occur (implied by `ws-api`).

## File Structure
```
src/wealthgrabber/
├── __init__.py
├── __main__.py
├── auth.py              # Authentication (keyring)
├── models.py            # Data models (AccountData, ActivityData, PositionData)
├── formatters.py        # Output formatters (Table, JSON, CSV)
├── accounts.py          # Account management logic
├── activities.py        # Activity/transaction logic
├── assets.py            # Asset position logic
├── cli.py               # Typer CLI application
├── exporting.py         # Unified snapshot export contract
├── dashboard.py         # Static dashboard HTML rendering
├── snapshots.py         # Local snapshot persistence helpers
├── analyze.py           # Historical portfolio analysis
tests/                   # Pytest suite
pyproject.toml           # Project configuration
```

## Architecture: Three-Layer Output Pattern

The application follows a clean three-layer architecture for data retrieval and output:

### Layer 1: Data Retrieval
Functions in each module (`accounts.py`, `activities.py`, `assets.py`) fetch and transform API data:
- **`get_accounts_data()`** - Fetches accounts and returns `list[AccountData]`
- **`get_activities_data()`** - Fetches activities and returns `list[ActivityData]`
- **`get_assets_data()`** - Fetches positions and returns `list[PositionData]`

These functions handle:
- API calls and error handling
- Data transformation (dicts → dataclasses)
- Filtering and aggregation logic
- Enhancement (e.g., security name lookups)

### Layer 2: Data Models
`models.py` defines simple, serializable dataclasses:
- **`AccountData`** - `description`, `number`, `value`, `currency`
- **`ActivityData`** - `date`, `activity_type`, `description`, `amount`, `currency`, `sign`, `account_label`
- **`PositionData`** - `symbol`, `name`, `quantity`, `market_value`, `book_value`, `currency`, `pnl`, `pnl_pct`, `account_label`

Activity model conventions:
- `amount` should be non-negative.
- `sign` carries transaction direction (`+` or `-`).
- `currency` should never be `None`; default to `"CAD"` when the API omits it.

### Layer 3: Formatters
`formatters.py` implements output formatters using a protocol-based design:

**`FormatterProtocol`** - Interface for all formatters with methods:
- `format_accounts(accounts: Sequence[AccountData]) -> str`
- `format_activities(activities: Sequence[ActivityData]) -> str`
- `format_positions(positions: Sequence[PositionData], show_totals: bool, group_label: Optional[str]) -> str`

**Concrete Implementations:**
- **`TableFormatter`** - ASCII tables with borders, alignment, and totals (default)
- **`JsonFormatter`** - JSON arrays with optional totals wrapper
- **`CsvFormatter`** - CSV format with headers and optional totals row

Formatter rules:
- Do not combine mixed-currency account balances into a single fake total.
- When multiple account currencies exist, totals should be shown per currency.
- Avoid duplicating sign information by formatting from normalized activity data.

**Factory:** `get_formatter(format_type: str) -> FormatterProtocol`

### Output Flow
```
CLI Command (with --format option)
    ↓
get_*_data() retrieves and transforms data
    ↓
Data models (AccountData, ActivityData, PositionData)
    ↓
get_formatter(format_type) selects formatter
    ↓
formatter.format_*() converts to output string
    ↓
print(output) to stdout
```

## CLI Usage

Data-display commands support `--format` with choices: `table` (default), `json`, `csv`

```bash
# Table format (default)
wealthgrabber list
wealthgrabber activities
wealthgrabber assets

# JSON format
wealthgrabber list --format json
wealthgrabber activities --format json --dividends
wealthgrabber assets --format json --by-account

# Unified export for local UI consumers
wealthgrabber export all
wealthgrabber export all --out snapshot.json

# Generate local dashboard HTML
wealthgrabber dashboard --snapshot snapshot.json --open
wealthgrabber dashboard --no-open

# Analyze persisted snapshot history
wealthgrabber analyze
wealthgrabber analyze --lookback-days 180 --format json

# CSV format
wealthgrabber list --format csv > accounts.csv
wealthgrabber activities --format csv > activities.csv
wealthgrabber assets --format csv > assets.csv
```

## Adding New Output Formats

To add a new output format (e.g., XML):

1. Create formatter class implementing `FormatterProtocol`:
   ```python
   class XmlFormatter:
       def format_accounts(self, accounts: Sequence[AccountData]) -> str:
           # XML formatting logic
           ...
   ```

2. Register in `get_formatter()`:
   ```python
   formatters = {
       "table": TableFormatter(),
       "json": JsonFormatter(),
       "csv": CsvFormatter(),
       "xml": XmlFormatter(),  # New!
   }
   ```

3. Add to `OutputFormat` enum in `cli.py`:
   ```python
   class OutputFormat(str, Enum):
       table = "table"
       json = "json"
       csv = "csv"
       xml = "xml"  # New!
   ```

No other changes needed - data retrieval and CLI plumbing remain the same.


## Dashboard / Export Pattern

The repo now includes a UI bridge pattern that keeps API/auth logic in Python:

- `build_export_snapshot()` in `exporting.py` builds a canonical payload with:
  - `schema_version`, `generated_at`
  - `accounts`, `activities`, `positions`
  - `totals` (`portfolio_value`, `book_value`, `pnl`)
  - `meta` (`base_currency`, `source`)
- `wealthgrabber export all` writes this payload to JSON.
- By default, unified exports are written to dated paths under `~/.wealthgrabber/exports/YYYY/MM/DD/`.
- `wealthgrabber dashboard` renders a local static HTML dashboard from either:
  - a provided snapshot (`--snapshot`), or
  - a live fetch when no snapshot is provided.
- By default, generated dashboards are written to dated paths under `~/.wealthgrabber/dashboards/YYYY/MM/DD/`, and the latest dashboard is also mirrored to `~/.wealthgrabber/dashboard/index.html`.
- The generated dashboard is a single local HTML file intended for fast inspection, not a long-running backend service.

## Snapshot Persistence / Analysis

- `list`, `activities`, and `assets` automatically write timestamped snapshots under `~/.wealthgrabber/snapshots/` by default.
- `WEALTHGRABBER_DATA_DIR` overrides the local data root for snapshots, dated exports, and dashboard output.
- Default data layout under the root:
  - `snapshots/accounts|activities|assets/YYYY/MM/DD/*.json`
  - `exports/YYYY/MM/DD/*.json`
  - `dashboards/YYYY/MM/DD/*.html`
  - `dashboard/index.html` for the latest dashboard convenience copy
- Use repo-local `working/` for temporary scratch artifacts created during development or debugging; it is git-ignored and separate from durable app data in `~/.wealthgrabber`.
- Code write-path contract:
  - `list`, `activities`, and `assets` write only to the durable `snapshots/` tree.
  - `export all` defaults to the durable `exports/` tree unless the caller passes `--out`.
  - `dashboard` defaults to the durable `dashboards/` tree and refreshes `dashboard/index.html` unless the caller passes `--out`.
  - Do not introduce new default writes into the repository root; use `working/` for repo-local scratch artifacts.
- `analyze.py` loads stored command snapshots and can fall back to dated unified export history when raw per-command history is unavailable. It derives:
  - portfolio value change over the lookback window
  - unrealized P&L
  - concentration metrics
  - negative-position exposure
  - dividend activity totals
- For browser-driven style/reference capture experiments, keep generated artifacts under repo-local `working/` rather than adding new durable app storage paths.

## Authentication / Dependency Notes

- The repo pins `ws-api==0.32.3` because earlier versions were brittle against Wealthsimple's current login flow.
- When verifying login behavior on Linux, prefer running outside restricted sandboxes so the desktop DBus and Secret Service keyring are reachable.
- Keep the documented runtime path aligned with system keyring usage.

## Memory / Lessons

- Repo-local operating memory lives in [`docs/session-memory.md`](docs/session-memory.md).
- Use it for stable lessons learned, environment quirks, and recurring workflow decisions.
- Prefer short, high-signal entries over long logs.
- Update it when a session uncovers a reusable lesson that is likely to matter again.

## Current State vs Roadmap

The feature docs describe both implemented capabilities and next-step ideas. As of the current codebase:
- Implemented: `export all`, `dashboard`, automatic snapshot persistence, `analyze`
- Not yet implemented as dedicated CLI commands: `snapshot save`, `snapshot list`, dashboard history/time-slider mode, compare mode, URL-encoded dashboard filters

When updating docs or code:
- Document shipped behavior separately from roadmap items.
- Do not describe planned snapshot/history commands as available until they exist in `cli.py`.

When extending this pattern:
- Keep export schema changes backward-compatible where possible.
- Prefer additive fields before changing/removing existing keys.

## PR Instructions
- Ensure `uv run pytest` passes before finishing.
- Keep `AGENTS.md` updated if new tools or patterns are introduced.
- Update [`docs/session-memory.md`](docs/session-memory.md) when the session produces a reusable operational lesson.
