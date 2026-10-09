<div align="center">

# BlockSurvey Skills

**Create surveys people actually finish, and score any survey the way an expert would, inside the AI you already use.**

[English](README.md) · [中文](README.zh-CN.md)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-9-8A2BE2.svg)](#the-skills)
[![Agent Skills standard](https://img.shields.io/badge/Agent%20Skills-SKILL.md%20standard-111111.svg)](https://agentskills.io)
[![Tests](https://github.com/BlockSurvey/blocksurvey-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/BlockSurvey/blocksurvey-skills/actions/workflows/ci.yml)
[![Built with Claude Opus](https://img.shields.io/badge/built%20with-Claude%20Opus-D97757.svg)](https://www.anthropic.com/claude)

[![Claude Code](https://img.shields.io/badge/Claude%20Code-✓-D97757.svg)](#30-second-install)
[![Codex](https://img.shields.io/badge/Codex%20CLI-✓-10A37F.svg)](#30-second-install)
[![Cursor](https://img.shields.io/badge/Cursor-✓-000000.svg)](#30-second-install)
[![Gemini CLI](https://img.shields.io/badge/Gemini%20CLI-✓-4285F4.svg)](#30-second-install)
[![ChatGPT](https://img.shields.io/badge/ChatGPT%20%2F%20Claude.ai-✓-74AA9C.svg)](#no-file-system-chatgpt-claudeai)

</div>

- ✍️ **Create high-conversion surveys** from a one-line brief: screener and skip logic, balanced scales, a welcome screen that gets people to start, demographics last. Every best practice is built in from the start.
- 🎯 **Score any survey 0–100** with **77 expert rubric checks + 48 static checks**: a grade, a publish verdict, a funnel showing where people will drop off, and ranked findings, each with a fix.
- 🔑 **No API keys.** Everything runs in your own LLM (Claude Code, Codex, Cursor, Gemini CLI, ChatGPT). The math is done by small Python scripts with no dependencies, so nothing gets sent anywhere.

Works for any survey: **Google Forms, Typeform, SurveyMonkey, Qualtrics, Microsoft Forms, paper, BlockSurvey**, or a list of questions you paste in.

---

## 30-second install

**Any agent (recommended).** Installs all 9 skills into the agents you use, via the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add BlockSurvey/blocksurvey-skills
```

Just one skill: `npx skills add BlockSurvey/blocksurvey-skills --skill survey-score`

<details>
<summary><b>Manual install (Claude Code, Codex CLI, Cursor, Gemini CLI)</b></summary>

```bash
git clone https://github.com/BlockSurvey/blocksurvey-skills.git
```

| Agent | Copy the skills here |
| --- | --- |
| Claude Code | `cp -r blocksurvey-skills/skills/* ~/.claude/skills/` |
| Codex CLI | `cp -r blocksurvey-skills/skills/* ~/.codex/skills/` |
| Cursor | `cp -r blocksurvey-skills/skills/* .cursor/skills/` (inside your project) |
| Gemini CLI | `cp -r blocksurvey-skills/skills/* ~/.gemini/skills/` (or `.gemini/skills/` in a project) |

Each skill folder is self-contained (its `references/` and `scripts/` come with it), so you can copy just the ones you want.

</details>

### No file system (ChatGPT, Claude.ai)

Upload [`prompts/<skill>.md`](prompts/) to a **Project** or **custom GPT**, then ask in plain words. Each file is a single-file version of one skill. Without the scripts, it follows the skill's built-in *No-Python fallback*.

### Then just ask

You never type a skill name. Say what you want and the agent picks the right skill from its description:

> "score this survey" · "create a churn survey for a B2B SaaS" · "fix my survey" · "add skip logic" · "write the invite email" · "export it for Google Forms"

## Try it

Copy-paste any of these into your agent:

```text
Create a churn survey for a B2B SaaS: people who cancelled in the last 30 days.
```

```text
Score this survey and tell me what to fix first:
1. How much do you love our fast and friendly support?
- Love it
- Like it
- It's OK
```

```text
Fix my survey using the score report, then score it again.
```

```text
Pretest this questionnaire with 6 simulated respondents. Where will people drop off?
```

```text
Only show the "why?" question to detractors, and screen out anyone who is not a customer.
```

```text
Write the welcome screen, invitation email and two reminders, then export it so I can paste it into Typeform.
```

## The skills

<!-- catalog:start -->
**9 skills** in 4 categories. Each one is a folder with a `SKILL.md`.

### ✍️ Create (2)

_Start from a brief or a proven template._

| Skill | What it does | Try saying |
| --- | --- | --- |
| [**survey-create**](skills/survey-create/SKILL.md) | Creates a complete, high-conversion survey from a one-line brief. | “Create a churn survey for a B2B SaaS that cancelled in the last 30 days.” |
| [**survey-templates**](skills/survey-templates/SKILL.md) | A library of 12 ready-to-use, pre-validated survey templates. | “Give me an NPS survey template for Acme Projects that closes on 30 November.” |

### ✅ Validate (2)

_Know if it is ready before anyone sees it._

| Skill | What it does | Try saying |
| --- | --- | --- |
| [**survey-score**](skills/survey-score/SKILL.md) | Score any survey, questionnaire or form 0-100 against a professional 77-item rubric plus 48 static checks, and get a grade, a publish verdict, a funnel view of… | “Score this survey and tell me what to fix first.” |
| [**survey-lint**](skills/survey-lint/SKILL.md) | Fast, deterministic survey lint with no AI judgement. | “Lint survey.json and fail CI on any blocker or high finding.” |

### 🔧 Improve (3)

_Fix the problems, route the right people, test it on simulated respondents._

| Skill | What it does | Try saying |
| --- | --- | --- |
| [**survey-fix**](skills/survey-fix/SKILL.md) | Applies the fixes from a survey score report or lint run to the survey itself and returns a patched survey, a before-and-after changes table, the decisions… | “Fix my survey using the score report.” |
| [**survey-logic**](skills/survey-logic/SKILL.md) | Designs and checks survey routing. | “Only show the follow-up to detractors and screen out non-customers.” |
| [**survey-pretest**](skills/survey-pretest/SKILL.md) | Runs a synthetic cognitive pretest of a survey before launch. | “Pretest this questionnaire with simulated respondents. Where will people drop off?” |

### 🚀 Ship (2)

_Get people to start it, then get it into your survey tool._

| Skill | What it does | Try saying |
| --- | --- | --- |
| [**survey-copy**](skills/survey-copy/SKILL.md) | Writes the conversion copy around a survey so more people start and finish it. | “Write the welcome screen, invite email and two reminders for this survey.” |
| [**survey-export**](skills/survey-export/SKILL.md) | Exports a survey into formats any survey tool can take. | “Export this survey so I can paste it into Google Forms.” |
<!-- catalog:end -->

They chain together: **create → score → fix → pretest / logic → copy → export**. Each skill ends by pointing you to the next one.

## Before / after

The deliberately bad example from the [survey-score skill](skills/survey-score/SKILL.md):

```text
# Customer Survey
1. What is your age?                                  18-25 · 25-35 · 35+
2. How much do you love our fast and friendly support? Love it · Like it · It's OK
3. How often do you use the app and the website?      Daily · Weekly · Monthly
4. Which premium features do you use most?            Export · Sync · Teams
5. Any other comments?
```

```text
Survey score: 46/100 · F · not_ready
46/100. 5 questions, 7 serious and 21 moderate issues. Biggest one: Your title
"Customer Survey" tells respondents nothing about what they're walking into.

high · Q2 · Q2 leads the witness — the wording nudges respondents toward one answer.
          → Reword Q2 neutrally; drop the loaded or one-sided phrase.
```

**What the findings say to fix** (the survey-fix skill applies these for you):

| Problem | Fix |
| --- | --- |
| "Customer Survey", no welcome, no thank-you | Specific title, a welcome with who is asking, why, time, privacy and a deadline, plus a thank-you that says what happens next |
| Q1 age ranges overlap at 25, and age comes first | `18–24 · 25–34 · 35+`, moved to the end with a reason and a "prefer not to say" option |
| Q2 leading, scale has no negative side | "How would you rate our support?" on a balanced, labelled five-point scale |
| Q3 asks about two things ("the app *and* the website") | Split into two questions |
| Q4 assumes everyone is on a premium plan | A screener with skip logic shows it only to premium users |
| No outcome question | An NPS or overall satisfaction question, with "why?" shown only to low scorers |

**The clean shape**, as in the test fixture [`tests/fixtures/acme_feedback.json`](tests/fixtures/acme_feedback.json) (8 questions, about 3 minutes), scores **98/100 · A · ready**: a screener first, NPS with a "why?" shown only to detractors, one matrix, open text kept optional, demographics last.

See the worked examples in [`examples/`](examples/README.md), for example [the SaaS churn survey report](examples/saas-churn/report.md).

## How the score works

Your LLM reads the survey and fills in a **judgments file**: a level or probability for each rubric item, plus a short note quoting the survey. A script with no dependencies turns that into the score. **The LLM judges, code does the math.** No API calls, and the same judgments always give the same number.

```
survey ──► survey_lint.py (48 static checks, ~1 ms)
       ──► your LLM judges the 77 rubric items in ONE pass ──► judgments.json
       ──► survey_score_calc.py ──► score · grade · verdict · categories · funnel · ranked fixes
```

**Seven perspectives** (ported from BlockSurvey's in-product Survey Score):

| | Perspective | What it checks (examples) |
| --- | --- | --- |
| **A** | Purpose & framing | Specific, respondent-facing title; purpose, privacy, audience, benefit, sponsor, deadline |
| **B** | Structure & flow | Logical order, an easy opener, demographics placement, sections, redundancy, scale direction |
| **C** | Coverage & gaps | Covers the objective; screener; outcome question; the missing "why"; obvious gaps; attention check |
| **D** | Question quality (each question) | Clarity, double-barrelled, leading, presuming, jargon, options exhaustive and non-overlapping, balanced scales, recall period, units, social desirability, best type |
| **E** | Respondent experience | Tone, burden, welcome that motivates, scannable welcome, reading level, straight-lining risk, thank-you |
| **F** | Trust & ethics | Sensitive topics, consent language, clear incentive, manipulative framing, contact provided |
| **G** | Conversion | A composite of what makes people start and finish (benefit, sponsor, scannable welcome, end-loading, abandon risk) |

Plus **48 static checks** (S01–S51): no title, overlapping number ranges, duplicate questions, an unreachable question, a screener with no exit, too many open-text boxes, oversized grids, early friction, and more. Category weights adapt to the kind of survey (customer satisfaction, market research, employee, academic, lead gen, registration, event).

**The funnel view** shows where you lose people:

| Stage | The question it answers |
| --- | --- |
| `start` | Will they click Start? |
| `continue` | Will they get through the first three questions? |
| `finish` | Will they reach Submit? |
| `answer_quality` | Will the answers be usable? |
| `actionability` | Can you make a decision from the data? |

**Grades and verdicts:**

| Score | Grade | Verdict |
| --- | --- | --- |
| ≥ 90 | A | `ready` |
| 80–89 | B | `ready` |
| 75–79 | C | `ready` |
| 70–74 | C | `needs_work` |
| 60–69 | D | `needs_work` |
| 50–59 | E | `needs_work` |
| < 50, or any blocker | F | `not_ready` |

Details: [`shared/scoring.md`](shared/scoring.md) · [`shared/rubric.md`](shared/rubric.md) · [`shared/static-checks.md`](shared/static-checks.md). Findings come as short, specific roasts ("Q2 leads the witness"). Ask for a polite tone and you get neutral wording with the same fixes.

### Optional: automate scoring with your own API key (CI / batch)

Every skill works without a key. If you want scoring to run unattended, for example in CI or over a folder of surveys, copy [`.env.example`](.env.example) to `.env` and fill in **one** provider:

| Provider | Variables |
| --- | --- |
| TypeSafe Jev | `TYPESAFE_API_KEY`, `TYPESAFE_MODEL` |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |

```bash
python shared/scripts/survey_judge.py survey.json --provider openai --dry-run          # prints the cost estimate, sends nothing
python shared/scripts/survey_judge.py survey.json --provider openai --out judgments.json
python shared/scripts/survey_score_calc.py survey.json judgments.json --lint --md
```

The script makes one batched request per survey and prints a cost estimate first. It only runs when you pass `--provider`. See [`shared/judge.md`](shared/judge.md).

## What's inside

```
blocksurvey-skills/
├── skills/                 9 installable skills (SKILL.md + references/ + scripts/)
│   ├── survey-create/      survey-templates/ (12 templates)
│   ├── survey-score/       survey-lint/
│   ├── survey-fix/         survey-pretest/      survey-logic/
│   └── survey-copy/        survey-export/
├── shared/                 the knowledge core, synced into each skill by scripts/build.py
│   ├── rubric.md           77 rubric items: levels, weights, severities, roasts, fixes
│   ├── static-checks.md    48 static checks
│   ├── scoring.md          weights, grades, funnel, manual-tally fallback
│   ├── playbook.md         rules for writing surveys, ordered by the funnel
│   └── scripts/            survey_lint.py · survey_score_calc.py · survey_export.py · survey_common.py
├── templates/              12 templates (NPS, CSAT, CES, PMF, churn, pricing, …), all lint clean
├── schemas/                survey.schema.json, the portable survey format
├── prompts/                single-file versions of the skills for ChatGPT / Claude.ai (generated)
├── examples/               briefs → surveys → score reports
└── tests/                  215+ pytest tests, run in CI on Python 3.9 and 3.12
```

The scripts use only the Python standard library (3.9+). Nothing to `pip install`.

## FAQ

<details>
<summary><b>What does it cost?</b></summary>

Nothing beyond the chat or agent you already pay for. The skills make no API calls. Scoring a survey is one judging pass in your own conversation, plus two local scripts that finish in milliseconds.

</details>

<details>
<summary><b>Where does my survey go? (privacy)</b></summary>

Nowhere new. It stays in your conversation with the LLM you already use, and the scripts run on your machine. The only thing that ever calls an API is the optional `survey_judge.py`, and only when you run it with `--provider` and your own key.

</details>

<details>
<summary><b>Which models does it work with?</b></summary>

Any capable model that follows instructions: Claude, GPT, Gemini, and others. The judging steps are written as explicit checklists with a fixed output shape, so results stay consistent across models. Stronger models catch more wording problems.

</details>

<details>
<summary><b>Does it work offline?</b></summary>

The scripts do: `survey_lint.py`, `survey_score_calc.py` and `survey_export.py` need no network. The judging is done by whatever model your agent runs on, so it works offline if your model is local.

</details>

<details>
<summary><b>Can I add my own checks?</b></summary>

Yes. Static checks live in `shared/scripts/survey_lint.py` and `shared/static-checks.md`, and rubric items live in `shared/rubric.md`. To propose one upstream, open an issue with evidence (see [CONTRIBUTING.md](CONTRIBUTING.md)). For a private rule, fork the repo and run `python scripts/build.py` to sync it into every skill.

</details>

<details>
<summary><b>How is this related to BlockSurvey?</b></summary>

The BlockSurvey team built it. The rubric and scoring are ported from BlockSurvey's in-product Survey Score. You don't need a BlockSurvey account: it works for any survey tool, and BlockSurvey is just one of the export targets.

</details>

<details>
<summary><b>Does the manual (no-Python) score match the script?</b></summary>

Not exactly. In plain chat with no code tool, the skill does a manual tally and labels it `approximate`. It lands in the same grade band in typical cases, but use the script when you need an exact number.

</details>

## Contributing

New skills, rubric items backed by evidence, templates and translations are all welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md). Short version: `python scripts/build.py && python scripts/validate_skills.py && python -m pytest -q && python scripts/build_catalog.py`.

Found a bug? [Open an issue](https://github.com/BlockSurvey/blocksurvey-skills/issues/new/choose) and include the skill, the agent you used and a survey excerpt.

## Roadmap

- [x] **v1.0**: 9 skills, 77-item rubric, 48 static checks, 12 templates, prompt pack, CI
- [ ] Preview GIFs for every skill (`assets/previews/`)
- [ ] Full Chinese translation of the README and skill guides
- [ ] More templates (healthcare intake, UX research, course evaluation, …)
- [ ] More judge providers for the optional `survey_judge.py`
- [ ] Listings in skills directories and a ready-made GPT

## Star history

[![Star History Chart](https://api.star-history.com/svg?repos=BlockSurvey/blocksurvey-skills&type=Date)](https://star-history.com/#BlockSurvey/blocksurvey-skills&Date)

---

<div align="center">

Built by the [BlockSurvey](https://blocksurvey.io) team · ported from BlockSurvey's in-product Survey Score · built with Claude Opus · [MIT](LICENSE)

Want to collect responses privately once the survey is ready? Import the export into [BlockSurvey](https://blocksurvey.io), or into any tool you like.

</div>
