# wealthgrabber

Wealthsimple Account Viewer CLI. Secure and simple tool to view your Wealthsimple account balances, transactions, and holdings from the command line.

## Features
- **Secure Authentication**: Uses system keyring to safely store credentials.
- **Account Listing**: Clear overview of all your accounts and their current values.
- **Transaction History**: View activities and transactions across your accounts.
- **Asset Positions**: Monitor your investment holdings with P&L tracking.
- **Multiple Output Formats**: Table (default), JSON, and CSV output for easy integration.
- **Unified Snapshot Export**: Build one JSON payload for downstream dashboards and tools.
- **Local Dashboard**: Generate a single-file HTML dashboard from a live fetch or saved snapshot.
- **Historical Snapshots**: Persist local snapshots automatically for later review and analysis.
- **Portfolio Analysis**: Summarize concentration, dividend activity, unrealized P&L, and history deltas.
- **Privacy Focused**: No data is stored externally; everything runs locally.

## Installation

This project is managed with `uv`.

Current dependency note:
- `ws-api` is pinned to `0.32.3` because older versions were unreliable against Wealthsimple's current login flow.

### Quick Install

Install the application globally so you can run `wealthgrabber` directly:

```bash
# Clone the repository
git clone <your-repo-url>
cd wealthgrabber

# Install the application
make install
```

After installation, you can use `wealthgrabber` directly without the `uv run` prefix:

```bash
wealthgrabber --help
wealthgrabber login
wealthgrabber list
```

### Development Setup

For development, you can use `uv sync` to set up the environment:

```bash
# Install dependencies and sync environment
uv sync

# Run with uv (if not globally installed)
uv run wealthgrabber --help
```

### Secure Linux Setup

For Linux desktop environments, prefer the system Secret Service keyring and avoid plaintext fallback keyrings.

Recommended invocation:

```bash
PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring \
UV_CACHE_DIR=/tmp/uv-cache \
/home/djvibe/.local/bin/uv run wealthgrabber --help
```

If you want this behavior by default, add the following to `~/.bashrc`:

```bash
export PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring
export UV_CACHE_DIR=/tmp/uv-cache
```

## Usage

The CLI provides these primary commands: `login`, `logout`, `list`, `activities`, `assets`, `export all`, `dashboard`, and `analyze`.

All commands support the `--verbose/-v` flag for detailed status messages during execution.

### Authentication

#### Login
Authenticate with your Wealthsimple credentials. This supports 2FA and will cache your session securely.

```bash
wealthgrabber login
```

Recommended on Linux:

```bash
PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring \
UV_CACHE_DIR=/tmp/uv-cache \
/home/djvibe/.local/bin/uv run wealthgrabber login
```

**Options:**
- `--force/-f`: Force a new login even if a valid session exists.
- `--username/-u EMAIL`: Email address to login with. If not provided, uses cached email or prompts.

#### Logout
Clear stored session and optionally cached email.

```bash
wealthgrabber logout
```

**Options:**
- `--username/-u EMAIL`: Email address to clear session for. If not provided, uses cached email.
- `--clear-email/-c`: Also clear the cached email address.

### Accounts

#### List Accounts
View a summary of your accounts with their current values.

```bash
wealthgrabber list
```

**Options:**
- `--show-zero/-z`: Show accounts with zero balance (default: true).
- `--liquid-only/-l`: Show only liquid accounts (excludes RRSP, LIRA, Private Equity, Private Credit).
- `--not-liquid/-n`: Show only non-liquid accounts (RRSP, LIRA, Private Equity, Private Credit).
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# View all accounts as table (default)
wealthgrabber list

# Show only liquid accounts in JSON format
wealthgrabber list --liquid-only --format json

# Show non-liquid accounts and hide zero balances
wealthgrabber list --not-liquid --no-show-zero
```

Notes:
- Table totals are grouped by currency when accounts span multiple currencies.
- JSON/CSV outputs preserve per-account currency values.

### Transactions

#### List Activities
View activities and transactions for your accounts.

```bash
wealthgrabber activities
```

**Options:**
- `--account/-a ACCOUNT_NUMBER`: Filter by account number (e.g., 'TFSA-001').
- `--dividends/-d`: Show only dividend transactions.
- `--limit/-n N`: Maximum number of activities per account (default: 50).
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# View recent activities as table (default)
wealthgrabber activities

# View only dividend transactions in JSON format
wealthgrabber activities --dividends --format json

# View last 100 activities from a specific account
wealthgrabber activities --account TFSA-001 --limit 100

# Export activities to CSV
wealthgrabber activities --format csv > activities.csv
```

Notes:
- Activity payloads normalize `amount` to a non-negative numeric value.
- Transaction direction is represented separately via `sign` (`+` or `-`).
- Missing activity currencies fall back to `CAD`.

### Investments

#### List Asset Positions
View all asset positions across your accounts with profit/loss tracking.

```bash
wealthgrabber assets
```

**Options:**
- `--account/-a ACCOUNT_NUMBER`: Filter by account number (e.g., 'TFSA-001').
- `--by-account/-b`: Show positions grouped by account instead of aggregated.
- `--format/-f {table,json,csv}`: Output format (default: table).

**Examples:**
```bash
# View all positions aggregated (default)
wealthgrabber assets

# View positions grouped by account
wealthgrabber assets --by-account

# View positions for a specific account in JSON format
wealthgrabber assets --account TFSA-001 --format json

# Export all positions to CSV
wealthgrabber assets --format csv > positions.csv
```



