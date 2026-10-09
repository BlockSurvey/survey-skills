---
name: survey-pretest
description: Runs a synthetic cognitive pretest of a survey before launch. Builds 5–8 realistic respondent personas from the survey's audience (varying expertise, motivation, phone or desktop, time pressure, language comfort, plus one person it does not apply to), walks each one through every question with a one-line think-aloud and a state (fine, confused, annoyed, would quit, satisficed, not applicable), and reports a drop-off table, time per persona, the top confusion points and prioritised fixes mapped to rubric ids. Use it when someone says "pretest my survey", "pilot this questionnaire", "simulate respondents", "where will people drop off", "will people understand this", "user-test my form", or before sending a survey built in Google Forms, Typeform, SurveyMonkey, Qualtrics, on paper or any other tool. A simulation, not a replacement for real pilot respondents.
license: MIT
metadata:
  author: blocksurvey
  version: "1.0.0"
  category: improve
---

# Survey pretest

This skill pretests a survey with simulated respondents. It builds a small panel of personas from the survey's own audience and purpose, has each one walk the survey question by question (following the display and skip logic), thinking aloud in one line and logging how the question landed and how long it took. It then aggregates the walk into a drop-off table, time per persona, the questions that confused people most (quoted), and a prioritised list of fixes, each mapped to a rubric or static-check id and to the survey-fix pattern that resolves it. It is honest about what it is: a fast cognitive walkthrough that catches wording, routing and effort problems, not a measurement of real behaviour. Five real people from the audience still beat any simulation.

## When to use

- A survey is drafted (or freshly fixed) and the user wants to know where people will struggle or drop off before launch.
- The score report says `needs_work` on the funnel stages `continue` or `finish` and the user wants to see why from a respondent's seat.
- The survey has logic and the user wants each path walked by someone it was built for, and by someone it was not.
- The user asks "will people understand Q5?", "is this too long on a phone?", "pilot this for me".

## Inputs

1. **Survey**: portable survey JSON (see [survey-format.md](references/survey-format.md)). Convert markdown or a pasted list with `python <skill-dir>/scripts/survey_export.py survey.md --format json --out survey.json`; from another tool, number questions `Q1…Qn`, infer types and mark guesses `inferred: true`.
2. **Audience** (from `audience`, else ask once, else infer from title and questions and say so): who will really receive it, through which channel (email, in-app, QR code, panel), and roughly what share on phones.
3. **Optional**: a score report or lint output (to cross-check findings), the panel size the user wants (default 6), personas the user insists on (e.g. "include a manager answering for their team").

## Procedure

**Paths.** `<skill-dir>` = the folder containing this SKILL.md (for example `~/.claude/skills/survey-pretest`). Run every script by its full path, `python <skill-dir>/scripts/survey_lint.py survey.json --json`, from wherever the user's survey is; never assume the current directory is the skill folder (it may be read-only). Use `python3` if `python` is missing. Write working files (`survey.json`) next to the user's survey, not inside `<skill-dir>`.

Do the whole walk in one pass: build the panel, walk all personas, then aggregate. Do not re-send the survey once per persona.

1. **Lint first.** Run `python <skill-dir>/scripts/survey_lint.py survey.json --json` (exit code 1 just means it found something). Keep the findings: the walk should confirm or explain them, and any blocker (no questions, empty labels, a grid with no rows) must be fixed before a pretest means anything.
2. **Build the panel.** Read [personas.md](references/personas.md) and create 5–8 personas grounded in the audience. Spread the six dimensions (expertise, motivation, device with at least half on phones, time pressure, language comfort, fit) and always include one edge persona the survey or a section does not apply to. Produce the panel table: one line per persona with the six values and their likely stopping point.
3. **Map the paths.** From `shown_when` and `jumps` (condition grammar in survey-format.md), note which questions each persona will see given the answers they would plausibly give. A screener jump to `end` stops that persona; that is routing working, not a drop-off.
4. **Walk every persona through every question they are shown.** For each, write one think-aloud line in the persona's voice (under 20 words, quoting the trouble words), one state from `fine | confused | annoyed | would_quit | satisficed | not_applicable`, and estimated seconds (base seconds per type and persona modifiers in personas.md; same base seconds as question-types.md). After `would_quit`, keep walking that persona marked `(forced)` so later questions are still tested; they stay counted as dropped. Walk the welcome screen too: a persona can quit before Q1 (S50, A9, A5).
5. **Aggregate.**
   - Drop-off table: per question, cumulative % of the panel that has logged `would_quit` at or before it, and the dominant state among those shown it.
   - Time per persona: total seconds vs `settings.stated_minutes` × 60.
   - Top confusion points: the 3–5 questions with the most non-`fine` states, each with 2–3 verbatim persona lines.
