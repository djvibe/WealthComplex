import json

from wealthgrabber.analyze import build_analysis, format_analysis


def _write_snapshot(base, category, rel_path, payload):
    path = base / "snapshots" / category / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_analysis_with_history(monkeypatch, tmp_path):
    monkeypatch.setenv("WEALTHGRABBER_DATA_DIR", str(tmp_path))

    _write_snapshot(
        tmp_path,
        "accounts",
        "2026/04/01/090000-000001.json",
        {
            "snapshot_type": "accounts",
            "created_at": "2026-04-01T09:00:00+00:00",
            "records": [{"value": 1000.0}, {"value": 500.0}],
        },
    )
    _write_snapshot(
        tmp_path,
        "accounts",
        "2026/04/08/090000-000001.json",
        {
            "snapshot_type": "accounts",
            "created_at": "2026-04-08T09:00:00+00:00",
            "records": [{"value": 2200.0}],
        },
    )
    _write_snapshot(
        tmp_path,
        "assets",
        "2026/04/08/091000-000001.json",
        {
            "snapshot_type": "assets",
            "created_at": "2026-04-08T09:10:00+00:00",
            "records": [
                {
                    "symbol": "AAA",
                    "market_value": 1500,
                    "book_value": 1000,
                    "pnl": 500,
                    "pnl_pct": 50,
                },
                {
                    "symbol": "BBB",
                    "market_value": 500,
                    "book_value": 700,
                    "pnl": -200,
                    "pnl_pct": -28.5,
                },
            ],
        },
    )
    _write_snapshot(
        tmp_path,
        "activities",
        "2026/04/08/092000-000001.json",
        {
            "snapshot_type": "activities",
            "created_at": "2026-04-08T09:20:00+00:00",
            "records": [
                {"activity_type": "DIY_DIVIDEND", "amount": 15.2, "sign": "+"},
                {"activity_type": "TRANSFER", "amount": 100, "sign": "+"},
            ],
        },
    )

    analysis = build_analysis(lookback_days=365)

    assert analysis["summary"]["portfolio_value"] == 2200
    assert analysis["summary"]["unrealized_pnl"] == 300
    assert analysis["summary"]["dividend_events"] == 1
    assert analysis["summary"]["dividend_total"] == 15.2
    assert analysis["summary"]["history_value_change"] == 700
    assert len(analysis["insights"]) >= 4


def test_format_analysis_json_and_csv():
    analysis = {
        "lookback_days": 30,
        "snapshot_counts": {"accounts": 1, "assets": 1, "activities": 1},
        "summary": {"portfolio_value": 1000.0, "unrealized_pnl": 20.0},
        "top_positions": [],
        "insights": ["test insight"],
    }

    json_out = format_analysis(analysis, output_format="json")
    parsed = json.loads(json_out)
    assert parsed["lookback_days"] == 30

    csv_out = format_analysis(analysis, output_format="csv")
    assert "metric,value" in csv_out
    assert "portfolio_value,1000.0" in csv_out
    assert "insight_1" in csv_out


def test_build_analysis_falls_back_to_export_history(monkeypatch, tmp_path):
    monkeypatch.setenv("WEALTHGRABBER_DATA_DIR", str(tmp_path))

    export_path = tmp_path / "exports" / "2026" / "04" / "08" / "093000-000001.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "generated_at": "2026-04-08T09:30:00+00:00",
                "accounts": [{"value": 3200.0}],
                "activities": [
                    {"activity_type": "DIVIDEND", "description": "Dividend", "amount": 22.5, "sign": "+"}
                ],
                "positions": [
                    {
                        "symbol": "BTC",
                        "market_value": 2500.0,
                        "book_value": 3000.0,
                        "pnl": -500.0,
                        "pnl_pct": -16.67,
                    }
                ],
                "totals": {"portfolio_value": 2500.0, "book_value": 3000.0, "pnl": -500.0},
                "meta": {"base_currency": "CAD", "source": "wealthgrabber"},
            }
        ),
        encoding="utf-8",
    )

    analysis = build_analysis(lookback_days=365)

    assert analysis["snapshot_counts"] == {"accounts": 1, "assets": 1, "activities": 1}
    assert analysis["summary"]["portfolio_value"] == 3200.0
    assert analysis["summary"]["market_value"] == 2500.0
    assert analysis["summary"]["dividend_total"] == 22.5
