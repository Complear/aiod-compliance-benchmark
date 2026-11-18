"""Collect every results/*/evaluation.json into results/SUMMARY.md: python -m cdb.summary"""

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"
TRACKS = [  # (title, directory suffix, metric keys)
    ("Track A: fact reading + rule engine", "", ["clause_coverage", "clause_precision", "under_classification_rate", "tier_accuracy"]),
    ("Track B: drafting with citations", "-draft", ["citation_validity", "citation_precision", "citation_recall", "unsupported_rate",
                                                             "article_precision", "article_recall"]),
    ("Track C: TAI Scan", "-taiscan", ["tier_accuracy", "article_precision", "article_recall"]),
]


def load(path):
    e = json.loads(path.read_text())
    return {**e.get("metrics", {}), "tier_accuracy": e.get("metrics", {}).get("tier_accuracy", e.get("tier_accuracy")),
            "n": e.get("n"), "sha": (e.get("dataset_sha256") or "")[:12]}


def table(title, suffix, keys):
    rows = [(s, load(p)) for s in ("test", "fresh") if (p := RESULTS / f"{s}{suffix}" / "evaluation.json").exists()]
    if not rows:
        return f"## {title}\n\nNot run.\n"
    head = "| Split | n | " + " | ".join(k.replace("_", " ") for k in keys) + " | dataset |"
    lines = [head, "|" + " --- |" * (len(keys) + 3)]
    for split, m in rows:
        cells = [f"{m[k]:.3f}" if isinstance(m.get(k), (int, float)) else "–" for k in keys]
        lines.append(f"| {split} | {m['n']} | " + " | ".join(cells) + f" | {m['sha']} |")
    return f"## {title}\n\n" + "\n".join(lines) + "\n"


def listing():
    """Tracks B and C side by side: a model listing obligations, alone (B) or with retrieval (TAI Scan, C)."""
    lines = ["## Listing obligations: Track B and Track C at article level", "",
             "| Split | Track B precision | Track B recall | Track C precision | Track C recall |", "| --- | --- | --- | --- | --- |"]
    for split in ("test", "fresh"):
        b, c = (RESULTS / f"{split}{x}" / "evaluation.json" for x in ("-draft", "-taiscan"))
        mb, mc = (load(x) if x.exists() else {} for x in (b, c))
        cell = lambda m, k: f"{m[k]:.3f}" if isinstance(m.get(k), (int, float)) else "–"  # noqa: E731
        lines.append(f"| {split} | {cell(mb, 'article_precision')} | {cell(mb, 'article_recall')} | "
                     f"{cell(mc, 'article_precision')} | {cell(mc, 'article_recall')} |")
    return "\n".join(lines) + "\n"


def main():
    body = "# Results\n\n" + "\n".join(table(*t) for t in TRACKS) + "\n" + listing()
    body += ("\nTrack C counts both high-risk routes as one tier and compares articles, not paragraphs. "
             "Rows with different dataset hashes were run on different data.\n")
    (RESULTS / "SUMMARY.md").write_text(body)
    print(body)


if __name__ == "__main__":
    main()
