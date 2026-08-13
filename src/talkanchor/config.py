"""Central configuration model for TalkAnchor.

Loaded from (in order of precedence): environment variables > config.yaml >
defaults. Written by the setup wizard; never committed to the repo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

NotifyChannel = Literal["ntfy", "webhook", "email", "none"]


class CloudflareSourceConfig(BaseSettings):
    enabled: bool = Field(
        default=True,
        description="Use the Cloudflare Tunnel connector IP as a source at all. Some tunnels "
        "(e.g. shared with another service, or spanning a multi-WAN setup) can never report a "
        "single unambiguous IP; disable this to run on http_echo alone instead of permanently "
        "failing the Cloudflare check.",
    )
    api_token: SecretStr = Field(
        default=SecretStr(""), description="Cloudflare API token (Zone:Read / Tunnel:Read scope)"
    )
    account_id: str = ""
    tunnel_id: str = ""


class HttpEchoSourceConfig(BaseSettings):
    url: str = "https://api.ipify.org?format=json"
    json_field: str = "ip"


class UniFiTalkTargetConfig(BaseSettings):
    host: str = ""
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_key_path: str = "~/.ssh/id_ed25519"
    sofia_profile: str = "external_talk"
    config_path: str = ""
    ext_sip_ip_param: str = "ext-sip-ip"
    ext_rtp_ip_param: str = "ext-rtp-ip"
    backup_dir_remote: str = "/root/talkanchor-backups"
    health_check_timeout_seconds: int = 30
    expected_registrations: list[str] = Field(default_factory=list)


class NotifyConfig(BaseSettings):
    channel: NotifyChannel = "none"
    ntfy_topic_url: str = ""
    webhook_url: str = ""
    email_to: str = ""
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_smtp_user: str = ""
    email_smtp_password: SecretStr = SecretStr("")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TALKANCHOR_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    dry_run: bool = True
    poll_interval_seconds: int = 300
    min_seconds_between_changes: int = 300
    data_dir: str = "./data"

    cloudflare: CloudflareSourceConfig = Field(default_factory=CloudflareSourceConfig)
    http_echo: HttpEchoSourceConfig = Field(default_factory=HttpEchoSourceConfig)
    unifi_talk: UniFiTalkTargetConfig = Field(default_factory=UniFiTalkTargetConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)

    web_host: str = "0.0.0.0"  # noqa: S104 - dashboard is meant to be reachable on the LAN
    web_port: int = 8420

    @property
    def state_db_path(self) -> Path:
        return Path(self.data_dir) / "talkanchor.sqlite3"

    @property
    def local_backup_dir(self) -> Path:
        return Path(self.data_dir) / "backups"


def load_settings(config_path: str | Path = "config.yaml") -> Settings:
    """Load settings from a YAML file, then let environment variables override it."""
    path = Path(config_path)
    yaml_values: dict = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            yaml_values = yaml.safe_load(fh) or {}
    return Settings(**yaml_values)
