"""Reads the EU AI Act framework pack (Complear's pack format) and applies its scoping rules.

The pack is the single source of which clauses apply: every requirement applies unless a scoping
rule triggered by an answer excludes it, and excluding a requirement excludes everything beneath
it — the same semantics as `Complear.Frameworks.Scoping`.
"""

import json
from functools import lru_cache
from pathlib import Path

PACK = Path(__file__).resolve().parent / "eu_ai_act_pack.json"


@lru_cache(maxsize=None)
def load(path=PACK):
    return json.loads(Path(path).read_text())


def nodes(pack=None):
    """(citation, ancestor citations, has_children, node) for every requirement, depth first."""
    def walk(reqs, ancestors):
        for r in reqs:
            kids = r.get("children", [])
            yield r["citation"], ancestors, bool(kids), r
            yield from walk(kids, ancestors + (r["citation"],))
    yield from walk((pack or load())["requirements"], ())


def leaves(pack=None):
    """Citations a system can be scored on: requirements with no children, chapters excluded."""
    return [c for c, _, has_kids, r in nodes(pack) if not has_kids and r["kind"] != "chapter"]


def excluded_citations(answers, pack=None):
    pack = pack or load()
    out = set()
    for q in pack["questions"]:
        answer = answers.get(q["key"])
        if answer is not None and answer not in q["options"]:
            raise ValueError(f"{q['key']}: {answer!r} is not one of {q['options']}")
        for rule in q.get("rules", []):
            if rule["when_answer"] == answer and rule["effect"] == "excluded":
                out.update(rule["citations"])
    return out


def applicable(answers, pack=None):
    """Sorted leaf citations that stay in scope for these answers."""
    pack = pack or load()
    cut = excluded_citations(answers, pack)
    return sorted(
        c for c, ancestors, has_kids, r in nodes(pack)
        if not has_kids and r["kind"] != "chapter" and c not in cut and not cut.intersection(ancestors)
    )
