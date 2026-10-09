# survey-create: worked examples

Two complete runs of the `survey-create` procedure, from brief to hand-over. Both surveys are complete (not abridged) and lint clean: `python <skill-dir>/scripts/survey_lint.py survey.json --json` prints `[]` and exits 0 for each, and the stated time is the `estimated_minutes_rounded_up` value from `--stats`. The organisations are fictional and the contact addresses use the reserved `.example` domain. The markdown section is left out to save space; in a real run it is the exact output of `python <skill-dir>/scripts/survey_export.py survey.json --format md`.

---

## Example 1: B2B SaaS churn exit survey

**Brief (user):** "Create a churn survey for our B2B SaaS. We're Acme Projects, project management for agencies. We want to know why customers cancel."

**Clarifying questions:** none. The decision (what to fix), the audience (teams that cancelled) and the channel (email after cancellation) are all inferable, so the agent states assumptions and proceeds.

### Survey brief
- **Decision:** After this survey we will decide which two churn drivers to address in next quarter's roadmap, and which are out of our control.
- **Shareables:**
  - "The top reason agencies leave is ___ (X %), then ___ (Y %)."
  - "X % were satisfied right up to leaving, so price or fit, not quality, drove it."
  - "Teams that left for a competitor mostly went to ___."
  - "The features teams missed most were ___."
  - "Churn reasons differ (or don't) by team size and agency type."
- **Kind:** feedback · **Audience:** account admins at agencies that cancelled or downgraded in the last 30 days · **Channel:** email link sent one day after cancellation, answered on a phone · **Budget:** 12 questions, ~4 min
- **Assumptions:** not anonymous, because an optional follow-up call needs an email; no incentive; closing date 30 November.
- **Fill before sending:** Nothing.

### Survey (JSON)
```json
{
  "title": "Why did your team leave Acme Projects? 4 minutes to help us fix it",
  "description": "A short exit survey for teams that cancelled or downgraded Acme Projects in the last 30 days.",
  "kind": "feedback",
  "audience": "Account admins at agencies that cancelled or downgraded Acme Projects in the last 30 days",
  "purpose": "Decide which two churn drivers to address in next quarter's roadmap, and which are fixable versus out of our control",
  "sponsor": "Acme Projects product team",
  "language": "en",
  "welcome": {"title": "Help us understand why you left", "description": "We're the Acme Projects product team. Your team recently cancelled or downgraded, and knowing why is the most useful thing you can tell us. Your answers decide what we fix next quarter.\n• Takes about 4 minutes\n• Only the product team sees your answers; we never share them outside Acme\n• Voluntary: you can stop at any time\n• Open until 30 November. Questions? research@acme.example", "button": "Start"},
  "thank_you": {"title": "Thank you, that really helps", "description": "We review every exit reason each month and publish what we changed in our quarterly product update. If you agreed to a call, we'll email you within a week. Questions? research@acme.example"},
  "settings": {"stated_minutes": 4, "progress_bar": true, "anonymous": false},
  "questions": [
    {"ref": "Q1", "type": "single_choice", "intent": "screener", "required": true, "label": "What happened to your team's Acme Projects subscription in the last 30 days?", "options": ["We cancelled it", "We moved to a cheaper plan", "Nothing, we're still on the same plan"], "jumps": [{"when": "Q1 is 'Nothing, we''re still on the same plan'", "to": "end"}]},
    {"ref": "Q2", "type": "single_choice", "intent": "attitude", "required": true, "label": "What was the main reason for the change?", "description": "Pick the one that mattered most.", "options": ["Too expensive for the value", "Missing features we needed", "Too hard for the team to adopt", "Fewer client projects", "Technical problems or bugs", "Support didn't solve our problems", "Company merged, closed or restructured"], "has_other": true, "randomize_options": true},
    {"ref": "Q3", "type": "yes_no", "intent": "behaviour", "required": false, "label": "Did your team move to another tool instead of Acme Projects?", "options": ["Yes", "No"]},
    {"ref": "Q4", "type": "short_text", "intent": "behaviour", "required": false, "label": "Which tool did your team move to?", "shown_when": "Q3 is 'Yes'"},
    {"ref": "Q5", "type": "multi_choice", "intent": "attitude", "required": false, "label": "Which features were missing? Select all that apply.", "options": ["Time tracking", "Client portal", "Resource planning", "Invoicing", "Integrations with our other tools"], "has_other": true, "shown_when": "Q2 is 'Missing features we needed'"},
    {"ref": "Q6", "type": "likert", "intent": "outcome", "required": true, "label": "Overall, how satisfied or dissatisfied was your team with Acme Projects before the change?", "scale": {"min": 1, "max": 5, "labels": {"1": "Very dissatisfied", "2": "Dissatisfied", "3": "Neither satisfied nor dissatisfied", "4": "Satisfied", "5": "Very satisfied"}}},
    {"ref": "Q7", "type": "single_choice", "intent": "behaviour", "required": false, "label": "Who made the final decision?", "options": ["I did", "I did, together with others", "Someone else in the company", "Not sure"]},
    {"ref": "Q8", "type": "long_text", "intent": "open_feedback", "required": false, "label": "What one thing could we have done to keep your team?"},
    {"ref": "Q9", "type": "statement", "role": "information", "label": "Almost done: two quick questions about your agency"},
    {"ref": "Q10", "type": "single_choice", "intent": "demographic", "required": false, "label": "How many people on your team used Acme Projects?", "description": "So we can see whether reasons differ by team size.", "options": ["1–5", "6–20", "21–50", "More than 50"], "has_prefer_not_to_answer": true},
    {"ref": "Q11", "type": "single_choice", "intent": "demographic", "required": false, "label": "What kind of agency do you run?", "description": "So we can see whether some kinds of agency leave for different reasons.", "options": ["Marketing or advertising", "Design or branding", "Software development", "Consulting", "Architecture or engineering"], "has_other": true, "has_prefer_not_to_answer": true},
    {"ref": "Q12", "type": "yes_no", "intent": "contact_or_admin", "required": false, "label": "Would you be open to a 15-minute call with our product team?", "options": ["Yes", "No"]},
    {"ref": "Q13", "type": "email", "intent": "contact_or_admin", "required": false, "label": "Which email address can we use to arrange the call?", "description": "We'll use it only to schedule this one call.", "shown_when": "Q12 is 'Yes'"}
  ]
}
```

