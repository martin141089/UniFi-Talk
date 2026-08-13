from __future__ import annotations

import io

import paramiko
import pytest

from talkanchor.config import UniFiTalkTargetConfig
from talkanchor.targets.base import ConfigTargetError
from talkanchor.targets.unifi_talk import (
    UniFiTalkTarget,
    _patch_param,
    connect_ssh,
    discover_sofia_configs,
    normalize_private_key_pem,
)


class _FakeSFTPFile:
    def __init__(self, files: dict[str, bytes], path: str, mode: str) -> None:
        self._files = files
        self._path = path
        self._buf = files.get(path, b"") if "r" in mode else b""

    def read(self) -> bytes:
        return self._buf

    def write(self, data: bytes) -> None:
        self._buf += data
        self._files[self._path] = self._buf

    def __enter__(self) -> _FakeSFTPFile:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class _FakeSFTP:
    def __init__(self, files: dict[str, bytes]) -> None:
        self._files = files

    def open(self, path: str, mode: str = "r") -> _FakeSFTPFile:
        return _FakeSFTPFile(self._files, path, mode)


class _FakeStdout:
    def __init__(self, text: str = "", exit_status: int = 0) -> None:
        self._text = text.encode()

        class _Channel:
            def recv_exit_status(_self) -> int:  # noqa: N805
                return exit_status

        self.channel = _Channel()

    def read(self) -> bytes:
        return self._text


class _FakeSSHClient:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.closed = False

    def open_sftp(self) -> _FakeSFTP:
        return _FakeSFTP(self.files)

    def exec_command(self, command: str, timeout: float = 30):
        return None, _FakeStdout(), _FakeStdout()

    def close(self) -> None:
        self.closed = True

SAMPLE_XML = """<profile name="external_talk">
  <settings>
    <param name="ext-sip-ip" value="203.0.113.7"/>
    <param name="ext-rtp-ip" value="203.0.113.7"/>
    <param name="auto-nat" value="false"/>
  </settings>
</profile>
"""


def test_patch_param_replaces_value():
    patched, found = _patch_param(SAMPLE_XML, "ext-sip-ip", "198.51.100.42")
    assert found is True
    assert 'name="ext-sip-ip" value="198.51.100.42"' in patched
    assert 'name="ext-rtp-ip" value="203.0.113.7"' in patched  # untouched


def test_patch_param_missing_param_reports_not_found():
    patched, found = _patch_param(SAMPLE_XML, "does-not-exist", "1.2.3.4")
    assert found is False
    assert patched == SAMPLE_XML


def test_normalize_private_key_pem_leaves_well_formed_key_usable():
    key = paramiko.RSAKey.generate(2048)
    buf = io.StringIO()
    key.write_private_key(buf)
    original = buf.getvalue()

    assert normalize_private_key_pem(original).replace("\n", "") == original.replace("\n", "")


def test_normalize_private_key_pem_rewraps_flattened_key(tmp_path):
    # Live-reproduced bug: a key that worked fine came back from Home
    # Assistant's Supervisor options with every line break stripped (its
    # generic Configuration tab renders password-typed fields as a
    # single-line box), and paramiko then rejects it outright.
    key = paramiko.RSAKey.generate(2048)
    buf = io.StringIO()
    key.write_private_key(buf)
    well_formed = buf.getvalue()
    flattened = well_formed.replace("\n", "")

    fixed = normalize_private_key_pem(flattened)
    assert "\n" in fixed

    key_path = tmp_path / "id_rsa"
    key_path.write_text(fixed)
    loaded = paramiko.RSAKey.from_private_key_file(str(key_path))
    assert loaded.get_base64() == key.get_base64()


def test_normalize_private_key_pem_leaves_non_pem_input_untouched():
    assert normalize_private_key_pem("not a key at all") == "not a key at all"
    assert normalize_private_key_pem("") == ""


def test_apply_dry_run_never_connects(tmp_path):
    config = UniFiTalkTargetConfig(
        host="udm.example.internal",
        config_path="/usr/local/freeswitch/conf/sofia.conf.d/external_talk.xml",
    )
    target = UniFiTalkTarget(config, local_backup_dir=tmp_path)

    result = target.apply("192.0.2.55", dry_run=True)

    assert result.success is True
    assert result.backup_path is None
    assert "192.0.2.55" in result.message
    assert list(tmp_path.iterdir()) == []  # no local backup was written either


def test_rollback_dry_run_never_connects(tmp_path):
    config = UniFiTalkTargetConfig(host="udm.example.internal", config_path="/x.xml")
    target = UniFiTalkTarget(config, local_backup_dir=tmp_path)

    result = target.rollback("/backups/x.xml.bak", dry_run=True)
    assert result.success is True


