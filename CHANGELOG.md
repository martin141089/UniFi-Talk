# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei
dokumentiert.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dieses Projekt folgt [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-08-12

### Hinzugefügt

- Geführter Web-Setup-Wizard (`/wizard`), der den CLI-Wizard für
  Umgebungen ohne Terminal spiegelt: Schritte für Cloudflare, Fallback-
  Quelle, UniFi-SSH (inkl. Host-Key-Abruf mit Bestätigung und
  SSH-basierter Sofia-Config-Discovery) und Benachrichtigungen, jeweils
  inline testbar, mit abschließender Zusammenfassung, Dry-Run-Testlauf
  und explizit bestätigtem Scharfschalten. Schreibt im eigenständigen
  Betrieb direkt in `config.yaml` (Hot-Reload ohne Neustart) und im
  Home-Assistant-Add-on über die Supervisor-API in die Add-on-Optionen
  (automatischer Neustart zur Übernahme).
- Dashboard-Bereich „Diagnose" (vormals „Setup-Helfer"): SSH-Host-Key
  abrufen, Sofia-Config-Pfad suchen und die Cloudflare-Verbindung gegen
  die aktuell gespeicherte Konfiguration testen.

### Behoben

- Home-Assistant-Add-on-Repository lag zwei statt eine Ebene tief und
  wurde vom Supervisor nicht gefunden ("is not a valid app repository").
- Add-on-Options-Schema markierte Felder mit leerem Standardwert
  fälschlich als Pflichtfelder und blockierte dadurch das Speichern der
  Konfiguration.

## [0.1.0] - 2026-08-12

Erstes Alpha-Release.

### Hinzugefügt

- Reconcile-Loop mit zwei IP-Quellen: Cloudflare-Tunnel-Connector-IP
  (primär) wird gegen einen konfigurierbaren HTTP-Echo-Fallback
  gegengeprüft, beide müssen übereinstimmen, bevor gehandelt wird.
- UniFi-Talk-SSH-Zieladapter: Auth nur per Key mit Host-Key-Prüfung,
  zeitgestempelte Remote- und lokale Backups vor jedem Schreibzugriff,
  Sofia-XML-Patching, `fs_cli` reloadxml/Profil-Neustart,
  `sofia status`-Health-Check-Polling mit automatischem Rollback bei
  Fehlschlag, sowie Rate-Limiting gegen flatternde IPs.
- Dry-Run-Modus, standardmäßig aktiv.
- Austauschbare Benachrichtigungs-Adapter: ntfy, generischer Webhook,
  E-Mail.
- Interaktiver Setup-Wizard (`talkanchor setup`) mit SSH-basierter
  Sofia-Config-Erkennung und expliziter zweiter Bestätigung vor dem
  Scharfschalten.
- `talkanchor`-CLI: `setup`, `check`, `run`, `web`, `rollback`.
- Lokales Web-Dashboard: aktuelle IP, Health-Status, Änderungshistorie,
  Live-Log, manuelle Jetzt-prüfen-/Rollback-auf-Backup-Aktionen.
- Plugin-Architektur (`IPSource`-, `ConfigTarget`-, `Notifier`-Protokolle),
  sodass UniFi Talk ein Referenz-Ziel ist, nicht das einzig mögliche.
- Docker-Image + Compose-Datei; Multi-Arch-Veröffentlichung (amd64/arm64)
  zu GHCR bei getaggten Releases.
- Home-Assistant-Add-on-Wrapper.
- Vollständige Testsuite für den Kern-Reconcile-Loop mit In-Memory-Fakes
  (kein echtes Netzwerk/SSH nötig).

[Unreleased]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/martin141089/UniFi-Talk/releases/tag/v0.1.0
