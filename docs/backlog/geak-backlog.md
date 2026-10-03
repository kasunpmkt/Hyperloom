# GEAK upstream backlog

Problems found in GEAK while validating Hyperloom on gpt-oss-120b and Qwen3-8B (1–3 Oct 2026, host `xe9680-3`,
GPU 7, GEAK checkout `GEAK@cfd5b589c7f3b3de120227dfe8ac66ac9665a28f`). This fork cannot change the GEAK repo for now,
so each entry records the evidence, the fix GEAK needs, and what Hyperloom does meanwhile. When GEAK becomes
changeable, file each entry upstream, pin the fixed revision, and retire the Hyperloom-side mitigation that only
existed to cover it (`AGENTS.md`: fix upstream, not around it).

Session paths are relative to `USER_DATA_PATH` (`/home/hasith/AMD/hyperloom-data`).

| Key | Problem | Hyperloom-side mitigation |
|---|---|---|
| GK-01 | Teardown misses a re-parented vLLM `EngineCore` | reap the session's GEAK servers when the delegation returns; check free VRAM before every server boot |
| GK-02 | `run_e2e` does not stop the servers its stages started when it exits | same as GK-01 |
| GK-03 | An interrupted run is flushed as a final `no_gain` | #58: record that Hyperloom stopped GEAK, re-delegate fresh on resume |
| GK-04 | No per-role usage report and no usage budget | #54 |
| GK-05 | Token waste inside GEAK's agents | none beyond a budget (#54) |

---

## GK-01 Teardown misses a re-parented vLLM `EngineCore`

**Evidence.** gpt-oss-120b, 3 Oct, session `gpt-oss-120b/20261003T031805Z-c30ce6cd`. During GEAK's tuning stage
(`geak/e2e_cycle0/tuning/legs/candprof`), a vLLM server was started through Magpie (`MAGPIE_RUN_PHASE=server`) at
11:02:30. Its API server (pid 1598163, group leader) exited, but its `VLLM::EngineCore` (pid 1598749, still in
group 1598163) was re-parented to pid 1 and kept 93% of the GPU after GEAK returned at about 11:14. Every vLLM boot
Hyperloom tried afterwards failed (`Free memory on device cuda:0 (8.08/191.98 GiB) on startup is less than desired
GPU memory utilization (0.95, 182.39 GiB)`): the re-validation of GEAK's own +27.4% result and all 8 SWEEP boots.
The run ended `sweep_failed` at +8.16% instead of keeping GEAK's result.

**Cause.** `e2e_workflow/scripts/server_teardown.sh` group-kills only when the launch proved `pgid == pid`. A pid
read from Magpie's `MAGPIE_SERVER_PID_FILE` is treated as unproven (`SERVER_GROUP_UNVERIFIED=1`), so teardown falls
back to "PID kill": the server pid and its transitive descendants, found through parent links. Once the API server
is gone, its `EngineCore` has parent pid 1 and is no longer a descendant, so the walk cannot find it, while the
group kill that would reach it is disallowed.

**Fix in GEAK.** Record the server's pgid and start time at launch even when the pid comes from Magpie's pid file
(Magpie launches through `setsid`, so `pgid == pid` can be checked then), and at teardown signal every process still
in that recorded group, re-parented ones included. This keeps the existing rule that a kill path never consults
`getpgid()` at kill time.

## GK-02 `run_e2e` does not stop the servers its stages started when it exits

**Evidence.** Same session as GK-01: `run_e2e.py` returned `status: ok` with the `candprof` stage's server engine
still running. Stages are partly agent-authored capture scripts, so whether a stage sources `server_teardown.sh` and
traps it is not guaranteed.

**Fix in GEAK.** `run_e2e` owns its eval dir: on exit, normal or SIGTERM, tear down every server pid file it handed
out under that dir, whether or not the stage's own trap ran.

## GK-03 An interrupted run is flushed as a final `no_gain`

**Evidence.** Qwen3-8B, 2 Oct, session `Qwen3-8B/20261002T154514Z-743fb653`: the optimizer was stopped 33 min into
GEAK, and `run_e2e` flushed `result.json` with `status: no_gain`, `throughput_speedup: 1.0`. On resume, `run_e2e`
continued from the pinned eval dir, read that run as finished, and returned `no_gain` immediately, so the work was
lost. Since #53, a stopped Hyperloom run stops GEAK, so this is now the normal outcome of a usage-limit stop.

**Fix in GEAK.** Mark a SIGTERM-flushed run `interrupted` (or partial), not a final verdict, and continue it from
its eval dir on the next run. Tracked in #58.

## GK-04 No per-role usage report and no usage budget

**Evidence.** gpt-oss-120b, 1 Oct: GEAK used more input tokens than all of Hyperloom's own agent calls in the same
run (55.5M against 25.0M cache-read tokens), within 2 of the run's 8 hours. GEAK's Claude transcripts land in the
container's shared `~/.claude/projects/<GEAK checkout>-e2e-workflow/` directory, mixed across sessions and without a
role field, and `result.json` carries no usage.

**Fix in GEAK.** Report per-role usage (input, output, cache read and write tokens, model) in `result.json` and in a
running file updated during the delegation, and accept a usage budget. Tracked in #54, which can also work without
GEAK by giving the GEAK child its own Claude config directory.

## GK-05 Token waste inside GEAK's agents

**Evidence.** gpt-oss-120b, 1 Oct (#45): GEAK was 54% of the run's price-weighted AI usage. The analysis behind #45
attributed it to benchmark polling turns, tuning sessions that keep growing, duplicate tuning sessions, and the
model choice per role.

**Fix in GEAK.** Poll benchmarks without an LLM turn per check, bound and reuse tuning sessions, de-duplicate them,
and choose a smaller model where a role allows it. Hyperloom can only cap the total (GK-04 / #54).

---

## Related upstream (not GEAK)

- **vLLM:** an `EngineCore` outlives its API server when the API server exits first (GK-01). The engine should exit
  when its parent dies, which would prevent this class of orphan for every launcher.
