"""Copy the EU AI Act framework pack from Complear and regenerate the clause catalogue.

    python -m cdb.vendor_pack <path to priv/frameworks/eu_ai_act_2024_1689@2026.1.json>

Only what the benchmark runs on is vendored: the framework block, the clause tree (citation, kind,
title) and the scoping questions with their options and rules. Complear's guidance (requirement
bodies, question instructions), controls, mappings, obligations and clocks stay in Complear.
Deployer duties the benchmark does not score (DEPLOYER_ONLY) are left out, with the questions that
only scope them.
"""

import json
import sys
from pathlib import Path

from cdb import pack

SOURCE = "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
DEPLOYER_ONLY = {"Art.50(3)"}


def strip(vendored):
    """Drop Complear's guidance text (the engine and scorer read none of it) and the deployer-only duties."""
    def clause(r):
        return {k: ([clause(c) for c in v if c["citation"] not in DEPLOYER_ONLY] if k == "children" else v)
                for k, v in r.items() if k != "body"}

    def scopes_only_dropped(q):
        return all(set(rule["citations"]) <= DEPLOYER_ONLY for rule in q.get("rules", []))

    return {**vendored, "requirements": [clause(r) for r in vendored["requirements"]],
            "questions": [{k: v for k, v in q.items() if k != "instructions"}
                          for q in vendored["questions"] if not scopes_only_dropped(q)]}


def main(argv=None):
    src = json.loads(Path((argv or sys.argv[1:])[0]).read_text())
    vendored = strip({k: src[k] for k in ("framework", "requirements", "questions")})
    pack.PACK.write_text(json.dumps(vendored, indent=1, ensure_ascii=False) + "\n")
    pack.load.cache_clear()
    rows = [{"id": c, "kind": r["kind"], "title": r["title"], "source": SOURCE}
            for c, _, has_kids, r in pack.nodes() if not has_kids and r["kind"] != "chapter"]
    (Path(__file__).resolve().parent.parent / "data" / "clauses.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"{len(rows)} clauses from {vendored['framework']['key']} {vendored['framework']['version']}")


if __name__ == "__main__":
    main()
