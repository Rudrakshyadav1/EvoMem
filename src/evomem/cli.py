from __future__ import annotations

import argparse
import json
from pathlib import Path

from .distillation import deterministic_distill, distill_with_provider
from .gating import gate
from .ingestion import normalize
from .repository import MemoryRepository
from .retrieval import retrieve
from .schemas import memory_from_dict
from .validation import validate
from .indexing import rebuild
from .evaluation_runner import build_plan, load_and_validate_records, load_tasks, write_manifest, write_report
from .repository_context import collect
from .execution import DockerExecutor, execute_if_isolated
from .providers import GeminiREST
from .integration import memory_context
from .openhands_adapter import health as openhands_health
from .openhands_runner import execute_prepared, prepare_run


def dump(value: object) -> None:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    print(json.dumps(value, indent=2, default=lambda item: item.__dict__))


def main() -> None:
    parser = argparse.ArgumentParser(prog="evomem", description="Evidence-grounded experience memory prototype")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest"); ingest.add_argument("--trajectory", required=True); ingest.add_argument("--output")
    pipeline = sub.add_parser("pipeline"); pipeline.add_argument("--trajectory", required=True); pipeline.add_argument("--store", default="data/memories"); pipeline.add_argument("--snapshot-root"); pipeline.add_argument("--provider", choices=("local", "gemini"), default="local"); pipeline.add_argument("--model", default="gemini-3.8-flash")
    retrieve_cmd = sub.add_parser("retrieve"); retrieve_cmd.add_argument("--query", required=True); retrieve_cmd.add_argument("--store", default="data/memories"); retrieve_cmd.add_argument("--language"); retrieve_cmd.add_argument("--top-k", type=int, default=5)
    index_cmd = sub.add_parser("index"); index_cmd.add_argument("--store", default="data/memories"); index_cmd.add_argument("--output", default="artifacts/indexes/memory-index.json"); index_cmd.add_argument("--provider", choices=("local", "gemini"), default="local"); index_cmd.add_argument("--model", default="gemini-embedding-001")
    health = sub.add_parser("health"); health.add_argument("--store", default="data/memories")
    evaluation = sub.add_parser("evaluate"); evaluation.add_argument("--output", default="artifacts/reports/evaluation.json"); evaluation.add_argument("--dataset"); evaluation.add_argument("--results"); evaluation.add_argument("--manifest"); evaluation.add_argument("--agent", default="external-adapter"); evaluation.add_argument("--agent-model", default="unspecified"); evaluation.add_argument("--seed", type=int); evaluation.add_argument("--max-steps", type=int, default=50)
    agent_context = sub.add_parser("agent-context"); agent_context.add_argument("--task", required=True); agent_context.add_argument("--task-id"); agent_context.add_argument("--store", default="data/memories"); agent_context.add_argument("--language"); agent_context.add_argument("--context-json")
    sub.add_parser("openhands-health")
    oh_run = sub.add_parser("openhands-run"); oh_run.add_argument("--manifest", required=True); oh_run.add_argument("--task-id", required=True); oh_run.add_argument("--condition", required=True); oh_run.add_argument("--task", required=True); oh_run.add_argument("--repo", required=True); oh_run.add_argument("--memory-store", required=True); oh_run.add_argument("--output-dir", required=True); oh_run.add_argument("--model"); oh_run.add_argument("--attempts", type=int, default=1); oh_run.add_argument("--retry-delay", type=float, default=5.0); oh_run.add_argument("--execute", action="store_true")
    context = sub.add_parser("context"); context.add_argument("--repo", required=True); context.add_argument("--file", action="append")
    execute = sub.add_parser("execute"); execute.add_argument("--repo", required=True); execute.add_argument("--image", required=True); execute.add_argument("--timeout", type=int, default=30); execute.add_argument("container_command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == "ingest":
        record = normalize(args.trajectory); data = record.to_dict()
        if args.output: Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        dump(data); return
    if args.command == "pipeline":
        record = normalize(args.trajectory)
        draft = deterministic_distill(record) if args.provider == "local" else distill_with_provider(record, GeminiREST(args.model))
        memory = validate(draft, args.snapshot_root)
        path = MemoryRepository(args.store).save(memory)
        dump({"memory": memory.to_dict(), "saved_to": str(path)}); return
    if args.command == "index":
        embedder = None if args.provider == "local" else GeminiREST(args.model)
        dump(rebuild(args.store, args.output, embedder)); return
    if args.command == "health":
        records = MemoryRepository(args.store).list()
        dump({"status": "ok", "memory_count": len(records), "isolated_execution": "not_configured", "external_api_required": False}); return
    if args.command == "evaluate":
        plan = build_plan(load_tasks(args.dataset)) if args.dataset else []
        records = load_and_validate_records(args.results, plan) if args.results else []
        if args.manifest:
            write_manifest(plan, args.manifest, agent=args.agent, model=args.agent_model, seed=args.seed, budget={"max_steps": args.max_steps})
        dump(write_report(records, args.output, plan)); return
    if args.command == "agent-context":
        current_context = json.loads(Path(args.context_json).read_text(encoding="utf-8")) if args.context_json else None
        dump(memory_context(args.task, args.store, args.language, task_id=args.task_id, current_context=current_context)); return
    if args.command == "openhands-health":
        dump(openhands_health().__dict__); return
    if args.command == "openhands-run":
        request = prepare_run(args.manifest, task_id=args.task_id, condition=args.condition, task_prompt=args.task, repository=args.repo, memory_store=args.memory_store, output_dir=args.output_dir)
        if not args.execute:
            dump({"status": "dry_run", "request_path": str(Path(args.output_dir) / "request.json"), "request": request}); return
        dump(execute_prepared(request, args.output_dir, model=args.model, attempts=args.attempts, retry_delay_seconds=args.retry_delay)); return
    if args.command == "context":
        dump(collect(args.repo, files=args.file)); return
    if args.command == "execute":
        container_command = args.container_command[1:] if args.container_command[:1] == ["--"] else args.container_command
        if not container_command:
            parser.error("execute requires a command after --, e.g. -- python -m pytest")
        dump(execute_if_isolated(container_command, DockerExecutor(args.repo, args.image), args.timeout).__dict__); return
    repository = MemoryRepository(args.store)
    results = retrieve(args.query, repository.list(), args.language, args.top_k)
    dump([{"memory_id": item.memory.memory_id, "score": item.score, "scores": item.scores, "status": item.memory.status,
           "gate": gate(item).__dict__, "reasons": item.reasons} for item in results])


if __name__ == "__main__":
    main()
