"""Serializes the wizard's collected answers into config.yaml.

Deliberately writes YAML (not .env) so nested sections stay readable; the
`Settings` loader in `talkanchor.config` accepts either, and env vars always
override the file at runtime (see .env.example) for Docker deployments that
prefer that route instead of running the wizard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def build_config_dict(answers: dict[str, Any]) -> dict[str, Any]:
    return {
        "dry_run": answers["dry_run"],
        "poll_interval_seconds": answers["poll_interval_seconds"],
        "min_seconds_between_changes": answers["min_seconds_between_changes"],
        "data_dir": answers.get("data_dir", "./data"),
        "cloudflare": {
            "api_token": answers["cloudflare_api_token"],
            "account_id": answers["cloudflare_account_id"],
            "tunnel_id": answers["cloudflare_tunnel_id"],
        },
        "http_echo": {
            "url": answers["http_echo_url"],
            "json_field": answers["http_echo_json_field"],
        },
        "unifi_talk": {
            "host": answers["unifi_host"],
            "ssh_port": answers["unifi_ssh_port"],
            "ssh_user": answers["unifi_ssh_user"],
            "ssh_key_path": answers["unifi_ssh_key_path"],
            "sofia_profile": answers["unifi_sofia_profile"],
            "config_path": answers["unifi_config_path"],
            "backup_dir_remote": answers["unifi_backup_dir_remote"],
            "health_check_timeout_seconds": answers["unifi_health_check_timeout_seconds"],
            "expected_registrations": answers.get("unifi_expected_registrations", []),
        },
        "notify": {
            "channel": answers["notify_channel"],
            "ntfy_topic_url": answers.get("notify_ntfy_topic_url", ""),
            "webhook_url": answers.get("notify_webhook_url", ""),
            "email_to": answers.get("notify_email_to", ""),
            "email_smtp_host": answers.get("notify_email_smtp_host", ""),
            "email_smtp_port": answers.get("notify_email_smtp_port", 587),
            "email_smtp_user": answers.get("notify_email_smtp_user", ""),
            "email_smtp_password": answers.get("notify_email_smtp_password", ""),
        },
        "web_host": answers.get("web_host", "0.0.0.0"),
        "web_port": answers.get("web_port", 8420),
    }


def write_config(config_dict: dict[str, Any], path: str | Path = "config.yaml") -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(config_dict, fh, sort_keys=False)
    target.chmod(0o600)  # contains secrets: owner read/write only
    return target
