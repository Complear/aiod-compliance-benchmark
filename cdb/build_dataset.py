"""Assemble data/raw/*.jsonl into data/cases.jsonl.

Each raw case carries gold facts and the tier its author intended. The engine derives the tier
and clauses; a case is rejected when its facts are invalid, its intended tier disagrees with the
engine, its text names the answer, or it shares an 8-word sequence with another case or with the
calidus-lab MDR x AI Act battery (pass that battery's directory with --lint-against).
"""

import argparse
import json
import re
import sys
from pathlib import Path

from cdb import engine

DATA = Path(__file__).resolve().parent.parent / "data"
GIVEAWAYS = re.compile(r"high[- ]risk|annex\s+iii|article\s+\d|art\.\s*\d|ai act", re.I)


def ngrams(text, n=8):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def external_texts(directory):
    texts = []
    for path in Path(directory).glob("*.json"):
        rows = json.loads(path.read_text())
        rows = rows if isinstance(rows, list) else rows.get("rows", [])
        texts += [r["text"] for r in rows if isinstance(r, dict) and "text" in r]
    return texts


def build(raw_cases, external=()):
    seen, external_grams = {}, set().union(*(ngrams(t) for t in external)) if external else set()
    accepted, rejected = [], []
    for case in raw_cases:
        problems = engine.validate(case.get("gold_facts", {}))
        if not problems:
            decided = engine.decide(case["gold_facts"])
            if decided["tier"] != case.get("target_tier"):
                problems.append(f"target_tier {case.get('target_tier')} but engine says {decided['tier']}")
        if GIVEAWAYS.search(case.get("text", "")):
            problems.append("text names the answer")
        grams = ngrams(case.get("text", ""))
        shared = [other for other, g in seen.items() if grams & g]
        if shared:
            problems.append(f"shares an 8-gram with {shared}")
        if grams & external_grams:
            problems.append("shares an 8-gram with the calidus-lab battery")
        if problems:
            rejected.append((case.get("id"), problems))
            continue
        seen[case["id"]] = grams
        accepted.append({
            "id": case["id"],
            "text": case["text"],
            "gold_facts": case["gold_facts"],
            "tier": decided["tier"],
            "expected_clauses": decided["clauses"],
            "surface": case.get("surface"),
            "split": case.get("split", "test"),
            "rationale": case.get("rationale"),
            "reviewed_by": None,
        })
    return accepted, rejected


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--lint-against", help="directory of calidus-lab battery JSON files")
    a = p.parse_args(argv)
    raw = []
    for path in sorted((DATA / "raw").glob("*.jsonl")):
        raw += [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    external = external_texts(a.lint_against) if a.lint_against else ()
    accepted, rejected = build(raw, external)
    # A rebuild keeps each case's recorded reviewer; a case whose facts changed must be reviewed again.
    out = DATA / "cases.jsonl"
    previous = {c["id"]: c for c in map(json.loads, out.read_text().splitlines())} if out.exists() else {}
    for c in accepted:
        old = previous.get(c["id"])
        if old and (old["gold_facts"], old["text"]) == (c["gold_facts"], c["text"]):
            c["reviewed_by"] = old.get("reviewed_by")
    (DATA / "cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in accepted))
    for case_id, problems in rejected:
        print(f"REJECTED {case_id}: {'; '.join(problems)}", file=sys.stderr)
    print(f"{len(accepted)} accepted, {len(rejected)} rejected")


if __name__ == "__main__":
    main()
