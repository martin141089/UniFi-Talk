"""Wires up sources/target/notifier/state from a Settings object.

This is the one place that knows how to turn config into concrete adapter
instances, so the CLI, scheduler, and dashboard don't duplicate it.
"""

from __future__ import annotations

from talkanchor.config import Settings
from talkanchor.core.reconciler import Reconciler
from talkanchor.core.state import StateStore
from talkanchor.notify import build_notifier
from talkanchor.sources.base import IPSource
from talkanchor.sources.cloudflare import CloudflareTunnelSource
from talkanchor.sources.http_echo import HttpEchoSource
from talkanchor.targets.base import ConfigTarget
from talkanchor.targets.unifi_talk import UniFiTalkTarget


def build_sources(settings: Settings) -> list[IPSource]:
    sources: list[IPSource] = []
    cf = settings.cloudflare
    if cf.api_token.get_secret_value() and cf.account_id and cf.tunnel_id:
        sources.append(
            CloudflareTunnelSource(
                api_token=cf.api_token.get_secret_value(),
                account_id=cf.account_id,
                tunnel_id=cf.tunnel_id,
            )
        )
    if settings.http_echo.url:
        sources.append(
            HttpEchoSource(settings.http_echo.url, json_field=settings.http_echo.json_field or None)
        )
    return sources


def build_target(settings: Settings) -> ConfigTarget:
    return UniFiTalkTarget(settings.unifi_talk, local_backup_dir=settings.local_backup_dir)


def build_reconciler(settings: Settings, state: StateStore | None = None) -> Reconciler:
    state = state or StateStore(settings.state_db_path)
    return Reconciler(
        sources=build_sources(settings),
        target=build_target(settings),
        notifier=build_notifier(settings.notify),
        state=state,
        dry_run=settings.dry_run,
        min_seconds_between_changes=settings.min_seconds_between_changes,
    )
