# Configuration Reference

TalkAnchor reads settings from `config.yaml`, then lets environment
variables override any value in it (see `.env.example`). The easiest way to
generate a first `config.yaml` is `talkanchor setup` (see the
[README quickstart](README.md#quickstart)) — this document is the reference
for every field once you want to tune something by hand.

Environment variables use the prefix `TALKANCHOR_` and a double underscore
(`__`) for nested fields, e.g. `TALKANCHOR_CLOUDFLARE__API_TOKEN`.

## Top-level

| Key | Env var | Default | Description |
|---|---|---|---|
| `dry_run` | `TALKANCHOR_DRY_RUN` | `true` | When true, TalkAnchor computes and logs what it *would* do but never opens an SSH connection or writes anything. Keep this on until you've reviewed a few cycles. |
| `poll_interval_seconds` | `TALKANCHOR_POLL_INTERVAL_SECONDS` | `300` | How often the scheduler checks the IP sources. |
| `min_seconds_between_changes` | `TALKANCHOR_MIN_SECONDS_BETWEEN_CHANGES` | `300` | Minimum time between two live changes (rate limit / anti-flapping). A change detected sooner is deferred and retried next cycle, not dropped. |
| `data_dir` | `TALKANCHOR_DATA_DIR` | `./data` | Local directory for the SQLite state DB, local backup copies, and the log file. |
| `web_host` / `web_port` | `TALKANCHOR_WEB_HOST` / `TALKANCHOR_WEB_PORT` | `0.0.0.0` / `8420` | Dashboard bind address/port. Not meant to be exposed to the internet — put it behind your own VPN/reverse proxy if you need remote access. |

## `cloudflare` — primary IP source

| Key | Description |
|---|---|
| `api_token` | Cloudflare API token. Minimal scope: **Account → Cloudflare Tunnel → Read**. |
| `account_id` | Your Cloudflare account ID. |
| `tunnel_id` | The ID of the tunnel whose connector IP you want to track. |

TalkAnchor calls `GET /accounts/{account_id}/cfd_tunnel/{tunnel_id}/connections`
and reads each active connector's `origin_ip`. If connectors disagree
(can happen mid-failover), TalkAnchor refuses to act that cycle rather than
guess.

## `http_echo` — fallback IP source

| Key | Default | Description |
|---|---|---|
| `url` | `https://api.ipify.org?format=json` | Any "what's my IP" HTTP endpoint. |
| `json_field` | `ip` | JSON field holding the IP. Leave empty to treat the whole response body as plain text. |

Both sources must agree on the current IP before TalkAnchor acts — this is
the plausibility check that guards against a single source glitching.

## `unifi_talk` — SSH target

| Key | Default | Description |
|---|---|---|
| `host` | — | UDM hostname or IP. |
| `ssh_port` | `22` | |
| `ssh_user` | `root` | |
| `ssh_key_path` | `~/.ssh/id_ed25519` | Private key path. **Key auth only — there is no password field.** |
| `sofia_profile` | `external_talk` | The FreeSWITCH Sofia profile name to patch/restart. |
| `config_path` | — | Absolute path to the Sofia profile XML on the UDM. Use `talkanchor setup`'s SSH discovery to find it, since the path is firmware-dependent and undocumented by Ubiquiti. |
| `ext_sip_ip_param` / `ext_rtp_ip_param` | `ext-sip-ip` / `ext-rtp-ip` | The XML `<param name="...">` attributes patched to the new IP. |
| `backup_dir_remote` | `/root/talkanchor-backups` | Remote directory backups are copied into before every write. |
| `health_check_timeout_seconds` | `30` | How long to poll `sofia status profile <profile> reg` for a healthy `REGED` state after a live change before giving up and rolling back. |
| `expected_registrations` | `[]` | Optional list of strings (e.g. gateway names) that must all show `REGED` for the health check to pass. If empty, TalkAnchor just checks that *some* registration is `REGED`. |

Before the first SSH connection, add the UDM's host key:

```sh
ssh-keyscan -H <host> >> ~/.ssh/known_hosts
```

## `notify`

| Key | Description |
|---|---|
| `channel` | One of `none`, `ntfy`, `webhook`, `email`. |
| `ntfy_topic_url` | e.g. `https://ntfy.sh/my-private-topic`. |
| `webhook_url` | Any endpoint accepting a JSON POST of `{title, body, level}` — Home Assistant, a Discord-compatible relay, Slack Incoming Webhooks, etc. |
| `email_to`, `email_smtp_host`, `email_smtp_port`, `email_smtp_user`, `email_smtp_password` | SMTP settings for the email adapter. |

TalkAnchor notifies on every apply, health-check, and rollback outcome —
success, failure, or deferred — never silently.

## Example `config.yaml`

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
  ntfy_topic_url: https://ntfy.sh/my-private-topic

web_host: 0.0.0.0
web_port: 8420
```
