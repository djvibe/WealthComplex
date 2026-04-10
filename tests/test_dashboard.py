from wealthgrabber.dashboard import render_dashboard_html, write_dashboard


def test_render_dashboard_embeds_json_payload_safely():
    html = render_dashboard_html(
        {
            "schema_version": "1.0",
            "generated_at": "2026-04-10T00:00:00+00:00",
            "accounts": [],
            "activities": [{"description": 'quote " and </script> tag'}],
            "positions": [],
            "totals": {},
            "meta": {},
        }
    )

    assert 'type="application/json"' in html
    assert "document.getElementById('snapshot-data').textContent" in html
    assert "&quot;" not in html
    assert "<\\/script>" in html


def test_write_dashboard_defaults_to_dated_history_and_updates_latest(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("WEALTHGRABBER_DATA_DIR", str(tmp_path))

    written = write_dashboard({"schema_version": "1.0", "totals": {}, "meta": {}})

    assert written.exists()
    assert written.parent.parent.parent.parent == tmp_path / "dashboards"

    latest = tmp_path / "dashboard" / "index.html"
    assert latest.exists()
    assert latest.read_text(encoding="utf-8") == written.read_text(encoding="utf-8")
