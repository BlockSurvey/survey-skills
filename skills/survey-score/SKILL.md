---
name: survey-score
description: Score any survey, questionnaire or form 0-100 against a professional 77-item rubric plus 48 static checks, and get a grade, a publish verdict, a funnel view of where respondents will drop off, and ranked findings with a concrete fix for each. Accepts survey JSON, markdown, a Google Forms / Typeform / SurveyMonkey / Qualtrics export, or plain pasted text. Use when the user asks to score, grade, rate, review, audit, roast, critique, evaluate, test or sanity-check a survey, NPS or CSAT questionnaire, feedback form, registration form or research study, or asks "is this survey any good?", "what's wrong with my survey?" or "will people finish this?".
license: MIT
metadata:
  author: blocksurvey
  version: "1.0.0"
  category: validate
---

# Survey score

Scores a survey the way an experienced survey methodologist would, then hands back a report you can act on: a 0–100 score with grade and verdict, seven category scores, a five-stage funnel (start → continue → finish → answer quality → actionability), the top 10 problems as specific roasts with fixes, a per-question table, and the three things to fix first. The split of work is strict: a script runs the deterministic checks, you (the model) judge the rubric in **one pass** and write a judgments file, and a second script does all the arithmetic. You never compute the score yourself.

## When to use

- The user shares a survey, form or questionnaire in any format and asks to score, review, grade, audit, roast or test it.
- Before publishing a survey, to answer "is this ready?" (verdict `ready` / `needs_work` / `not_ready`).
- After editing a survey, to compare before and after (re-run; the judgments format is stable).
- Another skill (for example survey-create) wants a self-check score.
- For a fast, deterministic check with no judgement (CI, pre-commit), use **survey-lint** instead.

## Inputs

Accept any of these, and ask for nothing else unless the survey itself is missing:

| Input | What to do |
| --- | --- |
| Portable survey JSON (has `title` and `questions` with `ref`, `type`, `label`) | Use as is. Format: [survey-format.md](references/survey-format.md). |
| Markdown, or a pasted question list (`1. Question?` then `- option` lines) | Save it to `survey.md` and normalise with `survey_export.py` (step 1). |
| Google Forms, Typeform, SurveyMonkey, Qualtrics or other tool export, a PDF or a screenshot transcript | Map it by hand to the portable JSON using the field tables in [survey-format.md](references/survey-format.md): portable `type` names only (`single_choice`, `multi_choice`, `rating`, `nps`, `matrix`, `long_text`…), refs `Q1…Qn` in order. |

When pasting text, put each option on its own line (`- option`); options written inline after the question are folded into the label and then trip blocker `S04_options_too_few`.

Useful but optional (ask only if the user offers context; otherwise infer and say so): who the respondents are (`audience`), the decision the survey informs (`purpose`), the promised time (`settings.stated_minutes`). Never invent a welcome screen, privacy line or thank-you that the user did not give you: their absence is a finding.

## Procedure

`<skill-dir>` = the folder containing this SKILL.md (for example `~/.claude/skills/survey-score`). Run every command from the **user's** folder, the one holding their survey, so the working files (`survey.json`, `lint.json`, `judgments.json`, `report.md`, `report.json`) land next to the survey and never inside `<skill-dir>` (it may be read-only). If the user only pasted text, use their current working folder. Scripts need Python 3.9+ and nothing else; use `python3` if `python` is missing.

1. **Normalise → `survey.json`.**
   - JSON already: copy it to `survey.json`.
   - Markdown or pasted text: `python <skill-dir>/scripts/survey_export.py survey.md --format json --out survey.json`.
   - Then open `survey.json` and fix every question marked `"inferred": true` whose guessed type is wrong (an "Email" box guessed as `short_text` → `email`; "Any other comments?" → `long_text`; a 1–5 satisfaction list → `rating`). Fill `required`, `shown_when` and `jumps` only from what the source says.
   - Produce: a valid `survey.json` and a one-line list of what you inferred, for the report's assumptions line.

2. **Lint → `lint.json`.** `python <skill-dir>/scripts/survey_lint.py survey.json --json > lint.json`
   - Exit `0` = no blocker/high; `1` = at least one blocker/high finding (not an error, keep going); `2` = invalid input: fix `survey.json` and rerun.
   - Read the findings so your judgments do not contradict them (lint already counted lengths, ranges, duplicates, missing screens). Note the answerable-question count `n` (questions whose `type` is not `statement` or `group`); you need it for C7 and for chunking.

