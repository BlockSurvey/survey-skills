# Golden example: virtual developer conference feedback

**Brief (user):** "Post-event feedback for a 300-person virtual developer conference; decision: keep/drop sessions and whether to run it again."

**How this was produced:** by following `skills/survey-create/SKILL.md` literally (procedure steps 1–9 and its output contract), then `skills/survey-score/SKILL.md` with `references/judging-guide.md` to write `judgments.json` in one pass. `report.md` and `report.json` are the unedited output of `shared/scripts/survey_score_calc.py`. No number in this folder was typed by hand.

**Clarifying questions:** none. The decision is in the brief; the audience (registrants) and channel (follow-up email) are inferable.

**Iterations:** one pass. Lint was clean on the first run (`[]`, exit 0) and the first score was 96, so no `survey-fix` pass was needed.

The survey JSON is in [`survey.json`](survey.json) (not repeated here); the scored report is in [`report.md`](report.md).

## Survey brief
- **Decision:** After this survey we will decide which session types to keep or drop, and whether to run the conference again next year.
- **Shareables:**
  - "{event} scored an NPS of ___ (live viewers ___, recording-only ___)." (Q1, Q2)
  - "Hands-on workshops were rated most valuable; panels least (or otherwise)." (Q5)
  - "X % would drop or shorten ___." (Q6)
  - "X % are likely to attend next year." (Q9)
  - "Developers and managers valued different session types (or didn't)." (Q11)
- **Kind:** feedback · **Audience:** the ~300 people who registered, whether they watched live or on recording · **Channel:** email to all registrants the day after the event · **Budget:** 9 answerable questions, ~4 min
- **Assumptions:** anonymous; no incentive; session *types* rather than individual talks are rated, so the survey stays short and reusable (individual talk ratings belong in the platform's per-session poll).
- **Fill before sending:** {event}, {date}, {contact}

## Survey (markdown)
```markdown
# How was {event}? 4 minutes to decide what we keep next time
> A short feedback survey for everyone who registered for {event}, our virtual developer conference.
**Audience:** People who registered for {event} (about 300 developers), whether they watched live or on recording · **Kind:** feedback · **Time:** ~4 min
**Sponsor:** {event} organising team · **Purpose:** Decide which session types to keep or drop, and whether to run {event} again next year · **Language:** en
**Settings:** anonymous=true
## Welcome
**How was {event}?**
Thanks for joining us. We're the organising team, and your answers decide which sessions we keep, which we drop, and whether we run {event} again.
• For everyone who registered, live or on recording
• Takes about 4 minutes
• Anonymous: we only look at answers in summary
• Voluntary: you can stop at any time
• Open until {date}. Questions? {contact}
[Start]
## Questions
### Q1. How did you watch {event}?  `single_choice` (required)
- [ ] Mostly live
- [ ] Partly live, partly on recording
- [ ] Only on recording
- [ ] I registered but didn't watch any of it
> Intent: screener
> Jump: if Q1 is 'I registered but didn''t watch any of it' → end
### Q2. How likely are you to recommend {event} to a friend or colleague?  `nps` (required)
> Scale: 0–10 · 0 = Not at all likely · 10 = Extremely likely
> Intent: outcome
### Q3. What is the main reason for your score?  `long_text`
> Intent: open_feedback
### Q4. Next: the sessions  `statement`
> Role: information
### Q5. How valuable or not valuable was each type of session to you?  `matrix`
Leave a row blank if you didn't watch that type.
| | Not at all valuable | Slightly valuable | Moderately valuable | Very valuable | Extremely valuable |
| Keynotes | | | | | |
| Technical talks | | | | | |
| Live coding demos | | | | | |
| Hands-on workshops | | | | | |
| Panel discussions | | | | | |
| Ask-me-anything sessions | | | | | |
> Intent: attitude
### Q6. Which session types would you drop or shorten next time? Select all that apply.  `multi_choice`
- [ ] Keynotes
- [ ] Technical talks
- [ ] Live coding demos
- [ ] Hands-on workshops
- [ ] Panel discussions
- [ ] Ask-me-anything sessions
- [ ] None of the above
> Intent: attitude
### Q7. Next: the online experience and next year  `statement`
> Role: information
### Q8. How satisfied or dissatisfied were you with the online event platform?  `likert`
> Scale: 1–5 · 1 = Very dissatisfied · 2 = Dissatisfied · 3 = Neither satisfied nor dissatisfied · 4 = Satisfied · 5 = Very satisfied
> Intent: attitude
### Q9. If we run {event} again next year, how likely or unlikely are you to attend?  `single_choice`
- [ ] Very unlikely
- [ ] Unlikely
- [ ] Not sure
- [ ] Likely
- [ ] Very likely
> Intent: outcome
### Q10. What one change would most improve the next edition?  `long_text`
> Intent: open_feedback
### Q11. Which best describes your role?  `single_choice`
So we can plan sessions for the people who come.
- [ ] Software developer or engineer
- [ ] Engineering manager
- [ ] DevOps or platform engineer
- [ ] Data or ML engineer
- [ ] Student
- [ ] Other (please specify)
- [ ] Prefer not to answer
> Intent: demographic
## Thank you
**Thank you, that helps a lot**
We'll email every registrant a summary of the feedback and our decision about next year by {date}. Questions? {contact}
```

## Self-check
- **Lint:** 0 blocker · 0 high · 0 medium · 0 low (`[]`, exit 0)
- **Time:** estimated 4.1 min, stated 4 min
- **Checklist:** Decide: K_survey_kind, X2_audience_kind, R_role (Q4, Q7 `information`), C5_gap_topic · Start: S01, A1, A2, A3, A5, A6, A8, A9, A10, F5, E4, E7, S50, S15, S16, S21 (anonymous, no PII) · Continue: B2, S46, S51 (the grid is the 4th answerable question and optional), S37 (standard NPS), Q15 · Finish: B1, B4, E6, E8, S30 (6×5 grid), S31, S34 (2 of 9 open), B7 (one optional open question near the end) · Answer quality: Q3a, Q6 ("registered but didn't watch", has_none on Q6, Other and Prefer not to answer on Q11), Q8/B8 (all scales low → high), S13 (Q6 "Select all that apply" is multi_choice) · Actionability: A7, C1, C2 + S41 (Q1 exits non-viewers), C3 (Q2 NPS), C4 (Q3), Q23, Q24
- **Bent rules:** B7: the "one change" open question sits second to last; it is optional and the last question is one click.
- **Score:** 96/100 · A · ready, after 1 pass (no findings; weakest funnel stages continue 93 and finish 93)

## Why this will convert
1. Start: the title names the event and the payoff ("4 minutes to decide what we keep next time"); the welcome says who is asking, what the answers decide, the time, anonymity, closing date and contact (A1, A2, A3, A5, A9, F5, S50).
2. Continue: one click to say how they watched (with an exit for no-shows), then the standard NPS; the only typing early on is optional (B2, S41, S37, S46, S51).
3. Finish: nothing is required after Q2, one 6×5 grid, statements mark each section, and the last question is one click (S18, S30, B4).
4. Answer quality: balanced, labelled scales that all run the same way; "None of these" on the drop list; "registered but didn't watch" on the screener; neutral wording (Q8, B8, Q6, Q3a).
5. Actionability: Q5 and Q6 give a keep/drop list per session type, Q2 and Q9 answer "run it again?", and Q3/Q10 explain both (C1, C3, C4, Q23).
