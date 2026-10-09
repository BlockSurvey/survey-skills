# BlockSurvey Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a public repo of 9 Agent Skills (SKILL.md standard) that let any LLM user create, score, fix, pretest, route, template, copy-write and export high-conversion surveys, porting BlockSurvey's Survey Score rubric.

**Architecture:** Knowledge lives once in `shared/` (rubric, static checks, playbook, scoring, schema, scripts) and is synced into each skill's `references/` and `scripts/` by `scripts/build.py` so every skill works when installed alone. The LLM judges rubric items and emits a judgments JSON; two stdlib Python scripts (`survey_lint.py`, `survey_score_calc.py`) do all counting and arithmetic deterministically. Skills are markdown instruction sets with explicit output contracts.

**Tech Stack:** Markdown (Agent Skills spec), Python 3.9+ stdlib only (scripts), pytest (tests), GitHub Actions (CI), `npx skills add` for install.

**Spec:** `docs/superpowers/specs/2026-10-09-blocksurvey-skills-design.md`

## Global Constraints

- Scripts: Python ≥ 3.9, **stdlib only**, never crash on `None`/wrong types (`_d/_l/_text` helpers), exit codes: 0 ok, 1 findings at blocker/high, 2 invalid input.
- No LLM API calls anywhere in the repo. No API keys. (CLAUDE.md cost rule.)
- SKILL.md frontmatter: `name` == directory name, lowercase/hyphens, `description` 1–1024 chars with what + when + keywords, `license: MIT`, `metadata.author: blocksurvey`, `metadata.version: "1.0.0"`, `metadata.category` ∈ {create, validate, improve, ship}. Body ≤ 500 lines. Relative links one level deep.
- Rubric item ids, instructions, criteria, weights, severities, roast/fix text are copied **verbatim** from `rubric.py` (rubric 1.2) and the v2 proposal; this repo's rubric version string is `"bs-skills-1.0"`.
- Portable schema types: `single_choice, multi_choice, dropdown, yes_no, short_text, long_text, number, rating, nps, likert, matrix, ranking, slider, date, email, phone, file, statement, consent, group`.
- Static check ids: shipped ids keep their numbers; v2 collisions renumbered: `S50_welcome_too_long`, `S51_early_friction`. All other v2 ids (S30–S48) unchanged.
- Every skill body ends with a `## Next` section naming the next skill in the flow and one BlockSurvey call-to-action line.
- Commit after every task; conventional commit messages; co-author line per session reminder.

## Review Focus

1. A survey pasted as **plain text / markdown** (no JSON) must still be scorable: `survey-score` normalises it first and flags inferred types. Test: `tests/test_normalise_md.py` (Task 6) round-trips the markdown export back to JSON.
2. **Options that are numeric ranges with currency and suffixes** (`£25-40k`, `Under 25`, `0-0,5`) must not produce false gap findings. Test in Task 3 (`test_parse_range_*`).
3. **Logic with deleted / unknown targets** (`jumps.to` naming a ref that does not exist) must behave like `end`, not crash, and must still feed S28. Test in Task 3 (`test_unreachable_with_unknown_target`).
4. **Judgments JSON with missing items / out-of-range values** (LLM skipped an item or wrote `p: 1.4`) must be clamped or treated as absent, with `meta.partial = true`, never a crash. Test in Task 4 (`test_calc_tolerates_bad_judgments`).
5. A survey of **0 answerable questions but with statements only** must be a blocker (`S02`) and still produce a full report. Test in Task 3 and Task 4.

---

## File Structure

```
blocksurvey-skills/
├── README.md                         catalog + install + how scoring works (Task 12)
├── README.zh-CN.md                   Phase 2 stub pointing at README (Task 12)
├── LICENSE                           MIT (Task 1)
├── CONTRIBUTING.md, CHANGELOG.md     (Task 12)
├── schemas/survey.schema.json        JSON Schema draft-07 for the portable survey (Task 1)
├── shared/
│   ├── rubric.md                     every judge item: id, scope, primitive, instructions, criteria, weight, severity, roast, fix, applies, kinds (Task 2)
│   ├── static-checks.md              every lint check: id, severity, condition, roast, fix (Task 2)
│   ├── scoring.md                    normalisation, deductions, weight profiles, grades, funnel mapping, judgments JSON contract (Task 2)
│   ├── playbook.md                   write-by rules ordered by funnel, each citing rubric ids (Task 2)
│   ├── question-types.md             portable type → BlockSurvey bType / Typeform / Google Forms, when to use each (Task 2)
│   ├── survey-format.md              the portable JSON explained + markdown form (Task 2)
│   └── scripts/
│       ├── survey_lint.py            static checks (Task 3)
│       ├── survey_score_calc.py      judgments + lint → report (Task 4)
│       ├── survey_export.py          JSON → markdown/csv/text; markdown → JSON (Task 5)
│       └── survey_common.py          load/normalise helpers shared by the three (Task 3)
├── skills/<name>/SKILL.md (+ references/, scripts/ synced from shared)   (Tasks 7–11)
├── templates/*.json                  pre-scored templates (Task 10)
├── examples/<brief>/{brief.md,survey.json,report.md}                    (Task 11)
├── prompts/<skill>.md                single-file prompt pack (Task 12)
├── scripts/build.py                  sync shared → skills; --check mode (Task 6)
├── scripts/validate_skills.py        frontmatter/body/link checks (Task 6)
├── scripts/build_catalog.py          README skill tables from frontmatter (Task 12)
├── tests/                            pytest (Tasks 3–6)
└── .github/workflows/ci.yml          pytest + validate + build --check (Task 6)
```

