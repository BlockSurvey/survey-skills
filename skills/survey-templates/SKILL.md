---
name: survey-templates
description: A library of 12 ready-to-use, pre-validated survey templates - NPS, CSAT, customer effort (CES), product-market fit (Sean Ellis 40 % test), churn and cancellation exit, onboarding feedback, employee engagement with eNPS and drivers, post-event feedback, Van Westendorp pricing, customer discovery (jobs to be done), an academic consent study with Likert constructs, and lead qualification - each with a screener, honest time, a welcome and thank-you screen, balanced scales and demographics last, and each passing the static linter with no blocker or high findings. Fills in your company, product, event, team and dates, trims or extends to fit, re-lints, and hands back portable JSON plus markdown for Google Forms, Typeform, SurveyMonkey, Qualtrics or any other tool. Use when someone asks for a survey template, a sample or example questionnaire, a standard NPS or CSAT survey, or wants a proven starting point fast.
license: MIT
metadata:
  author: blocksurvey
  version: "1.0.0"
  category: create
---

# Survey templates

Twelve complete surveys for the jobs people run surveys for most often. Each is written by the [playbook](references/playbook.md) rules: a respondent-facing title, a welcome under 120 words (who is asking, why, time, privacy, consent, contact), a screener with an exit, the outcome question early, gated follow-ups, fully labelled balanced scales, open text kept short and late, demographics last with "Prefer not to answer", and a thank-you that says what happens next. Every template passes `scripts/survey_lint.py` with zero blocker or high findings (and, as shipped, zero findings of any severity). This skill picks the right one, fills in the placeholders, tailors it, re-lints it and hands it over.

## When to use

- "Give me an NPS / CSAT / CES / eNPS survey template."
- "I need a churn (exit, cancellation) survey", "a post-event survey", "an onboarding survey", "a product-market-fit survey", "a pricing survey", "a customer discovery survey", "a consent form plus questionnaire for my study", "a lead qualification form".
- Someone wants a proven starting point now and will tailor it afterwards.
- When nothing below fits, or the brief is unusual, use `survey-create` instead (it can still borrow from a template).

## Inputs

- The survey type or goal (required), in any words. Match it to the table below.
- Values for the placeholders. Every template uses `{company}`, `{team}` (the team running it, e.g. "product team"), `{date}` (closing date) and `{contact}` (an email address); most use `{product}` or `{event}`. A few have extra variables, listed in the table.
- Optional tailoring: audience details, the options that fit their domain (for example their real cancellation reasons), questions to drop or add, the language.

Ask only for what you cannot infer. Anything still unknown stays as its `{placeholder}` and is listed under "Fill before sending"; never invent a name, email address, date or incentive.

## Templates

