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
| GEAK upstream problems (fixes this fork cannot make) | [`docs/backlog/geak-backlog.md`](geak-backlog.md) |
| Tracking issue | GitHub issue #1 in this fork; child issues #2–#21, #35–#40, #43–#45, #47 and #54–#58 |
| Board | GitHub project `users/ishara0925/projects/4`, arranged in execution order |
| Ground truth | `baselines/` (produced by issue #21) |
| Experiment records | `experiments/` and the generated `RESULTS.md` (see below) |

**Start of every work session:** read tracking issue #1, then the assigned issue, then
`baselines/README.md`. Check that the issue's dependencies (named in its body) are
closed before starting it. Work in a branch named `issue-<N>`.

Execution order: #21 → #4 → #37 → #38 → #39 → #3 → #35 → #2 → #5 → #7 → #6 → #15 → #12 → #10 → #13 → #16 →
#17 → #11 → #14 → #8 → #18 → #19 → #9 → #20. Issues #40 and #43 (bugs), #44 (after #40 and #43), #45, #47, #54 (after #45), #55 and #56 (bugs), #57,
#58 (upstream GEAK), #18, #19 and #9 have no dependency
on the main chain and can run in parallel. #8 proceeds only if #6 showed a gain with a
public draft.

## Ground truth and the noise band

`baselines/README.md` freezes the reference workloads and, per workload and metric, the
**noise band** measured from three stock-baseline runs. A change may claim a gain only
when its delta against ground truth is **outside the noise band**. A delta inside the
band is recorded as `inconclusive`, never as `keep`.

### Recipe KB state

Hyperloom's recipe KB (`$KNOWLEDGE_LOCAL_ROOT`, default `$USER_DATA_PATH/knowledge`) is keyed by
model, GPU, framework, architecture, framework version and precision, not by concurrency or
sequence length. Every run reads it (T0 warm replay, agent priors) and writes it back, including a
baseline-only run. A shared KB therefore makes each run depend on the runs before it, which the
noise band cannot absorb.

**Every ground-truth and experiment run starts from an empty KB of its own:** point
`KNOWLEDGE_LOCAL_ROOT` at a new empty directory per run. Keep the KB features enabled (no
`--degraded-kb`); an empty KB only removes the carried-over knowledge. The persistent
`$USER_DATA_PATH/knowledge` is for production use of Hyperloom only. An issue that changes the KB
itself (storage, replay, priors) adds a second comparison from a frozen, versioned KB snapshot,
copied fresh for each run.

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
| Workstation | `xe9680-3`, Ubuntu 22.04.5 LTS (kernel 5.15.0-130); shared with other users |
| GPUs | 8× AMD Instinct MI300X (gfx942); this project uses host GPU 7 only |
| ROCm / driver | host ROCk module 6.10.5; container ROCm 10.0.0 (HIP 7.15) |
| Run mode | `docker` (validated stack); container image tag: `rocm/vllm:rocm10.0.0_ubuntu24.04_py3.14_pytorch_2.12.0_vllm_0.27.0`, one long-running container `hyperloom-hasith` that sees only GPU 7, started with `--init` |
| Workspace clone | `/home/hasith/AMD/Hyperloom` |
| `USER_DATA_PATH` | `/home/hasith/AMD/hyperloom-data` (local disk; backup not confirmed, so anything that must be kept is committed under `baselines/` or `experiments/`); per-run KBs under `kb-runs/<run tag>/` |
| Hyperloom | source checkout (not the 1.1.2 wheel); the ground truth was measured at `main` `aac3eee24` |
