# Static checks (`bs-skills-1.0`)

Deterministic checks that need no LLM: counts, thresholds and structure. `scripts/survey_lint.py` runs them in about a millisecond. They are the only source of **blockers**. This file is the single source of truth for the lint catalog.

**Counts:** 27 shipped (`S01`, `S02`, `S03`–`S06` re-introduced, `S07`–`S19`, `S21`, `S24`, `S27`, `S28` = 23 static, + 4 hybrids `S22`, `S23`, `S25`, `S26`) + 21 from v2 (`S30`–`S48` = 19, + `S50`, `S51`) = **48 checks**.

Ported from BlockSurvey's `static_checks.py` (rubric 1.2), the v1 design spec §5.2 and the v2 proposal §6. Roast and fix text is verbatim from the source where the source has it. Where it is not, the text is marked *(authored)*. *(adapted)* marks a shipped text re-worded because it named a BlockSurvey setting the portable survey does not have.

**Id renumbering.** The shipped ids `S27_monotony_run` and `S28_unreachable_question` keep their numbers. The v2 proposal reused S27 and S28 for two new checks; here they are `S50_welcome_too_long` (v2 "S27") and `S51_early_friction` (v2 "S28").

## Definitions

Every check reads the [portable survey JSON](survey-format.md). Missing fields take the schema defaults; wrong types count as missing and never crash a check.

| Term | Meaning |
| --- | --- |
| answerable | A question whose `type` is not `statement` or `group`. |
| `n` | Number of answerable questions (`stats.answerable_questions`). |
| required | `required` is `true` (anything else counts as optional). |
| open-ended | `type` is `short_text` or `long_text`. |
| choice question | `type` is `single_choice`, `multi_choice`, `dropdown` or `ranking`. |
| matrix | `type` is `matrix`, or `likert` with a non-empty `rows` list. Rows = `rows`, columns = `columns` (or the scale points for a `likert`). |
| collects PII | `collects_pii` is `true`, or `type` is `email` or `phone`. |
| has logic | The survey has at least one question with a non-empty `shown_when` or a non-empty `jumps` list. |
| group children | Questions whose `group` equals the group question's `ref` (or, failing that, its `label`). |
| outcome question | A question with `intent: "outcome"`, or (when judgments are given) `Q24_intent` = `outcome` with confidence ≥ 0.6. |
| screener | A question with `intent: "screener"`, or `Q24_intent` = `screener` with confidence ≥ 0.6. |
| words | Whitespace-separated tokens after trimming. |
| label text | `label` trimmed, inner whitespace collapsed, compared case-insensitively where a check says "same". |

Placeholders in roast/fix: `{ref}` question ref; `{refs}` comma-separated refs; `{label}` label (first 80 characters); `{n}` answerable count; others are named in the condition.

### Finding shape

Each check yields one finding (the same shape `survey_score_calc.py` consumes):

```jsonc
{ "id": "S12_numeric_range_gap", "severity": "medium", "category": "questions", "scope": "question",
  "roast": "Q1: 'Under 25' then '26-35' — where does 25 go?", "fix": "Rewrite Q1's ranges so …",
  "question_ref": "Q1", "question_refs": ["Q1"], "funnel": "answer_quality",
  "evidence": { "kind": "static", "issues": ["…"] } }
```

`scope` is `question` when the check names a question, else `survey`. `evidence.kind` is `static` (or `hybrid` for the hybrid checks).

## Shipped checks (rubric 1.2)

