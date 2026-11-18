# Review of 17 November 2026

Reviewer: Miguel Amador (Complear). `reviewed_by` is set on all 109 cases, including the 16 added after the first review (c-001 to c-016).

## How the cases were checked

- **Scripts:** the engine self-check (`make gold`), the tier and clauses re-derived from every case's facts, duplicate ids, shared 8-word sequences, and any text that names its answer. All pass.
- **AI review:** four language-model reviewers read every case against `DATASET_BRIEF.md`, the AI Act and the MDR. A fifth checked the framework pack against EUR-Lex: the Official Journal text of 12 July 2024 and the consolidated version 02024R1689-20260727.
- **Names:** product and company names were searched on the web, and replacements were searched before use. No trademark register (EUIPO or TMview) was searched.

The reviewer adopted the rules and corrections below; the questions at the end are open for the
reviewer and are recorded here until answered.

## Rules adopted

| Rule | Before | Now |
| --- | --- | --- |
| Annex III area | Set for the sector the product is used in | Set only when the product performs a use Annex III lists. Art. 6(3) arises only for such a product. |
| `synthetic_content` | Applied inconsistently to language-model assistants | True when a generative model composes content: answers, summaries, code or speech. Verbatim transcription, template read-back and scripted voice menus are false. Rewriting and translation are flagged below. |
| MDR class | The class stated in the text, even against Rule 11 | Judged against MDR Annex VIII. A stated class that conflicts with Rule 11 is corrected or flagged. |
| IVDR | Could not be expressed | IVDR classes map by notified-body involvement: A to I, B to IIa, C to IIb, D to III. |
| Pack | EU AI Act as published in 2024 | As amended by Regulation (EU) 2026/1744 (pack version 2026.1). |

## Pack changes (version 2026.1)

- **Art. 10(5) is now Art. 4a(1).** Regulation (EU) 2026/1744 moved the text there word for word. It still applies only to high-risk systems.
- **Art. 50(3) is removed.** It binds deployers of emotion-recognition and biometric-categorisation systems. The pack scores provider duties, so the count goes from 47 to 46 scorable clauses.
- **Art. 49(1) is excluded for Annex III point 2 systems (critical infrastructure).** Those register nationally under Art. 49(5). No case is affected.
- **Not modelled:**
  - the application dates moved by 2026/1744 (2 Dec 2027 for Annex III systems, 2 Aug 2028 for Annex I products);
  - the rewritten Art. 4 (AI literacy) and the new Art. 6(1a)–(1c);
  - the new Art. 5(1)(ba)/(bb) prohibitions. They are added to the brief, but no case involves them.

**To do outside this repository:** Complear's own pack (`priv/frameworks/eu_ai_act_2024_1689@2024.1.json`) needs the same three changes.

## Corrections applied

| Case | Change | Effect |
| --- | --- | --- |
| a-028 | The text said "class I" for urgent-care triage; changed to class IIa (MDR Rule 11) | Tier: high-risk Annex III becomes high-risk MDR |
| b-017 | LLM coding assistant: `interacts_with_persons` and `synthetic_content` set to true | Tier: minimal becomes limited |
| a-029, a-031, a-032, a-034, a-035, a-036, a-037, a-046, a-047 | `annex_iii_area` set to none and `art6_3_exception` to false: none of them performs a listed use | Clauses: Art. 6(3), Art. 6(4) and Art. 49(2) drop out |
| a-025, a-026 | `art6_3_exception` set to false: the system influences the human assessment | None (profiling already made them high-risk) |
| b-001, b-005, b-006, b-009, b-011, b-012 | `synthetic_content` set to true: the text says a language model generates the replies | Clauses: Art. 50(2) added |
| a-008 | Prostate-biopsy grading is an IVDR class C device, recorded as IIb | None |
| b-024, b-044 | The text now states a trained model (it had read "statistical or machine-learning" or left it implicit) | None |
| a-001, a-004, a-005, a-006, a-013, a-020, a-021, a-027, a-028, a-040, a-047, b-001, b-016, b-021, b-026, b-028, b-030, b-039, b-042, b-045 | Names that match real products, brands or bodies replaced with fictional ones. a-040 had named Estonia's real Emergency Response Centre. | None |

