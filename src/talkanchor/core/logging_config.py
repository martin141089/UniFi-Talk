"""Central logging setup: rich console handler + optional file handler."""

from __future__ import annotations

import logging
from pathlib import Path

from rich.logging import RichHandler


def configure_logging(*, level: str = "INFO", log_file: str | Path | None = None) -> None:
    handlers: list[logging.Handler] = [RichHandler(rich_tracebacks=True, show_path=False)]

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
