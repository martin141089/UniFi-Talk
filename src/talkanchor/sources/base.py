"""IP-source adapter interface.

Any class implementing `check() -> str` (an IPv4/IPv6 address string) and
carrying a `name` attribute can be plugged in as a source. This is the
extension point community adapters (STUN, other DNS/tunnel providers, ...)
are meant to implement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class IPSourceError(RuntimeError):
    """Raised when a source cannot determine the current public IP."""


@runtime_checkable
class IPSource(Protocol):
    name: str

    async def check(self) -> str:
        """Return the currently observed public IP address as a string."""
        ...


@dataclass(frozen=True)
class IPObservation:
    source: str
    ip: str