| id | severity | category | condition (exact numbers) | roast | fix | funnel | source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `S01_no_title` | blocker | purpose | `title` empty after trimming. | The survey has no title, so respondents can't tell what it is. | Give the survey a title. | start | shipped-1.2 (severity: the shipped static check is `high`, but its structural-audit twin `TITLE_EMPTY` is a blocker and replaces it in the product; the spec lists "no title" as a blocker) |
| `S02_no_questions` | blocker / medium | coverage | `questions` empty → **blocker** (first roast/fix). Questions exist but `n == 0` (statements only) and the survey `kind` is not `information` → **blocker** (second roast, third fix): it collects nothing, so it must not publish as a survey. `n == 0` and `kind` is `information` → **medium** (second roast/fix): an explicit information page is legitimate. | blocker: There is nothing in this survey yet.<br>statements only: Nothing here asks for an answer, so no responses will be collected. | blocker: Add at least one question.<br>information page (medium): Add a question if you want responses; otherwise this is fine as an information page.<br>statements only, not `information` (blocker): Add at least one question, or set `kind: "information"` if this is an information page. *(authored)* | start | shipped-1.2 (statements-only severity: controller ruling, blocker unless `kind: information`) |
| `S03_label_empty` | blocker | questions | An answerable question whose `label` is empty after trimming. | {ref} has no question text. Respondents get an empty box and a shrug. *(authored)* | Write the question for {ref}, or delete it. *(authored)* | answer_quality | shipped-1.2 (audit `LABEL_EMPTY`, re-introduced) |
| `S04_options_too_few` | blocker | questions | A choice question with fewer than 2 non-empty `options` (counting `has_other` / `has_none` / `has_prefer_not_to_answer` as one option each). Also fires when a **required** `multi_choice` has `selection.min` greater than its option count (the impossible selection limit, audit `SELECTION_MIN_IMPOSSIBLE`). | {ref} gives respondents {k} option(s) to choose from. That's not a choice. *(authored)*<br>limit: {ref} requires at least {min} picks from {k} options. Nobody can submit. *(authored)* | Give {ref} at least two options, or change its type. *(authored)*<br>limit: Lower {ref}'s `selection.min` to at most the number of options. *(authored)* | answer_quality | shipped-1.2 (audit `OPTIONS_TOO_FEW`, re-introduced) |
| `S05_matrix_empty` | blocker | questions | A `matrix` with no non-empty `rows` or no non-empty `columns`. | {ref} is a grid with nothing to rate. *(authored)* | Add the rows (items) and columns (scale points) to {ref}, or delete it. *(authored)* | answer_quality | shipped-1.2 (audit `MATRIX_EMPTY`, re-introduced) |
| `S06_group_empty` | low | structure | A `group` with no children. | Group {ref} ("{label}") has no questions in it. *(authored)* | Move questions into {ref} or remove it. *(authored)* | finish | shipped-1.2 (audit `GROUP_EMPTY`, re-introduced) |
| `S07_no_description` | medium | purpose | `description` empty **and** `welcome.description` empty. | You haven't told people why they're here. No description, no welcome text. | Add a welcome screen that explains the purpose in two sentences. | start | shipped-1.2 |
| `S08_no_welcome` | low | purpose | `welcome` missing, or both `welcome.title` and `welcome.description` empty. | No welcome screen, so respondents start cold and aren't shown how long the survey takes. | Add a welcome screen; it shows the purpose and the time to complete. | start | shipped-1.2 |
| `S09_no_thank_you` | low | experience | `thank_you` missing, or both `thank_you.title` and `thank_you.description` empty. | No thank-you screen of your own, so respondents aren't told what happens next. | Add a thank-you screen that says what happens next. | finish | shipped-1.2 |
| `S10_duplicate_labels` | medium | structure | Two or more answerable questions with the same label text **and** the same `group`, where none of them has `shown_when` and none is a `jumps` target. One finding per duplicated label, `{refs}` = all of them. (Same text in different groups, or on conditional follow-ups like "Why?", asks different things.) | {refs} have identical question text ("{label}"). | Merge them, or reword each so they clearly ask different things. | finish | shipped-1.2 |
| `S11_duplicate_options` | medium | questions | The same option text (case-insensitive) appears twice in one question's `options`. `{duplicates}` = the repeated texts. | {ref} lists the same option twice ({duplicates}). | Remove the duplicate option(s) in {ref}. | answer_quality | shipped-1.2 |
| `S12_numeric_range_gap` | medium | questions | `options` look like numeric ranges and there is a gap or overlap between consecutive buckets. Exact algorithm: [Numeric ranges](#numeric-ranges-s12). `{issues}` = the issue strings joined with "; ". | {ref}: {issues} | Rewrite {ref}'s ranges so every value lands in exactly one bucket (no gaps, no shared boundaries). | answer_quality | shipped-1.2 |
| `S13_selection_hint_type_mismatch` | high | questions | The label (case-insensitive) contains a multi-select hint (`select all`, `select multiple`, `check all`, `tick all`, `choose all`, `all that apply`, `select up to`, `choose up to`, `select N` / `choose N` / `pick N` with N ≥ 2, or the number word two–ten) on a `single_choice`, `dropdown` or `yes_no`; **or** a single-select hint (`select one`, `choose one`, `pick one`, `only one`) on a `multi_choice`. English only: the judged `Q9_type_fit` / `Q25_best_type` cover other languages. | {ref} says "{hint}" but the question type lets respondents pick {one\|several}. They'll fight the form. *(authored)* | Change {ref}'s type (single_choice ↔ multi_choice) or reword the instruction to match. *(authored)* | answer_quality | v1 §5.2 (dropped from the shipped code for being English-only; restored here as a cheap pre-check) |
| `S14_selection_count_unenforced` | low | questions | A `multi_choice` whose label says `select N`, `choose N`, `pick N`, `up to N` or `at least N` (N a digit or number word), and `selection.min` and `selection.max` are both null/absent. | {ref} says to pick {N} but nothing stops anyone picking more or fewer. *(authored)* | Set `selection.min` / `selection.max` on {ref} to match the instruction. *(authored)* | answer_quality | v1 §5.2 |
| `S15_no_time_expectation` | low | purpose | A welcome screen exists (else `S08` covers it), `settings.stated_minutes` is absent/null, and neither `welcome.description` nor `description` mentions a duration (regex `\b\d+\s*(?:-\|–\|to)?\s*\d*\s*(?:min\|mins\|minute\|minutes)\b`, case-insensitive). | Respondents aren't told how long this takes. *(adapted from "'Time to complete' is switched off, so respondents aren't told how long this takes.")* | Set `settings.stated_minutes` and say the time on the welcome screen ("Takes about 4 minutes"). *(adapted)* | start | shipped-1.2 |
| `S16_time_mismatch` | medium | experience | `settings.stated_minutes` is set and either `stated > 2 × estimated + 3` or `estimated > 2 × stated + 3` (minutes; the +3 absorbs fixed overhead on short surveys). `estimated` per [Time estimate](#time-estimate-s16). | You promise ~{stated} minutes; by a rough estimate this is a ~{estimated}-minute survey. | Update `settings.stated_minutes` to the estimate, or cut questions until the promise is true. *(authored)* | start | v1 §5.2 |
| `S17_length_fatigue` | high / medium | experience | `n > 50` → **high** (but **medium** when the survey has logic, since no one path sees every question). `30 < n ≤ 50` → **medium**. | n > 50, no logic: {n} questions. That's not a survey, that's a shift.<br>n > 50, with logic: Up to {n} questions, depending on the path. Long paths lose people.<br>30 < n ≤ 50: {n} questions is long. Expect drop-off after the 20th. | n > 50: Cut to the questions that map to a decision; split the rest into a follow-up survey.<br>30 < n ≤ 50: Trim non-essential questions; consider a progress bar and section breaks. | finish | shipped-1.2 |
| `S18_all_required_long` | low | experience | (`n > 20` and required answerable ≥ 95 % of `n`) **or** (v2 tier: `n > 15` and required ≥ 80 % of `n`). One finding. `{required}` = required answerable count. | {required} of {n} questions are required. Every mandatory question is a place to quit instead of skip. | Make non-critical questions optional. | finish | shipped-1.2 + v2 §6 tier |
| `S19_no_open_ended` | low | coverage | `n > 15` and no answerable question is open-ended. **Kinds:** only for `research` and `feedback` (dropped when `K_survey_kind` is another kind with confidence ≥ 0.5). | {n} closed questions and not one place to say 'actually…'. | Add one optional open text question near the end. | actionability | shipped-1.2 |
| `S21_anonymous_but_pii` | high | trust | `settings.anonymous` is `true` and at least one answerable question collects PII. | The survey is marked anonymous but collects personally identifying answers (email, phone, wallet…). That's a promise you can't keep. | Remove the identifying questions or turn off the anonymous setting. | start | shipped-1.2 |
| `S24_no_progress_bar_long` | low | experience | `n > 20` and `settings.progress_bar` is `false` (default `true`). | {n} questions and the progress bar is hidden. Respondents can't see the finish line. | Turn the progress bar on in survey settings. | finish | shipped-1.2 |
| `S27_monotony_run` | low | experience | A run of **8 or more** consecutive answerable questions (`MONOTONY_RUN = 8`) with the same `type` and the same `group`, none of which (after the first) has `shown_when`. A group boundary or a conditional question breaks the run. One finding per run; `{first}`/`{last}` = first and last ref, `{count}` = run length. | {first}–{last}: {count} {type} questions in a row. By the tenth one respondents stop reading. | Break the run with a different format, a short statement, or by trimming it. | finish | shipped-1.2 |
| `S28_unreachable_question` | high | structure | A top-level question no respondent can reach (algorithm: [Reachability](#reachability-s28)). One finding per dead run of consecutive unreachable questions. `{what}` = `{ref} ("{label}")` for one question, or `{first}–{last} ({count} questions, starting "{label}")`; `{why}` = `{before} always jumps past it/them and nothing jumps to it/them`, or `nothing leads there` when the run starts at the top. Skipped when `settings.randomize_questions` is `true`. | {what} can never be shown: {why}. | Point a jump at {first}, or remove the default jump (`when: null`) on {before} (or the question before it). *(adapted from "clear the 'Always jump to' on …")* | finish | shipped-1.2 |

### Numeric ranges (S12)

Port of `static_checks.parse_range` and `numeric_range_issues`, exactly.

**Number token** `NUM = (?:£|\$|€)?\s*(\d+(?:[.,]\d+)?)\s*(k|m)?` — `k` × 1,000, `m` × 1,000,000; commas inside a number are thousands separators and are removed before parsing.

`parse_range(option)` → `(low, high, low_inclusive, high_inclusive)` or none. Trim the option, then try in this order (all case-insensitive):

1. If the text contains a decimal comma (`\d,\d{1,2}(?!\d)`, e.g. `0-0,5`), it is **not** a range → none.
2. **Range** `^\s*NUM\s*(?:-|–|—|to)\s*NUM\s*(?:\w+)?\s*$` → `(lo, hi, True, True)`. If only the second number has a suffix (`£25-40k`), the suffix applies to both.
3. **Under** `^\s*(?:under|below|less than|fewer than|<)\s*NUM` → `(None, n, True, False)`.
4. **Or less / up to** `^\s*NUM\s*(?:\w+\s+)?(?:or less|and under|or fewer|and below)` or `^\s*(?:up to|<=|≤)\s*NUM` → `(None, n, True, True)`.
5. **Over** `^\s*(?:over|above|more than|greater than|>)\s*NUM` → `(n, None, False, True)`.
6. **Plus / or more** `^\s*NUM\s*\+\s*(?:\w+)?\s*$` or `^\s*NUM\s*(?:\w+\s+)?(?:or more|and over|and above|or over)` → `(n, None, True, True)`.

`numeric_range_issues(options)`:

1. Parse every option. Stop (no issues) if fewer than **3** options parse, or fewer than **60 %** of the options parse.
2. Stop if any parsed bound is not a whole number (only integer buckets are safe: ages, years, money in k).
3. Effective low = `low` (inclusive) or `low + 1` (exclusive); effective high = `high` (inclusive) or `high − 1` (exclusive); open ends are none.
4. Sort by effective low (open low first). For each consecutive pair (h1 = effective high of the first, l2 = effective low of the second; skip if either is none):
   - `l2 > h1 + 1` → gap: `'{o1}' then '{o2}' — where does {missing} go?` with `{missing}` = `h1+1` when the gap is one value, else `h1+1–l2−1`.
   - `l2 ≤ h1` → overlap: `'{o1}' and '{o2}' both contain {l2}`.

Examples: `Under 25` / `26-35` → "'Under 25' then '26-35' — where does 25 go?"; `18-25` / `25-35` / `35+` → two overlaps; `Under 18` / `18-24` / `25-34` / `35+` → clean.

### Reachability (S28)

Port of `digest.apply_flow`. Applies to top-level questions (no `group`) in survey order.

1. After question *i*, the first `jumps` entry whose `when` is satisfied wins; else the default jump (`when: null`); else the next question. A jump `to` an unknown ref behaves like `end`. A default jump whose `to` is the very next question is plain fall-through.
2. *i* **exits always** when it has a default jump (`when: null`) to anything other than the next question.
3. Question *i* **falls through** when *i* = 0 or question *i − 1* does not exit always.
4. **Reached from**: every question whose `jumps[].to` is *i*'s ref.
5. Fixed point: start with nothing reachable; repeat until no change: *i* becomes reachable if *i* = 0, or it falls through and *i − 1* is reachable, or any question that jumps to it is reachable, or (for a `group`) any of its children is reachable.
6. Every question still unreachable is dead. Group consecutive dead questions into runs; one finding per run.

Conditions are not evaluated: any conditional jump counts as a possible path.

### Time estimate (S16)

`estimated minutes = round(Σ seconds / 60, 1)` over **every** question (statements and groups included), with the seconds per type from [question-types.md](question-types.md#seconds-per-type): `matrix` = 8 s × number of rows (at least 1); unknown types 12 s.

## v2 checks (proposal §6)

| id | severity | category | condition (exact numbers) | roast | fix | funnel | source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `S30_matrix_too_large` | medium / high | experience | A matrix with more than **5** columns → **medium**; more than **8** rows → **high** (the higher one wins; one finding). | {ref} is a {r}×{c} grid. On a phone that's a scroll-and-guess exercise. | Split {ref} into smaller grids (at most 5 columns and 8 rows) or separate questions. *(authored)* | finish | v2 |
| `S31_consecutive_matrices` | medium | experience | **2 or more** matrix questions adjacent among answerable questions. One finding per run. | {refs} are grids back to back. This is where straight-lining starts. *(authored)* | Put a different question type between them, or merge and trim. *(authored)* | finish | v2 |
| `S32_ranking_too_many` | medium | experience | A `ranking` with more than **7** options. | {ref} asks people to rank {k} items. Past seven, the bottom half is noise. *(authored)* | Ask for the top 3, or cut the list to 7 or fewer. *(authored)* | finish | v2 |
| `S33_long_radio_list` | low | questions | A `single_choice` with more than **10** options. | {ref} lists {k} options as radio buttons. That's a scroll, not a choice. *(authored)* | Use a dropdown. | finish | v2 |
| `S34_open_ended_overload` | medium | experience | Open-ended questions are more than **30 %** of `n`, **or** more than **3** required open-ended questions. | {k} of {n} questions ask people to type. Typing is the most expensive thing you can ask for. *(authored)* | Keep open text to at most 30 % of questions and at most 3 required; turn the rest into choices. *(authored)* | finish | v2 |
| `S35_loaded_words` | low (judge confirms) | questions | The label contains any of (case-insensitive, whole words): `obviously`, `clearly`, `don't you agree`, `wouldn't you`, `everyone knows`, `always`, `never`, `should`, `unfortunately`. Pre-filter: lint emits it at `info`; the calculator raises it to `low` only when `Q3a_leading` p ≥ 0.7 on the same question, and drops it otherwise. | {ref} uses a loaded word ("{word}"). It nudges the answer. *(authored)* | Reword {ref} without "{word}". *(authored)* | answer_quality | v2 |
| `S36_scale_endpoints_only` | low | questions | A `likert`, `rating` or `slider` with **7 or more** points (`scale.max − scale.min + 1`) whose `scale.labels` label only the two endpoints (or fewer). NPS is exempt (`S37`). | Label the middle too; endpoint-only scales drift. | Label every point of {ref}'s scale, or at least the midpoint. *(authored)* | answer_quality | v2 |
| `S37_nps_nonstandard` | medium | questions | A question of type `nps`, or a `rating`/`likert`/`slider`/`single_choice` whose label contains "recommend", where the scale is not 0–10 (`scale.min ≠ 0` or `scale.max ≠ 10`) **or** the label does not contain "likely". | {ref} is a recommend question that isn't standard NPS. Its number won't compare with anyone else's. *(authored)* | Use the standard wording and a 0–10 scale: "How likely are you to recommend … to a friend or colleague?" *(authored)* | answer_quality | v2 |
| `S38_none_not_exclusive` | medium | questions | A `multi_choice` with an option matching `^(none\|none of the above\|n/a\|not applicable)` (case-insensitive; word boundary after the match so 'Nonetheless' does not match) that is not in `exclusive_options`. (`has_none: true` adds an exclusive "None of the above" and is fine.) | '{option}' can be ticked alongside other options. Make it exclusive. *(generalised from "'None of the above' can be ticked alongside 'Option B'. Make it exclusive.")* | Add '{option}' to {ref}'s `exclusive_options`. *(authored)* | answer_quality | v2 |
| `S39_other_without_text` | low | questions | An option matching `^other` (case-insensitive) while `has_other` is `false` (so there is no text box). | {ref} has an 'Other' option with nowhere to say what 'other' is. *(authored)* | Remove the plain 'Other' option and set `has_other: true` on {ref} (it adds a text box). *(authored)* | answer_quality | v2 |
| `S40_long_list_not_randomised` | low | questions | A `single_choice` or `multi_choice` with more than **6** options, `randomize_options` not `true`, and the options are not an ordered scale: fewer than 60 % parse as numeric ranges, and no option contains an ordinal word (`never`, `rarely`, `sometimes`, `often`, `always`, `agree`, `disagree`, `satisfied`, `dissatisfied`, `very`, `extremely`, `not at all`, `somewhat`, `slightly`). English-only heuristic. | Order bias: the first three options get picked more. | Set `randomize_options: true` on {ref} (keep 'Other' and 'None' last). *(authored)* | answer_quality | v2 |
| `S41_screener_without_exit` | high | structure | A screener (see Definitions) with no `jumps` of its own and no later question whose `shown_when` names its ref. Deliberately stricter than v2's `has_logic == false`: only an exit or a gate driven by the screener's own answer actually routes non-qualifiers, whereas `has_logic` is also true when the screener is merely the target of other logic. | {ref} screens people out but nothing happens when they fail it. They keep answering questions that don't apply. *(generalised from "Q1 screens people out…")* | Add a jump on {ref}: non-qualifying answers → `end` (or to a short exit statement). *(authored)* | actionability | v2 |
| `S42_shouting_or_noise` | low | questions | The label is all upper-case and has more than **3** words; or contains **2 or more** `?`; or **3 or more** `!`; or the question has an option made only of emoji/symbols (no letters or digits). | {ref} is shouting (capitals, '??', '!!!' or emoji-only options). It reads as spam. *(authored)* | Use sentence case, one question mark, and words in the options. *(authored)* | answer_quality | v2 |
| `S43_label_too_long` | medium | questions | The label has more than **35** words. | {ref} is a paragraph, not a question. | Cut {ref} to one sentence under 35 words; move the context into its description. *(authored)* | finish | v2 |
| `S44_group_single_child` | low | structure | A `group` with exactly **1** child. | Group {ref} holds a single question. A section of one is just an extra click. *(authored)* | Remove the group around it, or merge it into a neighbouring section. *(authored)* | finish | v2 |
| `S45_yesno_type_mismatch` | medium | questions | A `yes_no` whose label does not start (case-insensitive) with one of `do`, `does`, `did`, `are`, `is`, `have`, `has`, `can`, `will`, `would`, `could`, `should`. English-only pre-filter for `Q25_best_type`. | {ref} is a yes/no question that doesn't read as one ("{label}"). *(authored)* | Rephrase {ref} as a yes/no question ("Do you…?") or change its type. *(authored)* | answer_quality | v2 |
| `S46_first_question_open_text` | medium | structure | The first answerable question is open-ended. | Opening with an essay question. Start with a click. | Move {ref} later and open with a quick closed question. *(authored)* | continue | v2 |
| `S47_no_logic_long_survey` | low | structure | `n > 30` and the survey has no logic. | Everyone sees all {n} questions. Branching would let most people finish sooner. | Add `shown_when` / `jumps` so respondents skip what doesn't apply to them. *(authored)* | finish | v2 |
| `S48_pii_before_content` | medium | structure | A question that collects PII comes before the first outcome question (see Definitions). Skipped when no outcome question is identified. | You ask for their email before you ask what they think. | Move {ref} after the first outcome question, or to the end. *(authored)* | continue | v2 |
| `S50_welcome_too_long` | medium | purpose | `welcome.description` has more than **120** words. (v2 "S27_welcome_too_long".) | A {k}-word welcome is a wall. Nobody reads walls on a phone. | Cut the welcome to under 120 words: why you're asking, how long it takes, what happens to the answers. *(authored)* | start | v2 |
| `S51_early_friction` | high | structure | Any of the first **3** answerable questions is required **and** is `long_text`, `file`, `email`, `phone`, a matrix, or `ranking`. One finding per question. `{thing}` = "an essay" / "a file" / "an email address" / "a phone number" / "a grid of ratings" / "a ranking". (v2 "S28_early_friction"; v2's `payment` and `signature` have no portable type.) | {ref} asks for {thing} before the respondent has invested anything. Move it later or make it optional. *(generalised from "Q{n} asks for {thing}…")* | Move {ref} after the first few easy questions, or make it optional. | continue | v2 |

## Hybrid checks (judge evidence + code rule)

The judge supplies the evidence (a per-question Noul); code applies the rule. Ported from `static_checks.py::hybrid_checks`. Run by `survey_score_calc.py` when judgments are present (not by lint alone). Only answerable questions with `role` = `question` (or no role) are checked: information and consent steps collect nothing to gate or decline.

| id | severity | category | condition (exact numbers) | roast | fix | funnel | source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `S22_conditional_without_logic` | high | structure | `Q10_depends_on_prior` p ≥ **0.7** (`NOUL_YES`) **and** no logic touches the question: it has no `shown_when`, no question `jumps` to it (`reached_from` has no conditional entry), and the question before it has no conditional jump elsewhere (`follows_unless`). The question's own `jumps` do not count. Logic elsewhere in the survey is no excuse. Whether an option already serves people it doesn't apply to ("Never", "N/A") is part of the Q10 judgment, not matched here. | {ref} ("{label}") only applies after a specific earlier answer, but everyone sees it and none of its options fit the respondents it doesn't apply to. | Add skip logic so {ref} shows only when it applies, or add an option for those it doesn't apply to. | answer_quality | shipped-1.2 |
| `S23_sensitive_without_optout` | low | trust | `Q12_sensitive` p ≥ **0.8** (`SENSITIVE_YES`; 0.7 flagged employment status and bank choice) **and** `required` is `true` **and** `has_prefer_not_to_answer` is not `true` **and** the question has an `options` list. | {ref} asks something personal, is required, and offers no way to decline. | Turn on 'Prefer not to answer' for {ref} or make it optional. | continue | shipped-1.2 |
| `S25_visual_not_described` | low | experience | `Q11_requires_visual` p ≥ **0.7** **and** `has_image` is `true` (or `has_video`, if present). | {ref} depends on its image. Fine on screen — invisible in exports, on screen readers, and to this reviewer. | Add a one-line description of the visual to {ref}. | answer_quality | shipped-1.2 |
| `S26_visual_missing` | medium | questions | `Q11_requires_visual` p ≥ **0.7** **and** `has_image` is not `true` (and no `has_video`). | {ref} asks about a screen or image that isn't there. | Attach the image to {ref} or rewrite it to stand on its own. | answer_quality | shipped-1.2 (the v1 table said high; the shipped code uses medium) |

**Confidence band.** As for rubric Nouls: when the evidence `p` is below **0.85** (`NOUL_STRONG`), the hybrid finding is reported **one severity lower** (high → medium → low; low stays low) and flagged uncertain, with "(Probably — the judge leans this way but isn't certain.)" appended to the roast.

**Judgment-assisted v2 checks.** Three v2 checks also read judgments when they exist, but run without them: `S35_loaded_words` (confirmed by `Q3a_leading`), `S41_screener_without_exit` and `S48_pii_before_content` (use `questions[].intent` from the survey, else `Q24_intent` with confidence ≥ 0.6).

## Deductions

Every check above deducts from its `category` score (and `S30`–`S34`, `S46`–`S48`, `S50`, `S51` also from G. Conversion): high −0.12, medium −0.06, low −0.02, blocker and info 0 (a blocker caps the score instead). Repeats of the same id add 25 % each, up to 2×; at most 0.35 per category. See [scoring.md](scoring.md#static-deductions).

## Not ported

| Source id | Why |
| --- | --- |
| S20 image without text | Removed from the shipped code; `Q11_requires_visual` with `S25`/`S26` replaced it. |
| S29 gating vs audience (v2) | Needs `X2_audience_kind` plus sign-in settings; deferred. `settings.sign_in_required` is in the schema so it can be added later. |
| S_&lt;CODE&gt; structural audit findings | BlockSurvey-internal (logic rows, stale keys, payment configs). Out of scope; the four portable ones are `S03`–`S06` above. |
