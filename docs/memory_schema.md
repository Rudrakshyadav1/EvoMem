# Memory schema and lifecycle

Canonical records are JSON serializations of `evomem.schemas.Memory`. Required top-level fields are `memory_id`, `task`, `solution`, `claims`, `provenance`, `context`, and `status`. Each claim records a stable claim ID, category, origin (`observed`, `inferred`, or `llm`), and one or more evidence references (`event_id`, source field, excerpt, evidence type). This makes a claim auditable without trusting a generated summary.

Lifecycle transitions are conservative:

| Status | Rule |
| --- | --- |
| `candidate` | created by a distiller; never trusted |
| `partially_validated` | at least one check verifies a claim but another is unsupported or uncertain |
| `validated` | every existing claim has provenance and passes the applicable non-execution check |
| `rejected` | no claim is verified |
| `stale` | reserved for a future targeted repository/dependency drift detector |
| `quarantined` | reserved for policy/security review; always rejected by the gate |

“Validated” in this prototype means only the claims above were evidence-checked. It does not mean the solution is algorithmically correct; execution is recorded as skipped until a genuine isolated runner exists.
