---
name: survey-create
description: Creates a complete, high-conversion survey from a one-line brief - the decision it informs, what you will be able to say when it closes, a respondent-facing title, a welcome screen that gets people to start (who is asking, why, time, privacy, consent), well-typed questions with screener and skip logic, balanced labelled scales, exhaustive options, demographics last, and a thank-you screen - then self-checks it against a 100-plus-item best-practice checklist and a static linter before handing it over as portable JSON plus markdown. Use when someone asks to create, write, draft, design, build or generate a survey, questionnaire, poll, feedback form, NPS, CSAT, churn or exit survey, customer research, employee or event feedback, or market or academic study, for Google Forms, Typeform, SurveyMonkey, Qualtrics, Microsoft Forms, paper or any other tool. Asks at most three questions, and only when the audience, decision or channel cannot be inferred.
license: MIT
metadata:
  author: blocksurvey
  version: "1.0.0"
  category: create
---

# Survey create

Turns a brief ("a churn survey for our B2B SaaS") into a survey that people start, finish and answer honestly, and that you can actually decide from. Every rule it writes by comes from the [playbook](references/playbook.md), which is the scoring rubric turned inside out, so the survey scores well by construction rather than by luck. The output is always the same shape: a brief (decision, shareables, budget), the survey as portable JSON, the same survey as markdown, a self-check, and a five-line "why this will convert" note. It works for any survey tool; the JSON and markdown import or paste into all of them.

## When to use

- "Create / write / draft / build a survey (or questionnaire, poll, feedback form) for …"
- A named survey type: NPS, CSAT, CES, product-market fit, churn or exit, onboarding, employee engagement or eNPS, event feedback, pricing, customer discovery, academic study, lead qualification.
- Someone has a goal ("find out why trials don't convert") and no questions yet.
- Not for checking an existing survey (use `survey-score` or `survey-lint`) or patching one (use `survey-fix`).
- If a ready-made template fits the request closely, `survey-templates` is faster; this skill can start from one of those templates and tailor it.

## Inputs

Accept any of: a one-line brief, a longer brief, notes, a list of draft questions, or an existing survey to rebuild. Pull out these facts:

| Fact | Ask only if it cannot be inferred | Default when it can be inferred but isn't stated |
| --- | --- | --- |
| **Decision** the survey informs | yes | infer from the survey type (churn → "which churn drivers to fix first") |
| **Audience**, precisely (who, plus a qualifying behaviour and a time window) | yes | the obvious population for the survey type, with a recall window |
| **Channel** (email link, in-app, QR at an event, panel, paper) | yes, if it changes length or tone | email link, answered on a phone |
| Sponsor (who is asking), contact, closing date | no | use placeholders `{team}`, `{contact}`, `{date}` and list them under "Fill before sending" |
| Incentive | no | none (never invent one) |
| Anonymous or not | no | anonymous, unless the survey needs contact details |
| Language | no | the brief's language |

**Clarifying questions: at most 3, in one message, and only for decision, audience or channel when they truly cannot be inferred.** Otherwise state your assumptions in the brief and proceed. A brief like "a churn survey for a B2B SaaS" needs zero questions: the decision, audience and channel are all inferable.

If the input is a pasted list of questions, normalise it first: `python scripts/survey_export.py draft.md --format json --out draft.json` (guessed types are marked `inferred: true`; confirm them).

## Procedure

Work in one pass. Load [playbook.md](references/playbook.md) once (it holds the rules and the pre-flight checklist); open [question-types.md](references/question-types.md), [survey-format.md](references/survey-format.md) or [static-checks.md](references/static-checks.md) only when a step needs a detail they hold. For worked examples, see [examples.md](references/examples.md).

