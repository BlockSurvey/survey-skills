# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org/).

## 1.0.0 — 2026-10-09

First public release.

### Skills (9)

- **Create:** `survey-create` (a high-conversion survey from a one-line brief, self-checked), `survey-templates` (12 pre-validated templates).
- **Validate:** `survey-score` (0–100 score against a 77-item rubric + 48 static checks, with grade, verdict, funnel and ranked roast-and-fix findings), `survey-lint` (deterministic static checks with CI exit codes).
- **Improve:** `survey-fix` (applies a score report's fixes and returns a patched survey and a changes table), `survey-pretest` (synthetic cognitive pretest with personas and a drop-off table), `survey-logic` (skip logic, branching, screeners and a reachability check).
- **Ship:** `survey-copy` (welcome, thank-you, invitation, reminders, SMS), `survey-export` (markdown, text, CSV and JSON, plus import steps for Google Forms, Typeform, SurveyMonkey, Qualtrics, BlockSurvey, Microsoft Forms and paper).

### Scripts (4, stdlib only)

- `survey_lint.py` runs the static checks, `survey_score_calc.py` turns judgments into a deterministic score and report, `survey_export.py` converts to and from markdown, text and CSV, and `survey_common.py` holds the shared helpers.

### Knowledge and content

- Shared rubric (77 items, 7 perspectives), static-check catalogue (48), scoring rules with weight profiles by survey kind, and a writing playbook ordered by the funnel.
- 12 templates, all lint clean: NPS, CSAT, CES, product-market fit, churn exit, onboarding, employee engagement, event feedback, Van Westendorp pricing, customer discovery, academic consent study, lead qualification.
- Worked examples in `examples/` (brief → survey → score report).
- Prompt pack in `prompts/`: single-file versions of each skill for ChatGPT and Claude.ai Projects.

### Tooling

- `scripts/build.py` (syncs shared files into skills), `scripts/validate_skills.py`, `scripts/build_catalog.py` (README tables from frontmatter), `scripts/build_prompts.py` (prompt pack), and a CI workflow on Python 3.9 and 3.12.
- An optional `survey_judge.py` with `.env.example` for automated scoring with your own TypeSafe Jev, OpenAI or Anthropic key. No skill requires a key.
