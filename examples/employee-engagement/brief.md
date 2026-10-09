# Golden example: quarterly employee engagement pulse

**Brief (user):** "Quarterly engagement pulse for a 120-person company; anonymous; decision: which two drivers HR acts on this quarter."

**How this was produced:** by following `skills/survey-create/SKILL.md` literally (procedure steps 1–9 and its output contract), then `skills/survey-score/SKILL.md` with `references/judging-guide.md` to write `judgments.json` in one pass. `report.md` and `report.json` are the unedited output of `shared/scripts/survey_score_calc.py`. No number in this folder was typed by hand.

**Clarifying questions:** none. Audience (everyone at the company), decision and anonymity are in the brief; channel (email or chat link, on a phone) is inferable.

**Iterations:**
- Self-check (create step 7), before scoring: the first draft had 6 answerable questions, 2 of them open text, and lint reported `S34_open_ended_overload` (medium, 2 of 6 = 33 %) and an `info` `S35_loaded_words` ("should" in "Which two of these should we work on first"). Fix: added a closed trend question (Q3 "Compared with three months ago…") and reworded the priority question to "Which two of these would you most like us to work on this quarter?". Walking the checklist (Q6 exhaustive options) also added "I joined less than three months ago" to Q3, since new joiners cannot compare. Lint then printed `[]`.
- Score (create step 8): 92/100 on the first scoring pass, above the 85 bar, so no `survey-fix` pass. The one remaining finding (A1, low: the title names the topic, not the purpose) is left in on purpose so the example shows what a "ready, one thing to polish" report looks like.

The survey JSON is in [`survey.json`](survey.json) (not repeated here); the scored report is in [`report.md`](report.md).

## Survey brief
- **Decision:** After this survey we will decide which two engagement drivers HR acts on this quarter.
- **Shareables:**
  - "Our employee NPS this quarter is ___ (last quarter ___)." (Q1)
  - "X % say working here got better in the last three months; Y % worse." (Q3)
  - "The lowest-agreement drivers were ___ and ___." (Q5)
  - "Asked directly, people most want us to work on ___ and ___." (Q6)
  - "In ___, workload stands out more than elsewhere (groups of 5 or more only)." (Q9)
- **Kind:** feedback · **Audience:** everyone employed at the company this quarter (~120 people) · **Channel:** link in email or chat, answered on a phone · **Budget:** 7 answerable questions, ~4 min
- **Assumptions:** anonymous, so no names, emails or tenure/age questions that could identify people in a 120-person company; only one coarse area question, optional, with a "groups of 5 or more" reporting rule; no incentive. The seven drivers (goal clarity, manager feedback, tools, workload, growth, recognition, psychological safety) are a common engagement-driver set; swap in your own.
- **Fill before sending:** {company}, {date}, {contact}; the area list in Q9 should match your departments, merged so every group has at least 5 people

