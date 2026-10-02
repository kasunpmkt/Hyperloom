<!--
SPDX-FileCopyrightText: 2026 KRAI Ltd. - Hasith Ishara
SPDX-License-Identifier: MIT
-->

# Ground truth: reference workloads and noise band

Every improvement in the backlog is judged against the numbers in this directory
(`docs/backlog/PROJECT.md` § *Ground truth and the noise band*). A change may claim a
gain only when its delta against ground truth is **outside the noise band** of that
workload and metric; a delta inside the band is `inconclusive`.

Produced by issue #21. Every number below is read from the artifacts committed next to this file.

## Environment

| Item | Value |
|---|---|
| Host | `xe9680-3`, Ubuntu 22.04.5 LTS, kernel 5.15.0-130-generic, 2× Xeon Platinum 8460Y+, 2.0 TiB RAM |
| GPUs | 8× AMD Instinct MI300X OAM (gfx942); every run uses one dedicated GPU, host GPU 7 |
| ROCm (host) | ROCk module 6.10.5 |
| Container image | `docker.io/rocm/vllm:rocm10.0.0_ubuntu24.04_py3.14_pytorch_2.12.0_vllm_0.27.0` |
| Framework (container) | vLLM 0.27.1.dev5+gf46a9dfe2, PyTorch 2.12.0+rocm10.0.0 (HIP 7.15), AITER 0.1.20.post1, Triton 3.8.0 |
| Run mode | `docker`, one long-running container that sees only GPU 7, started with `--init` |
| Hyperloom | source checkout; every run's `src/` is identical to `main` at `aac3eee24` |
| Claude model | Opus, through a Claude subscription token (`CLAUDE_CODE_OAUTH_TOKEN`) |
| Host sharing | Shared with other users' GPU jobs on the other seven GPUs |
| CPU governor | `powersave`, kept deliberately: the smoke run was measured in it, and every ground-truth and later run uses the same setting so their numbers compare |

## Reference workloads

All use the default random-token prompts, so they match existing recipe-KB rows.

| ID | Model | Framework | TP | CONC | ISL/OSL | Precision |
|---|---|---|---|---|---|---|
| `ref-dense-bf16` | Qwen3-8B | vLLM | 1 | 64 | 1024/1024 | BF16 |
| `ref-latency` | Qwen3-8B | vLLM | 1 | 4 | 1024/1024 | BF16 |
| `ref-moe-fp4` | gpt-oss-120b (MoE, 128 experts, top-4) | vLLM | 1 | 64 | 1024/1024 | MXFP4 |

`ref-moe-fp4` replaces the `ref-dense-fp8` row proposed in #21: it covers a mixture-of-experts
model and 4-bit weights, which is where the kernel stage matters (see *Hyperloom today*). The set
stays small because it is re-run for every issue.

## Method

- **Stock baseline (noise floor):** three runs of Hyperloom's own PRELUDE baseline and nothing else:
  `optimize --no-framework-agent --no-kernel --no-enable-conc-sweep --no-enable-roofline` with the
  workload flags. The baseline executor is the same one a full run uses: a discarded warmup round,
  then the measured round, plus the GSM8K accuracy gate.
- **Hyperloom today:** full `optimize` runs, in two configurations:
  - *default chain*, `--max-hours 3 --target-gain 30` for the Qwen3-8B workloads; Hyperloom's own
    gpt-oss preset (`--max-hours 6 --target-gain 10 --model-class moe_swa`) for `ref-moe-fp4`;
  - *settings-only* (the reference for later issues on the Qwen3-8B workloads), two runs each:
    `--no-kernel --no-enable-conc-sweep --no-enable-roofline --max-minutes-framework-pct 0.50
    --max-minutes-sweep-pct 0.01 --max-hours 3 --target-gain 30`.
- **Recipe KB:** every run starts from an empty KB of its own (`KNOWLEDGE_LOCAL_ROOT` set to a fresh
  directory), per `docs/backlog/PROJECT.md` § *Recipe KB state*. Noise runs 1–3 of `ref-dense-bf16`
  predate this rule. They used the shared KB, which held the smoke run's recipe; their baseline
  numbers are unaffected because PRELUDE measures the baseline before warm replay.
- **Spread** is (max − min) / mean of the runs.

## Metrics

Taken from each run's `baseline_report.json` (the measured round's InferenceX report) and
`session_breakdown.json` (`docs/reference/session-breakdown.md`):

