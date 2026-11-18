"""Scores predicted (tier, clauses, facts) against a case's expected answer."""

from cdb.engine import FACTS, SEVERITY


def score_case(expected_tier, expected_clauses, predicted_tier, predicted_clauses):
    exp, pred = set(expected_clauses), set(predicted_clauses)
    hit = len(exp & pred)
    if not exp and not pred:
        coverage = precision = 1.0
    else:
        coverage = hit / len(exp) if exp else 1.0
        precision = hit / len(pred) if pred else 0.0
    return {
        "clause_coverage": coverage,
        "clause_precision": precision,
        "under_classified": SEVERITY[predicted_tier] < SEVERITY[expected_tier],
        "tier_correct": predicted_tier == expected_tier,
    }


def aggregate(rows):
    """rows: dicts with expected/predicted tier, scores and facts. Returns the run summary."""
    n = len(rows)

    def mean(values):
        values = list(values)
        return round(sum(values) / len(values), 4) if values else None

    summary = {
        "n": n,
        "metrics": {
            "clause_coverage": mean(r["scores"]["clause_coverage"] for r in rows),
            "clause_precision": mean(r["scores"]["clause_precision"] for r in rows),
            "under_classification_rate": mean(float(r["scores"]["under_classified"]) for r in rows),
        },
        "tier_accuracy": mean(float(r["scores"]["tier_correct"]) for r in rows),
        "fact_accuracy": {
            k: mean(float(r["predicted_facts"][k] == r["gold_facts"][k]) for r in rows) for k in FACTS
        },
        "per_tier": {},
    }
    for t in sorted({r["expected_tier"] for r in rows}):
        sub = [r for r in rows if r["expected_tier"] == t]
        summary["per_tier"][t] = {
            "n": len(sub),
            "clause_coverage": mean(r["scores"]["clause_coverage"] for r in sub),
            "clause_precision": mean(r["scores"]["clause_precision"] for r in sub),
            "under_classification_rate": mean(float(r["scores"]["under_classified"]) for r in sub),
        }
    return summary
