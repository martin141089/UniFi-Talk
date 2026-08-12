from __future__ import annotations

import httpx
import pytest

from talkanchor.sources.base import IPSourceError
from talkanchor.sources.cloudflare import CloudflareTunnelSource
from talkanchor.sources.http_echo import HttpEchoSource


@pytest.mark.asyncio
async def test_http_echo_json_field(monkeypatch):
    source = HttpEchoSource("https://example.invalid/ip", json_field="ip")

    async def fake_get(self, url, **kwargs):
        return httpx.Response(200, json={"ip": "203.0.113.5"}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    assert await source.check() == "203.0.113.5"


@pytest.mark.asyncio
async def test_http_echo_plaintext(monkeypatch):
    source = HttpEchoSource("https://example.invalid/ip", json_field=None)

    async def fake_get(self, url, **kwargs):
        return httpx.Response(200, text="203.0.113.9\n", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    assert await source.check() == "203.0.113.9"


@pytest.mark.asyncio
async def test_http_echo_rejects_non_ip(monkeypatch):
    source = HttpEchoSource("https://example.invalid/ip", json_field=None)

    async def fake_get(self, url, **kwargs):
        return httpx.Response(200, text="not-an-ip", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    with pytest.raises(IPSourceError):
        await source.check()


@pytest.mark.asyncio
async def test_cloudflare_source_parses_origin_ip(monkeypatch):
    source = CloudflareTunnelSource(api_token="tok", account_id="acc", tunnel_id="tun")

    payload = {
        "success": True,
        "result": [
            {"conns": [{"origin_ip": "198.51.100.1", "colo_name": "fra"}]},
        ],
    }

    async def fake_get(self, url, **kwargs):
        assert "acc" in url and "tun" in url
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    assert await source.check() == "198.51.100.1"


@pytest.mark.asyncio
async def test_cloudflare_source_disagreeing_connectors_raises(monkeypatch):
    source = CloudflareTunnelSource(api_token="tok", account_id="acc", tunnel_id="tun")

    payload = {
        "success": True,
        "result": [
            {"conns": [{"origin_ip": "198.51.100.1"}]},
            {"conns": [{"origin_ip": "198.51.100.2"}]},
        ],
    }

    async def fake_get(self, url, **kwargs):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    with pytest.raises(IPSourceError):
        await source.check()


def test_cloudflare_source_requires_credentials():
    with pytest.raises(ValueError):
        CloudflareTunnelSource(api_token="", account_id="acc", tunnel_id="tun")
