from pathlib import Path

import pytest

from karaoke_server.cli import main
from karaoke_server.tls import ensure_certificate, fingerprint


def test_certificate_is_made_once_and_pinned(tmp_path: Path) -> None:
    cert, key = ensure_certificate(tmp_path, ("karaoke.tail1234.ts.net", "192.168.1.20"))
    pin = fingerprint(cert)
    assert len(pin) == 64
    again, _ = ensure_certificate(tmp_path)
    assert fingerprint(again) == pin
    assert key.stat().st_mode & 0o077 == 0


def test_operator_and_enrollment_commands(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = ["--data", str(tmp_path)]
    assert main([*data, "operator", "add", "Gael"]) == 0
    assert capsys.readouterr().out.startswith("op_")
    assert main([*data, "enroll", "player"]) == 0
    assert capsys.readouterr().out.startswith("enrol_p_")
    assert main([*data, "nodes"]) == 0
    assert main([*data, "gc"]) == 0
    assert "deleted 0" in capsys.readouterr().out
    assert main([*data, "fingerprint"]) == 0
    assert len(capsys.readouterr().out.strip()) == 64
    assert main([*data, "backup", str(tmp_path / "copy")]) == 0
    assert (tmp_path / "copy" / "karaoke-v4.db").is_file()
