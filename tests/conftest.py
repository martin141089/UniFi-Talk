from __future__ import annotations

import pytest

from talkanchor.core.state import StateStore


@pytest.fixture
def state(tmp_path):
    return StateStore(tmp_path / "test.sqlite3")
