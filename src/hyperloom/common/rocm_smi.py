# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""Shared rocm-smi readers: per-GPU VRAM, and the processes holding it."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, NamedTuple

_TIMEOUT_SEC = 20.0


class GpuVram(NamedTuple):
    """Per-GPU VRAM usage in MiB."""

    used_mib: float
    total_mib: float


class GpuHolder(NamedTuple):
    """A process holding GPU memory."""

    pid: int
    name: str
    vram_mib: float


def _rocm_smi_json(*args: str) -> dict[str, Any] | None:
    """Run ``rocm-smi <args> --json`` and return its object, or None when it cannot be read."""
    if not shutil.which("rocm-smi"):
        return None
    try:
        proc = subprocess.run(
            ["rocm-smi", *args, "--json"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SEC,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def gpu_holders() -> list[GpuHolder] | None:
    """Return the processes holding GPU memory via rocm-smi, or None when it cannot be read."""
    data = _rocm_smi_json("--showpids")
    if data is None:
        return None
    holders: list[GpuHolder] = []
    # Shape: {"system": {"PID<pid>": "name, #gpus, vram_bytes, sdma, cu_occupancy"}}.
    for fields in data.values():
        if not isinstance(fields, dict):
            continue
        for key, val in fields.items():
            parts = [part.strip() for part in str(val).split(",")]
            try:
                holders.append(GpuHolder(int(key.removeprefix("PID")), parts[0], float(parts[2]) / 1024**2))
            except (IndexError, ValueError):
                continue
    return holders


def gpu_vram_usage() -> list[GpuVram] | None:
    """Return per-GPU VRAM usage via rocm-smi, or None when it cannot be read."""
    data = _rocm_smi_json("--showmeminfo", "vram")
    if data is None:
        return None

    result: list[GpuVram] = []
    for fields in data.values():
        if not isinstance(fields, dict):
            continue
        raw: dict[str, Any] = {}
        for key, val in fields.items():
            kl = key.lower()
            if "vram" not in kl:
                continue
            # "VRAM Total Used Memory (B)" matches both, so used must win.
            if "used" in kl:
                raw["used"] = val
            elif "total" in kl:
                raw["total"] = val
        if not raw:
            continue
        try:
            usage = GpuVram(float(raw["used"]) / 1024**2, float(raw["total"]) / 1024**2)
        except (KeyError, TypeError, ValueError):
            return None
        if usage.total_mib <= 0.0:
            return None
        result.append(usage)
    return result or None


__all__ = ["GpuHolder", "GpuVram", "gpu_holders", "gpu_vram_usage"]
