# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei
dokumentiert.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dieses Projekt folgt [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.3] - 2026-08-14

### Hinzugefügt

- Dashboard-Verlauf zeigt nur noch die letzten 3 Einträge, mit „Weitere
  Verläufe laden"-Button zum Nachladen.
- Änderungshistorie wird automatisch auf die letzten 90 Einträge begrenzt.

### Geändert

- Reihenfolge im Dashboard: „Verlauf" steht jetzt vor „Diagnose".
- Changelog aufgeräumt: knappere, sachliche Einträge statt
  ausführlicher Fehlerbeschreibungen.

## [0.2.2] - 2026-08-14

### Behoben

- Health-Check nutzte einen fs_cli-Befehl, der so nicht existiert
  (`sofia status profile <profil> gateway`); Gateway-Registrierungen
  werden nur über das unskopierte `sofia status gateway` gemeldet.
- Verlaufstabelle im Dashboard und Wizard-Zusammenfassung liefen auf
  schmalen Bildschirmen über den Rand.

## [0.2.1] - 2026-08-13

### Behoben

- Logo in der Add-on-Dokumentation wurde von Home Assistants
  In-App-Doku-Viewer nicht angezeigt (kein `<picture>`-Support, keine
  Bildpfade außerhalb des Add-on-Ordners).

## [0.2.0] - 2026-08-13

### Geändert

- Logo/Icon im Home-Assistant-Add-on: korrekt zentriert, transparenter
  Hintergrund statt weißer Fläche; jetzt auch in der Add-on-Dokumentation
  sichtbar.
- Alle nutzersichtbaren Meldungen (Anwenden/Health-Check/Rollback,
  Benachrichtigungen, Log-Zeilen) durchgängig auf Deutsch.
- README und Add-on-Dokumentation ausführlicher und
  einsteigerfreundlicher, mit Inhaltsverzeichnis.
- Dashboard und Wizard für schmale Bildschirme optimiert.

## [0.1.19] - 2026-08-13

### Behoben

- Ein Dry-Run-Speichervorgang nach einem zurückgerollten scharfen Zyklus
  wurde fälschlich als bereits übernommene Änderung gewertet und hätte
  den nötigen Korrekturversuch dauerhaft unterdrückt.

## [0.1.18] - 2026-08-13

### Geändert

- `/api/check-now` läuft jetzt im Hintergrund statt die Anfrage bis zum
  Ende des Health-Checks offen zu halten — verhindert Verbindungsabbrüche
  bei hohem `health_check_timeout_seconds` durch Proxy/Browser-Timeouts.
  Dashboard und Wizard pollen das Ergebnis über einen neuen
  `/api/check-now-status`-Endpoint.

## [0.1.17] - 2026-08-13

### Behoben

- Health-Check fragte Endpunkt-Registrierungen statt der tatsächlich
  relevanten Gateway-Registrierungen zum SIP-Provider ab und wurde bei
  reinen Trunk-Profilen nie gesund.

## [0.1.16] - 2026-08-13

### Behoben

- Nach einem per Health-Check ausgelösten Rollback hielt TalkAnchor die
  verworfene neue IP fälschlich für bereits übernommen und hätte den
  zurückgerollten Zustand nie von selbst korrigiert.

## [0.1.15] - 2026-08-13

### Geändert

- Cloudflare-API-Token-Feld im Wizard ist kein maskiertes Passwortfeld
  mehr (iOS Safari ersetzte es trotz `autocomplete="off"` wiederholt
  durch ein gespeichertes Passwort).

## [0.1.14] - 2026-08-13

### Behoben

- Privater SSH-Schlüssel verlor beim Speichern über Home Assistants
  generisches Konfigurationsformular seine Zeilenumbrüche und wird jetzt
  beim Add-on-Start automatisch repariert.
- Sofia-Config-Suche im Wizard wählte bei mehreren Treffern blind den
  ersten statt des zum konfigurierten Profilnamen passenden.

## [0.1.13] - 2026-08-13

### Behoben

- Sofia-Config-Suche fand nur FreeSWITCHs generische Loader-Datei statt
  der eigentlichen Profildatei mit den IP-Parametern; sucht jetzt zuerst
  nach Dateiinhalt statt nur nach Dateiname.
- Fehlgeschlagenes Anwenden legte trotzdem ein Backup an.
- Wiederkehrender Traceback beim Neustart des Diensts behoben.

## [0.1.12] - 2026-08-13

### Hinzugefügt

- Schalter „Cloudflare-Tunnel-Connector-IP als Quelle verwenden"
  (`cloudflare_enabled`) für Tunnel, die strukturell keine eindeutige IP
  liefern können (z. B. Multi-WAN).

## [0.1.11] - 2026-08-13

### Behoben

- Wizard lädt beim Öffnen zusätzlich die bereits gespeicherte
  Konfiguration direkt vom Server statt sich nur auf den lokalen
  Browser-Entwurf zu verlassen.

