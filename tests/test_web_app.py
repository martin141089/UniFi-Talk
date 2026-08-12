from __future__ import annotations

from fastapi.testclient import TestClient

from talkanchor.config import Settings
from talkanchor.core.reconciler import Reconciler
from talkanchor.core.state import StateStore
from talkanchor.web.app import create_app
from tests.fakes import FakeNotifier, FakeSource, FakeTarget


def make_client(tmp_path, *, target=None):
    settings = Settings(data_dir=str(tmp_path))
    state = StateStore(tmp_path / "state.sqlite3")
    reconciler = Reconciler(
        sources=[FakeSource("a", "1.2.3.4")],
        target=target or FakeTarget(),
        notifier=FakeNotifier(),
        state=state,
        dry_run=True,
        min_seconds_between_changes=300,
    )
    app = create_app(settings, state=state, reconciler=reconciler)
    return TestClient(app), state


def test_dashboard_renders(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert "TalkAnchor" in response.text


def test_status_empty_initially(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert body["current_ip"] is None
    assert body["dry_run"] is True


def test_check_now_records_history(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post("/api/check-now")
    assert response.status_code == 200
    assert response.json()["changed"] is True

    history = client.get("/api/history").json()
    assert len(history) == 1
    assert history[0]["new_ip"] == "1.2.3.4"


def test_rollback_without_backup_returns_404(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post("/api/rollback")
    assert response.status_code == 404


def test_logs_endpoint_returns_list(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.get("/api/logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
