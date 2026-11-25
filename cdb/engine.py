"""Deterministic EU AI Act engine: facts -> tier -> answers to the pack's scoping questions -> clauses.

The reader (a small language model) only extracts facts. This module combines them into the AI Act
category (the combination the pack's single-question rules cannot express) and answers the
scoping questions of the EU AI Act framework pack; the pack's rules then decide which clauses apply.

`mdr_class` also carries IVDR devices, mapped by notified-body involvement: A to I, B to IIa, C to IIb,
D to III. ponytail: MDR class I devices that need a notified body (sterile, measuring, reusable surgical)
are not modelled.

`safety_component` is optional and defaults to true, so facts written before Regulation (EU) 2026/1744
keep their tier. Set it to false for AI in a device that is used solely for non-safety aspects (user
assistance, performance optimisation, service efficiency, automation, convenience, quality control) and
whose failure would not endanger health or safety: it is then not high-risk under Art. 6(1)
(Art. 6(1a), 6(1b)).
"""

from cdb import pack

FACTS = {
    "ai_system": bool,
    "prohibited_practice": bool,
    "mdr_class": ("none", "I", "IIa", "IIb", "III"),
    "annex_iii_area": (
        "none", "biometrics", "critical_infrastructure", "education", "employment",
        "essential_services", "law_enforcement", "migration", "justice_democracy",
    ),
    "art6_3_exception": bool,
    "profiling": bool,
    "special_category_data": bool,
    "remote_biometric_id": bool,
    "interacts_with_persons": bool,
    "synthetic_content": bool,
    "emotion_or_biometric_categorisation": bool,
}

# Optional facts and their defaults.
OPTIONAL = {"safety_component": True}

# Severity order used for the under-classification metric.
SEVERITY = {
    "out_of_scope": 0, "minimal": 1, "limited": 2,
    "high_risk_6_1": 3, "high_risk_6_2": 3, "prohibited": 4,
}

# Answer index in the pack's "ai_act_category" question, by engine outcome.
_CATEGORY = {
    "out_of_scope": 0, "prohibited": 1, "high_risk_6_1": 2, "high_risk_6_2": 3,
    "excepted": 4, "not_high_risk": 5,
}


def validate(facts):
    """Return a list of problems with a facts dict; empty when valid."""
    problems = [f"missing {k}" for k in FACTS if k not in facts]
    problems += [f"unknown {k}" for k in facts if k not in FACTS and k not in OPTIONAL]
    problems += [f"bad value {k}={facts[k]!r}" for k in OPTIONAL if k in facts and not isinstance(facts[k], bool)]
    for key, allowed in FACTS.items():
        if key not in facts:
            continue
        value = facts[key]
        ok = isinstance(value, bool) if allowed is bool else value in allowed
        if not ok:
            problems.append(f"bad value {key}={value!r}")
    return problems


def _excepted(f):
    return f["annex_iii_area"] != "none" and f["art6_3_exception"] and not f["profiling"]


def tier(f):
    if not f["ai_system"]:
        return "out_of_scope"
    if f["prohibited_practice"]:
        return "prohibited"
    if f["mdr_class"] in ("IIa", "IIb", "III") and f.get("safety_component", OPTIONAL["safety_component"]):
        return "high_risk_6_1"
    if f["annex_iii_area"] != "none" and not _excepted(f):
        return "high_risk_6_2"
    if f["interacts_with_persons"] or f["synthetic_content"] or f["emotion_or_biometric_categorisation"]:
        return "limited"
    return "minimal"


def answers(f):
    """The pack's scoping answers implied by the facts."""
    t = tier(f)
    outcome = t if t not in ("limited", "minimal") else ("excepted" if _excepted(f) else "not_high_risk")
    options = {q["key"]: q["options"] for q in pack.load()["questions"]}
    yes_no = lambda value: "Yes" if value else "No"  # noqa: E731
    return {
        "ai_act_category": options["ai_act_category"][_CATEGORY[outcome]],
        "annex_iii_biometrics": yes_no(f["annex_iii_area"] == "biometrics"),
        "bias_special_category_data": yes_no(f["special_category_data"]),
        "remote_biometric_identification": yes_no(f["remote_biometric_id"]),
        "interacts_with_persons": yes_no(f["interacts_with_persons"]),
        "generates_synthetic_content": yes_no(f["synthetic_content"]),
        "annex_iii_critical_infrastructure": yes_no(f["annex_iii_area"] == "critical_infrastructure" and t == "high_risk_6_2"),
    }


def clauses(f):
    return pack.applicable(answers(f))


def decide(facts):
    return {"tier": tier(facts), "clauses": clauses(facts)}
