# Export formats and import paths

What `scripts/survey_export.py` writes, what each format keeps and drops (measured on `tests/fixtures/acme_feedback.json` and a test survey with groups, statements, exclusive options and selection limits), and how to get each into the common survey tools.

```
python scripts/survey_export.py survey.json --format md|txt|csv|json [--out file]
python scripts/survey_export.py survey.md  --format json [--out file]     # also .txt or pasted text
```

Exit codes: 0 ok, 2 the input is not a readable survey (missing file, not JSON and not parseable text). Default format: `md` for a `.json` input, `json` otherwise.

Tool menu names below are from general knowledge and change often. Treat them as approximate and check the tool's current help page; the formats themselves are stable.

## Which format for which target

| Target | Format | Why |
| --- | --- | --- |
| Human review, docs, pull requests, a client | **Markdown** (`md`) | Readable, diffable, keeps every portable field, and round-trips back to JSON. |
| Any tool's "import from text", "create with AI", "quick import", or a paste into a builder | **Plain text** (`txt`) | Clean numbered questionnaire with type hints; what text importers and AI builders read best. Markdown also works in most AI importers. |
| Spreadsheet review, bulk-editing labels and options, a translation pass | **CSV** (`csv`) | One row per question. One-way: the script does not read CSV back. |
| Moving between skills, version control, your own tooling | **JSON** (`json`) | The canonical interchange; keeps everything, including unknown extra keys. |
| Paper or PDF | **Markdown** → your doc tool (or `pandoc survey.md -o survey.docx`) | Checkboxes and tables render as a printable form. |

## What survives each format

| Element | md | txt | csv | json |
| --- | --- | --- | --- | --- |
| Title, description | yes | yes | no | yes |
| Audience, kind, purpose, sponsor, language | yes (header lines) | no | no | yes |
| Settings (time, anonymous, progress bar…) | yes (non-default values only; defaults come back absent, same meaning) | no | no | yes |
| Welcome / thank-you title and text | yes, with button | yes, without button | no | yes |
| Question refs | yes | renumbered 1…n over answerable questions; statements and sections unnumbered | yes | yes |
| Type | exact | as a hint, e.g. "(select one)"; re-import guesses the type | exact | exact |
| Required | yes | "(required)" | yes | yes |
| Question description | yes | yes | no | yes |
| Options | yes | yes | yes (`\|`-joined) | yes |
| Other / None / Prefer not to answer | yes (as flags) | yes, as plain options | **no** (dropped) | yes |
| Exclusive options | yes | no | no | yes |
| Matrix rows / columns | yes (table) | yes (Rows: / Columns: lists) | yes | yes |
| Scale min–max and labels | yes | yes ("(0–10)", "Scale: 0 = …") | no | yes |
| Selection limits | yes | as a sentence ("Choose at most 2.") | no | yes |
| Randomise options | yes | no | no | yes |
| Groups / sections | yes | "Section: …" heading only; children not marked | no | yes |
| Intent, role, sensitive / PII / image flags | yes | no | no | yes |
| Display logic (`shown_when`) | yes, exact | as an English line ("Show only if Q3 <= 6") | yes (text) | yes |
| Skip logic (`jumps`) | yes, exact | as English lines ("If Q1 is 'No' go to the end") | yes (text) | yes |
| Unknown extra keys, `inferred` flags | **no** | no | no | yes |

**Logic is never live in md, txt or csv.** It travels as text that a person (or an AI importer) must rebuild as real branching in the target tool. After every import, re-create each `shown_when` and `jumps` and test the paths; an unrebuilt screener lets everyone through and an unrebuilt follow-up shows to everyone.

## Markdown

The canonical form (full rules in `survey-format.md`, "Markdown form"). Abridged, from the Acme fixture:

```
# Help shape Acme Invoicing: 3-minute customer check-in
> Tell us how invoicing with Acme works for you, so we can fix what slows you down.
**Audience:** Small-business owners who sent an invoice with Acme in the last 3 months · **Kind:** feedback · **Time:** ~3 min
**Sponsor:** Acme product team · **Purpose:** Decide which two invoicing problems to fix in the next quarter · **Language:** en
**Settings:** anonymous=true
## Welcome
**Help shape Acme Invoicing**
…
[Start]
## Questions
### Q1. Have you sent an invoice with Acme in the last 3 months?  `yes_no` (required)
- [ ] Yes
- [ ] No
> Intent: screener
> Jump: if Q1 is 'No' → end
### Q5. How satisfied are you with each of these?  `matrix` (required)
| | Very dissatisfied | Dissatisfied | Neither | Satisfied | Very satisfied |
| Creating an invoice | | | | | |
…
## Thank you
…
```

Round trip: `survey.json → md → json` gives back the same survey except (a) settings equal to their defaults are omitted, (b) `required: false` is written explicitly, (c) unknown extra keys and `inferred` flags are dropped. Use JSON, not markdown, as the source of truth if you rely on custom keys.

## Plain text