| Metric | Source field | Better |
|---|---|---|
| Output throughput | `output_throughput`; `outcome.baseline/final.throughput_tok_s_per_gpu` (whole-server total despite the name) | higher |
| TTFT p50 / p90 | `median_ttft_ms`, `p90_ttft_ms` | lower |
| TPOT p50 / p90 | `median_tpot_ms`, `p90_tpot_ms` | lower |
| E2EL p99 | `p99_e2el_ms` | lower |
| Accuracy (GSM8K, strict match) | `outcome.baseline.accuracy` | higher |

## Noise band

### `ref-dense-bf16`

| Metric | Run 1 | Run 2 | Run 3 | Min | Max | Mean | Spread |
|---|---|---|---|---|---|---|---|
| Output throughput (tok/s) | 4474.8 | 4407.0 | 4457.3 | 4407.0 | 4474.8 | 4446.3 | **1.52%** |
| TTFT p50 (ms) | 998.7 | 1004.0 | 1015.2 | 998.7 | 1015.2 | 1006.0 | 1.64% |
| TTFT p90 (ms) | 1340.9 | 1364.3 | 1425.3 | 1340.9 | 1425.3 | 1376.9 | 6.13% |
| TPOT p50 (ms) | 13.28 | 13.50 | 13.35 | 13.28 | 13.50 | 13.38 | 1.61% |
| TPOT p90 (ms) | 13.95 | 14.12 | 13.96 | 13.95 | 14.12 | 14.01 | 1.26% |
| E2EL p99 (ms) | 15839 | 16073 | 15817 | 15817 | 16073 | 15909 | 1.61% |
| GSM8K | 0.902 | 0.909 | 0.904 | 0.902 | 0.909 | 0.905 | 0.75% |

Counting the stock baselines measured inside the full runs too, there are 6 throughput samples
(4390.6–4474.8 tok/s, mean 4426.7): about **1.9%**. Use 2% as the throughput band.

### `ref-latency`

| Metric | Run 1 | Run 2 | Run 3 | Min | Max | Mean | Spread |
|---|---|---|---|---|---|---|---|
| Output throughput (tok/s) | 578.1 | 596.8 | 601.3 | 578.1 | 601.3 | 592.1 | **3.93%** |
| TTFT p50 (ms) | 160.5 | 161.2 | 158.7 | 158.7 | 161.2 | 160.1 | **1.51%** |
| TTFT p90 (ms) | 166.9 | 171.5 | 162.4 | 162.4 | 171.5 | 166.9 | 5.48% |
| TPOT p50 (ms) | 6.77 | 6.56 | 6.50 | 6.50 | 6.77 | 6.61 | 4.05% |
| TPOT p90 (ms) | 6.82 | 6.61 | 6.56 | 6.56 | 6.82 | 6.67 | 3.98% |
| E2EL p99 (ms) | 7093 | 6882 | 6835 | 6835 | 7093 | 6937 | 3.71% |
| GSM8K | 0.906 | 0.904 | 0.906 | 0.904 | 0.906 | 0.905 | 0.17% |

TTFT p50 is the most stable latency metric here, so latency gains are easiest to prove on it.

### `ref-moe-fp4`

