# Logic patterns

Routing patterns written in the portable survey's plain-text condition grammar, with JSON snippets you can paste into a survey. Every pattern below passes `scripts/survey_lint.py` with no `S28_unreachable_question` or `S41_screener_without_exit`. The grammar is copied from [survey-format.md](survey-format.md#conditions); the checks it must pass are in [static-checks.md](static-checks.md).

## Grammar reference

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

### What the checks need

| Check | What makes it pass |
| --- | --- |
| `S41_screener_without_exit` (lint) | The screener has `intent: "screener"` **and** either its own `jumps` or a later question whose `shown_when` names its ref. Without `intent: "screener"` lint cannot tell it is a screener (the judge may still flag C2). |
| `S28_unreachable_question` (lint) | Something leads to every top-level question: the question before it does not always jump away (`when: null` to somewhere else), or some question jumps to it. |
| `S22_conditional_without_logic` (hybrid; needs judgments, so lint alone will not show it) | Every question that only applies after a specific earlier answer has a `shown_when`, or a conditional jump leads to it, or the question before it conditionally jumps elsewhere. Check by hand. |

### Choosing between `shown_when` and `jumps`

- **`shown_when`** for one or a few questions that some people skip: the rule sits on the question it governs, survives reordering, and reads as "who sees this".
- **`jumps`** for exits (`to: "end"`) and for skipping a whole block in one place. Every block-skip needs the other branch to rejoin; check for dead runs.
- **Never both on the same path** for the same intent: it doubles the places a future edit can break.

---

## L1 Screener → end

Non-qualifiers finish at once. Required, first, `intent: "screener"`.

```jsonc
{ "ref": "Q1", "type": "yes_no", "intent": "screener", "required": true,
  "label": "Have you sent an invoice with Acme in the last 3 months?", "options": ["Yes", "No"],
  "jumps": [ { "when": "Q1 is 'No'", "to": "end" } ] }
```

Plain English: "If Q1 is No, the survey ends." Write the thank-you so it reads well for both groups ("Thanks for your time. …").

## L2 Screener → kind exit statement

A `statement` at the very end, reached only by the screener's jump; the last real question jumps to `end` so qualifiers never see it.

```jsonc
{ "ref": "Q1", "type": "yes_no", "intent": "screener", "required": true,
  "label": "Do you currently use Acme?", "options": ["Yes", "No"],
  "jumps": [ { "when": "Q1 is 'No'", "to": "Q9" } ] },
// … Q2–Q7 …
{ "ref": "Q8", "type": "long_text", "label": "Anything else you'd like to tell us?",
  "jumps": [ { "when": null, "to": "end" } ] },
{ "ref": "Q9", "type": "statement",
  "label": "Thanks! This survey is for current Acme users, so that's all we need from you." }
```

Reachable: Q9 is reached from Q1's jump, so no S28 even though Q8 always jumps past it.

## L3 Skip what doesn't apply (gated follow-up)

The default fix for a presuming question (Q3b, Q10, S22). Three common gates:

```jsonc
// yes/no gate
{ "ref": "Q4", "type": "yes_no", "label": "Do you use the Acme mobile app?", "options": ["Yes", "No"] },
{ "ref": "Q5", "type": "rating", "label": "How satisfied are you with the mobile app?",
  "scale": { "min": 1, "max": 5 }, "shown_when": "Q4 is 'Yes'" }

// feature picked in a multi-select
{ "ref": "Q9", "type": "rating", "label": "How satisfied are you with bank sync?",
  "scale": { "min": 1, "max": 5 }, "shown_when": "Q2 contains 'Bank sync'" }

// detractor / low-score follow-up
{ "ref": "Q4", "type": "long_text", "label": "What is the main reason for your score?",
  "shown_when": "Q3 <= 6" }
```

When the gate question is new, insert it with a sub-ref of the question before (`Q3.1`) so existing refs do not move.

## L4 Segment branches

Different groups answer different blocks, then rejoin. Two equivalent ways.

**With `shown_when` on each question** (preferred; robust to reordering):

```jsonc
{ "ref": "Q2", "type": "single_choice", "label": "Which best describes you?",
  "options": ["Business owner", "Accountant or bookkeeper"] },
{ "ref": "Q3", "type": "rating", "label": "How easy is it to get paid on time?",
  "scale": { "min": 1, "max": 5 }, "shown_when": "Q2 is 'Business owner'" },
{ "ref": "Q4", "type": "rating", "label": "How easy is it to manage several clients' invoices?",
  "scale": { "min": 1, "max": 5 }, "shown_when": "Q2 is 'Accountant or bookkeeper'" },
{ "ref": "Q5", "type": "long_text", "label": "What one change would help you most?" }   // everyone
```

**With `jumps`** (one place controls the whole block):

```jsonc
{ "ref": "Q2", "jumps": [ { "when": "Q2 is 'Accountant or bookkeeper'", "to": "Q6" } ] },
// Q3–Q5: owners' block; the last one skips the accountants' block
{ "ref": "Q5", "jumps": [ { "when": null, "to": "Q8" } ] },
// Q6–Q7: accountants' block, falls through into Q8
{ "ref": "Q8", "type": "long_text", "label": "What one change would help you most?" }
```

