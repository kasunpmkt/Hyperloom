# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT
"""A requested TraceLens analysis runs as a background task: the tick that received the request goes on."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from hyperloom.inference_optimizer.protocol.intent import Intent, IntentType
from hyperloom.orchestrator.kernel import request_handlers as krh
from hyperloom.orchestrator.roles import MockBackend, ScriptedPlan
from hyperloom.orchestrator.loop.coordinator import Coordinator

from ._trace_analyze_task import register_trace_analyze_executor, wait_for_dispatched_trace_analyze

# Long enough that a blocked call would fail it, short enough to keep the suite fast.
_PROMPT_SEC = 5.0


class _SlowAnalysis:
    """A TraceLens stand-in that runs until the test lets it finish."""

    def __init__(self, candidates_path: Path) -> None:
        self.release = asyncio.Event()
        self.started = asyncio.Event()
        self.calls = 0
        self._candidates_path = candidates_path

    async def __call__(self, payload: dict, *, session_dir: Path) -> dict:
        self.calls += 1
        self.started.set()
        # Bounded, so a request that blocks on it fails the test instead of hanging it.
        await asyncio.wait_for(self.release.wait(), 2 * _PROMPT_SEC)
        return {"status": "ok", "candidates_path": str(self._candidates_path), "hot_kernels": []}


def _silent_backends() -> dict[str, MockBackend]:
    silent = ScriptedPlan(
        turns=[], default_intent=Intent(type=IntentType.SEND_MESSAGE, payload={"topic": "heartbeat", "body_md": "ok"})
    )
    return {n: MockBackend(silent, name=n) for n in ("orchestration", "critic")}


def _request(trace_input: str) -> Intent:
    return Intent(
        type=IntentType.REQUEST,
        payload={"target_agent": "kernel_agent", "kind": "trace_analyze", "params": {"trace_input": trace_input}},
    )


@pytest.fixture
async def coord(session_dir: Path):
    c = Coordinator(session_dir, backends=_silent_backends())
    register_trace_analyze_executor(c)
    try:
        yield c
    finally:
        await c.stop()


@pytest.mark.asyncio
async def test_the_request_and_the_pump_return_while_the_analysis_runs(coord: Coordinator, tmp_path: Path) -> None:
    candidates = tmp_path / "kernel_candidates.json"
    candidates.write_text("{}", encoding="utf-8")
    analysis = _SlowAnalysis(candidates)

    with patch.dict(krh.KERNEL_REQUEST_HANDLERS, {"trace_analyze": analysis}):
        await asyncio.wait_for(coord._handle_intent("orchestration", _request("/t/trace.json.gz")), _PROMPT_SEC)
        [queued] = await coord.bus.tail(topic="response", to_agent="orchestration")
        assert queued.payload["status"] == "queued"
        request_id = queued.payload["in_reply_to"]

        await asyncio.wait_for(coord._pump_dispatcher_once(), _PROMPT_SEC)
        await asyncio.wait_for(analysis.started.wait(), _PROMPT_SEC)
        assert not coord.shared_state.last_trace_analyze, "nothing is recorded before the analysis lands"

        analysis.release.set()
        await wait_for_dispatched_trace_analyze(coord)

    done = (await coord.bus.tail(topic="response", to_agent="orchestration"))[0]
    assert done.payload["in_reply_to"] == request_id
    assert done.payload["status"] == "ok"
    assert coord.shared_state.last_trace_analyze["trace_input"] == "/t/trace.json.gz"
    steps = [e["status"] for e in coord.shared_state.lifecycle if e["step"] == "trace_analyze"]
    assert steps == ["START", "END"]


@pytest.mark.asyncio
async def test_a_repeat_request_for_a_trace_in_analysis_joins_that_run(coord: Coordinator, tmp_path: Path) -> None:
    candidates = tmp_path / "kernel_candidates.json"
    candidates.write_text("{}", encoding="utf-8")
    analysis = _SlowAnalysis(candidates)

    with patch.dict(krh.KERNEL_REQUEST_HANDLERS, {"trace_analyze": analysis}):
        await coord._handle_intent("orchestration", _request("/t/trace.json.gz"))
        await coord._pump_dispatcher_once()
        await asyncio.wait_for(analysis.started.wait(), _PROMPT_SEC)
        await coord._handle_intent("orchestration", _request("/t/trace.json.gz"))

        replies = await coord.bus.tail(topic="response", to_agent="orchestration")
        assert [r.payload["status"] for r in replies] == ["queued", "queued"]
        assert replies[0].payload["result"]["task_id"] == replies[1].payload["result"]["task_id"]

        analysis.release.set()
        await wait_for_dispatched_trace_analyze(coord)

    assert analysis.calls == 1
