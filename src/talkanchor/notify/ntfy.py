"""Notifier backed by ntfy.sh (or a self-hosted ntfy instance)."""

from __future__ import annotations

import httpx

from talkanchor.notify.base import Notification, NotificationLevel

_PRIORITY_BY_LEVEL = {
    NotificationLevel.INFO: "default",
    NotificationLevel.SUCCESS: "default",
    NotificationLevel.WARNING: "high",
    NotificationLevel.ERROR: "urgent",
}

_TAG_BY_LEVEL = {
    NotificationLevel.INFO: "information_source",
    NotificationLevel.SUCCESS: "white_check_mark",
    NotificationLevel.WARNING: "warning",
    NotificationLevel.ERROR: "rotating_light",
}


class NtfyNotifier:
    name = "ntfy"

    def __init__(self, topic_url: str, *, timeout_seconds: float = 10.0) -> None:
        if not topic_url:
            raise ValueError("ntfy notifier requires a topic_url, e.g. https://ntfy.sh/my-topic")
        self._topic_url = topic_url
        self._timeout_seconds = timeout_seconds

    async def send(self, notification: Notification) -> None:
        headers = {
            "Title": notification.title,
            "Priority": _PRIORITY_BY_LEVEL[notification.level],
            "Tags": _TAG_BY_LEVEL[notification.level],
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            await client.post(
                self._topic_url,
                content=notification.body.encode("utf-8"),
                headers=headers,
            )
