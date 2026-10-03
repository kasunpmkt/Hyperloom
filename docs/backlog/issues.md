# Hyperloom × Model-Optimizer: improvement backlog

Proposed GitHub issues to improve Hyperloom's **latency and throughput** by adopting
techniques from NVIDIA Model-Optimizer (ModelOpt). Each `## [HL-xx]` section below is
one issue. The body follows Hyperloom's feature-request template (Problem / Proposed
solution / Expected impact / Alternatives / Additional context) plus acceptance
criteria, so issues can be picked up and tried one by one.

- Hyperloom paths are relative to the Hyperloom repo root.
- ModelOpt paths are relative to the `NVIDIA/Model-Optimizer` repo root.
- Speedups quoted from ModelOpt were measured by NVIDIA on NVIDIA GPUs. They are
  motivation, not a prediction for MI300X/MI325X/MI355X; every issue must re-measure
  under Hyperloom's own benchmark protocol.
- ModelOpt is Apache-2.0. Any code ported (not just ideas) must keep its notices and be
  recorded in `THIRD_PARTY.md` and `REUSE.toml`.

Post with `create_issues.py` (see bottom of file). `HL-xx` references inside bodies are
rewritten to real `#123` issue links after creation.

## Suggested order

| Wave | Issues | Why first |
|---|---|---|
| 0. Bring-up and ground truth | HL-B0 | Nothing below can be judged until Hyperloom runs on the server and the reference numbers and their noise band exist |
| 1. Measure latency properly | HL-01, HL-02, HL-03, HL-04 | Latency cannot be optimized until it is an objective and is measured on realistic prompts |
| 2. Speculative decoding | HL-05, HL-06, HL-07, HL-08 | Largest decode-latency lever; Hyperloom only passes the flag through today |
| 3. Quantization in the loop | HL-09, HL-10, HL-11, HL-12, HL-13 | Quantization is currently a one-shot prelude with no search and no KEEP/REVERT |
| 4. Accuracy and knowledge | HL-14, HL-15 | Every new lever above trades accuracy; the gate and the KB must keep up |
| 5. Longer-horizon levers | HL-16, HL-17, HL-18 | Kernel-level sparse attention, diffusion caching, offline model variants |

## Label set

`create_issues.py` creates any label that does not exist yet.

| Label | Meaning |
|---|---|
| `type:feature`, `domain:inference` | Existing Hyperloom labels (from `scripts/migrate-labels.sh`) |
| `area:objective`, `area:benchmark`, `area:specdec`, `area:quantization`, `area:accuracy`, `area:recipe-kb`, `area:kernel`, `area:xdit`, `area:model-compression`, `area:host-overhead`, `area:search` | New: which part of the system the issue touches |
| `priority:P0` … `priority:P3` | New: P0 = do first / unblocks others, P3 = research |
| `source:modelopt` | New: idea ported from NVIDIA Model-Optimizer |

---

## [HL-00] Tracking: adopt Model-Optimizer techniques to improve latency and throughput
<!-- labels: type:task, domain:inference, source:modelopt -->

### Summary
This is the parent issue for the backlog below. Hyperloom already searches serving flags,
framework patches, and kernels well. The gaps are model-level levers that ModelOpt
offers and Hyperloom lacks:

- latency as an optimization objective,
- speculative decoding as a searched and measured lever,
- in-loop, sensitivity-driven quantization,
- stronger accuracy gates,
- sparsity, step caching, and pruning or distillation.

### Child issues
- [ ] **HL-B0 Bring-up: run Hyperloom on the server and record the ground-truth baseline** — do this first; every other issue compares against it
- [ ] HL-01 SLO-constrained latency objective
- [ ] HL-02 Capture ITL and per-user tok/s
- [ ] HL-03 Coherence gate before benchmarking
- [ ] HL-04 Realistic prompt datasets for benchmarking
- [ ] HL-05 Speculative decoding as a searched lever
- [ ] HL-06 Acceptance-rate metrics
- [ ] HL-07 Offline EAGLE-3 draft training on ROCm
- [ ] HL-08 Evaluate DFlash block drafters on ROCm
- [ ] HL-09 Quantization as an in-loop KEEP/REVERT lever
- [ ] HL-10 AutoQuantize-style per-layer mixed precision
- [ ] HL-11 Default exclusion list and MoE calibration coverage
- [ ] HL-12 Calibrated KV-cache quantization
- [ ] HL-13 Composable quantization recipes and escalation policy
- [ ] HL-14 Configurable, multi-signal accuracy gate
- [ ] HL-15 Recipe KB: latency Pareto points and model-level recipes
- [ ] HL-16 Per-operating-point tuning in SWEEP
- [ ] HL-17 Skip-softmax sparse attention for long-context prefill
- [ ] HL-18 Diffusion step caching for xDiT with a distributional quality gate
- [ ] HL-19 Offline model-variant track (prune + distill)
- [ ] HL-20 Host-side overhead: GPU idle time as a first-class search target
- [ ] HL-21 Cut the per-candidate cost of the framework search
- [ ] HL-22 Keep PRELUDE within its budget and spend the whole phase budget
- [ ] HL-23 Noise-aware keep threshold for framework candidates
- [ ] HL-24 Warm replay accepts a recipe below its own threshold and replays it partially
- [ ] HL-25 Resume drops a finished GEAK result and skips to SWEEP
- [ ] HL-26 Store a validated GEAK overlay in the recipe KB and replay it on the next run
- [ ] HL-27 Give the KERNEL delegation a usage budget and stop GEAK when the run stops
- [ ] HL-28 Don't run an LLM turn every tick while a delegated task is in flight
- [ ] HL-29 Report GEAK's Claude usage per role, and give the KERNEL delegation a usage budget
- [ ] HL-30 GEAK's timeout leaves no time to re-validate its result
- [ ] HL-31 Without `claude` on PATH, specialists silently lose source access
- [ ] HL-32 Inline TraceLens analysis freezes the coordinator and dominates PRELUDE's cost
- [ ] HL-33 (GEAK, upstream) An interrupted GEAK run is flushed as a final `no_gain`
- [ ] HL-34 Reap the KERNEL delegation's leftover servers and check free VRAM before every server boot

### Execution order (as arranged in project 4)
HL-B0 → HL-03 → HL-21 → HL-22 → HL-23 → HL-02 → HL-20 → HL-01 → HL-04 → HL-06 → HL-05 → HL-14 → HL-11 → HL-09 →
HL-12 → HL-15 → HL-16 → HL-10 → HL-13 → HL-07 → HL-17 → HL-18 → HL-08 → HL-19.
HL-24 and HL-25 (bugs), HL-26 (after HL-24 and HL-25), HL-27, HL-28, HL-29 (after HL-27), HL-30 and HL-31 (bugs),
HL-32, HL-33 (upstream GEAK), HL-34 (bug), HL-17, HL-18 and HL-08 have no dependency on the main chain and can run in parallel
whenever there is capacity. HL-07 only proceeds if HL-05 showed a gain with a public
draft.

### Review notes (second pass)
Every issue was re-checked against both codebases. None was found impossible, but the
following are **probes with uncertain outcome**, not committed features, and must stay
time-boxed: HL-08 (DFlash: vLLM-nightly-only on NVIDIA, no SGLang path, ROCm
unknown), HL-12's FP4-KV spike, HL-17 (Triton skip-softmax on ROCm), HL-19 (design
note only). HL-07 is the most expensive item and depends on HL-05 first showing a gain
with a public draft. Details are in each issue's body.

Known gaps in Hyperloom that these clarifications rely on:
- The InferenceX benchmark runner has no prompt-dataset input; only the AgentX aiperf
  client does (HL-04).
- `QuantizationConfig.layer_overrides` and `kv_cache` exist but are rendered as prompt
  text / never set by the CLI (HL-10, HL-12).
- Serving APIs expose only top-k logprobs, so any divergence check is truncated (HL-14).
- ModelOpt's `cache_diffusion` targets UNet/SDXL, not the DiT models xDiT serves (HL-18).

### Ground rules
- Follow `AGENTS.md`: one concern per PR, and state the observable effect in each PR.
- Fix upstream where the root cause is in vLLM, SGLang, Quark, or AITER.
- Record every ModelOpt code port in `THIRD_PARTY.md` and `REUSE.toml`.

---

## [HL-B0] Bring-up: run Hyperloom on the Dell server and record the ground-truth baseline
<!-- labels: type:task, domain:inference, area:benchmark, priority:P0 -->

### Problem / use case
Every other issue in this backlog claims a latency or throughput improvement. None of
those claims can be checked until Hyperloom runs end to end on our own hardware and we
have a **ground truth**: the stock numbers for a fixed set of reference workloads, what
Hyperloom achieves on them *today*, and how much run-to-run noise there is. Without the
noise band, a "2% gain" from a later issue is indistinguishable from a re-run.

### Proposed solution
1. **Inventory the server** and record it in the issue: GPU model and count
   (MI300X/MI325X/MI355X), ROCm version, driver, Docker with `/dev/kfd` + `/dev/dri`
   access, Python version, free disk under `USER_DATA_PATH`, and outbound access to
   `api.anthropic.com`, `github.com`, and Hugging Face. Note whether the host is shared
   with other jobs; a shared host cannot give a clean noise floor.
2. **Install Hyperloom** the documented way (`docs/install/install.md`): a dedicated
   workspace, `pip install hyperloom-inference-optimizer==1.1.2 --target .`, then
   `/hyperloom-setup` with `HYPERLOOM_RUN_MODE=docker` (the recommended, validated
   stack). Secrets go in `.env`, never in the issue.
3. **Smoke test** with the shortest demo (`/hyperloom-qwen3-8b-3h`, Qwen3-8B, no kernel
   phase). It must reach CLOSE and write `session_breakdown.json`. Fix or file whatever
   blocks it before going further; bring-up bugs are their own issues.
4. **Define the reference workloads** and freeze them in a `baselines/README.md` in the
   fork. Suggested minimum, all with the default random-token prompts so they match
   existing KB rows:

   | ID | Model | Framework | TP | CONC | ISL/OSL | Precision |
   |---|---|---|---|---|---|---|
   | ref-dense-bf16 | Qwen3-8B | vLLM | 1 | 64 | 1024/1024 | BF16 |
   | ref-dense-fp8 | Qwen3-14B-FP8 | vLLM | 1 | 64 | 1024/1024 | FP8 |
   | ref-latency | Qwen3-8B | vLLM | 1 | 4 | 1024/1024 | BF16 |

   Add an SGLang row and a MoE model if the hardware and budget allow. Keep the set
   small; it will be re-run for every issue.
