from __future__ import annotations

import io

import paramiko
import pytest

from talkanchor.config import UniFiTalkTargetConfig
from talkanchor.targets.base import ConfigTargetError
from talkanchor.targets.unifi_talk import UniFiTalkTarget, _patch_param, connect_ssh

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
