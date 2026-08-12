"""Interactive setup wizard.

Walks the user through Cloudflare, UniFi Talk SSH, notification, and safety
settings, offers SSH-based discovery of the Sofia config file, writes
config.yaml, and — only after a successful dry-run test the user can review
— optionally flips dry_run off with an explicit second confirmation.

Secrets are never printed back or logged; config.yaml is written with 0600
permissions and is already covered by .gitignore.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from talkanchor.config import Settings, load_settings
from talkanchor.core.factory import build_reconciler
from talkanchor.core.state import StateStore
from talkanchor.wizard.writer import build_config_dict, write_config

console = Console()

DISCLAIMER = (
    "[bold yellow]Kein offizielles Ubiquiti-Produkt.[/bold yellow] TalkAnchor verändert eine von "
    "der UniFi-Talk-Anwendung verwaltete, nicht offiziell dokumentierte Konfigurationsdatei über "
    "SSH. Nutzung erfolgt auf eigene Verantwortung. Vor dem ersten produktiven Einsatz unbedingt "
    "den Dry-Run-Modus nutzen und ein aktuelles Backup deines UniFi-Systems vorhalten."
)


def _non_empty(text: str) -> bool | str:
    return True if text.strip() else "Darf nicht leer sein."


def run_wizard(config_path: str = "config.yaml") -> None:
    console.print(
        Panel.fit(
            "[bold cyan]TalkAnchor[/bold cyan] — Setup-Wizard",
            subtitle="Deine dynamische IP im Griff.",
        )
    )
    console.print(Panel(DISCLAIMER, border_style="yellow"))

    answers: dict[str, Any] = {}

    console.rule("Cloudflare Tunnel (primäre IP-Quelle)")
    console.print(
        "Erstelle ein API-Token mit minimalem Scope: [bold]Account -> Cloudflare Tunnel -> Read[/bold]."
    )
    answers["cloudflare_api_token"] = questionary.password("Cloudflare API-Token:").ask() or ""
    answers["cloudflare_account_id"] = questionary.text(
        "Cloudflare Account-ID:", validate=_non_empty
    ).ask()
    answers["cloudflare_tunnel_id"] = questionary.text(
        "Cloudflare Tunnel-ID:", validate=_non_empty
    ).ask()

    console.rule("Fallback IP-Quelle (Plausibilitätsprüfung)")
    answers["http_echo_url"] = questionary.text(
        "Fallback HTTP-IP-Echo-URL:", default="https://api.ipify.org?format=json"
    ).ask()
    answers["http_echo_json_field"] = questionary.text(
        "JSON-Feld mit der IP (leer lassen für Klartext-Antwort):", default="ip"
    ).ask()

    console.rule("UniFi Talk (SSH-Ziel)")
    answers["unifi_host"] = questionary.text("UDM-Hostname oder IP:", validate=_non_empty).ask()
    answers["unifi_ssh_port"] = int(questionary.text("SSH-Port:", default="22").ask())
    answers["unifi_ssh_user"] = questionary.text("SSH-Benutzer:", default="root").ask()
    answers["unifi_ssh_key_path"] = questionary.path(
        "Pfad zum privaten SSH-Key (kein Passwort-Login):", default="~/.ssh/id_ed25519"
    ).ask()
    answers["unifi_sofia_profile"] = questionary.text(
        "Name des Sofia-Profils:", default="external_talk"
    ).ask()
    answers["unifi_backup_dir_remote"] = questionary.text(
        "Remote-Backup-Verzeichnis auf dem UDM:", default="/root/talkanchor-backups"
    ).ask()
    answers["unifi_health_check_timeout_seconds"] = int(
        questionary.text("Health-Check-Timeout (Sekunden):", default="30").ask()
    )
    expected_raw = questionary.text(
        "Erwartete Registrierungen zur Health-Check-Prüfung, kommagetrennt (optional):", default=""
    ).ask()
    answers["unifi_expected_registrations"] = [
        item.strip() for item in expected_raw.split(",") if item.strip()
    ]

    answers["unifi_config_path"] = _resolve_config_path(answers)

    console.rule("Polling & Sicherheit")
    answers["poll_interval_seconds"] = int(
        questionary.text("Polling-Intervall (Sekunden):", default="300").ask()
    )
    answers["min_seconds_between_changes"] = int(
        questionary.text(
            "Minimale Zeit zwischen zwei Änderungen (Sekunden, Rate-Limit):", default="300"
        ).ask()
    )
    answers["data_dir"] = questionary.text("Lokales Datenverzeichnis:", default="./data").ask()

    console.rule("Benachrichtigungen")
    channel = questionary.select(
        "Benachrichtigungskanal:",
        choices=["none", "ntfy", "webhook", "email"],
        default="none",
    ).ask()
    answers["notify_channel"] = channel
    if channel == "ntfy":
        answers["notify_ntfy_topic_url"] = questionary.text(
            "ntfy Topic-URL (z. B. https://ntfy.sh/mein-topic):", validate=_non_empty
        ).ask()
    elif channel == "webhook":
        answers["notify_webhook_url"] = questionary.text("Webhook-URL:", validate=_non_empty).ask()
    elif channel == "email":
        answers["notify_email_to"] = questionary.text("Empfänger-E-Mail:", validate=_non_empty).ask()
        answers["notify_email_smtp_host"] = questionary.text("SMTP-Host:", validate=_non_empty).ask()
        answers["notify_email_smtp_port"] = int(questionary.text("SMTP-Port:", default="587").ask())
        answers["notify_email_smtp_user"] = questionary.text("SMTP-Benutzer:", default="").ask()
        answers["notify_email_smtp_password"] = questionary.password("SMTP-Passwort:").ask() or ""

    console.rule("Dashboard")
    answers["web_host"] = questionary.text("Dashboard bind-Adresse:", default="0.0.0.0").ask()
    answers["web_port"] = int(questionary.text("Dashboard-Port:", default="8420").ask())

    # Dry-run is always ON at first write — going live is a separate, explicit step below.
    answers["dry_run"] = True

    config_dict = build_config_dict(answers)
    _print_summary(config_dict)

    write_config(config_dict, config_path)
    console.print(f"\n[green]Konfiguration gespeichert:[/green] {config_path} (dry_run: true)")

    if questionary.confirm("Jetzt einen Dry-Run-Testlauf ausführen?", default=True).ask():
        _run_dry_run_test(config_path)

    if questionary.confirm(
        "Möchtest du jetzt scharf schalten (dry_run -> false)? Nur bestätigen, wenn der Testlauf "
        "oben plausibel aussah.",
        default=False,
    ).ask():
        confirmation = questionary.text(
            'Zur Bestätigung bitte "GO LIVE" eintippen:'
        ).ask()
        if confirmation == "GO LIVE":
            config_dict["dry_run"] = False
            write_config(config_dict, config_path)
            console.print("[bold green]Scharf geschaltet.[/bold green] dry_run ist jetzt false.")
        else:
            console.print("[yellow]Abgebrochen — dry_run bleibt true.[/yellow]")
    else:
        console.print(
            "dry_run bleibt [bold]true[/bold]. Führe den Wizard später erneut aus, "
            "wenn du bereit bist, scharf zu schalten."
        )


def _resolve_config_path(answers: dict[str, Any]) -> str:
    if not questionary.confirm(
        "Sofia-Config-Pfad per SSH auf dem UDM suchen lassen (empfohlen)?", default=True
    ).ask():
        return questionary.text("Pfad zur Sofia-Profil-XML:", validate=_non_empty).ask()

    import paramiko

    from talkanchor.targets.unifi_talk import discover_sofia_configs

    console.print(f"Verbinde per SSH zu {answers['unifi_ssh_user']}@{answers['unifi_host']} ...")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    known_hosts = Path("~/.ssh/known_hosts").expanduser()
    if known_hosts.exists():
        client.load_host_keys(str(known_hosts))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())

    try:
        client.connect(
            hostname=answers["unifi_host"],
            port=answers["unifi_ssh_port"],
            username=answers["unifi_ssh_user"],
            key_filename=str(Path(answers["unifi_ssh_key_path"]).expanduser()),
            timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )
        candidates = discover_sofia_configs(client)
    except Exception as exc:  # noqa: BLE001 - surfaced directly to the interactive user
        console.print(f"[red]Discovery fehlgeschlagen:[/red] {exc}")
        console.print(
            f"Falls dies der erste Verbindungsversuch ist, füge den Host-Key hinzu: "
            f"ssh-keyscan -H {answers['unifi_host']} >> ~/.ssh/known_hosts"
        )
        return questionary.text("Pfad zur Sofia-Profil-XML (manuell):", validate=_non_empty).ask()
    finally:
        client.close()

    if not candidates:
        console.print("[yellow]Keine sofia*.xml-Dateien gefunden.[/yellow]")
        return questionary.text("Pfad zur Sofia-Profil-XML (manuell):", validate=_non_empty).ask()

    choice = questionary.select(
        "Gefundene Kandidaten — welcher ist das externe Sofia-Profil?",
        choices=[*candidates, "Manuell eingeben..."],
    ).ask()
    if choice == "Manuell eingeben...":
        return questionary.text("Pfad zur Sofia-Profil-XML:", validate=_non_empty).ask()
    return choice


def _print_summary(config_dict: dict[str, Any]) -> None:
    table = Table(title="Zusammenfassung", show_header=True, header_style="bold cyan")
    table.add_column("Einstellung")
    table.add_column("Wert")
    table.add_row("Dry-Run", "AN (Standard)")
    cf = config_dict["cloudflare"]
    table.add_row("Cloudflare Account/Tunnel", f"{cf['account_id']} / {cf['tunnel_id']}")
    table.add_row("Fallback-Quelle", config_dict["http_echo"]["url"])
    table.add_row("UniFi Host", config_dict["unifi_talk"]["host"])
    table.add_row("Sofia-Profil", config_dict["unifi_talk"]["sofia_profile"])
    table.add_row("Config-Pfad", config_dict["unifi_talk"]["config_path"])
    table.add_row("Polling-Intervall", f"{config_dict['poll_interval_seconds']}s")
    table.add_row("Rate-Limit", f"{config_dict['min_seconds_between_changes']}s")
    table.add_row("Benachrichtigung", config_dict["notify"]["channel"])
    console.print(table)


def _run_dry_run_test(config_path: str) -> None:
    settings: Settings = load_settings(config_path)
    state = StateStore(settings.state_db_path)
    reconciler = build_reconciler(settings, state=state)
    console.print("\n[bold]Führe Dry-Run-Testlauf aus...[/bold]")
    outcome = asyncio.run(reconciler.run_once())
    if outcome.skipped_reason and not outcome.changed:
        console.print(f"[yellow]Testlauf konnte keine eindeutige IP ermitteln:[/yellow] {outcome.skipped_reason}")
    elif outcome.event is not None:
        console.print(f"[green]Ermittelte IP:[/green] {outcome.checked_ip}")
        console.print(f"[green]Simulierte Aktion:[/green] {outcome.event.apply_message}")
    else:
        console.print(f"IP unverändert: {outcome.checked_ip}")
