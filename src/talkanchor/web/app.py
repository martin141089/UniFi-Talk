"""FastAPI dashboard: current IP, change history, live log, health status,
manual "check now" / "rollback to last backup" actions, and a guided setup
wizard (`/wizard`) for deployments with no terminal to run `talkanchor
setup` from — most notably the Home Assistant add-on.

Runs as a small local web app on the same host as the polling scheduler
(see `talkanchor.cli`); not meant to be exposed to the internet.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
from pathlib import Path
from typing import Any

import httpx
import paramiko
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from talkanchor import __version__
from talkanchor.config import Settings, load_settings
from talkanchor.core.factory import build_reconciler, build_target
from talkanchor.core.logging_config import live_log_handler
from talkanchor.core.reconciler import Reconciler
from talkanchor.core.state import ChangeEvent, StateStore
from talkanchor.sources.base import IPSourceError
from talkanchor.sources.cloudflare import CloudflareTunnelSource
from talkanchor.sources.cloudflare import verify_token as verify_cloudflare_token
from talkanchor.sources.http_echo import HttpEchoSource
from talkanchor.targets.base import ConfigTargetError
from talkanchor.targets.unifi_talk import connect_ssh, discover_sofia_configs, fetch_host_key
from talkanchor.wizard.writer import build_config_dict, write_config

logger = logging.getLogger("talkanchor.web")

_WEB_DIR = Path(__file__).parent
_SUPERVISOR_API = "http://supervisor"


def _ingress_base(request: Request) -> str:
    """Home Assistant's Ingress proxy serves this app under a per-install
    path prefix (e.g. /api/hassio_ingress/<token>) it passes along via the
    X-Ingress-Path header. Templates use this to set <base href> so that
    static assets, links, and fetch() calls — all written as relative URLs
    — resolve correctly under that prefix instead of 404ing against the
    Ingress proxy's own root. Outside Ingress (standalone/Docker) the
    header is absent and this is just "", giving the normal absolute root.
    """
    return request.headers.get("X-Ingress-Path", "").rstrip("/")


def _describe_token_shape(token: str) -> str:
    """Summarize a secret's shape without revealing most of it: length, a
    few characters at each end, and whether it contains anything outside
    printable ASCII (a strong sign of a mangled paste — e.g. a stray
    control character breaking HTTP header parsing).
    """
    control_chars = sorted({repr(ch) for ch in token if ord(ch) < 32 or ord(ch) > 126})
    shape = f"{len(token)} Zeichen (üblich sind 40), Anfang '{token[:6]}…', Ende '…{token[-6:]}'"
    if control_chars:
        shape += f", enthält nicht-druckbare Zeichen: {', '.join(control_chars)}"
    return shape


def _event_to_dict(event: ChangeEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "created_at": event.created_at.isoformat(),
        "old_ip": event.old_ip,
        "new_ip": event.new_ip,
        "dry_run": event.dry_run,
        "apply_success": event.apply_success,
        "apply_message": event.apply_message,
        "backup_path": event.backup_path,
        "health_ok": event.health_ok,
        "health_message": event.health_message,
        "rolled_back": event.rolled_back,
        "rollback_message": event.rollback_message,
    }


class SSHKeyRequest(BaseModel):
    private_key: str


class KnownHostsRequest(BaseModel):
    entry: str


class KeyscanRequest(BaseModel):
    host: str
    port: int = 22


class DiscoverRequest(BaseModel):
    host: str
    port: int = 22
    username: str = "root"


class CloudflareTestRequest(BaseModel):
    api_token: str
    account_id: str
    tunnel_id: str


class HttpEchoTestRequest(BaseModel):
    url: str
    json_field: str = "ip"


class WizardSaveRequest(BaseModel):
    dry_run: bool = True
    poll_interval_seconds: int = 300
    min_seconds_between_changes: int = 300
    cloudflare_api_token: str = ""
    cloudflare_account_id: str = ""
    cloudflare_tunnel_id: str = ""
    http_echo_url: str = "https://api.ipify.org?format=json"
    http_echo_json_field: str = "ip"
    unifi_host: str = ""
    unifi_ssh_port: int = 22
    unifi_ssh_user: str = "root"
    unifi_ssh_private_key: str = ""
    unifi_ssh_known_hosts_entry: str = ""
    unifi_sofia_profile: str = "external_talk"
    unifi_config_path: str = ""
    unifi_backup_dir_remote: str = "/root/talkanchor-backups"
    health_check_timeout_seconds: int = 30
    notify_channel: str = "none"
    notify_ntfy_topic_url: str = ""
    notify_webhook_url: str = ""


async def _restart_self(token: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            await client.post(
                f"{_SUPERVISOR_API}/addons/self/restart",
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError:
            logger.exception("Failed to trigger Home Assistant add-on self-restart")


def create_app(
    settings: Settings,
    *,
    state: StateStore | None = None,
    reconciler: Reconciler | None = None,
    config_path: str = "config.yaml",
) -> FastAPI:
    state = state or StateStore(settings.state_db_path)
    active_reconciler: Reconciler = reconciler or build_reconciler(settings, state=state)

    app = FastAPI(title="TalkAnchor Dashboard", version=__version__)
    app.mount("/static", StaticFiles(directory=_WEB_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=_WEB_DIR / "templates")

    app.state.settings = settings
    app.state.state_store = state
    app.state.reconciler = active_reconciler

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "version": __version__,
                "dry_run": settings.dry_run,
                "poll_interval_seconds": settings.poll_interval_seconds,
                "ingress_path": _ingress_base(request),
            },
        )

    @app.get("/wizard", response_class=HTMLResponse)
    async def wizard_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "wizard.html", {"version": __version__, "ingress_path": _ingress_base(request)}
        )

    @app.get("/api/wizard/prefill")
    async def wizard_prefill() -> dict[str, Any]:
        """Already-saved config, for the wizard to pre-fill on load.

        The wizard's own in-browser draft (localStorage) only survives in
        the same browser/tab — an Ingress session in a different app/tab,
        or the browser clearing site data, loses it even though the values
        were genuinely saved. This gives the wizard a server-side baseline
        to fall back to; the client-side draft (if any) still wins for
        anything edited more recently than the last save."""
        key_path = Path(settings.unifi_talk.ssh_key_path).expanduser()
        private_key = key_path.read_text(encoding="utf-8") if key_path.exists() else ""

        known_hosts_entry = ""
        known_hosts_path = Path("~/.ssh/known_hosts").expanduser()
        if known_hosts_path.exists() and settings.unifi_talk.host:
            prefix = f"{settings.unifi_talk.host} "
            for line in known_hosts_path.read_text(encoding="utf-8").splitlines():
                if line.startswith(prefix):
                    known_hosts_entry = line.strip()

        return {
            "dry_run": settings.dry_run,
            "poll_interval_seconds": settings.poll_interval_seconds,
            "min_seconds_between_changes": settings.min_seconds_between_changes,
            "cloudflare_api_token": settings.cloudflare.api_token.get_secret_value(),
            "cloudflare_account_id": settings.cloudflare.account_id,
            "cloudflare_tunnel_id": settings.cloudflare.tunnel_id,
            "http_echo_url": settings.http_echo.url,
            "http_echo_json_field": settings.http_echo.json_field,
            "unifi_host": settings.unifi_talk.host,
            "unifi_ssh_port": settings.unifi_talk.ssh_port,
            "unifi_ssh_user": settings.unifi_talk.ssh_user,
            "unifi_ssh_private_key": private_key,
            "unifi_ssh_known_hosts_entry": known_hosts_entry,
            "unifi_sofia_profile": settings.unifi_talk.sofia_profile,
            "unifi_config_path": settings.unifi_talk.config_path,
            "unifi_backup_dir_remote": settings.unifi_talk.backup_dir_remote,
            "health_check_timeout_seconds": settings.unifi_talk.health_check_timeout_seconds,
            "notify_channel": settings.notify.channel,
            "notify_ntfy_topic_url": settings.notify.ntfy_topic_url,
            "notify_webhook_url": settings.notify.webhook_url,
        }

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        last_ip = state.get_last_known_ip()
        last_change_at = state.last_change_at()
        recent = state.recent_events(limit=1)
        return {
            "current_ip": last_ip,
            "last_change_at": last_change_at.isoformat() if last_change_at else None,
            "dry_run": settings.dry_run,
            "poll_interval_seconds": settings.poll_interval_seconds,
            "last_event": _event_to_dict(recent[0]) if recent else None,
        }

    @app.get("/api/history")
    async def history(limit: int = 20) -> list[dict[str, Any]]:
        return [_event_to_dict(event) for event in state.recent_events(limit=limit)]

    @app.get("/api/logs")
    async def logs() -> list[dict[str, str]]:
        return list(live_log_handler.records)

    @app.post("/api/check-now")
    async def check_now() -> dict[str, Any]:
        outcome = await active_reconciler.run_once()
        return {
            "checked_ip": outcome.checked_ip,
            "changed": outcome.changed,
            "rate_limited": outcome.rate_limited,
            "skipped_reason": outcome.skipped_reason,
            "event": _event_to_dict(outcome.event) if outcome.event else None,
        }

    @app.post("/api/rollback")
    async def rollback() -> dict[str, Any]:
        events = state.recent_events(limit=20)
        target_event = next((e for e in events if e.apply_success and e.backup_path), None)
        if target_event is None or not target_event.backup_path:
            raise HTTPException(status_code=404, detail="No backup available to roll back to")

        target = build_target(settings)
        try:
            result = await asyncio.to_thread(target.rollback, target_event.backup_path, dry_run=settings.dry_run)
        except ConfigTargetError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return {"success": result.success, "message": result.message, "restored_from": target_event.backup_path}

    # -- quick diagnostics ----------------------------------------------------
    # Re-tests/re-discovers against the currently loaded config.yaml/options —
    # useful after setup to confirm things still work. For first-time setup,
    # use the guided wizard below instead (it doesn't require anything to be
    # saved yet).

    @app.post("/api/setup/ssh-keyscan")
    async def setup_ssh_keyscan() -> dict[str, str]:
        cfg = settings.unifi_talk
        if not cfg.host:
            raise HTTPException(status_code=400, detail="unifi_host ist nicht konfiguriert.")
        try:
            line = await asyncio.to_thread(fetch_host_key, cfg.host, cfg.ssh_port)
        except OSError as exc:
            raise HTTPException(
                status_code=502, detail=f"Verbindung zu {cfg.host}:{cfg.ssh_port} fehlgeschlagen: {exc}"
            ) from exc
        return {"known_hosts_entry": line}

    @app.post("/api/setup/discover-sofia")
    async def setup_discover_sofia() -> dict[str, list[str]]:
        cfg = settings.unifi_talk

        def _discover() -> list[str]:
            client = connect_ssh(host=cfg.host, port=cfg.ssh_port, username=cfg.ssh_user, key_path=cfg.ssh_key_path)
            try:
                return discover_sofia_configs(client)
            finally:
                client.close()

        try:
            candidates = await asyncio.to_thread(_discover)
        except ConfigTargetError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"candidates": candidates}

    @app.post("/api/setup/cloudflare-test")
    async def setup_cloudflare_test() -> dict[str, str]:
        cf = settings.cloudflare
        if not (cf.api_token.get_secret_value() and cf.account_id and cf.tunnel_id):
            raise HTTPException(status_code=400, detail="Cloudflare-Zugangsdaten sind nicht vollständig konfiguriert.")
        source = CloudflareTunnelSource(
            api_token=cf.api_token.get_secret_value(), account_id=cf.account_id, tunnel_id=cf.tunnel_id
        )
        try:
            ip = await source.check()
        except IPSourceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"ip": ip}

    # -- guided setup wizard ----------------------------------------------------
    # Mirrors `talkanchor setup` (the CLI wizard) as a step-by-step web flow for
    # deployments with no terminal — mainly the Home Assistant add-on, reached
    # via its Ingress sidebar entry. Each step tests/persists as you go (SSH key
    # and host key are written immediately so later steps can use them, exactly
    # like the CLI wizard expects them already on disk); the final "save" step
    # either writes config.yaml directly (standalone) or, when running under
    # the HA Supervisor, pushes the values into this add-on's own options and
    # triggers a restart so they take effect.

    @app.post("/api/wizard/ssh-key")
    async def wizard_ssh_key(body: SSHKeyRequest) -> dict[str, str]:
        key_path = Path(settings.unifi_talk.ssh_key_path).expanduser()
        key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        key_path.write_text(body.private_key.strip() + "\n", encoding="utf-8")
        key_path.chmod(0o600)
        return {"path": str(key_path)}

    @app.post("/api/wizard/ssh-generate-key")
    async def wizard_ssh_generate_key() -> dict[str, str]:
        """Generate a passphrase-less keypair for the user instead of making
        them run ssh-keygen themselves — TalkAnchor runs unattended, so a
        passphrase-protected key would never be usable anyway. Only the
        public half needs to leave this endpoint's response for the user to
        copy into UniFi; the private half is written straight to disk."""

        def _generate() -> tuple[str, str]:
            key = paramiko.RSAKey.generate(3072)
            buf = io.StringIO()
            key.write_private_key(buf)
            return buf.getvalue(), f"ssh-rsa {key.get_base64()} talkanchor"

        private_key, public_key = await asyncio.to_thread(_generate)
        key_path = Path(settings.unifi_talk.ssh_key_path).expanduser()
        key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        key_path.write_text(private_key, encoding="utf-8")
        key_path.chmod(0o600)
        return {"path": str(key_path), "private_key": private_key, "public_key": public_key}

    @app.post("/api/wizard/known-hosts")
    async def wizard_known_hosts(body: KnownHostsRequest) -> dict[str, bool]:
        known_hosts = Path("~/.ssh/known_hosts").expanduser()
        known_hosts.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with known_hosts.open("a", encoding="utf-8") as fh:
            fh.write(body.entry.strip() + "\n")
        return {"success": True}

    @app.post("/api/wizard/ssh-keyscan")
    async def wizard_ssh_keyscan(body: KeyscanRequest) -> dict[str, str]:
        try:
            line = await asyncio.to_thread(fetch_host_key, body.host, body.port)
        except OSError as exc:
            raise HTTPException(
                status_code=502, detail=f"Verbindung zu {body.host}:{body.port} fehlgeschlagen: {exc}"
            ) from exc
        return {"known_hosts_entry": line}

    @app.post("/api/wizard/discover-sofia")
    async def wizard_discover_sofia(body: DiscoverRequest) -> dict[str, list[str]]:
        key_path = settings.unifi_talk.ssh_key_path

        def _discover() -> list[str]:
            client = connect_ssh(host=body.host, port=body.port, username=body.username, key_path=key_path)
            try:
                return discover_sofia_configs(client)
            finally:
                client.close()

        try:
            candidates = await asyncio.to_thread(_discover)
        except ConfigTargetError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"candidates": candidates}

    @app.post("/api/wizard/cloudflare-test")
    async def wizard_cloudflare_test(body: CloudflareTestRequest) -> dict[str, str]:
        if not (body.api_token and body.account_id and body.tunnel_id):
            raise HTTPException(status_code=400, detail="Bitte Token, Account-ID und Tunnel-ID ausfüllen.")
        source = CloudflareTunnelSource(api_token=body.api_token, account_id=body.account_id, tunnel_id=body.tunnel_id)
        try:
            ip = await source.check()
        except IPSourceError as exc:
            token_problem = await verify_cloudflare_token(body.api_token)
            token_len_hint = f"Erhaltener Token: {_describe_token_shape(body.api_token)}."
            if token_problem:
                detail = f"{token_problem} {token_len_hint}"
            else:
                detail = (
                    f"Der API-Token ist bei Cloudflare gültig, aber der Zugriff auf Account-ID "
                    f"'{body.account_id}' / Tunnel-ID '{body.tunnel_id}' schlägt fehl. Bitte IDs und den "
                    f"Berechtigungs-Scope des Tokens (Account → Cloudflare Tunnel → Read, richtiger Account "
                    f"unter 'Account Resources') prüfen. Ursprünglicher Fehler: {exc}"
                )
            raise HTTPException(status_code=502, detail=detail) from exc
        return {"ip": ip}

    @app.post("/api/wizard/http-echo-test")
    async def wizard_http_echo_test(body: HttpEchoTestRequest) -> dict[str, str]:
        source = HttpEchoSource(body.url, json_field=body.json_field or None)
        try:
            ip = await source.check()
        except IPSourceError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"ip": ip}

    @app.post("/api/wizard/save")
    async def wizard_save(body: WizardSaveRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
        nonlocal settings, active_reconciler
        supervisor_token = os.environ.get("SUPERVISOR_TOKEN")

        if supervisor_token:
            ha_options = {
                "dry_run": body.dry_run,
                "poll_interval_seconds": body.poll_interval_seconds,
                "min_seconds_between_changes": body.min_seconds_between_changes,
                "cloudflare_api_token": body.cloudflare_api_token,
                "cloudflare_account_id": body.cloudflare_account_id,
                "cloudflare_tunnel_id": body.cloudflare_tunnel_id,
                "http_echo_url": body.http_echo_url,
                "unifi_host": body.unifi_host,
                "unifi_ssh_port": body.unifi_ssh_port,
                "unifi_ssh_user": body.unifi_ssh_user,
                "unifi_ssh_private_key": body.unifi_ssh_private_key,
                "unifi_ssh_known_hosts_entry": body.unifi_ssh_known_hosts_entry,
                "unifi_sofia_profile": body.unifi_sofia_profile,
                "unifi_config_path": body.unifi_config_path,
                "unifi_backup_dir_remote": body.unifi_backup_dir_remote,
                "health_check_timeout_seconds": body.health_check_timeout_seconds,
                "notify_channel": body.notify_channel,
                "notify_ntfy_topic_url": body.notify_ntfy_topic_url,
                "notify_webhook_url": body.notify_webhook_url,
            }
            async with httpx.AsyncClient(timeout=15) as client:
                try:
                    response = await client.post(
                        f"{_SUPERVISOR_API}/addons/self/options",
                        json={"options": ha_options},
                        headers={"Authorization": f"Bearer {supervisor_token}"},
                    )
                except httpx.HTTPError as exc:
                    raise HTTPException(status_code=502, detail=f"Supervisor nicht erreichbar: {exc}") from exc
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=502, detail=f"Supervisor lehnte die Optionen ab: {response.text[:300]}"
                )

            background_tasks.add_task(_restart_self, supervisor_token)
            return {
                "mode": "supervisor",
                "message": "Gespeichert. Das Add-on wird neu gestartet, um die Konfiguration zu übernehmen.",
            }

        answers = {
            "dry_run": body.dry_run,
            "poll_interval_seconds": body.poll_interval_seconds,
            "min_seconds_between_changes": body.min_seconds_between_changes,
            "data_dir": settings.data_dir,
            "cloudflare_api_token": body.cloudflare_api_token,
            "cloudflare_account_id": body.cloudflare_account_id,
            "cloudflare_tunnel_id": body.cloudflare_tunnel_id,
            "http_echo_url": body.http_echo_url,
            "http_echo_json_field": body.http_echo_json_field,
            "unifi_host": body.unifi_host,
            "unifi_ssh_port": body.unifi_ssh_port,
            "unifi_ssh_user": body.unifi_ssh_user,
            "unifi_ssh_key_path": settings.unifi_talk.ssh_key_path,
            "unifi_sofia_profile": body.unifi_sofia_profile,
            "unifi_config_path": body.unifi_config_path,
            "unifi_backup_dir_remote": body.unifi_backup_dir_remote,
            "unifi_health_check_timeout_seconds": body.health_check_timeout_seconds,
            "notify_channel": body.notify_channel,
            "notify_ntfy_topic_url": body.notify_ntfy_topic_url,
            "notify_webhook_url": body.notify_webhook_url,
            "web_host": settings.web_host,
            "web_port": settings.web_port,
        }
        write_config(build_config_dict(answers), config_path)

        settings = load_settings(config_path)
        active_reconciler = build_reconciler(settings, state=state)
        app.state.settings = settings
        app.state.reconciler = active_reconciler
        return {"mode": "file", "message": f"Gespeichert nach {config_path}."}

    return app
