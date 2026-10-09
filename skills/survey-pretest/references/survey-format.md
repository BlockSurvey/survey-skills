# Survey format

Every skill reads and writes one portable survey format, defined by [`schemas/survey.schema.json`](https://github.com/BlockSurvey/survey-skills/blob/main/schemas/survey.schema.json) in the repository (not bundled with the skill; this file is the working reference). This file walks through it, gives a complete annotated example, defines the condition language used by `shown_when` and `jumps`, and specifies the canonical markdown form that `survey_export.py` writes and reads.

The schema is lenient: unknown keys are allowed and kept, and only `title`, `questions`, and each question's `ref`, `type` and `label` are required. Scripts treat a field of the wrong type as missing and never crash on it.

## Survey fields

| Field | Type | Default | What it is | Read by |
| --- | --- | --- | --- | --- |
| `title` | string | — (required) | What respondents see first. Say what it is about and for whom. | A1, A2, S01 |
| `description` | string | `""` | One or two sentences under the title. | A3, A5, A6, A9, S07 |
| `kind` | `research` \| `feedback` \| `form` \| `quiz` \| `assessment` \| `information` | — | What the survey is for. Same keys as `K_survey_kind`; picks which items apply and the weight profile. | scoring |
| `audience` | string | — | Who should answer, in words. | X2, Q4, E5 |
| `purpose` | string | — | The decision the survey informs. Not shown to respondents; used by the judge and by `survey-create`. | A7, C1, Q5, Q23 |
| `sponsor` | string | — | The organisation or team running it. | A9 |
| `language` | BCP-47 string | `"en"` | Language of the text. | E9 |
| `welcome` | `{title, description, button}` | — | The welcome screen. | A3–A10, E4, E7, F2, F5, S08, S15, S50 |
| `thank_you` | `{title, description, button}` | — | The thank-you screen. | E3, F3b, F5, S09 |
| `settings.stated_minutes` | number | 5 in the schema; lint treats absent as "not stated" | The time promised to respondents. | S15, S16, A8 |
| `settings.progress_bar` | boolean | `true` | Show a progress bar. | S24 |
| `settings.anonymous` | boolean | `false` | Responses are anonymous (then collect no PII). | S21 |
| `settings.randomize_questions` | boolean | `false` | Shuffle question order (skips order-based checks such as S28). | S28 |
| `settings.sign_in_required` | boolean | `false` | Respondents must sign in. | (reserved for S29) |
| `settings.captcha` | boolean | `false` | Captcha before submit. | — |
| `settings.multiple_submissions` | boolean | `false` | Allow repeat submissions. | — |
| `questions` | array | — (required) | The questions in order. | everything |

## Question fields

| Field | Type | Default | What it is | Read by |
| --- | --- | --- | --- | --- |
| `ref` | string | — (required) | Stable reference: `Q1`, `Q2`, … in order. Conditions and jumps use it. Never reuse a ref. | all |
| `type` | one of the 20 types | — (required) | See [question-types.md](question-types.md). | Q9, Q25, many static checks |
| `label` | string | — (required) | The question text. One question, one sentence, ≤ 35 words. | Q1–Q4, S03, S43 |
| `description` | string | `""` | Help text under the label: definitions, units, why it is asked. | Q4, Q16, Q22 |
| `required` | boolean | `false` | Must be answered. | Q15, S18, S23, S51 |
| `options` | string[] | — | Choice options, in display order. | Q6, Q7, Q14, S04, S11, S12 |
| `has_other` | boolean | `false` | Adds "Other (please specify)" with a text box. | Q6, S39 |
| `has_none` | boolean | `false` | Adds an exclusive "None of the above". | Q6, S38 |
| `has_prefer_not_to_answer` | boolean | `false` | Adds "Prefer not to answer". | Q12, S23 |
| `randomize_options` | boolean | `false` | Shuffle options per respondent ("Other"/"None" stay last). | S40 |
| `exclusive_options` | string[] | `[]` | Options that cannot be combined with others (`multi_choice`). | S38 |
| `rows` | string[] | — | Items to rate (`matrix`, `likert` battery). | S05, S30 |
| `columns` | string[] | — | Scale points (`matrix`). | S05, S30, Q8 |
| `scale` | `{min, max, labels}` | — | Numeric scale for `rating`, `nps`, `likert`, `slider` (and bounds for `number`). `labels` is keyed by the value as a string. | S36, S37, Q8 |
| `selection` | `{min, max}` | `null`s | Pick limits for `multi_choice`. | S04, S14 |
| `shown_when` | string \| null | `null` | Display logic: show only when the [condition](#conditions) is true. | Q3b, Q5, S22, S28 |
| `jumps` | `[{when, to}]` | `[]` | Skip logic after this question. | S22, S28, S41 |
| `group` | string \| null | `null` | `ref` (or label) of the `group` this question sits in. | S06, S10, S27, S44 |
| `sensitive` | boolean | `false` | Author's flag: asks about a sensitive topic. A hint for the judge; Q12 decides. | Q12, Q16 |
| `has_image` | boolean | `false` | The question shows an image. | S25, S26 |
| `collects_pii` | boolean | `false` (`true` implied for `email`, `phone`) | Collects personally identifying data. | S21, S48 |
| `role` | `question` \| `information` \| `consent` | `question` | What the entry is for. Same keys as `R_role`. | applicability |
| `intent` | `screener` \| `demographic` \| `behaviour` \| `attitude` \| `outcome` \| `open_feedback` \| `contact_or_admin` | — | The question's job. Same keys as `Q24_intent` (which also has `instruction_only`). | S41, S48, Q24 mix |
| `inferred` | boolean | — | Set by importers on a value they guessed (e.g. a type inferred from "(select one)"). Not in the schema; allowed as an extra key. | skills report it |

## Annotated example

A feedback survey for existing customers. Eight questions: a screener that ends the survey for non-users, an NPS with a gated follow-up for detractors, a matrix, an open question, and demographics last with "Prefer not to say". It passes every static check.

```jsonc
{
  "title": "Help shape Acme Invoicing: 3-minute customer check-in",   // A1/A2: topic + purpose, addressed to the respondent
  "description": "Tell us how invoicing with Acme works for you, so we can fix what slows you down.",
  "kind": "feedback",
  "audience": "Small-business owners who sent an invoice with Acme in the last 3 months",
  "purpose": "Decide which two invoicing problems to fix in the next quarter",   // the decision (A7, C1, Q23)
  "sponsor": "Acme product team",
  "language": "en",
  "welcome": {
    "title": "Help shape Acme Invoicing",
    // E7/S50: short; purpose, time, privacy, consent, deadline, contact each findable
    "description": "We're the Acme product team. Your answers decide what we fix next, and we'll share the results in our May update.\n• Takes about 3 minutes\n• Anonymous: only the product team sees answers\n• Voluntary: you can stop at any time\n• Open until 30 May. Questions? research@acme.example",
    "button": "Start"
  },
  "thank_you": {
    "title": "Thank you, that's everything",
    // E3: says what happens next; F5: contact
    "description": "We read every answer. You'll see what we changed in the May product update. Questions? research@acme.example"
  },
  "settings": { "stated_minutes": 3, "progress_bar": true, "anonymous": true },   // S16: estimate is 3.3 min

  "questions": [
    { "ref": "Q1", "type": "yes_no", "intent": "screener", "required": true,
      "label": "Have you sent an invoice with Acme in the last 3 months?",        // C2 screener; Q19 recall window
      "options": ["Yes", "No"],
      "jumps": [ { "when": "Q1 is 'No'", "to": "end" } ] },                        // S41: the screener has an exit

    { "ref": "Q2", "type": "multi_choice", "intent": "behaviour", "required": true,
      "label": "Which of these have you used in the last 3 months? Select all that apply.",
      "options": ["Recurring invoices", "Payment reminders", "Expense tracking", "Bank sync", "Reports"],
      "has_none": true,                                                            // exclusive "None of the above" (S38)
      "randomize_options": true },                                                 // S40 not needed at 5 options, harmless

    { "ref": "Q3", "type": "nps", "intent": "outcome", "required": true,          // C3 outcome; S37 standard NPS
      "label": "How likely are you to recommend Acme Invoicing to a friend or colleague?",
      "scale": { "min": 0, "max": 10, "labels": { "0": "Not at all likely", "10": "Extremely likely" } } },

    { "ref": "Q4", "type": "long_text", "intent": "open_feedback", "required": false,
      "label": "What is the main reason for your score?",
      "shown_when": "Q3 <= 6" },                                                   // gated follow-up: Q3b and Q5 skipped

    { "ref": "Q5", "type": "matrix", "intent": "attitude", "required": true,     // 5th answerable: no early friction (S51)
      "label": "How satisfied are you with each of these?",
      "rows": ["Creating an invoice", "Getting paid on time", "Help from support"],  // S30: ≤ 8 rows
      "columns": ["Very dissatisfied", "Dissatisfied", "Neither", "Satisfied", "Very satisfied"] },  // ≤ 5 columns, balanced (Q8)

    { "ref": "Q6", "type": "long_text", "intent": "open_feedback", "required": false,
      "label": "What one change would make Acme Invoicing more useful to you?" },   // C4 "why"; optional open text near the end

    { "ref": "Q7", "type": "single_choice", "intent": "demographic", "required": false,
      "label": "How many people work at your business?",
      "description": "So we can compare answers across business sizes.",          // B3: demographics last, with a reason
      "options": ["Just me", "2–9", "10–49", "50 or more"],                        // S12: no gaps or overlaps
      "has_prefer_not_to_answer": true },

    { "ref": "Q8", "type": "dropdown", "intent": "demographic", "required": false,
      "label": "Which industry is your business in?",
      "options": ["Construction", "Creative services", "Consulting", "Health", "Hospitality", "Retail", "Technology", "Trades"],
      "has_other": true, "has_prefer_not_to_answer": true }
  ]
}
```

Time estimate (question-types.md): 10 + 15 + 8 + 60 + 8 × 3 + 60 + 10 + 10 = 197 s ≈ 3.3 min, within `stated_minutes` 3 (S16 allows 2 × 3 + 3 = 9).

## Conditions

`shown_when` and `jumps[].when` are plain-text conditions, readable by people and by the judge.

```
condition := clause { (" and " | " or ") clause }
clause    := REF " is " VALUE                 Q1 is 'Yes'
           | REF " is not " VALUE             Q1 is not 'Yes'
           | REF " contains " VALUE           Q3 contains 'Email'
           | REF " does not contain " VALUE   Q3 does not contain 'Email'
           | REF " " OP " " NUMBER            Q7 >= 7          OP: = != < <= > >=
           | REF " is empty"                  Q2 is empty
           | REF " is not empty"              Q2 is not empty
REF       := "Q" digits [ "." digits ]        a question ref that comes earlier in the survey
VALUE     := '…'                              single-quoted option text, exactly as in `options`; '' inside means one quote
```

- `is` / `is not` compare the single selected option (`single_choice`, `dropdown`, `yes_no`, `consent`).
- `contains` / `does not contain`: for `multi_choice`, whether that option is among the selected ones; for text, a case-insensitive substring.
- Comparisons (`OP`) apply to numeric answers: `number`, `rating`, `nps`, `likert`, `slider`.
- `is empty` / `is not empty`: the question was skipped / answered.
- `and` binds tighter than `or`; there are no parentheses. Keep conditions short; split complex routing into several jumps.
- Scripts only need the refs (every `Q\d+` in the text) to build the logic graph (S22, S28, S41, Q3b/Q5 skips); they do not evaluate conditions.

**`shown_when`**: the question is displayed only when the condition is true. It must refer to earlier questions.

**`jumps`**: evaluated after the question is answered, in order. The first entry whose `when` is true wins; an entry with `when: null` is the default and goes last; with no match and no default, the respondent continues to the next question. `to` is a question ref or `end` (which goes to the thank-you screen). Jumping backwards is allowed but rarely wise. A question that every path jumps past is unreachable (`S28_unreachable_question`).

Typical patterns:

```jsonc
{ "ref": "Q1", "jumps": [ { "when": "Q1 is 'No'", "to": "end" } ] }                 // screener exit
{ "ref": "Q4", "shown_when": "Q3 <= 6" }                                              // detractor follow-up
{ "ref": "Q9", "shown_when": "Q2 contains 'Bank sync'" }                              // ask only users of a feature
{ "ref": "Q3", "jumps": [ { "when": "Q3 is 'Never'", "to": "Q8" }, { "when": null, "to": "Q4" } ] }
```

## Markdown form

The canonical human-readable form. `survey_export.py --format md` writes it; `from_markdown` reads it back (round trip) and also accepts loosely pasted lists. BlockSurvey's AI Import accepts it as-is.

### Template

This is the exact skeleton (from the implementation plan, Task 5):

```
# Title
> description
**Audience:** … · **Kind:** research · **Time:** ~5 min
## Welcome
…
## Questions
### Q1. Label  `single_choice` (required)
Description line
- [ ] Option A
- [ ] Option B
- [ ] Other (please specify)
> Shown when: Q0 is 'Yes'
> Jump: if Q1 is 'No' → end
### Q2. … `matrix`
| | Col1 | Col2 |
| Row1 | | |
## Thank you
…
```

### Rules

**Header.**
- `# {title}`; `> {description}` (omitted when empty).
- `**Audience:** {audience} · **Kind:** {kind} · **Time:** ~{stated_minutes} min` — parts with no value are left out; the separator is ` · `.
- Optional second line: `**Sponsor:** {sponsor} · **Purpose:** {purpose} · **Language:** {language}`.
- Optional settings line, only for values that differ from the defaults: `**Settings:** progress_bar=false · anonymous=true · randomize_questions=true · sign_in_required=true · captcha=true · multiple_submissions=true`.

**Welcome / Thank you.** `## Welcome` (or `## Thank you`), then `**{title}**` on its own line if there is a title, then the description text as-is (it may span several lines), then `[{button}]` on its own line if there is a button. Omit the section when the screen is absent.

**Questions.** `## Questions`, then one block per question:

1. Heading: `### {ref}. {label}  ` + `` `{type}` `` + ` (required)` when required. Two spaces separate the label from the type.
2. Description: the plain lines after the heading that do not start with `- [ ]`, `|` or `>`.
3. Options: one `- [ ] {option}` line each, in order. Then, for the flags, exactly: `- [ ] Other (please specify)` (`has_other`), `- [ ] None of the above` (`has_none`), `- [ ] Prefer not to answer` (`has_prefer_not_to_answer`). An option listed in `exclusive_options` ends with ` *(exclusive)*`. `yes_no` without explicit options writes `- [ ] Yes` and `- [ ] No`.
4. Matrix (and `likert` with rows): a table, header `| | {col1} | {col2} | … |`, then one `| {row} | | … |` line per row (empty cells). Readers must also accept a `| --- |` separator row under the header.
5. Meta lines, each a blockquote, in this order and only when set:
   - `> Scale: {min}–{max}` + ` · {value} = {label}` per label, e.g. `> Scale: 0–10 · 0 = Not at all likely · 10 = Extremely likely`
   - `> Select: min {min} · max {max}` (either part may be omitted)
   - `> Randomize options`
   - `> Group: {group}`
   - `> Intent: {intent}`
   - `> Role: {role}` (only when not `question`)
   - `> Flags: {flag} · {flag}` from `sensitive`, `collects_pii`, `has_image`
   - `> Shown when: {shown_when}`
   - `> Jump: if {when} → {to}` per conditional jump, and `> Jump: otherwise → {to}` for the default (`when: null`)
6. `statement` and `group` blocks have no options; a `group`'s children carry `> Group: {ref}`.

**Lenient import** (`from_markdown` on pasted text that is not in the canonical form):
- `1. Question?` or `Q1. Question?` lines start questions; `- option`, `* option`, `a) option` and `- [ ] option` lines are options.
- Type inference, each marked `inferred: true`: `(select one)` / `(choose one)` → `single_choice`; `(select all that apply)` / `(select multiple)` → `multi_choice`; a label with "recommend" and "0–10" or "0-10" → `nps`; options exactly Yes / No → `yes_no`; no options and the label ends in "why?" or asks to "describe" / "explain" → `long_text`; no options otherwise → `short_text`; options otherwise → `single_choice`.
- Refs are assigned `Q1…Qn` in order when missing.

### Example

The annotated example above, in markdown form:

```
# Help shape Acme Invoicing: 3-minute customer check-in
> Tell us how invoicing with Acme works for you, so we can fix what slows you down.
**Audience:** Small-business owners who sent an invoice with Acme in the last 3 months · **Kind:** feedback · **Time:** ~3 min
**Sponsor:** Acme product team · **Purpose:** Decide which two invoicing problems to fix in the next quarter · **Language:** en
**Settings:** anonymous=true
## Welcome
**Help shape Acme Invoicing**
We're the Acme product team. Your answers decide what we fix next, and we'll share the results in our May update.
• Takes about 3 minutes
• Anonymous: only the product team sees answers
• Voluntary: you can stop at any time
• Open until 30 May. Questions? research@acme.example
[Start]
## Questions
### Q1. Have you sent an invoice with Acme in the last 3 months?  `yes_no` (required)
- [ ] Yes
- [ ] No
> Intent: screener
> Jump: if Q1 is 'No' → end
### Q2. Which of these have you used in the last 3 months? Select all that apply.  `multi_choice` (required)
- [ ] Recurring invoices
- [ ] Payment reminders
- [ ] Expense tracking
- [ ] Bank sync
- [ ] Reports
- [ ] None of the above
> Randomize options
> Intent: behaviour
### Q3. How likely are you to recommend Acme Invoicing to a friend or colleague?  `nps` (required)
> Scale: 0–10 · 0 = Not at all likely · 10 = Extremely likely
> Intent: outcome
### Q4. What is the main reason for your score?  `long_text`
> Intent: open_feedback
> Shown when: Q3 <= 6
### Q5. How satisfied are you with each of these?  `matrix` (required)
| | Very dissatisfied | Dissatisfied | Neither | Satisfied | Very satisfied |
| Creating an invoice | | | | | |
| Getting paid on time | | | | | |
| Help from support | | | | | |
> Intent: attitude
### Q6. What one change would make Acme Invoicing more useful to you?  `long_text`
> Intent: open_feedback
### Q7. How many people work at your business?  `single_choice`
So we can compare answers across business sizes.
- [ ] Just me
- [ ] 2–9
- [ ] 10–49
- [ ] 50 or more
- [ ] Prefer not to answer
> Intent: demographic
### Q8. Which industry is your business in?  `dropdown`
- [ ] Construction
- [ ] Creative services
- [ ] Consulting
- [ ] Health
- [ ] Hospitality
- [ ] Retail
- [ ] Technology
- [ ] Trades
- [ ] Other (please specify)
- [ ] Prefer not to answer
> Intent: demographic
## Thank you
**Thank you, that's everything**
We read every answer. You'll see what we changed in the May product update. Questions? research@acme.example
```

## Other export formats

- **CSV** (`--format csv`): header `ref,type,label,required,options,rows,columns,shown_when,jumps`; list cells joined with `|`; jumps written as `if {when} → {to}` joined with `; `.
- **Plain text** (`--format txt`): numbered questions with indented options, for pasting into BlockSurvey's AI Import or any form builder.
- **JSON** (`--format json`): the portable JSON above.
