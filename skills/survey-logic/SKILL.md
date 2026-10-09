---
name: survey-logic
description: Designs and checks survey routing - skip logic, display logic, branching and screeners - in a plain-text condition language any tool can follow. Turns "who should see what" into shown_when gates and jumps, gives every screener an exit, gates every follow-up that only applies to some people, finds unreachable questions, and returns a plain-English logic table plus the patched survey. Use it when someone says "add skip logic", "add branching", "only show this if", "screen out non-customers", "route people by role", "conditional questions", "display logic", "why can nobody reach Q7", or needs loops, quotas, piping or different endings described for Google Forms, Typeform, SurveyMonkey, Qualtrics, a paper form or any other tool.
license: MIT
metadata:
  author: blocksurvey
  version: "1.0.0"
  category: improve
---

# Survey logic

This skill designs the routing of a survey. It starts from the routing intent (who should see what, who should leave early), writes it as `shown_when` gates and `jumps` in the portable survey's plain-text condition grammar, makes sure every screener has an exit, every conditional question has a gate and no question is left unreachable, then runs the static checks to prove it. It hands back the logic in plain English, so the author can rebuild it in any tool, and the patched survey JSON. Loops, quotas, piping and per-branch endings, which the portable format does not model, are described as clear instructions instead.

## When to use

- A survey has a specific audience and needs a screener with an exit (C2_has_screener, S41_screener_without_exit).
- Some questions only apply after a certain answer ("If yes…", "How often do you use the app?") and everyone currently sees them (Q3b_presuming, Q10_depends_on_prior, S22_conditional_without_logic).
- Different groups (roles, customers vs non-customers, promoters vs detractors) should answer different blocks.
- Lint reports S28_unreachable_question or S41, or a long survey has no branching (S47_no_logic_long_survey).
- The user asks how to do a loop, quota, piping or a different ending in their tool.

## Inputs

1. **Survey**: portable survey JSON (see [survey-format.md](references/survey-format.md)). Convert markdown or a pasted list with `python scripts/survey_export.py survey.md --format json --out survey.json`; from another tool, number questions `Q1…Qn`, infer types, mark guesses `inferred: true`, and transcribe any existing logic into the grammar.
2. **Routing intent**, in the user's words: who the survey is for, who should be screened out, which groups see which sections, which questions are follow-ups. If they give none, propose one from the audience, the screener-like questions and any presuming wording, and ask for a yes before writing it.
3. **Target tool** (optional): some tools cannot do display logic on single questions, or cannot skip to the end; adapt the plain-English table accordingly.

## Procedure

1. **Lint the current survey.** Run `python scripts/survey_lint.py survey.json --json` (exit code 1 only means findings exist). Note existing S28, S41, S47 findings and any existing `shown_when` / `jumps`.
2. **Elicit the routing intent as a table.** One row per audience segment or condition: who · what they should see · what they skip · where they end. Include "everyone" as a row. Find the candidates yourself: screener-like questions, questions that presume ("your car", "the app", "If so"), follow-ups that only make sense after a score or a choice. Confirm the table with the user before writing logic when you had to infer it.
3. **Pick patterns.** For each row choose a pattern from [logic-patterns.md](references/logic-patterns.md): L1/L2 screener exits, L3 gated follow-ups, L4 segment branches, L5 section skips, L6 combined conditions, L7 loops (unrolled), L8 quotas (instructions), L9 piping (`{{Q1}}`, tool-dependent), L10 per-branch endings. Prefer `shown_when` for individual questions and `jumps` for exits and whole-block skips.
4. **Write the logic.** Edit the survey JSON:
   - Conditions use the grammar exactly: `Q1 is 'No'`, `Q2 contains 'Bank sync'`, `Q3 <= 6`. Copy option text verbatim, single-quoted.
   - Every `shown_when` and every jump condition names only earlier refs.
   - Every screener gets `intent: "screener"`, `required: true`, and a jump for non-qualifiers to `end` or to an exit statement.
   - A new gate question gets a sub-ref of the question before it (`Q3.1`) so existing refs and conditions do not move. Never `Q3a`.
   - Drop "If yes," from labels that are now gated.
