# Retrieval and gating

The current reproducible baseline derives two text-overlap signals from deterministic tokenization: Dice overlap, labelled `semantic_baseline` to avoid misrepresenting it as embeddings, and Jaccard lexical overlap. It combines them with language compatibility and lifecycle quality using documented weights (`0.45`, `0.35`, `0.10`, `0.10`). Results contain each component and a reason list. Indexes are not canonical; retrieval operates from JSON memory records and is therefore rebuildable.

The default policy accepts only `validated` records, rejects incompatible languages and quarantined records, and abstains below its configurable score threshold. `partially_validated` records can be admitted only by a caller explicitly changing policy. A gate decision is advisory: it cannot override repository facts, the task, tests, or security policy.
