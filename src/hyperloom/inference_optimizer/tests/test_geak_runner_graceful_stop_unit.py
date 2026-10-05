# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT
"""Behavioral tests for geak_runner's graceful-stop / flush contract."""

from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

_RUNNER_PY = (
    Path(__file__).resolve().parents[4]
    / "src"
    / "hyperloom"
    / "agents"
    / "kernel"
    / "tools"
    / "backends"
    / "geak_runner.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("geak_runner", _RUNNER_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


psr = _load_module()


def _write_fake_runner(tmp_path: Path, body: str) -> Path:
    """A fake run_e2e.py: argv = <handoff> <result>. Body decides behavior."""
    f = tmp_path / "fake_run_e2e.py"
    f.write_text(textwrap.dedent(body), encoding="utf-8")
    return f


def _handoff() -> dict:
    return {
        "schema_version": 1,
        "model_path": "/m",
        "framework": "vllm",
        "tp": 1,
        "workload": {"isl": 8, "osl": 8, "conc": 1},
        "exp_root": "/tmp/x",
    }


def test_resolve_runner_falls_back_to_cache_dir(tmp_path, monkeypatch):
    geak_root = tmp_path / "cache" / "GEAK"
    runner = geak_root / "interface" / "run_e2e.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("# fake\n", encoding="utf-8")
    monkeypatch.delenv("GEAK_E2E_RUNNER", raising=False)
    monkeypatch.delenv("GEAK_ROOT", raising=False)
    monkeypatch.setenv("HYPERLOOM_CACHE_DIR", str(tmp_path / "cache"))

    assert psr._resolve_runner() == str(runner)


def test_resolve_runner_prefers_newest_pinned_geak_in_cache(tmp_path, monkeypatch):
    import os as _os

    cache = tmp_path / "cache"
    old_runner = cache / "GEAK@1111111" / "interface" / "run_e2e.py"
    new_runner = cache / "GEAK@2222222" / "interface" / "run_e2e.py"
    for r in (old_runner, new_runner):
        r.parent.mkdir(parents=True)
        r.write_text("# fake\n", encoding="utf-8")
    _os.utime(old_runner.parent.parent, (1_000_000, 1_000_000))
    _os.utime(new_runner.parent.parent, (2_000_000, 2_000_000))
    monkeypatch.delenv("GEAK_E2E_RUNNER", raising=False)
    monkeypatch.delenv("GEAK_ROOT", raising=False)
    monkeypatch.setenv("HYPERLOOM_CACHE_DIR", str(cache))

    assert psr._resolve_runner() == str(new_runner)


def test_inner_timeout_is_reduced_by_flush_grace(tmp_path, monkeypatch):
    """run_e2e must receive GEAK_E2E_TIMEOUT_S = timeout_s - flush_grace."""
    runner = _write_fake_runner(
        tmp_path,
        """
        import json, os, sys
        # Echo the inner budget we were handed so the test can assert on it.
        result = {"status": "ok", "throughput_speedup": 1.16,
                  "final_throughput_tok_s": 535.4,
                  "inner_budget": os.environ.get("GEAK_E2E_TIMEOUT_S")}
        with open(sys.argv[2], "w") as fh:
            json.dump(result, fh)
        sys.exit(0)
    """,
    )
    monkeypatch.setenv("GEAK_E2E_RUNNER", str(runner))
    monkeypatch.setenv("GEAK_FLUSH_GRACE_S", "180")

    out = psr.call_geak(_handoff(), tmp_path / "out", timeout_s=600)

    assert out["status"] == "ok"
    assert out["inner_budget"] == "420"
    assert out["returncode"] == 0


def test_call_geak_uses_current_python_when_path_is_polluted(tmp_path, monkeypatch):
    """GEAK must run in Hyperloom's Python, not a framework venv from PATH."""
    fake_vllm_bin = tmp_path / "vllm-venv" / "bin"
    fake_vllm_bin.mkdir(parents=True)
    fake_python = fake_vllm_bin / "python3"
    fake_python.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    fake_python.chmod(0o755)

    runner = _write_fake_runner(
        tmp_path,
        """
        import json, sys
        with open(sys.argv[2], "w") as fh:
            json.dump({"status": "ok", "python": sys.executable}, fh)
        sys.exit(0)
    """,
    )
    monkeypatch.setenv("GEAK_E2E_RUNNER", str(runner))
    monkeypatch.setenv(
        "PATH",
        str(fake_vllm_bin) + os.pathsep + os.environ.get("PATH", ""),
    )

    out = psr.call_geak(_handoff(), tmp_path / "out", timeout_s=600)

    assert out["status"] == "ok"
    assert out["python"] == sys.executable


def test_sigterm_grace_lets_child_flush_result(tmp_path, monkeypatch):
    """On the hard-timeout path, SIGTERM gives the child time to flush; the flushed result.json is then read back (not discarded as no_result_json)."""
    runner = _write_fake_runner(
        tmp_path,
        """
        import json, signal, sys, time
        handoff, result_path = sys.argv[1], sys.argv[2]
        def _flush(signum, frame):
            with open(result_path, "w") as fh:
                json.dump({"status": "ok", "throughput_speedup": 1.16,
                           "flushed_on_term": True}, fh)
            sys.exit(0)
        signal.signal(signal.SIGTERM, _flush)
        # Outlive the outer hard timeout so the SIGTERM path triggers.
        time.sleep(60)
    """,
    )
    monkeypatch.setenv("GEAK_E2E_RUNNER", str(runner))
    monkeypatch.setenv("GEAK_FLUSH_GRACE_S", "5")

    out = psr.call_geak(_handoff(), tmp_path / "out", timeout_s=2)

    assert out["status"] == "ok"
    assert out["flushed_on_term"] is True
    rp = json.loads((tmp_path / "out" / "result.json").read_text())
    assert rp["flushed_on_term"] is True


def test_sigkill_escalation_when_child_ignores_sigterm(tmp_path, monkeypatch):
    """A child that ignores SIGTERM and never flushes is SIGKILLed; the runner reports a no-result error rather than hanging forever."""
    runner = _write_fake_runner(
        tmp_path,
        """
        import signal, time
        signal.signal(signal.SIGTERM, signal.SIG_IGN)  # refuse to die politely
        time.sleep(120)
    """,
    )
    monkeypatch.setenv("GEAK_E2E_RUNNER", str(runner))
    monkeypatch.setenv("GEAK_FLUSH_GRACE_S", "2")

    out = psr.call_geak(_handoff(), tmp_path / "out", timeout_s=2)

    assert out["status"] == "error"
    assert "no parseable result.json" in out["error"]
    assert out["returncode"] == -1
    assert not (tmp_path / "out" / "result.json").is_file()


def test_geak_output_survives_a_sigkill_in_the_output_dir(tmp_path, monkeypatch):
    """GEAK's own output is the only record of why it stopped before Finalize; it must outlive a killed run."""
    runner = _write_fake_runner(
        tmp_path,
        """
        import signal, sys, time
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        print("workflow: entering Capture", flush=True)
        print("Error: capture benchmark ran 0 times", file=sys.stderr, flush=True)
        time.sleep(120)
    """,
    )
    monkeypatch.setenv("GEAK_E2E_RUNNER", str(runner))
    monkeypatch.setenv("GEAK_FLUSH_GRACE_S", "2")
    out_dir = tmp_path / "out"

    out = psr.call_geak(_handoff(), out_dir, timeout_s=2)

    assert out["returncode"] == -1
    assert (out_dir / "run_e2e.stdout.log").read_text() == "workflow: entering Capture\n"
    assert (out_dir / "run_e2e.stderr.log").read_text() == "Error: capture benchmark ran 0 times\n"
    assert out["stdout_log"] == str(out_dir / "run_e2e.stdout.log")
    assert out["stderr_tail"] == "Error: capture benchmark ran 0 times\n"


def test_the_runner_summary_says_how_geak_ended(tmp_path, monkeypatch, capsys):
    """The kernel phase logs only this line, so it carries the exit code, the stop cause and where the logs are."""
    runner = _write_fake_runner(
        tmp_path,
        """
        import sys
        print("Traceback: workflow crashed", file=sys.stderr)
        sys.exit(3)
    """,
    )
    monkeypatch.setenv("GEAK_E2E_RUNNER", str(runner))
    handoff_path = tmp_path / "handoff.json"
    handoff_path.write_text(json.dumps(_handoff()), encoding="utf-8")
    out_dir = tmp_path / "out"

    previous = signal.getsignal(signal.SIGTERM)  # _main installs its own handler
    try:
        assert psr._main([str(handoff_path), str(out_dir), "--timeout-s", "60"]) == 1
    finally:
        signal.signal(signal.SIGTERM, previous)

    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["status"] == "error"
    assert summary["returncode"] == 3
    assert summary["stopped_by"] == ""
    assert summary["stderr_log"] == str(out_dir / "run_e2e.stderr.log")
    assert "Traceback: workflow crashed" in (out_dir / "run_e2e.stderr.log").read_text()


def _alive(pid: int) -> bool:
    """Whether ``pid`` is a live process; a zombie nobody reaped yet counts as gone."""
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, ProcessLookupError, IndexError):
        return False
    return state != "Z"


