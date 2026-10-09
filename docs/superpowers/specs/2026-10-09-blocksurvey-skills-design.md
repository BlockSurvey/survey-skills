# BlockSurvey Skills — Design Spec

**Date:** 2026-10-09
**Status:** Approved for build (autonomous session; owner pre-approved "spec first, then build with Opus")
**Owner:** Raja (BlockSurvey)
**Source of truth being ported:** `blocksurvey-ai-survey-api-function/utils/survey_score/` (rubric 1.2, Jev-based Survey Score) and `docs/superpowers/specs/2026-09-28-survey-score-rubric-v2-proposal.md`

---

## 1. Goal

A public GitHub repo, `blocksurvey/blocksurvey-skills`, that gives anyone using Claude Code, Codex / ChatGPT, Cursor, Gemini CLI or any chat LLM a set of **Agent Skills** to:

1. **Create** a high-conversion survey from a one-line brief, with every survey-methodology best practice baked in (not bolted on afterwards).
2. **Score** any existing survey 0–100 against the same multi-perspective rubric BlockSurvey's in-product Survey Score uses, and get ranked, specific "roast + fix" findings.
3. **Fix**, **pretest**, **template**, **route** (logic), and **export** surveys, so the whole lifecycle happens in the user's own LLM, with no API key and no cost beyond the chat.

Success looks like: a user types "create a churn survey for a B2B SaaS" and gets a survey that would score ≥ 85 on BlockSurvey's Survey Score on the first try, plus a one-click path into BlockSurvey. The repo reads like a product, trends on GitHub, and sends traffic to BlockSurvey.

### What the owner said (verbatim intent)

- "if they use this skill, they should be able to literally create the high performance, I mean high conversion survey with all best practices"
- "I have built the survey score feature ... validating around 10 plus a list of perspective ... Similar way you can use any model like OpenAI or LLM model"
- "I'm going to make this repo public ... build the trending ... use this skill along with their Claude and ChatGPT LLM in their local"
- Reference for presentation: `zhuyansen/awesome-claude-video-skills`

### Assumptions made (owner to correct)

