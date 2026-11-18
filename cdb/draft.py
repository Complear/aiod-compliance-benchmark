"""Track B, drafting with citations: python -m cdb.draft [--split test|fresh|all] --out results/<split>-draft

The model writes an obligation memo for each case: statements that each cite one clause of the
EU AI Act pack and quote, word for word, the part of the description that makes it apply.
Scored without a judge:

- citation_validity: share of distinct citations that are clauses of the pack (no invented articles)
- citation_precision: share of distinct citations that are among the case's expected clauses
- citation_recall: share of the expected clauses that are cited
- article_precision / article_recall: the same at article level (Art.15(3) counts as 15), the level at
  which Track C scores TAI Scan, so the two can be compared
- unsupported_rate: share of statements whose quoted evidence is not in the description

Whether the cited article supports the claim needs the legal text and a judge; not scored here.
"""

import argparse
import functools
import json
import re
import sys
import time
from pathlib import Path

from cdb import pack, reader
from cdb.taiscan import clause_articles
from cdb.run import dataset_sha256, load_cases

# From the installed pack, not data/clauses.jsonl, so the module also works where only the package is installed
CLAUSES = [{"id": c, "title": r["title"]} for c, _, kids, r in pack.nodes() if not kids and r["kind"] != "chapter"]
KNOWN = {c["id"] for c in CLAUSES}

PROMPT = """You read a short description of a software product and list the EU AI Act (Regulation (EU) 2024/1689) obligations that apply to its provider.

Answer only with a JSON object {"statements": [...]}. Each statement has:
- "claim": one sentence saying why the obligation applies to this product;
- "citation": exactly one clause id from the list below, written as listed (e.g. "Art.9(2)");
- "evidence": the words of the description, copied exactly, that make the clause apply (at most 25 words).

Cite only clauses from the list. One statement per clause; leave out clauses that do not apply. If the product is not an AI system, or no clause applies, answer {"statements": []}.

Clauses:
""" + "\n".join(f"{c['id']}: {c['title']}" for c in CLAUSES)

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["statements"],
    "properties": {"statements": {"type": "array", "maxItems": len(CLAUSES), "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["claim", "citation", "evidence"],
        "properties": {"claim": {"type": "string"}, "citation": {"type": "string"}, "evidence": {"type": "string"}},
    }}},
}


def parse(raw):
    """Statements from a model reply, or None when it is not a valid statements object."""
    try:
        start, end = raw.index("{"), raw.rindex("}") + 1
        doc = json.loads(raw[start:end])
    except (ValueError, TypeError):
        return None
    items = doc.get("statements") if isinstance(doc, dict) else None
    if not isinstance(items, list) or not all(
            isinstance(s, dict) and all(isinstance(s.get(k), str) for k in ("claim", "citation", "evidence"))
            for s in items):
        return None
    return items


def draft(text, chat):
    """Returns (statements, ok). Malformed output is retried once, then scored as an empty memo."""
    for _ in range(2):
        statements = parse(chat(text))
        if statements is not None:
            return statements, True
    return [], False


def citation_id(citation):
    """'Article 9 (2)' and 'Art. 9(2)' are both 'Art.9(2)'."""
    return re.sub(r"\s+", "", re.sub(r"^\s*Article\b\.?", "Art.", citation.strip(), flags=re.I))


def _norm(text):
    text = text.lower().translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"}))
    return re.sub(r"\s+", " ", text).strip().strip("\"'.")


def score_case(text, expected_clauses, statements):
    cited = {citation_id(s["citation"]) for s in statements}
    expected = set(expected_clauses)
    body = _norm(text)
    unsupported = [s for s in statements if not _norm(s["evidence"]) or _norm(s["evidence"]) not in body]
    precision, recall = _overlap(cited, expected)
    article_precision, article_recall = _overlap(clause_articles(cited), clause_articles(expected))
    return {
        "citation_validity": len(cited & KNOWN) / len(cited) if cited else 1.0,
        "citation_precision": precision,
        "citation_recall": recall,
        "article_precision": article_precision,
        "article_recall": article_recall,
        "unsupported_rate": len(unsupported) / len(statements) if statements else None,
        "statements": len(statements),
        "invalid_citations": sorted(cited - KNOWN),
    }


def _overlap(got, expected):
    """(precision, recall); an empty answer is right only when nothing was expected."""
    if not got:
        return (1.0, 1.0) if not expected else (0.0, 0.0)
    hit = len(got & expected)
    return hit / len(got), (hit / len(expected) if expected else 1.0)


def aggregate(rows):
    def mean(key):
        values = [r["scores"][key] for r in rows if r["scores"][key] is not None]
        return round(sum(values) / len(values), 4) if values else None

    return {
        "n": len(rows),
        "metrics": {k: mean(k) for k in ("citation_validity", "citation_precision", "citation_recall",
                                          "article_precision", "article_recall", "unsupported_rate")},
        "statements": sum(r["scores"]["statements"] for r in rows),
        "invalid_citations": sorted({c for r in rows for c in r["scores"]["invalid_citations"]}),
    }


def run(cases, write):
    rows = []
    for i, case in enumerate(cases, 1):
        statements, ok = write(case)
        rows.append({"id": case["id"], "expected_clauses": case["expected_clauses"], "statements": statements,
                     "reader_ok": ok, "scores": score_case(case["text"], case["expected_clauses"], statements)})
        print(f"[{i}/{len(cases)}] {case['id']} {len(statements)} statements", file=sys.stderr)
    return rows


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=["test", "fresh", "all"], default="test")
    p.add_argument("--limit", type=int)
    p.add_argument("--max-tokens", type=int, default=3000)
    p.add_argument("--out", default="results")
    p.add_argument("--rescore", action="store_true", help="score the memos already in --out again, without the model")
    a = p.parse_args(argv)
    out = Path(a.out)
    if a.rescore:
        texts = {c["id"]: c["text"] for c in load_cases()}
        rows = [{**r, "scores": score_case(texts[r["id"]], r["expected_clauses"], r["statements"])}
                for r in load_cases(out / "cases.jsonl")]
        previous = json.loads((out / "evaluation.json").read_text())
        summary = {**previous, **aggregate(rows), "dataset_sha256": dataset_sha256()}
        (out / "cases.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        (out / "evaluation.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary["metrics"], indent=2))
        return

    cases = [c for c in load_cases() if a.split == "all" or c["split"] == a.split][: a.limit]
    chat = functools.partial(reader._chat, max_tokens=a.max_tokens, system=PROMPT, schema=SCHEMA, name="statements")
    started = time.time()
    rows = run(cases, lambda c: draft(c["text"], chat))
    summary = aggregate(rows)
    summary.update({
        "benchmark": "Compliance Draft Benchmark", "track": "B: drafting with citations", "version": "0.2.0",
        "split": a.split, "dataset_sha256": dataset_sha256(),
        "reader_failures": sum(not r["reader_ok"] for r in rows), "seconds": round(time.time() - started, 1),
    })
    out.mkdir(parents=True, exist_ok=True)
    (out / "cases.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "evaluation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["metrics"], indent=2))


if __name__ == "__main__":
    main()
