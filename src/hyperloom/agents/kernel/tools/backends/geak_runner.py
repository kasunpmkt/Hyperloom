#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""GEAK e2e optimizer submission (whole-pipeline; GEAK@GEAK main)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

#: How often the runner checks whether it was told to stop or lost the optimizer that started it.
STOP_POLL_S = 2.0
#: Seconds a leftover process gets between SIGTERM and SIGKILL.
REAP_GRACE_S = 10.0
_PID_FILE_VAR = b"MAGPIE_SERVER_PID_FILE="


def _is_under(path: str, root: str) -> bool:
    return path == root or path.startswith(root + os.sep)


def _owned_by(pid_dir: Path, root: str) -> bool:
    """Whether the process works in ``root`` or serves from a Magpie pid file under it."""
    try:
        if _is_under(os.readlink(pid_dir / "cwd"), root):
            return True
        environ = (pid_dir / "environ").read_bytes()
    except OSError:
        return False
    for entry in environ.split(b"\0"):
        if entry.startswith(_PID_FILE_VAR):
            return _is_under(os.path.realpath(entry[len(_PID_FILE_VAR) :].decode(errors="replace")), root)
    return False


def _alive(pid: int) -> bool:
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (OSError, IndexError):
        return False
    return state != "Z"


def reap_leftovers(output_dir: Path, *, grace_s: float = REAP_GRACE_S) -> list[int]:
    """Stop every process GEAK left running in ``output_dir``; return their pids.

    GEAK's own teardown misses a vLLM ``EngineCore`` whose API server exited first: it is re-parented to pid 1 and
    leaves its process group and parent chain, so nothing above it can reach it (docs/backlog/geak-backlog.md GK-01),
    and it holds the GPU for every later measurement. Ownership is by location, never by name: whatever still works in
    the delegation's output dir, or serves from a pid file under it, was started for this delegation.
    """
    root = os.path.realpath(output_dir)
    me = os.getpid()
    pids = [
        int(entry.name)
        for entry in Path("/proc").iterdir()
        if entry.name.isdigit() and int(entry.name) != me and _owned_by(entry, root)
    ]
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + grace_s
        while any(_alive(pid) for pid in pids) and time.monotonic() < deadline:
            time.sleep(0.2)
        if not any(_alive(pid) for pid in pids):
            break
    return pids


def _resolve_runner() -> str:
    """Resolve run_e2e.py from $GEAK_E2E_RUNNER / $GEAK_ROOT (GEAK@GEAK)."""
    runner = os.environ.get("GEAK_E2E_RUNNER", "").strip()
    if runner and Path(runner).is_file():
        return runner
    roots: list[str] = []
    root = os.environ.get("GEAK_ROOT", "").strip()
    if root:
        roots.append(root)
    cache_dir = os.environ.get("HYPERLOOM_CACHE_DIR", "").strip()
    if cache_dir:
        # install.sh clones GEAK per revision as <cache>/GEAK@<sha>; prefer the newest such checkout, then the bare
        # dir.
        pinned = sorted(
            (p for p in Path(cache_dir).glob("GEAK@*") if p.is_dir()),
            key=lambda p: p.stat().st_mtime if p.exists() else 0.0,
            reverse=True,
        )
        roots.extend(str(p) for p in pinned)
        roots.append(str(Path(cache_dir) / "GEAK"))
    for root in dict.fromkeys(roots):
        cand = Path(root) / "interface" / "run_e2e.py"
        if cand.is_file():
            return str(cand)
    raise FileNotFoundError(
        "e2e runner not found. Set GEAK_E2E_RUNNER to "
        "<GEAK checkout>/interface/run_e2e.py (the installer exports it), "
        "or set GEAK_ROOT/HYPERLOOM_CACHE_DIR."
    )


