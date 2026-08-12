"""Notification-adapter interface: pluggable "tell a human what happened".

TalkAnchor never fails silently — every apply/health-check/rollback outcome
is routed through a `Notifier`. `NullNotifier` is used when the user hasn't
configured a channel yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class NotificationLevel(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Notification:
    title: str
    body: str
    level: NotificationLevel = NotificationLevel.INFO


@runtime_checkable
class Notifier(Protocol):
    name: str

    async def send(self, notification: Notification) -> None: ...


class NullNotifier:
    name = "none"

    async def send(self, notification: Notification) -> None:
        return None