5. **Record the ground truth** for each reference workload:
   - **Stock baseline** (the PRELUDE anchor): `output_throughput`, TTFT p50/p90,
     TPOT p50/p90, E2EL p99, and the GSM8K accuracy score from the accuracy gate.
   - **Noise floor:** run the stock baseline **three times** and record min/max/mean
     for every metric above. The spread is the noise band; later issues may only claim
     a gain that exceeds it.
   - **Hyperloom today:** one full `optimize` run per workload with the default phase
     chain, recording `cumulative_gain_validated`, the kept stack (`best_config`),
     phase durations, and the `stop_reason`. This is the number every later issue
     must beat.
6. **Persist everything**: commit `baselines/<ref-id>/` with `session_breakdown.json`,
   the final `state.json`, the recipe-KB row, the three noise-floor benchmark reports,
   and the exact wheel version, container image tag, and ROCm version. Do not commit
   logs that contain secrets.
7. **Set up unattended operation** so later issues can be worked without a laptop: a
   dedicated Linux user for Claude, `gh auth login` on the server with `repo` +
   `project` scopes, `tmux`, and either Remote Control or a self-hosted GitHub Actions
   runner. Document the chosen path in `baselines/README.md`.

### Acceptance criteria
- [ ] Server inventory posted in this issue.
- [ ] `/hyperloom-qwen3-8b-3h` completes to CLOSE on the server.
- [ ] `baselines/README.md` defines the reference workloads and the noise band per
      metric, with the three-run min/max/mean table.
- [ ] `baselines/<ref-id>/` committed for every reference workload, with stock,
      noise-floor, and Hyperloom-today results.
- [ ] Ground-truth table (stock vs Hyperloom-today, per workload, per metric) posted as
      a comment on the tracking issue.
- [ ] Unattended operation works: one issue-triggered or tmux-run Claude session
      completes a trivial task on the server and reports back.

### Expected impact
No performance change. It makes every later result measurable and comparable, and it
surfaces environment problems before they are mistaken for optimization failures.

### Additional context
Blocks every other issue. Install docs: `docs/install/install.md`,
`examples/README.md`. Session output schema: `docs/reference/session-breakdown.md`.

---

## [HL-01] Add an SLO-constrained latency objective (max throughput subject to TTFT/TPOT p90 bounds)
<!-- labels: type:feature, domain:inference, area:objective, priority:P0, source:modelopt -->

### Problem / use case
Every objective in `src/hyperloom/orchestrator/state/objective.py` is based on throughput
or roofline: `TARGET_GAIN_PCT`, `TARGET_TPUT_PER_GPU`, `TARGET_DIR`, and
`TARGET_WITHIN_ROOFLINE_PCT`. By default candidates are graded on `output_throughput`
(`src/hyperloom/common/perf_metric.py`). Latency is graded only in AgentX mode
(`e2e_norm_intvty_p90`).

TTFT and TPOT p50/p90 are recorded but are never constraints, so a candidate can raise
tokens/s while breaking a latency SLA. Hyperloom's own specialist prompt names this blind
spot: "Chunked prefill without `--max-num-batched-tokens` → tail latency regressions
invisible to throughput-only benches" (`orchestrator/prompts/specialist_prompt_builder.py`).

### Proposed solution
- Add objective keys such as `TARGET_TTFT_P90_MS`, `TARGET_TPOT_P90_MS`, and
  `TARGET_E2EL_P99_MS`. With these set, the objective becomes "maximize
  `output_throughput` subject to the latency bounds".
- A candidate that breaks a bound is REVERTed and the reason is logged (for example
  `slo_violation:ttft_p90`), even if its throughput gain passes the KEEP threshold.
- Add a pure-latency mode: minimize TPOT p90 (or TTFT p90) at a fixed concurrency, with
  throughput as a guard band. This reuses the AgentX comparability checks
  (`perf_metric.py`).
- Pass the active SLO into the Orchestration and Critic prompts so that intents and
  verdicts reason about latency.
- The SLO keys are *constraints*, so they compose with any existing throughput objective
  (`TARGET_GAIN_PCT` etc.). The pure-latency mode is a separate objective key
  (for example `TARGET_TPOT_P90_MS` with `OBJECTIVE=latency`), and setting both is a
  validation error.
- Measurement noise: p90 at low concurrency is noisy. Reuse the paired interleaved A/B
  path (`orchestrator/measurement/paired.py`) for SLO decisions, with the same
  ≥2-pairs rule.
- ModelOpt reference: the serving harness in
  `plugins/modelopt/skills/deployment/references/benchmarking.md` treats TTFT, ITL,
  output tok/s, and per-user tok/s as first-class results at every concurrency point.

### Acceptance criteria
- [ ] New objective keys are validated at the CLI and env boundary and documented in
      `docs/reference/environment-variables.md`.
- [ ] KEEP/REVERT honours the SLO, and a unit test pins the `slo_violation` REVERT path.
- [ ] `session_breakdown.json` reports the SLO and whether the final stack meets it.
- [ ] One end-to-end run in latency mode on a demo workload is compared with a
      throughput-mode run.

### Expected impact
Makes latency optimizable at all. It also stops "fast on average, bad at p90" configs
from being kept.

### Alternatives considered
Keep AgentX as the only latency mode. It is tied to the AgentX harness and its
interactivity metric, not to general TTFT/TPOT SLAs.

### Additional context
Blocks HL-05, HL-16. Related: HL-02.

---

## [HL-02] Capture ITL and per-user tok/s in benchmark results
<!-- labels: type:feature, domain:inference, area:benchmark, priority:P0, source:modelopt -->

### Problem / use case
`src/hyperloom/orchestrator/actions/executors/benchmark_result.py` records TTFT, TPOT,
E2EL, and interactivity, but **not inter-token latency (ITL)** or per-user output tok/s.

Speculative decoding and chunked prefill both change ITL *jitter* much more than mean
TPOT. Without ITL those effects cannot be seen.

### Proposed solution
- Parse ITL mean/p50/p90/p99 and per-user tok/s from the InferenceX/bench_serving output
  and from aiperf (AgentX already uses aiperf).
- Add the metric definitions from ModelOpt `examples/specdec_bench/specdec_bench/metrics/timing.py`
  (per-request generation TPS, TTFT, per-step time, with min/max/mean/std/quartiles) where
  the raw data allows it.
- Before accepting a result, verify that the measured output length equals the requested
  OSL. The ModelOpt benchmarking reference makes this check first, and it catches
  `ignore_eos` misconfiguration.

### Acceptance criteria
- [ ] The new fields are present in the persisted measurement schema and in
      `session_breakdown.json`, and the schema docs are updated.
- [ ] A benchmark whose output length is short of the target is flagged as not
      comparable and is not used for KEEP/REVERT.
- [ ] Tests pin the parser against recorded bench outputs from vLLM, SGLang, and aiperf.

### Expected impact
Supplies the latency axes that HL-01, HL-05, and HL-16 grade on.

### Additional context
ModelOpt: `examples/specdec_bench/specdec_bench/metrics/timing.py` and
`plugins/modelopt/skills/deployment/references/benchmarking.md`.

---

## [HL-03] Coherence gate before every benchmark
<!-- labels: type:feature, domain:inference, area:accuracy, priority:P1, source:modelopt -->

### Problem / use case
The GSM8K accuracy gate (`orchestrator/actions/executors/_accuracy_gate.py`) is costly, so
it runs once per candidate at most, and `MAGPIE_EVAL_LIMIT` often caps it. Some
candidates produce fluent garbage at high speed, and Hyperloom spends a full benchmark
before it finds out. Examples: a wrong KV dtype, a broken patch, or a bad
speculative-decoding config.

### Proposed solution
Port ModelOpt's cheap coherence probe (`plugins/modelopt/skills/deployment/references/benchmarking.md`):

- Send one or two fixed prompts, for example "capital of France" and "17 × 23", and
  require the expected tokens ("Paris" and "391").
- Run it after server start-up and before the throughput benchmark.
- On failure, REVERT immediately with reason `coherence_gate_failed`.

### Acceptance criteria
- [ ] The probe runs for every LLM candidate and is skipped for scriptable/xDiT
      workloads.
- [ ] A failure short-circuits the benchmark and is recorded in the ledger so the same
      config is not retried.
- [ ] Probe prompts can be overridden for models that are not chat-tuned, and the gate
      can be disabled per model (a base model may legitimately fail "capital of France").
- [ ] A false positive is expensive (it discards a good candidate), so the probe retries
      once with a second prompt set before it fails, and the failing completion is
      logged.

### Expected impact
Saves benchmark wall-clock on broken candidates. It also becomes important once HL-05 and
HL-09 widen the search to riskier levers.

---

## [HL-04] Realistic prompt datasets for benchmarking (MT-Bench, SPEED-Bench, ShareGPT)
<!-- labels: type:feature, domain:inference, area:benchmark, priority:P0, source:modelopt -->

### Problem / use case
Baseline workloads use synthetic random tokens (`RANDOM_RANGE_RATIO` in
`src/hyperloom/inference_optimizer/assets/configs/baseline_*.yaml`). Random tokens
give speculative decoding no realistic acceptance rate, and n-gram, EAGLE, and MTP gains
all come out as zero or negative. Prefix caching is also invisible on random prompts.

### Proposed solution
- Add a `--bench-dataset {random,mtbench,speed_bench,sharegpt,custom}` workload option,
  with `random` kept as the default for comparability with existing KB rows.
- **Which runner.** The default Magpie → InferenceX runner scripts take only
  `ISL/OSL/RANDOM_RANGE_RATIO` (`assets/configs/baseline_*.yaml`) and have no prompt
  dataset input. The AgentX aiperf client (`assets/agentx/aiperf_client.sh`,
  `AGENTX_DATASET`) already replays a corpus. So the first implementation should route
  non-random datasets through the aiperf client for vLLM/SGLang too, rather than
  extending InferenceX. Check first whether InferenceX has since grown a dataset flag;
  if it has, prefer that and keep one runner.
- Reuse ModelOpt's dataset loaders and preparation:
  - `examples/specdec_bench/specdec_bench/datasets/` (MT-Bench, SpecBench, SPEED-Bench
    splits `qualitative` / `throughput_1k` / `throughput_16k`),
  - `examples/specdec_bench/prepare_data.py`.
- Apply the chat template to prompts, which `docs/.../internals.md` already requires for
  speculative decoding.
- Record the dataset in the recipe KB identity so that random-token and real-prompt
  results are never compared.

### Acceptance criteria
- [ ] At least MT-Bench and one SPEED-Bench throughput split are runnable through the
      aiperf client for vLLM and SGLang, and the resulting metrics land in the same
      measurement schema as InferenceX runs.
