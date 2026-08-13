#!/usr/bin/env python3
"""Home Assistant add-on entrypoint.

Reads the supervisor-provided /data/options.json (populated from this
add-on's config.yaml `options`/`schema`), writes an equivalent TalkAnchor
config.yaml, provisions the SSH key/known_hosts if provided, and then
execs the same `talkanchor run` entrypoint the standalone Docker image
uses. State/backups live under /data, which the supervisor persists across
restarts and add-on updates — unlike the rest of the container filesystem.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

OPTIONS_PATH = Path("/data/options.json")
CONFIG_PATH = Path("/app/config.yaml")
DATA_DIR = Path("/data")


def main() -> None:
    options = json.loads(OPTIONS_PATH.read_text()) if OPTIONS_PATH.exists() else {}

    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    ssh_key_path = ssh_dir / "id_ed25519"
    private_key = options.get("unifi_ssh_private_key", "").strip()
    if private_key:
        ssh_key_path.write_text(private_key + "\n")
        ssh_key_path.chmod(0o600)

    known_hosts_entry = options.get("unifi_ssh_known_hosts_entry", "").strip()
    if known_hosts_entry:
        (ssh_dir / "known_hosts").write_text(known_hosts_entry + "\n")

    config = {
        "dry_run": options.get("dry_run", True),
        "poll_interval_seconds": options.get("poll_interval_seconds", 300),
        "min_seconds_between_changes": options.get("min_seconds_between_changes", 300),
        "data_dir": str(DATA_DIR),
        "cloudflare": {
            "enabled": options.get("cloudflare_enabled", True),
            "api_token": options.get("cloudflare_api_token", ""),
            "account_id": options.get("cloudflare_account_id", ""),
            "tunnel_id": options.get("cloudflare_tunnel_id", ""),
        },
        "http_echo": {
            "url": options.get("http_echo_url", "https://api.ipify.org?format=json"),
            "json_field": "ip",
        },
        "unifi_talk": {
            "host": options.get("unifi_host", ""),
            "ssh_port": options.get("unifi_ssh_port", 22),
            "ssh_user": options.get("unifi_ssh_user", "root"),
            "ssh_key_path": str(ssh_key_path),
            "sofia_profile": options.get("unifi_sofia_profile", "external_talk"),
            "config_path": options.get("unifi_config_path", ""),
            "backup_dir_remote": options.get("unifi_backup_dir_remote", "/root/talkanchor-backups"),
            "health_check_timeout_seconds": options.get("health_check_timeout_seconds", 30),
        },
        "notify": {
            "channel": options.get("notify_channel", "none"),
            "ntfy_topic_url": options.get("notify_ntfy_topic_url", ""),
            "webhook_url": options.get("notify_webhook_url", ""),
        },
        "web_host": "0.0.0.0",
        "web_port": 8420,
    }

    CONFIG_PATH.write_text(yaml.safe_dump(config, sort_keys=False))
    CONFIG_PATH.chmod(0o600)

    os.execvp("talkanchor", ["talkanchor", "run", "--config", str(CONFIG_PATH)])  # noqa: S606


if __name__ == "__main__":
    main()
