# Wealthsimple UI Capture

This repo includes a best-effort capture workflow for saving rendered Wealthsimple app pages plus the CSS, images, fonts, and scripts they load during an authenticated browser session.

## What It Does

- Opens `https://my.wealthsimple.com/app/home` in a headed persistent Chrome session
- Lets you log in manually in the real browser window
- Captures the current `/app/*` route and shallowly discovers additional `/app/*` links from the rendered page
- Saves:
  - rendered HTML snapshots
  - full-page screenshots for each captured route
  - DOM structure snapshots for each captured route
  - fetched stylesheets, images, fonts, and scripts
  - a `manifest.json` that maps source URLs to local files
  - a `capture.log` progress log

Artifacts are written to `working/wealthsimple-ui-mirror/` by default.
The browser session uses a dedicated repo-local Chrome profile at `working/browser-profiles/wealthsimple-capture/` by default, so your main Chrome profile is left alone.

## Run It

```bash
scripts/capture_wealthsimple_ui.sh
```

Optional environment variables:

```bash
MAX_PAGES=20 WAIT_MS=2500 scripts/capture_wealthsimple_ui.sh
OUTPUT_DIR="$PWD/working/ws-home" scripts/capture_wealthsimple_ui.sh
SESSION=wealthsimple-ui scripts/capture_wealthsimple_ui.sh
PROFILE_DIR="$HOME/.config/google-chrome/Profile 3" scripts/capture_wealthsimple_ui.sh
scripts/capture_wealthsimple_ui.sh https://my.wealthsimple.com/app/home
```

Default behavior:

- First run: you log in manually inside the dedicated capture profile.
- Later runs: the same dedicated profile is reused, so Wealthsimple session state can carry forward if it is still valid.
- The script launches Chrome directly through Playwright using that profile, then captures from the same live authenticated browser context.

If you want browser autofill or an existing Wealthsimple session to carry over, you can still override `PROFILE_DIR` to point at another Chrome profile directory. Prefer a dedicated or copied profile rather than a live default profile that is open in another Chrome process.

## Limits

- This is not a perfect offline clone of the application.
- Wealthsimple is a dynamic authenticated SPA, so some views may only appear after deeper interaction.
- Discovered assets are only the ones loaded during the captured session.
- The saved HTML is primarily for reference and style extraction; it is not guaranteed to work as a standalone offline app.
- Do not build tooling that extracts or persists Wealthsimple credentials from the OS keychain; rely on browser-managed autofill/session reuse instead.

For dashboard styling work, the most useful outputs are usually:

- `working/wealthsimple-ui-mirror/pages/*/index.html`
- `working/wealthsimple-ui-mirror/pages/*/page.png`
- `working/wealthsimple-ui-mirror/pages/*/dom.json`
- `working/wealthsimple-ui-mirror/assets/`
- `working/wealthsimple-ui-mirror/manifest.json`
- `working/wealthsimple-ui-mirror/capture.log`

## Documents

There is also a separate downloader for documents that appear under Wealthsimple's documents page. It reuses the same dedicated browser profile, opens the documents list, and downloads PDFs opened by the page into a local folder.

```bash
scripts/download_wealthsimple_docs.sh
```

Useful overrides:

```bash
START_DATE=2026-01-01 END_DATE=2026-12-31 scripts/download_wealthsimple_docs.sh
MAX_DOCS=50 scripts/download_wealthsimple_docs.sh
LOAD_MORE_LIMIT=5 scripts/download_wealthsimple_docs.sh
```

Artifacts are written to `working/wealthsimple-docs/` by default:

- PDFs
- `manifest.json`
- `download.log`

By default it starts from the unfiltered `https://my.wealthsimple.com/app/docs` view and sweeps the visible quick filters such as `2025 taxes`, `Account documents`, `Performance statements`, `2024 taxes`, and `My uploads`, deduping matches before download. Downloads are written incrementally as documents are discovered, rather than waiting for the full sweep to finish.