### Self-check
- **Lint:** 0 blocker · 0 high · 0 medium · 0 low (`[]`, exit 0)
- **Time:** `--stats`: estimated 3.4 min (every gated question counted), rounded up 4, stated 4 min
- **Checklist:**
  - Decide: K_survey_kind, X2_audience_kind, R_role (Q9 is `role: information`), C5_gap_topic (reason, satisfaction, competitor, missing features, decision-maker, size).
  - Start: S01, A1, A2, S02, S07, S08, A3, A8, A9, A6, A5, A10, F5, F3 / F3a / F3b (no incentive, none promised), E4, E7, S50 (66 words), S15, S16, S21 (not anonymous, so the optional email is fine).
  - Continue: B2, S46, S51 (Q2 is required but closed), Q15, S48 (email is the last question, after outcome Q6), B3, C6 (2 demographics of 12), F1 / Q12 / Q16 / S23 (no sensitive questions; both demographics optional with "Prefer not to answer").
  - Finish: B1, B4 (Q9 signposts the switch to "about your agency"), B5, S10, B7 (the end is two one-click questions and an optional email), E1, E6, E8, S17, S18, S24, S27, S28, S30–S33 (no grids or rankings), S34 (2 of 12 open), S43, S44, S06, S47, E3, S09.
  - Answer quality: Q1–Q4, Q13, Q17, Q19 (30-day window in Q1), Q21, Q22 (no amounts asked), E2, E5, E9, F4, Q6 (Q2 has Other; Q10/Q11 have "Prefer not to answer"), Q7, Q14, Q20, Q8 / B8 (one 5-point balanced scale), Q9, Q10 / S22 (Q4, Q5, Q13 gated; Q3 is a yes/no gate rather than a reason option, so a team can be both 'too expensive' and 'moved to a competitor'), Q11 / S25 / S26 (no images), C7 (not needed under 25 questions), S03–S05, S11–S14, S35–S40, S42, S45 (Q3 starts "Did", Q12 "Would").
  - Actionability: A7, C1 (each shareable has a question), C2 + S41 (Q1 screener exits to `end`), C3 (Q6 satisfaction, real experience), C4 (Q3–Q5 and Q8 explain Q2), C5, Q5, Q18, Q23, Q24 (intent on every question; outcome at Q6 of 12), Q25, S19 (not needed at 12 questions).
- **Bent rules:** None.
- **Score:** survey-score not installed in this run; not scored.

### Why this will convert
1. Start: the title asks the respondent a direct question and names the payoff ("4 minutes to help us fix it"); the 66-word welcome names the team, what changes, the time, who sees answers, the closing date and a contact (A1, A2, A3, A5, A8, A9, F5, S50).
2. Continue: a one-click screener with an exit, then the main reason as a closed, randomised list; nothing to type and no personal data in the first three (B2, S41, S46, S51, S40).
3. Finish: 12 questions, only 3 required, follow-ups shown only to the people they apply to, a signpost before the last stretch, and an end made of one-click questions (E6, S18, S22, B4, B7).
4. Answer quality: one balanced, fully labelled satisfaction scale, exhaustive options with Other and Prefer not to answer, a 30-day recall window, neutral wording throughout (Q8, S36, Q6, Q19, Q3a).
5. Actionability: every question feeds a shareable, the outcome sits at Q6, and the reason, competitor and missing-feature answers point straight at roadmap items (C1, C3, C4, Q23, Q24).

