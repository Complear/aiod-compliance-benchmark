"""Run the benchmark: python -m cdb.run --reader llm|gold [--split test|fresh|all] --out results/"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from cdb import engine, reader, scorer

DATA = Path(__file__).resolve().parent.parent / "data"


def load_cases(path=DATA / "cases.jsonl"):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def dataset_sha256():
    h = hashlib.sha256()
    for name in ("cases.jsonl", "clauses.jsonl"):
        h.update((DATA / name).read_bytes())
    return h.hexdigest()


def run(cases, read_facts):
    rows = []
    for i, case in enumerate(cases, 1):
        facts, ok = read_facts(case)
        pred = engine.decide(facts)
        rows.append({
            "id": case["id"],
            "gold_facts": case["gold_facts"],
            "predicted_facts": facts,
            "reader_ok": ok,
            "expected_tier": case["tier"],
            "predicted_tier": pred["tier"],
            "expected_clauses": case["expected_clauses"],
            "predicted_clauses": pred["clauses"],
            "scores": scorer.score_case(case["tier"], case["expected_clauses"], pred["tier"], pred["clauses"]),
        })
        print(f"[{i}/{len(cases)}] {case['id']} {case['tier']} -> {pred['tier']}", file=sys.stderr)
    return rows


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--reader", choices=["llm", "gold", "replay"], default="llm",
                   help="gold = feed the gold facts (engine self-check, must score perfectly); "
                        "replay = reuse predicted facts from an earlier results/cases.jsonl (--replay)")
    p.add_argument("--replay", help="results/<split>/cases.jsonl of an earlier llm run")
    p.add_argument("--split", choices=["test", "fresh", "all"], default="test")
    p.add_argument("--cases", default=str(DATA / "cases.jsonl"))
    p.add_argument("--limit", type=int)
    p.add_argument("--out", default="results")
    a = p.parse_args(argv)

    cases = [c for c in load_cases(a.cases) if a.split == "all" or c["split"] == a.split][: a.limit]
    if a.reader == "gold":
        read_facts = lambda c: (c["gold_facts"], True)  # noqa: E731
    elif a.reader == "replay":
        earlier = {r["id"]: r for r in load_cases(a.replay)}
        cases = [c for c in cases if c["id"] in earlier]
        read_facts = lambda c: (earlier[c["id"]]["predicted_facts"], earlier[c["id"]]["reader_ok"])  # noqa: E731
    else:
        read_facts = lambda c: reader.read(c["text"])  # noqa: E731

    started = time.time()
    rows = run(cases, read_facts)
    summary = scorer.aggregate(rows)
    summary.update({
        "benchmark": "Compliance Draft Benchmark",
        "version": "0.1.0",
        "split": a.split,
        "reader": a.reader,
        "dataset_sha256": dataset_sha256(),
        "reader_failures": sum(not r["reader_ok"] for r in rows),
        "seconds": round(time.time() - started, 1),
    })

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "cases.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    # ponytail: own layout until the AITF User Guide s7 evaluation.json format is mapped.
    (out / "evaluation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["metrics"], indent=2))


if __name__ == "__main__":
    main()
