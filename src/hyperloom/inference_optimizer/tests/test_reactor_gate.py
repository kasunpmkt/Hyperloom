# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""The reactor gate: no LLM turn on a tick where a phase is owned by an in-flight task and nothing has changed."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from hyperloom.inference_optimizer.breakdown.recorder import phase_event
from hyperloom.inference_optimizer.breakdown.recorder.assembler import phase_event_parts
from hyperloom.inference_optimizer.session.session_binding import session_scope
from hyperloom.orchestrator.bus.message_bus import Message
from hyperloom.orchestrator.loop import reactor_gate
from hyperloom.orchestrator.loop.coordinator import Coordinator
from hyperloom.orchestrator.loop.reactor_gate import GateInputs, ReactorGate
from hyperloom.orchestrator.roles.agent_role import default_role_registry
from hyperloom.orchestrator.roles.mock_backend import MockBackend, ScriptedPlan
from hyperloom.orchestrator.state.shared_state import SharedState

_ROLES = ("orchestration", "critic")


class _Clock:
    def __init__(self) -> None:
        self.now = time.time()

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    fake = _Clock()
    monkeypatch.setattr(time, "time", fake)
    return fake


async def _kernel_delegation(tmp_path: Path, *, lease_ttl_sec: int = 7200):
    """A KERNEL phase whose ``kernel_agent`` delegation is running, with chatty mock roles."""
    session = tmp_path / "session"
    session.mkdir()
    SharedState(phase="KERNEL_AGENT", kernel_enabled=True, kernel_optimizer="geak").save(session)
    backends = {role: MockBackend(ScriptedPlan(turns=[]), name=role) for role in _ROLES}
    coord = Coordinator(
        session_dir=session,
        backends=backends,
        role_registry=default_role_registry(),
        recipe_kb=None,
        knowledge_plane=None,
    )
    task = await coord.tasks.create(kind="kernel_agent", params={}, idempotency_key="kernel_agent_c0")
    await coord.tasks.transition(task.task_id, "running")
    await coord.locks.acquire_many(
        ["benchmark_lane"], holder_id=task.task_id, task_id=task.task_id, action="kernel_agent", ttl_sec=lease_ttl_sec
    )
    return coord, backends, task


async def _tick(coord: Coordinator, clock: _Clock, *, seconds: float = 30.0) -> None:
    clock.advance(seconds)
    for role in _ROLES:
        await coord._reactor_pass(role)


def _reactor_turns(phase: str = "KERNEL_AGENT") -> dict:
    ext, _status = phase_event.assemble_phase_ext(phase_event_parts(), event=phase_event.phase_event_id(phase, 0))
    return ext["reactor_turns"]


@pytest.mark.asyncio
async def test_an_owned_phase_holds_both_roles_until_the_delegation_returns(tmp_path: Path, clock: _Clock) -> None:
    coord, backends, task = await _kernel_delegation(tmp_path)
    with session_scope(coord.session_dir):
        for _ in range(5):
            await _tick(coord, clock)
        # One turn each on entry; each turn's observation broadcast does not wake the other role.
        assert {role: len(backends[role].calls) for role in _ROLES} == {"orchestration": 1, "critic": 1}

        await coord.tasks.transition(task.task_id, "succeeded")
        await _tick(coord, clock)

        assert {role: len(backends[role].calls) for role in _ROLES} == {"orchestration": 2, "critic": 2}
        assert _reactor_turns()["orchestration"] == {
            "run": 2,
            "skipped": 4,
            "reasons": {"new_context": 1, "owner_in_flight": 4, "unowned": 1},
        }


@pytest.mark.asyncio
async def test_mail_from_the_delegation_wakes_the_role_it_is_addressed_to(tmp_path: Path, clock: _Clock) -> None:
    coord, backends, task = await _kernel_delegation(tmp_path)
    await _tick(coord, clock)
    await coord.bus.append_and_seq(
        Message.new("kernel_agent", "orchestration", "response", {"kind": "geak_progress", "status": "running"})
    )
    await _tick(coord, clock)

    assert {role: len(backends[role].calls) for role in _ROLES} == {"orchestration": 2, "critic": 1}


@pytest.mark.asyncio
async def test_a_delegation_near_its_lease_end_wakes_the_roles(tmp_path: Path, clock: _Clock) -> None:
    coord, backends, _task = await _kernel_delegation(tmp_path, lease_ttl_sec=300)
    await _tick(coord, clock)
    await _tick(coord, clock)
    assert len(backends["orchestration"].calls) == 1

    await _tick(coord, clock, seconds=300 - 60 - reactor_gate.WAKE_MARGIN_SEC + 1)

    assert len(backends["orchestration"].calls) == 2


@pytest.mark.asyncio
async def test_the_heartbeat_wakes_a_role_on_a_delegation_that_never_returns(tmp_path: Path, clock: _Clock) -> None:
    coord, backends, _task = await _kernel_delegation(tmp_path)
    await _tick(coord, clock)
    await _tick(coord, clock, seconds=reactor_gate.HEARTBEAT_SEC - 1)
    assert len(backends["orchestration"].calls) == 1

    await _tick(coord, clock, seconds=1)

    assert len(backends["orchestration"].calls) == 2


@pytest.mark.asyncio
async def test_an_unowned_phase_runs_every_turn(tmp_path: Path, clock: _Clock) -> None:
    coord, backends, _task = await _kernel_delegation(tmp_path)
    coord.shared_state.phase = "FRAMEWORK_AGENT"
    for _ in range(3):
        await _tick(coord, clock)

    assert len(backends["orchestration"].calls) == 3


def _owned(**overrides) -> GateInputs:
    fields = dict(
        phase="KERNEL_AGENT",
        macro_cycle=0,
        owner_task_id="t-1",
        closing=False,
        mail=False,
        owner_lease_left_sec=None,
        phase_budget_left_sec=None,
    )
    fields.update(overrides)
    return GateInputs(**fields)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"phase_budget_left_sec": reactor_gate.WAKE_MARGIN_SEC}, reactor_gate.RUN_BUDGET_ENDING),
        ({"phase_budget_left_sec": -5.0}, reactor_gate.RUN_BUDGET_ENDING),
        ({"owner_lease_left_sec": -5.0}, reactor_gate.RUN_LEASE_ENDING),
        ({"closing": True}, reactor_gate.RUN_CLOSING),
        ({"owner_task_id": "t-2"}, reactor_gate.RUN_NEW_CONTEXT),
        ({"macro_cycle": 1}, reactor_gate.RUN_NEW_CONTEXT),
        ({"mail": True}, reactor_gate.RUN_MAIL),
    ],
)
def test_what_wakes_a_role_sitting_out_an_owned_phase(change: dict, reason: str) -> None:
    gate = ReactorGate()
    assert gate.decide("orchestration", _owned(), now=0.0) == (True, reactor_gate.RUN_NEW_CONTEXT)
    assert gate.decide("orchestration", _owned(), now=30.0) == (False, reactor_gate.SKIP_OWNER_IN_FLIGHT)

    assert gate.decide("orchestration", _owned(**change), now=60.0) == (True, reason)