- [ ] The dataset choice appears in `session_breakdown.json` and in the KB
      `canonical_id` or `prefer` rerank keys.
- [ ] Docs explain when to pick each dataset.

### Expected impact
Prerequisite for any speculative-decoding win (HL-05 to HL-08). It also makes prefix
caching measurable.

---

## [HL-05] Speculative decoding as a first-class searched lever (vLLM + SGLang)
<!-- labels: type:feature, domain:inference, area:specdec, priority:P0, source:modelopt -->

### Problem / use case
Hyperloom handles `--speculative-config` only as a pass-through JSON flag
(`grid_server_args.py`, `_workload_envs.py`). MTP is searched only in the ATOM default
grid, and only for `moe_mla` model classes (`orchestrator/actions/executors/explore.py`).
There is no speculative-decoding specialist domain (`orchestrator/specialists/domains.py`),
and there is no grid for vLLM or SGLang.

Speculative decoding is the largest decode-latency lever. As motivation (not measured on
AMD), ModelOpt reports DFlash on Qwen3-8B with vLLM at 443 vs 145 tok/s at TP=1 on H100.

### Proposed solution
- Add a `speculative` specialist domain that proposes grids over:
  - method: `ngram`, `eagle3`, `mtp` (native heads), and `draft_model`,
  - `num_speculative_tokens` (1–7), top-k / tree width, and `--gpu-memory-utilization`
    headroom, which the specialist prompt already requires for MTP.
- Discover draft checkpoints: look for a published EAGLE-3 or DFlash draft for the target
  model on Hugging Face, and detect native MTP heads in `config.json`. If none is found,
  fall back to `ngram` or file a HL-07 training request.
- Gate by concurrency. Acceptance and speedup usually shrink as batch size grows, so the
  lever must be tested at the session's CONC and re-checked in SWEEP (HL-16).
- Grade with HL-01 (latency objective) and HL-06 (acceptance metrics), on HL-04 datasets.
- ModelOpt reference: the flag shapes in `examples/specdec_bench/specdec_bench/models/vllm.py`
  and `models/sglang.py`, and the per-framework notes in
  `plugins/modelopt/skills/deployment/references/{vllm,sglang}.md`.

**ROCm support to verify before building the grid** (none of this is confirmed in either
repo):
- vLLM V1 on ROCm: `ngram` needs no kernels and should work everywhere; `eagle`/`eagle3`
  and `mtp` depend on the attention backend supporting multi-query verification. Check
  which of `TRITON_ATTN`, `ROCM_AITER_FA`, `ROCM_AITER_MLA` support it in the pinned vLLM
  version, and add that to the compatibility filter.
- SGLang on ROCm: `--speculative-algorithm EAGLE` and `EAGLE3`; Hyperloom already marks
  SGLang eagle patches optional in `_server_patcher.py`.
- Draft checkpoints must match the target's tokenizer and chat template; a draft trained
  on a different template gives low acceptance rather than an error.

### Acceptance criteria
- [ ] The specialist domain is registered with an allowlist entry in `PHASE_ALLOWED_ACTIONS`.
- [ ] The compatibility filter rejects combinations that ROCm vLLM/SGLang do not support.
      Verify the support matrix on ROCm first.
- [ ] One demo model (for example Qwen3-8B with a public EAGLE-3 draft) is measured on
      MI300X at CONC 1/8/64, and TPOT/ITL vs baseline are reported.
- [ ] The KB records method, draft path, and `num_speculative_tokens` in `best_config`.

### Expected impact
Large TPOT reductions at low and medium concurrency. The gain at high concurrency needs
measurement.

### Additional context
Depends on HL-01, HL-04, HL-06. Enables HL-07, HL-08.

---

## [HL-06] Acceptance-rate metrics for speculative decoding
<!-- labels: type:feature, domain:inference, area:specdec, area:benchmark, priority:P0, source:modelopt -->

### Problem / use case
Hyperloom has no acceptance-rate measurement. When a speculative config makes no gain,
nothing tells us why. The cause could be a bad draft, a draft length that is too long,
high concurrency, or a mismatch between the draft and the chat template.

### Proposed solution
- Port the metric definitions from ModelOpt
  `examples/specdec_bench/specdec_bench/metrics/acceptance_rate.py`:
  - mean and per-request acceptance length (AL),
  - AL histogram,
  - conditional acceptance rate per draft position,
  - joint acceptance rate per position.
- Source the counters from the running server, not a separate offline engine:
  - vLLM: the Prometheus `/metrics` endpoint (`vllm:spec_decode_num_draft_tokens_total`,
    `vllm:spec_decode_num_accepted_tokens_total`, and the per-position accepted-tokens
    counter). Read them before and after the benchmark and diff.
  - SGLang: `spec_accept_length` in server logs / metrics. Per-position counters may not
    exist there; if so, report only mean AL for SGLang.
  Confirm metric names against the pinned framework versions; they have been renamed
  before.
- Feed AL and per-position acceptance into the speculative specialist's next proposal, so
  that it can shorten the draft length when later positions rarely accept.
- Adopt ModelOpt's EAGLE-3 review threshold (AL ≥ 2.1 on MT-Bench, from
  `plugins/modelopt/skills/speculative-decoding/references/algorithms/eagle3.md`) as an
  advisory Critic signal, not a hard gate.

### Acceptance criteria
- [ ] AL and per-position acceptance are persisted per speculative candidate.
- [ ] The Critic prompt receives them.
- [ ] Parser tests use recorded vLLM and SGLang metric dumps.

### Expected impact
Makes speculative-decoding search informed rather than blind, and cuts wasted
benchmarks.

---

## [HL-07] Offline EAGLE-3 draft training pipeline on ROCm
<!-- labels: type:feature, domain:inference, area:specdec, priority:P1, source:modelopt -->

### Problem / use case
When no public draft exists for the target model, HL-05 can only fall back to n-gram.
ModelOpt has a complete, hardware-agnostic draft-training pipeline; only its TRT-LLM
hidden-state dumper and NIXL streaming path are NVIDIA-specific.

### Proposed solution
Add an optional prelude job, `--train-draft eagle3`, modelled on the existing quantization
prelude:

1. Build the dataset with `examples/dataset/make_dataset.py`.
2. Regenerate answers with the target served on vLLM-ROCm
   (`examples/speculative_decoding/scripts/server_generate.py`) so that the draft learns
   the target's own distribution.
3. Collect hidden states with the HF or vLLM backends
   (`collect_hidden_states/compute_hidden_states_{hf,vllm}.py`).
4. Train with `launch_train.sh --config modelopt_recipes/general/speculative_decoding/eagle3.yaml`.
5. Optionally compress the draft vocabulary (`scripts/calibrate_draft_vocab.py`).
6. Export and convert for vLLM (`scripts/export_hf_checkpoint.py`,
   `scripts/convert_to_vllm_ckpt.py`).
7. Hand the draft path to HL-05.

Use ModelOpt as a pinned dependency rather than a vendored copy. Its training path is
plain PyTorch/HF, but confirm that it installs on ROCm torch without the CUDA extensions.

**Scope and cost.** This is the most expensive issue in the backlog:
- Training needs a full GPU node for hours to days (ModelOpt's EAGLE-3 recipes assume
  8 GPUs with FSDP2), and offline hidden-state collection can need terabytes of disk.
  The vLLM-based collector (`compute_hidden_states_vllm.py`) needs a vLLM build that
  can return hidden states; on ROCm, use the HF collector first.
- It must run as a **separate offline job**, not inside a session's time budget. The
  session only consumes the resulting draft path.
- Do this only after HL-05 has shown that a *public* draft gives a measurable gain on
  ROCm; if HL-05 finds no gain, this issue is moot.

### Acceptance criteria
- [ ] The pipeline runs end to end on one MI300X node for an 8B model, with budget and
      disk requirements documented. Offline hidden states can need terabytes of disk.
- [ ] AL is reported on MT-Bench (HL-06), along with end-to-end TPOT gain (HL-05).
- [ ] The trained draft is registered in the recipe KB so later sessions can reuse it.

### Expected impact
Brings speculative decoding to models with no public draft. This is a high-effort item.

### Additional context
Depends on HL-05, HL-06. `modelopt/torch/speculative/`, `examples/speculative_decoding/`.

---

## [HL-08] Evaluate DFlash block-diffusion drafters on ROCm
<!-- labels: type:task, domain:inference, area:specdec, priority:P3, source:modelopt -->

### Problem / use case
ModelOpt's DFlash (`modelopt/torch/speculative/plugins/hf_dflash.py`,
`examples/speculative_decoding/doc/dflash.md`) predicts a whole block of tokens in one
forward pass. It reports the highest speculative speedups in the repo (3.1× at TP=1 and
AL 3–5 on H100 with vLLM).

**What is known:** ModelOpt's own docs (`examples/speculative_decoding/doc/dflash.md`)
validate DFlash only on **vLLM nightly (v0.19.1+) on H100**. `specdec_bench`'s vLLM
wrapper lists EAGLE, EAGLE3, NGRAM and DRAFT_TARGET but not DFlash, and there is no
documented SGLang path in the ModelOpt repo. ROCm support is unknown. Treat this as a
low-cost probe, not a planned feature.

### Proposed solution
Run a spike, time-boxed to one day:

- Confirm the pinned vLLM-ROCm version is ≥ the version that added `method: dflash`;
  if not, stop and note the version gap.
- Try `--speculative-config '{"method":"dflash",...}'` on vLLM-ROCm with a published
  DFlash draft (Qwen3-8B has one). Skip SGLang unless upstream has added it.
- Measure with HL-06.
- If the kernels are missing, file the upstream issue and decide whether it is a
  KernelForge target.
- If it works, add `dflash` to the HL-05 method set and the HL-07 training recipes
  (`modelopt_recipes/general/speculative_decoding/dflash.yaml`).

### Acceptance criteria
- [ ] Written result: supported, unsupported (with the upstream issue link), or needs
      kernels.
- [ ] If supported, measured AL and TPOT on one model.

---

## [HL-09] Make quantization an in-loop lever with KEEP/REVERT
<!-- labels: type:feature, domain:inference, area:quantization, priority:P0, source:modelopt -->

### Problem / use case
Quantization is a one-shot prelude (`src/hyperloom/agents/quantization/`,
`orchestrator/phases/quantization_request_handlers.py`):

- It is gated by `HYPERLOOM_QUANTIZE_ENABLED=1` and rewrites `--model`.
- It never runs on resume.
- It is not graded on throughput or latency, so there is no KEEP/REVERT and no
  comparison between schemes (`fp8`, `ptpc_fp8`, `mxfp4`, `mxfp4_fp8`).

The user has to guess the right scheme up front.

