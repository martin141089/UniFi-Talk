<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo/wordmark-dark.svg">
    <img src="assets/logo/wordmark.svg" alt="TalkAnchor" width="360">
  </picture>
</p>

<p align="center"><em>Deine dynamische IP im Griff. Stay registered. Stay reachable.</em></p>

<p align="center">
  <a href="https://github.com/martin141089/UniFi-Talk/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/martin141089/UniFi-Talk/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-00D9A3.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-0F2A3F.svg">
  <a href="https://github.com/martin141089/UniFi-Talk/pkgs/container/unifi-talk"><img alt="Docker" src="https://img.shields.io/badge/docker-GHCR-00D9A3.svg"></a>
</p>

---

**TalkAnchor** hält eine selbst gehostete [UniFi Talk](https://ui.com/talk)-
Installation verankert an deiner aktuellen dynamischen öffentlichen IP. Es
beobachtet die IP deines Cloudflare-Tunnel-Connectors, gleicht sie
gegen eine Fallback-Quelle ab und patcht — nur wenn beide übereinstimmen und
sich tatsächlich etwas geändert hat — sicher das FreeSWITCH-Sofia-SIP-Profil
per SSH, erstellt vorher ein Backup, startet das Profil neu und prüft, ob
sich der Trunk erfolgreich neu registriert, bevor der Vorgang als
abgeschlossen gilt.

## Warum TalkAnchor?

UniFi Talk registriert sich bei deinem SIP-Trunk (Telekom o. Ä.) mit einer
externen IP, die fest in der Sofia-Profil-Konfiguration hinterlegt ist
(`ext-sip-ip` / `ext-rtp-ip`, `auto-nat: false`). Bei Anschlüssen mit
**dynamischer öffentlicher IP** wird dieser Wert veraltet, sobald der
Provider die IP wechselt (Zwangstrennung, DHCP-Lease-Erneuerung, ...) —
Audio bricht ab, Anrufe werden getrennt, die Registrierung schlägt fehl.
Die UniFi-Talk-UI bietet dafür keinen Schalter; der Wert wird intern von
der App verwaltet und bei jedem App-Update zurückgesetzt.

Es gibt dafür keine offizielle Lösung, nur vereinzelte manuelle
Community-Workarounds, die beim nächsten Update wieder verloren gehen.
TalkAnchor ist ein schlanker, selbst gehosteter Dienst, der genau diese
Lücke schließt — und im nächsten Zyklus automatisch nachkorrigiert, selbst
wenn ein App-Update die Einstellung zurückgesetzt hat. Das ist der
eigentliche Clou, nicht nur eine Einschränkung, mit der man leben muss.

## Screenshot

![TalkAnchor Dashboard](docs/screenshots/dashboard.png)

**[Live-Demo →](https://martin141089.github.io/UniFi-Talk/)** (statisch,
Beispieldaten — kein Backend, wird aus `web-demo/` deployed; setzt voraus,
dass GitHub Pages einmalig unter *Settings → Pages → Source: GitHub
Actions* aktiviert wurde).

## Funktionen

- **IP-Erkennung aus zwei Quellen** — Cloudflare-Tunnel-Connector-IP als
  primäre Quelle, ein konfigurierbarer HTTP-Echo-Dienst als Fallback; beide
  müssen übereinstimmen, bevor irgendetwas passiert.
- **Dry-Run als Standard** — genau nachvollziehen, was TalkAnchor tun
  *würde*, bevor überhaupt eine SSH-Verbindung aufgebaut wird.
- **Backup vor jedem Schreibzugriff**, lokal und auf dem UDM, mit
  dokumentiertem manuellem Wiederherstellungsweg (siehe
  [SECURITY.md](SECURITY.md)).
- **Health-Check nach jeder Änderung** — fragt `sofia status` nach einer
  scharfen Änderung ab und rollt automatisch zurück (mit klarer
  Benachrichtigung in beiden Fällen), falls die Registrierung nicht wieder
  gesund wird.
- **Rate-Limiting** — ein flatterndes IP-Signal wird protokolliert und
  zurückgestellt, nicht wiederholt scharf ausgeführt.
- **Austauschbare Benachrichtigungen** — ntfy, generischer Webhook (Home
  Assistant, Discord-Relay, Slack) oder E-Mail.
- **Geführter Setup-Wizard** — interaktive CLI, die durch Cloudflare-,
  SSH- und Benachrichtigungs-Einrichtung führt, inklusive SSH-basierter
  Erkennung des (sonst undokumentierten) Sofia-Config-Pfads.
- **Lokales Dashboard** — aktuelle IP, Änderungshistorie, Live-Log,
  Health-Status, manuelle Prüfen-/Rollback-Buttons.
- **Plugin-Architektur** — UniFi Talk ist der Referenz-Zieladapter, nicht
  der einzig mögliche; siehe [CONTRIBUTING.md](CONTRIBUTING.md), um ein
  weiteres SIP-System oder eine weitere IP-Quelle zu ergänzen.

## Schnellstart

```sh
git clone https://github.com/martin141089/UniFi-Talk.git talkanchor
cd talkanchor
cp .env.example .env   # Cloudflare- + UniFi-SSH-Details eintragen, oder stattdessen den Wizard nutzen
docker compose -f docker/docker-compose.yml up -d
```

Oder zuerst den interaktiven Setup-Wizard ausführen (empfohlen — er kann
den Sofia-Config-Pfad selbstständig per SSH ermitteln):

```sh
uv venv .venv && uv pip install -e . --python .venv/bin/python
.venv/bin/talkanchor setup
```

Der Wizard schreibt zuerst immer `dry_run: true`, bietet an, sofort einen
Testlauf auszuführen, und schaltet erst nach einer zweiten, expliziten
Bestätigung scharf. Siehe [CONFIGURATION.md](CONFIGURATION.md) für jede
Einstellung und [docs/architecture.md](docs/architecture.md) dafür, wie
Reconcile-Loop und Plugin-Adapter zusammenspielen.

Sobald der Dienst läuft, ist das Dashboard unter `http://<host>:8420`
erreichbar.

## Haftungsausschluss

> ⚠️ **Kein offizielles Ubiquiti-Produkt.** TalkAnchor verändert eine von
> der UniFi-Talk-Anwendung verwaltete, nicht offiziell dokumentierte
> Konfigurationsdatei über SSH. Nutzung erfolgt auf eigene Verantwortung.
> Vor dem ersten produktiven Einsatz unbedingt den Dry-Run-Modus nutzen und
> ein aktuelles Backup deines UniFi-Systems vorhalten.

Das vollständige Sicherheitskonzept (SSH nur per Key, Host-Key-Prüfung,
Backups, Health-Checks, Rate-Limiting) steht in [SECURITY.md](SECURITY.md).

## Dokumentation

- [CONFIGURATION.md](CONFIGURATION.md) — jedes Config-Feld, jede Umgebungsvariable, ein vollständiges Beispiel
- [docs/architecture.md](docs/architecture.md) — Reconcile-Loop, Plugin-Protokolle, Deployment
- [SECURITY.md](SECURITY.md) — Sicherheitskonzept, Haftungsausschluss, manuelle Wiederherstellung
- [CONTRIBUTING.md](CONTRIBUTING.md) — neue Source-/Target-/Notify-Adapter beisteuern
- [homeassistant-addon/](homeassistant-addon/) — Home-Assistant-Add-on-Wrapper

## Lizenz

[MIT](LICENSE)