def call_geak(
    handoff: dict,
    output_dir: Path,
    *,
    timeout_s: int = 43200,
    python_bin: str = "",
    stop: threading.Event | None = None,
) -> dict:
    """Run GEAK e2e once and return the parsed result.json (+ run metadata).

    run_e2e runs in a session of its own, so nothing aimed at this process reaches it or the Claude CLIs it starts.
    The runner therefore takes its whole process group down -- SIGTERM, the flush grace, then SIGKILL -- on the
    timeout, when ``stop`` is set, and when the process that started the runner is gone: an optimizer killed outright
    (SIGKILL, or a native signal handler that never returns to Python) has no chance to tell it.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = output_dir / "handoff.json"
    result_path = output_dir / "result.json"
    handoff_path.write_text(json.dumps(handoff, indent=2), encoding="utf-8")

    runner = _resolve_runner()
    py = python_bin or sys.executable
    cmd = [py, runner, str(handoff_path), str(result_path)]

    env = dict(os.environ)
    # ``timeout_s`` is authoritative: run_e2e.py reads GEAK_E2E_TIMEOUT_S to self-stop before the outer subprocess
    # kill.
    grace_raw = os.environ.get("GEAK_FLUSH_GRACE_S", "").strip()
    flush_grace = int(grace_raw) if grace_raw.isdigit() and int(grace_raw) > 0 else 180
    inner_timeout = max(60, timeout_s - flush_grace)
    env["GEAK_E2E_TIMEOUT_S"] = str(inner_timeout)  # run_e2e's anyio budget

    started = time.time()
    # start_new_session=True -> run_e2e + its vllm/node children share a process group we can signal as a unit
    # (prevents leaked-server orphans).
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        start_new_session=True,
    )

    def _killpg(sig: int) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            # Process already exited; nothing to signal.
            pass

    parent = os.getppid()
    deadline = time.monotonic() + timeout_s
    stopped_by = ""
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=max(0.0, min(STOP_POLL_S, deadline - time.monotonic())))
            returncode = proc.returncode
            break
        except subprocess.TimeoutExpired:
            if stop is not None and stop.is_set():
                stopped_by = "sigterm"
            elif os.getppid() != parent:
                stopped_by = "parent_exited"
            elif time.monotonic() >= deadline:
                stopped_by = "timeout"
            else:
                continue
        # SIGTERM lets run_e2e flush result.json, then escalate to SIGKILL.
        _killpg(signal.SIGTERM)
        try:
            stdout, stderr = proc.communicate(timeout=flush_grace)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            _killpg(signal.SIGKILL)
            stdout, stderr = proc.communicate()
            returncode = -1
        break
    reaped = reap_leftovers(output_dir)
    stdout_tail = (stdout or "")[-4000:]
    stderr_tail = (stderr or "")[-4000:]

    result: dict = {}
    if result_path.is_file():
        try:
            _parsed = json.loads(result_path.read_text(encoding="utf-8"))
            if isinstance(_parsed, dict):
                result = _parsed
        except json.JSONDecodeError:
            pass
    if not result:
        result = {
            "status": "error",
            "error": f"no parseable result.json (rc={returncode})",
        }
    result.update(
        {
            "returncode": returncode,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "elapsed_s": round(time.time() - started, 2),
            "handoff_path": str(handoff_path),
            "result_path": str(result_path),
        }
    )
    if stopped_by:
        result["stopped_by"] = stopped_by
    if reaped:
        result["reaped_pids"] = reaped
    return result


def _main(argv: list[str]) -> int:
    """CLI: geak_runner.py <handoff.json> <output_dir> [--timeout-s N]."""
    import argparse

    ap = argparse.ArgumentParser(description="Run GEAK e2e once.")
    ap.add_argument("handoff_json")
    ap.add_argument("output_dir")
    # Explicit --timeout-s wins; else fall back to GEAK_E2E_TIMEOUT_S, else 12h.
    ap.add_argument("--timeout-s", type=int, default=None)
    args = ap.parse_args(argv)

    if args.timeout_s is not None:
        timeout_s = args.timeout_s
    else:
        timeout_s = int(os.environ.get("GEAK_E2E_TIMEOUT_S", "43200"))  # 12h

    handoff = json.loads(Path(args.handoff_json).read_text(encoding="utf-8"))
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda _signum, _frame: stop.set())
    out = call_geak(handoff, Path(args.output_dir), timeout_s=timeout_s, stop=stop)
    print(
        json.dumps(
            {
                "status": out.get("status"),
                "speedup": out.get("throughput_speedup"),
                "result_path": out.get("result_path"),
                "reaped_pids": out.get("reaped_pids", []),
            }
        )
    )
    return 0 if out.get("status") not in ("error", None) else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
