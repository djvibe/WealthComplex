#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/working/wealthsimple-ui-mirror}"
LOG_FILE="${LOG_FILE:-$OUTPUT_DIR/capture.log}"
MAX_PAGES="${MAX_PAGES:-12}"
WAIT_MS="${WAIT_MS:-1500}"
FIRST_ROUTE="${1:-https://my.wealthsimple.com/app/home}"
CAPTURE_SCRIPT="$ROOT_DIR/scripts/wealthsimple_capture.js"
DEFAULT_PROFILE_DIR="$ROOT_DIR/working/browser-profiles/wealthsimple-capture"
PROFILE_DIR="${PROFILE_DIR:-$DEFAULT_PROFILE_DIR}"

if ! command -v node >/dev/null 2>&1; then
  echo "node is required but was not found in PATH." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
mkdir -p "$PROFILE_DIR"
OUTPUT_DIR="$OUTPUT_DIR" \
LOG_FILE="$LOG_FILE" \
MAX_PAGES="$MAX_PAGES" \
WAIT_MS="$WAIT_MS" \
PROFILE_DIR="$PROFILE_DIR" \
node "$CAPTURE_SCRIPT" "$FIRST_ROUTE"