Reachable: Q6 is reached from Q2's jump; Q8 from Q5's default and Q7's fall-through. Forget Q2's jump and Q6–Q7 become a dead run (S28).

## L5 Skip a section for people with nothing to say

```jsonc
{ "ref": "Q6", "type": "single_choice", "label": "In the last 3 months, how often did you contact support?",
  "options": ["Never", "Once", "2–3 times", "4 or more times"],
  "jumps": [ { "when": "Q6 is 'Never'", "to": "Q10" } ] }
// Q7–Q9: support questions, seen only by people who contacted support; Q10 continues for everyone
```

## L6 Combined conditions

`and` binds tighter than `or`; no parentheses. Split anything harder into separate jumps (first match wins).

```jsonc
{ "ref": "Q12", "type": "long_text", "label": "What would make you more likely to recommend us?",
  "shown_when": "Q3 <= 6 and Q2 contains 'Bank sync'" }

// "(A or B) and C" cannot be written directly: use two jumps instead
{ "ref": "Q5", "jumps": [
  { "when": "Q2 is 'Owner' and Q4 >= 4", "to": "Q8" },
  { "when": "Q2 is 'Manager' and Q4 >= 4", "to": "Q8" } ] }
```

## L7 Loop / repeat for each item (not in the schema)

The portable format has no loop. Describe it, then unroll it for the items that matter:

- **Describe** in the logic table: "For each tool chosen in Q2, ask Q3 (satisfaction)". Many tools call this "loop", "repeat" or "piped follow-up".
- **Unroll** with sub-refs and one gate per item, up to about 5 items (beyond that, use a matrix):

```jsonc
{ "ref": "Q2", "type": "multi_choice", "label": "Which of these do you use? Select all that apply.",
  "options": ["Recurring invoices", "Payment reminders", "Bank sync"], "has_none": true },
{ "ref": "Q2.1", "type": "rating", "label": "How satisfied are you with recurring invoices?",
  "scale": { "min": 1, "max": 5 }, "shown_when": "Q2 contains 'Recurring invoices'" },
{ "ref": "Q2.2", "type": "rating", "label": "How satisfied are you with payment reminders?",
  "scale": { "min": 1, "max": 5 }, "shown_when": "Q2 contains 'Payment reminders'" },
{ "ref": "Q2.3", "type": "rating", "label": "How satisfied are you with bank sync?",
  "scale": { "min": 1, "max": 5 }, "shown_when": "Q2 contains 'Bank sync'" }
```

Alternative: one `matrix` with every item as a row and a "Don't use" column. Note: 8+ unrolled ratings in a row trip S27 (monotony); a gated question breaks the run in the lint count, but respondents still feel it.

## L8 Quotas (not in the schema)

Quotas ("stop after 200 accountants") are a setting of the survey tool or panel provider, not survey logic. Write them as instructions in the logic table and in the hand-off note:

| Quota | Based on | Limit | When full |
| --- | --- | --- | --- |
| Accountants | Q2 is 'Accountant or bookkeeper' | 200 complete responses | End with the screener's exit message |

If the tool has no quotas, the fallback is to close the link, or to screen them out manually after collection (say this costs their time).

## L9 Piping (tool-dependent)

Inserting an earlier answer into later text. The portable format has no piping field; use the `{{Q1}}` convention in the label and say it is tool-dependent: Typeform calls it "Recall information", Qualtrics "piped text", SurveyMonkey "piping", Google Forms has none (keep a generic label there).

```jsonc
{ "ref": "Q4", "type": "long_text", "label": "What do you like most about {{Q2}}?",
  "description": "Piping: replace {{Q2}} with your tool's piped-text token, or use 'the tool you chose'." }
```

Always write a label that still reads correctly if piping fails ("…about the tool you use most?").

## L10 Thank-you variants

The format has one `thank_you`. For per-branch endings, end each branch on its own `statement` and jump to `end` after it:

```jsonc
{ "ref": "Q8", "type": "statement", "label": "Thanks! As a customer, you'll see the changes in our May update.",
  "shown_when": "Q1 is 'Yes'" },
{ "ref": "Q9", "type": "statement", "label": "Thanks! We'll use this to make Acme easier to try.",
  "shown_when": "Q1 is 'No'" }
```

Keep the shared `thank_you` neutral ("Thank you, that's everything."). If the tool supports multiple endings natively, note the mapping in the hand-off.

## Anti-patterns

| Don't | Why | Instead |
| --- | --- | --- |
| `shown_when` naming a later question | The answer does not exist yet | Gate only on earlier refs; move the gate question up |
| Default jump (`when: null`) to a far question with nothing jumping into the skipped block | Dead run, S28 | Make the jump conditional, or point a jump at the block |
| Screener without `intent: "screener"` | Lint cannot check S41 | Set the intent on every screener |
| Screener that only routes "Yes" forwards (no exit) | Non-qualifiers answer everything, S41 | Jump non-qualifiers to `end` or an exit statement |
| Option text in a condition that differs from `options` (`'yes'` vs `'Yes'`, curly quotes) | Many tools match exactly; the rule never fires | Copy the option text exactly |
| Backwards jumps for "loops" | Easy to trap respondents | Unroll (L7) |
| Refs like `Q3a` or `Q3_a` | The grammar does not recognise them | `Q3.1` |