3. **Classify.** Decide, with a confidence each:
   - Survey kind (`K_survey_kind`): `research`, `feedback`, `form`, `quiz`, `assessment` or `information`. If `survey.json` has a sensible `kind`, use it.
   - Audience (`X2_audience_kind`): `existing_customers`, `prospects_or_general_public`, `employees`, `students`, `experts_or_professionals`, `event_attendees` or `unclear`.
   - Role (`R_role`) of every question: `question`, `information` or `consent`.
   - The kind switches items off (see "How to judge"); the kind + audience pick the weight profile.

4. **Judge every applicable rubric item in ONE pass → `judgments.json`.** Open [references/judging-guide.md](references/judging-guide.md) (one line per item) and walk it in this order: classifiers → survey-level A, B, C, E, F → for each question in order, all per-question items and locators that apply. Open [references/rubric.md](references/rubric.md) only for an item whose line leaves you unsure. Write the file exactly in the contract shape below. Produce: one complete `judgments.json`. Never judge item by item in separate passes, and never re-read the survey once per item.

5. **Calculate.** Run both (deterministic, instant):
   - `python <skill-dir>/scripts/survey_score_calc.py survey.json judgments.json --lint --md > report.md` → the report you present.
   - `python <skill-dir>/scripts/survey_score_calc.py survey.json judgments.json --lint --json > report.json` → the machine report the **survey-fix** skill reads.
   - Exit `0` = clean or minor issues, `1` = `not_ready` or a blocker/high finding (the report still printed; this is a result, not a failure), `2` = invalid input (read the one-line reason, fix the file, rerun).
   - If the footer says `partial: N item(s) not judged`, read `meta.missing_items` in `report.json` (entries look like `Q1:Q17_negative_wording`), add just those judgments to the same file, and rerun step 5. Do not re-judge the rest.
   - Add `--polite` to both commands when the user wants a neutral tone (no roasts; every fix is kept).

6. **Present the report** per the output contract. Copy every number, grade, verdict, roast and fix from the calculator verbatim. Your own words go only in the assumptions line, the one-line reading of the funnel, and in making the three "What to do first" bullets concrete with the survey's own wording.

7. **No Python?** Use the manual tally in the No-Python fallback section below.

### Judgments contract

The shape `survey_score_calc.py` reads (full rules: [scoring.md](references/scoring.md), "Judgments JSON contract"):

```json
{
  "rubric_version": "bs-skills-1.0",
  "survey_kind": "feedback",
  "audience_kind": "existing_customers",
  "survey": {
    "K_survey_kind":    {"choice": "feedback", "confidence": 0.8, "note": "asks about support and usage"},
    "A1_title_specific": {"level": 0, "confidence": 0.9, "note": "'Customer Survey' names no topic"},
    "A5_privacy_stated": {"p": 0.02, "note": "no intro text at all"},
    "C5_gap_topic":     {"choice": "satisfaction", "confidence": 0.6}
  },
  "questions": {
    "Q2": {
      "R_role":            {"choice": "question"},
      "Q1_clarity":        {"level": 2, "confidence": 0.7},
      "Q3a_leading":       {"p": 0.95, "note": "'How much do you love our fast and friendly support?'"},
      "Q24_intent":        {"choice": "attitude", "confidence": 0.9}
    }
  }
}
```

- `survey` holds survey-level items (including `K_survey_kind`, `X2_audience_kind`, `C5_gap_topic`); `questions` is keyed by `ref` and holds per-question items, locators and `R_role`.
- Score item → integer `level` from 0 (worst) to levels − 1. Noul item → `p` in [0, 1]. Choice item → `choice`, one of the item's keys.
- `confidence` in [0, 1], optional, default 0.7. Always give it on Score and Choice items when you are less than fairly sure.
- `note`: at most 200 characters, quoting the survey words that decided the answer. Write one on every survey-level item and on every per-question judgment that flags a problem; clean per-question passes may omit it to keep the file short.
- A wrong shape (level out of range, `p` outside [0, 1], unknown choice) counts as missing. Unknown ids are ignored.
- Skip `F3_incentive_clear`; answer `F3a_incentive_mentioned` and `F3b_incentive_delivery_clear` instead.

### How to judge