1. **Read the brief and fix the frame.** Extract the facts in the Inputs table. Ask (≤ 3 questions) or write down assumptions. Produce: the facts list.
2. **Write the decision and the shareables.** One sentence, "After this survey we will decide ___." Then 3–5 shareables: the sentences you will be able to say when it closes ("42 % of churned teams left over missing integrations"). Each shareable needs at least one question that produces it; each question must feed at least one shareable or the decision. (A7, C1, Q23)
3. **Pick kind, audience and budget.** Set `kind` (research, feedback, form, quiz, assessment, information), `audience` (precise, with a behaviour and a time window), `purpose` (the decision sentence) and `sponsor`. Budget by default: **≤ 12 answerable questions and ≤ 5 minutes; hard cap 20 questions unless the user asks for more**; open-ended ≤ 30 % of questions, ≤ 3 required, placed after the closed questions they explain. (K_survey_kind, X2, E6, S17, S34)
4. **Write the title, welcome and thank-you** (playbook §2, §3, §13):
   - Title: topic + purpose, addressed to the respondent, with the time if it helps ("Why did your team leave Acme Projects? 4 minutes to help us fix it"). Never an internal name. (A1, A2, S01)
   - Welcome, ≤ 120 words, one short paragraph then bullets: who is asking (A9); why their input matters and what changes because of it (A3, A8, E4); who it is for (A6); time, honestly (S15); how answers are handled (A5); "Taking part is voluntary; you can stop at any time" for research (F2); closing date if any (A10); a contact (F5); incentive with how and when it is delivered, only if real (F3a, F3b). No pressure, guilt or flattery (F4). (E7, S50)
   - Thank-you: thanks, what happens next and when, the incentive delivery again if any, the contact. (E3, S09, F5)
5. **Draft the questions**, in funnel order, each with `ref` (Q1…Qn), a portable `type` from [question-types.md](references/question-types.md), `intent`, `required`, and `label`:
   - **Screener first** when the audience is specific: one closed, required question (often `yes_no` with a recall window) with an exit jump `{"when": "Q1 is 'No'", "to": "end"}`. (C2, S41)
   - **Open easy**: the first answerable question is a one-click closed question on the title's topic. Nothing required and demanding (long text, grid, ranking, file, email, phone) in the first three. (B2, S46, S51, Q15)
   - **The outcome question early**, in the first half: overall satisfaction, NPS, effort, disappointment, or intent, measuring real experience rather than only a hypothetical. (C3, Q18, Q24)
   - **"Why" after the key closed questions**: one optional `long_text` "What is the main reason for your score?", gated with `shown_when` when it only applies to some answers (`"Q3 <= 6"`). (C4, Q10, S22)
   - **Gate every conditional question** with `shown_when` naming an earlier ref, or give it a "Not applicable" option. Ask "Do you use X?" before "How often do you use X?". (Q3b, Q10, S22)
   - **Group by topic**, general → specific; signpost topic changes with a short `statement` ("Next: the programme"). Never two grids back to back; never 8+ questions of one type in a row. (B1, B4, S27, S31)
   - **Each label**: one question, one sentence, ≤ 35 words, neutral ("How satisfied or dissatisfied…"), plain words, positive phrasing, a recall window ("in the last 30 days") for behaviour, units and formats ("in USD per month") for amounts. No "obviously", "always", "never", "should", "don't you agree". (Q1, Q2, Q3a, Q4, Q17, Q19, Q22, S35, S43)
   - **Options**: exhaustive (`has_other`, `has_none`, "Not sure", `has_prefer_not_to_answer` where someone might not fit), mutually exclusive, numeric buckets with no gaps or overlaps (`Under 25`, `25–34`, `35–44`, `45 or more`), parallel in form, one idea each; more than 6 unordered options → `randomize_options: true`; more than 10 → `dropdown`; a pick limit in the label → `selection.max`. (Q6, Q7, Q14, Q20, S11, S12, S14, S33, S38, S39, S40)
   - **Scales**: balanced, same direction everywhere (negative → positive), every point labelled on 5-point scales, midpoint labelled on 7+; NPS exactly 0–10 with "How likely are you to recommend [X] to a friend or colleague?" and endpoints "Not at all likely" / "Extremely likely"; grids ≤ 5 columns × 8 rows. (Q8, B8, S36, S37, S30)
   - **Type matches wording**: "Select all that apply" → `multi_choice`; a `yes_no` label starts with Do/Does/Did/Are/Is/Have/Has/Can/Will/Would/Could. Closed beats open for anything you can list. (Q9, Q25, S13, S45)
   - **Demographics last**, only those you will cut the data by (≤ 25 % of questions), each optional with a one-line reason in `description` ("So we can compare answers across team sizes") and `has_prefer_not_to_answer`. Sensitive questions (age, gender, income, health…) also set `sensitive: true`. (B3, C6, Q12, Q16, S23)
   - **Contact details** only when needed, optional, after the content, gated by a "Would you be open to a call?" `yes_no`; never on an anonymous survey. (S21, S48)
   - **Every entry has a role**: questions collect, `statement`s inform (`role: information`), `consent` asks for agreement (`role: consent`). (R_role)
