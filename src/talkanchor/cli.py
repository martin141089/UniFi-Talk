"""TalkAnchor CLI: `talkanchor setup|run|check|rollback|web`."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from talkanchor import __version__
from talkanchor.config import load_settings

app = typer.Typer(add_completion=False, help="TalkAnchor — Deine dynamische IP im Griff.")
console = Console()

CONFIG_PATH_OPTION = typer.Option("config.yaml", "--config", "-c", help="Pfad zur config.yaml")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Version anzeigen und beenden"),
) -> None:
    if version:
        console.print(f"talkanchor {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command()
def setup(config: str = CONFIG_PATH_OPTION) -> None:
    """Interaktiver Setup-Wizard: Quellen, SSH-Ziel, Benachrichtigungen, Dry-Run."""
    from talkanchor.wizard.prompts import run_wizard

    run_wizard(config)


@app.command()
def check(config: str = CONFIG_PATH_OPTION, verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Einen einzelnen Reconcile-Zyklus ausführen und beenden (auch für Cron/systemd-Timer geeignet)."""
    from talkanchor.core.factory import build_reconciler
    from talkanchor.core.logging_config import configure_logging

    configure_logging(level="DEBUG" if verbose else "INFO")
    settings = load_settings(config)
    reconciler = build_reconciler(settings)
    outcome = asyncio.run(reconciler.run_once())

    if outcome.event is not None:
        console.print(
            f"IP: {outcome.checked_ip} | changed={outcome.changed} | "
            f"apply_success={outcome.event.apply_success}"
        )
    else:
        console.print(
            f"IP: {outcome.checked_ip} | changed={outcome.changed} | "
            f"{outcome.skipped_reason or 'keine Änderung'}"
        )


@app.command()
def run(
    config: str = CONFIG_PATH_OPTION,
    with_web: bool = typer.Option(True, help="Dashboard zusätzlich zum Polling-Loop starten"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Dauerhaft laufender Dienst: Polling-Loop (+ optional Dashboard). Primärer Docker-Entrypoint."""
    from talkanchor.core.factory import build_reconciler
    from talkanchor.core.logging_config import configure_logging
    from talkanchor.core.scheduler import PollingScheduler

    settings = load_settings(config)
    configure_logging(
        level="DEBUG" if verbose else "INFO", log_file=Path(settings.data_dir) / "talkanchor.log"
    )

    if settings.dry_run:
        console.print("[yellow]DRY-RUN ist aktiv — es werden keine Änderungen am UniFi-Gerät vorgenommen.[/yellow]")

    reconciler = build_reconciler(settings)
    scheduler = PollingScheduler(reconciler, interval_seconds=settings.poll_interval_seconds)

    async def _main() -> None:
        scheduler.start()
        await scheduler.run_once_now()

        try:
            if with_web:
                import uvicorn

                from talkanchor.web.app import create_app

                web_app = create_app(settings, reconciler=reconciler, config_path=config)
                uv_config = uvicorn.Config(
                    web_app, host=settings.web_host, port=settings.web_port, log_level="warning"
                )
                server = uvicorn.Server(uv_config)
                await server.serve()
            else:
                await asyncio.Event().wait()
        finally:
            # Must happen before asyncio.run() below closes the event loop —
            # AsyncIOScheduler.shutdown() schedules cleanup on it via
            # call_soon_threadsafe, which raises "Event loop is closed" if
            # called after the fact (i.e. from an outer `finally`, once
            # asyncio.run() has already torn the loop down).
            scheduler.shutdown()

    asyncio.run(_main())


@app.command()
def web(config: str = CONFIG_PATH_OPTION) -> None:
    """Nur das Web-Dashboard starten, ohne den Polling-Loop."""
    import uvicorn

    from talkanchor.core.logging_config import configure_logging
    from talkanchor.web.app import create_app

    configure_logging(level="INFO")
    settings = load_settings(config)
    web_app = create_app(settings, config_path=config)
    uvicorn.run(web_app, host=settings.web_host, port=settings.web_port)


@app.command()
def rollback(config: str = CONFIG_PATH_OPTION) -> None:
    """Manuell auf das letzte erfolgreiche Backup zurückrollen."""
    from talkanchor.core.factory import build_target
    from talkanchor.core.state import StateStore

    settings = load_settings(config)
    state = StateStore(settings.state_db_path)
    events = state.recent_events(limit=20)
    target_event = next((e for e in events if e.apply_success and e.backup_path), None)
    if target_event is None or not target_event.backup_path:
        console.print("[yellow]Kein Backup zum Zurückrollen vorhanden.[/yellow]")
        raise typer.Exit(code=1)

    backup_path = target_event.backup_path
    if not typer.confirm(f"Auf Backup von {target_event.created_at} zurückrollen ({backup_path})?"):
        raise typer.Exit()

    target = build_target(settings)
    result = target.rollback(backup_path, dry_run=settings.dry_run)
    if result.success:
        console.print(f"[green]Rollback erfolgreich:[/green] {result.message}")
    else:
        console.print(f"[red]Rollback fehlgeschlagen:[/red] {result.message}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