---

### Task 1: Scaffold, license, schema

**Files:**
- Create: `LICENSE`, `.gitignore`, `schemas/survey.schema.json`, `requirements-dev.txt` (`pytest>=8`), `pyproject.toml` (pytest config only)

**Interfaces:**
- Produces: `schemas/survey.schema.json` — the portable survey schema from spec §3.5; required top-level keys `title`, `questions`; question required keys `ref`, `type`, `label`.

- [ ] **Step 1: Write the schema**

Draft-07 JSON Schema. `type` enum = the 20 portable types. `questions[].jumps[].to` is a ref string or `"end"`. `shown_when` and `jumps[].when` are free-text strings (plain English conditions; lint only parses the ref prefix `Qn`). `settings` keys as in spec §3.5 with defaults. `additionalProperties: true` everywhere (be lenient).

- [ ] **Step 2: Write `tests/test_schema.py`**

```python
import json, pathlib
SCHEMA = json.loads(pathlib.Path("schemas/survey.schema.json").read_text())
def test_schema_lists_all_types():
    types = SCHEMA["definitions"]["question"]["properties"]["type"]["enum"]
    assert set(types) == {"single_choice","multi_choice","dropdown","yes_no","short_text","long_text","number",
        "rating","nps","likert","matrix","ranking","slider","date","email","phone","file","statement","consent","group"}
def test_minimal_survey_keys():
    assert SCHEMA["required"] == ["title", "questions"]
```

- [ ] **Step 3: Run `python -m pytest tests/test_schema.py -q` → PASS. Commit** `chore: scaffold repo with license and portable survey schema`.

---

### Task 2: Shared knowledge files (the port)

**Files:**
- Create: `shared/rubric.md`, `shared/static-checks.md`, `shared/scoring.md`, `shared/playbook.md`, `shared/question-types.md`, `shared/survey-format.md`
- Source: `.../blocksurvey-ai-survey-api-function/utils/survey_score/{rubric.py,static_checks.py,scoring.py,schema.py}`, `docs/superpowers/specs/2026-09-28-survey-publish-score-design.md` §5–7, `...-rubric-v2-proposal.md` §2–7

**Interfaces:**
- Produces: `rubric.md` item table with columns `id | scope | primitive | applies | kinds | weight | instructions | criteria (worst→best) | severity | roast | fix | funnel`. Every id in `rubric.md` must appear in `survey_score_calc.py`'s `ITEMS` table (Task 4) and vice versa.
- Produces: `scoring.md` **Judgments JSON contract**:

```jsonc
{
  "rubric_version": "bs-skills-1.0",
  "survey_kind": "research", "audience_kind": "prospects_or_general_public",
  "survey": { "A1_title_specific": {"level": 1, "confidence": 0.8, "note": "…"},
              "A5_privacy_stated": {"p": 0.1, "note": "…"}, "C5_gap_topic": {"choice": "pricing", "confidence": 0.7} },
  "questions": { "Q1": { "Q1_clarity": {"level": 3, "confidence": 0.9}, "Q2_double_barreled": {"p": 0.05}, "Q24_intent": {"choice": "demographic", "confidence": 0.9} } }
}
```

