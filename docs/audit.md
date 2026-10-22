# Prototype audit (2026-10-17)

## What works

The legacy `phase-1` prototype can extract a limited set of OpenHands action and observation fields, request structured Gemini output, compile/run a supported C++ or Python file, create Gemini embeddings, and rank a small index by cosine similarity. The checked-in example includes a C++ trajectory, a candidate memory, a validated copy, and an index.

## What is partial or fragile

Extraction separates actions from observations and loses their original ordering and most provenance. It does not extract commands, files, errors, or test outcomes despite emitting placeholders. Distillation requires credentials at import time, has no provider boundary, and saves response JSON without independent structural or provenance checks. The validator points to `phase-1/trajectory/trajectory.json`, while the actual example is under `trajectory_logs/`; its claimed grounding is keyword overlap and it elevates a whole memory even when individual assertions are not independently established. Local `subprocess` execution is not a sandbox. Indexing only accepts files placed in one directory, hard-codes Gemini embeddings, stores no embedding metadata, and does not check dimension/model compatibility. Retrieval has no lexical signal, trust/lifecycle filter, compatibility analysis, gate, abstention, or explanation beyond cosine score.

## Security and integrity risks

Trajectory content is treated as trusted prompt material; local code is executed without isolation; file references may escape an intended repository snapshot; cloud keys are required at import and the legacy project has a local `.env`; and `validated` is used as a broad status despite only heuristic claim checks. Compilation and a few program outputs do not establish algorithmic correctness.

## Migration plan (completed decision)

1. Remove `phase-1` after auditing it: its limited code and generated artifacts were not a dependable baseline.
2. Add a standard-library core with strict dataclass validation, ordered normalized events, fact provenance, and deterministic distillation for fixtures.
3. Make validation claim-level and conservative: unsupported claims remain unverified; local execution is skipped unless an explicitly configured isolated runner exists.
4. Persist canonical memories separately from rebuildable indexes; add local lexical/semantic-baseline retrieval, compatibility checks, a gate, and abstention.
5. Add a provider interface and a real isolated runner only once their dependencies/runtime are available; then evaluate against controlled agent runs.

## First milestone and limits

This release implements steps 2–4 plus a mock OpenHands adapter, test fixtures, an evaluation scaffold, and a deterministic CLI. It does **not** claim real Gemini/OpenHands integration, semantic embedding quality, sandboxed execution, or benchmark improvement.
