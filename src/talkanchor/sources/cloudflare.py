"""IP source backed by the Cloudflare Tunnel connections API.

Verified against the official Cloudflare API docs (August 2026):
GET https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/connections

The response's `result` is a list of connector objects, each carrying a
`conns` list of active connections. Each connection has an `origin_ip` field:
the public IP address of the host running `cloudflared` — i.e. the current
WAN IP of the network TalkAnchor is trying to keep UniFi Talk anchored to.
"""

from __future__ import annotations

import httpx

from talkanchor.sources.base import IPSourceError

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareTunnelSource:
    name = "cloudflare_tunnel"

    def __init__(
        self,
        api_token: str,
        account_id: str,
        tunnel_id: str,
        *,
        base_url: str = CLOUDFLARE_API_BASE,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not api_token or not account_id or not tunnel_id:
            raise ValueError("Cloudflare source requires api_token, account_id and tunnel_id")
        self._api_token = api_token
        self._account_id = account_id
        self._tunnel_id = tunnel_id
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def check(self) -> str:
        url = f"{self._base_url}/accounts/{self._account_id}/cfd_tunnel/{self._tunnel_id}/connections"
        headers = {"Authorization": f"Bearer {self._api_token}"}
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.HTTPError as exc:
                raise IPSourceError(f"Cloudflare API request failed: {exc}") from exc

        if response.status_code != 200:
            raise IPSourceError(
                f"Cloudflare API returned HTTP {response.status_code}: {response.text[:300]}"
            )

        payload = response.json()
        if not payload.get("success", False):
            raise IPSourceError(f"Cloudflare API reported failure: {payload.get('errors')}")

        origin_ips: list[str] = []
        for connector in payload.get("result", []) or []:
            for conn in connector.get("conns", []) or []:
                origin_ip = conn.get("origin_ip")
                if origin_ip:
                    origin_ips.append(origin_ip)

        if not origin_ips:
            raise IPSourceError(
                "Cloudflare API returned no active tunnel connections with an origin_ip. "
                "Is the tunnel up?"
            )

        unique_ips = set(origin_ips)
        if len(unique_ips) > 1:
            raise IPSourceError(
                f"Cloudflare tunnel connectors disagree on origin IP: {sorted(unique_ips)}. "
                "This can happen mid-failover; refusing to pick one automatically."
            )

        return unique_ips.pop()
