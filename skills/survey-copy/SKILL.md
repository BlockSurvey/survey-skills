---
name: survey-copy
description: Writes the conversion copy around a survey so more people start and finish it - welcome screen, thank-you page, invitation email with subject lines, a halfway reminder, a last-day reminder and an SMS or chat message. Covers who is asking, why, what is in it for the respondent, time to complete, privacy, consent, deadline, incentive delivery and contact, with honest urgency only. Use when someone asks to write or improve a welcome screen, intro text, thank-you page, survey invitation, invite email, reminder email, subject line, SMS invite, or wants a better response rate before sending a survey built in Google Forms, Typeform, SurveyMonkey, Qualtrics or any other tool. Accepts the survey JSON (and updates its welcome and thank_you) or just a title, purpose, audience, incentive, deadline and sponsor. Tone warm, neutral or formal.
license: MIT
metadata:
  author: blocksurvey
  version: "1.0.0"
  category: ship
---

# Survey copy

What this skill does: it writes every piece of text a respondent reads outside the questions themselves, the welcome screen, the thank-you screen, the invitation email, two reminders and a short SMS or chat message, so that people click Start, trust the sender and know what happens next. Each piece is built from the start-of-funnel rules in [references/playbook.md](references/playbook.md) (sections 3 and 13) and checked against the rubric items that judge that text, so a survey that goes through this skill scores well on purpose, privacy, sponsor, time, deadline, incentive and contact by construction. Facts are never invented: anything the user has not given becomes a visible `[placeholder]`.

## When to use

- The survey is written and the user wants the welcome / intro, thank-you page, invitation, reminders or subject lines.
- A score report flags start-of-funnel items: `A3_purpose_explained`, `A5_privacy_stated`, `A6_audience_stated`, `A8_respondent_benefit`, `A9_sponsor_named`, `A10_deadline_stated`, `E3_thank_you_quality`, `E4_welcome_motivates`, `E7_welcome_scannable`, `F2_consent_language`, `F3b_incentive_delivery_clear`, `F5_contact_provided`, or static `S07`, `S08`, `S09`, `S15`, `S50`.
- Response rate is low and the user wants to rewrite the ask, not the questions.
- Not for the questions themselves (use `survey-fix`) or for routing (use `survey-logic`).

## Inputs

Accept either:

1. **A survey JSON** in the portable format ([references/survey-format.md](references/survey-format.md)). Read `title`, `description`, `kind`, `audience`, `purpose`, `sponsor`, `language`, `welcome`, `thank_you`, `settings.stated_minutes`, `settings.anonymous`, and scan the questions for `email` / `phone` / `collects_pii` (it decides what you may say about anonymity).
2. **A survey in markdown or pasted text.** Normalise it first: save it to a file and run `python scripts/survey_export.py survey.md --format json --out survey.json`. Types it guessed carry `inferred: true`; they don't matter for copy, but mention that the file was normalised.
3. **Just the facts**, no survey: title, purpose (the decision or what changes), audience, time in minutes, sponsor, incentive (what, how, when), deadline, contact, privacy handling, and whether it is research with people (consent needed).

Optional: `--tone warm|neutral|formal` (default: warm for customer and event surveys, neutral for employee and feedback, formal for academic research, healthcare, government and senior B2B audiences), channel (email, in-app, SMS, Slack/Teams), sender name, and the survey link (otherwise `{link}`).

Facts you must not make up: sponsor, incentive, deadline, contact, privacy handling (anonymous or not, who sees answers, retention), and what will change. If one is missing, write `[sponsor]`, `[deadline]`, `[contact email]`, etc. in the copy and list it under **Fill before sending**. Ask at most one question, and only when the missing fact blocks the whole job (for example, nobody knows who is running the survey).

## Procedure

Run scripts from the skill directory with Python 3.9+ (`python3` where `python` is not on the PATH).

