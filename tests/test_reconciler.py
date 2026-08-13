from __future__ import annotations

import pytest

from talkanchor.core.reconciler import Reconciler
from tests.fakes import FakeNotifier, FakeSource, FakeTarget


def make_reconciler(state, *, sources, target=None, notifier=None, dry_run=True, min_seconds=300):
    return Reconciler(
        sources=sources,
        target=target or FakeTarget(),
        notifier=notifier or FakeNotifier(),
        state=state,
        dry_run=dry_run,
        min_seconds_between_changes=min_seconds,
    )


@pytest.mark.asyncio
async def test_no_change_when_ip_matches_last_known(state):
    target = FakeTarget()
    reconciler = make_reconciler(state, sources=[FakeSource("a", "1.2.3.4")], target=target)

    first = await reconciler.run_once()
    assert first.changed is True

    second = await reconciler.run_once()
    assert second.changed is False
    assert target.applied_ips == ["1.2.3.4"]


@pytest.mark.asyncio
async def test_dry_run_never_calls_health_check_or_writes(state):
    target = FakeTarget()
    reconciler = make_reconciler(state, sources=[FakeSource("a", "9.9.9.9")], target=target, dry_run=True)

    outcome = await reconciler.run_once()
    assert outcome.changed is True
    assert outcome.event.dry_run is True
    assert outcome.event.backup_path is None
    assert target.health_checks == 0


@pytest.mark.asyncio
async def test_sources_must_agree(state):
    sources = [FakeSource("a", "1.1.1.1"), FakeSource("b", "2.2.2.2")]
    reconciler = make_reconciler(state, sources=sources)
    outcome = await reconciler.run_once()
    assert outcome.changed is False
    assert outcome.skipped_reason is not None


@pytest.mark.asyncio
async def test_single_failing_source_does_not_block_the_other(state):
    sources = [FakeSource("a", "1.1.1.1"), FakeSource("b", error="boom")]
    reconciler = make_reconciler(state, sources=sources)
    outcome = await reconciler.run_once()
    assert outcome.changed is True
    assert outcome.checked_ip == "1.1.1.1"


@pytest.mark.asyncio
async def test_all_sources_failing_is_reported_and_skipped(state):
    sources = [FakeSource("a", error="boom-a"), FakeSource("b", error="boom-b")]
    notifier = FakeNotifier()
    reconciler = make_reconciler(state, sources=sources, notifier=notifier)
    outcome = await reconciler.run_once()
    assert outcome.checked_ip is None
    assert outcome.changed is False
    assert len(notifier.sent) == 1


@pytest.mark.asyncio
async def test_rate_limit_defers_second_change(state):
    target = FakeTarget()
    source = FakeSource("a", "1.1.1.1")
    reconciler = make_reconciler(state, sources=[source], target=target, dry_run=False, min_seconds=300)
    await reconciler.run_once()

    source.ip = "2.2.2.2"
    outcome = await reconciler.run_once()
    assert outcome.rate_limited is True
    assert target.applied_ips == ["1.1.1.1"]  # second change was withheld


@pytest.mark.asyncio
async def test_failed_health_check_triggers_rollback(state):
    target = FakeTarget(health_ok=False, rollback_ok=True)
    source = FakeSource("a", "5.5.5.5")
    reconciler = make_reconciler(state, sources=[source], target=target, dry_run=False)

    outcome = await reconciler.run_once()
    assert outcome.event.health_ok is False
    assert outcome.event.rolled_back is True
    assert target.rolled_back_from == ["/backups/5.5.5.5.bak"]


@pytest.mark.asyncio
async def test_rollback_leaves_old_ip_as_last_known_so_it_gets_retried(state):
    # Live-reproduced bug: apply() succeeds (the write itself worked) but
    # the health check then fails and rollback restores old_ip. The next
    # cycle sees the same detected IP again and must treat that as a
    # change to retry, not as "already applied" — the live config is back
    # on old_ip, not new_ip, even though this event's apply_success=True.
    target = FakeTarget(health_ok=False, rollback_ok=True)
    source = FakeSource("a", "5.5.5.5")
    reconciler = make_reconciler(state, sources=[source], target=target, dry_run=False, min_seconds=0)

    first = await reconciler.run_once()
    assert first.event.rolled_back is True
    assert target.applied_ips == ["5.5.5.5"]

    second = await reconciler.run_once()
    assert second.changed is True  # not silently treated as "no change"
    assert target.applied_ips == ["5.5.5.5", "5.5.5.5"]  # retried


@pytest.mark.asyncio
async def test_dry_run_save_after_rollback_does_not_block_the_real_retry(state):
    # Live-reproduced bug: a real apply fails its health check and rolls
    # back (old_ip stays current). The operator then briefly switches to
    # dry-run (e.g. the wizard's "save as dry-run" preview) and back to
    # live before the next poll. The intervening dry-run event must not
    # make the reconciler think the real target is already on new_ip.
    target = FakeTarget(health_ok=False, rollback_ok=True)
    source = FakeSource("a", "5.5.5.5")
    live_reconciler = make_reconciler(state, sources=[source], target=target, dry_run=False, min_seconds=0)

    first = await live_reconciler.run_once()
    assert first.event.rolled_back is True
    assert target.applied_ips == ["5.5.5.5"]

    dry_run_reconciler = make_reconciler(state, sources=[source], target=target, dry_run=True, min_seconds=0)
    dry_outcome = await dry_run_reconciler.run_once()
    assert dry_outcome.event.dry_run is True

    second = await live_reconciler.run_once()
    assert second.changed is True  # not silently treated as "already applied"
    assert second.event.dry_run is False
    assert second.event.backup_path is not None  # a real (non-dry-run) apply happened


@pytest.mark.asyncio
async def test_failed_apply_is_recorded_without_health_check(state):
    target = FakeTarget(apply_ok=False)
    source = FakeSource("a", "7.7.7.7")
    reconciler = make_reconciler(state, sources=[source], target=target, dry_run=False)

    outcome = await reconciler.run_once()
    assert outcome.event.apply_success is False
    assert target.health_checks == 0
