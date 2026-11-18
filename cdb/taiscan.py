"""Track C: the same cases through AIoD's TAI Scan (https://tai-scan.aiodp.ai).

    TAI_USER=... TAI_PASS=... python -m cdb.taiscan --split test --out results/test-taiscan

TAI Scan takes five fields, not a free description, so each case is sent with role "provider",
type "AI system" and the description as the intended use; domain and input data are left to TAI
Scan to infer ("see intended use"). Its risk level is compared with the expected tier (both
high-risk routes count as high-risk) and its relevant articles with the articles of the expected
clauses. Answers are cached per case in <out>/cases.jsonl, so an interrupted run resumes.

Login: Keycloak password grant on the public client "tai-scan" (realm aiodp); credentials come
from the environment and go only to aiodp-auth.aiodp.ai. Where that grant refuses a real account,
sign in at https://tai-scan.aiodp.ai and pass the web app's token as TAI_TOKEN instead (browser
console: sessionStorage.getItem("keycloak_token")); it expires after a few minutes, so it suits a
single system, not a full benchmark run. The API allows about 5 requests a minute.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cdb.run import DATA, dataset_sha256, load_cases

TOKEN_URL = os.environ.get("TAI_TOKEN_URL", "https://aiodp-auth.aiodp.ai/realms/aiodp/protocol/openid-connect/token")
API = os.environ.get("TAI_API", "https://tai-scan-backend.aiodp.ai/api/v2")
PAUSE = float(os.environ.get("TAI_PAUSE", "13"))  # seconds between requests: 5 a minute
TIERS = {"out_of_scope": "out_of_scope", "prohibited": "prohibited", "high_risk_6_1": "high_risk",
         "high_risk_6_2": "high_risk", "limited": "limited", "minimal": "minimal"}


def level_to_tier(level):
    """TAI Scan's free-text risk level -> our tier, with both high-risk routes as one."""
    s = (level or "").lower()
    for words, tier in ((("prohibit", "unacceptable"), "prohibited"), (("high",), "high_risk"),
                        (("limited", "transparency"), "limited"), (("minimal", "low", "no risk"), "minimal"),
                        (("out of scope", "not an ai", "not applicable"), "out_of_scope")):
        if any(w in s for w in words):
            return tier
    return "unrecognised"


def articles(text):
    """'6, 25, 9' or 'Article 6(1), Art. 10' -> {'6', '25', '9'} / {'6', '10'}; annexes are not articles."""
    text = re.sub(r"annex\s+[ivx]+", " ", text or "", flags=re.I)
    return set(re.findall(r"(?<![\w(])(\d{1,3}[a-z]?)(?![\d])", text))


def clause_articles(clauses):
    return {m.group(1) for c in clauses if (m := re.match(r"Art\.(\d+[a-z]?)", c))}


def score(case, answer):
    exp, got = clause_articles(case["expected_clauses"]), articles(answer.get("articles", ""))
    tier = level_to_tier(answer.get("level"))
    return {
        "tier_correct": tier == TIERS[case["tier"]],
        "article_precision": len(exp & got) / len(got) if got else (1.0 if not exp else 0.0),
        "article_recall": len(exp & got) / len(exp) if exp else (1.0 if not got else 0.0),
        "tier": tier,
    }