---

## Example 2: post-event feedback survey

**Brief (user):** "Make a post-event feedback survey for Fieldwork Summit 2026, our two-day UX research conference. It was hybrid this year. We need to plan 2027."

**Clarifying questions:** none. The decision (plan 2027, including the hybrid format), the audience (registrants) and the channel (follow-up email) are inferable.

### Survey brief
- **Decision:** After this survey we will decide what to keep, change and drop in the 2027 programme, and whether to keep the hybrid format.
- **Shareables:**
  - "Fieldwork Summit 2026 scored an NPS of ___ (in person ___, online ___)."
  - "Workshops were the best-rated format; panels the weakest (or otherwise)."
  - "X % want more hands-on workshops."
  - "X % prefer a hybrid 2027; Y % in person only."
  - "The venue's weakest point was ___."
- **Kind:** feedback · **Audience:** people who registered for Fieldwork Summit 2026, in person or online · **Channel:** email to all registrants the day after the event · **Budget:** 10 questions, ~5 min
- **Assumptions:** anonymous; no incentive; closing date 15 November; results emailed by mid-December.
- **Fill before sending:** Nothing.

### Survey (JSON)
```json
{
  "title": "How was Fieldwork Summit 2026? 5 minutes to shape next year",
  "description": "A short feedback survey for everyone who attended Fieldwork Summit 2026, in person or online.",
  "kind": "feedback",
  "audience": "People who registered for Fieldwork Summit 2026 (in person or online)",
  "purpose": "Decide what to keep, change and drop in the 2027 programme, and whether to keep the hybrid format",
  "sponsor": "Fieldwork Summit organising team",
  "language": "en",
  "welcome": {"title": "How was Fieldwork Summit 2026?", "description": "Thanks for joining us. We're the organising team, and your answers decide what we keep, change and drop for 2027, including whether we stay hybrid.\n• Takes about 5 minutes\n• Anonymous: only the organising team sees answers, in summary\n• Voluntary: you can stop at any time\n• Open until 15 November. Questions? hello@fieldwork.example", "button": "Start"},
  "thank_you": {"title": "Thank you, see you in 2027", "description": "We'll email every attendee a summary of the feedback and our plans for 2027 by mid-December. Questions? hello@fieldwork.example"},
  "settings": {"stated_minutes": 5, "progress_bar": true, "anonymous": true},
  "questions": [
    {"ref": "Q1", "type": "single_choice", "intent": "screener", "required": true, "label": "How did you attend Fieldwork Summit 2026?", "options": ["In person", "Online", "Both in person and online", "I registered but didn't attend"], "jumps": [{"when": "Q1 is 'I registered but didn''t attend'", "to": "end"}]},
    {"ref": "Q2", "type": "nps", "intent": "outcome", "required": true, "label": "How likely are you to recommend Fieldwork Summit to a friend or colleague?", "scale": {"min": 0, "max": 10, "labels": {"0": "Not at all likely", "10": "Extremely likely"}}},
    {"ref": "Q3", "type": "long_text", "intent": "open_feedback", "required": false, "label": "What is the main reason for your score?"},
    {"ref": "Q4", "type": "statement", "role": "information", "label": "Next: the programme"},
    {"ref": "Q5", "type": "matrix", "intent": "attitude", "required": false, "label": "How satisfied or dissatisfied were you with each part of the programme?", "description": "Leave a row blank if you didn't attend that part.", "rows": ["Keynotes", "Talks", "Hands-on workshops", "Panel discussions"], "columns": ["Very dissatisfied", "Dissatisfied", "Neither", "Satisfied", "Very satisfied"]},
    {"ref": "Q6", "type": "single_choice", "intent": "attitude", "required": false, "label": "How did you find the balance between talks and hands-on workshops?", "options": ["Far too few workshops", "Slightly too few workshops", "About right", "Slightly too many workshops", "Far too many workshops"]},
    {"ref": "Q7", "type": "statement", "role": "information", "label": "Next: the venue and the online experience"},
    {"ref": "Q8", "type": "matrix", "intent": "attitude", "required": false, "label": "How satisfied or dissatisfied were you with each part of the venue?", "rows": ["Location and travel", "Rooms and seating", "Food and drinks", "Wi-Fi"], "columns": ["Very dissatisfied", "Dissatisfied", "Neither", "Satisfied", "Very satisfied"], "shown_when": "Q1 is 'In person' or Q1 is 'Both in person and online'"},
    {"ref": "Q9", "type": "likert", "intent": "attitude", "required": false, "label": "Overall, how satisfied or dissatisfied were you with the online experience?", "scale": {"min": 1, "max": 5, "labels": {"1": "Very dissatisfied", "2": "Dissatisfied", "3": "Neither satisfied nor dissatisfied", "4": "Satisfied", "5": "Very satisfied"}}, "shown_when": "Q1 is 'Online' or Q1 is 'Both in person and online'"},
    {"ref": "Q10", "type": "single_choice", "intent": "attitude", "required": false, "label": "Which format would you prefer for 2027?", "options": ["In person only", "Online only", "In person and online", "No preference"]},
    {"ref": "Q11", "type": "long_text", "intent": "open_feedback", "required": false, "label": "What one change would most improve Fieldwork Summit 2027?"},
    {"ref": "Q12", "type": "single_choice", "intent": "demographic", "required": false, "label": "Which best describes your role?", "description": "So we can plan sessions for the people who come.", "options": ["UX researcher", "Designer", "Product manager", "Research operations", "Student"], "has_other": true, "has_prefer_not_to_answer": true}
  ]
}
```

