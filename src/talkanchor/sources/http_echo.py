"""Fallback IP source: a plain HTTP "what's my IP" echo service.

Used as the second, independent signal that must agree with the primary
Cloudflare source before TalkAnchor acts on an IP change (see
`core.reconciler`). The URL and the JSON field holding the IP are both
configurable so any echo service (ipify, icanhazip, a self-hosted one, ...)
can be used.
"""

from __future__ import annotations

import ipaddress

import httpx

from talkanchor.sources.base import IPSourceError


class HttpEchoSource:
    name = "http_echo"

    def __init__(
        self,
        url: str,
        *,
        json_field: str | None = "ip",
        timeout_seconds: float = 10.0,
    ) -> None:
        if not url:
            raise ValueError("HTTP echo source requires a url")
        self._url = url
        self._json_field = json_field
        self._timeout_seconds = timeout_seconds

    async def check(self) -> str:
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            try:
                response = await client.get(self._url)
            except httpx.HTTPError as exc:
                raise IPSourceError(f"HTTP echo request to {self._url} failed: {exc}") from exc

        if response.status_code != 200:
            raise IPSourceError(
                f"HTTP echo service returned HTTP {response.status_code}: {response.text[:300]}"
            )

        raw_ip = self._extract_ip(response)
        try:
            ipaddress.ip_address(raw_ip)
        except ValueError as exc:
            raise IPSourceError(f"HTTP echo service returned a non-IP value: {raw_ip!r}") from exc
        return raw_ip

    def _extract_ip(self, response: httpx.Response) -> str:
        if not self._json_field:
            return response.text.strip()
        try:
            data = response.json()
        except ValueError:
            return response.text.strip()
        value = data.get(self._json_field)
        if not value:
            raise IPSourceError(
                f"HTTP echo service JSON response had no {self._json_field!r} field: {data!r}"
            )
        return str(value).strip()
