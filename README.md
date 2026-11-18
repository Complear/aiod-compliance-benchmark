# Compliance Draft Benchmark

> **Open source** (code under Apache 2.0, data under CC BY 4.0), published on the AI-on-Demand
> (AIoD) platform as part of the AGILE-AI programme. The code, the data and the model also ship in
> the AI Testing Framework images at `ghcr.io/complear/aitf`.

An open benchmark that measures how well an AI system maps a product description to its
**EU AI Act** (Regulation (EU) 2024/1689) risk tier and the obligations that apply, starting
with software as a medical device (SaMD). Built by Complear for the AI-on-Demand (AIoD)
platform, programme AGILE-AI.

```
description ──► reader (small LM) ──► facts (JSON) ──► rule engine ──► tier + clauses ──► scorer ──► scorecard
```

- **Reader**: any model behind an OpenAI-compatible endpoint. The public baseline is
  [Ministral-3-3B-Instruct-2512](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512-GGUF)
  (Apache 2.0, Q4_K_M GGUF) served by llama.cpp, unchanged (no fine-tuning).
- **Rule engine** (`cdb/engine.py`): deterministic, no model. Combines the facts into the AI Act
  category (Art. 5 screen, Art. 6(1) via the MDR class, Art. 6(2)/(3) via Annex III) and answers the
  scoping questions of the **EU AI Act framework pack** (`cdb/eu_ai_act_pack.json`, Complear's pack
  format). The pack's rules decide which of its 50 clauses apply (Art. 4, 4a, 5, 6, 9–20, 43, 47–50, 72, 73).
  Version 2026.1 follows the AI Act as amended by Regulation (EU) 2026/1744 (see `data/REVIEW.md`),
  including the rewritten Art. 4 (AI literacy) and the new Art. 6(1a)–(1c); it is vendored from
  Complear's pack, so the two share one rule source.
- **Scorer** (`cdb/scorer.py`): clause coverage, clause precision, under-classification rate
  (predicted tier less severe than expected), plus tier and per-fact accuracy.
- **Scorecard** (`schema/scorecard.schema.json`) and **Collector** (`collector/`): turn an
  evaluation result into a portable JSON record of what was tested, on which data, with which
  result, and which AI Act provision the result is evidence for.

## Track B: drafting with citations

Track A (above) never lets the model cite anything: it reads facts and the rules assign the clauses.
Track B (`cdb/draft.py`) asks the model for an obligation memo instead. Every statement cites one
clause of the pack and quotes, word for word, the part of the description that makes it apply. It
is scored without a judge, on the same cases and expected clauses:

- **citation validity**: share of distinct citations that are clauses of the pack (no invented articles)
- **citation precision** and **recall**: against the case's expected clauses
- **unsupported rate**: share of statements whose quoted evidence is not in the description
- **article precision** and **recall**: the same at article level (Art.15(3) counts as 15), the
  level at which Track C scores TAI Scan; `results/SUMMARY.md` sets the two side by side

Not scored yet: whether the cited article supports the claim. That needs the legal text of each
clause and a judge model checked against the regulatory team on a sample.

## Track C: TAI Scan

`cdb/taiscan.py` sends the same cases to AIoD's [TAI Scan](https://tai-scan.aiodp.ai) and scores its
answers against the same expected results: its risk level against the expected tier (both high-risk
routes count as one) and its relevant articles against the articles of the expected clauses
(article precision and recall). TAI Scan takes five fields rather than a description, so each case
goes in as the intended use of an AI system whose provider is asking. It needs an AIoD account
(`TAI_USER`, `TAI_PASS`, read from the environment); the API allows about 5 requests a minute, so
both splits take about 40 minutes, and answers are cached per case so an interrupted run resumes.

## Use

```sh
make test                 # unit tests (stdlib unittest; needs jsonschema)
make gold                 # engine self-check on gold facts: must score 1.0 / 1.0 / 0.0
make serve                # downloads the model and starts llama-server on :8080
make run                  # scores the reader on the test and fresh splits
make draft                # Track B: drafting with citations, test and fresh splits
make taiscan              # Track C: TAI Scan on both splits (needs TAI_USER, TAI_PASS)
make summary              # all results on one page: results/SUMMARY.md
make all                  # self-check, tracks A and B, track C when TAI_USER is set, summary
make scorecard            # writes results/test/scorecard.json
```

Score another model by pointing the reader elsewhere:
`READER_URL=https://host/v1 READER_MODEL=name READER_API_KEY=... make run`.
Credentials stay in the environment; nothing is stored in the repository.

## Data

