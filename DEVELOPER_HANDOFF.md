# EvoMem developer handoff

This document is the handoff point for the team integrating and extending
EvoMem. It distinguishes what is implemented and verified today from the work
that remains before making benchmark or production claims.

## What is complete

- The old Phase 1 prototype was removed. `src/evomem/` is the only supported
  implementation.
- Experience ingestion preserves ordered trajectory evidence and provenance.
- Distillation produces structured candidate memories; it does not declare
  them trustworthy.
- Validation determines lifecycle status. Only `validated` memories enter the
  default trusted retrieval pool.
- The persistent JSON memory store retains task, solution, claims, validation,
  provenance, and repository/dependency/file fingerprints.
- Retrieval combines deterministic token-overlap signals, language
  compatibility, and validation quality. It produces ranked candidates and all
  component scores.
- The gate rejects quarantined, unsafe, incompatible, or language-mismatched
  memories; it abstains on stale/warning contexts, untrusted lifecycle states,
  or low scores.
- `evomem issue-run` is the normal issue intake path. It fingerprints the
  supplied checkout, retrieves from the supplied curated global store, applies
  the gate, and records the exact approved context before an agent starts.
- Optional OpenHands/Gemini execution is Docker-confined: agent terminal
  commands have no network and only a writable disposable repository mount.
- The test suite has 24 passing tests. This is unit/integration verification,
  not a SWE-bench result.

## What is not complete

- There is no verified SWE-bench score yet. The local evaluator was blocked by
  Docker Desktop resource/storage issues on Apple Silicon; this does not block
  normal EvoMem integration.
- The default retrieval signal named `semantic_baseline` is reproducible token
  Dice overlap, not a learned embedding or a hosted vector database. The
  companion lexical Jaccard signal, language score, and validation score make
  the current retriever a transparent hybrid baseline.
- `issue-run` does not automatically promote a finished agent run to global
  memory. A successful run still needs trajectory/test capture, validation,
  and review before admission. This is intentional: agent self-reports must
  never become trusted global memory automatically.
- The system is a research prototype, not a multi-tenant production service.
  Authentication, access control, encryption, observability, job queuing, and
  scalable vector infrastructure are future integration work.

## Architecture and responsibility map

| Area | Main files | Responsibility |
| --- | --- | --- |
| CLI / integration contract | `src/evomem/cli.py` | Exposes all commands, including the standard `issue-run` workflow. |
| Issue orchestrator | `src/evomem/openhands_runner.py` | Builds repository-aware gated context, writes audit files, and optionally runs OpenHands. |
| Agent request boundary | `src/evomem/openhands_adapter.py` | Defines serializable requests and checks OpenHands availability. |
| Memory admission | `ingestion.py`, `distillation.py`, `validation.py` | Normalizes trajectories, derives candidates, and independently assigns lifecycle status. |
| Persistent global store | `repository.py`, `schemas.py` | Canonical JSON serialization and schema validation for memories. |
| Retrieval | `retrieval.py`, `indexing.py` | Deterministic hybrid ranking and optional rebuildable local vector index artifacts. |
| Guardrails | `gating.py`, `versioning.py`, `security.py`, `repository_context.py` | Safety, lifecycle, language, repository and dependency/file compatibility checks. |
| Docker boundaries | `execution.py`, `sandbox_runner.py` | Constrained validation container and writable agent workspace container. |
| Provider handling | `providers.py`, `llm_client.py` | Optional Gemini REST access; loads missing local environment variables without logging secrets. |
| Evaluation | `evaluation.py`, `evaluation_runner.py`, `docs/evaluation.md` | Chronological no-leak experiment planning and reporting. |
| Tests | `tests/test_pipeline.py` | Regression coverage for the pipeline, gates, Docker command restrictions, and `issue-run`. |

Read `docs/architecture.md`, `docs/retrieval_and_gating.md`,
`docs/operations.md`, and `docs/evaluation.md` before changing behavior.

## Standard integration procedure

### 1. Set up the development environment

```bash
cd /path/to/EvoMem
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,agent]'
.venv/bin/python -m pytest -q tests
```

The expected baseline is all tests passing. Do not commit `.env`, `artifacts/`,
or a virtual environment.

### 2. Establish the curated global memory store

Choose a persistent, access-controlled directory owned by the integration
service, for example `/srv/evomem/global-memory`. It is not a raw repository
dump. Store only distilled, reviewed memories with evidence and validation.

To admit a reviewed trajectory:

