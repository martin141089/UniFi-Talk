"""Generic JSON webhook notifier (Home Assistant, Discord-compatible via a
relay, Slack Incoming Webhooks, or any custom endpoint expecting JSON)."""

from __future__ import annotations

import httpx

from talkanchor.notify.base import Notification


class WebhookNotifier:
    name = "webhook"

    def __init__(self, url: str, *, timeout_seconds: float = 10.0) -> None:
        if not url:
            raise ValueError("webhook notifier requires a url")
        self._url = url
        self._timeout_seconds = timeout_seconds

    async def send(self, notification: Notification) -> None:
        payload = {
            "title": notification.title,
            "body": notification.body,
            "level": notification.level.value,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            await client.post(self._url, json=payload)