`data/cases.jsonl` — generated cases, reviewed and corrected by Miguel Amador on 17 November 2026
(`data/REVIEW.md`); `cdb/eu_ai_act_pack.json` — the vendored pack
(framework, clause tree with citations and titles, scoping questions with their options and rules;
Complear's guidance text is not included, and nothing here reads it; Art. 50(3), a deployer duty, is
left out); `data/clauses.jsonl` — its 50 scorable clauses.
Refresh both with `python -m cdb.vendor_pack <Complear pack path>`, then `make dataset`. Cases are generated, then the expected
tier and clauses are derived from each case's gold facts by the rule engine.

## Baseline (18 November 2026, reviewed cases, pack 2026.1 with Art. 4 and Art. 6(1a)–(1c))

Ministral-3-3B-Instruct-2512 Q4_K_M, no fine-tuning, llama.cpp, temperature 0, 0 malformed outputs.

| Split | n | Clause coverage | Clause precision | Under-classification | Tier accuracy |
| --- | --- | --- | --- | --- | --- |
| test | 88 | 0.914 | 0.864 | 0.034 | 0.852 |
| fresh | 21 | 0.864 | 0.940 | 0.048 | 0.857 |

Weakest facts on `test`: the Art. 6(3) exception (0.51), the Annex III area (0.66) and person
interaction (0.83). Most tier errors are minimal cases read as limited (5 of 13). Across both splits the
model finds the exception in all 9 cases that have it but also claims it in 12 of the 28 Annex III
cases that do not; it reads 6 of the 8 class I devices correctly. The reader prompt's second
worked example is a fictional system outside the dataset (it was NodeSight, the Collector's
example). A prompt rule for transcription (cases a-030, a-040) lowered coverage and raised
under-classification on `test` (0.034 to 0.057), so it is not in the prompt. Before the
review (13 November, uncorrected cases, pack 2024.1) the same model scored 0.920 / 0.911 / 0.025 /
0.886 on `test`; the cases, the pack and the reader prompt all changed, so the two are not a like-for-like comparison.
On 18 November the pack gained the rewritten Art. 4 (AI literacy, which applies to every AI system) and
Art. 6(1a)–(1c) (which go with Art. 6(1)); 97 cases gained expected clauses and none lost any. The model's
fact readings are identical to the 17 November run (0.907 / 0.847 on `test`, 0.860 / 0.929 on `fresh`);
the higher clause scores come only from Art. 4(1), which the rules get right whenever the AI-system fact is right.

### Track B baseline (18 November 2026)

Same model and settings, `max_tokens` 3000, 0 malformed outputs (`make draft`).

| Split | n | Statements | Citation validity | Citation precision | Citation recall | Unsupported | Article precision | Article recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | 88 | 743 | 0.942 | 0.314 | 0.231 | 0.458 | 0.381 | 0.303 |
| fresh | 21 | 187 | 0.973 | 0.347 | 0.227 | 0.391 | 0.443 | 0.304 |

Asked to write the memo directly, the same model cites real clauses but mostly the wrong ones, and
up to half of its quoted evidence is not in the description. Of the 43 invalid citations, all but one
join two or more clauses in one (e.g. `Art.13(2) + Art.15(3)`); the other is `Art.11(4)`, a real
provision outside the pack. The model never cites Art. 4(1) on its own, so recall falls against the
17 November run (0.256 to 0.231 on `test`), when Art. 4(1) was not in the pack. Track A reaches 0.91 coverage and 0.86 precision on the same cases
because the rules, not the model, choose the clauses. Article precision and recall compare it with
Track C: TAI Scan also lists obligations with a language model, but retrieves the legal text first.
Engine self-check on gold facts: 1.0 / 1.0 / 0.0 on all 109 cases.

## Containers

`docker/benchmark.Dockerfile` (data, engine, scorer, Collector; 156 MB) and
`docker/reader.Dockerfile` (llama.cpp server with the Ministral weights; ~3 GB). The benchmark
reaches the reader at `READER_URL` (default `http://reader:8080/v1`).

## Limits

- Cases generated by a language model, then reviewed and corrected by Miguel Amador (Complear) on
  17 November 2026 (`data/REVIEW.md`, which lists the judgement calls still open). Expected answers
  are only as good as the gold facts and the rules.
- Clause titles and the pack's summaries are plain-language paraphrases, not the legal text.
- Not modelled: MDR class I devices needing a notified body, IVDR classes beyond the A–D mapping,
  general-purpose AI models, deployer obligations, and the application dates of 2026/1744.
- Not legal advice.

## Licence

Code under the Apache License 2.0 (`LICENSE`); the data in `data/` under Creative Commons
Attribution 4.0 International (`data/LICENSE`). Model weights are not in this repository. The [Compliance Artifact Collector](https://github.com/Complear/compliance-artifact-collector)
uses this repository's engine for scoping.
