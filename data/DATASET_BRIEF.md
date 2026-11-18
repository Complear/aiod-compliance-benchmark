# Dataset brief — Compliance Draft Benchmark v0.1

Each case is a synthetic description of a software product (mostly health / SaMD) plus the
facts an expert would extract from it. A deterministic rule engine (`cdb/engine.py`) turns the
facts into an EU AI Act (Regulation (EU) 2024/1689) risk tier and the clauses that apply, so a
case's expected answer is fully determined by its `gold_facts`.

## Case format (one JSON object per line)

```json
{"id": "a-001",
 "text": "<the description, 60-140 words>",
 "gold_facts": {
   "ai_system": true,
   "prohibited_practice": false,
   "mdr_class": "IIb",
   "annex_iii_area": "none",
   "art6_3_exception": false,
   "profiling": false,
   "special_category_data": true,
   "remote_biometric_id": false,
   "interacts_with_persons": false,
   "synthetic_content": false,
   "emotion_or_biometric_categorisation": false
 },
 "target_tier": "high_risk_6_1",
 "surface": "notified-body note",
 "split": "test",
 "rationale": "<one or two sentences: why each non-default fact is set>"}
```

## Facts

| Fact | Values | Set it when the text shows... |
| --- | --- | --- |
| `ai_system` | bool | a machine-based system that infers outputs (predictions, recommendations, content, decisions) from inputs, with some autonomy — ML models, LLMs, learned scoring. Fixed hand-written rules, lookup tables, plain calculators and simple statistical estimates (e.g. averages) are `false`; the text must show a learned or inferring model. |
| `prohibited_practice` | bool | an Art. 5(1) practice: subliminal/manipulative techniques causing significant harm; exploiting vulnerabilities (age, disability, social/economic situation) causing significant harm; social scoring; predicting crime risk from profiling alone; untargeted scraping of facial images; emotion recognition in the workplace or education **except for medical or safety reasons**; biometric categorisation inferring race, political opinion, union membership, religion or philosophical beliefs, sex life or orientation; real-time remote biometric identification in public spaces for law enforcement; since Regulation (EU) 2026/1744 (from 2 December 2026), generating sexual images of identifiable people without consent, or child sexual abuse material. |
| `mdr_class` | "none", "I", "IIa", "IIb", "III" | the product is a medical device under MDR 2017/745 (or a safety component of one) with that class, judged against MDR Annex VIII (software that informs diagnostic or therapeutic decisions or monitors physiological processes is at least IIa under Rule 11). An in vitro diagnostic under IVDR 2017/746 maps by notified-body involvement: A to "I", B to "IIa", C to "IIb", D to "III". Non-medical products: "none". |
| `annex_iii_area` | "none", "biometrics", "critical_infrastructure", "education", "employment", "essential_services", "law_enforcement", "migration", "justice_democracy" | the use falls in an Annex III area. Health-relevant examples: emergency patient triage or emergency-call evaluation (essential_services, point 5(d)); eligibility for public healthcare benefits (essential_services, 5(a)); risk assessment and pricing for life or health insurance (essential_services, 5(c)); recruiting or evaluating staff (employment); emotion recognition or biometric categorisation (biometrics). Set the area even when an MDR class is also set. Set it only when the system itself performs a listed use (Annex III lists uses, not sectors): a tool merely deployed in an emergency department, an insurer or an HR team that performs none of the listed uses is "none", and then `art6_3_exception` is false. Point 5(c) is only risk assessment and pricing; point 5(d) is evaluating or classifying emergency calls, dispatch and emergency triage. Transcription or translation that the user sees beside its input, adding nothing (no code, classification or priority), is not a listed use: "none". |
| `art6_3_exception` | bool | only with an Annex III area: the system performs a narrow procedural task, improves the result of a previously completed human activity, detects decision patterns without replacing or influencing the human assessment, or performs a preparatory task. Otherwise `false`. |
| `profiling` | bool | the system profiles natural persons (automated evaluation of personal aspects such as health, behaviour, reliability, work performance). |
| `special_category_data` | bool | the provider processes special categories of personal data (health data, biometric data, ...) specifically to detect or correct bias in the model (Art. 4a(1), formerly Art. 10(5)). Training on health data alone does not set it. |
| `remote_biometric_id` | bool | the system identifies people at a distance by comparing biometric data with a reference database (Annex III 1(a)). One-to-one verification (unlocking a device, confirming a claimed identity) is `false`. |
| `interacts_with_persons` | bool | the system is intended to interact directly with natural persons (chatbot, conversational assistant, voice agent). |
| `synthetic_content` | bool | a generative model composes new audio, image, video or text content: a language model's answers, explanations, summaries or code, generated images or speech (Art. 50(2)). Verbatim transcription, template read-back and scripted voice menus are `false`. Art. 50(2) exempts standard editing and output that does not substantially alter the input; rewriting and translation are judgement calls to flag. |
| `emotion_or_biometric_categorisation` | bool | the system recognises emotions or categorises people from biometric data. |

## How the engine decides (so you can hit a target tier)

1. `ai_system` false → `out_of_scope`.
2. `prohibited_practice` → `prohibited`.
3. `mdr_class` IIa, IIb or III → `high_risk_6_1`.
4. `annex_iii_area` set: if `art6_3_exception` and not `profiling` → not high-risk (continue to 5); else `high_risk_6_2`.
5. any of `interacts_with_persons`, `synthetic_content`, `emotion_or_biometric_categorisation` → `limited`; else `minimal`.

`target_tier` is your intended tier; the engine recomputes it from `gold_facts` and rejects a
case where they disagree.

## Writing rules

- **Facts must follow from the text alone.** Every fact you set must be supported by words in the
  text; every fact left at its default must be at least plausibly absent. Never name the tier,
  an AI Act article, "high-risk", "Annex III" or the MDR class rule; you MAY state the MDR class
  when a real document would (a CE certificate, a notified-body note), and roughly half the
  MDR cases should leave the class implicit (intended purpose and harm make it clear).
- Fictional product and company names only. No real products, people or personal data.
- Vary the **surface**: use at least 8 of: notified-body note, instructions-for-use excerpt,
  tender requirement, investor one-pager, product web page, internal chat message,
  regulatory submission summary, clinical study synopsis, press release, procurement email,
  user forum post, conference abstract. Vary length, tone and order of information.
- No two cases may share an 8-word sequence. Do not copy text from
  `~/jev-lab/data/mdr_aiact/` (you may read it for style only).
- Include traps: a non-AI rule-based device with a high MDR class (`out_of_scope`); an AI
  system of MDR class I (not high-risk via MDR); medical emotion recognition (not prohibited,
  but Annex III biometrics); a wellness app with no medical purpose; an Annex III system whose
  exception is cancelled by profiling.
- `split`: "test" for normal cases; the cases listed as "fresh" in your task use a surface
  style not used elsewhere in your file and get `"split": "fresh"`.