6. **Set honest settings.** Estimate time from [question-types.md](references/question-types.md#seconds-per-type) (closed ≈ 10 s, matrix 8 s per row, `long_text` 60 s, `short_text` 30 s, statement 8 s). Set `settings.stated_minutes` to the estimate rounded to the nearest whole minute (round up when in doubt), and use the same number in the welcome and title. Set `anonymous` (false if you collect contact details) and `progress_bar: true`. (S15, S16, S21, S24)
7. **Self-check.**
   - Save the survey as `survey.json` and run `python scripts/survey_lint.py survey.json --json`. Exit code 0 means no blocker or high finding. Fix every **blocker** and **high** finding, then re-run until clean. Fix medium and low findings too unless the brief justifies them; list any you keep, with the reason.
   - Walk the playbook's **Pre-flight checklist** (Decide, Start, Continue, Finish, Answer quality, Actionability) in one pass. Record the ids you satisfied per stage, and any rule you bent with the reason (for example "C2: no screener, the audience is everyone on the mailing list").
8. **Score, if available.** If the `survey-score` skill is installed, score `survey.json` with it and revise against its top findings until the score is **≥ 85 or after two revision passes**, whichever comes first. Re-run lint after each revision. If it is not installed, skip this step and say so in the self-check.
9. **Export and hand over.** Run `python scripts/survey_export.py survey.json --format md --out survey.md` and emit the output contract below. Keep `survey.json` and `survey.md` on disk when you have file access.

## Output contract

Emit exactly these sections, in this order, with these headings:

````
## Survey brief
- **Decision:** After this survey we will decide … (one sentence)
- **Shareables:** (3–5 bullets, each a sentence you will be able to say, e.g. "X % of … because …")
- **Kind:** feedback · **Audience:** … · **Channel:** … · **Budget:** N questions, ~M min
- **Assumptions:** … (or "None: everything came from the brief.")
- **Fill before sending:** {team}, {contact}, {date} … (or "Nothing.")

## Survey (JSON)
```json
{ … the complete survey, valid against schemas/survey.schema.json, every question with ref, type, label, intent, required … }
```

## Survey (markdown)
```markdown
… the exact output of survey_export.py --format md …
```

## Self-check
- **Lint:** 0 blocker · 0 high · N medium · N low (each remaining finding: id, ref, why it stays)
- **Time:** estimated X.X min, stated M min
- **Checklist:** Decide: ids … · Start: ids … · Continue: ids … · Finish: ids … · Answer quality: ids … · Actionability: ids …
- **Bent rules:** id: reason (or "None.")
- **Score:** NN/100 after K passes (or "survey-score not installed; not scored.")

## Why this will convert
1. Start: … (cite ids)
2. Continue: … (cite ids)
3. Finish: … (cite ids)
4. Answer quality: … (cite ids)
5. Actionability: … (cite ids)
````

Exactly five numbered lines under "Why this will convert", one per funnel stage, each naming the concrete choice and the ids it satisfies. No other sections, no preamble beyond one sentence.

## Quality bar

Before replying, confirm every line:

- [ ] Decision sentence written; 3–5 shareables, each traceable to a question; every question traceable to a shareable. (A7, C1, Q5, Q23)
- [ ] `kind`, `audience`, `purpose`, `sponsor` set; ≤ 12 answerable questions and ≤ 5 min unless justified; never over 20 unless asked. (K_survey_kind, X2, E6, S17)
- [ ] Title is respondent-facing; welcome ≤ 120 words with sponsor, purpose, benefit, audience, time, privacy, consent line (research), contact; thank-you says what happens next. (A1, A2, A3, A5, A6, A8, A9, F2, F5, E3, E7, S50)
- [ ] Screener with an exit when the audience is specific; every conditional question gated. (C2, S41, Q10, S22)
- [ ] First question closed and easy; nothing required and demanding in the first three; outcome question in the first half. (B2, S46, S51, Q24)
- [ ] Open-ended ≤ 30 % and late; demographics last, optional, with reasons and "Prefer not to answer". (S34, B7, B3, C6, S23)
- [ ] Options exhaustive, exclusive, parallel; scales balanced, labelled, one direction; NPS standard. (Q6, Q7, Q14, Q8, B8, S36, S37)
- [ ] `stated_minutes` matches the estimate and the welcome; no PII on an anonymous survey. (S16, S21)
- [ ] `python scripts/survey_lint.py survey.json --json` shows no blocker or high finding; the JSON validates against the schema (only `title`, `questions`, and each question's `ref`, `type`, `label` are required; types are from the 20 portable types).
- [ ] Output has exactly the five contract sections, and the markdown is the script's output, not hand-written (unless in fallback).

## Example

**Input:** "Create a churn survey for a B2B SaaS."

**Key output (abridged; full version in [examples.md](references/examples.md)):**

- **Decision:** After this survey we will decide which two churn drivers to address in next quarter's roadmap.
- **Shareables:** "The top reason teams leave is …"; "X % were satisfied right up to leaving, so price or fit, not quality, drove it"; "Teams that left for a competitor went to …"; "Churn reasons differ (or don't) by team size".
- **Assumptions:** audience = account admins who cancelled or downgraded in the last 30 days; channel = email one day after cancellation; not anonymous (optional follow-up call).
- **Questions (11):** Q1 screener "What happened to your team's subscription in the last 30 days?" → end if nothing changed · Q2 main reason (8 randomised options + Other) · Q3/Q4 gated follow-ups (which tool, which features) · Q5 satisfaction before leaving (outcome, 5-point labelled) · … · demographics last with reasons · optional call `yes_no` gating an email.
- **Self-check:** Lint 0 blocker · 0 high · 0 medium · 0 low; estimated 3.3 min, stated 4.
- **Why this will convert, line 2:** "Continue: one-click screener with an exit, then the main reason as a closed question; no required typing in the first three (B2, S41, S46, S51)."

## No-Python fallback

If scripts cannot run (plain chat, no shell):

1. Write the JSON by hand following [survey-format.md](references/survey-format.md); check that `title` and `questions` exist and every question has `ref`, `type` (one of the 20 portable types) and `label`.
2. Lint by hand against these thresholds from [static-checks.md](references/static-checks.md): title present (S01); ≥ 2 options on every choice question (S04); no numeric range gaps or overlaps (S12); "select all" only on `multi_choice` (S13); screener has an exit (S41); first answerable question not open text (S46); nothing required and demanding in the first three (S51); no PII before the outcome question (S48); open-ended ≤ 30 % (S34); grids ≤ 5 × 8 (S30), no two grids adjacent (S31); labels ≤ 35 words (S43); welcome ≤ 120 words (S50); no PII when anonymous (S21); `yes_no` labels start with Do/Are/Have… (S45); NPS 0–10 with "likely" (S37).
3. Estimate time by hand: Σ seconds per type ÷ 60.
4. Write the markdown by hand using the template in [survey-format.md](references/survey-format.md#markdown-form).
5. In the self-check, write "Lint: manual (scripts unavailable)" and list the checks you walked.

## Next

Score it: run **survey-score** on `survey.json` for a 0–100 grade, a funnel view and ranked findings (then **survey-fix** for anything it flags). Flow: **create** → score → fix → pretest → logic → copy → export.

Want to run it? Import the export into BlockSurvey or your survey tool of choice.