## Survey (markdown)
```markdown
# Quarterly pulse: how is work going? 4 anonymous minutes
> A short, anonymous quarterly check-in for everyone at {company}.
**Audience:** Everyone employed at {company} (about 120 people) during this quarter · **Kind:** feedback · **Time:** ~4 min
**Sponsor:** {company} People team · **Purpose:** Decide which two engagement drivers HR acts on this quarter · **Language:** en
**Settings:** anonymous=true
## Welcome
**How is work going?**
This is the People team's quarterly pulse. Your answers decide the two things we work on this quarter, and we'll share the results and our plan with everyone.
• For everyone at {company}
• Takes about 4 minutes
• Anonymous: we don't collect names or emails, and we only report groups of 5 or more
• Voluntary: you can skip any question or stop at any time
• Open until {date}. Questions? {contact}
[Start]
## Questions
### Q1. How likely are you to recommend {company} as a place to work to a friend or colleague?  `nps`
> Scale: 0–10 · 0 = Not at all likely · 10 = Extremely likely
> Intent: outcome
### Q2. What is the main reason for your score?  `long_text`
> Intent: open_feedback
### Q3. Compared with three months ago, how is working at {company} for you now?  `single_choice`
- [ ] Much worse
- [ ] Somewhat worse
- [ ] About the same
- [ ] Somewhat better
- [ ] Much better
- [ ] I joined less than three months ago
> Intent: attitude
### Q4. Next: what shapes your work day to day  `statement`
> Role: information
### Q5. Thinking about the last three months, how much do you agree or disagree with each statement?  `matrix`
| | Strongly disagree | Disagree | Neither agree nor disagree | Agree | Strongly agree |
| I understand how my work contributes to {company}'s goals | | | | | |
| My manager gives me useful feedback | | | | | |
| I have the tools I need to do my job well | | | | | |
| My workload is manageable | | | | | |
| I can see a path to grow my career here | | | | | |
| I am recognised when I do good work | | | | | |
| I can raise concerns without fear of negative consequences | | | | | |
> Intent: attitude
### Q6. Which two of these would you most like us to work on this quarter? Choose up to two.  `multi_choice`
- [ ] Clarity on goals
- [ ] Feedback from managers
- [ ] Tools
- [ ] Workload
- [ ] Career growth
- [ ] Recognition
- [ ] Safety to speak up
- [ ] Other (please specify)
> Select: min 1 · max 2
> Randomize options
> Intent: attitude
### Q7. What one change would make the biggest difference to your work this quarter?  `long_text`
> Intent: open_feedback
### Q8. One last, optional question  `statement`
> Role: information
### Q9. Which area do you work in?  `single_choice`
So we can see where action is needed. We never report a group with fewer than 5 answers.
- [ ] Engineering
- [ ] Product and design
- [ ] Sales and marketing
- [ ] Customer success and support
- [ ] Operations, finance and HR
- [ ] Prefer not to answer
> Intent: demographic
## Thank you
**Thank you for your honesty**
We'll share the results and the two areas we'll act on at the all-hands on {date}, and report back on progress next quarter. Questions? {contact}
```

## Self-check
- **Lint:** 0 blocker · 0 high · 0 medium · 0 low (`[]`, exit 0, after the step-7 revision above)
- **Time:** estimated 3.9 min, stated 4 min
- **Checklist:** Decide: K_survey_kind, X2_audience_kind, R_role (Q4, Q8 `information`), C5_gap_topic · Start: S01, A2, A3, A5 (anonymous, groups of 5+), A6, A8, A9, A10, F5, E4, E7, S50, S15, S16, S21 (anonymous, no PII) · Continue: B2 (eNPS first), S46, S51 (nothing required at all), Q15, S48 · Finish: B1, B4, E6, S30 (7×5 grid), S31, S34 (2 of 7 open), S14 (Q6 `selection.max` 2 matches "Choose up to two") · Answer quality: Q3a, Q6 (new-joiner option, Other, Prefer not to answer), Q8/B8, Q17 (all statements positively phrased), Q19 (three-month window on Q3 and Q5) · Actionability: A7, C1, C3 (eNPS), C4 (Q2, Q7), Q23, Q24
- **Bent rules:** A1: the title says what it is ("Quarterly pulse: how is work going?") but not what it is for; kept short because it is a recurring, recognisable pulse. E8: the seven drivers are one agree/disagree grid (one look-alike battery) so they can be compared side by side.
- **Score:** 92/100 · A · ready, after 1 scoring pass (one low finding: A1)

## Why this will convert
1. Start: the welcome leads with what the answers decide ("the two things we work on this quarter"), names the People team, and makes anonymity concrete ("we don't collect names or emails, and we only report groups of 5 or more") (A3, A5, A9, E4).
2. Continue: one tap to answer the eNPS, an optional reason, then a one-click trend question; nothing is required anywhere (B2, S46, S51, Q15).
3. Finish: 7 questions in about 4 minutes, signposted, one 7×5 grid, and an optional one-click area question to end (E6, B4, S30, B7).
4. Answer quality: balanced, fully labelled agree/disagree scale, positively worded statements, a three-month window, and an option for new joiners (Q8, Q17, Q19, Q6).
5. Actionability: Q5 shows which drivers score lowest and Q6 asks directly which two to act on, so HR can pick the two drivers from two independent signals (A7, C1, Q23).
