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
3. Konfiguration ausfüllen (siehe unten), Add-on starten und über die
   Seitenleiste (Ingress) oder `http://<ha-host>:8420` öffnen.

## Konfiguration

| Option | Beschreibung |
|---|---|
| `dry_run` | Auf `true` lassen, bis ein paar Zyklen im Log geprüft wurden. |
| `poll_interval_seconds` / `min_seconds_between_changes` | Wie in der eigenständigen Konfiguration — siehe [CONFIGURATION.md](../CONFIGURATION.md). |
| `cloudflare_api_token` / `cloudflare_account_id` / `cloudflare_tunnel_id` | Cloudflare-Tunnel-Connector-IP-Quelle. Token-Scope: Account → Cloudflare Tunnel → Read. |
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

### Setup-Helfer (kein Terminal nötig)

Der interaktive CLI-Wizard (`talkanchor setup`) braucht ein Terminal, das
es im Add-on-Kontext nicht gibt. Stattdessen bietet das Dashboard
(Ingress-Seitenleiste, Bereich „Setup-Helfer") dieselben SSH-Schritte als
Buttons an:

1. `unifi_host`, `unifi_ssh_user`, `unifi_ssh_private_key` ausfüllen, speichern, Add-on neu starten.
2. Im Dashboard **„SSH-Host-Key abrufen"** klicken, den angezeigten Fingerprint prüfen und die Zeile in `unifi_ssh_known_hosts_entry` eintragen, speichern, neu starten.
3. **„Sofia-Config-Pfad suchen"** klicken, den passenden Pfad in `unifi_config_path` eintragen.
4. **„Cloudflare-Verbindung testen"**, um `cloudflare_api_token`/`cloudflare_account_id`/`cloudflare_tunnel_id` zu prüfen.

Jeder Schritt wirkt auf die zuletzt gespeicherte und aktive Konfiguration
— nach jeder Änderung erst speichern und das Add-on neu starten, bevor der
nächste Schritt ausgeführt wird.

## Haftungsausschluss

⚠️ Kein offizielles Ubiquiti-Produkt — siehe den Haftungsausschluss in der
Haupt-[SECURITY.md](../SECURITY.md). Mit `dry_run: true` beginnen.
