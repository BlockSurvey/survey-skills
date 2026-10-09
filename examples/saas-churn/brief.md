# Golden example: B2B SaaS churn survey

**Brief (user):** "Create a churn survey for a B2B SaaS that just lost a customer; audience: the admin who cancelled; decision: which of 5 churn drivers to fix first."

**How this was produced:** by following `skills/survey-create/SKILL.md` literally (procedure steps 1–9 and its output contract), then `skills/survey-score/SKILL.md` with `references/judging-guide.md` to write `judgments.json` in one pass. `report.md` and `report.json` are the unedited output of `shared/scripts/survey_score_calc.py`. No number in this folder was typed by hand.

**Clarifying questions:** none. Decision, audience and channel are all in the brief or inferable.

**Iterations:** one pass. Lint was clean on the first run (`[]`, exit 0) and the first score was 94, above the create skill's 85 bar, so no `survey-fix` pass was needed.

The survey JSON is in [`survey.json`](survey.json) (not repeated here); the scored report is in [`report.md`](report.md).

## Survey brief
- **Decision:** After this survey we will decide which of five churn drivers (price for the value, missing features, ease of learning and use, reliability, support) to fix first.
- **Shareables:**
  - "The top reason admins gave for cancelling was ___ (X %), then ___ (Y %)." (Q2)
  - "Weighted across all five drivers, ___ contributed most to cancellations." (Q6)
  - "X % were satisfied right up to cancelling, so fit or price, not quality, drove it." (Q4)
  - "X % of churned teams moved to another product built for the same job; Y % went back to spreadsheets." (Q7)
  - "Reasons differ (or don't) between small and large teams." (Q9)
- **Kind:** feedback · **Audience:** the account admin who cancelled their team's subscription in the last 30 days · **Channel:** email link sent the day after cancellation, answered on a phone · **Budget:** 9 answerable questions, ~4 min
- **Assumptions:** not anonymous (the optional follow-up call needs an email, gated behind a yes/no); no incentive; closing date and contact are placeholders.
- **Fill before sending:** {company}, {product}, {date}, {contact}

## Survey (markdown)
```markdown
# Why did your team cancel {product}? 4 minutes to help us fix it
> A short exit survey for the admin who cancelled their team's {product} subscription in the last 30 days.
**Audience:** The account admin who cancelled their team's {product} subscription in the last 30 days · **Kind:** feedback · **Time:** ~4 min
**Sponsor:** {company} product team · **Purpose:** Decide which of five churn drivers (price for value, missing features, ease of use, reliability, support) to fix first · **Language:** en
## Welcome
**Help us understand why you cancelled**
We're the {company} product team. You recently cancelled {product}, and knowing why is the most useful thing you can tell us: your answers decide which problem we fix first.
• For the admin who cancelled in the last 30 days
• Takes about 4 minutes
• Only the product team sees your answers; we never share them outside {company}
• Voluntary: you can stop at any time
• Open until {date}. Questions? {contact}
[Start]
## Questions
### Q1. Did you cancel your team's {product} subscription in the last 30 days?  `yes_no` (required)
- [ ] Yes
- [ ] No
> Intent: screener
> Jump: if Q1 is 'No' → end
### Q2. What was the main reason your team cancelled?  `single_choice` (required)
Pick the one that mattered most.
- [ ] The price was too high for the value
- [ ] Features we needed were missing
- [ ] It was too hard for the team to learn and use
- [ ] Bugs, outages or slow performance
- [ ] Support didn't resolve our issues
- [ ] Our needs changed (budget, team or project)
- [ ] Other (please specify)
> Randomize options
> Intent: attitude
### Q3. What happened that made this the main reason?  `long_text`
A sentence or two is plenty.
> Intent: open_feedback
### Q4. Overall, how satisfied or dissatisfied was your team with {product} before you cancelled?  `likert` (required)
> Scale: 1–5 · 1 = Very dissatisfied · 2 = Dissatisfied · 3 = Neither satisfied nor dissatisfied · 4 = Satisfied · 5 = Very satisfied
> Intent: outcome
### Q5. Next: how much each factor mattered  `statement`
> Role: information
### Q6. How much did each of these contribute to your decision to cancel?  `matrix`
| | Not at all | Slightly | Moderately | Very much | Completely |
| Price for the value | | | | | |
| Missing features | | | | | |
| Ease of learning and use | | | | | |
| Reliability (bugs, outages, speed) | | | | | |
| Support | | | | | |
> Intent: attitude
### Q7. What is your team using instead of {product} now?  `single_choice`
- [ ] Another product built for the same job
- [ ] General tools (spreadsheets, documents or email)
- [ ] A tool we built ourselves
- [ ] Nothing yet
- [ ] Not decided yet
- [ ] Other (please specify)
> Intent: behaviour
### Q8. Almost done: two quick questions about your team  `statement`
> Role: information
### Q9. How many people on your team used {product}?  `single_choice`
So we can see whether reasons differ by team size.
- [ ] 1–5
- [ ] 6–20
- [ ] 21–50
- [ ] More than 50
- [ ] Prefer not to answer
> Intent: demographic
### Q10. Would you be open to a 15-minute call with our product team?  `yes_no`
- [ ] Yes
- [ ] No
> Intent: contact_or_admin
### Q11. Which email address can we use to arrange the call?  `email`
We'll use it only to schedule this one call.
> Intent: contact_or_admin
> Shown when: Q10 is 'Yes'
## Thank you
**Thank you, that really helps**
We review every answer at the end of each month and publish what we changed in our product update. If you agreed to a call, we'll email you within a week to find a time. Questions? {contact}
```