## [0.1.10] - 2026-08-13

### Hinzugefügt

- Wizard-Eingaben werden laufend im Browser zwischengespeichert und bei
  erneutem Öffnen automatisch wiederhergestellt.

## [0.1.9] - 2026-08-13

### Behoben

- Irreführende Paramiko-Fehlermeldung bei abgelehnter SSH-Authentifizierung
  ("encountered RSA key, expected OPENSSH key") durch eine klare Meldung
  ersetzt.

## [0.1.8] - 2026-08-13

### Hinzugefügt

- Knopf „Schlüssel automatisch erzeugen" im SSH-Schritt des Wizards —
  kein Terminal mehr nötig, nur die öffentliche Zeile zum Einfügen bei
  UniFi wird angezeigt.

## [0.1.7] - 2026-08-13

### Behoben

- Warnhinweis am Cloudflare-Token-Feld: der Tunnel-Connector-Token ist
  nicht dasselbe wie das benötigte API-Token.

## [0.1.6] - 2026-08-13

### Hinzugefügt

- „Anzeigen"-Knopf am Cloudflare-Token-Feld sowie eine sichere
  Kurzform des empfangenen Tokens in der Fehlermeldung zur
  Copy-Paste-Diagnose.

## [0.1.5] - 2026-08-13

### Behoben

- Cloudflare-Token-Feld erkennt und entfernt automatisch ein
  versehentlich mitkopiertes `Bearer <token>`-Präfix.

## [0.1.4] - 2026-08-13

### Hinzugefügt

- Cloudflare-Verbindungstest im Wizard unterscheidet jetzt zwischen
  ungültigem Token und gültigem Token ohne Zugriff auf Account/Tunnel.

## [0.1.3] - 2026-08-13

### Behoben

- Dashboard und Wizard waren unter Home Assistants Ingress-Proxy
  ungestylt (absolute statt relative Asset-/API-Pfade).

## [0.1.2] - 2026-08-12

### Hinzugefügt

- Geführter Web-Setup-Wizard (`/wizard`) als Pendant zum CLI-Wizard für
  Umgebungen ohne Terminal (insbesondere das Home-Assistant-Add-on).

## [0.1.1] - 2026-08-12

### Hinzugefügt

- Dashboard-Bereich „Setup-Helfer" (SSH-Host-Key, Sofia-Config-Pfad,
  Cloudflare-Verbindungstest) als Web-Ersatz für die SSH-Schritte des
  CLI-Wizards.

### Behoben

- Home-Assistant-Add-on-Repository wurde vom Supervisor nicht gefunden.
- Options-Schema markierte optionale Felder fälschlich als Pflichtfelder.

## [0.1.0] - 2026-08-12

Erstes Alpha-Release.

### Hinzugefügt

- Reconcile-Loop mit zwei IP-Quellen (Cloudflare-Tunnel-Connector-IP +
  HTTP-Echo-Fallback), die vor jeder Aktion übereinstimmen müssen.
- UniFi-Talk-SSH-Zieladapter: Key-Auth mit Host-Key-Prüfung, Backups vor
  jedem Schreibzugriff, Sofia-XML-Patching, Health-Check mit
  automatischem Rollback, Rate-Limiting.
- Dry-Run-Modus, standardmäßig aktiv.
- Austauschbare Benachrichtigungs-Adapter: ntfy, Webhook, E-Mail.
- Interaktiver Setup-Wizard (`talkanchor setup`).
- `talkanchor`-CLI: `setup`, `check`, `run`, `web`, `rollback`.
- Lokales Web-Dashboard: aktuelle IP, Health-Status, Änderungshistorie,
  Live-Log, manuelle Aktionen.
- Plugin-Architektur (`IPSource`, `ConfigTarget`, `Notifier`).
- Docker-Image + Compose-Datei, Multi-Arch-Veröffentlichung zu GHCR.
- Home-Assistant-Add-on-Wrapper.
- Vollständige Testsuite mit In-Memory-Fakes.

[Unreleased]: https://github.com/martin141089/UniFi-Talk/compare/v0.2.3...HEAD
[0.2.3]: https://github.com/martin141089/UniFi-Talk/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/martin141089/UniFi-Talk/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/martin141089/UniFi-Talk/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.19...v0.2.0
[0.1.19]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.18...v0.1.19
[0.1.18]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.17...v0.1.18
[0.1.17]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.16...v0.1.17
[0.1.16]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.15...v0.1.16
[0.1.15]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.14...v0.1.15
[0.1.14]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.13...v0.1.14
[0.1.13]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.12...v0.1.13
[0.1.12]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.11...v0.1.12
[0.1.11]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.10...v0.1.11
[0.1.10]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.9...v0.1.10
[0.1.9]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/martin141089/UniFi-Talk/releases/tag/v0.1.0
