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
                raise IPSourceError(f"Cloudflare-API-Anfrage fehlgeschlagen: {exc}") from exc

        if response.status_code != 200:
            raise IPSourceError(
                f"Cloudflare-API antwortete mit HTTP {response.status_code}: {response.text[:300]}"
            )

        payload = response.json()
        if not payload.get("success", False):
            raise IPSourceError(f"Cloudflare-API meldet einen Fehler: {payload.get('errors')}")

        origin_ips: list[str] = []
        for connector in payload.get("result", []) or []:
            for conn in connector.get("conns", []) or []:
                origin_ip = conn.get("origin_ip")
                if origin_ip:
                    origin_ips.append(origin_ip)

        if not origin_ips:
            raise IPSourceError(
                "Cloudflare-API meldet keine aktiven Tunnel-Verbindungen mit origin_ip. "
                "Läuft der Tunnel?"
            )

        unique_ips = set(origin_ips)
        if len(unique_ips) > 1:
            raise IPSourceError(
                f"Cloudflare-Tunnel-Connectoren melden unterschiedliche Ursprungs-IPs: "
                f"{sorted(unique_ips)}. Das kann während eines Failovers vorkommen; "
                "TalkAnchor wählt in diesem Fall bewusst keine automatisch aus."
            )

        return unique_ips.pop()


async def verify_token(
    api_token: str,
    *,
    base_url: str = CLOUDFLARE_API_BASE,
    timeout_seconds: float = 10.0,
) -> str | None:
    """Check the token itself via Cloudflare's `/user/tokens/verify` endpoint.

    This needs no account/tunnel ID, so it isolates "the token is bad" from
    "the token is fine but lacks access to this account/tunnel" when the
    connections check above fails with an authentication error.

    Returns None if the token verifies as active, otherwise a short reason.
    """
    url = f"{base_url.rstrip('/')}/user/tokens/verify"
    headers = {"Authorization": f"Bearer {api_token}"}
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        try:
            response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            return f"Verify-Anfrage an Cloudflare fehlgeschlagen: {exc}"

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if response.status_code == 200 and isinstance(payload, dict) and payload.get("success"):
        return None

    errors = payload.get("errors") if isinstance(payload, dict) else response.text[:200]
    return f"Cloudflare lehnt den Token selbst ab (HTTP {response.status_code}): {errors}"