```bash
evomem pipeline \
  --trajectory /path/to/trajectory.json \
  --store /srv/evomem/global-memory
```

Use `--provider gemini --model MODEL` only when LLM-assisted distillation is
intended. Provider output remains a candidate; validation controls its status.

### 3. Make every new issue follow the standard chain

Use a disposable checkout for the coding agent. Do not give an agent a
developer's primary checkout.

```bash
evomem issue-run \
  --task "Issue description, error, acceptance criteria, and relevant logs" \
  --repo /path/to/disposable-checkout \
  --memory-store /srv/evomem/global-memory \
  --language Python \
  --output-dir /srv/evomem/runs/issue-123
```

This dry-run is the required policy point. It writes:

- `agent-context.json`: accepted memories plus every gate decision and reason.
- `request.json`: the repository fingerprint, final prompt, budget, and
  approved context that would be sent to an agent.

The launcher should inspect or retain these files for audit. An empty accepted
memory list with `abstained: true` is correct behavior when no safe experience
exists.

### 4. Execute only after review

For OpenHands/Gemini execution, set `GEMINI_API_KEY` in the runtime
environment. Do not put it into source, memory records, artifacts, or logs.

```bash
evomem issue-run \
  --task "Issue description" \
  --repo /path/to/disposable-checkout \
  --memory-store /srv/evomem/global-memory \
  --language Python \
  --output-dir /srv/evomem/runs/issue-123 \
  --execute \
  --image python:3.12-slim \
  --model gemini-3.5-flash-lite \
  --max-steps 100 \
  --attempts 2
```

Choose a task image containing the repository's real dependencies. A generic
Python image is acceptable for exploration, but it is not sufficient evidence
for a benchmark or repository-specific success claim.

### 5. Close the learning loop safely

After an agent run:

1. Preserve the task text, patch/diff, relevant commands, test results, and
   outcome in a normalized trajectory input.
2. Run the admission pipeline against the correct repository snapshot.
3. Review validation status and evidence. Promote only `validated` records to
   the global store used by `issue-run`.
4. Keep rejected, stale, and quarantined records for audit; do not inject them.
5. Record whether the supplied memory helped, harmed, or was correctly
   abstained from. These labels support future evaluation.

Do not automatically trust a model's completion message or automatically add
its patch to global memory.

## Guardrail invariants

Developers must preserve these properties when extending the system:

1. **Evidence before trust:** an LLM may propose content but may not set a
   memory to `validated`.
2. **Gate before injection:** no retrieved memory may enter an agent prompt
   without a recorded gate decision.
3. **Abstention is valid:** an empty context is safer than speculative transfer.
4. **Repository facts win:** memory is advisory and cannot override current
   code, tests, security policy, or issue requirements.
5. **Cross-repository reuse is conservative:** incompatible repository context
   is rejected; compatibility warnings abstain.
6. **No secret persistence:** API keys and credentials never belong in memories,
   prompts, request files, fixtures, or Git.
7. **Sandbox scope is minimal:** use no network, a disposable checkout, and an
   image containing no secrets.

## Recommended next development milestones

1. Build a post-run trajectory exporter so successful `issue-run` executions
   can enter the review/validation queue without manual formatting.
2. Add a real embedding provider and vector index query path, while retaining
   the current deterministic retriever as an evaluation baseline.
3. Add repository-specific task-image discovery and automated test selection.
4. Complete the SWE-bench experiment matrix: no memory, candidate memory,
   validated semantic baseline, validated hybrid, and validated hybrid + gate.
5. Measure task success, misleading-memory use, retrieval quality, acceptance
   rate, abstention rate, stale-memory detection, and negative transfer.
6. For production, add store access control, encrypted storage, run queueing,
   structured telemetry, retention policies, and model/provider failover.

## Useful commands

```bash
# Validate the local codebase
.venv/bin/python -m pytest -q tests

# Inspect the current curated store
evomem health --store /srv/evomem/global-memory

# Inspect raw retrieval and gate decisions without starting an agent
evomem retrieve --query "your issue" --store /srv/evomem/global-memory --language Python

# Prepare the standard issue flow (recommended entry point)
evomem issue-run --task "your issue" --repo /path/to/checkout \
  --memory-store /srv/evomem/global-memory --output-dir artifacts/issue-runs/example
```

`LOCAL_SWEBENCH_RUNBOOK.md` exists only on the original developer machine and
is intentionally Git-ignored. It is optional benchmark infrastructure, not a
project requirement for normal integration.
