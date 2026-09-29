<!--
SPDX-FileCopyrightText: 2026 KRAI Ltd. - Hasith Ishara
SPDX-License-Identifier: MIT
-->

# Ground truth: reference workloads and noise band

Every improvement in the backlog is judged against the numbers in this directory
(`docs/backlog/PROJECT.md` § *Ground truth and the noise band*). A change may claim a
gain only when its delta against ground truth is **outside the noise band** of that
workload and metric; a delta inside the band is `inconclusive`.

Produced by issue #21. **Status: draft.** The workloads are proposed and not yet
frozen; every value marked _TBD_ is filled in from measured artifacts, never typed.

## Environment

| Item | Value |
|---|---|
| Host | `xe9680-3`, Ubuntu 22.04.5 LTS, kernel 5.15.0-130-generic |
| GPUs | 8x AMD Instinct MI300X OAM (gfx942); runs use one dedicated GPU: _TBD_ |
| ROCm (host) | ROCk module 6.10.5 |
| ROCm / framework (container) | _TBD_ |
| Run mode | `docker` |
| Container image | `docker.io/rocm/vllm:rocm10.0.0_ubuntu24.04_py3.14_pytorch_2.12.0_vllm_0.27.0` |
| Hyperloom | source checkout, commit _TBD_ |
| Claude model | _TBD_ |
| Host sharing | Shared with other GPU jobs; the neighbouring load during each measurement is recorded next to it |

## Reference workloads

All use the default random-token prompts, so they match existing recipe-KB rows.

| ID | Model | Framework | TP | CONC | ISL/OSL | Precision |
|---|---|---|---|---|---|---|
| `ref-dense-bf16` | Qwen3-8B | vLLM | 1 | 64 | 1024/1024 | BF16 |
| `ref-latency` | Qwen3-8B | vLLM | 1 | 4 | 1024/1024 | BF16 |
| `ref-dense-fp8` | Qwen3-14B-FP8 | vLLM | 1 | 64 | 1024/1024 | FP8 |

The set stays small because it is re-run for every issue.

## Metrics

Taken from `session_breakdown.json` (`docs/reference/session-breakdown.md`):

| Metric | Source field | Better |
|---|---|---|
| Output throughput | `outcome.baseline.throughput_tok_s_per_gpu` / `outcome.final.throughput_tok_s_per_gpu` (whole-server total despite the name) | higher |
| TTFT p50 / p90 | `perf.ttft_p50_ms`, `perf.ttft_p90_ms` | lower |
| TPOT p50 / p90 | `perf.tpot_p50_ms`, `perf.tpot_p90_ms` | lower |
| E2EL p99 | `e2el_p99_ms` from the benchmark report | lower |
| Accuracy (GSM8K) | `outcome.baseline.accuracy` | higher |

## Noise band

For each workload, the stock baseline is measured three times on the same benchmark path
PRELUDE uses. The band is the min–max spread of those three runs.

### `ref-dense-bf16`

| Metric | Run 1 | Run 2 | Run 3 | Min | Max | Mean | Band (% of mean) |
|---|---|---|---|---|---|---|---|
| Output throughput | _TBD_ | | | | | | |
| TTFT p50 / p90 | _TBD_ | | | | | | |
| TPOT p50 / p90 | _TBD_ | | | | | | |
| E2EL p99 | _TBD_ | | | | | | |
| GSM8K | _TBD_ | | | | | | |

`ref-latency` and `ref-dense-fp8` get the same table once they are measured.

## Hyperloom today

One full `optimize` run per workload with the default phase chain. This is the number
every later issue must beat.

| Workload | Stock throughput | Hyperloom throughput | `cumulative_gain_pct_validated` | Kept stack (`action_path`) | `stop_reason` | Elapsed |
|---|---|---|---|---|---|---|
| `ref-dense-bf16` | _TBD_ | | | | | |
| `ref-latency` | _TBD_ | | | | | |
| `ref-dense-fp8` | _TBD_ | | | | | |

## Layout

```
baselines/
  README.md                 this file
  <ref-id>/
    session_breakdown.json  from the Hyperloom-today optimize run
    state.json              final state of that run
    kb_row.json             its recipe-KB row
    noise/run{1,2,3}/       report.json for each stock-baseline run
    versions.txt            Hyperloom commit, image tag, ROCm and framework versions
```

Logs that can contain secrets are never committed.

## Unattended operation

A tmux session `hyperloom` on the host, started from a fresh login so it has the GPU
groups, running Claude Code from the workspace clone with `/remote-control`.