- **Score levels are situations, not a sliding scale.** Read the level descriptions and pick the one that matches what is on the page. A title that names the topic but not the purpose is level 1, whatever you feel about it overall.
- **`p` is a calibrated probability that the item's statement is true.** 0.9 = clearly yes, 0.7 = probably, 0.5 = unsure (counts as no evidence), 0.1 = clearly no. Most Noul items are phrased so yes = problem; items marked (yes = good) in the guide are the reverse. Do not shade `p` to be kind or harsh: the calculator already downgrades findings between 0.7 and 0.85 to "uncertain".
- **Confidence is how sure you are of the level**, not how bad the problem is. Below 0.35 a Score answer becomes an info note; 0.35–0.6 is reported one severity lower.
- **Applicability (skip what does not apply):**
  - `statement` / `group` entries: only `R_role`, `Q1_clarity`, `Q2_double_barreled`, `Q3a_leading`, `Q3b_presuming`, `Q13_grammar`.
  - Role `information` or `consent`: only `R_role`, `Q1_clarity`, `Q4_jargon`, `Q5_relevance`, `Q13_grammar`, `L_hard_to_read`, `L_pressuring`.
  - `shown_when` set: no `Q3b_presuming` (the display rule supplies the premise); no `Q5_relevance` when the condition names an earlier ref.
  - Option, scale, text and quantity items only where the question has them (the `applies` column in the guide). A `single_choice` or `dropdown` with 3+ options counts as a scale, so it gets `Q8` and `Q17`.
- **Kinds gate survey items.** Skip `A7`, `C3`, `C4`, `C6` unless the kind is research or feedback; `C2` and `F2` unless research; `C5_obvious_gap` unless research, feedback or assessment. Skipped items are not defects.
- **Locators matter.** Answer the `L_*` items on every question they apply to. Without them a survey-level finding ("demographics come too early") cannot point at a question and is reported as a hunch.
- **Don't count inside a judgment.** Lengths, word counts, ranges and duplicates are lint's job. Judge meaning, wording and fit.
- **Large surveys (more than 150 questions):** judge the survey-level items once, the per-question items in chunks of 50 questions, then merge the `questions` objects into one `judgments.json` before step 5.

## Output contract

Emit exactly these sections, in this order. Section 1–5 content comes from the calculator's `--md` output.

```markdown
# Survey score: {score}/100 · {grade} · {verdict}

{summary line from the calculator}

_Assumptions: kind {kind}, audience {audience}, profile {weight_profile}. {what you inferred in step 1, or "nothing inferred"}._

## Categories
| Category | Weight | Score | Findings |   ← all seven rows, verbatim

## Funnel (predicted completion: {low|medium|high})
| Stage | Score | Drivers |                 ← all five stages, verbatim
{one sentence: the weakest stage and what drives it, in plain words}

## Top findings
1. {severity} · {ref or survey} · {roast} → {fix}   ← up to 10, calculator order
…and {k} more (see --json).                       ← the calculator's own line; the full list is in report.json

## Questions
| Ref | Type | Label | Score | Findings |      ← answerable questions only (statements and groups are not listed); Score `—` = no judged evidence; for more than 30, only rows with findings, then "{m} more questions with no findings"

## What to do first
- {first fix, made concrete with the survey's own words}
- {second}
- {third}
```

- Never alter a number, severity, grade or verdict. Never add findings the calculator did not produce; put any extra observation under a final `## Also noticed` line, clearly marked as outside the score.
- When the calculator prints `Nothing to report.` or `Nothing urgent. Publish.`, keep those lines as they are instead of inventing findings or bullets.
- Findings flagged uncertain keep the calculator's "(Probably …)" or "hunch" wording.
- If `partial` remains true after one retry, add the footer line `Partial: {N} item(s) not judged`.
- Offer, in one line after the report, the files you wrote (`survey.json`, `judgments.json`, `report.json`).

## Quality bar

Before replying, check:

