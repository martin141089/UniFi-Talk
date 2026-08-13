from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import SecretStr

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


def test_dashboard_uses_relative_asset_paths(tmp_path):
    """No leading-slash hrefs/srcs — those 404 under Home Assistant Ingress,
    which serves the app under a path prefix. See _ingress_base()."""
    client, _ = make_client(tmp_path)
    response = client.get("/")
    assert 'href="/static' not in response.text
    assert 'src="/static' not in response.text
    assert '<base href="/" />' in response.text


def test_dashboard_base_href_reflects_ingress_path(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.get("/", headers={"X-Ingress-Path": "/api/hassio_ingress/sometoken"})
    assert '<base href="/api/hassio_ingress/sometoken/" />' in response.text


def test_wizard_page_uses_relative_asset_paths(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.get("/wizard")
    assert 'href="/static' not in response.text
    assert 'src="/static' not in response.text


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
    assert response.json()["started"] is True

    status = client.get("/api/check-now-status").json()
    assert status["running"] is False
    assert status["error"] is None
    assert status["result"]["changed"] is True

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


def test_setup_ssh_keyscan_requires_host(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post("/api/setup/ssh-keyscan")
    assert response.status_code == 400


def test_setup_ssh_keyscan_returns_line(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module

    settings = Settings(data_dir=str(tmp_path))
    settings.unifi_talk.host = "udm.example.internal"
    state = StateStore(tmp_path / "state.sqlite3")
    reconciler = Reconciler(
        sources=[FakeSource("a", "1.2.3.4")],
        target=FakeTarget(),
        notifier=FakeNotifier(),
        state=state,
        dry_run=True,
        min_seconds_between_changes=300,
    )
    monkeypatch.setattr(
        app_module, "fetch_host_key", lambda host, port: f"{host} ssh-ed25519 AAAAfake"
    )
    client = TestClient(app_module.create_app(settings, state=state, reconciler=reconciler))

    response = client.post("/api/setup/ssh-keyscan")
    assert response.status_code == 200
    assert response.json()["known_hosts_entry"] == "udm.example.internal ssh-ed25519 AAAAfake"


def test_setup_discover_sofia_returns_candidates(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module

    settings = Settings(data_dir=str(tmp_path))
    settings.unifi_talk.host = "udm.example.internal"
    state = StateStore(tmp_path / "state.sqlite3")
    reconciler = Reconciler(
        sources=[FakeSource("a", "1.2.3.4")],
        target=FakeTarget(),
        notifier=FakeNotifier(),
        state=state,
        dry_run=True,
        min_seconds_between_changes=300,
    )

    class FakeSSHClient:
        def close(self) -> None:
            pass

    monkeypatch.setattr(app_module, "connect_ssh", lambda **kwargs: FakeSSHClient())
    monkeypatch.setattr(
        app_module, "discover_sofia_configs", lambda client: ["/path/a.xml", "/path/b.xml"]
    )
    client = TestClient(app_module.create_app(settings, state=state, reconciler=reconciler))

    response = client.post("/api/setup/discover-sofia")
    assert response.status_code == 200
    assert response.json()["candidates"] == ["/path/a.xml", "/path/b.xml"]


def test_setup_cloudflare_test_requires_credentials(tmp_path):
    client, _ = make_client(tmp_path)
    response = client.post("/api/setup/cloudflare-test")
    assert response.status_code == 400


def test_setup_cloudflare_test_returns_ip(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module

    settings = Settings(data_dir=str(tmp_path))
    settings.cloudflare.api_token = SecretStr("tok")
    settings.cloudflare.account_id = "acc"
    settings.cloudflare.tunnel_id = "tun"
    state = StateStore(tmp_path / "state.sqlite3")
    reconciler = Reconciler(
        sources=[FakeSource("a", "1.2.3.4")],
        target=FakeTarget(),
        notifier=FakeNotifier(),
        state=state,
        dry_run=True,
        min_seconds_between_changes=300,
    )

    async def fake_check(self):
        return "198.51.100.9"

    monkeypatch.setattr(app_module.CloudflareTunnelSource, "check", fake_check)
    client = TestClient(app_module.create_app(settings, state=state, reconciler=reconciler))

    response = client.post("/api/setup/cloudflare-test")
    assert response.status_code == 200
    assert response.json()["ip"] == "198.51.100.9"