| # | Assumption | Why |
| --- | --- | --- |
| A1 | The repo **contains the skills** (not a curated list of other people's repos). The reference repo is an awesome-list; what we borrow is its presentation: categories, tables, counts, previews, install one-liners, bilingual README. | Owner said "build a list of survey skills under this repo". |
| A2 | Skills follow the **Agent Skills open standard** (`SKILL.md` + `scripts/` + `references/`), so one copy works in Claude Code, Codex CLI, ChatGPT (custom instructions / project files), Cursor, Gemini CLI. Install: `npx skills add blocksurvey/blocksurvey-skills`. | Owner wants Claude **and** ChatGPT users. |
| A3 | **The LLM is the judge; code is the arithmetic.** The Jev rubric is ported as literal judge instructions the host LLM applies; counts, thresholds, weights and the 0–100 composition stay in a dependency-free Python script so the number is deterministic and reproducible. | Mirrors the existing design's split and the cost rule in CLAUDE.md (no API calls → no spend). |
| A4 | A **portable survey JSON** (`survey.schema.json`, this repo) is the interchange format between skills, not BlockSurvey's raw document (~60 keys/question). A mapping table to BlockSurvey question types is included; export produces text/markdown that BlockSurvey's AI Import accepts. | Public users don't have BlockSurvey JSON; BlockSurvey-specific structural audit is out of scope here. |
| A5 | License **MIT** for skills content; BlockSurvey branding in README; "Built with Claude Opus" badge. | Trending repos are permissive; the reference repo has an Opus section. |
| A6 | Phase 1 (this build) = 9 skills + shared references + lint/score scripts + README + CI. Phase 2 (later) = GIF previews, zh-CN README, awesome-list submissions, ChatGPT GPT. | Keep the first public release coherent and testable. |

---

## 2. Non-goals (v1)

- Calling any LLM API from scripts (no keys, no cost, no vendor lock).
- Reproducing BlockSurvey's **structural audit** of its raw JSON (logic-row states, stale keys). That is product-internal.
- Running surveys, collecting responses, or analysing results.
- A web UI. The repo is markdown + scripts.

---

## 3. The knowledge core (what makes the skills "powerful")

Everything is derived from the shipped Survey Score and its v2 proposal, re-expressed so a general LLM can apply it without Jev.

### 3.1 Perspectives (the "10-plus perspectives")

| Code | Perspective | Rubric items (ported from `rubric.py`) | Funnel stage |
| --- | --- | --- | --- |
| A | Purpose & framing | A1 title specific, A2 title respondent-facing, A3 purpose explained, A5 privacy stated, A6 audience stated, A7 objective inferable, **A8 respondent benefit, A9 sponsor named, A10 deadline stated** (v2) | Start |
| B | Structure & flow | B1 logical order, B2 opening question, B3 demographics placement, B4 sections signposted, B5 redundant questions, **B7 end-loading, B8 scale direction consistent** (v2) | Continue / Finish |
| C | Coverage & gaps | C1 objective coverage, C2 has screener, C3 has outcome question, C4 missing why, C5 obvious gap (+ gap-topic list), C6 demographics proportionate, **C7 attention check** (v2) | Act |
| D | Question quality (per question) | Q1 clarity, Q2 double-barreled, Q3a leading, Q3b presuming, Q4 jargon, Q5 relevance, Q6 options not exhaustive, Q7 options overlap, Q8 scale unbalanced, Q9 type fit, Q10 depends on prior, Q11 requires visual, Q12 sensitive, Q13 grammar, Q14 options parallel, **Q15 abandon risk, Q16 sensitive reassured, Q17 negative wording, Q18 hypothetical, Q19 recall period, Q20 option double-barreled, Q21 social desirability, Q22 units stated, Q23 actionable, Q24 intent, Q25 best type** (v2) | Answer well |
| E | Respondent experience | E1 tone consistent, E2 burden, E3 thank-you quality, E4 welcome motivates, E5 reading level, E6 length justified, **E7 welcome scannable, E8 straight-lining risk, E9 language consistent** (v2) | Finish |
| F | Trust & ethics | F1 sensitive topics (info), F2 consent language, F3 incentive clear, F4 manipulative framing, **F5 contact provided** (v2) | Start |
| G | Conversion (v2) | Composite of A8, A9, E7, E8, B7, mean Q15, static S27–S34, S46–S48 | All |
| S | Static / deterministic checks | S01–S28 (shipped) + S27–S48 (v2) — see §3.3 | — |
| K | Survey kind & audience | `K_survey_kind` (research / feedback / form / quiz / assessment / information) and `X2_audience_kind`; selects weight profile and which items apply | — |

Every item keeps its original **id**, **instructions (verbatim)**, **criteria levels (worst → best)**, **weight**, **severity per level**, **roast** and **fix** text, and **applicability** rules (e.g. `Q3b` skipped when `shown_when` is set; `Q5` skipped for gated follow-ups; `C2/C3/C4/C6/F2` only for research/feedback kinds). The roast voice is a feature: specific, honest, a little funny, never cruel.

### 3.2 Scoring (deterministic, in `scripts/survey_score_calc.py`)

Ported from `scoring.py`:

- Score level → `level / (levels − 1)`; Noul → `p` or `1 − p` (`good_when_yes`).
- Category score = weighted mean − static deductions (high −0.12, medium −0.06, low −0.02; repeats +25 % each, cap 2×; category cap 0.35), clamp 0..1.
- Overall = 100 × Σ(category weight × category score). Weight profile by survey kind (v2 §7.1 table; default A .20 B .15 C .20 D .25 E .15 F .05; G added for customer-facing kinds).
- Blockers (no title, no questions, empty label, too few options, impossible selection limit) → verdict `not_ready`, cap 49.
- Grade/verdict: ≥ 90 A, 80–89 B, 75–79 C ready; 70–74 C, 60–69 D, 50–59 E needs_work; < 50 F not_ready.
- Funnel view `{start, continue, finish, answer_quality, actionability}` from the item → stage mapping.
- Findings sorted blocker → high → medium → low → info, then weight; top finding feeds the one-line summary.

The LLM never does the arithmetic. It fills a **judgments JSON** (`{item_id: {level|p, confidence, note}}` per survey and per question); the script turns that into the report. If no Python is available (plain ChatGPT), the skill includes a short manual-tally fallback that yields the same grade band.

### 3.3 Static checks (in `scripts/survey_lint.py`, no LLM)

Ported: S01 no title, S02 no questions, S07 no description, S08 no welcome, S09 no thank-you, S10 duplicate labels, S11 duplicate options, S12 numeric range gap/overlap (full `parse_range` port), S13 selection-hint/type mismatch, S14 selection count unenforced, S15 no time expectation, S16 time mismatch (per-type seconds table), S17 length fatigue (> 30 / > 50), S18 all-required-long (+ 80 % tier), S19 no open-ended, S21 anonymous but PII, S24 no progress bar long, S27 monotony run (8+ same type), S28 unreachable question (jump graph fixed point).
Added from v2: S27 welcome too long (> 120 words), S28 early friction (first 3 demanding + required), S30 matrix too large (> 5 cols / > 8 rows), S31 consecutive matrices, S32 ranking > 7, S33 long radio list (> 10), S34 open-ended overload, S35 loaded words (pre-filter), S36 scale endpoints only, S37 NPS non-standard, S38 "None" not exclusive, S39 Other without text, S40 long list not randomised, S42 shouting/noise, S43 label > 35 words, S44 group single child, S45 yes/no mismatch, S46 first question open text, S47 no logic on long survey, S48 PII before content.

Ids that collide between the shipped set and the v2 proposal (S27, S28) are renumbered in this repo (`S27_monotony_run`, `S28_unreachable_question` keep their shipped ids; v2's become `S50_welcome_too_long`, `S51_early_friction`). The lint catalog in `references/static-checks.md` is the single source of truth.

### 3.4 Best-practice playbook (for creation)

`references/playbook.md` turns the rubric inside-out into **rules to write by**, ordered by the funnel: title & welcome (WIIFM, sponsor, time, privacy, consent), opener, screener + exit logic, section signposting, question writing (one thing per question, neutral, no presumption, plain words, recall window, units, balanced labelled scales, exhaustive & exclusive options, parallel options, "Other/None/Prefer not to say" rules), type selection table, length budget (≤ 10 min, ≤ 20 questions default; ≤ 30 % open-ended, open-ended last), demographics last with a reason, sensitive questions with reassurance + opt-out, thank-you with what-happens-next, mobile rules (matrix limits, no ranking > 7), accessibility (no image-only questions), trust (consent, contact, incentive delivery). Each rule cites the rubric id it satisfies so creation and scoring agree by construction.

### 3.5 Portable survey JSON (`schemas/survey.schema.json`)

```jsonc
{
  "title": "", "description": "", "kind": "research|feedback|form|quiz|assessment|information",
  "audience": "", "purpose": "", "sponsor": "", "language": "en",
  "welcome": { "title": "", "description": "", "button": "Start" },
  "thank_you": { "title": "", "description": "" },
  "settings": { "stated_minutes": 5, "progress_bar": true, "anonymous": false, "randomize_questions": false,
                "sign_in_required": false, "captcha": false, "multiple_submissions": false },
  "questions": [
    { "ref": "Q1", "type": "single_choice", "label": "", "description": "", "required": true,
      "options": ["..."], "has_other": false, "has_none": false, "has_prefer_not_to_answer": false,
      "randomize_options": false, "exclusive_options": ["None of the above"],
      "rows": [], "columns": [],                         // matrix
      "scale": { "min": 0, "max": 10, "labels": { "0": "Not at all likely", "10": "Extremely likely" } },
      "selection": { "min": null, "max": null },         // multi_choice limits
      "shown_when": "Q1 is 'Yes'",                       // display logic, plain text
      "jumps": [ { "when": "Q1 is 'No'", "to": "end" } ],// skip logic; when=null is the default jump
      "group": null, "sensitive": false, "has_image": false, "collects_pii": false,
      "role": "question|information|consent",
      "intent": "screener|demographic|behaviour|attitude|outcome|open_feedback|contact_or_admin" }
  ]
}
```

Types: `single_choice, multi_choice, dropdown, yes_no, short_text, long_text, number, rating, nps, likert, matrix, ranking, slider, date, email, phone, file, statement, consent, group`. `references/blocksurvey-types.md` maps each to BlockSurvey `bType` (and to Typeform/Google Forms names for export).

---

## 4. The skills (Phase 1)

Repo layout (Agent Skills standard; each skill self-contained, shared material symlinked or copied by the build script so each skill still works when installed alone):

```
blocksurvey-skills/
├── README.md  README.zh-CN.md  LICENSE  CONTRIBUTING.md  CHANGELOG.md
├── skills/
│   ├── survey-create/        SKILL.md  references/{playbook,question-types,examples}.md
│   ├── survey-score/         SKILL.md  references/{rubric,static-checks,scoring}.md  scripts/{survey_lint.py,survey_score_calc.py}
│   ├── survey-lint/          SKILL.md  scripts/survey_lint.py
│   ├── survey-fix/           SKILL.md  references/fix-patterns.md
│   ├── survey-pretest/       SKILL.md  references/personas.md
│   ├── survey-logic/         SKILL.md  references/logic-patterns.md
│   ├── survey-templates/     SKILL.md  templates/*.json (pre-scored)
│   ├── survey-copy/          SKILL.md  references/copy-patterns.md
│   └── survey-export/        SKILL.md  scripts/survey_export.py  references/formats.md
├── shared/                   canonical copies: rubric.md, static-checks.md, playbook.md, scoring.md, schema, scripts
├── schemas/survey.schema.json
├── examples/                 briefs → surveys → score reports (JSON + MD)
├── prompts/                  single-file prompt pack for plain ChatGPT / Claude.ai (no file system)
├── tests/                    pytest for scripts; skill-structure validation
├── scripts/                  build (sync shared → skills), validate (skills-ref), catalog (README tables)
└── .github/workflows/ci.yml  ISSUE_TEMPLATE/
```

| # | Skill | Trigger (description keywords) | Input → Output | Depends on |
| --- | --- | --- | --- | --- |
| 1 | **survey-create** | create / design / build / draft a survey, questionnaire, NPS, CSAT, feedback form, research study | Brief (+ optional audience, kind, length, must-ask) → clarify ≤ 3 questions only if essential → survey JSON + readable markdown → **self-score with survey-score, iterate until ≥ 85 or 2 passes** → report | playbook, templates, score |
| 2 | **survey-score** | score / review / audit / roast / grade / evaluate / is this survey good | Survey (JSON, markdown, pasted text, Google Form export) → normalise to JSON → lint (script) → judge rubric (LLM, judgments JSON) → calc (script) → report: score, grade, verdict, categories, funnel, ranked roasts with fixes, per-question table | rubric, static-checks, scoring, lint, calc |
| 3 | **survey-lint** | lint / quick check / deterministic / no LLM | Survey JSON → static findings only; ~1 ms; exit code for CI | lint |
| 4 | **survey-fix** | fix / rewrite / improve / split / rebalance / apply the findings | Survey + score report (or a single finding) → patched survey + diff + before/after mini-score | fix-patterns, rubric |
| 5 | **survey-pretest** | pretest / pilot / simulate respondents / cognitive interview / where will people drop | Survey → 5–8 synthetic personas from the audience → each walks the survey thinking aloud → confusion, abandon points, satisficing, time per persona → prioritised issues | personas, rubric |
| 6 | **survey-logic** | skip logic / branching / screener / display logic / quotas / routing | Survey + routing intent → `shown_when` / `jumps` filled in, screener + exit, reachability check (lint S28), logic table in plain English | logic-patterns, lint |
| 7 | **survey-templates** | template / starter / standard NPS, CSAT, CES, PMF, churn, onboarding, employee engagement, event feedback, pricing (Van Westendorp), academic consent | Kind + a few variables → instantiated pre-scored template | templates, create |
| 8 | **survey-copy** | welcome screen / thank-you page / invitation email / reminder / subject line | Survey → welcome, thank-you, invite + 2 reminders, subject lines; conversion copy rules (WIIFM, time, privacy, sponsor, deadline) | copy-patterns |
| 9 | **survey-export** | export / import into BlockSurvey / Typeform / Google Forms / CSV / markdown | Survey JSON → markdown (BlockSurvey AI Import ready), CSV, plain text, Typeform-ish JSON; prints "open blocksurvey.io → AI import → paste" steps | export script, formats |

Design rules for every SKILL.md:

- Frontmatter per spec: `name` = directory name, `description` ≤ 1024 chars with what + when + keywords, `license: MIT`, `metadata: {author: blocksurvey, version, category, funnel}`.
- Body ≤ 500 lines; progressive disclosure: steps + output contract in the body, rubric/playbook in `references/`.
- Output contract is explicit (headings, JSON block) so results are consistent across models.
- Cost discipline: no API calls; big references are loaded only when needed; the score skill judges the survey in **one pass** (all items at once) rather than one call per item.
- Each skill ends with a "Next" line pointing at the natural next skill (create → score → fix → export) and a one-line BlockSurvey call-to-action.

---

## 5. Data flow

```
brief ──survey-create──▶ survey.json ──survey-score──▶ report.json ──survey-fix──▶ survey.json'
                              │                 ▲                                      │
                     survey-templates     survey-lint (script)                   survey-pretest
                              │                                                        │
                        survey-logic ◀──────────────────────────────────────────────────┘
                              │
                        survey-copy ──▶ survey-export ──▶ markdown / CSV / BlockSurvey AI Import
```

`survey-score` internals: `normalise → survey_lint.py (static findings) → LLM judges rubric items in one pass → judgments.json → survey_score_calc.py (findings + lint → score, grade, verdict, funnel) → render report.md`.

---

## 6. Error handling

- Input not parseable as survey JSON → the skill extracts questions from text/markdown into the schema first and says what it inferred (type guesses are flagged `inferred: true`).
- Scripts: pure Python 3.9+, stdlib only, never crash on `None`/wrong types (port the `_d/_l/_text` convention); invalid JSON → exit 2 with a one-line reason; findings → exit 1 if any blocker/high (for CI use), else 0.
- No Python available → score skill prints the manual tally table; lint skill lists the checks for the LLM to apply by hand (lower fidelity, stated).
- Over 150 questions → score in chunks of 50 for per-question items; survey-level once.

---

## 7. Testing & quality gates

- `tests/test_lint.py`: one test per static check with minimal synthetic surveys (ported from `test_static_checks.py` cases, e.g. `Under 25 / 26-35` gap, "select multiple" on single choice).
- `tests/test_score_calc.py`: normalisation, weights sum to 1 per profile, blocker cap, grade boundaries, finding order, repeat dampening.
- `tests/test_export.py`: round trip JSON → markdown → JSON for every type.
- `tests/test_skills.py`: every `skills/*/SKILL.md` has valid frontmatter (name = dir, description ≤ 1024, no uppercase), body ≤ 500 lines, every relative link resolves, shared files in sync with `shared/`.
- CI (GitHub Actions): pytest + `skills-ref validate` on push/PR; `scripts/build_catalog.py --check` ensures README tables match `skills/`.
- Golden examples: 3 briefs (SaaS churn, event feedback, employee engagement) with committed survey.json and score report; a reviewer should recognise the roasts as correct.
- Manual acceptance (owner): run `survey-create` in Claude Code and in Codex, paste the result into BlockSurvey, run the in-product Survey Score, expect ≥ 85.

---

## 8. Discoverability ("build the trending")

- README (EN + zh-CN) modelled on the reference list: hero line, badges (license, skills count, "works with" Claude Code / Codex / Cursor / Gemini CLI / ChatGPT, Built with Claude Opus), 30-second install (`npx skills add blocksurvey/blocksurvey-skills`, plus manual copy for ChatGPT projects), **category tables** (Create / Validate / Improve / Ship) with one-line "what it does" + "try: …" prompt, a before/after score example, a GIF slot per skill, "How scoring works" section (perspectives table), FAQ, Contributing, Star History.
- GitHub topics: `agent-skills, claude-skills, claude-code, codex, chatgpt, cursor, survey, surveys, questionnaire, survey-design, nps, customer-feedback, market-research, blocksurvey, awesome-list`.
- `prompts/` pack lets ChatGPT-web users use the skills without a file system (copy one file into a Project / custom GPT).
- Phase 2: submit to `travisvn/awesome-claude-skills`, `gmh5225/awesome-skills`, `libukai/awesome-agent-skills`, skills.sh, agentskillsfinder; record previews; a BlockSurvey blog post; a GPT in the GPT Store.

---

## 9. Build plan (summary; detail in the implementation plan)

1. Scaffold repo, LICENSE, schema, `shared/` knowledge files extracted from `rubric.py`, `static_checks.py`, `scoring.py`, the design spec and the v2 proposal (this is the critical path; done by the lead with direct access to the source).
2. Port `survey_lint.py` and `survey_score_calc.py` to the portable schema with tests (TDD).
3. Build the 9 skills in parallel with Opus subagents from this spec + `shared/`; each subagent gets one skill, the spec, and the shared references.
4. Build script syncs `shared/` into skills; validate; examples; README; CI.
5. Review pass (code-review on scripts, skill-structure tests), then owner acceptance.

---

## 10. Open decisions for the owner (not blocking)

1. Repo name and org: assumed `blocksurvey/blocksurvey-skills`.
2. Weight profiles per survey kind (v2 §7.1) are literature defaults; owner may retune.
3. Whether to include the G (conversion) category in the composite score or only the funnel view. Assumed: included for customer-facing kinds, as v2 recommends.
4. Tone of roasts in a public repo: kept as in product (direct, witty) with a `--polite` output mode.
