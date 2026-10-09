# Personas for a synthetic pretest

How to build the simulated respondents, what each state means, how long each question takes, and a worked mini-example. This is a cognitive-pretest simulation: it finds wording, routing and effort problems before real people see them. It does not predict response rates and it does not replace a pilot with five real respondents from the audience.

## Building the panel

Build **5 to 8** personas from the survey's `audience`, `purpose`, `kind` and welcome text. If `audience` is empty, infer it from the title and questions and say so.

Every panel must vary these six dimensions. Spread them; never give one persona all the hard traits and the others none.

| Dimension | Values to spread across the panel |
| --- | --- |
| Expertise | expert in the topic · typical · novice (new to the product, the field or the vocabulary) |
| Motivation | keen (cares about the outcome) · neutral · reluctant (doing it as a favour, or because of the incentive) |
| Device | phone (at least half the panel, matching real traffic) · desktop |
| Time pressure | relaxed · squeezed (between meetings, on a commute; will skim) |
| Language comfort | native · fluent second-language reader · low literacy or reading in a hurry |
| Fit | in the audience · **one edge persona for whom the survey, or a section of it, does not apply** (a non-user who got the link, a lapsed customer, a manager answering for a team) |

Rules:

1. **Ground every persona in the survey.** Name a role and situation the audience description implies ("Priya, runs a two-person bakery, invoices weekly from her phone"), not a generic marketing persona.
2. **One line of profile each**: a first name (used as the persona's only label; never `P1`, `P2`, which clash with survey-fix pattern ids), situation, the six dimension values, and the one thing most likely to make them stop.
3. **Include the edge persona every time.** It is the persona that exposes missing screeners (C2, S41), presuming questions (Q3b, Q10, S22) and non-exhaustive options (Q6).
4. **No stereotypes.** Vary expertise and language comfort by situation, not by nationality, age or gender. Do not use real people.
5. **Keep it honest.** A persona answers as that person plausibly would, including skipping, guessing and quitting. Do not make personas suspiciously cooperative so the survey looks good.

## States

Each persona logs exactly one state per question shown to them.

| State | Meaning | Typical cause | Maps to |
| --- | --- | --- | --- |
| `fine` | Understood it at once and answered truthfully. | — | — |
| `confused` | Had to re-read, or could read it two ways, or did not know a term. Answered, but the answer may not mean what the author thinks. | ambiguity, jargon, two questions in one, missing unit or window | Q1, Q2, Q4, E5, Q19, Q22, S43 |
| `annoyed` | Understood it but resents it: too long, too personal, repetitive, a grid on a phone, required when it should not be. Still answers. | effort, intrusiveness, repetition | Q15, S18, S30, S31, B5, E6, Q16 |
| `would_quit` | Would close the survey here. Counted as dropped from this question on. | demanding and required early, PII before trust, a wall of text, a long grid on a phone, a question that does not apply with no way out | S51, S48, Q15, S17, S50, S22 |
| `satisficed` | Answered without real thought: picked the first option, straight-lined a grid, typed "n/a". Data is noise. | monotony, long lists, fatigue, unbalanced or unlabelled scales | E8, S27, S31, S40, S36, Q8 |
| `not_applicable` | The question does not apply to them and no option says so. They guess, pick something false, or skip if they can. | presuming wording, missing screener or gate, non-exhaustive options | Q3b, Q10, S22, Q6, C2, S41 |

When two states apply, log the worse one: `would_quit` > `not_applicable` > `confused` > `satisficed` > `annoyed` > `fine`.

**After `would_quit`**: keep walking that persona through the rest of the survey, marked `(forced)`, so later questions still get tested; for the drop-off table they stay counted as dropped. Routing still applies: a persona sent to `end` by a jump stops there and is **not** counted as quitting (that is the screener working).

**Routing**: follow `shown_when` and `jumps` exactly as written for each persona's answers. A question not shown to a persona gets no line from them. This is how the simulation tests the logic.

## Seconds per question

Base seconds are the same as [question-types.md](question-types.md#seconds-per-type), so the simulated totals line up with the survey's time estimate (S16).

| Type | Base seconds | Type | Base seconds |
| --- | --- | --- | --- |
| `single_choice` | 10 | `slider` | 10 |
| `multi_choice` | 15 | `matrix` / `likert` with rows | 8 × rows |
| `dropdown` | 10 | `ranking` | 25 |
| `yes_no` | 10 | `date` | 12 |
| `short_text` | 30 | `email` | 15 |
| `long_text` | 60 | `phone` | 15 |
| `number` | 15 | `file` | 60 |
| `rating` | 8 | `statement` | 8 |
| `nps` | 8 | `consent` | 6 |
| `likert` (single) | 8 | `group` | 5 |

Persona modifiers (simulation heuristics, not scoring rules; apply at most two, multiply):

| Condition | Multiplier |
| --- | --- |
| Phone, and the question is a matrix, ranking, `long_text` or `file` | × 1.5 |
| Novice, or second-language reader, on a question logged `confused` | × 1.5 |
| Squeezed for time | × 0.7 (they skim; a `long_text` becomes a few words) |
| `satisficed` | × 0.5 |
| Low literacy, any question with a label over 20 words | × 1.5 |

Round each question to whole seconds. A persona's total = Σ over the questions shown to them (including `statement`s). Compare each total with `settings.stated_minutes` × 60: over by more than 50 % is worth reporting; the survey-level S16 rule (stated vs estimated, ±(2× + 3 min)) stays the authority on time mismatch.

## Think-aloud lines

One line per persona per question, in the persona's voice, under 20 words, saying what they think while answering. Quote the words that cause trouble.

- Good: `"'AR reconciliation'? I just mark invoices paid. Picking 'Neutral'."` → `confused`
- Good: `"My email, already? I haven't even seen a question yet."` → `would_quit`
- Bad: `"This question is unclear."` (no voice, no quote, no reason)

## Aggregation

1. **Drop-off table**: for each question in order, **Shown to** = personas still active there (not yet dropped, not routed past it or out by logic; `(forced)` rows are excluded), the cumulative share of the panel that has logged `would_quit` at or before it (personas routed to `end` by a screener are removed from the denominator from that point, and reported separately), and the dominant state among the active personas shown it. Forced rows still appear in the walkthrough and still surface problems, but never count in Shown to or the dominant state.
2. **Time per persona**: total seconds vs stated time.
3. **Top confusion points**: the questions with the most non-`fine` states, each with two or three verbatim persona lines.
4. **Prioritised fixes**: one row per problem, ordered by (personas lost, then personas affected, then earliness in the survey). Each fix names the rubric or static id from the "Maps to" column and the survey-fix pattern that resolves it.

## Worked mini-example

Survey: "Acme Invoicing check-in", audience "small-business owners who invoiced with Acme in the last 3 months", stated 2 minutes, phone-first. Questions: Q1 `email` (required) "Your email address"; Q2 `rating` 1–5 "How easy is AR reconciliation in Acme?"; Q3 `single_choice` "How often do you use the mobile app?" (Daily / Weekly / Monthly); Q4 `long_text` (required) "What should we build next?".

Panel (5):

| Persona | Profile |
| --- | --- |
| Priya | Two-person bakery owner; typical; keen; phone; squeezed; native. Stops at: effort on a phone. |
| Marcus | Freelance accountant; expert; neutral; desktop; relaxed; native. Stops at: vague questions. |
| Ana | Cleaning-company owner; novice; reluctant; phone; squeezed; second-language. Stops at: jargon, typing. |
| Tom | Café manager; typical; neutral; phone; relaxed; native. Stops at: personal data early. |
| Lee (edge) | Tried Acme once a year ago, now uses a spreadsheet; got the link in a newsletter; desktop. Stops at: questions that don't apply. |

Walk (excerpt):

| Q | Persona | Think-aloud | State | s |
| --- | --- | --- | --- | --- |
| Q1 | Tom | "Email first? I don't know who's reading this yet." | would_quit | 15 |
| Q1 | Ana | "Fine, but why do they need it if it's feedback?" | annoyed | 15 |
| Q2 | Ana | "'AR reconciliation'… I'll just put 3." | confused | 12 |
| Q2 | Priya | "No idea what AR means, tapping 4 to move on." | satisficed | 4 |
| Q3 | Marcus | "I never use the app. None of these fit." | not_applicable | 10 |
| Q3 | Lee | "I don't even use Acme any more." | not_applicable | 10 |
| Q4 | Priya | "Typing an essay on my phone? Required? Closing." | would_quit | 63 |

Drop-off (cumulative): Q1 20 % (Tom) · Q2 20 % · Q3 20 % · Q4 60 % (Priya, Ana). Dominant state at Q3: `not_applicable` (2 of 4 shown).

Prioritised fixes:

| # | Problem | Personas | Id | survey-fix pattern |
| --- | --- | --- | --- | --- |
| 1 | Required essay last, typed on a phone | lost Priya, Ana | Q15, B7 | P21 Move friction later (make Q4 optional) |
| 2 | Email asked before anything else | lost Tom | S51, Q15 | P21 Move friction later |
| 3 | No screener; lapsed users answer everything | Lee | C2, S41 | P12 Add a screener and an exit |
| 4 | Q3 presumes app use; no "I don't use it" | Marcus, Lee | Q3b, Q6, Q19 | P2 De-presume and gate |
| 5 | "AR reconciliation" is jargon | Priya, Ana | Q4 | P19 Plain language |