def _wait_until_gone(pids: list[int], *, timeout_s: float) -> list[int]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        alive = [pid for pid in pids if _alive(pid)]
        if not alive:
            return []
        time.sleep(0.2)
    return [pid for pid in pids if _alive(pid)]


def _wait_for_file(path: Path, *, timeout_s: float = 20.0) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.is_file() and path.read_text().strip():
            return path.read_text().strip()
        time.sleep(0.1)
    raise AssertionError(f"{path} never appeared")


def _geak_tree_stub(tmp_path: Path, monkeypatch) -> Path:
    """A run_e2e that starts a long-lived child in its own process group, as run_e2e starts the Claude CLIs."""
    runner = _write_fake_runner(
        tmp_path,
        f"""
        import subprocess, sys, time
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
        open({str(tmp_path / "tree.pids")!r}, "w").write(f"{{__import__('os').getpid()}} {{child.pid}}")
        time.sleep(300)
    """,
    )
    monkeypatch.setenv("GEAK_E2E_RUNNER", str(runner))
    monkeypatch.setenv("GEAK_FLUSH_GRACE_S", "5")
    handoff = tmp_path / "handoff.json"
    handoff.write_text(json.dumps(_handoff()), encoding="utf-8")
    return handoff


def test_an_optimizer_killed_outright_leaves_no_geak_process_behind(tmp_path, monkeypatch):
    """SIGKILL, or a native signal handler, gives the optimizer no chance to stop GEAK; the runner must notice."""
    handoff = _geak_tree_stub(tmp_path, monkeypatch)
    optimizer = subprocess.Popen(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                f"""
                import subprocess, sys, time
                runner = subprocess.Popen(
                    [sys.executable, {str(_RUNNER_PY)!r}, {str(handoff)!r}, {str(tmp_path / "out")!r}, "--timeout-s", "600"],
                    start_new_session=True,
                )
                open({str(tmp_path / "runner.pid")!r}, "w").write(str(runner.pid))
                time.sleep(300)
                """
            ),
        ]
    )
    runner_pid = int(_wait_for_file(tmp_path / "runner.pid"))
    tree = [int(pid) for pid in _wait_for_file(tmp_path / "tree.pids").split()]

    optimizer.kill()
    optimizer.wait()

    assert _wait_until_gone([runner_pid, *tree], timeout_s=30) == []