A numbered questionnaire for paste-in imports. From the Acme fixture:

```
Help shape Acme Invoicing: 3-minute customer check-in

Tell us how invoicing with Acme works for you, so we can fix what slows you down.

Welcome: Help shape Acme Invoicing
We're the Acme product team. Your answers decide what we fix next, …
• Takes about 3 minutes
…

1. Have you sent an invoice with Acme in the last 3 months? (yes/no) (required)
   If Q1 is 'No' go to the end

2. Which of these have you used in the last 3 months? Select all that apply. (select all that apply) (required)
   - Recurring invoices
   …
   - None of the above

3. How likely are you to recommend Acme Invoicing to a friend or colleague? (0–10) (required)
   Scale: 0 = Not at all likely · 10 = Extremely likely

4. What is the main reason for your score? (long answer)
   Show only if Q3 <= 6

5. How satisfied are you with each of these? (rate each row) (required)
   Rows:
   - Creating an invoice
   …
   Columns:
   - Very dissatisfied
   …

Thank you: Thank you, that's everything
We read every answer. …
```

Type hints: `(select one)`, `(select all that apply)`, `(yes/no)`, `(0–10)`, `(1–5)` or the scale range, `(rate each row)`, `(rank the items)`, `(short answer)`, `(long answer)`, `(number)`, `(date)`, `(email)`, `(phone)`, `(file upload)`, `(check to agree)`. Logic refs are renumbered to match the printed numbers. A text importer that keeps the hints in the question text needs them deleted after import (or delete them before pasting).

## CSV

Header and one row per question, list cells joined with `|`, jumps as `if {when} → {to}` joined with `; `:

```
ref,type,label,required,options,rows,columns,shown_when,jumps
Q1,yes_no,Have you sent an invoice with Acme in the last 3 months?,true,Yes|No,,,,if Q1 is 'No' → end
Q3,nps,How likely are you to recommend Acme Invoicing to a friend or colleague?,true,,,,,
Q5,matrix,How satisfied are you with each of these?,true,,Creating an invoice|Getting paid on time|Help from support,Very dissatisfied|Dissatisfied|Neither|Satisfied|Very satisfied,,
Q7,single_choice,How many people work at your business?,false,Just me|2–9|10–49|50 or more,,,,
```

Note Q7: the JSON has `has_prefer_not_to_answer: true`, but "Prefer not to answer" is not in the CSV; "Other" and "None of the above" are dropped the same way. Scale labels, descriptions, welcome and thank-you are not in the CSV either.

**CSV is one-way.** `survey_export.py` reads JSON and markdown/text only; given a CSV it does not fail, it produces a survey with the header as its title and no questions. To bring spreadsheet edits back: apply the changed labels and options to the JSON (an agent can do this row by row by `ref`), then re-export. Keep the `ref` column unchanged while editing.

## JSON

The portable survey format (`survey-format.md`, `schemas/survey.schema.json`). `--format json` on a JSON input re-emits it pretty-printed with every key, including unknown ones; on markdown or text input it is the normaliser. Typeform, Google Forms and the others do not import this JSON directly; use it as the source you export from, and as the input to every other skill.

## Import steps by tool

Each tool row is one option among equals. Pick by where the survey will run.

### Google Forms

No built-in import from text. Options:
1. **Manual (reliable).** forms.google.com → Blank form → title and description from the export. For each question: add question → choose the type from the table below → paste the label → paste the options (pasting several lines into one option field creates one option per line).
2. **AI builder**, where your Google Workspace account has it ("Help me create a form"): paste the plain-text export as the prompt; review every question afterwards.
3. **Add-ons** from the Google Workspace Marketplace that build a form from a Doc or text: paste the plain-text export into a Doc first.

After import, check: logic only exists as "Go to section based on answer", so split the form into sections at each `shown_when` / jump target; `ranking` has no native type (use a multiple-choice grid, one choice per column); `nps` is a linear scale 0–10 with endpoint labels; "None of the above" cannot be made exclusive on Checkboxes; switch off "Collect email addresses" if the survey promises anonymity.

### Typeform

1. typeform.com → Create a new form → the AI / "create from text" option where offered; paste the plain-text export.
2. Or create from scratch and add each question with the matching type (table below).

After import, check: rebuild jumps and display logic under Logic (branching); `multi_choice` needs "Multiple selection" on; `nps` uses the Net Promoter Score® type; set the Welcome and Ending screens from the copy; hide the question numbers if the export's hints came through in the text.

### SurveyMonkey

1. Create survey → the "build with AI" or "import questions / paste your survey" option where offered; paste the plain-text export.
2. Or build manually question by question.

After import, check: skip logic (question and page logic) must be rebuilt; matrix and NPS types map to Matrix / Rating Scale and the NPS question; "Other (please specify)" is a setting on the question, not an option.

### Qualtrics

