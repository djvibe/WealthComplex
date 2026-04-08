"""Portfolio analysis command based on persisted snapshots."""

from __future__ import annotations

import json
from typing import Any

from .snapshots import (
    SNAPSHOT_ACCOUNTS,
    SNAPSHOT_ACTIVITIES,
    SNAPSHOT_ASSETS,
    load_snapshots,
)

DIVIDEND_MARKERS = ("DIVIDEND", "DISTRIBUTION")


def _latest_records(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not snapshots:
        return []
    latest = snapshots[-1]
    records = latest.get("records", [])
    return records if isinstance(records, list) else []


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def build_analysis(lookback_days: int = 90) -> dict[str, Any]:
    """Build analysis summary and insight list from historical snapshots."""
    account_snaps = load_snapshots(SNAPSHOT_ACCOUNTS, lookback_days)
    asset_snaps = load_snapshots(SNAPSHOT_ASSETS, lookback_days)
    activity_snaps = load_snapshots(SNAPSHOT_ACTIVITIES, lookback_days)

    latest_accounts = _latest_records(account_snaps)
    latest_assets = _latest_records(asset_snaps)

    total_value = sum(_safe_float(acc.get("value")) for acc in latest_accounts)
    total_market_value = sum(_safe_float(pos.get("market_value")) for pos in latest_assets)
    total_book_value = sum(_safe_float(pos.get("book_value")) for pos in latest_assets)
    total_pnl = total_market_value - total_book_value
    total_pnl_pct = (total_pnl / total_book_value * 100.0) if total_book_value else 0.0

    sorted_assets = sorted(
        latest_assets,
        key=lambda p: _safe_float(p.get("market_value")),
        reverse=True,
    )
    top_positions = []
    for pos in sorted_assets[:5]:
        mv = _safe_float(pos.get("market_value"))
        weight = (mv / total_market_value * 100.0) if total_market_value else 0.0
        top_positions.append(
            {
                "symbol": pos.get("symbol", "N/A"),
                "market_value": mv,
                "weight_pct": weight,
                "pnl_pct": _safe_float(pos.get("pnl_pct")),
            }
        )

    top_1 = sum(p["weight_pct"] for p in top_positions[:1])
    top_3 = sum(p["weight_pct"] for p in top_positions[:3])
    top_5 = sum(p["weight_pct"] for p in top_positions[:5])

    losers = [pos for pos in latest_assets if _safe_float(pos.get("pnl")) < 0]
    losers_mv = sum(_safe_float(pos.get("market_value")) for pos in losers)
    losers_weight = (losers_mv / total_market_value * 100.0) if total_market_value else 0.0

    dividend_events = 0
    dividend_total = 0.0
    for snap in activity_snaps:
        records = snap.get("records", [])
        if not isinstance(records, list):
            continue
        for act in records:
            if not isinstance(act, dict):
                continue
            act_type = str(act.get("activity_type", "")).upper()
            description = str(act.get("description", "")).upper()
            sign = str(act.get("sign", ""))
            if any(marker in act_type or marker in description for marker in DIVIDEND_MARKERS):
                amount = _safe_float(act.get("amount"))
                if sign == "-":
                    amount *= -1
                if amount > 0:
                    dividend_events += 1
                    dividend_total += amount

    total_history_values = []
    for snap in account_snaps:
        records = snap.get("records", [])
        if not isinstance(records, list):
            continue
        total_history_values.append(sum(_safe_float(acc.get("value")) for acc in records))

    value_change = 0.0
    value_change_pct = 0.0
    if len(total_history_values) >= 2:
        start_value = total_history_values[0]
        end_value = total_history_values[-1]
        value_change = end_value - start_value
        value_change_pct = (value_change / start_value * 100.0) if start_value else 0.0

    insights: list[str] = []
    if total_value <= 0:
        insights.append("No account value data found yet. Run list/assets commands to build history.")
    else:
        insights.append(f"Portfolio value is {total_value:,.2f} based on your latest account snapshot.")

    insights.append(
        f"Unrealized P&L is {total_pnl:,.2f} ({total_pnl_pct:+.2f}%) across current positions."
    )
    insights.append(
        f"Concentration: top 1 = {top_1:.1f}%, top 3 = {top_3:.1f}%, top 5 = {top_5:.1f}% of holdings."
    )

    if top_1 >= 25:
        insights.append("Risk flag: your largest position exceeds 25% of invested assets.")

    insights.append(
        f"Loss exposure: {len(losers)} positions are negative, representing {losers_weight:.1f}% of market value."
    )
    insights.append(
        f"Dividend activity (last {lookback_days}d): {dividend_events} events totaling {dividend_total:,.2f}."
    )

    if len(total_history_values) >= 2:
        insights.append(
            f"Portfolio value changed by {value_change:,.2f} ({value_change_pct:+.2f}%) over stored history window."
        )

    return {
        "lookback_days": lookback_days,
        "snapshot_counts": {
            "accounts": len(account_snaps),
            "assets": len(asset_snaps),
            "activities": len(activity_snaps),
        },
        "summary": {
            "portfolio_value": total_value,
            "market_value": total_market_value,
            "book_value": total_book_value,
            "unrealized_pnl": total_pnl,
            "unrealized_pnl_pct": total_pnl_pct,
            "top_1_weight_pct": top_1,
            "top_3_weight_pct": top_3,
            "top_5_weight_pct": top_5,
            "losers_count": len(losers),
            "losers_weight_pct": losers_weight,
            "dividend_events": dividend_events,
            "dividend_total": dividend_total,
            "history_value_change": value_change,
            "history_value_change_pct": value_change_pct,
        },
        "top_positions": top_positions,
        "insights": insights,
    }


def format_analysis(analysis: dict[str, Any], output_format: str = "table") -> str:
    """Format analysis payload for CLI display."""
    if output_format == "json":
        return json.dumps(analysis, indent=2)

    if output_format == "csv":
        lines = ["metric,value"]
        for key, value in analysis.get("summary", {}).items():
            lines.append(f"{key},{value}")
        for i, msg in enumerate(analysis.get("insights", []), start=1):
            escaped = str(msg).replace('"', '""')
            lines.append(f"insight_{i},\"{escaped}\"")
        return "\n".join(lines)

    summary = analysis.get("summary", {})
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("Portfolio Analysis")
    lines.append("=" * 80)
    lines.append(f"Lookback (days): {analysis.get('lookback_days')}")
    counts = analysis.get("snapshot_counts", {})
    lines.append(
        "Snapshots loaded: "
        f"accounts={counts.get('accounts', 0)}, "
        f"assets={counts.get('assets', 0)}, "
        f"activities={counts.get('activities', 0)}"
    )
    lines.append("-" * 80)
    lines.append(f"Portfolio Value:      {summary.get('portfolio_value', 0.0):>15,.2f}")
    lines.append(f"Unrealized P&L:      {summary.get('unrealized_pnl', 0.0):>15,.2f}")
    lines.append(f"Unrealized P&L %:    {summary.get('unrealized_pnl_pct', 0.0):>14.2f}%")
    lines.append(f"Top 1 Weight:        {summary.get('top_1_weight_pct', 0.0):>14.2f}%")
    lines.append(f"Top 3 Weight:        {summary.get('top_3_weight_pct', 0.0):>14.2f}%")
    lines.append(f"Loss Exposure:       {summary.get('losers_weight_pct', 0.0):>14.2f}%")
    lines.append(f"Dividend Total:      {summary.get('dividend_total', 0.0):>15,.2f}")

    top_positions = analysis.get("top_positions", [])
    if top_positions:
        lines.append("-" * 80)
        lines.append("Top Positions")
        for pos in top_positions:
            lines.append(
                f"- {pos.get('symbol', 'N/A'):>8}: "
                f"{pos.get('market_value', 0.0):>12,.2f} "
                f"({pos.get('weight_pct', 0.0):.2f}%)"
            )

    lines.append("-" * 80)
    lines.append("Insights")
    for msg in analysis.get("insights", []):
        lines.append(f"* {msg}")

    lines.append("=" * 80)
    return "\n".join(lines)


def print_analysis(lookback_days: int = 90, output_format: str = "table") -> None:
    """Build and print portfolio analysis."""
    analysis = build_analysis(lookback_days=lookback_days)
    print(format_analysis(analysis, output_format=output_format))
