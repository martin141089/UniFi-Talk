# Konfigurationsreferenz

TalkAnchor liest Einstellungen aus `config.yaml` und lässt Umgebungsvariablen
anschließend jeden Wert darin überschreiben (siehe `.env.example`). Der
einfachste Weg, eine erste `config.yaml` zu erzeugen, ist `talkanchor setup`
(siehe [README-Schnellstart](README.md#schnellstart)) — dieses Dokument ist
die Referenz für jedes Feld, wenn du etwas von Hand nachjustieren willst.

Umgebungsvariablen verwenden das Präfix `TALKANCHOR_` und einen doppelten
Unterstrich (`__`) für verschachtelte Felder, z. B.
`TALKANCHOR_CLOUDFLARE__API_TOKEN`.

## Oberste Ebene

| Schlüssel | Env-Var | Standard | Beschreibung |
|---|---|---|---|
| `dry_run` | `TALKANCHOR_DRY_RUN` | `true` | Wenn true, berechnet und protokolliert TalkAnchor, was es *tun würde*, öffnet aber nie eine SSH-Verbindung und schreibt nichts. So lange aktiviert lassen, bis du ein paar Zyklen geprüft hast. |
| `poll_interval_seconds` | `TALKANCHOR_POLL_INTERVAL_SECONDS` | `300` | Wie oft der Scheduler die IP-Quellen prüft. |
| `min_seconds_between_changes` | `TALKANCHOR_MIN_SECONDS_BETWEEN_CHANGES` | `300` | Mindestabstand zwischen zwei scharfen Änderungen (Rate-Limit / Anti-Flapping). Eine früher erkannte Änderung wird zurückgestellt und im nächsten Zyklus erneut versucht, nicht verworfen. |
| `data_dir` | `TALKANCHOR_DATA_DIR` | `./data` | Lokales Verzeichnis für die SQLite-State-DB, lokale Backup-Kopien und die Log-Datei. |
| `web_host` / `web_port` | `TALKANCHOR_WEB_HOST` / `TALKANCHOR_WEB_PORT` | `0.0.0.0` / `8420` | Bind-Adresse/Port des Dashboards. Nicht für die direkte Veröffentlichung im Internet gedacht — bei Fernzugriff hinter ein eigenes VPN/Reverse-Proxy stellen. |

## `cloudflare` — primäre IP-Quelle

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `enabled` | `true` | Cloudflare überhaupt als Quelle nutzen. Auf `false` setzen, wenn der Tunnel strukturell nie eine eindeutige IP liefern kann (z. B. ein Tunnel, der gleichzeitig über mehrere WAN-Leitungen verbunden ist) — TalkAnchor läuft dann allein mit `http_echo`, ohne `api_token`/`account_id`/`tunnel_id` löschen zu müssen. |
| `api_token` | — | Cloudflare-API-Token. Minimaler Scope: **Account → Cloudflare Tunnel → Read**. |
| `account_id` | — | Deine Cloudflare-Account-ID. |
| `tunnel_id` | — | Die ID des Tunnels, dessen Connector-IP verfolgt werden soll. |

TalkAnchor ruft `GET /accounts/{account_id}/cfd_tunnel/{tunnel_id}/connections`
auf und liest die `origin_ip` jedes aktiven Connectors aus. Wenn sich
Connectors uneinig sind (kann während eines Failovers passieren, oder
dauerhaft bei einem über mehrere WAN-Leitungen verbundenen Tunnel),
verweigert TalkAnchor in diesem Zyklus eine Aktion, statt zu raten — in
letzterem Fall hilft nur `enabled: false`.

## `http_echo` — Fallback-IP-Quelle

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `url` | `https://api.ipify.org?format=json` | Beliebiger „Was ist meine IP"-HTTP-Endpunkt. |
| `json_field` | `ip` | JSON-Feld, das die IP enthält. Leer lassen, um den gesamten Antworttext als Klartext zu behandeln. |

Sind beide Quellen aktiv (Cloudflare `enabled` und vollständig konfiguriert),
müssen sie bei der aktuellen IP übereinstimmen, bevor TalkAnchor handelt —
das ist die Plausibilitätsprüfung, die vor einer einzelnen fehlerhaften
Quelle schützt. Mit `cloudflare.enabled: false` läuft TalkAnchor bewusst
nur mit dieser einen Quelle.

## `unifi_talk` — SSH-Ziel

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `host` | — | UDM-Hostname oder IP. |
| `ssh_port` | `22` | |
| `ssh_user` | `root` | |
| `ssh_key_path` | `~/.ssh/id_ed25519` | Pfad zum privaten Key. **Nur Key-Auth — es gibt kein Passwort-Feld.** |
| `sofia_profile` | `external_talk` | Name des FreeSWITCH-Sofia-Profils, das gepatcht/neu gestartet wird. |
| `config_path` | — | Absoluter Pfad zur Sofia-Profil-XML auf dem UDM. Über die SSH-Discovery von `talkanchor setup` ermitteln lassen, da der Pfad firmwareabhängig und von Ubiquiti nicht dokumentiert ist. |
| `ext_sip_ip_param` / `ext_rtp_ip_param` | `ext-sip-ip` / `ext-rtp-ip` | Die XML-`<param name="...">`-Attribute, die auf die neue IP gepatcht werden. |
| `backup_dir_remote` | `/root/talkanchor-backups` | Remote-Verzeichnis, in das vor jedem Schreibzugriff Backups kopiert werden. |
| `health_check_timeout_seconds` | `30` | Wie lange `sofia status profile <profile> gateway` nach einer scharfen Änderung auf einen gesunden `REGED`-Status abgefragt wird, bevor aufgegeben und zurückgerollt wird. |
| `expected_registrations` | `[]` | Optionale Liste von Strings (z. B. Gateway-Namen), die alle `REGED` zeigen müssen, damit der Health-Check besteht. Wenn leer, prüft TalkAnchor nur, ob *irgendeine* Registrierung `REGED` ist. |

Vor der ersten SSH-Verbindung den Host-Key des UDM hinzufügen:

```sh
ssh-keyscan -H <host> >> ~/.ssh/known_hosts
```

## `notify`

| Schlüssel | Beschreibung |
|---|---|
| `channel` | Einer von `none`, `ntfy`, `webhook`, `email`. |
| `ntfy_topic_url` | z. B. `https://ntfy.sh/mein-privates-topic`. |
| `webhook_url` | Beliebiger Endpunkt, der einen JSON-POST von `{title, body, level}` akzeptiert — Home Assistant, ein Discord-kompatibles Relay, Slack Incoming Webhooks usw. |
| `email_to`, `email_smtp_host`, `email_smtp_port`, `email_smtp_user`, `email_smtp_password` | SMTP-Einstellungen für den E-Mail-Adapter. |

TalkAnchor benachrichtigt bei jedem Apply-, Health-Check- und
Rollback-Ergebnis — Erfolg, Fehler oder Zurückstellung — niemals stillschweigend.

## Beispiel `config.yaml`

```yaml
dry_run: true
poll_interval_seconds: 300
min_seconds_between_changes: 300
data_dir: ./data

cloudflare:
  api_token: "..."
  account_id: "..."
  tunnel_id: "..."

http_echo:
  url: https://api.ipify.org?format=json
  json_field: ip

unifi_talk:
  host: udm.internal.example
  ssh_port: 22
  ssh_user: root
  ssh_key_path: ~/.ssh/id_ed25519
  sofia_profile: external_talk
  config_path: /usr/local/freeswitch/conf/sofia.conf.d/external_talk.xml
  backup_dir_remote: /root/talkanchor-backups
  health_check_timeout_seconds: 30
  expected_registrations: []

notify:
  channel: ntfy
  ntfy_topic_url: https://ntfy.sh/mein-privates-topic

web_host: 0.0.0.0
web_port: 8420
```
