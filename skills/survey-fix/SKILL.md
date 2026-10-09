---
name: survey-fix
description: Applies the fixes from a survey score report or lint run to the survey itself and returns a patched survey, a before-and-after changes table, the decisions only the author can make, and the expected score impact. Use it after scoring or linting a survey, or whenever someone says "fix my survey", "apply these fixes", "rewrite the bad questions", "make this survey better", "clean up this questionnaire", or pastes a list of problems (double-barreled, leading, missing options, range gaps, no screener, long welcome) for a survey built in Google Forms, Typeform, SurveyMonkey, Qualtrics, on paper or any other tool. Keeps question refs stable and never changes what a question measures without saying so.
license: MIT
metadata:
  author: blocksurvey
  version: "1.0.0"
  category: improve
---

# Survey fix

This skill turns a list of survey problems into a fixed survey. It takes the survey plus a score report (from survey-score), a lint run (from survey-lint), bare finding ids or a pasted list of complaints, applies one tested fix pattern per finding in severity order, keeps every question ref stable, re-runs the static checks, and hands back the patched survey with a changes table that shows every rewrite as before → after. Anything that would change what the survey measures (cutting questions, adding new topics, dropping the anonymity promise) is not applied: it goes to the author as a decision.

## When to use

- A survey has just been scored or linted and the user wants the fixes applied, not just listed.
- The user names problems directly: "Q4 is leading", "the age ranges overlap", "there's no screener".
- A pretest (survey-pretest) produced prioritised fixes mapped to finding ids.
- The user pastes a survey and says "make it better" with no report: run lint first (step 2), fix the static findings, and suggest running survey-score for the judged ones.

## Inputs

Accept, in order of preference:

1. **Survey**: portable survey JSON (see [survey-format.md](references/survey-format.md)). Markdown in the canonical form, or a pasted question list, converts with `python <skill-dir>/scripts/survey_export.py survey.md --format json --out survey.json`. A survey from another tool (exported text, screenshots transcribed, a Google Forms list) is normalised the same way: number the questions `Q1…Qn`, infer types, and mark guessed values `inferred: true`.
2. **Findings**, any of:
   - a score report JSON: read `findings_by_id[]` (one row per id with `severity`, `question_refs`, `fix`, `checklist`) and `findings[]` (per-occurrence `roast`, `evidence`, `uncertain`);
   - lint output from `python <skill-dir>/scripts/survey_lint.py survey.json --json` (a list of findings with `id`, `severity`, `question_ref(s)`, `fix`);
   - bare ids (`Q3b_presuming on Q6, S12 on Q9`) or plain complaints ("Q2 asks two things"): map each complaint to the closest id in [rubric.md](references/rubric.md) or [static-checks.md](references/static-checks.md) and say which id you chose.
3. **Constraints** (ask once, only if unclear): may you add questions? may you reorder? must refs stay as they are, or is renumbering fine? which tool will run it (some tools cannot do display logic)?

If no findings are given at all, lint the survey and work from the static findings; say that judged findings (wording, leading, presuming) need survey-score.

## Procedure

**Paths.** `<skill-dir>` = the folder containing this SKILL.md (for example `~/.claude/skills/survey-fix`). Run every script by its full path, `python <skill-dir>/scripts/survey_lint.py survey.json --json`, from wherever the user's survey is; never assume the current directory is the skill folder (it may be read-only). Use `python3` if `python` is missing. Write working files (`survey.json`, `survey.fixed.json`) next to the user's survey, not inside `<skill-dir>`.

1. **Load the survey and findings.** Convert to JSON if needed. Build one working list of findings: id, severity, refs, uncertain flag. Drop `info` findings (they are notes, not defects). Keep uncertain findings but mark them "applied (judge was unsure)" or skip them if the fix is invasive.
2. **Baseline lint.** Run `python <skill-dir>/scripts/survey_lint.py survey.json --json` and save the output as the "before" static findings. (The script exits 1 when it finds anything; that is expected, not an error.) Merge any static findings the report did not list.
3. **Group by severity.** Order: blocker → high → medium → low. Within a severity, survey-level and structural fixes (welcome, screener, reachability, order) before per-question wording, so later edits land on the final structure.
4. **Apply one pattern per finding.** Look the id up in the index of [fix-patterns.md](references/fix-patterns.md) and apply that pattern. For every edit write one row: ref · finding id · before → after · why. Rules:
   - **Never change meaning silently.** Rewording, re-labelling, adding opt-outs, adding units or windows, moving, gating and type changes that match the wording are applied and shown. Cutting a question, merging two, adding a new topic, or changing what is measured goes to "Decisions for you" with your recommendation.
   - **Keep refs stable.** Edit in place. New questions get a sub-ref of the question before them (`Q5.1`, `Q5.2`; before `Q1` use `Q0`): conditions only accept `Q<digits>` or `Q<digits>.<digits>`, so never `Q5a` or `Q5_a`. Moving a question keeps its ref. If the user asks for clean numbering, renumber last and print a mapping table (old → new), rewriting every ref inside `shown_when`, `jumps[].when` and `jumps[].to`.
   - **Do not invent facts.** Dates, contacts, incentive details, team names the user has not given become `[placeholders]` and are listed as decisions.
   - **One finding, one fix.** If two findings hit the same question (e.g. Q2 and Q19 on Q7), make one combined rewrite and list both ids in its row.
