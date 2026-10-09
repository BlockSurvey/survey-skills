# Contributing

Thanks for helping make surveys better. This repo is a set of Agent Skills (`SKILL.md` standard) plus a small, stdlib-only Python core. Everything here is plain markdown and Python 3.9+, so there is nothing to install beyond `pytest`.

```bash
pip install -r requirements-dev.txt
python -m pytest -q                       # all tests
python scripts/validate_skills.py         # every SKILL.md follows the standard + project rules
python scripts/build.py --check           # shared/ files are in sync inside each skill
python scripts/build_catalog.py --check   # README skill tables match the SKILL.md frontmatter
python scripts/build_prompts.py --check   # prompts/ pack matches the skills
```

CI runs all of these on Python 3.9 and 3.12. Drop `--check` to regenerate.

## Ground rules

1. **Generic first.** Skills, examples, templates and type names work for any survey tool: Google Forms, Typeform, SurveyMonkey, Qualtrics, Microsoft Forms, paper, BlockSurvey. BlockSurvey may appear only as one export target and in a one-line call to action. Never make a BlockSurvey account a prerequisite.
2. **No API keys, no network.** Skills never call an LLM API or the internet. The host LLM does the judging and the scripts do the arithmetic. The optional `shared/scripts/survey_judge.py` is the only exception, and it is opt-in via `--provider`.
3. **The LLM judges, code does the math.** If something can be counted (lengths, ranges, duplicates, reachability), it belongs in `survey_lint.py`, not in a judgement.
4. **Roast voice.** Findings are specific, honest and a little funny, never cruel or personal: roast the survey, not the person ("Q2 leads the witness", not "you clearly don't care about your users"). Every roast comes with a concrete fix. `--polite` mode must keep the fix and drop the roast.
5. **Honest numbers.** Don't put a score, test count or claim in docs that a script or test doesn't produce.

## Add a skill

1. **Create the folder** `skills/<name>/`. `<name>` is lowercase-hyphenated and equals the frontmatter `name`.
2. **Write `SKILL.md`** with this frontmatter:
   ```yaml
   ---
   name: survey-example
   description: What it does + when to use it + the words people actually say (max 1024 chars). This is what routes requests to your skill, so include the trigger phrases.
   license: MIT
   metadata:
     author: blocksurvey
     version: "1.0.0"
     category: create   # create | validate | improve | ship
   ---
   ```
   Keep the body at 500 lines or fewer, with: what this skill does, When to use, Inputs, Procedure, Output contract, Quality bar, Example, No-Python fallback and `## Next` (required). Put long material in `references/` and link it from the body (`references/x.md`, one level deep).
3. **Declare shared files** in `skills/<name>/skill.manifest.json`:
   ```json
   { "references": ["survey-format.md"], "scripts": ["survey_common.py", "survey_lint.py"] }
   ```
   Then run `python scripts/build.py` to copy them in. Never edit the synced copies inside a skill. Edit `shared/` and rebuild.
4. **Validate and test:** `python scripts/validate_skills.py && python -m pytest -q`. If you change a script, add tests under `tests/`.
5. **Add it to the catalog:** add a `"try"` sentence (one natural thing a user would say) for the skill in `scripts/catalog_meta.json`, then run `python scripts/build_catalog.py` and `python scripts/build_prompts.py`. Commit the regenerated `README.md`, `README.zh-CN.md` and `prompts/`.
6. **Optional preview:** drop `assets/previews/<name>.gif` (≤ 2 MB, ~15 s) and rebuild the catalog. It appears in the table automatically.

## Propose a rubric item or static check

Open an issue titled `rubric: <short name>` with:

- **The problem** it catches, and one real (anonymised) survey question that has it.
- **Evidence** that it hurts response rate or data quality: a methodology source, a study, or your own A/B numbers.
- **How to judge it**: levels (worst to best) or a yes/no probability, the funnel stage, a proposed weight and severity, and a roast + fix.
- Whether it can be **counted by code** (then it is a static check for `survey_lint.py`) or needs judgement (a rubric item).

Once it's agreed, the change touches `shared/rubric.md` or `shared/static-checks.md`, the scripts, `shared/judging-guide`-style cheat sheets where they exist, and the tests. Then run `python scripts/build.py`.

## Templates

Templates live in `templates/` (synced into `skills/survey-templates/templates/`). A new template must pass `survey_lint.py` with no blocker or high finding, include a screener, an honest time estimate, a welcome and a thank-you, and put demographics last.

## Commits and pull requests

- Use small, focused commits with conventional prefixes (`feat(skills):`, `fix(score):`, `docs:`, `test:`).
- In the PR description, say what changed and paste the test and `--check` output.
- Report bugs with the bug template: which skill, which agent or tool, a survey excerpt, and expected vs actual.
