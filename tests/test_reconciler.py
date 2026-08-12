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
async def test_failed_apply_is_recorded_without_health_check(state):
    target = FakeTarget(apply_ok=False)
    source = FakeSource("a", "7.7.7.7")
    reconciler = make_reconciler(state, sources=[source], target=target, dry_run=False)

    outcome = await reconciler.run_once()
    assert outcome.event.apply_success is False
    assert target.health_checks == 0
