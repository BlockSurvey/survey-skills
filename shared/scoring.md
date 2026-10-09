# Scoring (`bs-skills-1.0`)

How a judged survey becomes a 0–100 score, a grade, a verdict, a funnel view and a ranked list of findings. Ported from BlockSurvey's `scoring.py` (rubric 1.2) and the v2 proposal §7. Every number here is policy, not inference: change a weight and the report changes without re-judging.

**The LLM never does the arithmetic.** It fills in a judgments JSON (one pass, all items at once); `scripts/survey_score_calc.py` turns that into the report. Without Python, use the [manual tally](#manual-tally-fallback-no-python).

## Pipeline

```
survey (JSON / markdown / pasted text)
  → normalise to the portable JSON            (survey-format.md)
  → survey_lint.py                             static findings, stats          (static-checks.md)
  → LLM judges every applicable rubric item    judgments.json, ONE pass         (rubric.md)
  → survey_score_calc.py survey.json judgments.json --lint
  → report: score, grade, verdict, categories, funnel, findings, per-question table
```

Surveys over 150 questions: judge the survey-level items once, and the per-question items in chunks of 50 questions; merge the `questions` objects before running the calculator.

## Constants

| Name | Value | Use |
| --- | --- | --- |
| `NOUL_YES` | 0.7 | Noul `p ≥ 0.7` counts as yes. |
| `NOUL_NO` | 0.3 | Noul `p ≤ 0.3` counts as no. |
| `NOUL_STRONG` | 0.85 | Yes-findings below this are one severity lower and uncertain. |
| `NOUL_WEAK` | 0.15 | No-findings (`good_when_yes`) above this are one severity lower and uncertain. |
| `SENSITIVE_YES` | 0.8 | `Q12_sensitive` threshold for `S23` (stricter: 0.7 flagged employment status and bank choice). |
| `LOW_CONFIDENCE` | 0.35 | A Score answer below this confidence becomes an `info` note. |
| `SCORE_CONFIDENT` | 0.6 | A Score answer between 0.35 and 0.6 confidence is one severity lower and uncertain. Also the bar for Choice findings (`Q19`, `Q25`) and for `Q24_intent` in static checks. |
| `GAP_TOPIC_CONFIDENT` | 0.5 | Confidence needed for `C5_gap_topic` to name a topic, and for `K_survey_kind` / `X2_audience_kind` to gate items and pick a profile. |
| `MIN_CERTAINTY` | 0.1 | Below this an answer is a guess and carries no weight. |
| `DEFAULT_CONFIDENCE` | 0.7 | Used when a judgment omits `confidence`. |
| `LOCATE_YES` | 0.7 | Locator `p` at or above this points a finding at a question. |
| `LOCATE_FALLBACK` | 0.5 | If no locator reaches 0.7, the top 3 at or above 0.5 are offered as "Most likely". |
| `LOCATE_MAX` | 8 | At most 8 located questions per finding. |
| `STATIC_DEDUCTION` | blocker 0, high 0.12, medium 0.06, low 0.02, info 0 | Category deduction per static finding id. |
| `STATIC_REPEAT_FACTOR` | 0.25 | Each repeat of the same static id adds 25 % of its base deduction… |
| `STATIC_REPEAT_CAP` | 2.0 | …up to 2× the base. |
| `STATIC_DEDUCTION_CAP` | 0.35 | No category (or funnel stage) loses more than 0.35 to static findings. |
| `QUESTION_HIGH_PENALTY` | 0.02 | The `questions` category loses 0.02 per high-severity question-scoped finding… |
| `QUESTION_HIGH_PENALTY_CAP` | 0.20 | …capped at 0.20. |
| `NEUTRAL_BASE` | 0.70 | Start value of a category (or funnel stage) with no judged evidence. |
| `BLOCKER_SCORE_CAP` | 49 | Any blocker caps the overall score at 49. |
| `READY_AT` | 75 | Verdict `ready` from 75. |
| `NOT_READY_BELOW` | 50 | Verdict `not_ready` below 50 (or with any blocker). |

`SEVERITY_DOWNGRADE` (one step down): `blocker → blocker`, `high → medium`, `medium → low`, `low → low`, `info → info`.

Severity order for ranking: `blocker`, `high`, `medium`, `low`, `info`.

## Judgments JSON contract

The judging LLM writes exactly this shape (one object per survey):

```jsonc
{
  "rubric_version": "bs-skills-1.0",
  "survey_kind": "research", "audience_kind": "prospects_or_general_public",
  "survey": { "A1_title_specific": {"level": 1, "confidence": 0.8, "note": "…"},
              "A5_privacy_stated": {"p": 0.1, "note": "…"}, "C5_gap_topic": {"choice": "pricing", "confidence": 0.7} },
  "questions": { "Q1": { "Q1_clarity": {"level": 3, "confidence": 0.9}, "Q2_double_barreled": {"p": 0.05}, "Q24_intent": {"choice": "demographic", "confidence": 0.9} } }
}
```

Rules:

- `survey` holds survey-level items (`scope: survey` in rubric.md, companions included); `questions` is keyed by question `ref` and holds per-question items, locators (including `L_duplicate_of_earlier`) and `R_role`.
- **Score** item → integer `level`, `0 ≤ level ≤ levels − 1` (0 = worst, as in the criteria column).
- **Noul** item → `p` in `[0, 1]`: the probability the instruction's statement is **true** (for a "yes = problem" item, high `p` = problem; for `good_when_yes`, low `p` = problem).
- **Choice** item → `choice`, one of the item's keys.
- `confidence` in `[0, 1]`, optional, default **0.7**. `note` optional, at most 200 characters, quoting the evidence (the words in the survey that led to the answer).
- `survey_kind` (one of the `K_survey_kind` keys) and `audience_kind` (one of the `X2_audience_kind` keys) are optional top-level shortcuts; when present they win over the companion items.
- A value of the wrong shape (a `level` out of range or not an integer, a `p` outside `[0, 1]`, an unknown `choice`) is treated as **missing**.
- **Missing items** (applicable but absent or invalid) are treated as absent evidence: they neither help nor hurt; the report sets `meta.partial = true` and lists them in `meta.missing_items`. Unknown item ids and items that do not apply are ignored.
- Judge every applicable item in one pass. Never re-send the survey once per item.

## From answer to value

Every value is in `[0, 1]`, 1 = best.

| Primitive | Value | Certainty (evidence strength) |
| --- | --- | --- |
| Score | `level / (levels − 1)` | `confidence` |
| Noul | `1 − p`, or `p` when `good_when_yes` | `abs(p − 0.5) / 0.5` (a coin-flip `p` is no evidence) |
| Choice `Q19_recall_period` | `missing_but_needed` → 0; `stated`, `not_applicable` → 1 | `confidence` |
| Choice `Q25_best_type` | `current_type_is_best` or the current type → 1; any other type → 0. Only used when `confidence ≥ 0.6`. | `confidence` |
| Other Choice items | no value (informational) | — |

**Evidence weight** = `item weight × certainty`, or **0** when certainty `< MIN_CERTAINTY` (0.1). Uncertainty is not a defect: a judgment the judge cannot make must not pull a category towards "half bad". (The shipped code derives Score certainty from the level probabilities; a chat LLM reports `confidence` instead.)

Items with `informational` or weight 0 never enter a score.

## Applicability

Ported from `rubric.py::item_applies`, applied in this order to each per-question item and question:

1. **Not answerable** (`type` is `statement` or `group`): only `Q1_clarity`, `Q2_double_barreled`, `Q3a_leading`, `Q3b_presuming`, `Q13_grammar`. Findings from these are reported; non-answerable questions get no per-question score.
2. **`role` ≠ `question`** (`information` or `consent`, from `R_role` or `questions[].role`): only the `NON_QUESTION_ITEMS` = `Q1_clarity`, `Q4_jargon`, `Q5_relevance`, `Q13_grammar`, `L_hard_to_read`, `L_pressuring`. For these roles `Q1_clarity` uses its role-specific fix.
3. **`shown_when` set**: skip `Q3b_presuming` (the display rule guarantees the premise). Skip `Q5_relevance` when `shown_when` names an earlier question ref (a gated follow-up inherits its parent's relevance).
4. **`applies`**:
   - `all` → applies.
   - `options`, `with_options_or_columns` → the question has a non-empty `options` or `columns`.
   - `single_choice` → has options **and** `type` ∈ {`single_choice`, `dropdown`, `yes_no`, `consent`} (bType set `multiplechoice`, `dropdown`, `consent`, `customerexperience`).
   - `scale` → `type` ∈ {`rating`, `nps`, `likert`, `slider`, `matrix`} or (`single_choice`/`dropdown` with 3+ options), **and** has options or columns.
   - `text` → `type` ∈ {`short_text`, `long_text`}.
   - `quantity` (v2) → `type` ∈ {`number`, `slider`, `date`}, or `short_text` (the judge decides whether its label asks for an amount; answer `p = 1` when it does not ask for one).
5. **Gates** (v2): `C7_has_attention_check` counts only when answerable questions `> 25`; `Q16_sensitive_reassured` counts only when that question's `Q12_sensitive` `p ≥ 0.7`; `F3b_incentive_delivery_clear` counts only when `F3a_incentive_mentioned` `p ≥ 0.7`; `F3_incentive_clear` is ignored when F3a and F3b are both present.

**Kinds gating.** Items carry a `kinds` list (rubric.md); default is every kind. The survey kind is: top-level `survey_kind` in the judgments, else `K_survey_kind` when its confidence ≥ 0.5, else the survey's `kind` field, else unknown. When the kind is known and not in an item's list, the item is skipped entirely (no finding, no score): a form is not marked down for research coverage it was never meant to have. Unknown kind → nothing is skipped. Kinds-gated items: `A7` (research, feedback), `C2` (research), `C3`, `C4`, `C6` (research, feedback), `C5_obvious_gap` (research, feedback, assessment), `F2` (research). Static `S19_no_open_ended` is gated to research and feedback the same way.

## Findings from judgments

Placeholders are rendered with `{ref}`, `{label}` (first 80 characters), `{title}`, plus `{stated_minutes}`, `{type}`, `{choice}` for the v2 items. A per-question finding gets `target: question`, `question_refs: [ref]` and one checklist line `{ref} "{label, first 60}": {fix}`; a survey-level finding gets the item's `target` and the fix as its checklist line.

**Score.** The level the answer lands on selects the severity and roast; a level with no severity produces nothing.
- `confidence < 0.35` → severity `info`, uncertain, roast + " (The judge wasn't sure about this one.)"
- `0.35 ≤ confidence < 0.6` → one severity lower, uncertain, roast + " (Probably — the judge leans this way but isn't certain.)"
- otherwise → full severity.

**Noul.** Problem when `p ≥ 0.7` (or `p ≤ 0.3` for `good_when_yes`). Full severity when `p ≥ 0.85` (or `p ≤ 0.15`); otherwise one severity lower, uncertain, roast + " (Probably — the judge leans this way but isn't certain.)"

(The shipped wording says "Jev" where this port says "the judge".)

**Choice.** `Q19_recall_period` = `missing_but_needed` with confidence ≥ 0.6 → medium. `Q25_best_type` names a type other than `current_type_is_best` and the current type, with confidence ≥ 0.6 → medium, and on that question Q25's fix replaces `Q9_type_fit`'s fix. Other choices produce no finding.

**Item-specific severity rules.**
- `Q15_abandon_risk` level 0: `high` in the first five answerable questions, `medium` later.
- `A10_deadline_stated`: `info` when the weight profile is `event_feedback` or `employee_engagement`.
- `Q21_social_desirability`: `medium` when the weight profile is `academic_research` or `employee_engagement`.
- Informational items (`F1`, `F3a`, `Q10`, `Q11`, `Q12`, `Q18`, `Q24`, locators, companions) produce no finding of their own. `Q10`/`Q11`/`Q12` feed the hybrid checks in static-checks.md.

**Code rules over informational items (v2).** These emit survey-level findings under the item's id with `evidence.rule` set. They do not change the score (only static ids deduct), they inform the report.
- `Q18_hypothetical`, rule `only_outcome_hypothetical`: at least one outcome question exists and **every** outcome question has `Q18_hypothetical` `p ≥ 0.7` → medium. Roast: "Your only outcome measure is a hypothetical. Stated intent over-predicts real behaviour."
- `Q24_intent`, intent mix (intent from `questions[].intent`, else `Q24_intent` with confidence ≥ 0.6):
  - rule `no_outcome`: no outcome question → medium, unless the kind is `form`, `quiz` or `information`, or `C3_has_outcome_question` already produced a finding. Roast *(authored)*: "Nothing here measures the outcome. You'll have context and no verdict." Fix: "Add one direct outcome question (overall satisfaction, likelihood, intent) tied to the purpose."
  - rule `demographics_heavy`: demographic questions are more than 25 % of answerable questions → low. Roast *(authored)*: "{k} of {n} questions are demographics. That's a census, not a survey." Fix: "Keep only the demographics you will cut the data by."
  - rule `outcome_buried`: the first outcome question sits after 80 % of the answerable questions → low. Roast *(authored)*: "The question that matters most is near the very end, where the tired and the hurried have already left." Fix: "Move the main outcome question into the first half."
  - Screener without logic is the static check `S41_screener_without_exit`.

## Locating survey-level findings

A survey-level item says *that* something is wrong, never *where*. Each is paired with a per-question **locator** Noul (rubric.md §Locators) that turns the finding into a checklist. Locators never change a score.

| Survey item | Locator |
| --- | --- |
| `C4_missing_why` | `L_needs_why` |
| `E2_burden` | `L_hard_to_recall` |
| `B1_logical_order` | `L_topic_jump` |
| `B3_demographics_placement` and `C6_demographics_proportionate` (alias) | `L_is_demographic` |
| `F4_manipulative_framing` | `L_pressuring` |
| `E5_reading_level` | `L_hard_to_read` |
| `F1_sensitive_topics` | `L_sensitive_topic` |
| `B5_redundant_questions` | `L_duplicate_of_earlier` (only questions with `role` = `question`) |

When a located item produces a finding:

1. Collect the locator's `p` for every question; sort high → low.
2. **Hits** = questions with `p ≥ 0.7`, at most 8. Roast + " See: Q3, Q7."
3. No hits → the top 3 with `p ≥ 0.5`, roast + " Most likely: Q3, Q7."
4. Still none, but locator answers exist → the finding is a hunch: one severity lower, uncertain, roast + " (The judge flagged this survey-wide but couldn't point at a specific question — treat it as a hunch.)"
5. `question_refs` = the located refs; one checklist line per ref from the locator's template (its `fix`), and `evidence.located = [{ref, p}]`.

Special cases:
- `B2_opening_question` points at the first answerable question: roast + " See: {ref}.", checklist `{ref} "{label, first 60}": open with an easy, on-topic question instead; move this one later.`
- `C1_objective_coverage` and `C5_obvious_gap` are absence findings, named by `C5_gap_topic`. The topic is **named** when the choice is not `none` or `other_unlisted` and its confidence ≥ 0.5: roast + " Most likely missing: {topic description, lower-case}.", checklist "Add a question about: {topic description, lower-case}." Not named → one severity lower, uncertain, roast + " (The judge couldn't name the missing topic — treat it as a hunch.)" In the category score, `C5_obvious_gap`'s evidence weight is **halved** when no topic is named.

**Follow-ups.** A `Q5_relevance` finding on a question that other questions are gated on (their `shown_when` names its ref) covers those follow-ups too: `question_refs` adds them, roast + " Its follow-ups (Q6, Q7) only show after it and go with it.", and a checklist line per follow-up "{follow-up}: shown only after {ref}; keep or remove them together."

## Category scores

Categories: `purpose` (A), `structure` (B), `coverage` (C), `questions` (D), `experience` (E), `trust` (F), `conversion` (G).

1. **Survey-level categories** (A, B, C, E, F): weighted mean of the applicable, non-informational survey items' values, each weighted by its evidence weight. `None` when no item has evidence.
2. **Per-question score**: for each answerable question, the weighted mean (evidence weights) of its applicable, non-informational items. `None` without evidence.
3. **`questions` (D)** = mean of the per-question scores − `min(0.20, 0.02 × number of high-severity findings with scope question)` (rubric, static and hybrid findings alike, after downgrades), floored at 0.
4. **`conversion` (G)** = weighted mean of `A8_respondent_benefit` (2), `A9_sponsor_named` (2), `E7_welcome_scannable` (1), `E8_straightlining_risk` (2), `B7_end_loading` (1) and the mean of `Q15_abandon_risk` across questions (3), each also scaled by its certainty.
5. A category with no evidence starts from `NEUTRAL_BASE` 0.70.
6. Subtract the category's [static deductions](#static-deductions); clamp to `[0, 1]`.
7. **Evaluated categories**: those with judged evidence. The overall is re-weighted over evaluated categories only (rather than pulled towards a made-up 70). With no judged evidence at all (a lint-only preview), every category uses the neutral base.

### Static deductions

Static and hybrid findings (ids starting with `S`) deduct; rubric findings already shaped the base. For one category:

```
for each distinct static id in the category:
    deduction += STATIC_DEDUCTION[severity] × min(2.0, 1 + 0.25 × (count − 1))
category deduction = min(0.35, Σ deduction)
```

The severity used is the (first) finding's severity. G additionally takes the deductions of `S30`–`S34`, `S46`–`S48`, `S50`, `S51` (they count in their own category too, by design).

## Weight profiles

The category weights depend on the survey kind and audience (v2 §7.1, with G added).

| Profile | A purpose | B structure | C coverage | D questions | E experience | F trust | G conversion | Σ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `default` | .20 | .15 | .20 | .25 | .15 | .05 | .00 | 1.00 |
| `customer_satisfaction` | .15 | .10 | .15 | .20 | .20 | .05 | .15 | 1.00 |
| `market_research` | .15 | .10 | .25 | .25 | .10 | .05 | .10 | 1.00 |
| `employee_engagement` | .10 | .10 | .15 | .20 | .15 | .20 | .10 | 1.00 |
| `academic_research` | .10 | .15 | .20 | .30 | .05 | .20 | .00 | 1.00 |
| `lead_generation` | .15 | .10 | .05 | .15 | .20 | .15 | .20 | 1.00 |
| `registration_or_form` | .10 | .10 | .00 | .30 | .30 | .20 | .00 | 1.00 |
| `event_feedback` | .10 | .10 | .15 | .20 | .30 | .05 | .10 | 1.00 |

**Normalisation:** every row already sums to 1.00 with G included (the v2 `default` row's G "—" is 0), so no renormalisation was needed. If a row is retuned and no longer sums to 1, divide each weight by the row sum.

**Choosing the profile** (the v2 table is keyed by v2's ten-way `X1_survey_kind`; this port keeps the shipped six kinds and uses the audience to pick):

| `K_survey_kind` | `X2_audience_kind` | Profile |
| --- | --- | --- |
| `research` | `employees` | `employee_engagement` |
| `research` | `students` | `academic_research` |
| `research` | any other | `market_research` |
| `feedback` | `employees` | `employee_engagement` |
| `feedback` | `event_attendees` | `event_feedback` |
| `feedback` | any other | `customer_satisfaction` |
| `form` | `prospects_or_general_public` | `lead_generation` |
| `form` | any other | `registration_or_form` |
| `quiz`, `assessment`, `information` | any | `default` |
| unknown (confidence < 0.5, not stated) | any | `default` |

The audience is the top-level `audience_kind`, else `X2_audience_kind` with confidence ≥ 0.5, else `unclear`. The chosen profile is reported in `meta.weight_profile`.

## Overall, grade and verdict

```
overall = round(100 × Σ(w_c × score_c) / Σ w_c)     over evaluated categories, profile weights w_c
if any blocker: overall = min(overall, 49)
overall = clamp(overall, 0, 100)
```

| Overall | Grade | Verdict |
| --- | --- | --- |
| ≥ 90 | A | `ready` |
| 80–89 | B | `ready` |
| 75–79 | C | `ready` |
| 70–74 | C | `needs_work` |
| 60–69 | D | `needs_work` |
| 50–59 | E | `needs_work` |
| < 50, or any blocker | F | `not_ready` |

Grade floors: A 90, B 80, C 70, D 60, E 50, else F. Verdict: `not_ready` if any blocker or overall < 50; `ready` if overall ≥ 75; else `needs_work`. (A blocker forces the score ≤ 49, so its grade is always F.) `not_ready` means "an expert would tell you not to publish this", which is rarer than "an expert would have a list for you".

## Funnel view

A second view of the same evidence, by where a survey leaks respondents. Every rubric item and static check has a `funnel` column (rubric.md, static-checks.md): `start` (will they click Start?), `continue` (will they survive the first three questions?), `finish` (will they reach Submit?), `answer_quality` (will the answers be usable?), `actionability` (can the owner decide from the data?).

For each stage:

1. **Pairs**: every applicable, non-informational survey-level item of that stage with evidence → `(evidence weight, value)`; every per-question item of that stage → one pair `(item weight × mean certainty, mean value across the questions it was judged on)`.
2. **Base** = weighted mean of the pairs, or `NEUTRAL_BASE` 0.70 when there are none.
3. **Stage score** = base − static deductions of the static/hybrid findings whose check has that stage (same formula and 0.35 cap as categories), clamped, × 100, rounded.
4. **Drivers**: up to 3 ids that cost the stage most — items ranked by `weight × (1 − value)` (a per-question item is named `id:Qn` for its worst question) together with static ids ranked by their deduction.

`predicted_completion_band` from the `finish` score: `low` < 50, `medium` 50–74, `high` ≥ 75.

```jsonc
"funnel": {
  "start":          { "score": 71, "drivers": ["A9_sponsor_named", "A8_respondent_benefit"] },
  "continue":       { "score": 44, "drivers": ["S51_early_friction", "Q15_abandon_risk:Q3"] },
  "finish":         { "score": 38, "drivers": ["S17_length_fatigue", "E8_straightlining_risk"] },
  "answer_quality": { "score": 66, "drivers": ["Q3b_presuming:Q15", "Q8_scale_unbalanced:Q12"] },
  "actionability":  { "score": 58, "drivers": ["Q24_intent", "Q23_actionable:Q9"] },
  "predicted_completion_band": "low"
}
```

## Findings order, grouping and summary

**Order.** Sort by `(severity rank, uncertain, −weight)`: blocker → high → medium → low → info; within a severity, confident findings before hunches, then higher rubric weight first (static checks weight 1). The top finding feeds the summary.

**`findings_by_id`.** One row per distinct id, in the same order: `{id, severity, category, target, count, question_refs, fix, checklist}`, merging refs and checklist lines without duplicates.

**Summary line** (ported from `scoring.py::summary_line`). Let `n` = "{q} question(s)" plus " and {i} information step(s)" when some answerable entries have a non-question role. `top` = the first finding that is not `info` and not uncertain; if none, the first that is not `info`.

| Situation | Summary |
| --- | --- |
| `ready` and no `top` | `{score}/100. Clean, focused, and ready to publish. Nothing worth roasting.` |
| `ready` | `{score}/100. Ready to publish; one thing to polish first: {top.roast}` |
| any blocker | `{score}/100. Not publishable yet — {blockers} blocker(s). Start here: {top.roast}` |
| otherwise, with `top` | `{score}/100. {n}, {high} serious and {medium} moderate issues. Biggest one: {top.roast}` |
| otherwise, no `top` | `{score}/100. {high + medium} issues to fix before publishing.` |

## Report shape

```jsonc
{ "score": 63, "grade": "D", "verdict": "needs_work", "summary": "…",
  "categories": [{"id": "purpose", "label": "Purpose & framing", "weight": 0.2, "score": 58, "findings": 3}, …],
  "funnel": { "start": {"score": 71, "drivers": […]}, …, "predicted_completion_band": "low" },
  "findings": [ { "id", "severity", "category", "scope", "roast", "fix", "question_ref", "question_label",
                  "evidence", "uncertain", "target", "question_refs", "checklist", "funnel" }, … ],
  "findings_by_id": [ { "id", "severity", "category", "target", "count", "question_refs", "fix", "checklist" }, … ],
  "questions": [ { "ref", "type", "role", "label", "required", "score", "finding_ids" }, … ],
  "stats": { "answerable_questions", "required_answerable", "open_ended_questions", "pii_questions",
             "questions_with_logic", "estimated_minutes", "stated_minutes", … },
  "meta": { "rubric_version": "bs-skills-1.0", "survey_kind": "research", "audience_kind": "…",
            "weight_profile": "market_research", "partial": false, "missing_items": [ … ] } }
```

`categories[].findings` counts non-`info` findings. Category labels: Purpose & framing, Structure & flow, Coverage & gaps, Question quality, Respondent experience, Trust & ethics, Conversion. `questions` lists answerable questions only. `--polite` output keeps every fix and replaces each roast with a neutral one-line description of the problem.

## Manual tally fallback (no Python)

When the calculator cannot run (plain ChatGPT, no code tool), estimate the grade band by hand. **Approximate**: it lands in the same band as the calculator for most surveys, typically within ±8 points; say so in the report.

1. Run the static checks by hand (static-checks.md) and judge the rubric items. Write down every finding with its severity, after the confidence downgrades above. Ignore `info` findings and count each static id once however many questions it hits (plus one extra if it hits 4 or more).
2. Count: **B** blockers, **H** high, **M** medium, **L** low.
3. Points = `100 − 6·H − 3·M − 1·L`, floored at 0.
4. Apply the caps, first that matches:

| Condition | Result |
| --- | --- |
| B ≥ 1 | min(points, 49) → **F**, `not_ready` |
| H ≥ 6 | min(points, 59) → at best **E** |
| H ≥ 4 | min(points, 69) → at best **D** |
| H ≥ 2 | min(points, 79) → at best **C** (`ready` only from 75) |
| H = 0 and M ≤ 2 | max(points, 80) → at least **B** |

5. Grade and verdict from the table in [Overall, grade and verdict](#overall-grade-and-verdict).

Why these numbers: a high finding usually means a level-0 answer on a weight-2 to weight-4 item (pulling its category 25–50 % down) or a 0.12 static deduction, worth about 4–8 overall points once category weights (0.15–0.25) apply; a medium is about half that; a low barely moves the score. The caps mirror the calculator: a blocker caps at 49, and several high findings across categories rarely leave a survey above the next band down.

Report it as: `~{points}/100 (manual tally, approximate) · grade {g} · {verdict}`.