| File | Kind | Audience | Questions | ~Min | When to use | Key outcome question |
| --- | --- | --- | --- | --- | --- | --- |
| [nps.json](templates/nps.json) | feedback | customers active in the last 3 months | 6 | 2 | Track loyalty over time; find what separates promoters from detractors | "How likely are you to recommend {product} to a friend or colleague?" (0–10) |
| [csat.json](templates/csat.json) | feedback | customers who contacted support in the last 7 days | 7 | 3 | After a support interaction; find which part of support to fix | "Overall, how satisfied or dissatisfied were you with the support you received?" (5-point) |
| [ces.json](templates/ces.json) | feedback | customers who completed a task in the last 7 days | 7 | 3 | After a task (setup, plan change, refund); find where effort is highest | "{company} made it easy for me to get this done." (7-point agree) |
| [product_market_fit.json](templates/product_market_fit.json) | research | people who used {product} 2+ times in the last 2 weeks | 9 | 3 | Test product-market fit (40 % "Very disappointed" benchmark) and find your core segment | "How would you feel if you could no longer use {product}?" |
| [churn_exit.json](templates/churn_exit.json) | feedback | customers who cancelled or downgraded in the last 30 days | 11 | 4 | Right after cancellation or downgrade; rank churn reasons | "Overall, how satisfied or dissatisfied were you with {product} before you made this change?" plus the main-reason question |
| [onboarding_feedback.json](templates/onboarding_feedback.json) | feedback | people who signed up in the last 30 days | 9 | 4 | 2–4 weeks after sign-up; find where new users get stuck | "Overall, how easy or difficult has it been to get started with {product}?" |
| [employee_engagement.json](templates/employee_engagement.json) | feedback | everyone employed at {company} for 1+ month | 8 | 5 | Twice-yearly engagement pulse; eNPS plus 9 drivers, anonymous | "How likely are you to recommend {company} as a place to work to a friend or colleague?" (eNPS) |
| [event_feedback.json](templates/event_feedback.json) | feedback | people who registered for {event} | 8 | 4 | Within 48 hours of an event (in person, online or hybrid) | "How likely are you to recommend {event} to a friend or colleague?" |
| [pricing_van_westendorp.json](templates/pricing_van_westendorp.json) | research | people who choose or pay for tools like {product} | 11 | 3 | Before setting or changing a price; Van Westendorp's 4 price questions plus context. Extra: `{currency}`, `{product_description}` | The four price points (too cheap, bargain, getting expensive, too expensive), plus current satisfaction and interest |
| [customer_discovery.json](templates/customer_discovery.json) | research | people who did the job in the last 3 months | 13 | 5 | Early discovery, jobs-to-be-done style: trigger, current tools, pain, spend. Extra: `{job}` (e.g. "hire a freelancer"), `{job_past}` ("hired a freelancer"), `{currency}` | "Overall, how satisfied or dissatisfied are you with the way you handle this today?" |
| [academic_consent_study.json](templates/academic_consent_study.json) | research | adults who used {product} for work in the last 3 months | 12 | 5 | University or ethics-reviewed study: consent, age check, Likert constructs (Technology Acceptance Model), demographics. Extra: `{institution}`, `{ethics_ref}`, `{retention}` | "Overall, how satisfied or dissatisfied are you with {product}?" plus usefulness, ease-of-use and intention batteries |
| [lead_qualification.json](templates/lead_qualification.json) | form | visitors who asked for a demo or pricing | 8 | 2 | Demo or pricing request form; routes buyers, researchers, customers and job seekers | None (a form): qualifies on reason, size, timeline and role |

Question counts are answerable questions (statements excluded); minutes are what each template promises, close to the estimate in [survey-format.md](references/survey-format.md).

## Procedure

