# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""Round-trip tests for the .env writers in both installers against every .env reader."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from hyperloom.inference_optimizer.cli import preflight

_ASSETS = Path(__file__).resolve().parents[1] / "assets"
_INSTALL_SH = _ASSETS / "install_baremetal.sh"
_KERNEL_INSTALL_SH = Path(__file__).resolve().parents[2] / "agents" / "kernel" / "scripts" / "install.sh"
# Both installers must stay self-contained, so each carries its own writer; both are held to the same contract.
_WRITERS = {"install_baremetal": _INSTALL_SH, "kernel_install": _KERNEL_INSTALL_SH}
_RUNTIME_ENV_SH = _ASSETS / "runtime_env.sh"

_VALUES = (
    "sk-ant-api03-plain_value.1",
    "<PLEASE_FILL_IN>",
    "Ocp-Apim-Subscription-Key: secret",
    "a;b",
    "$HOME/literal",
    "~/not-expanded",
    "it's quoted",
    'it\'s \\ "double" quoted',
    "",
)


def _functions(script: Path, *names: str) -> str:
    chunks = []
    for name in names:
        chunk = subprocess.run(
            ["sed", "-n", f"/^{name}()/,/^}}/p", str(script)], check=True, capture_output=True, text=True
        ).stdout
        assert chunk.strip(), f"{name}() not found in {script.name}"
        chunks.append(chunk)
    return "\n".join(chunks)


def _bash(body: str, writer: Path = _INSTALL_SH, **env: str) -> str:
    script = (
        "set -euo pipefail\n"
        + _functions(writer, "dotenv_render_value", "upsert_dotenv_var", "remove_dotenv_var")
        + _functions(_INSTALL_SH, "read_dotenv_var")
        + body
    )
    result = subprocess.run(
        ["bash", "-c", script], check=True, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", **env}
    )
    return result.stdout


def _write(dotenv: Path, value: str, writer: Path = _INSTALL_SH) -> None:
    dotenv.write_text("HYPERLOOM_RUN_MODE=baremetal\nHL_TEST_VALUE=stale\n")
    _bash('\nupsert_dotenv_var HL_TEST_VALUE "$VALUE"\n', writer, DOTENV=str(dotenv), VALUE=value)


@pytest.mark.parametrize("writer", _WRITERS.values(), ids=_WRITERS.keys())
@pytest.mark.parametrize("value", _VALUES)
def test_an_upserted_value_reads_back_unchanged_through_every_reader(tmp_path: Path, value: str, writer: Path) -> None:
    dotenv = tmp_path / ".env"
    _write(dotenv, value, writer)

    sourced = _bash('\nset -a; . "$DOTENV"; set +a; printf %s "$HL_TEST_VALUE"\n', DOTENV=str(dotenv), HOME="/home/x")
    loaded = _bash(
        f'\n. "{_RUNTIME_ENV_SH}"; load_dotenv_no_clobber; printf %s "$HL_TEST_VALUE"\n',
        REPO_ROOT=str(tmp_path),
        HOME="/home/x",
    )
    read_back = _bash("\nread_dotenv_var HL_TEST_VALUE\n", DOTENV=str(dotenv)).removesuffix("\n")
    parsed = preflight._parse_env_assignments(dotenv.read_text())["HL_TEST_VALUE"]

    assert (sourced, loaded, read_back, parsed) == (value, value, value, value)


def test_a_plain_value_is_written_bare(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    _write(dotenv, "https://api.anthropic.com/v1")

    assert "HL_TEST_VALUE=https://api.anthropic.com/v1\n" in dotenv.read_text()


def test_the_documented_placeholder_is_written_so_the_file_still_sources(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    _write(dotenv, "<PLEASE_FILL_IN>")

    assert "HL_TEST_VALUE='<PLEASE_FILL_IN>'\n" in dotenv.read_text()
    subprocess.run(["bash", "-n", str(dotenv)], check=True)


@pytest.mark.parametrize("writer", _WRITERS.values(), ids=_WRITERS.keys())
@pytest.mark.parametrize("value", ["it's $HOME", "it's `cmd`"])
def test_a_value_no_reader_agrees_on_is_refused_and_leaves_the_file_alone(
    tmp_path: Path, value: str, writer: Path
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("HL_TEST_VALUE=stale\n")
    with pytest.raises(subprocess.CalledProcessError) as failure:
        _bash('\nupsert_dotenv_var HL_TEST_VALUE "$VALUE"\n', writer, DOTENV=str(dotenv), VALUE=value)

    assert "cannot be written portably" in failure.value.stderr
    assert dotenv.read_text() == "HL_TEST_VALUE=stale\n"


@pytest.mark.skipif(os.geteuid() != 0, reason="only root can hand a file to another owner")
@pytest.mark.parametrize("writer", _WRITERS.values(), ids=_WRITERS.keys())
@pytest.mark.parametrize("call", ['upsert_dotenv_var HL_TEST_VALUE "new value"', "remove_dotenv_var HL_TEST_VALUE"])
def test_rewriting_as_root_keeps_the_users_ownership(tmp_path: Path, writer: Path, call: str) -> None:
    """The documented Docker flow runs setup as root on the host user's .env."""
    dotenv = tmp_path / ".env"
    dotenv.write_text("HL_TEST_VALUE=stale\n")
    os.chown(dotenv, 4242, 4343)
    dotenv.chmod(0o644)

    _bash(f"\n{call}\n", writer, DOTENV=str(dotenv))

    st = dotenv.stat()
    assert (st.st_uid, st.st_gid, st.st_mode & 0o777) == (4242, 4343, 0o600)
