# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""Round-trip tests for the .env writer in install_baremetal.sh against every .env reader."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hyperloom.inference_optimizer.cli import preflight

_ASSETS = Path(__file__).resolve().parents[1] / "assets"
_INSTALL_SH = _ASSETS / "install_baremetal.sh"
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


def _functions(*names: str) -> str:
    chunks = []
    for name in names:
        chunk = subprocess.run(
            ["sed", "-n", f"/^{name}()/,/^}}/p", str(_INSTALL_SH)], check=True, capture_output=True, text=True
        ).stdout
        assert chunk.strip(), f"{name}() not found in install_baremetal.sh"
        chunks.append(chunk)
    return "\n".join(chunks)


def _bash(body: str, **env: str) -> str:
    script = "set -euo pipefail\n" + _functions("dotenv_render_value", "upsert_dotenv_var", "read_dotenv_var") + body
    result = subprocess.run(
        ["bash", "-c", script], check=True, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", **env}
    )
    return result.stdout


def _write(dotenv: Path, value: str) -> None:
    dotenv.write_text("HYPERLOOM_RUN_MODE=baremetal\nHL_TEST_VALUE=stale\n")
    _bash('\nupsert_dotenv_var HL_TEST_VALUE "$VALUE"\n', DOTENV=str(dotenv), VALUE=value)


@pytest.mark.parametrize("value", _VALUES)
def test_an_upserted_value_reads_back_unchanged_through_every_reader(tmp_path: Path, value: str) -> None:
    dotenv = tmp_path / ".env"
    _write(dotenv, value)

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


@pytest.mark.parametrize("value", ["it's $HOME", "it's `cmd`"])
def test_a_value_no_reader_agrees_on_is_refused_and_leaves_the_file_alone(tmp_path: Path, value: str) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("HL_TEST_VALUE=stale\n")
    with pytest.raises(subprocess.CalledProcessError) as failure:
        _bash('\nupsert_dotenv_var HL_TEST_VALUE "$VALUE"\n', DOTENV=str(dotenv), VALUE=value)

    assert "cannot be written portably" in failure.value.stderr
    assert dotenv.read_text() == "HL_TEST_VALUE=stale\n"
