# Evaluation protocol

Use identical task IDs, models, budgets, seeds, and success rules for: no memory, candidate/unvalidated memory, validated lexical baseline, validated hybrid baseline, and validated retrieval with the gate. Construct memories only from earlier chronological tasks in the same repository. The planner rejects duplicate task IDs and duplicate repository/order pairs; it never gives the no-memory arm a memory.

Generate an auditable plan before launching agents:

```bash
evomem evaluate --dataset data/evaluation/chronological_fixture.json \
  --output artifacts/reports/evaluation-plan.json \
  --manifest artifacts/reports/run-manifest.json \
  --agent "openhands-adapter" --agent-model "your-model" --seed 7
```

Persist one record per completed run with task ID, condition, supplied memory IDs, source task IDs, gate decision, test evidence, success, cost, elapsed time, and any negative-transfer label. Submit records through `evomem evaluate --dataset ... --results results.json`; unknown runs, duplicate runs, no-memory injections, and future/cross-repository source-task leakage are rejected.

`evomem.evaluation.rates` computes only metrics whose input labels exist. Missing labels remain `null`, rather than silently becoming failures. This repository includes no benchmark results and makes no performance claim.

## Agent integration boundary

`evomem openhands-health` checks whether the optional OpenHands SDK can load. EvoMem prepares serializable, condition-specific requests for an external OpenHands runner; it does not yet launch OpenHands directly. This keeps evaluation planning testable without an agent runtime and avoids claiming integration when a local SDK/dependency installation is broken. The `no_memory` request forcibly strips all memories.

OpenHands execution is now opt-in for one manifest run at a time. It writes `request.json`, `trajectory.json`, and `outcome.json` to the requested output directory. It performs a dry run unless `--execute` is supplied; execution may edit the specified repository.

```bash
evomem openhands-run --manifest artifacts/reports/run-manifest.json \
  --task-id alpha-001 --condition no_memory \
  --task "Fix the documented issue" --repo /absolute/path/to/repository \
  --memory-store /absolute/path/to/staged-prior-memories \
  --output-dir artifacts/runs/alpha-001/no-memory

# Add --execute only after confirming request.json and using a disposable checkout.
```

`--attempts` controls whole-run retries after a provider failure (default: one attempt). Every terminal outcome, including a temporary provider failure, is saved in `outcome.json` so unavailable model calls are never counted as task failures or silently discarded.
