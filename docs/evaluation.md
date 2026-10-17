# Evaluation protocol

Use identical task IDs, models, budgets, seeds, and success rules for: no memory, candidate/unvalidated memory, validated lexical baseline, validated hybrid baseline, and validated retrieval with the gate. Construct memories only from earlier chronological tasks. Persist one record per run with task ID, condition, supplied memory IDs, gate decision, test evidence, success, cost, elapsed time, and any negative-transfer label.

`evomem.evaluation.rates` computes only metrics whose input labels exist. This repository includes no benchmark results and makes no performance claim.
