# SPDX-FileCopyrightText: 2026 Advanced Micro Devices, Inc.
# SPDX-License-Identifier: MIT

"""Whether a reactor role takes its LLM turn this tick.

A turn is a fresh agent session with the whole composed prompt, so on a phase owned by one in-flight task -- KERNEL
under its ``kernel_agent`` delegation -- every turn until that task returns can only re-read the same state and hold.
The gate sits a role out while that is all a turn could do, and lets it run as soon as something it could act on
appears: the owner leaves flight, the phase or its owner changes, mail other than the other role's routine
observations arrives, the owner's lease or the phase budget nears its end, the run starts closing, or a heartbeat
falls due so a stuck delegation is still looked at.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The longest a role sits out an owned phase without a turn.
HEARTBEAT_SEC: float = 600.0
#: How close to the end of the owner's lease or the phase budget a role is woken, so it can act before either runs out.
WAKE_MARGIN_SEC: float = 120.0

RUN_UNOWNED = "unowned"
RUN_CLOSING = "closing"
RUN_NEW_CONTEXT = "new_context"
RUN_MAIL = "mail"
RUN_LEASE_ENDING = "lease_ending"
RUN_BUDGET_ENDING = "budget_ending"
RUN_HEARTBEAT = "heartbeat"
SKIP_OWNER_IN_FLIGHT = "owner_in_flight"


@dataclass(frozen=True)
class GateInputs:
    """What the gate reads about one role on one tick.

    Attributes:
        phase: The current phase.
        macro_cycle: The current macro cycle.
        owner_task_id: The in-flight task that owns the phase, or ``""`` when the phase is not owned.
        closing: Whether the run is in its closing phase.
        mail: Whether the role has unread mail it should react to.
        owner_lease_left_sec: Seconds until the owner's earliest lease expires, if it holds one.
        phase_budget_left_sec: Seconds left in the phase budget, if the phase has one.
    """

    phase: str
    macro_cycle: int
    owner_task_id: str
    closing: bool
    mail: bool
    owner_lease_left_sec: float | None
    phase_budget_left_sec: float | None

    @property
    def context(self) -> tuple[str, int, str]:
        """The phase, cycle and owner a role's last turn saw; a change is new to the role."""
        return (self.phase, self.macro_cycle, self.owner_task_id)


class ReactorGate:
    """Per-role decision of whether to run a reactor turn, remembering each role's last turn."""

    def __init__(self, *, heartbeat_sec: float = HEARTBEAT_SEC, wake_margin_sec: float = WAKE_MARGIN_SEC) -> None:
        """Create a gate with no turn remembered for any role."""
        self._heartbeat_sec = float(heartbeat_sec)
        self._wake_margin_sec = float(wake_margin_sec)
        self._last_turn: dict[str, tuple[tuple[str, int, str], float]] = {}

    def decide(self, role: str, inputs: GateInputs, *, now: float) -> tuple[bool, str]:
        """Return ``(run, reason)`` for ``role`` this tick; a run is remembered as the role's latest turn."""
        reason = self._run_reason(role, inputs, now=now)
        if reason == SKIP_OWNER_IN_FLIGHT:
            return False, reason
        self._last_turn[role] = (inputs.context, float(now))
        return True, reason

    def _run_reason(self, role: str, inputs: GateInputs, *, now: float) -> str:
        if not inputs.owner_task_id:
            return RUN_UNOWNED
        if inputs.closing:
            return RUN_CLOSING
        last = self._last_turn.get(role)
        if last is None or last[0] != inputs.context:
            return RUN_NEW_CONTEXT
        if inputs.mail:
            return RUN_MAIL
        if inputs.owner_lease_left_sec is not None and inputs.owner_lease_left_sec <= self._wake_margin_sec:
            return RUN_LEASE_ENDING
        if inputs.phase_budget_left_sec is not None and inputs.phase_budget_left_sec <= self._wake_margin_sec:
            return RUN_BUDGET_ENDING
        if float(now) - last[1] >= self._heartbeat_sec:
            return RUN_HEARTBEAT
        return SKIP_OWNER_IN_FLIGHT
