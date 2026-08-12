# Beitragen zu TalkAnchor

Danke, dass du einen Beitrag in Erwägung ziehst! TalkAnchor ist bewusst um
eine schlanke Plugin-Architektur herum gebaut, sodass die meisten Beiträge
den Kern-Reconcile-Loop gar nicht anfassen müssen.

## Entwicklungsumgebung einrichten

```sh
git clone https://github.com/martin141089/UniFi-Talk.git talkanchor
cd talkanchor
uv venv .venv && uv pip install -e ".[dev]" --python .venv/bin/python
.venv/bin/pytest
.venv/bin/ruff check src tests
.venv/bin/mypy src
```

(Ein normales `venv`/`pip install -e ".[dev]"` funktioniert genauso —
`uv` ist nur schneller.)

## Projektstruktur

```
src/talkanchor/
├── core/       # Polling-Loop, State, Reconcile-/Diff-Logik — nur Protokolle, keine I/O-Adapter
├── sources/    # IP-Quellen-Adapter (implementieren IPSource)
├── targets/    # Config-Ziel-Adapter (implementieren ConfigTarget)
├── notify/     # Benachrichtigungs-Adapter (implementieren Notifier)
├── wizard/     # interaktive Setup-CLI
└── web/        # FastAPI-Dashboard
```

## Einen neuen IP-Quellen-Adapter hinzufügen

Das `IPSource`-Protokoll aus `talkanchor.sources.base` implementieren:

```python
class MySource:
    name = "my_source"

    async def check(self) -> str:
        """Gibt die aktuelle öffentliche IP als String zurück, oder wirft IPSourceError."""
```

In `talkanchor.core.factory.build_sources` hinter einem eigenen
Config-Abschnitt in `talkanchor.config` registrieren und Tests nach dem
Vorbild von `tests/test_sources.py` ergänzen (HTTP-Schicht mocken, in der
CI keine echten Endpunkte ansprechen).

## Einen neuen Config-Ziel-Adapter hinzufügen

Das `ConfigTarget`-Protokoll aus `talkanchor.targets.base` implementieren:
`apply(new_ip, *, dry_run) -> ApplyResult`,
`health_check() -> HealthCheckResult`, `rollback(backup_path, *, dry_run) ->
RollbackResult`. `unifi_talk.py` ist die Referenzimplementierung — dort
lässt sich die erwartete Form ablesen (Dry-Run fasst nie das Netzwerk an,
apply() sichert immer vor dem Schreiben, health_check() fragt mit Timeout
ab).

Nicht verhandelbar für jeden neuen Ziel-Adapter, passend zum
Sicherheitskonzept von TalkAnchor (siehe [SECURITY.md](SECURITY.md)):

- Nur Key-basierte Authentifizierung — keine Klartext-Passwort-Felder.
- Backup vor jedem Schreibzugriff, mit einem Weg zum Zurückrollen.
- `dry_run=True` muss ein echtes No-op sein (im Idealfall überhaupt keine Verbindung).

## Einen neuen Benachrichtigungs-Adapter hinzufügen

Das `Notifier`-Protokoll aus `talkanchor.notify.base` implementieren
(`async def send(self, notification: Notification) -> None`) und in
`talkanchor.notify.build_notifier` einbinden.

## Code-Stil

- Ruff fürs Linting (`ruff check`), mypy für die Typprüfung — beides läuft
  in der CI und muss bestehen.
- Kleine, fokussierte Adapter bevorzugen statt Konfigurations-Flags in
  bestehenden Adaptern.
- Tests verwenden Fakes (siehe `tests/fakes.py`) für den Kern-Loop — keine
  echten Netzwerk-/SSH-Aufrufe in Unit-Tests.

## Pull Requests

- PRs auf jeweils einen Adapter/eine Funktion fokussieren.
- Tests für neue Adapter beilegen.
- `CHANGELOG.md` unter „Unreleased" aktualisieren.
