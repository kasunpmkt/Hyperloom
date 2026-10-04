# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT
"""Run a requested ``trace_analyze`` the way a run does: queued by the request, started by the dispatcher pump."""

from __future__ import annotations

import asyncio
from typing import Any


def register_trace_analyze_executor(coord: Any) -> None:
    """Register the executor the CLI wires for ``trace_analyze``."""
    coord.sub.register_executor("trace_analyze", lambda ctx: coord._run_trace_analyze_task(ctx))


async def wait_for_dispatched_trace_analyze(coord: Any) -> None:
    """Wait for the ``trace_analyze`` tasks the pump started to land."""
    await asyncio.gather(*(a.atask for a in coord.dispatcher._inflight_actions.values() if a.kind == "trace_analyze"))


async def run_dispatched_trace_analyze(coord: Any) -> None:
    """Let the pump start the queued ``trace_analyze`` task and wait for it to land."""
    register_trace_analyze_executor(coord)
    await coord._pump_dispatcher_once()
    await wait_for_dispatched_trace_analyze(coord)