class Client:
    def __init__(self):
        self.token, self.expires = None, 0

    def _post(self, url, data, headers):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)

    def bearer(self):
        if os.environ.get("TAI_TOKEN"):  # the token the TAI Scan web app holds after a browser sign-in
            return os.environ["TAI_TOKEN"]
        if time.time() > self.expires - 30:
            form = urllib.parse.urlencode({"grant_type": "password", "client_id": os.environ.get("TAI_CLIENT", "tai-scan"), "scope": "openid profile",
                                           "username": os.environ["TAI_USER"], "password": os.environ["TAI_PASS"]})
            try:
                t = self._post(TOKEN_URL, form.encode(), {"Content-Type": "application/x-www-form-urlencoded"})
            except urllib.error.HTTPError as e:  # not the API: the AIoD login refused TAI_USER/TAI_PASS
                raise SystemExit(f"AIoD login ({TOKEN_URL}): HTTP {e.code} {e.read().decode()[:300]}")
            self.token, self.expires = t["access_token"], time.time() + t.get("expires_in", 60)
        return self.token

    def call(self, endpoint, features):
        for attempt in range(4):
            print(f"TAI Scan {endpoint}: waiting {PAUSE:.0f} s (rate limit), then asking"
                  + (f" (attempt {attempt + 1})" if attempt else ""), file=sys.stderr, flush=True)
            time.sleep(PAUSE)
            try:
                return self._post(f"{API}/{endpoint}", json.dumps(features).encode(),
                                  {"Authorization": f"Bearer {self.bearer()}", "Content-Type": "application/json"})
            except urllib.error.HTTPError as e:
                if e.code == 429 or e.code >= 500:  # rate limit or server error: back off and retry
                    time.sleep(PAUSE * (attempt + 2))
                    continue
                raise SystemExit(f"{endpoint}: HTTP {e.code} {e.read().decode()[:300]}")
        raise SystemExit(f"{endpoint}: gave up after 4 attempts")


def features(case):
    return {"role": "provider", "type": "AI system", "domain": "see intended use",
            "input_data": "see intended use", "intended_use": case["text"]}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=["test", "fresh", "all"], default="test")
    p.add_argument("--out", default="results/test-taiscan")
    p.add_argument("--limit", type=int)
    p.add_argument("--obligations", action="store_true", help="also fetch the obligations text (slower)")
    a = p.parse_args(argv)
    if not (os.environ.get("TAI_TOKEN") or (os.environ.get("TAI_USER") and os.environ.get("TAI_PASS"))):
        sys.exit("set TAI_TOKEN (from a browser sign-in), or TAI_USER and TAI_PASS (your AIoD account)")

    cases = [c for c in load_cases(DATA / "cases.jsonl") if a.split == "all" or c["split"] == a.split][: a.limit]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cache_path = out / "cases.jsonl"
    cache = {r["id"]: r for r in load_cases(cache_path)} if cache_path.exists() else {}
    client, started = Client(), time.time()
    for i, case in enumerate(cases, 1):
        row = cache.get(case["id"])
        if not row or row.get("text") != case["text"] or (a.obligations and "obligations" not in row["answer"]):
            f = features(case)
            answer = {**client.call("risk_level", f), **client.call("relevant_resources", f)}
            if a.obligations:
                answer.update(client.call("obligation_generation", f))
            row = cache[case["id"]] = {"id": case["id"], "text": case["text"], "answer": answer}
            cache_path.write_text("".join(json.dumps(r) + "\n" for r in cache.values()))
        print(f"[{i}/{len(cases)}] {case['id']} {case['tier']} -> {row['answer'].get('level')}", file=sys.stderr)

    rows = [{**cache[c["id"]], "expected_tier": c["tier"], "scores": score(c, cache[c["id"]]["answer"])} for c in cases]
    mean = lambda k: round(sum(float(r["scores"][k]) for r in rows) / len(rows), 4)  # noqa: E731
    summary = {
        "n": len(rows),
        "metrics": {"tier_accuracy": mean("tier_correct"), "article_precision": mean("article_precision"),
                    "article_recall": mean("article_recall")},
        "levels": sorted({r["answer"].get("level", "") for r in rows}),
        "unrecognised_levels": sum(r["scores"]["tier"] == "unrecognised" for r in rows),
        "benchmark": "Compliance Draft Benchmark", "track": "C: TAI Scan", "split": a.split,
        "dataset_sha256": dataset_sha256(), "seconds": round(time.time() - started, 1),
    }
    (out / "scored.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "evaluation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["metrics"], indent=2))


if __name__ == "__main__":
    main()
