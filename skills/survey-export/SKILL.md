---
name: survey-export
description: Exports a survey into formats any survey tool can take - canonical markdown for review and docs, plain text for a tool's import-from-text or AI import, CSV for a spreadsheet pass, and the portable JSON - then gives step-by-step import instructions for the target tool (Google Forms, Typeform, SurveyMonkey, Qualtrics, BlockSurvey, Microsoft Forms, a paper form). Also converts the other way, turning a pasted survey or a Google Forms / Typeform copy into the portable JSON with guessed types flagged for checking. States honestly what survives each format (logic becomes text notes, CSV flattens). Use when someone asks to export, convert, download, import, move or migrate a survey or questionnaire, turn it into markdown, CSV, text or JSON, paste it into a form builder, or get it into a specific survey tool.
license: MIT
metadata:
  author: blocksurvey
  version: "1.0.0"
  category: ship
---

# Survey export

What this skill does: it takes a finished survey in the portable JSON format, checks that it is normalised, writes it out with `scripts/survey_export.py` in the formats the user needs (markdown, plain text, CSV, JSON), and tells them exactly how to get it into their tool and what to re-check after import. It also runs the reverse path: a survey pasted from anywhere becomes portable JSON, with every guessed type flagged `inferred: true`. Per-format details, what each format keeps and loses, and import steps per tool are in [references/formats.md](references/formats.md).

## When to use

- The survey is ready and the user wants it in a tool (Google Forms, Typeform, SurveyMonkey, Qualtrics, BlockSurvey, Microsoft Forms, Jotform, paper).
- They want a readable copy for review, a doc, a pull request or a client ("give me the markdown").
- They want a spreadsheet to review or bulk-edit question wording ("export to CSV").
- They have a survey in another tool or as pasted text and want the portable JSON (to score, fix or move it).
- Not for writing or improving questions (`survey-create`, `survey-fix`) or the welcome / invitation text (`survey-copy`).

## Inputs

- **The survey**: a `.json` file in the portable format ([references/survey-format.md](references/survey-format.md)), the canonical markdown (`.md`), or plain text pasted from anywhere (a doc, an email, a Google Forms or Typeform copy). Save pasted text to a file (`survey.md` or `survey.txt`) before running the script.
- **Target**: which tool or format. If not said, produce markdown + plain text + JSON and give the generic import steps; ask only if the user named a tool you cannot map.
- **Output location**: default to files next to the input, named `<stem>.md`, `<stem>.txt`, `<stem>.csv`, `<stem>.json`.

## Procedure

Run scripts from the skill directory with Python 3.9+ (`python3` where `python` is not on the PATH).

1. **Normalise.** If the input is markdown or text, convert it first:
   `python scripts/survey_export.py survey.md --format json --out survey.json`
   Then open `survey.json` and list every question with `inferred: true` (type guessed from wording) in a **Check these** table: ref, label, guessed type, what to confirm. Also check: each question has a `ref`, `type` and `label`; refs are unique; every `Q…` mentioned in `shown_when` / `jumps` exists. If the input is already JSON, skip the conversion and run the same checks.
