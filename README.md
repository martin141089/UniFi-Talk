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

**TalkAnchor** keeps a self-hosted [UniFi Talk](https://ui.com/talk) install
anchored to your current dynamic public IP. It watches your Cloudflare
Tunnel connector's IP, cross-checks it against a fallback source, and — only
when both agree something actually changed — safely patches the FreeSWITCH
Sofia SIP profile over SSH, backs up first, restarts the profile, and
verifies the trunk re-registers before calling it done.

## Why TalkAnchor?

UniFi Talk registers with your SIP trunk (Telekom, etc.) using an external
IP baked into its Sofia profile config (`ext-sip-ip` / `ext-rtp-ip`,
`auto-nat: false`). On connections with a **dynamic public IP**, that value
goes stale the moment your provider rotates it (forced disconnect, DHCP
lease renewal, ...) — audio breaks, calls drop, registration fails. The
UniFi Talk UI has no toggle for this; the value is managed internally by the
app and gets reset on every app update.

There's no first-party fix, and only scattered manual community
workarounds that get wiped out on the next update. TalkAnchor is a small,
self-hosted service that closes that gap — and re-corrects automatically
the next cycle even after an app update resets things, which is the actual
point, not just a limitation to work around.

## Screenshot

![TalkAnchor dashboard](docs/screenshots/dashboard.png)

**[Live demo →](https://martin141089.github.io/UniFi-Talk/)** (static,
fake data — no backend, deployed from `web-demo/`; requires GitHub Pages to
be enabled once under *Settings → Pages → Source: GitHub Actions*).

## Features

- **Dual-source IP detection** — Cloudflare Tunnel connector IP as the
  primary source, a configurable HTTP echo service as a fallback; both must
  agree before anything happens.
- **Dry-run by default** — review exactly what TalkAnchor *would* do before
  it ever opens an SSH connection.
- **Backup before every write**, locally and on the UDM, with a documented
  manual restore path (see [SECURITY.md](SECURITY.md)).
- **Health-checked changes** — polls `sofia status` after a live change and
  automatically rolls back (with a clear notification either way) if
  registration doesn't come back healthy.
- **Rate-limited** — a flapping IP signal gets logged and deferred, not
  acted on repeatedly.
- **Pluggable notifications** — ntfy, generic webhook (Home Assistant,
  Discord relay, Slack), or email.
- **Guided setup wizard** — interactive CLI that walks through Cloudflare,
  SSH, and notification setup, with SSH-based discovery of the (otherwise
  undocumented) Sofia config path.
- **Local dashboard** — current IP, change history, live log, health
  status, manual check/rollback buttons.
- **Plugin architecture** — UniFi Talk is the reference target adapter, not
  the only one; see [CONTRIBUTING.md](CONTRIBUTING.md) to add another SIP
  system or IP source.

## Quickstart

```sh
git clone https://github.com/martin141089/UniFi-Talk.git talkanchor
cd talkanchor
cp .env.example .env   # fill in Cloudflare + UniFi SSH details, or run the wizard instead
docker compose -f docker/docker-compose.yml up -d
```

Or run the interactive setup wizard first (recommended — it can discover
the Sofia config path for you over SSH):

```sh
uv venv .venv && uv pip install -e . --python .venv/bin/python
.venv/bin/talkanchor setup
```

The wizard always writes `dry_run: true` first, offers to run a test cycle
immediately, and only flips to a live run after a second, explicit
confirmation. See [CONFIGURATION.md](CONFIGURATION.md) for every setting
and [docs/architecture.md](docs/architecture.md) for how the reconcile loop
and plugin adapters fit together.

Once running, the dashboard is at `http://<host>:8420`.

## Disclaimer

> ⚠️ **Kein offizielles Ubiquiti-Produkt.** TalkAnchor verändert eine von
> der UniFi-Talk-Anwendung verwaltete, nicht offiziell dokumentierte
> Konfigurationsdatei über SSH. Nutzung erfolgt auf eigene Verantwortung.
> Vor dem ersten produktiven Einsatz unbedingt den Dry-Run-Modus nutzen und
> ein aktuelles Backup deines UniFi-Systems vorhalten.

See [SECURITY.md](SECURITY.md) for the full safety model (key-only SSH,
host-key verification, backups, health checks, rate limiting).

## Documentation

- [CONFIGURATION.md](CONFIGURATION.md) — every config field, env var, and a full example
- [docs/architecture.md](docs/architecture.md) — reconcile loop, plugin protocols, deployment
- [SECURITY.md](SECURITY.md) — safety model, disclaimer, manual restore
- [CONTRIBUTING.md](CONTRIBUTING.md) — adding new source/target/notify adapters
- [homeassistant-addon/](homeassistant-addon/) — Home Assistant add-on wrapper

## License

[MIT](LICENSE)
