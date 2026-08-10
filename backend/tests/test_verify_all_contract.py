import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def test_verify_all_checks_tracked_and_untracked_text_whitespace():
    source = (ROOT / "scripts" / "verify_all.ps1").read_text(encoding="utf-8")

    assert "function Invoke-RepositoryTextCheck" in source
    assert "git diff --check" in source
    assert "git ls-files --others --exclude-standard" in source
    assert "trailing whitespace" in source.lower()


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell 5/7 is not installed")
def test_verify_all_test_failure_code_returns_real_native_exit_code():
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "verify_all.ps1"),
            "-TestFailureCode",
            "37",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 37
    assert "Test failure code probe returned: 37" in result.stdout


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell 5/7 is not installed")
def test_verify_all_text_check_only_runs_repository_text_check():
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "verify_all.ps1"),
            "-TextCheckOnly",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "=== Git diff check ===" in result.stdout