### Proposed solution
- Add a `quantize` action in FRAMEWORK_AGENT. It produces a checkpoint per scheme, with a
  cache keyed by (model, scheme, calibration settings), and benchmarks it like any other
  candidate.
- The accuracy gate (HL-14) plus the performance gate decide KEEP.
- Order candidates by expected value: FP8 first, then PTPC-FP8, then MXFP4 variants on
  MI355X. Stop early when a candidate fails accuracy.
- Keep the prelude as a fast path when the user pins a scheme.
- **Budget and caching.** Quantizing a 70B model can take hours and a full node. The
  action must charge its wall-clock to the session budget, and the exported checkpoint
  must be cached under `USER_DATA_PATH` keyed by (model hash, scheme, calibration
  settings) so that resume and later sessions never re-quantize. Limit the in-loop
  search to schemes whose quantization time fits the remaining budget.
- **Baseline handling.** A kept quantized checkpoint changes the model, so the
  profile/roofline from PRELUDE is stale. Re-run `profile` after a quantization KEEP
  before KERNEL_AGENT starts.
- Follow ModelOpt's pattern of treating precision as a searched recipe rather than an
  input (`plugins/modelopt/skills/quant-recipe-search/`,
  `plugins/modelopt/skills/day0-release/`, which returns
  ACCEPT/REGRESSION/ANOMALOUS/INFEASIBLE).

### Acceptance criteria
- [ ] The `quantize` action has a PolicyGate allowlist entry and a ledger fingerprint so
      schemes are not re-quantized.
- [ ] A kept quantized checkpoint becomes the new baseline model for later phases, and
      its KB row stores the scheme.
- [ ] A demo on MI300X compares BF16, FP8, and PTPC-FP8 for throughput, TPOT, and
      accuracy.

### Expected impact
Turns the biggest memory-bandwidth lever into something Hyperloom can search and verify.

### Additional context
Blocks HL-10, HL-12. Depends on HL-14 for a trustworthy accuracy gate.

---

## [HL-10] AutoQuantize-style per-layer mixed precision (sensitivity scoring + budgeted solver)
<!-- labels: type:feature, domain:inference, area:quantization, priority:P1, source:modelopt -->

### Problem / use case
`QuantizationConfig` already has `layer_overrides` and `exclude_layers`
(`orchestrator/phases/quantization_schemes.py`), but `resolve_scheme_prompt()` fills in
only `global_scheme` and the CLI exposes nothing per-layer. When MXFP4 everywhere fails
accuracy, the fallback is FP8 everywhere, which leaves most of the MXFP4 gain unused.

### Proposed solution
Port the core of ModelOpt AutoQuantize (`modelopt/torch/quantization/algorithms.py`,
`_auto_quantize_cost.py`, `_auto_quantize_shapley.py`). The searcher is hardware-agnostic
PyTorch:

- **Search space.** Each quantizable Linear or expert group is one choice among
  {MXFP4, FP8, PTPC-FP8, BF16}. Use grouping rules that match vLLM-ROCm/SGLang fusion:
  q/k/v, gate/up, and per-layer experts (see `quant_grouping_rules`).
- **Sensitivity score.** Start with the forward-only `kl_div` method, which needs no
  labels and no backward pass. Add the gradient/Fisher method later.
- **Cost model.** Use effective bits per format: MXFP4 is about 4.25 bits with e8m0
  scales per 32 elements. Include the `active_moe` cost model for MoE, where routed
  experts are weighted by top_k/num_experts.
- **Solver.** Minimize total sensitivity under an effective-bits budget, using an ILP with
  lower-bound retries.
- **Output.** Emit a Quark per-layer quantization config (Quark's layer-specific config
  mechanism), not ModelOpt's `quant_method: modelopt` config, so that vLLM-ROCm loads
  the checkpoint through the Quark path. Note that Hyperloom's existing
  `QuantizationConfig.layer_overrides` is only rendered into *prompt text* for the Quark
  skill (`quantization_schemes.py:_strategy_paragraph`); this issue needs a structured
  path from the solver's assignment to Quark's config, not free text.
- **Scoring on ROCm.** ModelOpt's fake-quant CUDA extensions do not build on ROCm.
  Score with plain-torch emulation instead: FP8 is a `float8_e4m3` cast (mind
  e4m3fnuz on MI300), and MXFP4 emulation (block-32, e8m0 scale) is a few lines of
  torch. Quark's own fake-quant modules are the other option. Scoring cost is
  O(#groups × #formats) forwards per calibration batch for `kl_div`; cap
  `score_size` to keep it under an hour on one node.
- **Loop.** Expose the effective-bits budget as a searched knob in HL-09. For example, try
  4.5, 5.5, and 6.5 bits and KEEP the fastest that passes accuracy.

### Acceptance criteria
- [ ] Sensitivity scoring and the solver work on one dense model and one MoE model on
      MI355X.
- [ ] The mixed checkpoint loads in vLLM-ROCm and passes HL-14.
- [ ] Throughput, TPOT, and accuracy are compared for global FP8, global MXFP4, and mixed
      precision at the chosen budget.

### Expected impact
Recovers most of the MXFP4 speedup on models where global MXFP4 fails accuracy.

### Additional context
Depends on HL-09. ModelOpt recipes: `modelopt_recipes/general/auto_quantize/*.yaml`.

---

## [HL-11] Default quantization exclusion list and MoE calibration coverage
<!-- labels: type:feature, domain:inference, area:quantization, priority:P1, source:modelopt -->

### Problem / use case
The Quark prelude relies on Quark defaults and free-text `exclude_layers`. ModelOpt keeps
a curated, commented list of modules that must stay high precision. Rarely routed MoE
experts also get few or no calibration tokens, which yields bad scales.

### Proposed solution
- Port the patterns in ModelOpt
  `modelopt_recipes/configs/ptq/units/default_disabled_quantizers.yaml` into a Hyperloom
  default `exclude_layers` set passed to Quark:
  - `lm_head`, routers and gates (`*router*`, `*mlp.gate.*`, `*shared_expert_gate*`),
  - linear-attention and Mamba `conv1d`,
  - MTP heads (`mtp.*`),
  - vision towers and projectors.
  Keep the inline reasons.
- Port the idea behind `moe_calib_experts_ratio` (`modelopt/torch/quantization/config.py`):
  temporarily raise top_k during calibration so every expert sees tokens, and report
  tokens per expert. First check whether Quark supports it; if not, raise it upstream
  with Quark per the "fix upstream" rule, and ship the exclusion list alone under this
  issue. The two halves are independent; do not block the exclusion list on the Quark
  change.

### Acceptance criteria
- [ ] The default exclusions apply unless the user overrides them, and the exclusions
      actually applied are logged in the quantization outcome.
- [ ] Per-expert calibration token counts are reported for MoE models.
- [ ] An A/B test of accuracy on one MoE model runs with and without the coverage fix.

### Expected impact
Fewer quantization accuracy failures, which in turn means more KEEPs in HL-09.

---

## [HL-12] Calibrated KV-cache quantization
<!-- labels: type:feature, domain:inference, area:quantization, priority:P1, source:modelopt -->

### Problem / use case
KV quantization means only `--kv-cache-dtype fp8_e4m3` with default (unit) scales. It is
listed as a serving lever that needs an accuracy check
(`specialist_prompt_builder.py`), and `quantization_schemes.py` says "only fp8
supported today". There are no calibrated scales, and no FP4 KV on MI355X. KV bandwidth
dominates decode at long context and high concurrency.

### Proposed solution
- Add two KV variants that the loop can try:
  - `fp8_cast` uses constant scales and needs no calibration. This is what
    `--kv-cache-dtype fp8_e4m3` does today on a checkpoint without scales, and it is
    ModelOpt's safe default.
  - `fp8_calibrated` uses per-layer K/V amax scales from a short calibration pass.
    Quark already supports `kv_cache` FP8 with exported `k_scale`/`v_scale`, and
    Hyperloom's `QuantizationConfig.kv_cache` field exists but is never set by the CLI.
    So the work is: (1) expose it, (2) make the loop pair the flag with a checkpoint
    that carries scales, (3) verify vLLM-ROCm and SGLang actually read those scales
    for the chosen attention backend (some backends ignore them silently).
  - This variant is only available when HL-09 has produced a Quark checkpoint; on a
    BF16 model only `fp8_cast` applies.
- Reference: ModelOpt KV presets `modelopt_recipes/configs/ptq/units/kv_fp8*.yaml` and
  `kv_cache_auto_quant.py`, which also searches KV precision per layer with a `kv_cache`
  cost model.
- Spike (optional, MI355X only): FP4/MXFP4 KV. No ROCm attention backend is known to
  read an FP4 KV cache today, so this is a "does any kernel exist" check, not an
  implementation. If none exists, close the spike with a note; do not build a kernel
  under this issue.

### Acceptance criteria
- [ ] `fp8_calibrated` is produced and loaded on vLLM-ROCm, and compared with `fp8_cast`
      on accuracy (HL-14) and on long-context TPOT.
- [ ] The KV variant is recorded in the KB `best_config`.
- [ ] The FP4 KV spike outcome is written up.

### Expected impact
Better accuracy when KV is FP8, so FP8 KV is kept more often. That brings decode speedups
at long ISL and high concurrency.

---

## [HL-13] Composable quantization recipes and a calibration escalation policy
<!-- labels: type:feature, domain:inference, area:quantization, area:recipe-kb, priority:P2, source:modelopt -->

### Problem / use case
Quantization intent is free text sent to Quark, which is hard to reproduce, deduplicate,
or reuse across sessions. The agent also has no policy for what to try next when a
scheme fails accuracy.

### Proposed solution
- Adopt ModelOpt's recipe model (`modelopt/recipe/config.py`, `loader.py`,
  `modelopt_recipes/`):
  - small YAML units (numerics, exclusions, KV) composed with `imports`,
  - three tiers: `general/`, `model_type/<hf model_type>/`, and `models/<org>/<ckpt>/`
    for architecture-specific deltas.
- Hyperloom recipes map to Quark configs, get a stable fingerprint for the ledger, and are
  stored in the recipe KB (see HL-15).
- Encode ModelOpt's decision guide (`modelopt_recipes/ptq.md`) as the agent's escalation
  policy after an accuracy failure:
  1. Narrow scope, for example experts only for MoE or MLP only for dense.
  2. Switch the calibration algorithm, roughly max → MSE → AWQ/GPTQ, mapped to Quark's
     algorithms.
  3. Fall back to a higher precision for the failing groups (HL-10).

### Acceptance criteria
- [ ] Recipe schema, loader, and at least the `general` tier recipes for fp8, ptpc_fp8,
      mxfp4, and mxfp4_fp8.
