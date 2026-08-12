"""Central logging setup: rich console handler + optional file handler + an
in-memory ring buffer the dashboard's "live log" view reads from."""

from __future__ import annotations

import logging
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from rich.logging import RichHandler


class RingBufferHandler(logging.Handler):
    """Keeps the last `capacity` log records in memory for the dashboard."""

    def __init__(self, capacity: int = 200) -> None:
        super().__init__()
        self.records: deque[dict[str, str]] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(
            {
                "time": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
            }
        )


live_log_handler = RingBufferHandler()


def configure_logging(*, level: str = "INFO", log_file: str | Path | None = None) -> None:
    live_log_handler.setFormatter(logging.Formatter("%(message)s"))
    handlers: list[logging.Handler] = [
        RichHandler(rich_tracebacks=True, show_path=False),
        live_log_handler,
    ]

    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )
