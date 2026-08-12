"""SMTP email notifier."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from talkanchor.notify.base import Notification


class EmailNotifier:
    name = "email"

    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        to_address: str,
        from_address: str | None = None,
    ) -> None:
        if not smtp_host or not to_address:
            raise ValueError("email notifier requires smtp_host and to_address")
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._to_address = to_address
        self._from_address = from_address or smtp_user or to_address

    async def send(self, notification: Notification) -> None:
        await asyncio.to_thread(self._send_sync, notification)

    def _send_sync(self, notification: Notification) -> None:
        message = EmailMessage()
        message["Subject"] = f"[TalkAnchor] {notification.title}"
        message["From"] = self._from_address
        message["To"] = self._to_address
        message.set_content(notification.body)

        with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if self._smtp_user:
                smtp.login(self._smtp_user, self._smtp_password)
            smtp.send_message(message)
