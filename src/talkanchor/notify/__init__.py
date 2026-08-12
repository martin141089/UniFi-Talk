from talkanchor.config import NotifyConfig
from talkanchor.notify.base import Notification, NotificationLevel, Notifier, NullNotifier
from talkanchor.notify.email import EmailNotifier
from talkanchor.notify.ntfy import NtfyNotifier
from talkanchor.notify.webhook import WebhookNotifier

__all__ = [
    "Notification",
    "NotificationLevel",
    "Notifier",
    "NullNotifier",
    "NtfyNotifier",
    "WebhookNotifier",
    "EmailNotifier",
    "build_notifier",
]


def build_notifier(config: NotifyConfig) -> Notifier:
    """Factory: turn NotifyConfig.channel into a concrete Notifier instance."""
    if config.channel == "ntfy":
        return NtfyNotifier(config.ntfy_topic_url)
    if config.channel == "webhook":
        return WebhookNotifier(config.webhook_url)
    if config.channel == "email":
        return EmailNotifier(
            smtp_host=config.email_smtp_host,
            smtp_port=config.email_smtp_port,
            smtp_user=config.email_smtp_user,
            smtp_password=config.email_smtp_password.get_secret_value(),
            to_address=config.email_to,
        )
    return NullNotifier()
