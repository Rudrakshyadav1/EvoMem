# Architecture

`trajectory JSON → ordered normalized events → deterministic candidate memory → claim validation → canonical JSON repository → rebuildable in-memory hybrid ranking → retrieval gate → agent adapter context`.

All source evidence is preserved as event ID + field + excerpt. Distillation creates only candidate memories. The validator—not the distiller—controls lifecycle status. Current local retrieval labels its token-overlap score `semantic_baseline`; it is deliberately not represented as a learned embedding model.

The trusted retrieval pool contains only `validated` memories. `partially_validated`, `rejected`, `stale`, and `quarantined` records remain available for audit but the default gate abstains. The gate records one of `accepted`, `rejected`, or `abstained` and can return no memory.

Execution validation is skipped until an isolated executor is configured. `evomem execute` uses a constrained read-only Docker mount for validation, while `openhands-sandbox-run` keeps model calls on the host and confines agent terminal commands to a no-network Docker container with only the disposable repository mounted at `/workspace`. Repository compatibility compares repository ID plus only tracked dependency/file fingerprints; an unrelated commit alone does not force staleness. It returns compatible, warning, incompatible, or unknown, and the gate abstains on a relevant drift warning.
