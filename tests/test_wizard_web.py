from __future__ import annotations

from fastapi.testclient import TestClient

from talkanchor.config import Settings
from talkanchor.core.reconciler import Reconciler
from talkanchor.core.state import StateStore
from talkanchor.web.app import create_app
from tests.fakes import FakeNotifier, FakeSource, FakeTarget


def make_wizard_client(tmp_path, monkeypatch, *, config_path=None):
    monkeypatch.setenv("HOME", str(tmp_path))
    settings = Settings(data_dir=str(tmp_path))
    state = StateStore(tmp_path / "state.sqlite3")
    reconciler = Reconciler(
        sources=[FakeSource("a", "1.2.3.4")],
        target=FakeTarget(),
        notifier=FakeNotifier(),
        state=state,
        dry_run=True,
        min_seconds_between_changes=300,
    )
    app = create_app(
        settings,
        state=state,
        reconciler=reconciler,
        config_path=str(config_path or tmp_path / "config.yaml"),
    )
    return TestClient(app), settings


def test_wizard_page_renders(tmp_path, monkeypatch):
    client, _ = make_wizard_client(tmp_path, monkeypatch)
    response = client.get("/wizard")
    assert response.status_code == 200
    assert "Setup-Wizard" in response.text


def test_wizard_ssh_key_written_to_disk(tmp_path, monkeypatch):
    client, settings = make_wizard_client(tmp_path, monkeypatch)
    response = client.post("/api/wizard/ssh-key", json={"private_key": "FAKE-KEY-CONTENT"})
    assert response.status_code == 200
    key_path = response.json()["path"]
    with open(key_path) as fh:
        assert "FAKE-KEY-CONTENT" in fh.read()


def test_wizard_known_hosts_appends(tmp_path, monkeypatch):
    client, _ = make_wizard_client(tmp_path, monkeypatch)
    response = client.post("/api/wizard/known-hosts", json={"entry": "udm.local ssh-ed25519 AAAAfake"})
    assert response.status_code == 200
    known_hosts = tmp_path / ".ssh" / "known_hosts"
    assert "udm.local ssh-ed25519 AAAAfake" in known_hosts.read_text()


def test_wizard_ssh_keyscan(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module

    monkeypatch.setattr(app_module, "fetch_host_key", lambda host, port: f"{host} ssh-ed25519 AAAAfake")
    client, _ = make_wizard_client(tmp_path, monkeypatch)
    response = client.post("/api/wizard/ssh-keyscan", json={"host": "udm.local", "port": 22})
    assert response.status_code == 200
    assert response.json()["known_hosts_entry"] == "udm.local ssh-ed25519 AAAAfake"


def test_wizard_discover_sofia(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module

    class FakeSSHClient:
        def close(self) -> None:
            pass

    monkeypatch.setattr(app_module, "connect_ssh", lambda **kwargs: FakeSSHClient())
    monkeypatch.setattr(app_module, "discover_sofia_configs", lambda client: ["/a.xml"])
    client, _ = make_wizard_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/wizard/discover-sofia", json={"host": "udm.local", "port": 22, "username": "root"}
    )
    assert response.status_code == 200
    assert response.json()["candidates"] == ["/a.xml"]


def test_wizard_cloudflare_test(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module

    async def fake_check(self):
        return "198.51.100.9"

    monkeypatch.setattr(app_module.CloudflareTunnelSource, "check", fake_check)
    client, _ = make_wizard_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/wizard/cloudflare-test",
        json={"api_token": "tok", "account_id": "acc", "tunnel_id": "tun"},
    )
    assert response.status_code == 200
    assert response.json()["ip"] == "198.51.100.9"


def test_wizard_cloudflare_test_diagnoses_invalid_token(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module
    from talkanchor.sources.base import IPSourceError

    async def fake_check(self):
        raise IPSourceError("Cloudflare API returned HTTP 400: ...9106...")

    async def fake_verify_token(api_token, **kwargs):
        return "Cloudflare lehnt den Token selbst ab (HTTP 400): [{'code': 1000, 'message': 'Invalid API Token'}]"

    monkeypatch.setattr(app_module.CloudflareTunnelSource, "check", fake_check)
    monkeypatch.setattr(app_module, "verify_cloudflare_token", fake_verify_token)
    client, _ = make_wizard_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/wizard/cloudflare-test",
        json={"api_token": "short-token", "account_id": "acc", "tunnel_id": "tun"},
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "lehnt den Token selbst ab" in detail
    assert "11 Zeichen" in detail


def test_wizard_cloudflare_test_diagnoses_permission_issue(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module
    from talkanchor.sources.base import IPSourceError

    async def fake_check(self):
        raise IPSourceError("Cloudflare API reported failure: [...]")

    async def fake_verify_token(api_token, **kwargs):
        return None

    monkeypatch.setattr(app_module.CloudflareTunnelSource, "check", fake_check)
    monkeypatch.setattr(app_module, "verify_cloudflare_token", fake_verify_token)
    client, _ = make_wizard_client(tmp_path, monkeypatch)
    response = client.post(
        "/api/wizard/cloudflare-test",
        json={"api_token": "valid-token", "account_id": "acc", "tunnel_id": "tun"},
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "gültig, aber der Zugriff" in detail
    assert "acc" in detail and "tun" in detail


def test_wizard_http_echo_test(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module

    async def fake_check(self):
        return "203.0.113.5"

    monkeypatch.setattr(app_module.HttpEchoSource, "check", fake_check)
    client, _ = make_wizard_client(tmp_path, monkeypatch)
    response = client.post("/api/wizard/http-echo-test", json={"url": "https://example.invalid", "json_field": "ip"})
    assert response.status_code == 200
    assert response.json()["ip"] == "203.0.113.5"


def test_wizard_save_writes_config_file_and_hot_reloads(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    client, _ = make_wizard_client(tmp_path, monkeypatch, config_path=config_path)

    response = client.post(
        "/api/wizard/save",
        json={
            "dry_run": True,
            "cloudflare_api_token": "tok",
            "cloudflare_account_id": "acc",
            "cloudflare_tunnel_id": "tun",
            "unifi_host": "udm.local",
            "unifi_config_path": "/x.xml",
            "notify_channel": "none",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "file"
    assert config_path.exists()

    status = client.get("/api/status").json()
    assert status["dry_run"] is True


def test_wizard_save_uses_supervisor_api_when_token_present(tmp_path, monkeypatch):
    import talkanchor.web.app as app_module

    monkeypatch.setenv("SUPERVISOR_TOKEN", "sup-tok")
    calls = []

    class FakeResponse:
        status_code = 200
        text = "{}"

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append({"url": url, "json": kwargs.get("json")})
            return FakeResponse()

    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeAsyncClient)
    client, _ = make_wizard_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/wizard/save",
        json={"dry_run": True, "unifi_host": "udm.local", "notify_channel": "none"},
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "supervisor"
    # First call is the options POST; a second (fire-and-forget) restart call
    # may follow via BackgroundTasks — only the first call is asserted on.
    assert calls[0]["url"] == "http://supervisor/addons/self/options"
    assert calls[0]["json"]["options"]["unifi_host"] == "udm.local"
