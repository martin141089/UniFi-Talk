# Security Policy

TalkAnchor connects to your UniFi Talk device over SSH and patches a live
FreeSWITCH configuration file. Please read this before deploying it.

## Disclaimer

⚠️ **TalkAnchor is not an official Ubiquiti product.** It modifies a
configuration file that the UniFi Talk application manages internally and
does not officially document. Use at your own risk. Always run in dry-run
mode first and keep a current backup of your UniFi system before your first
live run.

## Design principles

- **SSH key authentication only.** There is no password field anywhere in
  the configuration schema — `talkanchor.config.UniFiTalkTargetConfig` has
  no such field, and the wizard never asks for one.
- **Host key verification is enforced.** The SSH client rejects unknown host
  keys (`paramiko.RejectPolicy`) instead of trust-on-first-use. Add your
  UDM's host key with `ssh-keyscan -H <host> >> ~/.ssh/known_hosts` before
  first use.
- **Dry-run is the default.** `dry_run: true` ships as the default in
  `config.yaml`/`.env.example`; going live via the setup wizard requires a
  second, explicit `GO LIVE` confirmation.
- **Every write is backed up first**, both on the remote device
  (`unifi_talk.backup_dir_remote`) and locally (`<data_dir>/backups`), with
  a timestamp, before any config file is touched.
- **Health-checked, not fire-and-forget.** After a live change, TalkAnchor
  polls `sofia status` for up to `health_check_timeout_seconds` before
  declaring success; on failure it attempts an automatic rollback and
  notifies you either way — it never fails silently.
- **Rate-limited.** `min_seconds_between_changes` prevents a flapping IP
  signal from causing repeated SIP profile restarts.
- **Secrets never reach the repo or logs.** `config.yaml`/`.env` are
  `.gitignore`d and written with `0600` permissions by the wizard; log
  output never includes token/password values.

## Recommended Cloudflare API token scope

Create a token scoped to **Account → Cloudflare Tunnel → Read** only. No
write or zone-level access is required.

## Reporting a vulnerability

If you find a security issue, please open a
[private security advisory](https://github.com/martin141089/UniFi-Talk/security/advisories/new)
instead of a public issue. We'll respond as soon as possible.

## Manual restore

If you ever need to restore a backup by hand (e.g. TalkAnchor itself is
down), the file is a plain XML copy — SSH in and copy it back:

```sh
ssh <user>@<udm-host>
cp /root/talkanchor-backups/<file>.bak <path-to-sofia-profile.xml>
fs_cli -x "reloadxml"
fs_cli -x "sofia profile <profile-name> restart"
```
