"""Reference config-target adapter: patches UniFi Talk's FreeSWITCH Sofia
SIP profile over SSH.

UniFi Talk (FreeSWITCH under the hood) keeps its external SIP/RTP IP in a
Sofia profile XML, e.g.:

    <profile name="external_talk">
      <settings>
        <param name="ext-sip-ip" value="203.0.113.7"/>
        <param name="ext-rtp-ip" value="203.0.113.7"/>
        ...
      </settings>
    </profile>

The exact file path is device/firmware-dependent and not documented by
Ubiquiti, which is why the setup wizard offers SSH-based discovery
(`discover_sofia_configs`) instead of hardcoding one.

Security notes:
  * SSH key auth only — this adapter has no password parameter at all.
  * Host keys are verified against ~/.ssh/known_hosts (and the system host
    key store); unknown hosts are rejected rather than silently trusted.
    Run `ssh-keyscan -H <host> >> ~/.ssh/known_hosts` once during setup.
  * Every apply() takes a timestamped backup (remote + local copy) before
    writing anything.
  * In dry-run mode this adapter never opens an SSH connection at all.
"""

from __future__ import annotations

import logging
import re
import shlex
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import paramiko

from talkanchor.config import UniFiTalkTargetConfig
from talkanchor.targets.base import (
    ApplyResult,
    ConfigTargetError,
    HealthCheckResult,
    RollbackResult,
)

logger = logging.getLogger("talkanchor.targets.unifi_talk")

_PARAM_TEMPLATE = re.compile(
    r'(<param\s+name="{param}"\s+value=")[^"]*("\s*/?>)',
)


def _patch_param(xml_text: str, param_name: str, new_value: str) -> tuple[str, bool]:
    pattern = re.compile(_PARAM_TEMPLATE.pattern.format(param=re.escape(param_name)))
    new_text, count = pattern.subn(rf"\g<1>{new_value}\g<2>", xml_text)
    return new_text, count > 0


def discover_sofia_configs(client: paramiko.SSHClient) -> list[str]:
    """Best-effort SSH discovery of candidate Sofia profile XML files.

    Used by the setup wizard so the user doesn't have to know UniFi Talk's
    internal filesystem layout.
    """
    _, stdout, _ = client.exec_command(
        'find / -xdev -iname "sofia*.xml" 2>/dev/null', timeout=30
    )
    paths = [line.strip() for line in stdout.read().decode("utf-8", "ignore").splitlines() if line.strip()]
    return paths


def fetch_host_key(host: str, port: int, *, timeout: float = 10.0) -> str:
    """Fetch `host:port`'s SSH host key without verifying it against
    known_hosts — this *is* the trust-on-first-use step. It's meant to be
    reviewed and pasted into `unifi_ssh_known_hosts_entry` by the user
    (e.g. from the setup helper in the dashboard when there's no terminal
    to run `ssh-keyscan` from, such as the Home Assistant add-on), not
    auto-trusted by TalkAnchor itself.
    """
    sock = socket.create_connection((host, port), timeout=timeout)
    transport = paramiko.Transport(sock)
    try:
        transport.start_client(timeout=timeout)
        key = transport.get_remote_server_key()
    finally:
        transport.close()
    return f"{host} {key.get_name()} {key.get_base64()}"


def connect_ssh(*, host: str, port: int, username: str, key_path: str) -> paramiko.SSHClient:
    """Open a host-key-verified SSH connection. Shared by UniFiTalkTarget
    and the dashboard's setup helper (SSH-based Sofia config discovery)."""
    if not host:
        raise ConfigTargetError("SSH host is not configured.")

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    known_hosts = Path("~/.ssh/known_hosts").expanduser()
    if known_hosts.exists():
        client.load_host_keys(str(known_hosts))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())

    resolved_key_path = Path(key_path).expanduser()
    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            key_filename=str(resolved_key_path),
            timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )
    except paramiko.SSHException as exc:
        raise ConfigTargetError(
            f"SSH connection to {host} failed: {exc}. If this is the first connection, "
            f"fetch the host key first (setup helper, or `ssh-keyscan -H {host} "
            ">> ~/.ssh/known_hosts` on a workstation)."
        ) from exc
    return client


@dataclass
class _Connection:
    client: paramiko.SSHClient
    sftp: paramiko.SFTPClient


