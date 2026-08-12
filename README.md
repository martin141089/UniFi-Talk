# TalkAnchor

> Deine dynamische IP im Griff. Stay registered. Stay reachable.

TalkAnchor keeps a self-hosted [UniFi Talk](https://ui.com/talk) install
anchored to your current dynamic public IP by watching a Cloudflare Tunnel
connector and patching the FreeSWITCH Sofia SIP profile over SSH whenever it
drifts.

**Status:** early alpha, work in progress. Full README with quickstart,
architecture and screenshots lands in Phase 5.

⚠️ **Not an official Ubiquiti product.** See [SECURITY.md](SECURITY.md) and
the disclaimer that will ship in the full README before running this
against production hardware. Always start in dry-run mode.

## License

[MIT](LICENSE)
