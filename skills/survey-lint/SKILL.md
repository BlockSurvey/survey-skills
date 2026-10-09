---
name: survey-lint
description: Fast, deterministic survey lint with no AI judgement - runs the 44 deterministic static checks (of 48 in the catalogue; the other 4 are hybrids that need AI judgements) (missing title or questions, empty options, overlapping or gapped number ranges, duplicate questions, too many open-text boxes, oversized grids, unreachable questions, screeners with no exit, early friction and more) in about a millisecond, prints a findings table with fixes, and returns an exit code for CI. Works on survey JSON, markdown or a pasted question list. Use when the user asks to lint, quick-check, validate or sanity-check a survey or form structurally, wants a repeatable check with no LLM, or wants to gate a survey file in CI or a pre-commit hook. For a full 0-100 quality score with wording and coverage judgements, use survey-score.
license: MIT
metadata:
  author: blocksurvey
  version: "1.0.0"
  category: validate
---

# Survey lint

Runs the deterministic half of the survey review: the 44 static checks (the catalogue has 48; the 4 hybrids need AI judgements and run only in survey-score) that need counting, thresholds and structure, never opinion. The same survey always gives the same findings, so the result is safe to automate. It catches the mistakes that break a survey outright (blockers such as no questions, an empty question, a choice with one option) and the ones that quietly cost completions or data quality (number ranges with gaps, five text boxes in a row, a 10-row grid, a screener that never screens anyone out). It does not judge wording, bias or coverage; that is **survey-score**.

## When to use

- "Lint / quick-check / validate this survey", or any request for a fast structural check.
- In CI or a pre-commit hook, to block a survey file with a blocker or high-severity problem.
- While editing, as a cheap loop between full scores.
- When the user explicitly wants no LLM judgement, or results that are reproducible run to run.
- Not for "is this survey good?": use **survey-score**, which includes this lint plus 77 judged rubric items.

## Inputs

| Input | What to do |
| --- | --- |
| Portable survey JSON (`title`, `questions` with `ref`, `type`, `label`) | Use as is. Format: [survey-format.md](references/survey-format.md). |
| Markdown or a pasted question list | Save to `survey.md`, then normalise (step 1). |
| A survey-tool export (Google Forms, Typeform, SurveyMonkey, Qualtrics…) | Map it by hand to the portable JSON with the field tables in [survey-format.md](references/survey-format.md), using portable type names. |

When pasting text, put each option on its own line (`- option`); options written inline after the question are folded into the label and then trip blocker `S04_options_too_few`.

Nothing else is needed. Settings such as `settings.stated_minutes`, `jumps`, `shown_when` and `required` make the checks sharper; copy them over when the source has them.

## Procedure

`<skill-dir>` = the folder containing this SKILL.md (for example `~/.claude/skills/survey-lint`). Run every command from the **user's** folder, the one holding their survey, so `survey.json` and any output stay next to the survey and never inside `<skill-dir>` (it may be read-only). Scripts need Python 3.9+ and nothing else; use `python3` if `python` is missing.

1. **Normalise → `survey.json`.** JSON input: use it. Markdown or pasted text: `python <skill-dir>/scripts/survey_export.py survey.md --format json --out survey.json`, then correct any question marked `"inferred": true` whose guessed type is wrong (an "Email" box → `email`, "Any other comments?" → `long_text`). Produce: a valid `survey.json` and a list of inferred types.
2. **Lint.** `python <skill-dir>/scripts/survey_lint.py survey.json`
   - Prints a markdown table (`Severity | Check | Question | Roast | Fix`), or `No static findings.`
   - `--json` prints the findings as a JSON array (for tools); `--polite` drops the roast and keeps the fix.
3. **Read the exit code.**

| Exit | Meaning | CI action |
| --- | --- | --- |
| `0` | No blocker or high finding (medium/low may exist). | Pass. |
| `1` | At least one `blocker` or `high` finding. | Fail the build. |
| `2` | Invalid input: unreadable file, bad JSON, or not a survey. A one-line reason is printed on stderr. | Fail; fix the file. |

4. **Present** the result per the output contract. Copy the table verbatim; add nothing to it.

### CI usage