- [ ] The escalation policy is in the quantization specialist's prompt, and a test
      verifies the escalation order after a failure.

---

## [HL-14] Configurable, multi-signal accuracy gate
<!-- labels: type:feature, domain:inference, area:accuracy, priority:P1, source:modelopt -->

### Problem / use case
- The serving accuracy gate is one GSM8K run with a hard-coded
  `ACCURACY_THRESHOLD = 0.05` absolute drop
  (`orchestrator/actions/executors/_accuracy_gate.py:25`). The threshold is not
  configurable.
- The quantization prelude uses a separate 3% relative gap in Quark llm-eval.
- There is no multi-task evaluation and no logit-divergence check.
- `DEFAULT_ENABLEMENT_ACCURACY_FLOOR = 0.5` in code, but
  `docs/reference/environment-variables.md` says 0.05.

Once HL-05 and HL-09 to HL-12 add model-changing levers, a single GSM8K score is too weak
a guard.

### Proposed solution
- Make the threshold configurable, and unify the absolute/relative semantics between the
  serving gate and the quantization gate.
- Add optional tasks through lm-eval (MMLU and a long-context task), selected per model
  type. ModelOpt reference: `examples/llm_eval/` (`lm_eval_hf.py`, `mmlu.py`,
  `run_lm_eval_vllm.sh`).
- Add a cheap logit-divergence check against the baseline server on a fixed prompt set.
  It is sensitive to the small regressions that GSM8K misses and much cheaper than a
  full eval. ModelOpt's AutoQuantize `kl_div` method uses the same signal.
  - **What is measurable through the serving API:** vLLM and SGLang expose only top-k
    log-probabilities per position (`logprobs` / `top_logprobs`, usually k ≤ 20), not the
    full distribution. So implement a *truncated* KL over the baseline's top-k, plus
    top-1 agreement rate, with the same fixed prompts and `temperature=0` on both
    servers. Full KL is not available without a Python-level model hook, which is out
    of scope here.
  - Record the baseline's top-k logprobs once per session (in PRELUDE) and compare
    every candidate against that file; do not keep the baseline server alive.
  - Thresholds must be calibrated on the noise floor: run baseline vs baseline twice
    and set the gate above the observed divergence.
- Fix the doc/code mismatch on the enablement floor.

### Acceptance criteria
- [ ] Threshold and task set are configurable at the CLI and env boundary and
      documented.
- [ ] The divergence check runs per candidate and is recorded in the ledger.
- [ ] Tests pin the gate decision for pass, fail, and a missing metric.

### Expected impact
Gives trustworthy KEEP decisions for quantization and speculative-decoding candidates.

---

## [HL-15] Recipe KB: store latency Pareto points and model-level recipes
<!-- labels: type:feature, domain:inference, area:recipe-kb, priority:P2 -->

### Problem / use case
A `Recipe` in `orchestrator/knowledge/recipe_kb/schema.py` stores one `best_throughput`
and a `best_config` of server args and envs. It has no latency axes, no per-concurrency
points, no quantization recipe, no speculative-decoding draft, and no accuracy score.
Warm starts cannot pick the best recipe for a latency SLO.

### Proposed solution
- Extend `Recipe` (versioned, with migration) with:
  - `operating_points`: a list of {conc, isl, osl, dataset, output_tput, ttft_p90,
    tpot_p90, itl_p90, AL},
  - `model_recipe`: {quant recipe fingerprint (HL-13), kv variant (HL-12), draft path and
    method (HL-05/07)},
  - `accuracy`: {tasks, scores, divergence}.
- T0 warm-start lookup (`recipe_kb_t0.py`) ranks by the session's objective: throughput,
  or the SLO from HL-01.

### Acceptance criteria
- [ ] Schema version bump with backward-compatible reads of existing rows. The KB is
      persisted data, so compatibility is owed here.
- [ ] The CLOSE writer fills the new fields.
- [ ] A warm start in latency mode picks the latency-optimal row in a test.

---

## [HL-16] Per-operating-point tuning in SWEEP (latency configs at low CONC, throughput configs at high CONC)
<!-- labels: type:feature, domain:inference, area:objective, area:benchmark, priority:P1 -->

### Problem / use case
SWEEP (`orchestrator/kernel/conc_sweep.py`, `DEFAULT_CONCS=[256,…,2]`) re-measures the
*final* stack across concurrencies for reporting only. A stack tuned at CONC=64 is rarely
latency-optimal at CONC=1–8. Speculative decoding, smaller `max-num-batched-tokens`, and
graph-capture sizes all shift with batch size.

### Proposed solution
- Let SWEEP run a small re-tune per operating-point bucket, covering levers that are
  cheap to switch (spec-decode on/off and draft length, chunked-prefill size, graph
  capture sizes).
- Emit one recommended config per bucket, for example latency (CONC ≤ 8), balanced, and
  throughput.
- **Budget.** A per-bucket re-tune multiplies benchmark cost. Cap it: at most N
  candidates per bucket (default 3), only the cheap-to-switch levers, and skip the
  re-tune when the remaining session budget is below a threshold. The existing "skip
  SWEEP when the validated gain has not moved" rule stays.
- **Output contract.** The session's single `best_config` stays as is (it is what the
  KB and reports consume today); per-bucket configs are an additional field, so
  existing consumers keep working.
- ModelOpt's serving harness sweeps concurrency from 1 to 512 with a separate artifact per
  point. Hyperloom would additionally *optimize* per point.

### Acceptance criteria
- [ ] SWEEP output contains per-bucket best configs with their latency and throughput
      metrics.
- [ ] Each bucket respects the HL-01 SLO.
- [ ] KB rows store the per-bucket configs (HL-15).

### Additional context
Depends on HL-01, HL-02. Most useful together with HL-05.

---

## [HL-17] Skip-softmax / N:M sparse attention for long-context prefill (KernelForge target)
<!-- labels: type:feature, domain:inference, area:kernel, priority:P2, source:modelopt -->

### Problem / use case
Hyperloom has no sparsity levers, and grep finds no sparse kernels in KernelForge. TTFT
at long ISL is attention-bound.

### Proposed solution
Evaluate ModelOpt's attention sparsity (`modelopt/torch/sparsity/attention_sparsity/`):

- **`triton_skip_softmax` (BLASST, arXiv 2512.12087).** Skips KV tiles whose max score is
  below the running max plus ln(λ). The threshold is calibrated per sequence length
  (`calibration/ruler_dataset.py`).
- **`triton_sparse_softmax`.** N:M on attention scores, keeping dense sink and recent
  tokens.

The kernels are Triton (`modelopt/torch/kernels/common/attention/triton_fa.py`,
`kernels/sparsity/attention/`), so they are a natural KernelForge Triton or FlyDSL port
target on ROCm. The vLLM adapter must be re-targeted from FA/FlashInfer to
`TRITON_ATTN` or `ROCM_AITER_FA`. Known limits are eager-only and no speculative
decoding, so make it prefill-only first.

**Do not** port 2:4 weight sparsity. It has no ROCm serving GEMM path, and it needs
fine-tuning to recover accuracy.

### Acceptance criteria
- [ ] Spike: the Triton skip-softmax kernel compiles and runs on MI300X, and TTFT is
      measured at ISL 16k/32k/64k against baseline. Start with the kernel in
      isolation (a KernelForge micro-benchmark against the `TRITON_ATTN` prefill
      kernel), before any vLLM integration.
- [ ] The vLLM integration, if attempted, targets `TRITON_ATTN` only; the AITER
      backends are HIP/assembly and are out of scope for a Triton port.
- [ ] Accuracy on a long-context task passes the HL-14 gate.
- [ ] Go/no-go on integrating it as a KernelForge rewrite plus a vLLM-ROCm attention
      patch.

---

## [HL-18] Diffusion step caching for xDiT, with a distributional quality gate
<!-- labels: type:feature, domain:inference, area:xdit, priority:P2, source:modelopt -->

### Problem / use case
The xDiT path locks precision to BF16 and has no step caching.
`inference_optimizer/assets/configs/baseline_xdit.yaml` explains why:
"feature-level, step-skipping optims (fbcache/teacache) diverge per-image and can only be
validated distributionally (FID), which is not yet wired up here." The per-image
LPIPS/SSIM/MSE gate rejects any caching.

### Proposed solution
1. Add a distributional quality gate: FID and CLIP score over a fixed prompt set of about
   200–1k prompts, compared with the BF16 baseline. It is used only for levers flagged
   `distributional`.
2. Add training-free step caching as a searched lever. **Use xDiT's own FBCache /
   TeaCache** as the mechanism: ModelOpt's `examples/diffusers/cache_diffusion/` is
   built around UNet models (its default config is SDXL) and DeepCache-style block
   caching, which does not transfer to the DiT models xDiT serves. Use ModelOpt only as a
   design reference for how the cache-selection policy is expressed per step.
   Searched knobs: cache threshold (residual-diff), warm-up steps, and which blocks are
   cached.
3. Later: few-step distilled students (ModelOpt `modelopt/torch/fastgen`, DMD2) as an
   offline model variant (HL-19).

### Acceptance criteria
- [ ] FID/CLIP gate implemented and documented, with thresholds justified on a BF16
      re-run noise floor. FID on 200–1k images is itself noisy; the acceptance
      criterion must state the sample size and the noise band measured on two BF16
      runs.
- [ ] The gate's cost is bounded: generating 1k images per candidate may be longer than
      the benchmark itself, so the lever must be tried with a small image set first and
      the full set only on a provisional KEEP.
- [ ] Step caching measured on one xDiT model for img/s and E2E latency against the
      quality gate.

---

## [HL-19] Offline model-variant track: pruned + distilled checkpoints as candidates (research)
<!-- labels: type:feature, domain:inference, domain:training, area:model-compression, priority:P3, source:modelopt -->

### Problem / use case
Hyperloom optimizes a fixed model. ModelOpt's Megatron-Bridge tutorial for
Nemotron-3-Nano-30B-A3B
(`examples/megatron_bridge/tutorials/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/`) reports these
vLLM throughput gains on H100:

| Stage | Gain |
|---|---|
| Minitron prune + distill | 2.0× |
| Plus FP8 | 2.6× |

These are architecture-level wins that no serving flag can reach.

### Proposed solution
Research issue, not an in-loop lever: distillation costs about 100B tokens.

- Define how an *offline model variant* enters Hyperloom: a pruned or distilled HF
  checkpoint registered in the KB with its accuracy, then optimized by the normal loop.
- Evaluate Puzzletron's latency-in-the-loop MIP (`modelopt/torch/puzzletron/`, with
  `runtime_vllm.py` measuring real vLLM latency per candidate block). Its "search
  architecture against measured serving latency" design mirrors Hyperloom's loop and
  could use Hyperloom's benchmark harness on ROCm.