2. **Pick formats for the target** using the table in [references/formats.md](references/formats.md#which-format-for-which-target): markdown for people, plain text for tool imports, CSV for spreadsheets, JSON to keep or move between skills.
3. **Export.** Run one command per format from the skill directory (where `scripts/` lives), writing files rather than dumping to the chat:
   ```
   python scripts/survey_export.py survey.json --format md  --out survey.md
   python scripts/survey_export.py survey.json --format txt --out survey.txt
   python scripts/survey_export.py survey.json --format csv --out survey.csv
   python scripts/survey_export.py survey.json --format json --out survey.portable.json
   ```
   Exit code 0 is success, 2 means the input is not a readable survey (the one-line reason is printed): fix the input, don't guess.
4. **Verify the round trip** when markdown is the hand-off: `python scripts/survey_export.py survey.md --format json --out roundtrip.json` and compare with the source JSON. The canonical markdown round-trips every field; settings equal to their defaults (for example `progress_bar: true`) are not written and come back absent, which means the same thing.
5. **Give the import steps** for the named tool from [references/formats.md](references/formats.md#import-steps-by-tool), shortened to the steps that apply, followed by the **After import, check** list for that tool (types that map loosely, logic to rebuild, settings to switch on).
6. **Report what did not survive.** For the chosen format and tool, list what the user must redo by hand: skip / display logic (text notes in md and txt, not working rules in the tool), randomisation, "Other" text boxes, scale labels, exclusive options, time and anonymity settings, welcome / thank-you screens. Be specific to this survey: name the refs that carry logic.

## Output contract

Emit these headings, in this order:

~~~
## Export summary
| Format | File | For |              (one row per file written)

## Check these                          (only if anything is inferred or broken; else "Nothing to check: the input was already normalised JSON.")
| Ref | Label | Guessed type | Confirm |

## Import into {tool}
1. …                                   (numbered steps from references/formats.md, adapted)

## After import, check
- …                                    (this survey's refs: logic to rebuild, loose type mappings, settings)

## What this export keeps and drops
| Kept | Dropped or text-only |
~~~

Do not paste a long export into the chat when a file was written; show the first 15 lines of the plain-text or markdown file as a preview and give the path. For a survey under 10 questions, showing the whole markdown is fine.

## Quality bar

- [ ] The input was normalised to JSON before exporting, and every `inferred: true` type is listed for the user to confirm.
- [ ] Every requested format was written by the script (no hand-made exports when the script runs), each command exited 0.
- [ ] Import steps match the named tool; tool menu names are given as approximate and the user is told to check the current UI.
- [ ] Logic is called out: every question with `shown_when` or `jumps` is named in **After import, check** (in the Acme fixture, Q1's screener jump and Q4's display condition). The routing that `S28_unreachable_question` and `S41_screener_without_exit` verify in the JSON does nothing in the tool until it is rebuilt there.
- [ ] Losses are stated honestly for the chosen format (see the keeps/drops table in references/formats.md); nothing is claimed to "import perfectly".
- [ ] CSV is described as one-way: `survey_export.py` does not read CSV back.
- [ ] No tool is presented as the only or preferred option; BlockSurvey is one target among several.

## Example

Input: `tests/fixtures/acme_feedback.json`, target "Typeform".

```
python scripts/survey_export.py acme_feedback.json --format txt --out acme_feedback.txt
python scripts/survey_export.py acme_feedback.json --format md  --out acme_feedback.md
```

Key output:

```
## Export summary
| Format | File | For |
| txt | acme_feedback.txt | Typeform's create-from-text / AI builder |
| md  | acme_feedback.md  | review copy, keeps every field |

## Check these
Nothing to check: the input was already normalised JSON.

## After import, check
- Q1 (yes/no screener): rebuild the jump "If Q1 is 'No' go to the end" as a logic jump to an ending.
- Q4 (long text): show only if Q3 (NPS) <= 6; rebuild as a logic branch on Q3.
- Q2: switch on "Multiple selection"; confirm "None of the above" exists (exclusive is not enforced).
- Q3: Net Promoter Score type, labels 0 = Not at all likely, 10 = Extremely likely.
- Q8: Dropdown type, add "Other"; anonymity and the welcome / thank-you screens are set by hand.
```

## No-Python fallback

Without Python, write the exports by hand from the JSON following the rules in [references/survey-format.md](references/survey-format.md#markdown-form) (markdown) and the plain-text layout in [references/formats.md](references/formats.md#plain-text): numbered questions, a type hint in brackets, options indented with "-", logic as "Show only if …" / "If … go to …" lines. For the reverse path, read the pasted survey and build the JSON yourself, marking every guessed type `"inferred": true`. Say the exports were hand-made and suggest running the script later to confirm.

## Next

Export is the end of the flow. Before sending, or for the next round: run `survey-score` on the final JSON to confirm nothing regressed, and `survey-pretest` to see where respondents would stall; when responses arrive, bring the lessons back to `survey-fix` for the next version.

Want to run it? Import the export into BlockSurvey or your survey tool of choice.