b-002 is removed from the raw generator output. It had been rejected because it shared a phrase with a-028, and the correction to a-028 removed that phrase. It never belonged to the dataset.

## Open questions for the reviewer

**Decided by the reviewer, 17 November 2026**

| Case | Decision | Change |
| --- | --- | --- |
| a-023 | Camera-based distress and pain alerts are MDR class IIa (Rule 11). | Text and mdr_class now IIa: high-risk via Art. 6(1), was Annex III. |
| b-021 | Conception-support fertility estimate is MDR class IIa (Rule 11). | Text and mdr_class now IIa: high-risk via Art. 6(1), was minimal. |
| a-033 | Art. 50(2) editing exemption applies when the user can see the input. The interviewer sees their own notes and confirms the rewrite. | synthetic_content false: minimal, was limited. |
| a-040 | Same rule. The call-taker hears the caller's own speech beside the translation. | synthetic_content false: minimal, was limited. |
| a-030 | A transcriber that does not evaluate, classify, prioritise or dispatch calls is not an Annex III point 5(d) use. | Area none, no exception: still minimal, without the Art. 6(3) clauses. |

**Tier-neutral judgement calls**

- **MDR class:**
  - a-002: IIa or IIb.
  - a-004: IIb or III.
  - a-007: IIa or IIb.
- **`special_category_data`:**
  - a-003: subgroups by age and sex, which are not special categories.
  - a-024: a tender asks for accuracy by skin tone.
- **`profiling`:** applied unevenly across per-patient assessments. Cases: a-006, a-018, a-023, a-044, b-012, b-021.
- **`synthetic_content`:** the text does not say the assistant is generative. Cases: a-005, a-009, a-031, a-037, b-008 (template read-back) and a-002 (compiled report).
- **Emotion or biometric analysis:** a-045, where the video-interview score could rely on facial or vocal features.
- **Names:**
  - Corvik Re (a-027) is close to the real Corgi Re and Corvus Insurance.
  - Generic names were kept: CardioCue, CredCheck, StockSense, FormFlow, ScoreCard, Pulsar, Lumina.
  - A trademark search is still to do.

**Coverage gap, closed by new cases:** after the corrections only four cases used the Art. 6(3) exception (a-033, a-038, a-039, a-040), all in `test`, and two tested an AI device of MDR class I (b-009, b-015). Sixteen cases were added in `raw/cases_c.jsonl`, 9 in `test` and 7 in `fresh`. They were reviewed with the reviewer's decisions below.

| Cases | What they test |
| --- | --- |
| c-001 to c-005 | The exception applies: decision-pattern detection (c-001, employment), a narrow procedural task (c-002, education), preparatory tasks (c-003 public benefits, c-004 migration, c-005 insurance). |
| c-006 | The exception would apply, but the system estimates each candidate's reliability: profiling cancels it. |
| c-007 to c-010 | Near misses that replace or effectively set the human decision, so no exception: c-007 public benefits, c-008 education, c-009 emergency calls, c-010 insurance pricing. |
| c-011, c-012, c-015 | AI in class I devices (a patient lift, a rollator, a ward bed: MDR Rule 13), one with a voice assistant. |
| c-013, c-016 | IVD instruments of class A, mapped to class I; c-016 with a language-model assistant. |
| c-014 | A class I walking frame that recognises emotions: not high-risk through the product route, but in the biometrics area. |

**Decided by the reviewer on the new cases**

| Case | Decision | Change |
| --- | --- | --- |
| c-014 | The walking frame stays class I: the emotion alert is part of a device under Rule 13. | None: high-risk only through the biometrics area. |
| a-040 | Transcription or translation that the user sees beside its input, adding nothing such as a code or a classification, is not an Annex III use; a-040 follows a-030. | Area none, no exception: still minimal. Added to `DATASET_BRIEF.md`. |

The new names were checked by web search only; no trademark register was searched.