1. **Pick the template.** Match the request to the "When to use" column. If two fit (for example NPS and CSAT), say which you chose and why in one line. If none fits, switch to `survey-create`.
2. **Copy it** to `survey.json` from `templates/<file>.json` (in this skill's folder).
3. **Collect variable values.** Infer what you can from the conversation (company, product, event). Ask for the rest in one message, at most 3 questions; anything still unknown stays a placeholder.
4. **Fill the placeholders** in every string (title, description, audience, purpose, sponsor, welcome, thank-you, labels, descriptions, options). With Python:
   ```
   python -c "import json,sys; v=json.loads(sys.argv[2]); s=open(sys.argv[1]).read(); [s:=s.replace('{'+k+'}',json.dumps(x)[1:-1]) for k,x in v.items()]; open(sys.argv[1],'w').write(s)" survey.json '{"company":"Acme","product":"Acme Projects","team":"product team","date":"30 November","contact":"research@acme.example"}'
   ```
   Then search the file for any remaining `{` placeholders and list them under "Fill before sending". Re-read every label once: substitutions must read naturally (watch articles and plurals).
5. **Tailor** (only where the user's context calls for it):
   - Replace generic options with the user's real ones (churn reasons, support channels, departments, roles), keeping them exhaustive, exclusive and parallel, with `has_other` where someone might not fit. If you change an option, update every condition that quotes it (`"Q2 is 'Switched to another product'"`).
   - Adjust recall windows and the audience line together (a quarterly NPS uses "in the last 3 months" in both).
   - **Trim** questions that do not serve the user's decision. Never remove the screener's exit, the outcome question, or the welcome's time, privacy and contact lines. When you remove a question, delete or redirect every `shown_when` and `jumps` that names its ref, then renumber refs Q1…Qn and update all conditions to match.
   - **Extend** within budget: ≤ 12 answerable questions and ≤ 5 minutes by default, never over 20 unless asked; open-ended ≤ 30 %; new questions follow the playbook (portable type, `intent`, neutral one-sentence label, gated follow-ups, demographics last with a reason).
6. **Re-time.** If the question count changed, re-estimate (closed ≈ 10 s, matrix 8 s per row, `long_text` 60 s, `short_text` 30 s, statement 8 s) and update `settings.stated_minutes`, the welcome bullet and the title so all three agree.
7. **Always re-lint**: `python scripts/survey_lint.py survey.json --json`. Fix every blocker and high finding and re-run until the exit code is 0. Fix medium and low findings unless the user's context justifies them.
8. **Export**: `python scripts/survey_export.py survey.json --format md --out survey.md`, then emit the output contract.

## Output contract

````
## Template used
{file} — {kind}, {N} questions, ~{M} min. Why this one: … (one line)

## Variables
| Variable | Value |
| --- | --- |
| {company} | … |
| … | … |

## Changes from the template
- … (one bullet per change: options replaced, questions trimmed or added, refs renumbered; or "None: used as shipped.")

## Survey (JSON)
```json
{ … the complete filled-in survey … }
```

## Survey (markdown)
```markdown
… the exact output of survey_export.py --format md …
```

## Self-check
- **Lint:** 0 blocker · 0 high · N medium · N low (each remaining finding: id, ref, why it stays)
- **Time:** estimated X.X min, stated M min

## Fill before sending
- {placeholder}: what to put there (or "Nothing.")
````

## Quality bar

- [ ] The template matches the request; if it was a judgement call, the reason is stated.
- [ ] No `{placeholder}` remains except those listed under "Fill before sending"; nothing invented (names, emails, dates, incentives).
- [ ] Substituted text reads naturally in every label, option and screen.
- [ ] Any changed option is reflected in every condition that quotes it; refs are sequential and every `shown_when` / `jumps` points at an existing earlier ref or `end`. (S28, S41)
- [ ] Screener exit, outcome question, welcome time / privacy / contact lines are intact. (S41, C3, A5, F5, S15)
- [ ] Budget respected: ≤ 12 questions and ≤ 5 min by default, open-ended ≤ 30 %, demographics last. (E6, S34, B3)
- [ ] `stated_minutes`, welcome and title agree with the estimate. (S16)
- [ ] `python scripts/survey_lint.py survey.json --json` exits 0 (no blocker or high).

## Example

**Input:** "I need an NPS survey for Acme Projects. Close it on 30 November; replies to research@acme.example."

**Key output:**

- **Template used:** `nps.json`, feedback, 6 questions, ~2 min. Why: a recurring loyalty score with a reason and a priority question.
- **Variables:** `{company}` Acme · `{product}` Acme Projects · `{team}` product team · `{date}` 30 November · `{contact}` research@acme.example.
- **Changes from the template:** Q5 options replaced with Acme's roadmap themes (Time tracking, Client portal, Faster loading, Integrations, Mobile app, Lower price), `has_other` kept.
- **Self-check:** Lint 0 blocker · 0 high · 0 medium · 0 low; estimated 1.8 min, stated 2.
- **Fill before sending:** Nothing.

## No-Python fallback

1. Open the template file and copy its JSON.
2. Replace each `{placeholder}` by hand; then search for `{` to catch any you missed.
3. Hand-check the lint thresholds that tailoring can break: every choice question keeps ≥ 2 options (S04); numeric buckets have no gaps or overlaps (S12); "Select all" only on `multi_choice` (S13); the screener keeps its exit (S41); no condition quotes an option or ref that no longer exists (S28); open-ended ≤ 30 % (S34); labels ≤ 35 words (S43); welcome ≤ 120 words (S50); no email or phone on an anonymous survey (S21).
4. Write the markdown by hand using the template in [survey-format.md](references/survey-format.md#markdown-form), and write "Lint: manual (scripts unavailable)" in the self-check.

## Next

Score it: run **survey-score** on the filled-in `survey.json` to confirm it still grades well after tailoring (then **survey-fix** for anything it flags). Flow: create → score → fix → pretest → logic → copy → export.

Want to run it? Import the export into BlockSurvey or your survey tool of choice.