5. **Check structure.** Walk every row of the intent table through the survey and confirm the path. Then check by hand what lint cannot: every question that presumes an earlier answer now has a `shown_when`, or a conditional jump leading to it, or follows a question that conditionally jumps elsewhere (otherwise S22 fires once the survey is judged). Check no `when: null` jump leaves a block with nothing leading into it.
6. **Run lint.** `python scripts/survey_lint.py survey.logic.json --json`. Confirm there are no `S28_unreachable_question` or `S41_screener_without_exit` findings. Fix any that appear and re-run. Report other findings without fixing them (that is survey-fix's job) unless your logic caused them.
7. **Write the plain-English logic** and the hand-off notes for anything outside the schema (loops, quotas, piping tokens, native multiple endings in the user's tool).
8. **Export if asked.** `python scripts/survey_export.py survey.logic.json --format md`: the markdown shows every rule as `> Shown when:` and `> Jump:` lines, ready to rebuild in another tool.

## Output contract

Emit exactly these sections, in this order:

```
## Routing intent
| Who | Sees | Skips | Ends at |

## Logic table
| Ref | Rule (grammar) | In plain English |
| Q1 | jump: Q1 is 'No' → end | People who haven't invoiced in 3 months finish here. |
| Q5 | shown_when: Q4 is 'Yes' | Only app users are asked about the app. |

## Paths
- <segment>: Q1 → Q2 → Q4 → … → end  (<k> questions, ~<m> min)

## Patched survey
<one fenced json block: the complete survey with the logic added, every field kept>

## Lint
Before: <ids or "none">. After: <ids or "none">. S28: none. S41: none. S22 (manual check): every conditional question is gated.

## Hand-off notes
<only when needed: loops, quotas, piping tokens, endings, tool limitations>
```

## Quality bar

Before replying, check:

- [ ] Every screener has `intent: "screener"` and an exit (no S41).
- [ ] Every question is reachable on at least one path (no S28); every block-skip has a rejoin.
- [ ] Every conditional question has a gate (S22 by manual check; Q3b_presuming and Q10_depends_on_prior resolved).
- [ ] Every condition parses under the grammar, names only earlier refs, and quotes option text exactly as in `options`.
- [ ] New refs use `Qn.m`; no existing ref changed.
- [ ] Each path in Paths ends at `end` and its time is plausible against `settings.stated_minutes`.
- [ ] Loops, quotas and piping are described, not faked; piping says it is tool-dependent.
- [ ] Logic is no more complex than the intent needs (prefer one `shown_when` to three jumps).

## Example

**Input:** "Only current customers should answer; accountants and owners get different questions; ask detractors why." Survey: Q1 "Do you currently use Acme?", Q2 role (Owner / Accountant or bookkeeper), Q3–Q4 owner questions, Q5–Q6 accountant questions, Q7 NPS, Q8 "Why did you give that score?", Q9 "Anything else?".

**Key output:**

| Ref | Rule (grammar) | In plain English |
| --- | --- | --- |
| Q1 | `intent: screener`; jump: `Q1 is 'No'` → end | Non-customers finish here. |
| Q3, Q4 | shown_when: `Q2 is 'Owner'` | Only owners see the owner questions. |
| Q5, Q6 | shown_when: `Q2 is 'Accountant or bookkeeper'` | Only accountants see theirs. |
| Q8 | shown_when: `Q7 <= 6` | Only detractors are asked why. |

Paths: owner promoter Q1 → Q2 → Q3 → Q4 → Q7 → Q9 (6 questions); accountant detractor Q1 → Q2 → Q5 → Q6 → Q7 → Q8 → Q9 (7); non-customer Q1 → end (1).
Lint: Before S41 on Q1 (marked as a screener, no exit). After none. S28 none. S41 none.

## No-Python fallback

When scripts cannot run, do the S28 and S41 checks by hand:

- **S41**: for each question with `intent: "screener"`, confirm it has its own `jumps` or a later question's `shown_when` names its ref.
- **S28**: go through top-level questions in order. A question is reachable if it is the first one, or the question before it is reachable and has no `when: null` jump elsewhere, or a reachable question jumps to it. Any question that fails is dead: point a jump at it or make the skipping jump conditional.

Label the section `## Lint (manual check)`. Everything else is unchanged.

## Next

Re-score the survey with **survey-score** to confirm the routing findings are gone and see the new paths' effect on the funnel; if the score raises wording issues, run **survey-fix**. Flow: create → score → fix → pretest → **logic** → copy → export.

Want to run it? Import the export into BlockSurvey or your survey tool of choice.