- Check ROCm readiness of the training stacks involved: Megatron-Bridge and ModelOpt
  distill plugins. Neither repo documents a ROCm training path; if Megatron-Bridge does
  not run on ROCm, the HF/accelerate distillation path (`examples/llm_distill/main.py`)
  is the fallback, at lower scale.
- This issue produces a **design note only**. Do not start a pruning or distillation
  run under it; a run is its own issue with its own budget, once the note is accepted.

### Acceptance criteria
- [ ] Design note on the model-variant contract (KB fields, accuracy provenance) and a
      go/no-go recommendation.

---

## [HL-20] Host-side overhead: measure GPU idle time and make it a first-class search target
<!-- labels: type:feature, domain:inference, area:host-overhead, priority:P1 -->

### Problem / use case
The ground-truth runs in HL-B0 show the GPU idle for **about half the time** on a single-GPU
Qwen3-8B vLLM workload. The step-4 roofline trace (TraceLens, 1718 ms steady-state window) reports
49.15% compute and 50.85% idle, and the GEMMs, which are 74.6% of compute, already run at 60–82% of the
708 TFLOPS BF16 roofline. The largest remaining opportunity is therefore host-side: kernel launch and
dispatch overhead, scheduling, and CPU work between steps. It is not kernel efficiency.

Hyperloom already has the pieces, but they don't drive the search:

- `system_specialist` (launch/dispatch overhead, host-blocking calls, KFD/driver env vars, `numactl`)
  and `serving_specialist` (scheduler, CUDA graphs, batching, chunked prefill, `max-num-seqs`) exist
  in `orchestrator/specialists/domains.py`, and `roofline_snapshot.py` routes `idle` and
  `host_overhead` bottlenecks to `system_specialist`.
- In practice, candidate discovery followed the roofline's compute-bound verdict. Round 1 went to AITER
  and GEMM levers, host-side variants came in round 2, and the settings phase ended at +1.92%, inside
  the noise band. The smoke run found +14.46% mainly from two levers that fill idle time: FP8 KV cache
  (+12.1%, more concurrent requests) and `FULL_DECODE_ONLY` CUDA graphs (fewer launches). The
  roofline-driven run never proposed FP8 KV.
- No record shows GPU idle % per candidate, so nothing tells whether a kept change shrank the gap.

### Proposed solution
Extend the framework agent's existing loop; do not add an agent or a phase. Host-side levers are
applied the same way as other framework levers (server args and env vars, KEEP/REVERT), and a new
phase would compete for the same wall-clock budget that already starves KERNEL_AGENT.

1. **Measure.** Carry GPU busy % and idle % from the PRELUDE trace into `session_breakdown.json`, and
   measure them again for kept candidates when a trace is taken. Put them in the HL-B0 experiment
   records next to throughput and latency.
2. **Prioritise by the idle signal.** When idle % is high (threshold to be set from data, e.g. > 30%),
   candidate discovery ranks host-side and capacity levers first, next to the compute-bound
   recommendations rather than after them.
3. **Cover the host-side levers explicitly** in `system_specialist` / `serving_specialist`:
   - CUDA-graph mode and capture sizes;
   - async scheduling;
   - `max-num-seqs` and `max-num-batched-tokens`;
   - chunked-prefill size;
   - KV-cache capacity (FP8 KV, coordinated with HL-12's calibrated KV quantization);
   - CPU/NUMA affinity of the serving process (`numactl`, cores local to the GPU).
4. **Diagnose what is not software.** A one-off check of how much of the idle share comes from CPU
   frequency scaling: the ground truth runs with the `powersave` governor. It needs root on the host,
   so it is a manual diagnosis, never an autonomous lever, and the ground truth keeps `powersave`.

Out of scope here: per-concurrency tuning of the same levers, which is HL-16. HL-20 makes the idle
signal drive the search; HL-16 tunes the result per operating point.

### Acceptance criteria
- [ ] GPU busy % / idle % appear in `session_breakdown.json` for the PRELUDE trace, and in every
      HL-B0 experiment record.
- [ ] With a high idle share, the first framework explore round includes at least one host-side or
      capacity candidate (verified on `ref-dense-bf16`).
- [ ] Each lever in item 3 can be proposed, benchmarked and kept or reverted, with the idle % change
      recorded for kept candidates.
- [ ] The governor diagnosis is written up: idle % and throughput under `powersave` vs `performance`
      on the same workload.
- [ ] On `ref-dense-bf16` and `ref-latency`, the gain against ground truth is outside the noise band,
      or the record explains why not (`inconclusive`).

### Expected impact
The step-4 profile puts the ceiling for this work well above what kernel tuning can reach on these
workloads (GEMMs are within about 20–40% of their roofline; the GPU is idle for half the time). The
smoke run's +14.46% came almost entirely from idle-filling levers.

---

## [HL-21] Cut the per-candidate cost of the framework search (accuracy eval at workload concurrency)
<!-- labels: type:feature, domain:inference, area:search, priority:P1 -->

### Problem / use case
In the HL-B0 runs, the framework stage tested 8–11 candidates in 1.5–2 h on the CONC-64 workload,
and only **2–4** on the CONC-4 workload. Each candidate gets two measurements. The second, on the
warm server, takes about 1–2 minutes. The first takes **about 8.5 minutes at CONC 64 and about
31 minutes at CONC 4**, although the CONC-4 benchmark window itself is only **34 s** (20 prompts).
Example: `aiter_on` ran 00:33:32 → 01:05:11, then 01:05:11 → 01:06:19.

The first measurement is: server restart, benchmark, and the GSM8K accuracy run (`RUN_EVAL: 'true'`
in the baseline config). The baseline shows the eval runs at the workload's concurrency. Its warmup
round took 31 min, and the measured round, on the same warm server, took 1 min. So at low
concurrency, the accuracy check, not the benchmark, decides how many candidates fit in the budget.

### Proposed solution
1. **Measure first:** record the time breakdown of every candidate (server start, benchmark,
   accuracy eval) in `session_breakdown.json`.
2. **Run the accuracy eval at its own concurrency,** independent of the workload's CONC. The eval
   checks correctness, not serving performance, so it does not need the benchmark's concurrency.
3. **Order the gates:** benchmark first, and run the accuracy eval only for candidates that would
   be kept on performance. A candidate that loses on speed is reverted without an eval. #4 (the
   coherence gate) still catches broken outputs cheaply before the benchmark.
4. **Check the restart cost:** confirm the vLLM compile and graph caches are reused across
   candidates, and how long a restart takes on its own.

### Acceptance criteria
- [ ] Per-candidate time breakdown in `session_breakdown.json`.
- [ ] On `ref-latency`, a 3 h settings-only run tests at least 3× as many candidates as the HL-B0
      runs (2–4), with the same accuracy protection on every kept candidate.
- [ ] On `ref-dense-bf16`, the median time per candidate drops measurably (HL-B0: 10.4–12.2 min).
- [ ] No candidate is kept without an accuracy result.

---

## [HL-22] Keep PRELUDE within its budget and spend the whole phase budget
<!-- labels: type:feature, domain:inference, area:search, priority:P1 -->

### Problem / use case
PRELUDE's planned share is about 3% of the wall clock. In the HL-B0 runs it took **36–50 min**
(CONC 64) and **74–87 min** (CONC 4) of a 180-min budget. On gpt-oss-120b it took about 2 h of 6 h.
Everything after it gets the remainder:
- in the default chain, KERNEL_AGENT got 30 min and ~1 min instead of about 85, and kept nothing;
- PRELUDE's profiling run repeats the full GSM8K evaluation the baseline has already done (Qwen
  CONC 4: 38 min; gpt-oss: still running after 50+ min);
- at the other end, phases end with work left undone. In the smoke run, explore rounds 6–8 were
  queued but never dispatched once the phase budget hit 0 (orchestration alert: "queued explore
  tasks appear to be admitted but never dispatched").

### Proposed solution
1. Do not run the accuracy eval in PRELUDE's profiling run: the baseline already has the score.
2. Measure each PRELUDE step's duration against its share, and re-plan the downstream phase
   budgets from the actual remaining time, not the planned shares.
3. When a phase ends with budget-limited tasks still queued, either dispatch them if the remaining
   session time allows, or record them as skipped. Never drop them silently.

### Acceptance criteria
- [ ] PRELUDE's profiling run makes no GSM8K call.
- [ ] `session_breakdown.json` reports each phase's planned vs actual minutes.
- [ ] On `ref-dense-bf16` and `ref-latency`, PRELUDE drops measurably below the HL-B0 times (36 / 74 min).
- [ ] No queued explore task is dropped without a recorded reason.

---

## [HL-23] Noise-aware keep threshold for framework candidates
<!-- labels: type:feature, domain:inference, area:search, priority:P1 -->

### Problem / use case
Hyperloom kept `aiter-linear-rmsnorm-async` at **+0.6%** on `ref-dense-bf16`, whose measured
run-to-run noise is about ±1.5–1.9% (HL-B0). Noise-level "wins" become the base for the next
round, so every later candidate is compared against a lucky high reading, and real small gains can
be rejected. The AgentX mode uses a 3–5% bar (`common/perf_metric.py`); the default mode evidently
accepts much less. With two measurements per candidate and ~4% noise at CONC 4, a real 3% gain can
not be told apart from chance.

### Proposed solution
1. Estimate the noise band in PRELUDE, from the baseline's warmup and measured rounds plus one
   extra cheap warm repeat, or take it from a supplied reference (`baselines/`).
2. KEEP only when the gain exceeds that band. For a candidate inside the band but promising, add
   warm repeats, which cost 1–2 min each on the warm server, before deciding.
3. Record the band, the threshold used, and the number of repeats per decision.

### Acceptance criteria
- [ ] Each KEEP/REVERT in the records shows the threshold and repeat count it used.
- [ ] Replaying the HL-B0 settings-only runs' decisions, the +0.6% keep is no longer a KEEP.
- [ ] A known real lever (`--kv-cache-dtype fp8`, +13% on `ref-dense-bf16`) is still kept.

---

## [HL-24] Warm replay accepts a recipe below its own threshold and replays it partially
<!-- labels: type:bug, domain:inference, area:recipe-kb, priority:P2 -->

### Problem / use case
In the HL-B0 noise runs, which used a shared KB still holding the smoke run's recipe (FP8 KV +
`FULL_DECODE_ONLY`, +14.46%):

- PRELUDE logged `warm-replay REPRODUCED: measured=+0.64% (expected=+14.46%, min_required=+11.57%);
  pushed warm_replay onto stack`. The measured gain was far below the required one, yet the replay
  was accepted and stacked.