def test_discover_sofia_configs_prefers_content_match_over_filename():
    # Live-reproduced bug: a naive "sofia*.xml" filename search only ever
    # found FreeSWITCH's generic autoload_configs/sofia.conf.xml loader,
    # which never contains ext-sip-ip — the real profile file (arbitrarily
    # named, e.g. sip_profiles/external_talk.xml) was never surfaced.
    class _FakeClient:
        def exec_command(self, command: str, timeout: float = 30):
            if "grep" in command:
                return None, _FakeStdout("/etc/freeswitch/sip_profiles/external_talk.xml\n"), _FakeStdout()
            return None, _FakeStdout("/etc/freeswitch/autoload_configs/sofia.conf.xml\n"), _FakeStdout()

    candidates = discover_sofia_configs(_FakeClient())
    assert candidates == ["/etc/freeswitch/sip_profiles/external_talk.xml"]


def test_discover_sofia_configs_falls_back_to_filename_search_when_content_search_finds_nothing():
    class _FakeClient:
        def exec_command(self, command: str, timeout: float = 30):
            if "grep" in command:
                return None, _FakeStdout(""), _FakeStdout()
            return None, _FakeStdout("/etc/freeswitch/autoload_configs/sofia.conf.xml\n"), _FakeStdout()

    candidates = discover_sofia_configs(_FakeClient())
    assert candidates == ["/etc/freeswitch/autoload_configs/sofia.conf.xml"]


def test_apply_live_fails_safely_when_param_not_found_and_skips_backup(tmp_path, monkeypatch):
    # Live-reproduced bug: the discovered config_path didn't actually
    # contain ext-sip-ip/ext-rtp-ip (e.g. it was FreeSWITCH's generic
    # sofia.conf.xml loader, not the actual profile file). apply() must
    # fail without touching the remote file or creating a pointless
    # backup on every retry.
    files = {"/x.xml": b'<profile><settings><param name="something-else" value="1"/></settings></profile>'}
    fake_client = _FakeSSHClient(files)
    monkeypatch.setattr("talkanchor.targets.unifi_talk.connect_ssh", lambda **kwargs: fake_client)

    config = UniFiTalkTargetConfig(host="udm.example.internal", config_path="/x.xml", backup_dir_remote="/backups")
    target = UniFiTalkTarget(config, local_backup_dir=tmp_path)

    result = target.apply("198.51.100.9", dry_run=False)

    assert result.success is False
    assert "nicht in /x.xml gefunden" in result.message
    assert files["/x.xml"] == b'<profile><settings><param name="something-else" value="1"/></settings></profile>'
    assert list(files.keys()) == ["/x.xml"]  # no remote backup written
    assert list(tmp_path.iterdir()) == []  # no local backup written either
    assert fake_client.closed is True


def test_apply_live_success_patches_and_backs_up(tmp_path, monkeypatch):
    original = (
        b'<profile><settings>'
        b'<param name="ext-sip-ip" value="1.1.1.1"/>'
        b'<param name="ext-rtp-ip" value="1.1.1.1"/>'
        b"</settings></profile>"
    )
    files = {"/x.xml": original}
    fake_client = _FakeSSHClient(files)
    monkeypatch.setattr("talkanchor.targets.unifi_talk.connect_ssh", lambda **kwargs: fake_client)

    config = UniFiTalkTargetConfig(host="udm.example.internal", config_path="/x.xml", backup_dir_remote="/backups")
    target = UniFiTalkTarget(config, local_backup_dir=tmp_path)

    result = target.apply("198.51.100.9", dry_run=False)

    assert result.success is True
    assert result.backup_path is not None
    assert files["/x.xml"] == (
        b'<profile><settings>'
        b'<param name="ext-sip-ip" value="198.51.100.9"/>'
        b'<param name="ext-rtp-ip" value="198.51.100.9"/>'
        b"</settings></profile>"
    )
    assert files[result.backup_path] == original  # remote backup has the original content
    assert len(list(tmp_path.iterdir())) == 1  # local backup written too


def test_connect_ssh_explains_paramikos_misleading_rejected_auth_message(tmp_path, monkeypatch):
    # Paramiko tries RSA, then ECDSA, then Ed25519 against the same key
    # file; if the server rejects public-key auth outright (e.g. the
    # public key isn't actually in authorized_keys), the exception that
    # survives is the *last* class's unrelated "wrong key format" parse
    # error, not the real "authentication failed" reason. connect_ssh()
    # should translate that specific pattern into an actionable message.
    key = paramiko.RSAKey.generate(2048)
    buf = io.StringIO()
    key.write_private_key(buf)
    key_path = tmp_path / "id_rsa"
    key_path.write_text(buf.getvalue())
    key_path.chmod(0o600)

    def fake_connect(self, **kwargs):
        raise paramiko.SSHException("encountered RSA key, expected OPENSSH key")

    monkeypatch.setattr(paramiko.SSHClient, "connect", fake_connect)

    with pytest.raises(ConfigTargetError) as exc_info:
        connect_ssh(host="udm.example.internal", port=22, username="root", key_path=str(key_path))

    detail = str(exc_info.value)
    assert "abgelehnt" in detail
    assert "vollständige, exakte öffentliche Schlüssel" in detail
    assert "encountered RSA key, expected OPENSSH key" in detail  # raw message kept for debugging
