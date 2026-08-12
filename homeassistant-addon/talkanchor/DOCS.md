# TalkAnchor Home Assistant Add-on

Thin wrapper around the standalone [TalkAnchor](https://github.com/martin141089/UniFi-Talk)
Docker image for users who already run Home Assistant on their network. It
translates this add-on's configuration UI into the same `config.yaml`
the CLI/Compose deployment uses, then runs the identical polling
loop + dashboard.

## Installation

1. Settings → Add-ons → Add-on Store → ⋮ → **Repositories** → add
   `https://github.com/martin141089/UniFi-Talk`.
2. Find **TalkAnchor** in the store and install it.
3. Fill in the configuration (see below), start the add-on, and open it
   via the sidebar (ingress) or `http://<ha-host>:8420`.

## Configuration

| Option | Description |
|---|---|
| `dry_run` | Keep `true` until you've reviewed a few cycles in the log. |
| `poll_interval_seconds` / `min_seconds_between_changes` | Same as the standalone config — see [CONFIGURATION.md](../../CONFIGURATION.md). |
| `cloudflare_api_token` / `cloudflare_account_id` / `cloudflare_tunnel_id` | Cloudflare Tunnel connector IP source. Token scope: Account → Cloudflare Tunnel → Read. |
| `http_echo_url` | Fallback IP source. |
| `unifi_host` / `unifi_ssh_port` / `unifi_ssh_user` | UDM SSH connection details. |
| `unifi_ssh_private_key` | Paste the **private** key contents directly (multi-line). Key-only auth — there is no password option. |
| `unifi_ssh_known_hosts_entry` | The UDM's SSH host key line, e.g. the output of `ssh-keyscan -H <host>` run from your own machine. Required — unknown host keys are rejected, not trusted on first use. |
| `unifi_sofia_profile` / `unifi_config_path` | Sofia profile name and the path to its XML on the UDM. Since the add-on can't run the interactive wizard's SSH discovery, find the path once via `talkanchor setup` on a workstation, or SSH in manually and run `find / -iname "sofia*.xml"`. |
| `unifi_backup_dir_remote` | Remote backup directory on the UDM. |
| `notify_channel` / `notify_ntfy_topic_url` / `notify_webhook_url` | Optional notifications. For Home Assistant automations, point `notify_webhook_url` at a `webhook` trigger and react to it from HA itself. |

State, history, and local backup copies persist under `/data`, which the
Supervisor keeps across add-on restarts and updates.

## Disclaimer

⚠️ Not an official Ubiquiti product — see the main
[SECURITY.md](../../SECURITY.md) disclaimer. Start with `dry_run: true`.
