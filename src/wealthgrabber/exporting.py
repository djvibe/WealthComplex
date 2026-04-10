"""Portfolio export helpers used by CLI commands and dashboard rendering."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ws_api import WealthsimpleAPI

from wealthgrabber.accounts import get_accounts_data
from wealthgrabber.activities import get_activities_data
from wealthgrabber.assets import get_assets_data
from wealthgrabber.snapshots import default_export_snapshot_path

SNAPSHOT_SCHEMA_VERSION = "1.0"


def _totals_from_positions(positions: list[Any]) -> dict[str, float]:
    """Calculate aggregate totals from position records."""
    portfolio_value = sum(float(p.market_value) for p in positions)
    book_value = sum(float(p.book_value) for p in positions)
    pnl = portfolio_value - book_value
    return {
        "portfolio_value": portfolio_value,
        "book_value": book_value,
        "pnl": pnl,
    }


def build_export_snapshot(
    ws: WealthsimpleAPI,
    *,
    show_zero_balances: bool = True,
    liquid_only: bool = False,
    not_liquid: bool = False,
    dividends_only: bool = False,
    activities_limit: int = 200,
    by_account: bool = True,
    currency: str = "CAD",
) -> dict[str, Any]:
    """Build a unified snapshot payload for downstream UIs."""
    accounts = get_accounts_data(
        ws,
        show_zero_balances=show_zero_balances,
        liquid_only=liquid_only,
        not_liquid=not_liquid,
    )
    activities = get_activities_data(
        ws,
        dividends_only=dividends_only,
        limit=activities_limit,
    )
    positions = get_assets_data(
        ws,
        by_account=by_account,
        currency=currency,
    )

    base_currency = (
        positions[0].currency
        if positions
        else (accounts[0].currency if accounts else currency)
    )

    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "accounts": [asdict(account) for account in accounts],
        "activities": [asdict(activity) for activity in activities],
        "positions": [asdict(position) for position in positions],
        "totals": _totals_from_positions(positions),
        "meta": {
            "base_currency": base_currency,
            "source": "wealthgrabber",
        },
    }


def save_export_snapshot(snapshot: dict[str, Any], out_path: Path | None = None) -> Path:
    """Persist export snapshot to disk and return the written path."""
    out_path = out_path or default_export_snapshot_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return out_path


def load_export_snapshot(snapshot_path: Path) -> dict[str, Any]:
    """Load snapshot JSON file."""
    return json.loads(snapshot_path.read_text(encoding="utf-8"))
