# Golden examples

Three surveys built from one-line briefs and scored, plus one deliberately bad survey. Each folder has the brief and the self-check (`brief.md`), the survey (`survey.json`), the judge's answers (`judgments.json`) and the calculator's report (`report.md`, `report.json`).

| Example | Kind | Questions | Minutes (est. / stated) | Score · grade · verdict | Top finding |
| --- | --- | --- | --- | --- | --- |
| [saas-churn](saas-churn/) | feedback (customer satisfaction profile) | 9 | 3.1 / 4 | 94 · A · ready | None ("Nothing to report.") |
| [event-feedback](event-feedback/) | feedback (event feedback profile) | 9 | 4.1 / 4 | 96 · A · ready | None ("Nothing to report.") |
| [employee-engagement](employee-engagement/) | feedback (employee engagement profile) | 7 | 3.9 / 4 | 92 · A · ready | low · `A1_title_specific`: the title names a topic, not a purpose |
| [bad-survey](bad-survey/) | feedback (customer satisfaction profile) | 40 | 9.7 / 3 | 11 · F · not_ready | high · `Q1_clarity` on Q11: "Don't you agree that our pricing is fair and our support is helpful?" can be read two ways |

"Questions" counts answerable questions (statements excluded). Minutes are the calculator's estimate and the survey's `settings.stated_minutes`.

## How they were produced

The three good surveys were written by following [`survey-create`](../skills/survey-create/SKILL.md) literally from the one-line brief at the top of each `brief.md`: decision and shareables first, then title, welcome and thank-you, then the questions, the lint self-check and the pre-flight checklist. Each was then scored by following [`survey-score`](../skills/survey-score/SKILL.md): lint, one judging pass over every applicable rubric item using the [judging guide](../skills/survey-score/references/judging-guide.md), then the calculator. The bad survey was written by hand to plant defects and judged the same way. Nothing was tuned to hit a number: the judgments say what each survey's words support, and every survey-level answer and every flagged question carries a note quoting its evidence. Every score, grade, verdict, roast and fix in `report.md` and `report.json` is unedited calculator output. Any revisions are listed under "Iterations" in each `brief.md`. Only the employee-engagement survey needed one, a lint fix before it was scored.

`tests/test_examples.py` guards all of this. It checks each survey against the schema, checks the lint expectations, and re-runs the calculator on the committed judgments to confirm it reproduces each `report.json` exactly.

## Regenerate

From the repository root, for any example:

```bash
python3 shared/scripts/survey_lint.py examples/saas-churn/survey.json --json
python3 shared/scripts/survey_score_calc.py examples/saas-churn/survey.json examples/saas-churn/judgments.json --lint --md > examples/saas-churn/report.md
python3 shared/scripts/survey_score_calc.py examples/saas-churn/survey.json examples/saas-churn/judgments.json --lint --json > examples/saas-churn/report.json
```

The calculator exits `1` for the bad survey. That is its result, not an error. If you change a survey, re-judge it (the judgments describe that exact wording) before regenerating the report.

Placeholders such as `{company}`, `{product}`, `{event}`, `{date}` and `{contact}` are left for you to fill before sending.
