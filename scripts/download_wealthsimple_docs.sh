#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE_DIR="${PROFILE_DIR:-$ROOT_DIR/working/browser-profiles/wealthsimple-capture}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/working/wealthsimple-docs}"
LOG_FILE="${LOG_FILE:-$OUTPUT_DIR/download.log}"
DOCS_URL="${1:-https://my.wealthsimple.com/app/docs}"

mkdir -p "$OUTPUT_DIR"

PROFILE_DIR="$PROFILE_DIR" \
OUTPUT_DIR="$OUTPUT_DIR" \
LOG_FILE="$LOG_FILE" \
START_DATE="${START_DATE:-}" \
END_DATE="${END_DATE:-}" \
MAX_DOCS="${MAX_DOCS:-200}" \
LOAD_MORE_LIMIT="${LOAD_MORE_LIMIT:-20}" \
node "$ROOT_DIR/scripts/download_wealthsimple_docs.js" "$DOCS_URL"
