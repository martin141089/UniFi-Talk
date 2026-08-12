"""The core reconcile loop: check sources, agree on an IP, diff against the
last known state, and — if it actually changed and we're not rate-limited —
apply it to the target, health-check it, and notify.

This module never touches SSH or Cloudflare directly; it only depends on the
`IPSource` / `ConfigTarget` / `Notifier` protocols, so it can be fully
exercised in tests with fakes (see tests/test_reconciler.py) as required for
Phase 1 (dry-run only, no real SSH).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from talkanchor.core.state import ChangeEvent, StateStore
from talkanchor.notify.base import Notification, NotificationLevel, Notifier
from talkanchor.sources.base import IPSource, IPSourceError
from talkanchor.targets.base import ConfigTarget

logger = logging.getLogger("talkanchor.reconciler")


class SourcesDisagreeError(RuntimeError):
    """Raised when configured IP sources return conflicting addresses."""


@dataclass
class ReconcileOutcome:
    checked_ip: str | None
    changed: bool
    rate_limited: bool = False
    event: ChangeEvent | None = None
    skipped_reason: str | None = None


class Reconciler:
    def __init__(
        self,
        *,
        sources: list[IPSource],
        target: ConfigTarget,
        notifier: Notifier,
        state: StateStore,
        dry_run: bool,
        min_seconds_between_changes: int,
    ) -> None:
        if not sources:
            raise ValueError("Reconciler requires at least one IP source")
        self._sources = sources
        self._target = target
        self._notifier = notifier
        self._state = state
        self._dry_run = dry_run
        self._min_seconds_between_changes = min_seconds_between_changes

    async def _agreed_ip(self) -> str:
        observations: dict[str, str] = {}
        errors: list[str] = []
        for source in self._sources:
            try:
                observations[source.name] = await source.check()
            except IPSourceError as exc:
                errors.append(f"{source.name}: {exc}")

        if not observations:
            raise IPSourceError(f"All IP sources failed: {'; '.join(errors)}")

        unique_ips = set(observations.values())
        if len(self._sources) > 1 and len(observations) < len(self._sources):
            logger.warning(
                "Only %d/%d IP sources responded (%s); proceeding cautiously with what we have",
                len(observations),
                len(self._sources),
                "; ".join(errors),
            )
        if len(unique_ips) > 1:
            raise SourcesDisagreeError(
                f"IP sources disagree, refusing to act: {observations}"
            )
        return unique_ips.pop()

    def _is_rate_limited(self) -> bool:
        last_change_at = self._state.last_change_at()
        if last_change_at is None:
            return False
        elapsed = (datetime.now(UTC) - last_change_at).total_seconds()
        return elapsed < self._min_seconds_between_changes

    async def run_once(self) -> ReconcileOutcome:
        try:
            current_ip = await self._agreed_ip()
        except (IPSourceError, SourcesDisagreeError) as exc:
            logger.error("IP check failed: %s", exc)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: IP check failed",
                    body=str(exc),
                    level=NotificationLevel.WARNING,
                )
            )
            return ReconcileOutcome(checked_ip=None, changed=False, skipped_reason=str(exc))

        last_known_ip = self._state.get_last_known_ip()
        if current_ip == last_known_ip:
            logger.debug("IP unchanged (%s); nothing to do", current_ip)
            return ReconcileOutcome(checked_ip=current_ip, changed=False)

        logger.info("IP change detected: %s -> %s", last_known_ip, current_ip)

        if self._is_rate_limited():
            message = (
                f"IP changed ({last_known_ip} -> {current_ip}) but a change was applied "
                f"within the last {self._min_seconds_between_changes}s; holding off to avoid "
                "flapping. Will retry next cycle."
            )
            logger.warning(message)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: change deferred (rate limit)",
                    body=message,
                    level=NotificationLevel.WARNING,
                )
            )
            return ReconcileOutcome(
                checked_ip=current_ip, changed=True, rate_limited=True, skipped_reason=message
            )

        return await self._apply_change(last_known_ip, current_ip)

    async def _apply_change(self, old_ip: str | None, new_ip: str) -> ReconcileOutcome:
        apply_result = self._target.apply(new_ip, dry_run=self._dry_run)

        event = ChangeEvent(
            old_ip=old_ip,
            new_ip=new_ip,
            dry_run=self._dry_run,
            apply_success=apply_result.success,
            apply_message=apply_result.message,
            backup_path=apply_result.backup_path,
        )

        if not apply_result.success:
            event = self._state.record_change(event)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: failed to apply new IP",
                    body=f"{old_ip} -> {new_ip} failed: {apply_result.message}",
                    level=NotificationLevel.ERROR,
                )
            )
            return ReconcileOutcome(checked_ip=new_ip, changed=True, event=event)

        if self._dry_run:
            event = self._state.record_change(event)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: dry-run would apply new IP",
                    body=f"{old_ip} -> {new_ip} (dry-run, no changes were written)",
                    level=NotificationLevel.INFO,
                )
            )
            return ReconcileOutcome(checked_ip=new_ip, changed=True, event=event)

        health = self._target.health_check()
        event.health_ok = health.healthy
        event.health_message = health.message

        if health.healthy:
            event = self._state.record_change(event)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: IP updated successfully",
                    body=f"{old_ip} -> {new_ip}, health check passed ({health.message})",
                    level=NotificationLevel.SUCCESS,
                )
            )
            return ReconcileOutcome(checked_ip=new_ip, changed=True, event=event)

        # Health check failed: notify clearly and offer/perform rollback if we have a backup.
        logger.error("Health check failed after applying %s: %s", new_ip, health.message)
        if apply_result.backup_path:
            rollback_result = self._target.rollback(apply_result.backup_path, dry_run=self._dry_run)
            event.rolled_back = rollback_result.success
            event.rollback_message = rollback_result.message
            event = self._state.record_change(event)
            level = NotificationLevel.WARNING if rollback_result.success else NotificationLevel.ERROR
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: health check failed, rollback attempted",
                    body=(
                        f"{old_ip} -> {new_ip} failed health check ({health.message}). "
                        f"Rollback {'succeeded' if rollback_result.success else 'FAILED'}: "
                        f"{rollback_result.message}"
                    ),
                    level=level,
                )
            )
        else:
            event = self._state.record_change(event)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: health check failed, no backup to roll back to",
                    body=f"{old_ip} -> {new_ip} failed health check ({health.message}).",
                    level=NotificationLevel.ERROR,
                )
            )

        return ReconcileOutcome(checked_ip=new_ip, changed=True, event=event)