class UniFiTalkTarget:
    name = "unifi_talk"

    def __init__(self, config: UniFiTalkTargetConfig, *, local_backup_dir: str | Path) -> None:
        self._config = config
        self._local_backup_dir = Path(local_backup_dir)

    # -- connection -----------------------------------------------------

    def _connect(self) -> paramiko.SSHClient:
        cfg = self._config
        if not cfg.config_path:
            raise ConfigTargetError(
                "UniFi Talk target is not configured (config_path missing). "
                "Run `talkanchor setup` first."
            )
        return connect_ssh(host=cfg.host, port=cfg.ssh_port, username=cfg.ssh_user, key_path=cfg.ssh_key_path)

    def _run(self, client: paramiko.SSHClient, command: str, *, timeout: float = 30) -> tuple[int, str, str]:
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        return exit_status, stdout.read().decode("utf-8", "ignore"), stderr.read().decode("utf-8", "ignore")

    # -- apply ------------------------------------------------------------

    def apply(self, new_ip: str, *, dry_run: bool) -> ApplyResult:
        cfg = self._config
        if dry_run:
            return ApplyResult(
                success=True,
                backup_path=None,
                message=(
                    f"[dry-run] would back up {cfg.config_path} and set "
                    f"{cfg.ext_sip_ip_param}={new_ip}, {cfg.ext_rtp_ip_param}={new_ip} on "
                    f"{cfg.host}, then reload sofia profile '{cfg.sofia_profile}'"
                ),
            )

        client = self._connect()
        try:
            sftp = client.open_sftp()
            try:
                with sftp.open(cfg.config_path, "r") as fh:
                    original_text = fh.read().decode("utf-8")
            except OSError as exc:
                raise ConfigTargetError(
                    f"Could not read {cfg.config_path} on {cfg.host}: {exc}"
                ) from exc

            backup_path = self._backup(client, sftp, cfg.config_path, original_text)

            patched_text, sip_found = _patch_param(original_text, cfg.ext_sip_ip_param, new_ip)
            patched_text, rtp_found = _patch_param(patched_text, cfg.ext_rtp_ip_param, new_ip)
            if not sip_found or not rtp_found:
                missing = []
                if not sip_found:
                    missing.append(cfg.ext_sip_ip_param)
                if not rtp_found:
                    missing.append(cfg.ext_rtp_ip_param)
                raise ConfigTargetError(
                    f"Parameter(s) {missing} not found in {cfg.config_path}. Config layout may "
                    "differ from what was discovered during setup — re-run `talkanchor setup "
                    "--discover` to confirm the path."
                )

            with sftp.open(cfg.config_path, "w") as fh:
                fh.write(patched_text.encode("utf-8"))

            reload_status, reload_out, reload_err = self._run(
                client, 'fs_cli -x "reloadxml"'
            )
            restart_status, restart_out, restart_err = self._run(
                client, f'fs_cli -x "sofia profile {shlex.quote(cfg.sofia_profile)} restart"'
            )

            if reload_status != 0 or restart_status != 0:
                raise ConfigTargetError(
                    f"fs_cli commands failed (reloadxml exit={reload_status}: {reload_err or reload_out}; "
                    f"restart exit={restart_status}: {restart_err or restart_out})"
                )

            return ApplyResult(
                success=True,
                backup_path=backup_path,
                message=f"Patched {cfg.config_path} to {new_ip} and restarted profile '{cfg.sofia_profile}'",
            )
        except ConfigTargetError as exc:
            return ApplyResult(success=False, backup_path=None, message=str(exc))
        finally:
            client.close()

    def _backup(
        self, client: paramiko.SSHClient, sftp: paramiko.SFTPClient, config_path: str, original_text: str
    ) -> str:
        cfg = self._config
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        filename = Path(config_path).name
        remote_backup_path = f"{cfg.backup_dir_remote.rstrip('/')}/{filename}.{timestamp}.bak"

        mkdir_status, _, mkdir_err = self._run(client, f"mkdir -p {shlex.quote(cfg.backup_dir_remote)}")
        if mkdir_status != 0:
            raise ConfigTargetError(f"Could not create remote backup dir: {mkdir_err}")

        with sftp.open(remote_backup_path, "w") as fh:
            fh.write(original_text.encode("utf-8"))

        self._local_backup_dir.mkdir(parents=True, exist_ok=True)
        local_backup_path = self._local_backup_dir / f"{filename}.{timestamp}.bak"
        local_backup_path.write_text(original_text, encoding="utf-8")

        logger.info("Backed up %s to %s (remote) and %s (local)", config_path, remote_backup_path, local_backup_path)
        return remote_backup_path

    # -- health check -----------------------------------------------------

    def health_check(self) -> HealthCheckResult:
        cfg = self._config
        client = self._connect()
        try:
            import time

            deadline = time.monotonic() + cfg.health_check_timeout_seconds
            last_output = ""
            while time.monotonic() < deadline:
                status, out, _err = self._run(
                    client, f'fs_cli -x "sofia status profile {shlex.quote(cfg.sofia_profile)} reg"'
                )
                last_output = out
                if status == 0 and self._registrations_ok(out, cfg.expected_registrations):
                    return HealthCheckResult(
                        healthy=True,
                        details={"sofia_status": out.strip()},
                        message=f"Profile '{cfg.sofia_profile}' registrations look healthy",
                    )
                time.sleep(2)

            return HealthCheckResult(
                healthy=False,
                details={"sofia_status": last_output.strip()},
                message=(
                    f"Profile '{cfg.sofia_profile}' did not show healthy registrations within "
                    f"{cfg.health_check_timeout_seconds}s"
                ),
            )
        finally:
            client.close()

    @staticmethod
    def _registrations_ok(sofia_status_output: str, expected_registrations: list[str]) -> bool:
        if not expected_registrations:
            return "REGED" in sofia_status_output
        return all(
            reg in sofia_status_output and "REGED" in sofia_status_output for reg in expected_registrations
        )

    # -- rollback -----------------------------------------------------------

    def rollback(self, backup_path: str, *, dry_run: bool) -> RollbackResult:
        cfg = self._config
        if dry_run:
            return RollbackResult(success=True, message=f"[dry-run] would restore {backup_path} -> {cfg.config_path}")

        client = self._connect()
        try:
            status, _out, err = self._run(
                client, f"cp {shlex.quote(backup_path)} {shlex.quote(cfg.config_path)}"
            )
            if status != 0:
                return RollbackResult(success=False, message=f"Failed to restore backup: {err}")

            self._run(client, 'fs_cli -x "reloadxml"')
            restart_status, _out2, err2 = self._run(
                client, f'fs_cli -x "sofia profile {shlex.quote(cfg.sofia_profile)} restart"'
            )
            if restart_status != 0:
                return RollbackResult(success=False, message=f"Restored file but restart failed: {err2}")

            return RollbackResult(success=True, message=f"Restored {cfg.config_path} from {backup_path}")
        finally:
            client.close()
