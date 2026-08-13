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
            raise IPSourceError(f"Alle IP-Quellen fehlgeschlagen: {'; '.join(errors)}")

        unique_ips = set(observations.values())
        if len(self._sources) > 1 and len(observations) < len(self._sources):
            logger.warning(
                "Nur %d/%d IP-Quellen haben geantwortet (%s); fahre vorsichtig mit dem fort, was vorliegt",
                len(observations),
                len(self._sources),
                "; ".join(errors),
            )
        if len(unique_ips) > 1:
            raise SourcesDisagreeError(
                f"IP-Quellen widersprechen sich, keine Aktion: {observations}"
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
            logger.error("IP-Prüfung fehlgeschlagen: %s", exc)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: IP-Prüfung fehlgeschlagen",
                    body=str(exc),
                    level=NotificationLevel.WARNING,
                )
            )
            return ReconcileOutcome(checked_ip=None, changed=False, skipped_reason=str(exc))

        last_known_ip = self._state.get_last_known_ip(include_dry_run=self._dry_run)
        if current_ip == last_known_ip:
            logger.debug("IP unverändert (%s); nichts zu tun", current_ip)
            return ReconcileOutcome(checked_ip=current_ip, changed=False)

        logger.info("IP-Änderung erkannt: %s -> %s", last_known_ip, current_ip)

        if self._is_rate_limited():
            message = (
                f"IP geändert ({last_known_ip} -> {current_ip}), aber innerhalb der letzten "
                f"{self._min_seconds_between_changes}s wurde bereits eine Änderung angewendet; "
                "wird zurückgestellt, um Flattern zu vermeiden. Nächster Zyklus versucht es erneut."
            )
            logger.warning(message)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: Änderung zurückgestellt (Rate-Limit)",
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
                    title="TalkAnchor: Anwenden der neuen IP fehlgeschlagen",
                    body=f"{old_ip} -> {new_ip} fehlgeschlagen: {apply_result.message}",
                    level=NotificationLevel.ERROR,
                )
            )
            return ReconcileOutcome(checked_ip=new_ip, changed=True, event=event)

        if self._dry_run:
            event = self._state.record_change(event)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: Dry-Run würde neue IP anwenden",
                    body=f"{old_ip} -> {new_ip} (Dry-Run, es wurde nichts geschrieben)",
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
                    title="TalkAnchor: IP erfolgreich aktualisiert",
                    body=f"{old_ip} -> {new_ip}, Health-Check bestanden ({health.message})",
                    level=NotificationLevel.SUCCESS,
                )
            )
            return ReconcileOutcome(checked_ip=new_ip, changed=True, event=event)

        # Health-Check fehlgeschlagen: klar benachrichtigen und Rollback anbieten/durchführen, falls Backup vorhanden.
        logger.error("Health-Check nach Anwenden von %s fehlgeschlagen: %s", new_ip, health.message)
        if apply_result.backup_path:
            rollback_result = self._target.rollback(apply_result.backup_path, dry_run=self._dry_run)
            event.rolled_back = rollback_result.success
            event.rollback_message = rollback_result.message
            event = self._state.record_change(event)
            level = NotificationLevel.WARNING if rollback_result.success else NotificationLevel.ERROR
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: Health-Check fehlgeschlagen, Rollback versucht",
                    body=(
                        f"{old_ip} -> {new_ip} hat den Health-Check nicht bestanden ({health.message}). "
                        f"Rollback {'erfolgreich' if rollback_result.success else 'FEHLGESCHLAGEN'}: "
                        f"{rollback_result.message}"
                    ),
                    level=level,
                )
            )
        else:
            event = self._state.record_change(event)
            await self._notifier.send(
                Notification(
                    title="TalkAnchor: Health-Check fehlgeschlagen, kein Backup für Rollback vorhanden",
                    body=f"{old_ip} -> {new_ip} hat den Health-Check nicht bestanden ({health.message}).",
                    level=NotificationLevel.ERROR,
                )
            )

        return ReconcileOutcome(checked_ip=new_ip, changed=True, event=event)
