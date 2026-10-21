import json
from datetime import datetime, timedelta, timezone

from watch.main import window_start

NOW = datetime(2026, 10, 21, 2, 0, tzinfo=timezone.utc)


def test_window_defaults_to_24h(tmp_path):
    assert window_start(NOW, tmp_path / "missing.json") == NOW - timedelta(hours=24)


def test_window_uses_last_run(tmp_path):
    state = tmp_path / "state.json"
    last = NOW - timedelta(hours=30)
    state.write_text(json.dumps({"last_run": last.isoformat()}))
    assert window_start(NOW, state) == last