_Filled in from `ref-moe-fp4/noise{1,2,3}/` (runs in progress)._ Until then, two stock samples exist:
1462.1 tok/s (the full run's baseline) and 1523.1 tok/s (`ab-stock1`), about 4% apart.

### Accuracy band

Three runs understate GSM8K noise. Across all 14 Qwen3-8B baselines (both workloads, including two
aborted early attempts) strict-match GSM8K spans **0.8946–0.9090, a 1.6% spread**; lm-eval's own
standard error per run is ±0.0083. The eval is greedy and covers all 1,319 questions, so the variation is
serving nondeterminism (batching), not sampling; the flexible-extract score moves with it, so it is not an
answer-format effect. #21's "anomaly" (0.898 in the `ref-latency` default-chain run) is inside this band.
**Use 1.6% (about 2 standard errors) as the accuracy band** for Qwen3-8B, not the 3-run spread.

## Hyperloom today

### Qwen3-8B

| Workload | Configuration | Stock → Hyperloom (tok/s) | Gain | Kept stack (`action_path`) | Verdict |
|---|---|---|---|---|---|
| `ref-dense-bf16` | default chain | 4390.6 → 4474.7 | +1.92% | `explore:aiter-master-on` | inconclusive |
| `ref-dense-bf16` | settings-only, run 1 | 4392.3 → 4480.1 | +2.00% | `explore:aiter-master-on` | inconclusive |
| `ref-dense-bf16` | settings-only, run 2 | 4438.1 → 4464.9 | +0.60% | `explore:aiter-linear-rmsnorm-async` | inconclusive |
| `ref-latency` | default chain | 596.3 → 596.3 | 0% | none | no gain |
| `ref-latency` | settings-only, run 1 | 597.9 → 597.9 | 0% | none | no gain |
| `ref-latency` | settings-only, run 2 | 601.4 → 601.4 | 0% | none | no gain |

All runs ended with `stop_reason: sweep_done`. **The settings-only pair is the reference** later
issues compare against. Hyperloom today finds no gain outside the noise band on either workload.

A known lever exists: `--kv-cache-dtype fp8` alone, on stock-baseline runs with no agents
(`ref-dense-bf16/ab-fp8kv{1,2}/`), gives 5034.9 and 5000.7 tok/s (**+13.7% / +13.0%** against the
6-run stock mean), TPOT p50 11.65 / 11.81 ms, GSM8K 0.909 / 0.906. None of the five full runs proposed
it, so the gap is in the framework agent's proposals, not in measurement (#37–#39).

### gpt-oss-120b (`ref-moe-fp4`)

One full run with the default chain (`ref-moe-fp4/today/`, 6-hour preset):

| Phase | Result |
|---|---|
| PRELUDE | Stock 1462.1 tok/s, GSM8K 0.962 |
| FRAMEWORK_AGENT | 7 candidates, kept `--attention-backend ROCM_AITER_UNIFIED_ATTN` + `VLLM_ROCM_USE_AITER=1`: 1502.3 tok/s, **+2.75%** |
| KERNEL_AGENT (GEAK) | Tuned `triton_kernels` MXFP4 MoE launch settings: +20.7% in GEAK's own harness. The run was stopped at the plan-usage limit while GEAK finished, and the resumed run dropped the result (#43). |

The run has no `session_breakdown.json` because it never reached CLOSE; `state.json` and `kb_row.json`
are its record. Its +2.75% is inside the two stock samples' 4% spread.

The kernel result, measured separately with the stock-baseline method (the GEAK add-on on the server's
`PYTHONPATH`, no agents):

| Run | Configuration | Output tok/s | TPOT p50 (ms) | GSM8K |
|---|---|---|---|---|
| `today` (baseline) | stock | 1462.1 | 42.24 | 0.962 |
| `ab-stock1` | stock | 1523.1 | 41.16 | 0.965 |
| `ab-geak1` | GEAK settings | 1795.2 | 34.65 | 0.966 |
| `ab-geak2` | GEAK settings | 1826.3 | 33.63 | 0.961 |
| `ab-geak-aiter1` | GEAK settings + AITER attention | **1867.8** | 33.54 | 0.964 |

GEAK's settings give **+21.3%** (mean against mean), and with AITER attention **+25.1%**, accuracy
unchanged. Against this workload, the number to beat is the stock band; the reachable best measured so
far is 1867.8 tok/s.

## Layout

```
baselines/
  README.md                       this file
  <ref-id>/
    noise1/ noise2/ noise3/       stock-baseline runs: baseline_report.json, session_breakdown.json
    today/                        default-chain optimize run: + state.json, kb_row.json
    settings1/ settings2/         settings-only optimize runs (Qwen3-8B): same files as today/
    ab-<name>/                    single-change A/B runs on the stock-baseline method
    */session.txt                 run tag and session directory name
```

Logs that can contain secrets are never committed; the files here were scanned for credentials before
commit.

## Unattended operation

Runs are driven from a tmux session `hyperloom` on the host, started from a fresh login so it has the
GPU groups:

- **`pipeline` window:** a pipeline script runs the steps one at a time; each run is launched into the
  container with its own empty KB, and `run-watch.sh` writes milestones (phase changes, baseline, new
  best, finish) and stops the run at 80% of the Claude plan's 5-hour or 7-day limit.
- **`relay` window:** a Claude Code session follows the milestone log and posts each milestone to the
  operator's Slack DM.
- **`dev` window:** a second Claude Code session works backlog issues in its own git worktree. It
  completed #40 unattended (PR #42); a Notification hook raises a Slack alert when it needs input.

Claude Code Remote Control is disabled by the organization's policy, so Slack is the remote channel.
