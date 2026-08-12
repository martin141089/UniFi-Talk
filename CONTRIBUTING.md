# Contributing to TalkAnchor

Thanks for considering a contribution! TalkAnchor is built around a small
plugin architecture on purpose, so most contributions don't need to touch
the core reconcile loop at all.

## Development setup

```sh
git clone https://github.com/martin141089/UniFi-Talk.git talkanchor
cd talkanchor
uv venv .venv && uv pip install -e ".[dev]" --python .venv/bin/python
.venv/bin/pytest
.venv/bin/ruff check src tests
.venv/bin/mypy src
```

(Any standard `venv`/`pip install -e ".[dev]"` works too — `uv` is just
faster.)

## Project layout

```
src/talkanchor/
├── core/       # polling loop, state, reconcile/diff logic — protocol-only, no I/O adapters
├── sources/    # IP-source adapters (implement IPSource)
├── targets/    # config-target adapters (implement ConfigTarget)
├── notify/     # notification adapters (implement Notifier)
├── wizard/     # interactive setup CLI
└── web/        # FastAPI dashboard
```

## Adding a new IP source adapter

Implement the `IPSource` protocol from `talkanchor.sources.base`:

```python
class MySource:
    name = "my_source"

    async def check(self) -> str:
        """Return the current public IP as a string, or raise IPSourceError."""
```

Register it in `talkanchor.core.factory.build_sources` behind its own config
section in `talkanchor.config`, and add tests mirroring
`tests/test_sources.py` (mock the HTTP layer, don't hit real endpoints in
CI).

## Adding a new config-target adapter

Implement the `ConfigTarget` protocol from `talkanchor.targets.base`:
`apply(new_ip, *, dry_run) -> ApplyResult`,
`health_check() -> HealthCheckResult`, `rollback(backup_path, *, dry_run) ->
RollbackResult`. `unifi_talk.py` is the reference implementation — look
there for the expected shape (dry-run never touches the network, apply()
always backs up before writing, health_check() polls with a timeout).

Non-negotiables for any new target adapter, matching TalkAnchor's safety
model (see [SECURITY.md](SECURITY.md)):

- Key-based auth only — no plaintext password fields.
- Back up before every write, with a way to roll back.
- `dry_run=True` must be a true no-op (no connection at all, ideally).

## Adding a new notification adapter

Implement the `Notifier` protocol from `talkanchor.notify.base`
(`async def send(self, notification: Notification) -> None`) and wire it
into `talkanchor.notify.build_notifier`.

## Code style

- Ruff for linting (`ruff check`), mypy for type checking — both run in CI
  and must pass.
- Prefer small, focused adapters over configuration flags inside existing
  ones.
- Tests use fakes (see `tests/fakes.py`) for the core loop — no real
  network/SSH calls in unit tests.

## Pull requests

- Keep PRs focused on one adapter/feature at a time.
- Include tests for new adapters.
- Update `CHANGELOG.md` under "Unreleased".
