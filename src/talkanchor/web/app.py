"""FastAPI dashboard: current IP, change history, live log, health status,
and manual "check now" / "rollback to last backup" actions.

Runs as a small local web app on the same host as the polling scheduler
(see `talkanchor.cli`); not meant to be exposed to the internet.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from talkanchor import __version__
from talkanchor.config import Settings
from talkanchor.core.factory import build_reconciler, build_target
from talkanchor.core.logging_config import live_log_handler
from talkanchor.core.reconciler import Reconciler
from talkanchor.core.state import ChangeEvent, StateStore
from talkanchor.targets.base import ConfigTargetError

_WEB_DIR = Path(__file__).parent


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


def create_app(settings: Settings, *, state: StateStore | None = None, reconciler: Reconciler | None = None) -> FastAPI:
    state = state or StateStore(settings.state_db_path)
    reconciler = reconciler or build_reconciler(settings, state=state)

    app = FastAPI(title="TalkAnchor Dashboard", version=__version__)
    app.mount("/static", StaticFiles(directory=_WEB_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=_WEB_DIR / "templates")

    app.state.settings = settings
    app.state.state_store = state
    app.state.reconciler = reconciler

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "version": __version__,
                "dry_run": settings.dry_run,
                "poll_interval_seconds": settings.poll_interval_seconds,
            },
        )

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
        outcome = await reconciler.run_once()
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

    return app
