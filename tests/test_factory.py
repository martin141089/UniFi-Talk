from __future__ import annotations

from pydantic import SecretStr

from talkanchor.config import Settings
from talkanchor.core.factory import build_sources
from talkanchor.sources.cloudflare import CloudflareTunnelSource
from talkanchor.sources.http_echo import HttpEchoSource


def _settings_with_cloudflare_creds(*, enabled: bool) -> Settings:
    settings = Settings()
    settings.cloudflare.enabled = enabled
    settings.cloudflare.api_token = SecretStr("tok")
    settings.cloudflare.account_id = "acc"
    settings.cloudflare.tunnel_id = "tun"
    return settings


def test_build_sources_includes_cloudflare_when_enabled_and_configured():
    sources = build_sources(_settings_with_cloudflare_creds(enabled=True))
    assert any(isinstance(s, CloudflareTunnelSource) for s in sources)
    assert any(isinstance(s, HttpEchoSource) for s in sources)


def test_build_sources_skips_cloudflare_when_disabled_even_with_full_creds():
    # Some tunnels (e.g. shared with another service, or spanning a
    # multi-WAN setup) can never report a single unambiguous IP; the
    # enabled flag lets a user opt out without having to clear the
    # otherwise-valid credentials.
    sources = build_sources(_settings_with_cloudflare_creds(enabled=False))
    assert not any(isinstance(s, CloudflareTunnelSource) for s in sources)
    assert any(isinstance(s, HttpEchoSource) for s in sources)


def test_build_sources_skips_cloudflare_when_credentials_incomplete():
    settings = Settings()  # default: enabled=True but no credentials
    sources = build_sources(settings)
    assert not any(isinstance(s, CloudflareTunnelSource) for s in sources)
    assert any(isinstance(s, HttpEchoSource) for s in sources)
