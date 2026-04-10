# Session Memory

This file is a lightweight repo-local memory for future sessions. It should capture reusable operational knowledge, not a blow-by-blow history.

## Stable Facts

- Use the system Linux Secret Service keyring for credential storage.
- Preferred secure invocation:
  `PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring UV_CACHE_DIR=/tmp/uv-cache uv run wealthgrabber ...`
- `ws-api` is pinned to `0.32.3` because earlier versions were brittle against Wealthsimple's current login flow.

## Lessons Learned

### 2026-04-10

- Sandbox-restricted sessions may not be able to talk to the desktop DBus session bus, which prevents Secret Service keyring access even when `gnome-keyring-daemon` is running.
- Activity data should use normalized semantics:
  - `amount` is non-negative
  - `sign` carries direction
  - `currency` defaults to `CAD` if omitted by the API
- Account totals must not collapse mixed currencies into a single labeled total.
- Dashboard money rendering should fall back to the snapshot base currency when an activity currency is missing.
- Default local data storage is organized under `~/.wealthgrabber/` with dated `snapshots/`, `exports/`, and `dashboards/` trees; keep `dashboard/index.html` as a convenience copy of the latest rendered dashboard.
- `analyze` should remain backward-compatible with raw per-command snapshots but can use dated unified export history as a fallback source.
- Repo-local generated scratch artifacts should go in `working/` rather than the project root; keep `.playwright-cli/` at the root but git-ignored.

## Update Rule

Add an entry when:
- a dependency pin is introduced for a durable reason
- an environment quirk materially changes how the app must be run
- a data-model or formatter invariant is important enough to preserve across future edits

Do not add entries for:
- one-off typos
- temporary experiments
- routine command output with no lasting value
