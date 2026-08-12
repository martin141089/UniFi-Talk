"""In-memory fakes for the source/target/notifier protocols, used across tests
so the core reconcile loop can be fully exercised without any network or SSH."""

from __future__ import annotations

from talkanchor.notify.base import Notification
from talkanchor.sources.base import IPSourceError
from talkanchor.targets.base import ApplyResult, HealthCheckResult, RollbackResult


class FakeSource:
    def __init__(self, name: str, ip: str | None = None, error: str | None = None) -> None:
        self.name = name
        self.ip = ip
        self.error = error
        self.calls = 0

    async def check(self) -> str:
        self.calls += 1
        if self.error:
            raise IPSourceError(self.error)
        assert self.ip is not None
        return self.ip


class FakeTarget:
    name = "fake_target"

    def __init__(self, *, apply_ok: bool = True, health_ok: bool = True, rollback_ok: bool = True) -> None:
        self.apply_ok = apply_ok
        self.health_ok = health_ok
        self.rollback_ok = rollback_ok
        self.applied_ips: list[str] = []
        self.rolled_back_from: list[str] = []
        self.health_checks = 0

    def apply(self, new_ip: str, *, dry_run: bool) -> ApplyResult:
        self.applied_ips.append(new_ip)
        if not self.apply_ok:
            return ApplyResult(success=False, backup_path=None, message="apply failed")
        return ApplyResult(
            success=True,
            backup_path=None if dry_run else f"/backups/{new_ip}.bak",
            message="ok" if dry_run else f"applied {new_ip}",
        )

    def health_check(self) -> HealthCheckResult:
        self.health_checks += 1
        return HealthCheckResult(healthy=self.health_ok, message="ok" if self.health_ok else "not healthy")

    def rollback(self, backup_path: str, *, dry_run: bool) -> RollbackResult:
        self.rolled_back_from.append(backup_path)
        message = "rolled back" if self.rollback_ok else "rollback failed"
        return RollbackResult(success=self.rollback_ok, message=message)


class FakeNotifier:
    name = "fake_notifier"

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    async def send(self, notification: Notification) -> None:
        self.sent.append(notification)