def test_a_sigterm_to_the_runner_stops_run_e2e_and_its_children(tmp_path, monkeypatch):
    handoff = _geak_tree_stub(tmp_path, monkeypatch)
    runner = subprocess.Popen(
        [sys.executable, str(_RUNNER_PY), str(handoff), str(tmp_path / "out"), "--timeout-s", "600"],
        start_new_session=True,
        stdout=subprocess.PIPE,
    )
    tree = [int(pid) for pid in _wait_for_file(tmp_path / "tree.pids").split()]

    runner.send_signal(signal.SIGTERM)
    runner.wait(timeout=30)

    assert _wait_until_gone(tree, timeout_s=10) == []
    assert json.loads((runner.stdout.read() or b"{}").decode())["status"] == "error"


def test_processes_geak_left_in_its_output_dir_are_reaped_and_bystanders_are_not(tmp_path, monkeypatch):
    """GEAK's teardown can miss a re-parented vLLM EngineCore; the runner owns the output dir and clears it."""
    out = tmp_path / "out"
    eval_dir = out / "e2e_cycle0"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    pids_file = tmp_path / "leftover.pids"
    runner = _write_fake_runner(
        tmp_path,
        f"""
        import json, os, subprocess, sys
        os.makedirs({str(eval_dir)!r}, exist_ok=True)
        sleeper = [sys.executable, "-c", "import time; time.sleep(300)"]
        # Detached like a setsid'd server whose API process has gone: neither stays a descendant of run_e2e. Servers
        # log to files, so neither holds run_e2e's pipes.
        quiet = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        in_dir = subprocess.Popen(sleeper, cwd={str(eval_dir)!r}, **quiet)
        pid_file_env = dict(os.environ, MAGPIE_SERVER_PID_FILE={str(eval_dir / "server.pid")!r})
        by_pid_file = subprocess.Popen(sleeper, cwd={str(elsewhere)!r}, env=pid_file_env, **quiet)
        open({str(pids_file)!r}, "w").write(f"{{in_dir.pid}} {{by_pid_file.pid}}")
        with open(sys.argv[2], "w") as fh:
            json.dump({{"status": "ok", "throughput_speedup": 1.2}}, fh)
    """,
    )
    monkeypatch.setenv("GEAK_E2E_RUNNER", str(runner))
    bystander = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"], cwd=elsewhere)
    try:
        out_result = psr.call_geak(_handoff(), out, timeout_s=60)
        leftovers = [int(pid) for pid in pids_file.read_text().split()]

        assert out_result["status"] == "ok"
        assert sorted(out_result["reaped_pids"]) == sorted(leftovers)
        assert _wait_until_gone(leftovers, timeout_s=5) == []
        assert _alive(bystander.pid)
    finally:
        bystander.kill()
        bystander.wait()


def test_a_clean_geak_run_reaps_nothing(tmp_path, monkeypatch):
    runner = _write_fake_runner(
        tmp_path,
        """
        import json, sys
        with open(sys.argv[2], "w") as fh:
            json.dump({"status": "ok"}, fh)
    """,
    )
    monkeypatch.setenv("GEAK_E2E_RUNNER", str(runner))

    assert "reaped_pids" not in psr.call_geak(_handoff(), tmp_path / "out", timeout_s=60)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
