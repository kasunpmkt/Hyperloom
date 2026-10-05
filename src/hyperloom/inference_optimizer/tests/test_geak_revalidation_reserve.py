# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT
"""GEAK's allowance leaves room for the re-validation round that makes its result count."""

from __future__ import annotations

from pathlib import Path

import pytest

from hyperloom.common.deadline import Deadline
from hyperloom.orchestrator.loop.coordinator import Coordinator
from hyperloom.orchestrator.phases import machine_state as _phase_state
from hyperloom.orchestrator.state.shared_state import SharedState

# The 2 Oct gpt-oss-120b session: a cold baseline pass and its hot second pass.
_COLD_SEC = 934.67
_HOT_SEC = 280.79
_MARGIN_SEC = 300


def _coordinator(tmp_path: Path, *, remaining_sec: float, double_run: bool = True) -> Coordinator:
    coord = Coordinator.__new__(Coordinator)
    coord.session_dir = tmp_path
    coord._run_deadline = Deadline.after(remaining_sec)
    coord._phase_budget_pct = {}
    coord.shared_state = SharedState(
        baseline_tput=1497.0,
        model_path="/models/m",
        gpu_type="mi300x",
        max_minutes=420,
        baseline_runtime_sec=_COLD_SEC,
        baseline_warm_runtime_sec=_HOT_SEC,
        baseline_double_run=double_run,
        phase_history=[{"phase": "KERNEL_AGENT", "evidence": {}}],
    )
    return coord


@pytest.fixture(autouse=True)
def _default_margins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEAK_BUDGET_MARGIN_S", raising=False)
    monkeypatch.delenv("GEAK_MIN_RUN_S", raising=False)


@pytest.mark.parametrize("double_run", [True, False])
def test_geak_that_uses_its_whole_allowance_leaves_its_rebench_and_the_closing_reserve(
    tmp_path: Path, double_run: bool
) -> None:
    remaining_sec = 5080 + _MARGIN_SEC + 120
    coord = _coordinator(tmp_path, remaining_sec=remaining_sec, double_run=double_run)
    state = coord.shared_state

    timeouts = coord.phase_kernel._geak_timeouts()

    rebench_sec = _phase_state.baseline_round_cost_sec(state, double_run=double_run)
    assert rebench_sec == pytest.approx(_COLD_SEC + _HOT_SEC if double_run else _COLD_SEC)
    assert timeouts.budget_known
    assert timeouts.revalidation_reserve_sec == round(rebench_sec)
    assert timeouts.runner_timeout == timeouts.kill_timeout - _MARGIN_SEC
    # Even a GEAK that runs until it is killed hands back enough for the explore admission to run its rebench.
    left_after_geak = remaining_sec - timeouts.kill_timeout - state.closing_reserve_sec()
    assert left_after_geak >= rebench_sec


def test_an_unbounded_run_reserves_nothing(tmp_path: Path) -> None:
    coord = _coordinator(tmp_path, remaining_sec=0)
    coord._run_deadline = None

    timeouts = coord.phase_kernel._geak_timeouts()

    assert not timeouts.budget_known
    assert timeouts.revalidation_reserve_sec == 0


@pytest.mark.asyncio
async def test_a_budget_that_fits_geak_but_not_its_rebench_skips_geak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = tmp_path / "runner-started"
    runner = tmp_path / "geak_runner.py"
    runner.write_text(f"open({str(started)!r}, 'w').close()\n", encoding="utf-8")
    monkeypatch.setattr(
        "hyperloom.orchestrator.actions.executors._kernel_agent_tool._kernel_agent_tool_path",
        lambda _name: runner,
    )
    # Without the reserve this leaves GEAK about 1200s, above GEAK_MIN_RUN_S.
    coord = _coordinator(tmp_path, remaining_sec=1200 + _MARGIN_SEC + 120)
    coord.phase_kernel._record_geak_kernel_journey = lambda _result: None

    await coord._run_geak_kernel_phase(from_phase="FRAMEWORK_AGENT")

    state = coord.shared_state
    assert not started.exists()
    assert state.geak_result["error_class"] == "insufficient_budget"
    assert "re-validate" in state.geak_result["error"]
    budget = state.phase_history[-1]["evidence"]["geak_budget"]
    assert budget["revalidation_reserve_s"] == round(_COLD_SEC + _HOT_SEC)
    assert budget["runner_timeout_s"] < 600
