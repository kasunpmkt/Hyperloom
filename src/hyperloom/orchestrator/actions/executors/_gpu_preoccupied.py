# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""A server that would not boot because another process already holds the GPU's memory, and who holds it."""

from __future__ import annotations

from pathlib import Path

from hyperloom.common.rocm_smi import gpu_holders

#: Error class for a boot refused because the GPU was already occupied. It says nothing about the candidate.
GPU_PREOCCUPIED = "gpu_preoccupied"

# Startup-time "the GPUs are already occupied" refusals.
_GPU_PREOCCUPIED_MARKERS: tuple[str, ...] = (
    # vLLM: "Free memory on device cuda:0 (84.11/287.98 GiB) on startup is less than desired GPU memory utilization
    # (0.95, 273.59 GiB).
    "on startup is less than desired gpu memory utilization",
    "reduce gpu memory used by other processes",
    # sglang: "Not enough memory. Please try to increase --mem-fraction-static."
    "not enough memory. please try to increase --mem-fraction-static",
)


def is_insufficient_gpu_memory(*texts: str) -> bool:
    """True when a server refused to boot because VRAM was already occupied."""
    blob = "\n".join(t for t in texts if t).lower()
    return any(m in blob for m in _GPU_PREOCCUPIED_MARKERS)


def _process_name(pid: int, reported: str) -> str:
    if reported and reported != "unknown":
        return reported
    try:
        return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip() or "unknown"
    except OSError:
        return "unknown"


def gpu_holders_summary() -> str:
    """One line naming the processes holding GPU memory, or ``""`` when none can be read."""
    return ", ".join(
        f"pid {h.pid} ({_process_name(h.pid, h.name)}, {h.vram_mib / 1024:.1f} GiB)" for h in gpu_holders() or []
    )


__all__ = ["GPU_PREOCCUPIED", "gpu_holders_summary", "is_insufficient_gpu_memory"]