## Self-check
- **Lint:** 0 blocker · 0 high · 0 medium · 0 low (`python3 shared/scripts/survey_lint.py examples/saas-churn/survey.json --json` prints `[]`, exit 0)
- **Time:** estimated 3.1 min, stated 4 min
- **Checklist:** Decide: K_survey_kind, X2_audience_kind, R_role (Q5, Q8 `information`), C5_gap_topic · Start: S01, A1, A2, A3, A5, A6, A8, A9, A10, F5, E4, E7, S50, S15, S16, S21 (not anonymous, so the optional email is allowed) · Continue: B2, S46, S51 (Q2 is required but closed; the grid is optional), Q15, S48 (email last, after the outcome) · Finish: B1, B4, B7, E6, E8, S17, S30 (5×5 grid), S31, S34 (1 of 9 open) · Answer quality: Q2, Q3a, Q6 (Other on Q2/Q7, Prefer not to answer on Q9), Q8/B8 (one balanced labelled satisfaction scale; one unipolar contribution scale), Q19 (30-day window in Q1), S12 (team-size buckets contiguous) · Actionability: A7, C1 (every driver rated in Q6), C3 (Q4), C4 (Q3 explains Q2), Q23, Q24 (intent on every question)
- **Bent rules:** C2 / screener: kept a one-click screener with an exit even though the email goes only to cancellers, because forwarded links happen.
- **Score:** 94/100 · A · ready, after 1 pass (no findings; funnel: start 93, continue 93, finish 97, answer quality 95, actionability 96)

## Why this will convert
1. Start: the title asks the admin a direct question and names the payoff ("4 minutes to help us fix it"); the welcome names the team, what changes, the time, who sees the answers, the closing date and a contact (A1, A2, A3, A5, A9, F5, S50).
2. Continue: a one-click screener with an exit, then the main reason as a closed, randomised list; nothing to type and no personal data in the first three (B2, S41, S46, S51, S40).
3. Finish: 9 questions, 3 required, two short signposts, one small 5×5 grid, and an end made of one-click questions plus an optional, gated email (E6, B4, S30, B7).
4. Answer quality: a fully labelled, balanced satisfaction scale, exhaustive options with Other and Prefer not to answer, a 30-day recall window, neutral wording (Q8, S36, Q6, Q19, Q3a).
5. Actionability: Q2 names the top driver and Q6 weights all five, so the fix-first decision falls straight out of the data; Q3 explains it and Q9 cuts it by team size (A7, C1, C4, Q23).