- [ ] `survey.json` passed lint without exit 2, and every `inferred` type was checked.
- [ ] `judgments.json` has `survey_kind`, `audience_kind`, every survey-level item that the kind allows (A1–A3, A5–A10, B1–B5, B7, B8, C1–C7, E1–E9, F1, F2, F3a, F3b, F4, F5, `C5_gap_topic`), and every applicable per-question item and locator for every question.
- [ ] The calculator ran and `meta.partial` is false (or the gaps are listed).
- [ ] On every question you asked yourself the four classic defects: double-barrelled (`Q2_double_barreled`), leading (`Q3a_leading`), presuming (`Q3b_presuming`), options not exhaustive (`Q6_options_not_exhaustive`).
- [ ] Every non-trivial judgment has a note quoting the survey; no note invents text the survey lacks.
- [ ] Blockers (`S01`–`S05`) and high findings appear first, as the calculator ranked them.
- [ ] All numbers in the report are copied from the calculator; none computed by you.
- [ ] Roasts stay specific and witty, never cruel; with `--polite`, none appear.

## Example

Input (pasted text, normalised in step 1; Q5's guessed `short_text` corrected to `long_text`):

```text
# Customer Survey

1. What is your age? (select one)
- 18-25
- 25-35
- 35+

2. How much do you love our fast and friendly support? (select one)
- Love it
- Like it
- It's OK

3. How often do you use the app and the website? (select one)
- Daily
- Weekly
- Monthly

4. Which premium features do you use most? (select all that apply)
- Export
- Sync
- Teams

5. Any other comments?
```

Lint found `S07_no_description`, `S08_no_welcome`, `S09_no_thank_you` and `S12_numeric_range_gap` (Q1: "'18-25' and '25-35' both contain 25"). Judgments snippet (the full file covers every applicable item):

```json
"survey": {"A1_title_specific": {"level": 0, "confidence": 0.9, "note": "'Customer Survey' names no topic"},
           "C3_has_outcome_question": {"p": 0.1, "note": "no satisfaction, NPS or intent question"}},
"questions": {"Q2": {"Q3a_leading": {"p": 0.95, "note": "'How much do you love our fast and friendly support?'"},
                     "Q8_scale_unbalanced": {"p": 0.95, "note": "two positive points, no negative"}},
              "Q3": {"Q2_double_barreled": {"p": 0.95, "note": "'the app and the website'"}},
              "Q4": {"Q3b_presuming": {"p": 0.9, "note": "assumes a premium plan"}}}
```

Report headline from `python <skill-dir>/scripts/survey_score_calc.py survey.json judgments.json --lint --md`:

```markdown
# Survey score: 46/100 · F · not_ready

46/100. 5 questions, 7 serious and 21 moderate issues. Biggest one: Your title "Customer Survey" tells respondents nothing about what they're walking into.

5. high · Q2 · Q2 leads the witness — the wording nudges respondents toward one answer. → Reword Q2 neutrally; drop the loaded or one-sided phrase.
```

What to do first, made concrete: retitle it ("Help us improve Acme support: a 2-minute check-in") and add a welcome line on why you ask and what happens to the answers; add one outcome question ("Overall, how satisfied are you with Acme?"); reword Q2 neutrally ("How would you rate our support?") on a balanced five-point scale.

## No-Python fallback

When no code tool can run (plain chat), keep the same judging and output shape, and estimate the score by hand:

1. Apply the static checks by hand from [static-checks.md](references/static-checks.md), starting with the blockers (`S01`–`S05`) and the high checks (`S13`, `S17`, `S21`, `S28`, `S30`, `S41`, `S51`, and the hybrids `S22`, `S26` once you have judged `Q10`/`Q11`).
2. Judge the rubric as in step 4 and turn each answer into a finding using the severity column of [rubric.md](references/rubric.md), with the confidence downgrades in [scoring.md](references/scoring.md).
3. Follow "Manual tally fallback (no Python)" in [scoring.md](references/scoring.md): count blockers B, high H, medium M, low L (each static id once, plus one if it hits 4 or more questions); points = 100 − 6·H − 3·M − 1·L; apply the caps; read grade and verdict from the table.
4. Headline: `~{points}/100 (manual tally, approximate) · grade {g} · {verdict}`. Replace the category and funnel tables with one line: "Not computed without the calculator." Keep Top findings, Questions (findings only, no scores) and What to do first.
5. Say that the manual tally is approximate and not validated against the calculator.

## Next

- Found problems? Use **survey-fix** to apply the findings (it reads `report.json`), then score again.
- Before launch: **survey-pretest** (simulated respondents), **survey-logic** (screeners and branching), **survey-copy** (welcome, thank-you, invitations), then **survey-export**.
- Want to run it? Import the export into BlockSurvey or your survey tool of choice.