1. **Collect the facts.** Produce a short fact sheet: sponsor, audience, purpose (what changes because of the answers), time (from `settings.stated_minutes`; if absent, use the estimate from a `survey-lint` or `survey-score` report, or ask; never round down), privacy (anonymous only if `settings.anonymous` is true **and** no question collects PII, else say who sees the answers), consent needed (`kind: research` or human-subjects study), incentive (what / how / when, or none), deadline (or none), contact, results-sharing promise. Mark each as given or `[placeholder]`.
2. **Pick the tone and the angle.** Choose the tone (input or default above) and the WIIFM angle for the audience from [references/copy-patterns.md](references/copy-patterns.md) (customer, employee, event, research, lead-gen). Load that file now; you need its openers, privacy lines and words to avoid.
3. **Write the welcome screen** (title + description + button). Lead with who is asking and why it matters to the respondent, then bullets: time, privacy, consent line (research only), deadline (if any), incentive (if any), contact. **≤ 80 words** in `welcome.description` (the lint cap `S50_welcome_too_long` is 120; 80 keeps it to one phone screen). Title ≤ 8 words; button is a verb ("Start", "Share my view").
4. **Write the thank-you screen.** Thanks, what happens next (when results are shared or what changes), how and when the incentive arrives (if any), contact. ≤ 60 words.
5. **Write the invitation email.** Three subject-line options, each ≤ 50 characters, no ALL CAPS, no "URGENT", no clickbait. Body ≤ 120 words: why them, why it matters, time, privacy, deadline, incentive, a plain-text call to action on its own line (`Start the survey: {link}`), contact, a named human sender.
6. **Write two reminders.** Reminder 1, around day 3 ("halfway": the survey is still open, here is why it matters). Reminder 2, on the last day ("closes tonight" or "closes tomorrow", only if that is true). Three subject lines each (≤ 50 characters), body ≤ 80 words. Send only to non-respondents; if the tool cannot filter, add "If you've already answered, thank you, and please ignore this." No fake urgency, no guilt, no "last chance" when it is not (`F4_manipulative_framing`). If there is no deadline, reminder 2 becomes a plain final reminder with no time claim.
7. **Write the SMS / chat variant.** ≤ 160 characters including `{link}` (count `{link}` as 23 characters, a typical short link) and, for SMS, the opt-out text the channel requires ("Reply STOP to opt out"). Sponsor, ask, time, link.
8. **Check every piece in one pass** against the Quality bar below and build the checklist table. Count words with `len(text.split())` and characters with `len(text)`; fix anything over a limit before replying.
9. **Update the JSON** (when one was given): replace `welcome` (`title`, `description`, `button`) and `thank_you` (`title`, `description`) with the new text, keep every other key untouched, set `settings.stated_minutes` if you stated a time it lacked. Write it back (as `survey.json` or the user's filename), then run `python scripts/survey_export.py survey.json --format md` and show the `## Welcome` and `## Thank you` sections so the user sees the result in place. Placeholders stay in the JSON as `[…]`; say so.

## Output contract

Emit these headings, in this order, every time (use `n/a` with a reason when a piece does not apply, never drop a heading):

~~~
## Fact sheet
| Fact | Value | Source |            (given / from survey JSON / [placeholder])

## Welcome screen
**Title:** …
**Description:** …                 (multi-line, bullets with "•")
**Button:** …
Words: N / 80

## Thank-you screen
**Title:** …
**Description:** …
Words: N / 60

## Invitation email
Subject options:
1. … (N chars)
2. … (N chars)
3. … (N chars)
Body:
…
Start the survey: {link}
…
Words: N / 120

## Reminder 1: halfway (day 3)
Subject options: 1–3 (N chars each)
Body: …   Words: N / 80

## Reminder 2: closes tonight (last day)
Subject options: 1–3 (N chars each)
Body: …   Words: N / 80

## SMS / chat
…   Characters: N / 160

## Checklist
| Rubric id | Satisfied by | Status |   (one row each: A3 A5 A6 A8 A9 A10 E3 E4 E7 F2 F3 F4 F5; Status = yes / n/a (reason) / needs [placeholder])

## Fill before sending
- [placeholder] → what to put there      (or "Nothing: every fact was given.")

## Updated survey JSON
```json
{ "welcome": { … }, "thank_you": { … }, "settings": { "stated_minutes": … } }
```
~~~

The last block shows only the changed keys; the full file is written to disk when a JSON was given. Without a survey JSON, show the same keys so the user can paste them into any tool's welcome and thank-you screens.

## Quality bar

Run this before replying. Every line must hold or be reported in the checklist.

- [ ] `A9_sponsor_named`: the sponsor is named in the welcome, the email's first two lines and the SMS. A human name signs the email.
- [ ] `A3_purpose_explained` (aim for level 3): topic, why the answers matter, and how they will be used, in the welcome and the email.
- [ ] `A8_respondent_benefit` (aim for level 2): a concrete outcome ("we'll share results in May", "decides what we fix next") or a named incentive. "Help us improve" alone is level 1.
- [ ] `A6_audience_stated`: the welcome or email says who it is for ("anyone who invoiced with Acme in the last 3 months").
- [ ] `A5_privacy_stated`: one line on anonymity / who sees answers. Never write "anonymous" if the survey asks for an email, phone or name (`S21_anonymous_but_pii`); write "confidential: only [team] sees your answers" instead.
- [ ] Time stated, matching `settings.stated_minutes` (`S15_no_time_expectation`, `S16_time_mismatch`).
- [ ] `F2_consent_language` (research only): "Taking part is voluntary; you can skip any question or stop at any time."
- [ ] `A10_deadline_stated`: the closing date in the welcome, email and reminders, when there is one. Reminder 2's urgency is true.
- [ ] `F3a_incentive_mentioned` / `F3b_incentive_delivery_clear`: mentioned only if real; what, how and when, repeated on the thank-you screen.
- [ ] `F5_contact_provided`: a contact in the welcome or thank-you, and in every email.
- [ ] `E3_thank_you_quality` (aim for level 2): thanks plus what happens next.
- [ ] `E4_welcome_motivates` (level 2) and `E7_welcome_scannable` (level 2): starts with why their input matters; purpose, time and privacy each on their own line; ≤ 80 words.
- [ ] `F4_manipulative_framing`: no guilt, flattery, false scarcity or pressure words (list in [references/copy-patterns.md](references/copy-patterns.md#words-to-avoid)).
- [ ] Limits: welcome ≤ 80 words, thank-you ≤ 60, invitation ≤ 120, reminders ≤ 80, subject lines ≤ 50 characters, SMS ≤ 160 characters.
- [ ] Every missing fact is a visible `[placeholder]` listed under Fill before sending; nothing is invented.
- [ ] The language matches `language` in the survey; the copy reads at a plain, general-audience level (`E5_reading_level`).

## Example

Input: `tests/fixtures/acme_feedback.json` style survey (feedback, Acme product team, 3 minutes, anonymous, open until 30 May, contact research@acme.example, no incentive), `--tone warm`.

Key output:

```
## Welcome screen
**Title:** Help shape Acme Invoicing
**Description:** We're the Acme product team, and we want to hear from anyone who sent an
invoice with Acme in the last 3 months. Your answers decide which two problems we fix next,
and we'll share the results in our May update.
• Takes about 3 minutes
• Anonymous: only the product team sees answers
• Voluntary: skip any question or stop at any time
• Open until 30 May. Questions? research@acme.example
**Button:** Start
Words: 71 / 80

## Invitation email
Subject options:
1. 3 minutes to shape Acme Invoicing (33 chars)
2. What should Acme fix next? (26 chars)
3. Your invoicing feedback, by 30 May (34 chars)

## Reminder 2: closes tonight (last day)
Subject options: 1. Acme survey closes tonight (26 chars) …
Body: Hi {first_name}, the Acme Invoicing survey closes at midnight tonight. If you
haven't had 3 minutes yet, this is the moment: your answers decide what we fix next quarter.
Start the survey: {link}
If you've already answered, thank you, and please ignore this. Priya, Acme product team

## Checklist (excerpt)
| A10 | welcome bullet 4, invitation, both reminders | yes |
| F2  | welcome bullet 3 | yes (not required: kind is feedback) |
| F3  | - | n/a (no incentive) |
```

## No-Python fallback

The script is only used to normalise pasted text and to preview the result. Without Python: read the pasted survey directly and take the facts from it; write the copy as above; count words and characters by hand (or estimate and stay well under each limit); and hand back the new `welcome` and `thank_you` objects as a JSON block for the user to paste. Say that the preview step was skipped.

## Next

Copy done: export the survey with `survey-export` (markdown for review, plain text for any tool's text import, CSV for a spreadsheet pass, JSON to keep). If the welcome changed a promise (time, anonymity), re-run `survey-lint` first to confirm `S15`, `S16`, `S21` and `S50` are clean.

Want to run it? Import the export into BlockSurvey or your survey tool of choice.
