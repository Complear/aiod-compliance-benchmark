"""Collector: turn an evaluation result into a scorecard (schema/scorecard.schema.json).

    python collector/collector.py --evaluation results/evaluation.json \
        --subject subject.json --mapping collector/mapping.json --out scorecard.json

subject.json holds the "subject", "benchmark" and "run" blocks the evaluation does not carry
(missing benchmark fields are filled from the evaluation when it has them). mapping.json maps
each metric name to {"higher_is_better": bool, "ai_act_refs": [...]}. The scorecard is validated
before it is written; nothing is written when it is invalid.

ponytail: reads metrics as a {name: number} object under "metrics"; map the AITF User Guide s7
evaluation.json layout here once it is confirmed.
"""

import argparse
import json
import sys
from pathlib import Path

import jsonschema

SCHEMA = json.loads((Path(__file__).resolve().parent.parent / "schema" / "scorecard.schema.json").read_text())


def collect(evaluation, subject, mapping):
    """Returns (scorecard, warnings). Raises jsonschema.ValidationError when invalid."""
    warnings = []
    benchmark = dict(subject.get("benchmark", {}))
    for src, dst in (("benchmark", "name"), ("version", "version"), ("dataset_sha256", "dataset_sha256"), ("split", "split")):
        if src in evaluation and dst not in benchmark:
            benchmark[dst] = evaluation[src]

    metrics = []
    for name, value in evaluation.get("metrics", {}).items():
        if value is None:
            warnings.append(f"metric {name} has no value; skipped")
            continue
        rule = mapping.get(name)
        if rule is None:
            warnings.append(f"metric {name} is not in the mapping; copied with no AI Act refs")
            rule = {"higher_is_better": True, "ai_act_refs": []}
        entry = {"name": name, "value": value, "higher_is_better": rule["higher_is_better"],
                 "ai_act_refs": rule["ai_act_refs"]}
        if isinstance(evaluation.get("n"), int):
            entry["n"] = evaluation["n"]
        metrics.append(entry)

    card = {
        "schema_version": "0.1",
        "subject": subject["subject"],
        "benchmark": benchmark,
        "run": subject["run"],
        "metrics": metrics,
    }
    if subject.get("limitations"):
        card["limitations"] = subject["limitations"]
    jsonschema.validate(card, SCHEMA, format_checker=jsonschema.FormatChecker())
    return card, warnings


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--evaluation", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--mapping", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    load = lambda path: json.loads(Path(path).read_text())  # noqa: E731
    try:
        card, warnings = collect(load(a.evaluation), load(a.subject), load(a.mapping))
    except (jsonschema.ValidationError, KeyError) as exc:
        print(f"invalid scorecard: {exc}", file=sys.stderr)
        return 1
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    Path(a.out).write_text(json.dumps(card, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