6. **Prioritise fixes.** One row per problem, ordered by personas lost, then personas affected, then how early it occurs. Map each to the rubric or static id it is evidence for (see the states table in personas.md: e.g. `not_applicable` on a presuming question → Q3b_presuming / S22_conditional_without_logic; `would_quit` on a required early email → S51_early_friction) and to the survey-fix pattern (P1–P24 in survey-fix's fix-patterns.md; name the pattern, e.g. "P2 De-presume and gate"). Where the walk agrees with a lint finding, say so; where it finds something lint cannot (wording, presumption, jargon), say that too.
7. **State the limits** in one line at the top of the report: simulated personas, no real behaviour, numbers are directional.

## Output contract

Emit exactly these sections, in this order:

```
> Simulated pretest: <n> personas built from the stated audience. Directional, not a measurement; confirm with 5 real pilot respondents.

## Panel
| Persona | Profile (expertise · motivation · device · time · language · fit) | Likely stopping point |

## Walkthrough
### <Persona name>
| Q | Think-aloud | State | s |
| welcome | … | fine | 10 |
| Q1 | … | confused | 15 |
(one table per persona; questions they were not shown are omitted; forced rows marked "(forced)")

## Drop-off
| Question | Shown to (active, excludes forced) | % would_quit (cumulative) | Dominant state |
Routed out by the screener: <n> (<names>), not counted as drop-off.

## Time per persona
| Persona | Path length (questions) | Seconds | vs stated <m> min |

## Top confusion points
1. **Qn** "<label>": <k> of <shown> personas struggled. "<line>" (Marcus) · "<line>" (Lee)

## Prioritised fixes
| # | Problem | Personas lost / affected | Finding id | survey-fix pattern |
```

Label personas by first name only (never `P1`, `P2`: those are survey-fix pattern ids) and use the names consistently across all sections. Keep the walkthrough tables complete: a missing row hides a problem.

## Quality bar

Before replying, check:

- [ ] 5–8 personas; at least half on a phone; one edge persona for whom the survey or a section does not apply.
- [ ] Every persona is grounded in the stated audience; no stereotypes, no real people.
- [ ] Every question shown to a persona has exactly one line, one state, one number of seconds; logic was followed exactly as written.
- [ ] Screener exits are reported separately, not as drop-off.
- [ ] Seconds use the base table in personas.md; totals are compared with `stated_minutes`.
- [ ] Every prioritised fix names a real id from rubric.md or static-checks.md and a survey-fix pattern.
- [ ] Personas were not made conveniently cooperative: if nobody struggled anywhere, re-check the edge persona and the phone personas on grids, long text and early required questions.
- [ ] The simulation disclaimer is the first line.

## Example

**Input:** a 4-question "Acme Invoicing check-in", stated 2 minutes: Q1 required email, Q2 rating "How easy is AR reconciliation in Acme?", Q3 "How often do you use the mobile app?" (Daily / Weekly / Monthly), Q4 required long text "What should we build next?".

**Key output** (panel of 5, worked in full in personas.md):

| Question | Shown to | % would_quit (cumulative) | Dominant state |
| --- | --- | --- | --- |
| Q1 | 5 | 20 % | annoyed |
| Q2 | 4 | 20 % | confused |
| Q3 | 4 | 20 % | not_applicable |
| Q4 | 4 | 60 % | would_quit |

Top confusion: **Q2** "AR reconciliation": "No idea what AR means, tapping 4 to move on." (Priya).
Fixes: 1 · required essay last, typed on a phone · lost 2 · Q15_abandon_risk, B7_end_loading · P21 Move friction later. 2 · email first · lost 1 · S51_early_friction · P21 Move friction later. 3 · no screener · 1 affected · C2_has_screener, S41 · P12 Add a screener and an exit. 4 · Q3 presumes app use · 2 affected · Q3b_presuming, Q6 · P2 De-presume and gate. 5 · jargon · 2 affected · Q4_jargon · P19 Plain language.

## No-Python fallback

When scripts cannot run, skip step 1's lint and instead check the static items the walk depends on by hand: blockers (S01–S05), S51 (demanding and required in the first three), S41 (screener with no exit), S28 (questions nothing leads to), S50 (welcome over 120 words). Convert pasted text to the JSON shape by hand. The walk, aggregation and output are unchanged.

## Next

Apply the prioritised fixes with **survey-fix** (hand it this report's fix table: it accepts finding ids), then re-score with **survey-score**. If the walk exposed routing problems, design the logic with **survey-logic**. Flow: create → score → fix → **pretest** → logic → copy → export.

Want to run it? Import the export into BlockSurvey or your survey tool of choice.