### Unified Export

#### Export Everything to One Snapshot
Generate a canonical schema-v1 JSON payload with accounts, activities, positions, totals, and metadata for downstream apps.

```bash
wealthgrabber export all
wealthgrabber export all --out snapshot.json
```

**Options:**
- `--out/-o PATH`: Output file path (default: a dated file under `~/.wealthgrabber/exports/YYYY/MM/DD/`).
- `--activities-limit N`: Maximum activities per account included in the snapshot (default: 200).

Snapshot shape:

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
    "base_currency": "CAD",
    "source": "wealthgrabber"
  }
}
```

Export notes:
- `activities` records use normalized `amount` + `sign` semantics.
- `meta.base_currency` is the dashboard default, not a guarantee that every account or activity is denominated in that currency.

### Dashboard

#### Generate Local Dashboard HTML
Create a local interactive dashboard from a snapshot file or a live fetch. The current implementation writes a single HTML file for local viewing; it does not start a persistent web server.

```bash
# From live API data
wealthgrabber dashboard --open

# From existing snapshot
wealthgrabber dashboard --snapshot snapshot.json --open

# Generate file without opening browser
wealthgrabber dashboard --snapshot snapshot.json --out dashboard.html --no-open
```

**Options:**
- `--snapshot/-s PATH`: Read an existing export snapshot instead of fetching live data.
- `--out/-o PATH`: Output HTML path (default: a dated file under `~/.wealthgrabber/dashboards/YYYY/MM/DD/`).
- `--open/--no-open`: Open generated dashboard in default browser (default: open).

When `--out` is omitted, the latest generated dashboard is also mirrored to `~/.wealthgrabber/dashboard/index.html` for convenience.

### Analyze Portfolio (Historical Insights)
Use persisted snapshots to generate portfolio insights over time.

```bash
wealthgrabber analyze
wealthgrabber analyze --lookback-days 180 --format json
```

**Options:**
- `--lookback-days/-d N`: Number of days of stored snapshots to analyze (default: 90).
- `--format/-f {table,json,csv}`: Output format (default: table).

Current analysis includes:
- portfolio value over the stored lookback window
- unrealized P&L and P&L percentage
- top position concentration
- negative-position exposure
- dividend event count and total

## Snapshot Storage

Every time you run `list`, `activities`, or `assets`, the fetched data is snapshotted locally with a UTC timestamp. These snapshots power `wealthgrabber analyze`, and `analyze` can also fall back to unified export history when needed.

You can also create a unified UI-oriented snapshot with `wealthgrabber export all`.

Default root:
- `~/.wealthgrabber/`

Structure:
```
~/.wealthgrabber/
  snapshots/
    accounts/YYYY/MM/DD/HHMMSS-microseconds.json
    activities/YYYY/MM/DD/HHMMSS-microseconds.json
    assets/YYYY/MM/DD/HHMMSS-microseconds.json
  exports/YYYY/MM/DD/HHMMSS-microseconds.json
  dashboards/YYYY/MM/DD/HHMMSS-microseconds.html
  dashboard/index.html
```

Override root directory with:
- `WEALTHGRABBER_DATA_DIR=/path/to/data`

Repo-local scratch outputs:
- Use `working/` for temporary repo-local artifacts such as ad hoc exports, dashboard files, Playwright captures, and other debugging output.
- `working/` is git-ignored on purpose.

## Troubleshooting

### Keyring backend errors

If login fails with a keyring backend error, verify the app is using your desktop Secret Service keyring:

```bash
PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring \
UV_CACHE_DIR=/tmp/uv-cache \
/home/djvibe/.local/bin/uv run python -c "import keyring; print(keyring.get_keyring())"
```

### Wealthsimple login bootstrap issues

If login fails with `Couldn't find wssdi in login page response headers`, make sure you are on the pinned dependency set from this repo:

```bash
uv sync
```

This repo pins `ws-api==0.32.3` because older versions were more brittle.

## Roadmap Notes

The product docs in `docs/` include both shipped features and planned follow-up work.

Implemented now:
- `export all`
- `dashboard`
- automatic snapshot persistence
- `analyze`

Planned in the feature docs, but not yet exposed as dedicated CLI commands:
- `snapshot save`
- `snapshot list`
- dashboard history mode
- compare mode / time navigation
- richer insight screens and guided workflows

## Output Formats

### Table Format (Default)
Human-readable ASCII tables with formatting, alignment, and totals where applicable.

### JSON Format
Structured JSON output suitable for programmatic processing.

### CSV Format
Comma-separated values for import into spreadsheets or other tools.

## Development

If you are an AI assistant or a developer looking to contribute, please refer to [CLAUDE.md](CLAUDE.md) for detailed guidelines.

## Product Ideas / Visual Dashboard

If you want to evolve `wealthgrabber` from a downloader CLI into a richer viewing experience, see:

- [`docs/view-experience-opportunities.md`](docs/view-experience-opportunities.md)
- [`docs/frontend-delivery-strategy.md`](docs/frontend-delivery-strategy.md)

They outline:
- the local-first dashboard roadmap,
- snapshot/timeline ideas, and
- phased implementation details spanning both shipped commands and planned next steps.

## Contributor Notes

If you are updating behavior or workflows, also review:
- [`AGENTS.md`](AGENTS.md)
- [`docs/session-memory.md`](docs/session-memory.md)
