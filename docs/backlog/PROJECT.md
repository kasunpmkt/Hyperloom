<!--
SPDX-FileCopyrightText: 2026 KRAI Ltd. - Hasith Ishara
SPDX-License-Identifier: MIT
-->

# Project rules: the ModelOpt improvement backlog

This file is loaded into every Claude Code session in this fork (via `CLAUDE.md`).
It is the standing context for the **developer agent** that works the backlog. It does
not change how Hyperloom itself runs.

## Goal

Improve Hyperloom's inference **latency and throughput** on AMD Instinct GPUs by adopting
techniques from NVIDIA Model-Optimizer (ModelOpt): a latency objective, speculative
decoding as a searched lever, in-loop quantization, stronger accuracy gates, and later
sparsity, step caching, and pruned model variants.

Three standing rules:

1. Every claimed gain is **re-measured on our AMD hardware** under Hyperloom's benchmark
   protocol. Speedups quoted from ModelOpt were measured on NVIDIA GPUs and are
   motivation only.
2. A root cause inside vLLM, SGLang, Quark, AITER, or ModelOpt is **fixed upstream** and
   pinned, not worked around locally (`AGENTS.md`).
3. Any ModelOpt **code** that is ported (not just an idea) keeps its Apache-2.0 notice and
   is recorded in `THIRD_PARTY.md` and `REUSE.toml`.

## Two agent layers, kept apart

- **Hyperloom's own agents** (Orchestration, Critic, specialists) run *inside* an
  `optimize` session and optimize a serving workload. Their instructions are the
  `SKILL.md` files under `src/hyperloom/` (for example
  `src/hyperloom/inference_optimizer/SKILL.md`) and the prompts under
  `src/hyperloom/orchestrator/prompts/`.
- **The developer agent** (a Claude Code session reading this file) changes Hyperloom's
  source and treats a Hyperloom session as the thing under test: it launches runs, reads
  the artifacts, and judges the change.

The two share no state or prompts. The developer agent must not follow the runtime
`SKILL.md` files as its own instructions, and must not edit them except when an issue
asks for it. The `.claude/skills/hyperloom-*` skills are for *launching* runs, not for
development.

## Where the backlog lives

| What | Where |
|---|---|
| Issue texts, labels, execution order | [`docs/backlog/issues.md`](issues.md) (source of truth; sync with `create_issues.py --update`) |
| Tracking issue | GitHub issue #1 in this fork; child issues #2–#21 |
| Board | GitHub project `users/ishara0925/projects/4`, arranged in execution order |
| Ground truth | `baselines/` (produced by issue #21) |
| Experiment records | `experiments/` and the generated `RESULTS.md` (see below) |

**Start of every work session:** read tracking issue #1, then the assigned issue, then
`baselines/README.md`. Check that the issue's dependencies (named in its body) are
closed before starting it. Work in a branch named `issue-<N>`.

Execution order: #21 → #4 → #3 → #2 → #5 → #7 → #6 → #15 → #12 → #10 → #13 → #16 →
#17 → #11 → #14 → #8 → #18 → #19 → #9 → #20. Issues #18, #19 and #9 have no dependency
on the main chain and can run in parallel. #8 proceeds only if #6 showed a gain with a
public draft.

## Ground truth and the noise band

`baselines/README.md` freezes the reference workloads and, per workload and metric, the
**noise band** measured from three stock-baseline runs. A change may claim a gain only
when its delta against ground truth is **outside the noise band**. A delta inside the
band is recorded as `inconclusive`, never as `keep`.

## Experiment log

The log has two levels. One rule governs both: **numbers are extracted by a script from
Hyperloom's artifacts, never typed by the agent.**

### Level 1: inside a session

Hyperloom already records what it tried. `session_breakdown.json`
(`docs/reference/session-breakdown.md`) carries the per-stage `timeline`, the kept stack
in `outcome.final.action_path`, `outcome.stop_reason`, `metadata.elapsed_minutes`, and
the `critic` block; per-proposal verdicts and their reasons live in the session
directory's ledger and review files. Nothing here is re-logged by hand; it is extracted.

### Level 2: our experiments

One record per (issue × reference workload × run), under
`experiments/<YYYYMMDD>-issue<N>-<workload>/`:

- `record.json` — written by `scripts/record_experiment.py <session_dir> --issue N
  --workload <ref-id> [--pr M]`. The script reads `session_breakdown.json` and
  `baselines/` and fills in: the metrics (`output_throughput`, TTFT/TPOT p50/p90,
  E2EL p99, accuracy), Hyperloom's `elapsed_minutes` and per-phase durations,
  `cumulative_gain_pct_validated`, `stop_reason`, the kept stack, counts of candidates
  tried / kept / reverted, the delta against ground truth per metric, and whether each
  delta is outside the noise band. The only hand-supplied fields are `verdict`
  (`keep` | `discard` | `inconclusive`) and `reason`. The script refuses `keep` when no
  graded metric is outside the noise band, and refuses any record whose `session_dir`
  does not exist.
- `candidates.md` — the extracted Level-1 list: each candidate Hyperloom tried, its
  measured delta, KEEP or REVERT, and the Critic's reason. This answers "why was X
  discarded" without opening the session directory.
- `RESULTS.md` at the repo root is **generated** by `scripts/render_results.py` from every
  `record.json` and is never hand-edited. It has one row per run (issue, change,
  workload, baseline → new for each graded metric, delta, in/out of noise band,
  Hyperloom time, candidates tried/kept, verdict, reason, PR) and a collapsed table with
  the best run per issue.

Rules:

- **Every run is recorded, including discards.** The discard reasons are the more
  valuable half of the log.
- A run's `session_dir` must still exist when the record is committed; the evidence
  stays reproducible.
- The scripts named above are the contract. Until they land (their own PR, first task
  after #21), records are still created, by hand, in the same schema, and the
  numbers are copied from `session_breakdown.json` with the path cited.

## Reporting contract

The developer agent writes to GitHub at three fixed points, and at no others:

1. **Pickup:** comment on the issue with the plan and the reference workloads to be run;
   move the project item to *In progress*.
2. **Result:** comment with the `RESULTS.md` row(s) for this issue, and update the single
   pinned summary comment on tracking issue #1 in place.
3. **PR opened:** the PR description states the observable effect (per `AGENTS.md`) and
   links the issue and the experiment records; move the project item to *In review*.

Each PR commits its `experiments/` records and the regenerated `RESULTS.md`. Branches are
pushed early, not only at PR time; the workstation is not a backup.

Never paste secrets (API keys, tokens, custom headers) into issues, comments, records,
or logs. `.env` stays local.

## Environment

Filled in by issue #21 and kept current here:

| Item | Value |
|---|---|
| Workstation | _(hostname, Ubuntu version)_ |
| GPUs | _(model × count)_ |
| ROCm / driver | _(version)_ |
| Run mode | `docker` (validated stack); container image tag: _(tag)_ |
| Workspace clone | _(absolute path; always the same path, so Claude's memory stays in one place)_ |
| `USER_DATA_PATH` | _(persistent disk; holds the recipe KB and session dirs; backed up)_ |
| Hyperloom wheel | 1.1.2 |