- The replayed stack was `--compilation-config {"cudagraph_mode":"FULL_DECODE_ONLY"}` only. The FP8
  KV part of the recipe was missing, which explains the +0.64%.

### Proposed solution
Find why the reproduce check passed below `min_required`, and why the replayed overlay dropped the
`--kv-cache-dtype` argument. Fix both, with tests that replay a two-lever recipe.

### Acceptance criteria
- [ ] A warm replay below `min_required` is rejected and recorded as not reproduced.
- [ ] Replaying a recipe applies every lever in it; a test covers a KV-dtype + compilation-config recipe.

---

## [HL-25] Resume drops a finished GEAK result and skips to SWEEP
<!-- labels: type:bug, domain:inference, area:kernel, priority:P1 -->

### Problem / use case
In the gpt-oss-120b full run (1 Oct, session `20261001T044820Z-b30c5cdf`, TP 1, CONC 64), the run was
stopped at 10:05 UTC by the plan-usage limit while GEAK was in its KERNEL delegation. GEAK kept running and
wrote `geak/result.json` at about 10:21: `status: ok`, `throughput_speedup: 1.207`, `output_parity: pass`,
with a deployable overlay.

The run was resumed with `--resume-from <session> --extend-hours 1`:

- `resume: re-entering KERNEL GEAK delegation (no completion evidence on the current phase row);
  recover-from-disk or re-run.` (12:47:48)
- 0.4 s later: `KERNEL_AGENT → SWEEP (reason=kernel_no_more_leverage)`. `state.json` shows
  `last_consumed_escalate_hint: skip_to_sweep` at that moment.

The crash-recovery branch in `orchestrator/phases/kernel.py` (promote `result.json`, then
`_revalidate_geak_candidate`) did not take effect: the best stayed at the framework result (+2.75%) and SWEEP
measured that config. The GEAK change was real: measured on its own by Hyperloom's PRELUDE baseline executor,
the overlay gave 1795.2 tok/s against stock baselines of 1523.1 and 1462.1 (+17.9% / +22.8%), with GSM8K
0.9659 against 0.9651 / 0.9621.

