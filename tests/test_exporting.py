from unittest.mock import MagicMock, patch

from wealthgrabber.exporting import build_export_snapshot
from wealthgrabber.models import AccountData, ActivityData, PositionData


def test_build_export_snapshot_structure():
    ws = MagicMock()

    with (
        patch(
            "wealthgrabber.exporting.get_accounts_data",
            return_value=[
                AccountData(
                    description="TFSA",
                    number="TFSA-001",
                    value=1000.0,
                    currency="CAD",
                )
            ],
        ),
        patch(
            "wealthgrabber.exporting.get_activities_data",
            return_value=[
                ActivityData(
                    date="2026-01-01",
                    activity_type="DIVIDEND",
                    description="Dividend",
                    amount=10.0,
                    currency="CAD",
                    sign="+",
                    account_label="TFSA (TFSA-001)",
                )
            ],
        ),
        patch(
            "wealthgrabber.exporting.get_assets_data",
            return_value=[
                PositionData(
                    symbol="AAPL",
                    name="Apple",
                    quantity=2.0,
                    market_value=500.0,
                    book_value=400.0,
                    currency="CAD",
                    pnl=100.0,
                    pnl_pct=25.0,
                    account_label="TFSA (TFSA-001)",
                )
            ],
        ),
    ):
        payload = build_export_snapshot(ws)

    assert payload["schema_version"] == "1.0"
    assert "generated_at" in payload
    assert payload["totals"]["portfolio_value"] == 500.0
    assert payload["totals"]["book_value"] == 400.0
    assert payload["totals"]["pnl"] == 100.0
    assert payload["meta"]["base_currency"] == "CAD"
    assert len(payload["accounts"]) == 1
    assert len(payload["activities"]) == 1
    assert len(payload["positions"]) == 1
