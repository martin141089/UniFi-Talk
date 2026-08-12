from __future__ import annotations

import stat

from talkanchor.config import load_settings
from talkanchor.wizard.writer import build_config_dict, write_config

SAMPLE_ANSWERS = {
    "dry_run": True,
    "poll_interval_seconds": 120,
    "min_seconds_between_changes": 300,
    "data_dir": "./data",
    "cloudflare_api_token": "secret-token",
    "cloudflare_account_id": "acc123",
    "cloudflare_tunnel_id": "tun456",
    "http_echo_url": "https://api.ipify.org?format=json",
    "http_echo_json_field": "ip",
    "unifi_host": "udm.local",
    "unifi_ssh_port": 22,
    "unifi_ssh_user": "root",
    "unifi_ssh_key_path": "~/.ssh/id_ed25519",
    "unifi_sofia_profile": "external_talk",
    "unifi_config_path": "/usr/local/freeswitch/conf/sofia.conf.d/external_talk.xml",
    "unifi_backup_dir_remote": "/root/talkanchor-backups",
    "unifi_health_check_timeout_seconds": 30,
    "notify_channel": "none",
}


def test_build_config_dict_roundtrips_through_settings(tmp_path):
    config_dict = build_config_dict(SAMPLE_ANSWERS)
    config_path = write_config(config_dict, tmp_path / "config.yaml")

    settings = load_settings(config_path)
    assert settings.cloudflare.account_id == "acc123"
    assert settings.cloudflare.api_token.get_secret_value() == "secret-token"
    assert settings.unifi_talk.host == "udm.local"
    assert settings.dry_run is True


def test_write_config_sets_restrictive_permissions(tmp_path):
    config_dict = build_config_dict(SAMPLE_ANSWERS)
    config_path = write_config(config_dict, tmp_path / "config.yaml")

    mode = stat.S_IMODE(config_path.stat().st_mode)
    assert mode == 0o600