Vendor the skill into the repository (or install it on the runner) and call the script by the path to the vendored skill; here it is `vendor/survey-lint`.

```bash
python vendor/survey-lint/scripts/survey_lint.py surveys/onboarding.json || exit 1
```

GitHub Actions step (fails the job on exit 1 or 2):

```yaml
- name: Lint surveys
  run: |
    for f in surveys/*.json; do
      python vendor/survey-lint/scripts/survey_lint.py "$f" --polite || exit 1
    done
```

Use `--json` to feed findings into another tool (each finding has `id`, `severity`, `category`, `scope`, `question_ref`, `question_refs`, `funnel`, `roast`, `fix`, `evidence`).

## Output contract

```markdown
# Survey lint: {k} finding(s) · {b} blocker · {h} high · {m} medium · {l} low · exit {0|1|2}

_{Inferred: Q3 type → email, … | Nothing inferred.}_

| Severity | Check | Question | Roast | Fix |     ← the script's table, verbatim, already sorted by severity

{One line: "Fix the blockers first: {ids}." when any; otherwise "No blockers." }

_Static checks only. Wording, bias, coverage and the 0–100 score need survey-score._
```

With no findings: the heading with `0 finding(s) · exit 0`, the line `No static findings.`, and the static-only footer. With exit 2: the reason from stderr and what to fix, no table.

## Quality bar

- [ ] The script actually ran; the table is its output, not your re-creation.
- [ ] Counts in the heading match the table rows; the exit code is the real one.
- [ ] Every `inferred` type was checked before linting (a wrong type causes false findings such as `S34_open_ended_overload`).
- [ ] Blockers (`S01_no_title`, `S02_no_questions`, `S03_label_empty`, `S04_options_too_few`, `S05_matrix_empty`) are named first when present.
- [ ] No opinions on wording or bias added; that is survey-score's job.

## Example

Input (pasted text):

```text
# Product Survey v2

1. What is your annual income? (select one)
- Under 25k
- 26k-50k
- 50k-100k

2. How much do you love our amazing new dashboard and reporting?
- A lot
- Somewhat

3. Email address

4. Any comments?
```

After step 1 (Q3 corrected to `email`, Q4 to `long_text`), `python <skill-dir>/scripts/survey_lint.py survey.json` gives, among others:

```markdown
| medium | S07_no_description |  | You haven't told people why they're here. No description, no welcome text. | Add a welcome screen that explains the purpose in two sentences. |
| medium | S12_numeric_range_gap | Q1 | Q1: 'Under 25k' then '26k-50k' — where does 25000–25999 go?; '26k-50k' and '50k-100k' both contain 50000 | Rewrite Q1's ranges so every value lands in exactly one bucket (no gaps, no shared boundaries). |
```

Exit `0`: nothing blocks publishing, but the leading Q2 and the bare "Product Survey v2" title are judgement calls that only survey-score will catch.

## No-Python fallback

When the script cannot run, apply the checks by hand from [static-checks.md](references/static-checks.md) and say the result is lower fidelity. Work in this order:

1. Blockers: `S01`–`S05` (no title, no questions, empty label, fewer than 2 options, empty matrix).
2. High: `S13_selection_hint_type_mismatch`, `S17_length_fatigue` (more than 50 questions, no logic), `S21_anonymous_but_pii`, `S28_unreachable_question`, `S30_matrix_too_large` (more than 8 rows), `S41_screener_without_exit`, `S51_early_friction` (a required long text, file, email, phone, matrix or ranking in the first 3 questions).
3. The rest of the catalogue, using its exact thresholds (for example `S34`: open-ended above 30 % of questions or more than 3 required; `S43`: label over 35 words).
4. Emit the same output contract with `exit —` in the heading and the footer "Applied by hand; approximate."

Skip the hybrid checks (`S22`, `S23`, `S25`, `S26`): they need judged evidence and run only in survey-score.

## Next

- Want the full picture (wording, bias, coverage, funnel, 0–100 score)? Use **survey-score**.
- Then **survey-fix** to apply the findings, and **survey-export** to ship it.
- Want to run it? Import the export into BlockSurvey or your survey tool of choice.