1. Survey → Tools → Import/Export → **Import Survey**, and choose a `.txt` file in Qualtrics' Simple or Advanced TXT format.
2. The Simple format is close to the plain-text export: question text on one line, choices on the following lines, a blank line between questions. Before importing, delete the type hints, the "(required)" text, the leading indentation and the logic lines from `survey.txt`; keep them in a side note.

After import, check: rebuild display logic and skip logic per question; set Force response for required questions; matrix, NPS and slider types need re-selecting.

### Microsoft Forms

1. Paste the plain-text export into a Word document.
2. forms.office.com → **Quick import** (imports from Word or PDF), then review each question.

After import, check: branching ("Add branching") replaces jumps and display logic; ranking and Net Promoter Score® are native types; required toggles.

### BlockSurvey

1. blocksurvey.io → New survey → **AI import**.
2. Paste the plain-text export (or the markdown; both are accepted) and review the generated survey.

After import, check: logic rules, the welcome and thank-you screens, and the anonymity setting against the source JSON.

### Paper, PDF or a document

1. Open `survey.md` in any markdown editor or convert it (`pandoc survey.md -o survey.docx`).
2. Replace logic lines with routing instructions ("If No, go to question 8").

### Portable type → tool type

Approximate names; see `question-types.md` (Other platforms) for the full table.

| Portable | Typeform | Google Forms | SurveyMonkey | Qualtrics | Microsoft Forms |
| --- | --- | --- | --- | --- | --- |
| `single_choice` | Multiple Choice | Multiple choice | Multiple Choice | Multiple choice (single answer) | Choice |
| `multi_choice` | Multiple Choice + Multiple selection | Checkboxes | Checkboxes | Multiple choice (multiple answer) | Choice + Multiple answers |
| `dropdown` | Dropdown | Dropdown | Dropdown | Multiple choice (dropdown list) | Choice (drop-down) |
| `yes_no` | Yes/No | Multiple choice | Multiple Choice | Multiple choice | Choice |
| `short_text` / `long_text` | Short Text / Long Text | Short answer / Paragraph | Single / Comment Box | Text entry (single / multi line) | Text (short / long answer) |
| `rating` / `likert` | Rating / Opinion Scale | Rating / Linear scale | Star Rating / Rating Scale | Slider / Matrix (Likert) | Rating / Likert |
| `nps` | Net Promoter Score® | Linear scale 0–10 | NPS | Net Promoter Score | Net Promoter Score® |
| `matrix` | Matrix | Multiple choice grid | Matrix / Rating Scale | Matrix table | Likert |
| `ranking` | Ranking | (grid workaround) | Ranking | Rank order | Ranking |
| `date` / `email` / `file` | Date / Email / File Upload | Date / Short answer + validation / File upload | Date / Time, Contact Info, File Upload | Text entry + validation, File upload | Date, Text, Upload file |

## Reverse path: from another tool to JSON

Most tools have no clean export of the questionnaire itself, but all of them let you copy it as text.

1. **Get the text.**
   - Google Forms: open the preview (eye icon), select all, copy; or print the form to PDF and copy from it.
   - Typeform: copy the questions from the builder's outline, or from the shared preview.
   - SurveyMonkey: print or download the survey as PDF and copy the text.
   - Qualtrics: Tools → Import/Export → Export Survey to Word, then copy.
   - Microsoft Forms, BlockSurvey and others: copy from the preview, or from any print / PDF view.
2. **Tidy lightly** (optional): one question per numbered line, options on the lines below starting with `-`, `*`, `a)` or `- [ ]`. Add "(select one)" or "(select all that apply)" where the tool's layout made it obvious but the text does not.
3. **Normalise:** save as `survey.txt` and run `python scripts/survey_export.py survey.txt --format json --out survey.json`.

What the loose parser does (from `survey-format.md`, "Lenient import"): `1. Question?` or `Q1. Question?` starts a question; option lines become `options`; refs become `Q1…Qn`; every type is guessed and marked `"inferred": true`: "(select one)" → `single_choice`, "(select all that apply)" → `multi_choice`, "recommend" + "0–10" → `nps`, Yes/No options → `yes_no`, no options → `short_text` (or `long_text` for "why?", "describe", "explain"), other options → `single_choice`. "Other (please specify)", "None of the above" and "Prefer not to answer" become the matching flags. Lines in the plain-text export's own style ("Show only if …", "If … go to …", "Welcome:", "Thank you:", "(required)") are read back too.

Expect to fix by hand after a reverse import:
- Every `inferred: true` type: `dropdown` comes back as `single_choice`, `likert` as `rating`, a "Why did you…?" question may come back as `short_text`.
- Scale labels come back in the question `description`, not in `scale.labels`.
- Statements and sections are dropped; selection limits become description text; exclusive options, intent, randomisation and PII flags are gone.
- Logic copied from a tool's UI is usually not in the text at all. Rebuild it with `survey-logic`.
- Settings (time, anonymity) and the welcome's button are not recovered; set them, or run `survey-copy`.

Then run `survey-score` (or `survey-lint` for a fast check) on the normalised JSON before you change anything else.
