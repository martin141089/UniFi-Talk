from __future__ import annotations

from talkanchor.core.state import RETENTION_LIMIT, ChangeEvent


def test_get_last_known_ip_returns_none_when_no_events(state):
    assert state.get_last_known_ip() is None


def test_get_last_known_ip_uses_new_ip_for_a_successful_unreverted_change(state):
    state.record_change(ChangeEvent(old_ip="1.1.1.1", new_ip="2.2.2.2", dry_run=False, apply_success=True))
    assert state.get_last_known_ip() == "2.2.2.2"


def test_get_last_known_ip_uses_old_ip_when_the_change_was_rolled_back(state):
    # apply_success=True (the write itself worked) but a failed health
    # check triggered a rollback — the live config is back on old_ip, so
    # that's what should count as "current", not new_ip.
    state.record_change(
        ChangeEvent(
            old_ip="1.1.1.1", new_ip="2.2.2.2", dry_run=False, apply_success=True, health_ok=False, rolled_back=True
        )
    )
    assert state.get_last_known_ip() == "1.1.1.1"


def test_get_last_known_ip_ignores_failed_applies(state):
    state.record_change(ChangeEvent(old_ip="1.1.1.1", new_ip="2.2.2.2", dry_run=False, apply_success=False))
    assert state.get_last_known_ip() is None


def test_get_last_known_ip_ignores_dry_run_events_by_default(state):
    # A dry-run event never touches the target, so it must not make the
    # reconciler believe a pending real change is already applied.
    state.record_change(ChangeEvent(old_ip="1.1.1.1", new_ip="2.2.2.2", dry_run=True, apply_success=True))
    assert state.get_last_known_ip() is None
    assert state.get_last_known_ip(include_dry_run=True) == "2.2.2.2"


def test_record_change_prunes_oldest_events_past_retention_limit(state):
    for i in range(RETENTION_LIMIT + 10):
        state.record_change(ChangeEvent(old_ip=None, new_ip=f"10.0.0.{i}", dry_run=True, apply_success=True))

    events = state.recent_events(limit=RETENTION_LIMIT + 50)
    assert len(events) == RETENTION_LIMIT
    # the newest events survive, the oldest ones were pruned
    assert events[0].new_ip == f"10.0.0.{RETENTION_LIMIT + 9}"
    assert events[-1].new_ip == "10.0.0.10"
