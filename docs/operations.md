# Operations and security boundaries

Run `evomem health` before an experiment. The local pipeline needs no API key and does not run trajectory commands. `evomem index` creates a disposable, rebuildable local hash-token index from canonical memory JSON records. Its metadata rejects incompatible model/dimension values. It is a reproducibility baseline, not a semantic embedding claim.

Use `evomem context --repo /path/to/repo` to collect a read-only identity, commit, and hashes for dependency manifests. It stores no file contents. Add `--file relative/path` to fingerprint a task-relevant source file.

`evomem execute --repo /path/to/repo --image IMAGE -- COMMAND` invokes Docker only when Docker exists. It uses no network, a read-only root filesystem and repository mount, a `no-new-privileges` policy, all capabilities dropped, CPU/memory/PID limits, and a temporary writable `/tmp`. Build output must target `/tmp`; failing closed is intentional. Never put secrets in the image, command, repository, or output.

The executor module is an interface for a genuine container or VM integration. Until one is supplied, execution validation returns `skipped`; EvoMem never falls back to running LLM/trajectory commands through local `subprocess`.

`evomem openhands-sandbox-run` keeps Gemini calls in the host runner but confines every agent terminal command to a Docker container with no network and only a writable `/workspace` mount. It intentionally exposes no direct file-editor or browser tools. Pass a disposable checkout with `--repo` and an image that contains the benchmark task's historical dependencies. A generic Python image is sufficient for exploration but not for a SWE-bench correctness claim; evaluate any patch with SWE-bench's official task image and harness.

LLM integration is optional and behind `StructuredLLM`. A provider must return JSON that is schema-checked before it is saved. A provider never determines lifecycle status. Secrets stay in environment variables and must not be persisted in memories, reports, fixtures, or logs.

The default `pipeline` and `index` providers are local and require no network or credentials. To use Gemini, set `GEMINI_API_KEY` in your shell (never commit it), then pass `--provider gemini --model MODEL`. EvoMem uses Gemini's structured `generateContent` REST endpoint and `embedContent` endpoint with bounded retry/timeout behavior. A valid JSON response creates only a candidate; generated solution/lesson interpretations remain uncertain until independently validated.

Before global retrieval, classify a record as global, package, or repository scope. Repository-scoped records must include repository and dependency/file context. Cross-repository reuse must be rejected for different repository identities when the record says it is repository-specific, and otherwise requires explicit compatible language/framework/preconditions. Raw patches and commands are advisory evidence, never automatically executed.