### Proposed solution
On resume, run the KERNEL recovery (read `result.json`, promote, re-validate with Hyperloom's harness) before
the phase machine evaluates its exit conditions, and make sure a `skip_to_sweep` hint only fires after a
recovered result has been promoted or rejected. Record the outcome in `session_breakdown.json` either way.

### Acceptance criteria
- [ ] A test resumes a session whose KERNEL row has no completion evidence but whose `geak/result.json` is
      `status: ok`; the result is re-validated, and kept or reverted, before any transition to SWEEP.
- [ ] A rejected recovered result is recorded with its reason; it is not silently dropped.
- [ ] A recovered `provisional` result (GEAK salvage) is re-measured, never promoted on GEAK's own number.

---

## [HL-26] Store a validated GEAK overlay in the recipe KB and replay it on the next run
<!-- labels: type:feature, domain:inference, area:recipe-kb, area:kernel, priority:P2 -->

### Problem / use case
A GEAK win costs about 2 h of GPU time and about 11M input-equivalent Opus tokens (gpt-oss-120b, 1 Oct: 11
GEAK sessions, 55.5M cache-read, 2.7M cache-write, 0.4M output tokens). After the run, nothing in Hyperloom
lets a later run reuse it:

- The run's recipe KB (`recipe.json`) has `kernel_optimizations: []` and no reference to the overlay. It
  holds only the framework recipe (`--attention-backend ROCM_AITER_UNIFIED_ATTN`, +2.75%).
- GEAK's own KB write (`kb_write.json`) wrote the overlay locally but did not promote it
  (`remote_unavailable: no_credentials`).

So the next gpt-oss-120b run on the same MI300X / vLLM / fp4 key would run GEAK again for a result that is
already measured. The overlay (`tuning/deploy/installed_overlay`) is a self-contained `PYTHONPATH` drop-in and
can be replayed without GEAK.

### Proposed solution
When a GEAK result is kept after Hyperloom's re-validation, copy its overlay into the recipe KB entry (as a
content-addressed artifact next to `recipe.json`) and add it to `kernel_optimizations` with its measured gain,
the accuracy result and the GEAK report path. Warm replay (PRELUDE) puts a stored overlay on the server
`PYTHONPATH` and checks it against its recorded gain, under the same rules as HL-24 (#40). KERNEL then starts
from the replayed stack, or is skipped when the replay reproduces and the remaining target is met.

### Acceptance criteria
- [ ] A kept GEAK result adds an entry to `kernel_optimizations` with the overlay artifact, gain and accuracy.
- [ ] A run with that KB replays the overlay in PRELUDE and logs `warm-replay REPRODUCED` or `NOT REPRODUCED`.
- [ ] A KB keyed to another GPU architecture or framework version does not replay the overlay.

---

## [HL-27] Give the KERNEL delegation a usage budget and stop GEAK when the run stops
<!-- labels: type:feature, domain:inference, area:kernel, priority:P2 -->

### Problem / use case
Hyperloom passes GEAK a wall-clock budget only (`GEAK_E2E_TIMEOUT_S`, default 43200 s, shrunk to the run
deadline). It does not pass or track the Claude usage GEAK spends, and it does not stop GEAK when the
optimizer itself stops:

- In the gpt-oss-120b run (1 Oct), GEAK used more input tokens than all 149 of Hyperloom's own agent calls in
  the same run (55.5M against 25.0M cache-read tokens), within 2 of the run's 8 hours.
- When the optimizer was stopped at 10:05 UTC for the plan-usage limit, GEAK and its Claude sessions kept
  running for about 16 minutes. The operator's watcher script has to kill `run_e2e.py` / `geak_runner` and
  the bundled `claude` processes itself.

### Proposed solution
1. Read the token usage of the GEAK sessions (from their transcripts or GEAK's result) into
   `session_breakdown.json`, per GEAK role, next to the framework agents' usage.
2. Add a `--kernel-usage-budget` (tokens or a share of the run's budget) that Hyperloom passes to GEAK. When
   GEAK has no matching option yet, Hyperloom stops the delegation at the budget and recovers what is on disk.
3. When the optimizer gets SIGTERM or hits its deadline, stop the GEAK process group and its Claude
   subprocesses, then record the partial result.

The changes inside GEAK that would cut its usage (benchmark polling turns, growing tuning sessions, duplicate
tuning sessions, model choice per role) belong to the GEAK repo and are not part of this issue.

### Acceptance criteria
- [ ] `session_breakdown.json` reports GEAK token usage per role for a run with a KERNEL delegation.
- [ ] A test stops the optimizer during a (mocked) GEAK delegation; no GEAK or `claude` process survives it.
- [ ] A delegation that reaches its usage budget is stopped and its on-disk result is handled as in HL-25.

---

## [HL-28] Don't run an LLM turn every tick while a delegated task is in flight
<!-- labels: type:feature, domain:inference, area:kernel, priority:P1 -->

### Problem / use case
`Coordinator.tick` runs `_reactor_pass` for every role on every tick, and `_reactor_turn` always calls the
backend: a fresh agent session with the full composed prompt and tool schemas. That happens even when nothing
can change until a delegated task finishes.

In the gpt-oss-120b run (1 Oct, `--tick-interval-sec 30`), the KERNEL phase delegated to GEAK at 08:21. Between
08:22 and 10:05 the orchestrator started **124 Opus sessions**, about one a minute. Each had a ~40,000-character
status prompt, checked `get_running_tasks`, and ended with a hold, e.g. `tick67 hold: no state change ...
kernel_agent task c4b884f9 is still the sole in-flight work`.

Measured from the session transcripts, weighting tokens by API price ratios (cache read 0.1x, cache write
1.25x, output 5x input):

| | Share of the run's AI usage |
|---|---|
| Orchestrator ticks during the KERNEL delegation | **32.2%** (525 turns, 21.8M cache-read, 3.0M cache-write tokens) |
| All of GEAK | 54% |
| The whole FRAMEWORK phase (7 candidates) | 4.0% |

These ticks add to GEAK's own usage in the same window. During it, plan usage went from 62% to 82% of the
5-hour limit in 25 minutes, which stopped the run (HL-25).

### Proposed solution
Skip a role's reactor LLM turn when its state has not changed since its last turn and a delegated task is
still within its lease. Wake it on an event instead: the task completes, fails or times out, the lease is near
its end, the phase budget is near its end, or a message or intent is addressed to it. Keep a slow heartbeat
turn (for example every 10 minutes) so a stuck task is still noticed. Count skipped turns in
`session_breakdown.json`.

This is separate from HL-27, which limits what GEAK itself spends.

### Acceptance criteria
- [ ] A test runs a KERNEL phase with a long-running mocked delegation; the reactor is not called on ticks
      where nothing changed, and it is called when the task completes.
- [ ] A delegation that runs past its lease or the phase budget still wakes the role.
- [ ] `session_breakdown.json` reports reactor turns run and skipped per phase.
- [ ] On a rerun of the gpt-oss-120b workload, orchestrator usage during the KERNEL delegation falls by at
      least 80%, and the run's result is unchanged.

---

## [HL-29] Report GEAK's Claude usage per role, and give the KERNEL delegation a usage budget
<!-- labels: type:feature, domain:inference, area:kernel, priority:P2 -->

### Problem / use case
Split out of HL-27 (parts 1–2). Part 3, stopping GEAK with the run, is in the PR for HL-27.

In the gpt-oss-120b run of 1 Oct, GEAK used more input tokens than all 149 of Hyperloom's own agent calls in the same run (55.5M against 25.0M cache-read tokens), within 2 of the run's 8 hours. `session_breakdown.json` shows none of it, and nothing stops GEAK from spending the whole plan window: the run was stopped by the 80% plan-usage rule while GEAK was the main spender.

There is no clean source for that usage yet:
- GEAK's Claude transcripts land in the container user's shared `~/.claude/projects/<GEAK checkout>-e2e-workflow/` directory. It is keyed by GEAK's working directory, so every GEAK run from every session is mixed in it, and no field says which GEAK role (setup, tuning, verify, …) a session belongs to.
- `result.json` carries no usage.

### Proposed solution
1. Pick the source:
   - (a) **Upstream:** GEAK reports per-role usage (input, output, cache-read and cache-write tokens, model) in `result.json` and in a running file it updates during the delegation. AGENTS.md's "fix upstream" points here.
   - (b) **Hyperloom-side:** give the GEAK child its own Claude config directory inside the session (`CLAUDE_CONFIG_DIR=<session>/geak/claude`) so its transcripts are per session. Attribute roles from GEAK's prompts. This has to be checked against GEAK's credential and settings handling first.
2. Read that usage into `session_breakdown.json`, on the KERNEL event, per GEAK role, next to the framework agents' usage.
3. Add `--kernel-usage-budget` (tokens or a share of the run's budget). Pass it to GEAK where GEAK supports it; otherwise Hyperloom stops the delegation at the budget, using the runner teardown from HL-27, and recovers what is on disk as in HL-25.

Related: the optimizer's own SIGTERM drain was pre-empted on 1 Oct by a native failure-signal handler (absl-style stack dump, process killed at once). Finding which import installs it, and keeping Hyperloom's drain, is worth a separate bug.

### Acceptance criteria
- [ ] `session_breakdown.json` reports GEAK token usage per role for a run with a KERNEL delegation.
- [ ] A delegation that reaches its usage budget is stopped, and its on-disk result is handled as in HL-25.
- [ ] The chosen source is recorded in `docs/components/geak.md`.

---

## [HL-30] GEAK's timeout leaves no time to re-validate its result
<!-- labels: type:bug, domain:inference, area:kernel, priority:P1 -->

### Problem / use case
In the gpt-oss-120b rerun (2 Oct, session `gpt-oss-120b/20261002T172218Z-4e7ac5a0`, `--max-hours 6`), GEAK
finished `status: ok` with +20.0% on its own harness at 23:00:58, 21 minutes before the session's end. Hyperloom never
measured it: the re-validation round (`needs 1215s`) plus the closing reserve did not fit, and the result was recorded
`revalidation_status: failed`, `session_time_exhausted`. The run reported 3.24% instead of about 24.6%. Only a manual
`--resume-from … --extend-hours 1` re-measured it: 1826.9 tok/s, GSM8K 0.9682, kept; 24.59% validated.

The cause: `_geak_timeouts` in `orchestrator/phases/kernel.py` sizes GEAK's runner timeout as the session time left,
minus the closing reserve and a 300 s margin. It does not reserve the round Hyperloom itself must run on GEAK's result,
so a GEAK that uses its allowance always finishes too late to count.

### Proposed solution
Subtract one re-validation round from GEAK's allowance: the measured duration of the session's baseline double-run
(warmup + measured round), which is the shape of the rebench. If what remains is below `GEAK_MIN_RUN_S`, skip GEAK as
today. Record the reserved window in the KERNEL event's evidence.

### Acceptance criteria
- [ ] A test with a run deadline shows GEAK's runner timeout leaves at least one baseline round plus the closing reserve.
- [ ] A GEAK that uses its whole allowance is still re-validated in the same run.

---

## [HL-31] Without `claude` on PATH, specialists silently lose source access and every source patch fails
<!-- labels: type:bug, domain:inference, area:search, priority:P1 -->

### Problem / use case
`_register_executors` (`inference_optimizer/cli/executors.py`) runs specialists as `claude` CLI subprocesses, each in
its own workspace with `bypassPermissions`, but only if `shutil.which("claude")` finds the CLI. In the validated Docker
setup it does not: the CLI is installed at `/root/.local/bin/claude` (GEAK runs it from there), which is not on the
container's PATH. Hyperloom then
logs one warning and falls back to an in-process backend that runs with Claude Code's default permissions and only the
optimizer's working directory (the repo checkout) allowed.

Every specialist then fails. In the 2 Oct gpt-oss rerun, FRAMEWORK specialists hit 63 refused tool calls (reading vLLM's
source, the session's own TraceLens `analysis.md`, even `mkdir` of their own `runs/specialist/<id>/src`), ran out of their
8 turns, and crashed. The orchestrator then reported "specialist arm suspended - sandbox blocks all source reads/writes".
The same `Reached maximum number of turns (8)` crashes are in every earlier run on this container (9 and 12 per run), so
source patches have never run here. With `/root/.local/bin` on PATH (2–3 Oct 9 h run), the PRELUDE specialists completed
with 11 hints and 0 refused calls.

### Proposed solution
1. Resolve the installed CLI (its install path, or the `GEAK_CLAUDE_BIN` setup already writes to `.env`), not only PATH;
   or have setup put it on PATH in the runtime env.
2. Never degrade silently: if subprocess mode was requested and no CLI is found, fail preflight with the reason, or give
   the in-process specialists the same workspace, allowed directories and permission mode. A run must not proceed with the
   source arm quietly disabled.
3. Report the specialist dispatch mode in `session_breakdown.json` metadata.

### Acceptance criteria
- [ ] In the validated Docker setup, specialists run in subprocess mode without any PATH change by the operator.
- [ ] A test with no CLI available fails preflight (or runs in-process with workspace access) instead of falling back
      to an in-process backend that cannot read or write source.

---

## [HL-32] The TraceLens trace analysis runs inline, freezing the coordinator for ~20 min, and is PRELUDE's largest cost
<!-- labels: type:bug, domain:inference, area:search, priority:P2 -->

### Problem / use case
`trace_analyze` runs the LLM-backed TraceLens analysis (its own Claude agent with sub-agents), taking about 20 minutes on
gpt-oss-120b. It runs inline: as PRELUDE's roofline step, and as an inline "fast action"
(`INFERENCE_OPTIMIZER_INLINE_FAST_ACTIONS`, on by default) when the orchestrator requests it in its reactor turn. Either way
the tick loop is blocked for its whole duration:
- Qwen3-8B, 2 Oct: the orchestrator's first KERNEL turn requested `trace_analyze`. `state.tick` stayed at 2 from 16:16 to
  16:37, the critic got no turn, and the `kernel_agent` task (GEAK) was not dispatched until it returned.
- gpt-oss-120b, 1 Oct (`main`): no reactor turn during PRELUDE's 06:12–06:32 analysis.

It is also the largest cost in PRELUDE: 3.8 M of 4.8 M weighted tokens on 1 Oct and 3.9 M of 4.7 M on 2 Oct (about 80%).

### Proposed solution
1. Run `trace_analyze` as a dispatched task, never as an inline fast action; keep inline execution for actions that are
   actually cheap.
2. Reuse an analysis of the same trace instead of re-running it, and consider the deterministic TraceLens path where the
   LLM pass adds little.

### Acceptance criteria
- [ ] A test shows a `trace_analyze` request does not block the tick loop.
- [ ] PRELUDE token use on gpt-oss-120b drops measurably against the 2 Oct figure.

---

## [HL-33] (GEAK, upstream) An interrupted GEAK run is flushed as a final `no_gain`
<!-- labels: type:bug, domain:inference, area:kernel, priority:P2 -->

### Problem / use case
On SIGTERM, GEAK's `run_e2e` flushes `result.json` with `status: no_gain`, `throughput_speedup: 1.0` (Qwen3-8B, 2 Oct,
stopped 33 min into GEAK). On resume, `run_e2e` continues from the pinned eval dir, sees that run as finished, and returns
`no_gain` at once, so the interrupted work is lost. With #53, a stopped run now does stop GEAK, which makes this the
common case after a usage-limit stop. Before #53, GEAK kept running and finished on its own; on 1 Oct that is how the +21%
result existed at all.

### Proposed solution
GEAK marks a SIGTERM-flushed run as `interrupted` (or partial), not a final verdict, and continues it from its eval dir on
the next run. Hyperloom treats `interrupted` as re-runnable, not settled. Pin the GEAK fix per AGENTS.md.

### Acceptance criteria
- [ ] A GEAK run stopped mid-tuning and then resumed continues its work instead of returning `no_gain`.
- [ ] Hyperloom's resume recovery re-delegates an `interrupted` result rather than settling it.

---

## [HL-34] Reap the KERNEL delegation's leftover servers and check free VRAM before every server boot
<!-- labels: type:bug, domain:inference, area:kernel, priority:P1 -->

### Problem / use case
A vLLM server left running by the KERNEL delegation makes every later measurement in the session fail, and Hyperloom
reports that as candidate failures.

gpt-oss-120b, 3 Oct, session `gpt-oss-120b/20261003T031805Z-c30ce6cd`:
- During GEAK's tuning stage, a Magpie-launched vLLM server's API server exited, but its `VLLM::EngineCore`
  (pid 1598749, parent pid 1) kept 93% of GPU 7 after GEAK returned `ok` at about 11:14. GEAK's teardown misses it;
  see `docs/backlog/geak-backlog.md` GK-01/GK-02. The GEAK repo cannot be changed for now.
- Every vLLM boot Hyperloom tried afterwards failed in about 30 s with `Free memory on device cuda:0 (8.08/191.98 GiB)
  on startup is less than desired GPU memory utilization (0.95, 182.39 GiB)`. That covered the re-validation of
  GEAK's +27.4% result (`revalidation_status: failed`) and all 8 SWEEP boots (`failed_pairs: 8`, `sweep_failed`).
- The run reported +8.16% instead of keeping GEAK's result. Nothing in the session named the cause; the orphan was
  found and stopped by hand after the run.

### Proposed solution
1. **Reap the delegation's leftovers.** When `geak_runner` finishes, after `run_e2e` exits or is stopped, it stops every
   process that still belongs to the delegation's output dir: a working directory under it, or a `MAGPIE_SERVER_PID_FILE`
   under it. The runner launched GEAK into that dir, so the match cannot reach anyone else's process. Never match by
   process name. Record what was reaped in the GEAK result.
2. **Check the GPU before every server boot.** Before a benchmark or server lifecycle boots vLLM, compare free VRAM
   with what the launch needs. If the GPU is held, fail the step as `gpu_busy`, naming the holding pids, instead of
   letting vLLM fail and counting it as a candidate failure. A GEAK re-validation that hits `gpu_busy` is retried after
   reclaim, not settled as `failed`.

### Acceptance criteria
- [ ] A test with a stub `run_e2e` that leaves a detached process (parent pid 1, its own session) under the output dir
      shows the runner stops it, and a process outside the dir is left alone.
- [ ] A test with the GPU held shows a server boot fails as `gpu_busy` naming the pid, and GEAK's re-validation is not
      recorded as `failed` for that reason.
- [ ] `docs/backlog/geak-backlog.md` GK-01/GK-02 point at this issue.

---

## Posting these issues

`create_issues.py` (next to this file) parses every `## [HL-xx] Title` section, creates
missing labels, creates the issues in order, and then rewrites `HL-xx` references to the
real `#N` numbers. It can also add each issue to a GitHub Project.

```bash
gh auth login                      # needs repo scope; add project scope for --project
gh auth refresh -s project         # only if using --project

python create_issues.py --repo <owner>/<repo> --dry-run
python create_issues.py --repo <owner>/<repo>
python create_issues.py --repo <owner>/<repo> --project <number> --project-owner <owner>
python create_issues.py --repo <owner>/<repo> --only HL-01,HL-02   # post a subset
```