### Self-check
- **Lint:** 0 blocker · 0 high · 0 medium · 0 low (`[]`, exit 0)
- **Time:** `--stats`: estimated 4.3 min with every gated question counted, rounded up 5, stated 5 min (any single path is about 3.8 min)
- **Checklist:**
  - Decide: K_survey_kind, X2_audience_kind, R_role (Q4, Q7 are `role: information`), C5_gap_topic (overall, programme, format balance, venue, online, 2027 format, role).
  - Start: S01, A1, A2, S02, S07, S08, A3, A8, A9, A6, A5, A10, F5, F3 / F3a / F3b (no incentive), E4, E7, S50 (55 words), S15, S16, S21 (anonymous, no PII).
  - Continue: B2, S46, S51 (the first grid is the 4th answerable question and optional), Q15, S48 (no PII), B3, C6 (1 demographic of 10), F1 / Q12 / Q16 / S23 (role is not sensitive; optional with "Prefer not to answer").
  - Finish: B1, B4 (statements before the programme and venue blocks), B5, S10, B7, E1, E6, E8, S17, S18, S24, S27, S28, S30 (both grids 4 × 5), S31 (Q5 and Q8 are separated by Q6), S32, S33, S34 (2 of 10 open), S43, S44, S06, S47, E3, S09.
  - Answer quality: Q1–Q4, Q13, Q17, Q19 (the event is the recall frame), Q21, Q22, E2, E5, E9, F4, Q6 (Q1 includes "registered but didn't attend"; Q10 includes "No preference"; Q12 has Other and Prefer not to answer), Q7, Q14, Q20, Q8 / B8 (all scales run negative → positive; Q6 is a balanced 5-point "too few ↔ too many"), Q9, Q10 / S22 (Q8 shown to in-person attendees, Q9 to online), Q11, S25, S26, C7, S03–S05, S11–S14, S35–S40, S42, S45.
  - Actionability: A7, C1, C2 + S41 (Q1 exits non-attendees to `end`), C3 (Q2 NPS at the start), C4 (Q3 explains Q2; Q11 asks for the one change), C5, Q5, Q18 (NPS reflects the real event; only Q10 is a preference), Q23, Q24, Q25, S19.
- **Bent rules:** None. (Q2 uses the event name without the year so NPS compares across editions.)
- **Score:** survey-score not installed in this run; not scored.

### Why this will convert
1. Start: a respondent-facing title with the time and the payoff ("5 minutes to shape next year"); a 55-word welcome that names the organisers, says what the answers decide (including the hybrid question), and states time, anonymity, closing date and contact (A1, A2, A3, A8, A9, A5, F5, S50).
2. Continue: one click to say how they attended (with an exit for no-shows), then the standard NPS; the only typing early on is optional (B2, S41, S37, S46, S51).
3. Finish: nothing is required after Q2, in-person and online attendees each skip the block that doesn't apply, two small grids are separated, and statements mark each section (S18, S22, S30, S31, B4).
4. Answer quality: balanced, fully labelled scales all running the same way; exhaustive options including "No preference" and "registered but didn't attend"; neutral wording (Q8, B8, S36, Q6, Q3a).
5. Actionability: every block maps to a 2027 decision (programme mix, venue, format), NPS can be cut by attendance mode, and the two open questions ask for a reason and one change, not an essay (C1, C3, C4, Q23, Q24).
