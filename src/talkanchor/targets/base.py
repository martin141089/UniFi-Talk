"""Config-target adapter interface.

A target adapter knows how to patch a specific system's SIP/IP configuration
to a new public IP, verify the change worked, and roll it back if not. UniFi
Talk (`unifi_talk.py`) is the reference implementation; the interface is
generic enough for other targets (pfSense, FreePBX, ...) to be added by the
community.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ApplyResult:
    success: bool
    backup_path: str | None = None
    message: str = ""


@dataclass
class HealthCheckResult:
    healthy: bool
    details: dict[str, str] = field(default_factory=dict)
    message: str = ""


@dataclass
class RollbackResult:
    success: bool
    message: str = ""


class ConfigTargetError(RuntimeError):
    """Raised when a target adapter cannot apply, check, or roll back a change."""


@runtime_checkable
class ConfigTarget(Protocol):
    name: str

    def apply(self, new_ip: str, *, dry_run: bool) -> ApplyResult:
        """Back up the current config and patch it to `new_ip`. No-op write in dry-run."""
        ...

    def health_check(self) -> HealthCheckResult:
        """Verify the target came back up correctly after an apply()."""
        ...

    def rollback(self, backup_path: str, *, dry_run: bool) -> RollbackResult:
        """Restore the config from a previously taken backup."""
        ...