- [ ] **Step 1: Generate `rubric.md` from `rubric.py`** with a throwaway extraction script in the scratchpad (import-free: regex over the S(...)/N(...)/L(...) calls is fragile; instead run `python - <<EOF` inside the API repo's `env/bin/python` with `from utils.survey_score.rubric import SURVEY_ITEMS, QUESTION_ITEMS, OVERVIEW_LOCATORS, ROLE_ITEM, GAP_TOPICS, SURVEY_KINDS, ROLES` and dump to markdown). Then append the v2 items (A8–A10, B7, B8, C7, E7–E9, F5, F3a/F3b split, Q15–Q25, X2 audience kinds) copied verbatim from the v2 proposal tables, each with a `funnel` column.
- [ ] **Step 2: Write `static-checks.md`** from spec §5.2 table + `static_checks.py` constants + v2 §6 table, applying the id renumbering rule. Columns `id | severity | category | condition (exact numbers) | roast | fix | funnel`.
- [ ] **Step 3: Write `scoring.md`** from `scoring.py` and spec §7: normalisation, deductions (−0.12/−0.06/−0.02, +25 % repeats cap 2×, category cap 0.35), neutral 0.70 for missing evidence, blockers cap 49, grade table, weight profiles (v2 §7.1 incl. G), funnel mapping, NOUL thresholds (0.7/0.3/0.85/0.15, SENSITIVE 0.8, LOW_CONFIDENCE 0.35, SCORE_CONFIDENT 0.6), the judgments JSON contract, and the **manual tally fallback** (count findings by severity → grade band).
- [ ] **Step 4: Write `playbook.md`** (spec §3.4): ~12 sections in funnel order; each rule as `- **Rule.** Why. (satisfies A3, E4)`; include the length budget table, the type-selection table, option-writing rules, scale rules (balanced, fully labelled, same direction, NPS 0–10 "How likely… recommend"), demographics-last, sensitive-with-opt-out, mobile limits, accessibility.
- [ ] **Step 5: Write `question-types.md`** (portable type → BlockSurvey bType from `schema.py` BTYPE map; seconds-per-type table for time estimates; Typeform/Google Forms names) and `survey-format.md` (JSON walkthrough + the markdown form that `survey_export.py` reads/writes, see Task 5).
- [ ] **Step 6: Review against source** — count items: survey-level 29 (+ v2 12), per-question 14 (+ 7 locators + v2 11), static 27 shipped + 21 v2. Commit `docs: shared rubric, static checks, scoring, playbook, formats`.

---

### Task 3: `survey_common.py` + `survey_lint.py` (TDD)

**Files:**
- Create: `shared/scripts/survey_common.py`, `shared/scripts/survey_lint.py`, `tests/test_lint.py`, `tests/fixtures/*.json`

**Interfaces:**
- `survey_common.load_survey(path_or_text: str) -> dict` (JSON file, JSON string, or markdown via `survey_export.from_markdown` — markdown import wired in Task 5)
- `survey_common.normalise(survey: dict) -> dict` — fills defaults, assigns refs `Q1..` if missing (`Qn.m` for group children), strips HTML, decodes entities, drops empty options, computes `stats` (`answerable_questions, required_answerable, open_ended_questions, pii_questions, questions_with_logic, estimated_minutes, stated_minutes, top_level_questions`), `reached_from/unreachable` via jump graph fixed point.
- `survey_lint.run(survey: dict) -> list[Finding]` where `Finding = {"id","severity","category","scope","question_ref","question_label","roast","fix","evidence":{"kind":"static",...}}`
- CLI: `python survey_lint.py survey.json [--json] [--polite]` → markdown table or JSON; exit codes per Global Constraints.

- [ ] **Step 1: Tests first** — one test per check, minimal synthetic surveys, e.g.:

```python
from survey_lint import run
def q(ref, type="single_choice", label="Q?", options=None, **kw):
    return {"ref": ref, "type": type, "label": label, "options": options or ["A","B"], "required": True, **kw}
def ids(s): return {f["id"] for f in run(s)}
def test_no_title_is_blocker():
    f = [x for x in run({"title": "", "questions": [q("Q1")]}) if x["id"] == "S01_no_title"][0]
    assert f["severity"] == "blocker"
def test_numeric_range_gap():
    s = {"title": "T", "questions": [q("Q1", options=["Under 25","26-35","36-45","Over 45"])]}
    assert "S12_numeric_range_gap" in ids(s)
def test_currency_suffix_ranges_touching_no_gap():
    s = {"title": "T", "questions": [q("Q1", options=["£25-40k","£40-60k","£60-80k"])]}
    assert any("both contain 40" in f["roast"] for f in run(s) if f["id"]=="S12_numeric_range_gap")
def test_decimal_comma_not_a_range():
    s = {"title": "T", "questions": [q("Q1", options=["0-0,5","0,5-1","1-2"])]}
    assert "S12_numeric_range_gap" not in ids(s)
def test_select_multiple_on_single_choice():
    s = {"title":"T","questions":[q("Q1", label="Select all that apply")]}
    assert "S13_selection_hint_type_mismatch" in ids(s)
def test_unreachable_with_unknown_target():
    s = {"title":"T","questions":[q("Q1", jumps=[{"when": None, "to": "Q99"}]), q("Q2"), q("Q3")]}
    f = [x for x in run(s) if x["id"]=="S28_unreachable_question"]
    assert f and set(f[0]["evidence"]["refs"]) == {"Q2","Q3"}
def test_statements_only_is_blocker():
    s = {"title":"T","questions":[{"ref":"Q1","type":"statement","label":"Hi"}]}
    assert "S02_no_questions" in ids(s)
def test_matrix_too_large():
    s = {"title":"T","questions":[{"ref":"Q1","type":"matrix","label":"Rate","rows":list("abcdefghi"),"columns":list("123456")}]}
    assert "S30_matrix_too_large" in ids(s)
def test_null_safety():
    run({"title": None, "questions": [None, 1, "x", {}, {"ref":"Q1","type":None,"label":None,"options":None,"jumps":[None,{}]}]})
```
Also: S10, S11, S16, S17, S18, S19, S21, S24, S27, S31–S48, S50, S51 — one test each, asserting presence and severity.

- [ ] **Step 2: Run → FAIL (module missing).**
- [ ] **Step 3: Implement** `survey_common.py` then `survey_lint.py`, porting `parse_range`, `numeric_range_issues`, hint regexes, time estimate (seconds table from `schema.py`), monotony run, jump-graph reachability (`defaultJumpTo`/first satisfied rule semantics simplified: `jumps` list in order; `when: null` = default; unknown target = end; group reached when any child reached), and every v2 static check with the exact thresholds in `static-checks.md`.
- [ ] **Step 4: Run → PASS. Commit** `feat(scripts): portable survey lint with static checks`.

---

### Task 4: `survey_score_calc.py` (TDD)

**Files:**
- Create: `shared/scripts/survey_score_calc.py`, `tests/test_score_calc.py`, `tests/fixtures/judgments_*.json`

**Interfaces:**
- `ITEMS: dict[id, Item]` with `Item = {"category","scope","primitive","levels"|None,"weight","good_when_yes","severity":{level|"noul": sev},"roast","fix","applies","kinds","funnel","informational"}` — generated from `rubric.md` content (hand-copied constants; a test asserts `rubric.md` ids == `ITEMS` keys).
- `calc(survey: dict, judgments: dict, lint_findings: list) -> Report` where

```jsonc
Report = { "score": 63, "grade": "D", "verdict": "needs_work", "summary": "…",
  "categories": [{"id":"purpose","label":"Purpose & framing","weight":0.2,"score":58,"findings":3}, …],
  "funnel": {"start":{"score":71,"drivers":[…]}, "continue":…, "finish":…, "answer_quality":…, "actionability":…, "predicted_completion_band":"low"},
  "findings": [Finding…],  "findings_by_id": [{"id","severity","category","count","question_refs","fix"}],
  "questions": [{"ref","type","label","score","finding_ids"}],
  "stats": {…}, "meta": {"rubric_version":"bs-skills-1.0","weight_profile":"research","partial":false,"missing_items":[…]} }
```
- CLI: `python survey_score_calc.py survey.json judgments.json [--lint] [--json|--md] [--polite]`; `--lint` runs `survey_lint.run` internally.

- [ ] **Step 1: Tests first**

```python
from survey_score_calc import calc, ITEMS, normalise_score, normalise_noul, grade_for
def test_rubric_md_matches_items():
    import re, pathlib
    md_ids = set(re.findall(r"^\| `([A-Z]\d{1,2}[a-z]?_[a-z_]+|[A-Z]_[a-z_]+)`", pathlib.Path("shared/rubric.md").read_text(), re.M))
    assert md_ids == set(ITEMS)
def test_weights_sum_to_one_per_profile():
    from survey_score_calc import WEIGHT_PROFILES
    for k, w in WEIGHT_PROFILES.items(): assert abs(sum(w.values()) - 1) < 1e-6, k
def test_score_normalisation(): assert normalise_score(1, 3) == 0.5
def test_noul_good_when_yes(): assert normalise_noul(0.9, True) == 0.9 and normalise_noul(0.9, False) == 0.1
def test_grades():
    assert grade_for(90, False) == ("A","ready") and grade_for(74, False) == ("C","needs_work") and grade_for(95, True) == ("F","not_ready")
def test_blocker_caps_at_49(survey_min, judgments_perfect):
    r = calc(survey_min | {"title": ""}, judgments_perfect, [{"id":"S01_no_title","severity":"blocker","category":"purpose","scope":"survey","roast":"","fix":""}])
    assert r["score"] <= 49 and r["verdict"] == "not_ready"
def test_noul_strong_band_downgrades():
    # p = 0.75 on a high item → reported medium + uncertain
def test_repeat_dampening():
    # same static id × 6 → deduction == base * 2 (cap)
def test_calc_tolerates_bad_judgments(survey_min):
    r = calc(survey_min, {"survey": {"A1_title_specific": {"level": 9}}, "questions": {"Q1": {"Q2_double_barreled": {"p": 1.4}}}}, [])
    assert r["meta"]["partial"] is True and 0 <= r["score"] <= 100
def test_finding_order(): # blocker, high, medium, low, info then weight desc
def test_funnel_keys(): # all five stages + band present
```

- [ ] **Step 2: Run → FAIL. Step 3: Implement** (port `scoring.py` logic: normalise, applicability (`item_applies` incl. `shown_when`, role, kinds), category composition, deductions, hybrid checks S22/S23/S25/S26 from judgments (`Q10`, `Q12`, `Q11`), locator → `question_refs` attachment, funnel, summary line = top finding roast, markdown renderer, `--polite` strips roast and keeps fix).
- [ ] **Step 4: Run → PASS. Commit** `feat(scripts): deterministic survey score calculator`.

---

### Task 5: `survey_export.py` (TDD)

**Files:**
- Create: `shared/scripts/survey_export.py`, `tests/test_export.py`

**Interfaces:**
- `to_markdown(survey) -> str` — the canonical markdown form (documented in `survey-format.md`):

```
# Title
> description
**Audience:** … · **Kind:** research · **Time:** ~5 min
## Welcome
…
## Questions
### Q1. Label  `single_choice` (required)
Description line
- [ ] Option A
- [ ] Option B
- [ ] Other (please specify)
> Shown when: Q0 is 'Yes'
> Jump: if Q1 is 'No' → end
### Q2. … `matrix`
| | Col1 | Col2 |
| Row1 | | |
## Thank you
…
```
- `from_markdown(text) -> dict` (round-trips `to_markdown`; tolerant of pasted plain lists: `1. question?` lines, `- option` lines, `(select one)` hints → type inference with `inferred: true`)
- `to_csv(survey) -> str` (`ref,type,label,required,options|,rows|,columns|,shown_when,jumps`), `to_text(survey) -> str` (numbered plain text for BlockSurvey AI Import)
- CLI: `python survey_export.py survey.json --format md|csv|txt|json` and `python survey_export.py survey.md --format json`.

- [ ] **Step 1: Tests**: round trip every type; `from_markdown` on a plain numbered list infers `single_choice` for `(select one)`, `multi_choice` for `(select all that apply)`, `nps` for "0–10 … recommend", `long_text` for a question with no options ending in "why?"; null safety.
- [ ] **Step 2–4:** FAIL → implement → PASS. Wire `survey_common.load_survey` to call `from_markdown` for non-JSON input. Commit `feat(scripts): survey export/import (markdown, csv, text)`.

---

### Task 6: Build, validate, CI

**Files:**
- Create: `scripts/build.py`, `scripts/validate_skills.py`, `tests/test_skills.py`, `.github/workflows/ci.yml`, `skills/.gitkeep`

**Interfaces:**
- `build.py`: for each `skills/*/skill.manifest.json` (`{"references": ["rubric.md", …], "scripts": ["survey_lint.py", …]}`) copy from `shared/` into `references/` and `scripts/`; `--check` exits 1 if any copy differs.
- `validate_skills.py`: frontmatter rules from Global Constraints; body ≤ 500 lines; every `](relative)` link resolves; prints a table; exit 1 on failure.
- `tests/test_skills.py` imports both and asserts they pass on the repo.

- [ ] **Step 1:** write `test_skills.py` (parametrised over `skills/*`), `test_build_check_passes`.
- [ ] **Step 2:** implement; CI runs `pip install -r requirements-dev.txt && pytest -q && python scripts/validate_skills.py && python scripts/build.py --check`.
- [ ] **Step 3:** Commit `chore: skill build/validate scripts and CI`.

---

### Task 7: `survey-score` and `survey-lint` skills (Opus subagent)

**Files:** `skills/survey-score/{SKILL.md,skill.manifest.json}`, `skills/survey-lint/{SKILL.md,skill.manifest.json}`

**Brief for the subagent:** Read spec §4 rows 2–3, `shared/scoring.md` (judgments contract), `shared/rubric.md`, `shared/static-checks.md`. Write SKILL.md with: trigger description; **Procedure**: (1) obtain survey → if not JSON run `scripts/survey_export.py <file> --format json` or normalise by hand; (2) run `python scripts/survey_lint.py survey.json --json > lint.json`; (3) classify survey kind + audience; (4) judge **all** applicable rubric items in one pass, writing `judgments.json` exactly per contract (levels are integers, p in 0–1, confidence in 0–1, a one-line note with the evidence quote); (5) run `python scripts/survey_score_calc.py survey.json judgments.json --lint --md`; (6) present the report with the **output contract**: headline (score/grade/verdict/summary), category table, funnel table, top 10 findings as `severity · ref · roast → fix`, per-question table, "what to do first" (3 bullets); (7) no-Python fallback: manual tally from `scoring.md`. Include a worked mini example (5-question survey → judgments snippet → report headline). Manifest: references `rubric.md, static-checks.md, scoring.md, survey-format.md`; scripts all four. `survey-lint` is the thin deterministic-only variant (steps 1–2 + output table + CI usage `exit code`).

- [ ] Steps: write both SKILL.md + manifests → `python scripts/build.py` → `python scripts/validate_skills.py` → `pytest -q` → commit `feat(skills): survey-score and survey-lint`.

---

### Task 8: `survey-create` and `survey-templates` skills (Opus subagent)

**Files:** `skills/survey-create/{SKILL.md,skill.manifest.json,references/examples.md}`, `skills/survey-templates/{SKILL.md,skill.manifest.json}`, `templates/*.json` (≥ 10: nps, csat, ces, product_market_fit, churn_exit, onboarding_feedback, employee_engagement, event_feedback, pricing_van_westendorp, customer_discovery, academic_consent_study, lead_qualification)

**Brief:** Read spec §4 rows 1 and 7, `shared/playbook.md`, `shared/question-types.md`, `shared/survey-format.md`, `shared/scoring.md`. `survey-create` procedure: (1) read the brief; ask at most 3 clarifying questions **only** if audience, decision, or channel is unknowable, else state assumptions; (2) write the one-sentence decision the survey informs + 3–5 shareables; (3) pick kind, audience, length budget (default ≤ 12 questions, ≤ 5 min; hard cap 20 unless asked); (4) draft title/welcome/thank-you per playbook §1; (5) draft questions per playbook, assign types from `question-types.md`, intent per question, screener + exit logic, demographics last; (6) **self-check** against the playbook checklist (list of rubric ids) and run `scripts/survey_lint.py`; (7) if `survey-score` skill is available, score and revise until ≥ 85 or 2 passes; (8) output: survey JSON (schema) + markdown (`survey_export.py --format md`) + a 5-line "why this will convert" note citing rules. Templates: each JSON validated by lint with zero high findings; `survey-templates` SKILL lists them in a table (kind, questions, minutes, when to use) and instantiates with variables `{company}`, `{product}`, `{event}`.

- [ ] Steps: write → build → validate → `for t in templates/*.json; python shared/scripts/survey_lint.py $t` must show no blocker/high → commit `feat(skills): survey-create and survey-templates`.

---

### Task 9: `survey-fix`, `survey-pretest`, `survey-logic` skills (Opus subagent)

**Files:** `skills/survey-fix/{SKILL.md,manifest,references/fix-patterns.md}`, `skills/survey-pretest/{SKILL.md,manifest,references/personas.md}`, `skills/survey-logic/{SKILL.md,manifest,references/logic-patterns.md}`

**Brief:** Read spec §4 rows 4–6, `shared/rubric.md`, `shared/playbook.md`, `shared/static-checks.md`, `shared/survey-format.md`. `fix-patterns.md`: one pattern per rubric/static id family (split double-barreled, de-presume + gate, neutralise leading, exhaust options, balance scale, add recall window, add units, move demographics, add screener+exit, shorten welcome, fix range gaps) each with before → after example. `survey-fix` procedure: take report (or finding ids) → apply patterns in severity order → output patched JSON + unified "changed questions" table + re-run lint. `survey-pretest`: build 5–8 personas from `audience` (vary expertise, motivation, device, time-pressure, edge case "does not apply"); each walks every question thinking aloud (one line), logs `confused | annoyed | would_quit | satisficed | fine`, estimated seconds; aggregate → drop-off curve table, top confusion points, time per persona, prioritised fixes mapped to rubric ids. `survey-logic`: patterns (screener → exit, branch by segment, skip N/A, loop groups, quota, piping) in the `shown_when`/`jumps` plain-text grammar; output the logic table + run lint for S22/S28/S41.

- [ ] Steps: write → build → validate → pytest → commit `feat(skills): survey-fix, survey-pretest, survey-logic`.

---

### Task 10: `survey-copy` and `survey-export` skills (Opus subagent)

**Files:** `skills/survey-copy/{SKILL.md,manifest,references/copy-patterns.md}`, `skills/survey-export/{SKILL.md,manifest,references/formats.md}`

**Brief:** Read spec §4 rows 8–9, `shared/playbook.md` §1, `shared/survey-format.md`. `survey-copy`: welcome (≤ 80 words: who is asking, why, WIIFM, time, privacy, consent line if research), thank-you (what happens next, incentive delivery, contact), invitation email + 2 reminders (subject lines ×3 each, ≤ 120 words), SMS variant; rules cite A3/A5/A6/A8/A9/E3/E4/E7/F2/F3/F5. `survey-export`: run `scripts/survey_export.py` for md/csv/txt; `formats.md` documents each target including the BlockSurvey path: blocksurvey.io → New survey → **AI import** → paste the `txt`/`md` output; Typeform/Google Forms manual steps; note on logic portability.

- [ ] Steps: write → build → validate → pytest → commit `feat(skills): survey-copy and survey-export`.

---

### Task 11: Golden examples

**Files:** `examples/saas-churn/{brief.md,survey.json,judgments.json,report.md}`, `examples/event-feedback/…`, `examples/employee-engagement/…`

- [ ] Produce each by following `survey-create` then `survey-score` literally (the lead or an Opus subagent); the committed `report.md` must be generated by `survey_score_calc.py` from the committed `judgments.json`; add `tests/test_examples.py` that re-runs calc and asserts the committed score matches. Commit `docs: golden examples`.

---

### Task 12: README, catalog, prompt pack, contributing

**Files:** `README.md`, `README.zh-CN.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `scripts/build_catalog.py`, `prompts/*.md`, `.github/ISSUE_TEMPLATE/{bug.md,skill-request.md}`

- [ ] `build_catalog.py` renders the skills tables from frontmatter between `<!-- catalog:start -->` / `<!-- catalog:end -->`; `--check` for CI.
- [ ] README sections (spec §8): hero + badges; "30-second install" (`npx skills add blocksurvey/blocksurvey-skills`, Claude Code manual `~/.claude/skills/`, Codex `~/.codex/skills/`, Cursor `.cursor/skills/`, ChatGPT: upload `prompts/<skill>.md` to a Project); "Try it" prompts; catalog tables by category (Create / Validate / Improve / Ship) with GIF placeholders `assets/previews/<skill>.gif`; "Before / after" score example from `examples/`; "How the score works" (perspectives table + funnel); FAQ (cost = none; works offline; which models); Contributing; Star history image; footer "Built by BlockSurvey · Built with Claude Opus".
- [ ] `prompts/<skill>.md` = SKILL.md body + inlined essential references (rubric table for score, playbook for create) for file-system-less chat use; generated by `scripts/build_prompts.py` (add to build).
- [ ] README also documents the OPTIONAL `.env.example` keys (TypeSafe Jev, OpenAI, Anthropic) and `survey_judge.py` (Task 14): every skill works with no key; keys only enable automated/CI scoring.
- [ ] Generic-first rule (owner, 2026-10-09): README and every skill are tool-agnostic (Google Forms, Typeform, SurveyMonkey, Qualtrics, BlockSurvey…); BlockSurvey appears only as an export target and in the footer/CTA.
- [ ] Commit `docs: README, catalog, prompt pack`. Tag `v1.0.0` in CHANGELOG (no git tag until owner pushes).

---

### Task 14: Optional API judge (`survey_judge.py`) + `.env.example`

Added by controller ruling after the owner asked mid-run for "a placeholder in the environment file so users can fill their Jev and OpenAI API keys and use the skills further".

**Files:**
- Create: `.env.example`, `shared/scripts/survey_judge.py`, `tests/test_judge.py`, `shared/judge.md` (how to use; referenced by survey-score SKILL.md as an optional path)
- Modify: `skills/survey-score/skill.manifest.json` (add `survey_judge.py` to scripts and `judge.md` to references), then `python scripts/build.py`

**Interfaces:**
- Consumes: `shared/rubric.md` items (parsed at runtime by `survey_score_calc.ITEMS` — import and reuse that table; do not duplicate it), `survey_common.normalise(survey)`, the Judgments JSON contract in `shared/scoring.md`.
- Produces: `judge(survey: dict, provider: str, model: str | None, api_key: str) -> dict` returning a judgments JSON exactly per contract; CLI `python survey_judge.py survey.json --provider jev|openai|anthropic [--model …] [--out judgments.json] [--dry-run]`. `--dry-run` prints the request(s) that would be sent and the estimated input tokens and cost, and exits 0 without network (this is the cost-estimate step required before any paid call).

**Global constraints:** stdlib only (`urllib.request`, `json`, `os`). Keys read from env or `.env` in CWD (simple `KEY=value` parser; never print key values). No call is made unless `--provider` is given explicitly. Default models: jev `jev-latest`, openai `gpt-4o-mini`, anthropic `claude-haiku-5-5`. One request for all survey-level items; per-question items batched 6 questions per request (jev) or all questions in one request (openai/anthropic, since chat models handle it). Retry 429/529/503 with exponential backoff, 3 attempts. On any failure, return partial judgments and set `meta.partial`.

**Provider contracts:**
- **jev**: `POST {TYPESAFE_BASE_URL|https://api.typesafe.ai}/v1/systemone`, `Authorization: Bearer <TYPESAFE_API_KEY>`, body `{state, model, questions:{id:{type:"noul"|"score"|"choice", instructions, criteria}}}`; answers `{id:{type, noul|score|choice, probabilities, confidence}}`. Map: noul → `p`; score → `level = round(score)`, `confidence`; choice → `choice`, `confidence`. Per-question batching: `state = {survey:{title,purpose,kind,audience}, questions:[…6 with previous/next/parent context…]}`, rewrite `` `question. `` → `` `questions[i]. `` in instructions, key `<item>__<ref>`. See workspace `source/jev-http-api.md`.
- **openai**: `POST https://api.openai.com/v1/chat/completions`, `Authorization: Bearer <OPENAI_API_KEY>`, `response_format: {"type":"json_object"}`, temperature 0. System prompt = judging instructions; user = the normalised survey JSON + the item list (id, primitive, instructions, criteria) + the exact output contract. Parse JSON; clamp values.
- **anthropic**: `POST https://api.anthropic.com/v1/messages`, headers `x-api-key: <ANTHROPIC_API_KEY>`, `anthropic-version: 2023-06-01`, `content-type: application/json`; body `{model, max_tokens: 16000, system: <judging instructions>, messages: [{role:'user', content: <survey + items + contract>}]}`; do NOT send `thinking`, `temperature` or `tool_choice` (current models reject or ignore them); response `content` is a list of blocks — concatenate `text` blocks, check `stop_reason` (`max_tokens` → partial; `refusal` → partial with note), then extract the JSON object (first `{` … last `}`). Default model `claude-haiku-5-5` (cheapest judge tier); document `--model claude-opus-5-5` for highest accuracy. Stdlib `urllib` is a deliberate zero-dependency choice for this public repo; say so in a comment.

**Cost estimate rule (CLAUDE.md):** `--dry-run` must print `~N input tokens × $price = $X` using a 4-chars-per-token estimate and a small price table (jev $0.042/M in; gpt-4o-mini $0.15/M in, $0.60/M out; claude-haiku-5-5 $0.10/M in, $0.50/M out (≤100k-token prompts); claude-sonnet-5-5 $2/$10; claude-opus-5-5 $4/$20 — table verified 2026-10-09, label "verify current pricing" in output). Refuse to run (exit 2) without `--yes` if the estimate exceeds $1.

**`.env.example`:**
```
# Optional. Every skill works without any key: your chat LLM is the judge.
# Fill these only if you want scripts/survey_judge.py to score surveys automatically (CI, batch runs).
TYPESAFE_API_KEY=
TYPESAFE_MODEL=jev-latest
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-haiku-5-5
```
Add `.env` to `.gitignore` (keep `.env.example` tracked).

**Tests (`tests/test_judge.py`, no network):** monkeypatch `urllib.request.urlopen` with a fake returning canned bodies for each provider → assert the returned judgments match the contract (ids, `level` int, `p` in [0,1], `choice` str), `--dry-run` prints tokens/cost and makes no call, missing key → exit 2 with a clear message, 429 then 200 → one retry then success, malformed JSON from chat model → `meta.partial` true.

- [ ] Steps: tests → FAIL → implement → PASS → `python scripts/build.py` → `pytest -q` → commit `feat(scripts): optional API judge (Jev/OpenAI/Anthropic) and .env.example`.

---

### Task 13: Final review and acceptance

- [ ] `pytest -q`, `python scripts/validate_skills.py`, `python scripts/build.py --check`, `python scripts/build_catalog.py --check` all green.
- [ ] Dispatch a reviewer (code-review on `shared/scripts/`, silent-failure hunt).
- [ ] Smoke: install locally with `npx skills add ./ -a claude-code --copy` (or manual copy) and run `survey-score` on `examples/saas-churn/survey.json`.
- [ ] Report to owner with: repo tree, how to publish (GitHub org, topics list), Phase 2 list.