5. **Re-check what you touched.** For each edit, check the knock-on rules in fix-patterns.md (new options vs S12, moved questions vs `shown_when` pointing backwards and S28, added questions vs S27/S16/S17, new `long_text` vs S34). Set `settings.stated_minutes` to the new estimate if the length changed (seconds per question: `single_choice`/`dropdown`/`yes_no` 10, `multi_choice` 15, `short_text` 30, `long_text` 60, rating-type scales 8, `ranking` 25, matrix 8 × rows; the full list is under P17 in fix-patterns.md).
6. **Re-run lint.** Save the patched survey and run `python <skill-dir>/scripts/survey_lint.py survey.fixed.json --json`. Compare with the baseline: list which static ids are gone, which remain, and any new ones. Fix new ones caused by your edits before replying; if one cannot be fixed without a decision, say so.
7. **Estimate the score impact.** Do not compute a new score by hand. Give the direction from the scoring rules: each resolved high finding is worth roughly 4–8 overall points, a medium about half that, a low barely moves it; clearing every blocker lifts the cap of 49. Name the grade band you expect and recommend re-scoring with survey-score for the real number.
8. **Export if asked.** `python <skill-dir>/scripts/survey_export.py survey.fixed.json --format md` (or `txt`, `csv`) for pasting into the user's tool.

## Output contract

Emit exactly these sections, in this order:

```
## Fixed survey
<one fenced json block: the complete patched survey, every field kept, unknown keys preserved>

## Changes
| Ref | Finding | Before | After | Why |
| --- | --- | --- | --- | --- |
| Q7 | Q2_double_barreled | "How fast and friendly was support?" | Q7 "How fast was support's response?" + Q7.1 "How friendly was support?" | Two things in one question |
| survey | S50_welcome_too_long | 184-word welcome | 62-word welcome with time, privacy, contact | Nobody reads walls on a phone |

## Decisions for you
- [ ] <finding id> · <what you recommend> · <what it changes> · <what it saves or gains>

## Lint before → after
Before: <n> static findings (<ids>). After: <n> (<ids>). New: <none | ids + why>.

## Expected impact
<2–4 lines: findings resolved by severity, expected grade band, "re-score with survey-score to confirm">
```

When refs were renumbered, add `## Ref mapping` (`| Old | New |`) after Changes. When nothing could be applied (every fix is a decision), say so in one line and still print Decisions and Lint.

## Quality bar

Before replying, check:

- [ ] Every non-info finding in the input appears either in Changes or in Decisions for you (none silently dropped).
- [ ] Every row in Changes shows a real before → after, not "improved wording".
- [ ] No ref was reused or silently changed; new refs use `Qn.m`; every `shown_when` points at an earlier ref.
- [ ] No question was cut, merged or given a new meaning without being listed as a decision.
- [ ] The after-lint has no blockers and no S28_unreachable_question or S41_screener_without_exit introduced by your edits.
- [ ] Gated questions (P2) have a `shown_when` or a conditional jump into them, so S22_conditional_without_logic cannot fire.
- [ ] Scales across the survey run one direction (B8), are balanced with a midpoint where neutral is real (Q8), label every point on 5-point scales (playbook rule), and label at least the midpoint on 7+ point scales (S36).
- [ ] `settings.stated_minutes` matches the new estimate within the S16 tolerance.
- [ ] Placeholders are bracketed and listed as decisions; nothing was invented.
- [ ] The fixed survey is valid JSON with every original field kept.

## Example

**Input:** a 6-question feedback survey plus a report whose `findings_by_id` holds `S12_numeric_range_gap` (Q1, medium), `Q2_double_barreled` (Q3, high), `Q3b_presuming` (Q4, high), `B3_demographics_placement` (medium), `Q23_actionable` (Q6, low).

**Key output:**

| Ref | Finding | Before | After | Why |
| --- | --- | --- | --- | --- |
| Q3 | Q2_double_barreled | "How easy and fast was checkout?" | Q3 "How easy was checkout?" + Q3.1 "How fast was checkout?" | Two things in one question |
| Q4 | Q3b_presuming | Q4 "How often do you use the app?" (everyone) | new Q3.2 "Do you use the Acme app?" (yes_no); Q4 "In the last 30 days, how often did you use the app?" `shown_when: "Q3.2 is 'Yes'"` | Non-users had no true answer; window added (Q19) |
| Q1 | S12_numeric_range_gap | "Under 25" · "26-35" · "36+" | "Under 25" · "25–34" · "35 or more" | 25-year-olds had no bucket |
| Q1 | B3_demographics_placement | position 1 | moved to the end; `description` "So we can compare age groups."; prefer-not-to-answer added | Earn trust before personal questions |

Decisions for you: `Q23_actionable` · cut Q6 ("How did you hear about us?") — no decision depends on it · saves ~10 s.
Lint before → after: 1 (S12) → 0. Expected impact: two high and two medium resolved; expect roughly one grade band up; re-score to confirm.

## No-Python fallback

When scripts cannot run (plain chat, no code tool):

- Convert pasted text to the JSON shape by hand (refs `Q1…Qn`, portable types from survey-format.md).
- Replace the lint runs with a manual pass over the static checks most fixes touch: S12 (every whole value in one bucket), S28 (something leads to every question), S41 (every `intent: "screener"` has an exit jump or gates a later question), S27 (no 8+ same-type run), S30–S34 (grids ≤ 5 × 8, ranking ≤ 7, radio ≤ 10, open text ≤ 30 %), S43 (labels ≤ 35 words), S50 (welcome ≤ 120 words), S51 (nothing demanding and required in the first three). Label the section `## Lint before → after (manual check)`.
- Everything else (patterns, Changes table, decisions) is unchanged.

## Next

Re-score the fixed survey with **survey-score** to confirm the new grade, then run **survey-pretest** to see how simulated respondents get through it. Flow: create → score → **fix** → pretest → logic → copy → export.

Want to run it? Import the export into BlockSurvey or your survey tool of choice.
