# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""Which python3 each installer leaves first on PATH after it puts the system bins in front."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_INSTALLERS = {
    "inference_optimizer": Path(__file__).resolve().parents[1] / "assets" / "install.sh",
    "kernel_agent": Path(__file__).resolve().parents[2] / "agents" / "kernel" / "scripts" / "install.sh",
}
_NO_HOST_VENV = pytest.mark.skipif(
    Path("/opt/venv/bin/python").exists() or Path("/venv/bin/python").exists(), reason="a host venv wins"
)


def _path_block(installer: Path) -> str:
    text = installer.read_text()
    start = text.index("_caller_python_bin=")
    end = text.index("\ndone\n", start) + len("\ndone\n")
    return text[start:end]


def _interpreter(root: Path) -> Path:
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True)
    for name in ("python", "python3"):
        exe = bin_dir / name
        exe.write_text("#!/bin/sh\nexit 0\n")
        exe.chmod(0o755)
    return bin_dir


def _python3_after_block(installer: Path, path: str, virtual_env: str = "") -> str:
    script = f"set -euo pipefail\n{_path_block(installer)}\ncommand -v python3\n"
    env = {"PATH": path, **({"VIRTUAL_ENV": virtual_env} if virtual_env else {})}
    return subprocess.run(["bash", "-c", script], check=True, capture_output=True, text=True, env=env).stdout.strip()


@_NO_HOST_VENV
@pytest.mark.parametrize("installer", _INSTALLERS.values(), ids=_INSTALLERS.keys())
def test_an_image_interpreter_outside_the_known_venvs_stays_first(tmp_path: Path, installer: Path) -> None:
    """rocm/vllm rocm10 keeps its torch in /opt/python; docker mode gives install.sh no VIRTUAL_ENV for it."""
    image_bin = _interpreter(tmp_path / "opt-python")

    assert _python3_after_block(installer, f"{image_bin}:/usr/bin:/bin") == str(image_bin / "python3")


@_NO_HOST_VENV
@pytest.mark.parametrize("installer", _INSTALLERS.values(), ids=_INSTALLERS.keys())
def test_an_activated_virtualenv_still_outranks_the_callers_interpreter(tmp_path: Path, installer: Path) -> None:
    image_bin = _interpreter(tmp_path / "opt-python")
    venv_bin = _interpreter(tmp_path / "venv")

    assert _python3_after_block(installer, f"{image_bin}:/usr/bin:/bin", str(venv_bin.parent)) == str(
        venv_bin / "python3"
    )
