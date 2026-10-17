from __future__ import annotations

import argparse
import json
from pathlib import Path

from .distillation import deterministic_distill
from .gating import gate
from .ingestion import normalize
from .repository import MemoryRepository
from .retrieval import retrieve
from .schemas import memory_from_dict
from .validation import validate


def dump(value: object) -> None:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    print(json.dumps(value, indent=2, default=lambda item: item.__dict__))


def main() -> None:
    parser = argparse.ArgumentParser(prog="evomem", description="Evidence-grounded experience memory prototype")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest"); ingest.add_argument("--trajectory", required=True); ingest.add_argument("--output")
    pipeline = sub.add_parser("pipeline"); pipeline.add_argument("--trajectory", required=True); pipeline.add_argument("--store", default="data/memories"); pipeline.add_argument("--snapshot-root")
    retrieve_cmd = sub.add_parser("retrieve"); retrieve_cmd.add_argument("--query", required=True); retrieve_cmd.add_argument("--store", default="data/memories"); retrieve_cmd.add_argument("--language"); retrieve_cmd.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.command == "ingest":
        record = normalize(args.trajectory); data = record.to_dict()
        if args.output: Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        dump(data); return
    if args.command == "pipeline":
        record = normalize(args.trajectory)
        memory = validate(deterministic_distill(record), args.snapshot_root)
        path = MemoryRepository(args.store).save(memory)
        dump({"memory": memory.to_dict(), "saved_to": str(path)}); return
    repository = MemoryRepository(args.store)
    results = retrieve(args.query, repository.list(), args.language, args.top_k)
    dump([{"memory_id": item.memory.memory_id, "score": item.score, "scores": item.scores, "status": item.memory.status,
           "gate": gate(item).__dict__, "reasons": item.reasons} for item in results])


if __name__ == "__main__":
    main()
