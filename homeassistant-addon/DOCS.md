# TalkAnchor Home-Assistant-Add-on

Schlanker Wrapper um das eigenständige
[TalkAnchor](https://github.com/martin141089/UniFi-Talk)-Docker-Image für
alle, die bereits Home Assistant im Netzwerk betreiben. Er übersetzt die
Konfigurations-UI dieses Add-ons in dieselbe `config.yaml`, die auch das
CLI-/Compose-Deployment nutzt, und startet dann denselben Polling-Loop +
Dashboard.

## Installation

1. Settings → Add-ons → Add-on Store → ⋮ → **Repositories** →
   `https://github.com/martin141089/UniFi-Talk` hinzufügen.
2. **TalkAnchor** im Store finden und installieren.
3. Add-on starten (die Konfiguration kann leer bleiben) und über die
   Seitenleiste (Ingress) öffnen.
4. Auf **„Setup-Wizard öffnen"** klicken und dem geführten Ablauf folgen
   (siehe unten) — er schreibt die Konfiguration direkt in die
   Add-on-Optionen, ganz ohne das HA-Konfigurationsformular von Hand
   auszufüllen.

## Geführter Setup-Wizard

Der interaktive CLI-Wizard (`talkanchor setup`) braucht ein Terminal, das
es im Add-on-Kontext nicht gibt. Der Web-Wizard unter `/wizard`
(erreichbar über den Button oben im Dashboard) bietet dieselbe Führung:

1. **Cloudflare** — Token, Account-ID, Tunnel-ID eintragen, Verbindung
   direkt testen.
2. **Fallback-Quelle** — HTTP-Echo-URL prüfen.
3. **UniFi Talk (SSH)** — Host, Port, Benutzer und den privaten Key
   eintragen; Key speichern; Host-Key abrufen, Fingerprint prüfen und
   bestätigen; anschließend den Sofia-Config-Pfad automatisch per SSH
   suchen lassen und aus der Trefferliste auswählen.
4. **Benachrichtigungen** — Kanal und Polling-Einstellungen.
5. **Zusammenfassung** — alle Werte im Überblick, **„Speichern
   (Dry-Run)"** schreibt die Konfiguration in die Add-on-Optionen und
   startet das Add-on neu, um sie zu übernehmen. Danach steht **„Jetzt
   Testlauf ausführen"** zur Verfügung. Erst nach getipptem `GO LIVE` lässt
   sich scharf schalten.

Der Wizard schreibt dabei direkt über die Home-Assistant-Supervisor-API in
die Add-on-Optionen (`hassio_api: true` im Manifest) — das manuelle
Ausfüllen des Konfigurationsformulars in den HA-Einstellungen ist nicht
mehr nötig, kann aber weiterhin genutzt werden.

## Konfiguration

Die folgende Tabelle ist zum Nachschlagen gedacht — der Setup-Wizard oben
ist der empfohlene Weg, sie auszufüllen.

| Option | Beschreibung |
|---|---|
| `dry_run` | Auf `true` lassen, bis ein paar Zyklen im Log geprüft wurden. |
| `poll_interval_seconds` / `min_seconds_between_changes` | Wie in der eigenständigen Konfiguration — siehe [CONFIGURATION.md](../CONFIGURATION.md). |
| `cloudflare_enabled` | Cloudflare als IP-Quelle nutzen (Standard: an). Bei Tunneln, die strukturell keine eindeutige IP liefern können (z. B. Multi-WAN-Setups mit mehreren gleichzeitig verbundenen Leitungen), auf `false` setzen — TalkAnchor läuft dann allein mit `http_echo_url`. |
| `cloudflare_api_token` / `cloudflare_account_id` / `cloudflare_tunnel_id` | Cloudflare-Tunnel-Connector-IP-Quelle. Token-Scope: Account → Cloudflare Tunnel → Read. Nur relevant, wenn `cloudflare_enabled` an ist. |
| `http_echo_url` | Fallback-IP-Quelle. |
| `unifi_host` / `unifi_ssh_port` / `unifi_ssh_user` | SSH-Verbindungsdetails zum UDM. |
| `unifi_ssh_private_key` | Den Inhalt des **privaten** Keys direkt einfügen (mehrzeilig). Nur Key-Auth — es gibt keine Passwort-Option. |
| `unifi_ssh_known_hosts_entry` | Die SSH-Host-Key-Zeile des UDM. Erforderlich — unbekannte Host-Keys werden abgelehnt statt beim ersten Kontakt vertraut. |
| `unifi_sofia_profile` / `unifi_config_path` | Name des Sofia-Profils und Pfad zu dessen XML auf dem UDM. |
| `unifi_backup_dir_remote` | Remote-Backup-Verzeichnis auf dem UDM. |
| `notify_channel` / `notify_ntfy_topic_url` / `notify_webhook_url` | Optionale Benachrichtigungen. Für Home-Assistant-Automatisierungen `notify_webhook_url` auf einen `webhook`-Trigger zeigen lassen und in HA selbst darauf reagieren. |

State, Historie und lokale Backup-Kopien werden unter `/data`
gespeichert, das der Supervisor über Add-on-Neustarts und -Updates hinweg
erhält.

Das Dashboard bietet außerdem einen Bereich „Diagnose" mit denselben
Prüfungen (Host-Key, Sofia-Pfad, Cloudflare) gegen die aktuell
*gespeicherte* Konfiguration — nützlich, um nach dem Setup erneut zu
prüfen, ob noch alles erreichbar ist.

## Haftungsausschluss

⚠️ Kein offizielles Ubiquiti-Produkt — siehe den Haftungsausschluss in der
Haupt-[SECURITY.md](../SECURITY.md). Mit `dry_run: true` beginnen.
