import json
import unittest
from pathlib import Path

import jsonschema

from cdb import draft, engine, pack, reader, scorer
from cdb.build_dataset import build
from collector.collector import collect

ROOT = Path(__file__).resolve().parent.parent
BASE = {k: (False if t is bool else "none") for k, t in engine.FACTS.items()}


def facts(**overrides):
    return {**BASE, "ai_system": True, **overrides}


class EngineTest(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(engine.tier({**BASE, "mdr_class": "III"}), "out_of_scope")
        self.assertEqual(engine.tier(facts(prohibited_practice=True, mdr_class="III")), "prohibited")
        self.assertEqual(engine.tier(facts(mdr_class="IIa")), "high_risk_6_1")
        self.assertEqual(engine.tier(facts(mdr_class="I")), "minimal")
        self.assertEqual(engine.tier(facts(mdr_class="I", interacts_with_persons=True)), "limited")

    def test_art6_3_exception_is_cancelled_by_profiling(self):
        excepted = facts(annex_iii_area="essential_services", art6_3_exception=True)
        self.assertEqual(engine.tier(excepted), "minimal")
        self.assertEqual(engine.clauses(excepted), ["Art.49(2)", "Art.5(1)", "Art.6(3)", "Art.6(4)"])
        self.assertEqual(engine.tier({**excepted, "profiling": True}), "high_risk_6_2")

    def test_conditional_clauses_and_routes(self):
        mdr = engine.clauses(facts(mdr_class="IIb", special_category_data=True))
        self.assertTrue({"Art.4a(1)", "Art.43(3)", "Art.11(2)", "Art.6(1)"} <= set(mdr))
        self.assertFalse({"Art.49(1)", "Art.43(2)", "Art.6(2)"} & set(mdr))
        self.assertNotIn("Art.4a(1)", engine.clauses(facts(mdr_class="IIb")))
        # Art.4a(1) (formerly Art.10(5)) covers high-risk systems only
        self.assertNotIn("Art.4a(1)", engine.clauses(facts(special_category_data=True)))
        rbi = engine.clauses(facts(annex_iii_area="biometrics", remote_biometric_id=True))
        self.assertTrue({"Art.12(3)", "Art.14(5)", "Art.43(1)", "Art.49(1)"} <= set(rbi))
        self.assertNotIn("Art.43(2)", rbi)
        employment = engine.clauses(facts(annex_iii_area="employment"))
        self.assertIn("Art.43(2)", employment)
        self.assertFalse({"Art.43(1)", "Art.12(3)", "Art.11(2)"} & set(employment))
        self.assertIn("Art.49(1)", employment)
        # Annex III point 2 systems register nationally (Art. 49(5)), not in the EU database
        self.assertNotIn("Art.49(1)", engine.clauses(facts(annex_iii_area="critical_infrastructure")))
        # Art. 50(3) binds deployers; the pack scores provider duties
        self.assertNotIn("Art.50(3)", engine.clauses(facts(emotion_or_biometric_categorisation=True)))

    def test_out_of_scope_prohibited_and_minimal(self):
        self.assertEqual(engine.clauses({**BASE}), [])
        self.assertEqual(engine.clauses(facts(prohibited_practice=True, mdr_class="III")), ["Art.5(1)"])
        self.assertEqual(engine.clauses(facts()), ["Art.5(1)"])
        self.assertEqual(engine.clauses(facts(interacts_with_persons=True, synthetic_content=True)),
                         ["Art.5(1)", "Art.50(1)", "Art.50(2)"])

    def test_every_clause_is_a_pack_leaf_and_catalogued(self):
        catalogue = {json.loads(l)["id"] for l in (ROOT / "data/clauses.jsonl").read_text().splitlines()}
        self.assertEqual(catalogue, set(pack.leaves()))
        everything = facts(mdr_class="IIb", special_category_data=True, remote_biometric_id=True,
                           interacts_with_persons=True, synthetic_content=True,
                           emotion_or_biometric_categorisation=True)
        self.assertLessEqual(set(engine.clauses(everything)), catalogue)

    def test_answers_are_pack_options(self):
        options = {q["key"]: q["options"] for q in pack.load()["questions"]}
        for f in (BASE, facts(), facts(annex_iii_area="education", art6_3_exception=True), facts(mdr_class="III")):
            for key, answer in engine.answers(f).items():
                self.assertIn(answer, options[key])

    def test_gold_facts_reproduce_every_case(self):
        path = ROOT / "data/cases.jsonl"
        if not path.exists():
            self.skipTest("dataset not built")
        for line in path.read_text().splitlines():
            case = json.loads(line)
            self.assertEqual(engine.decide(case["gold_facts"]),
                             {"tier": case["tier"], "clauses": case["expected_clauses"]}, case["id"])


class DraftArticleTest(unittest.TestCase):
    def test_articles_are_scored_at_track_c_level(self):
        st = lambda c: {"claim": "x", "citation": c, "evidence": "reads CT"}  # noqa: E731
        s = draft.score_case("It reads CT.", ["Art.15(1)", "Art.15(3)", "Art.9(1)"], [st("Art.15(4)"), st("Art.11(1)")])
        self.assertEqual((s["citation_precision"], s["citation_recall"]), (0.0, 0.0))
        self.assertEqual((s["article_precision"], s["article_recall"]), (0.5, 0.5))  # 15 right, 11 wrong; 9 missed


class PackTest(unittest.TestCase):
    def test_only_what_the_benchmark_runs_on_is_vendored(self):
        text = pack.PACK.read_text()
        self.assertNotIn('"body"', text)  # Complear's guidance stays in Complear
        self.assertNotIn('"instructions"', text)


class ScorerTest(unittest.TestCase):
    def test_perfect_and_empty(self):
        c = ["Art.9(1)", "Art.50(1)"]
        self.assertEqual(scorer.score_case("high_risk_6_1", c, "high_risk_6_1", c),
                         {"clause_coverage": 1.0, "clause_precision": 1.0, "under_classified": False, "tier_correct": True})
        s = scorer.score_case("high_risk_6_1", c, "out_of_scope", [])
        self.assertEqual((s["clause_coverage"], s["clause_precision"], s["under_classified"]), (0.0, 0.0, True))
        self.assertEqual(scorer.score_case("out_of_scope", [], "out_of_scope", [])["clause_precision"], 1.0)

    def test_partial(self):
        s = scorer.score_case("limited", ["A", "B"], "prohibited", ["A", "C", "D", "E"])
        self.assertEqual((s["clause_coverage"], s["clause_precision"], s["under_classified"]), (0.5, 0.25, False))


class ReaderTest(unittest.TestCase):
    def test_malformed_output_retries_then_defaults(self):
        calls = []
        facts_out, ok = reader.read("x", chat=lambda t: calls.append(t) or "not json")
        self.assertEqual((facts_out, ok, len(calls)), (reader.DEFAULT_FACTS, False, 2))

    def test_valid_output_is_parsed(self):
        good = facts(mdr_class="IIa")
        self.assertEqual(reader.read("x", chat=lambda t: "```json\n" + json.dumps(good) + "\n```"), (good, True))
        self.assertIsNone(reader.parse(json.dumps({**good, "mdr_class": "IV"})))


class DraftTest(unittest.TestCase):
    TEXT = "StrokeSight runs a convolutional network over head CT to flag large-vessel occlusion. Class IIb."

    def st(self, citation, evidence="a convolutional network over head CT"):
        return {"claim": "applies", "citation": citation, "evidence": evidence}

    def test_citations_are_scored_against_the_pack_and_the_expected_clauses(self):
        s = draft.score_case(self.TEXT, ["Art.9(1)", "Art.15(3)"],
                             [self.st("Article 9 (1)"), self.st("Art.9(1)"), self.st("Art.99(9)")])
        self.assertEqual(s["citation_validity"], 0.5)  # distinct citations: Art.9(1) and the invented Art.99(9)
        self.assertEqual(s["citation_precision"], 0.5)
        self.assertEqual(s["citation_recall"], 0.5)
        self.assertEqual(s["invalid_citations"], ["Art.99(9)"])

    def test_evidence_must_be_quoted_from_the_description(self):
        s = draft.score_case(self.TEXT, ["Art.9(1)"],
                             [self.st("Art.9(1)", "Convolutional  network over head CT."), self.st("Art.9(1)", "trained on 40,000 scans"),
                              self.st("Art.9(1)", "")])
        self.assertAlmostEqual(s["unsupported_rate"], 2 / 3)  # case and spacing ignored; invented and empty quotes count

    def test_an_empty_memo_is_right_only_when_nothing_applies(self):
        self.assertEqual(draft.score_case(self.TEXT, [], [])["citation_precision"], 1.0)
        none = draft.score_case(self.TEXT, ["Art.9(1)"], [])
        self.assertEqual((none["citation_recall"], none["unsupported_rate"]), (0.0, None))

    def test_malformed_output_retries_then_scores_an_empty_memo(self):
        calls = []
        self.assertEqual(draft.draft("x", chat=lambda t: calls.append(t) or '{"statements": [{"claim": 1}]}'), ([], False))
        self.assertEqual(len(calls), 2)
        ok = {"statements": [self.st("Art.9(1)")]}
        self.assertEqual(draft.draft("x", chat=lambda t: "```json\n" + json.dumps(ok) + "\n```"), (ok["statements"], True))

    def test_the_prompt_lists_every_scorable_clause(self):
        self.assertEqual(len(draft.KNOWN), 46)
        self.assertTrue(all(f"{c}:" in draft.PROMPT for c in draft.KNOWN))


class DatasetBuildTest(unittest.TestCase):
    def test_rejects_wrong_tier_giveaway_and_shared_ngrams(self):
        text = "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda."
        ok = {"id": "1", "text": text, "gold_facts": facts(), "target_tier": "minimal"}
        accepted, rejected = build([
            ok,
            {**ok, "id": "2", "text": "Unrelated words for the second case of this test here."},
            {**ok, "id": "3", "text": "Other words entirely about something else in this sentence.", "target_tier": "limited"},
            {**ok, "id": "4", "text": "This high-risk system is clearly something else entirely."},
        ])
        self.assertEqual([c["id"] for c in accepted], ["1", "2"])
        self.assertEqual([r[0] for r in rejected], ["3", "4"])
        _, dup = build([ok, {**ok, "id": "5"}])
        self.assertEqual(dup[0][0], "5")


class CollectorTest(unittest.TestCase):
    subject = json.loads((ROOT / "schema/examples/subject.example.json").read_text())
    mapping = json.loads((ROOT / "collector/mapping.json").read_text())
    evaluation = {"benchmark": "Compliance Draft Benchmark", "version": "0.1.0", "dataset_sha256": "a" * 64,
                  "n": 3, "metrics": {"clause_coverage": 0.8, "clause_precision": 0.7,
                                      "under_classification_rate": 0.1, "latency": 2.0}}

    def test_builds_valid_scorecard_and_warns_on_unmapped(self):
        card, warnings = collect(self.evaluation, self.subject, self.mapping)
        self.assertEqual([m["name"] for m in card["metrics"]],
                         ["clause_coverage", "clause_precision", "under_classification_rate", "latency"])
        self.assertFalse(card["metrics"][2]["higher_is_better"])
        self.assertEqual(len(warnings), 1)

    def test_example_scorecards_validate(self):
        schema = json.loads((ROOT / "schema/scorecard.schema.json").read_text())
        for path in (ROOT / "schema/examples").glob("scorecard.*.json"):
            jsonschema.validate(json.loads(path.read_text()), schema)

    def test_invalid_subject_fails(self):
        bad = {**self.subject, "run": {"date": "2026-11-13", "environment": "laptop"}}
        with self.assertRaises(jsonschema.ValidationError):
            collect(self.evaluation, bad, self.mapping)



class TaiScanScoringTest(unittest.TestCase):
    def test_levels_articles_and_score(self):
        from cdb import taiscan
        self.assertEqual(taiscan.level_to_tier("High-risk"), "high_risk")
        self.assertEqual(taiscan.level_to_tier("Unacceptable risk"), "prohibited")
        self.assertEqual(taiscan.level_to_tier("Limited risk (transparency)"), "limited")
        self.assertEqual(taiscan.level_to_tier("???"), "unrecognised")
        self.assertEqual(taiscan.articles("Article 6(1), Art. 10, Annex III, 4a"), {"6", "10", "4a"})
        case = {"tier": "high_risk_6_1", "expected_clauses": ["Art.9(1)", "Art.10(2)", "Art.10(3)"]}
        s = taiscan.score(case, {"level": "High-risk", "articles": "6, 9, 10, 25"})
        self.assertTrue(s["tier_correct"])
        self.assertEqual((s["article_precision"], s["article_recall"]), (0.5, 1.0))


if __name__ == "__main__":
    unittest.main()
