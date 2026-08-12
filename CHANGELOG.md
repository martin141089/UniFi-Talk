# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-08-12

Initial alpha release.

### Added

- Dual-source IP reconcile loop: Cloudflare Tunnel connector IP (primary)
  cross-checked against a configurable HTTP echo fallback, requiring
  agreement before acting.
- UniFi Talk SSH target adapter: key-only auth with host-key verification,
  timestamped remote+local backups before every write, Sofia XML patching,
  `fs_cli` reloadxml/profile-restart, `sofia status` health-check polling
  with automatic rollback on failure, and rate limiting against flapping
  IPs.
- Dry-run mode, on by default.
- Pluggable notification adapters: ntfy, generic webhook, email.
- Interactive setup wizard (`talkanchor setup`) with SSH-based Sofia config
  discovery and an explicit second confirmation before going live.
- `talkanchor` CLI: `setup`, `check`, `run`, `web`, `rollback`.
- Local web dashboard: current IP, health status, change history, live
  log, manual check-now / rollback-to-backup actions.
- Plugin architecture (`IPSource`, `ConfigTarget`, `Notifier` protocols) so
  UniFi Talk is a reference target, not the only one.
- Docker image + Compose file; multi-arch (amd64/arm64) publish to GHCR on
  tagged releases.
- Home Assistant add-on wrapper.
- Full test suite for the core reconcile loop using in-memory fakes (no
  real network/SSH required).

[Unreleased]: https://github.com/martin141089/UniFi-Talk/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/martin141089/UniFi-Talk/releases/tag/v0.1.0
