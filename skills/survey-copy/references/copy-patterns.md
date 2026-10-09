# Copy patterns

Reusable lines for the text around a survey. Pick, adapt, and fill the `{variables}`; never keep a promise you cannot honour. Every pattern names the rubric ids it helps satisfy (see the rubric in the score skill, or `playbook.md` §3 and §13 here).

Variables used below: `{sponsor}` (team or organisation), `{audience}`, `{topic}`, `{change}` (what the answers decide), `{minutes}`, `{deadline}`, `{contact}`, `{incentive}`, `{delivery}` (how and when it arrives), `{results_when}`, `{privacy}` (the true handling in one word: "anonymous" only if no PII is collected, else "confidential"; see Privacy one-liners), `{first_name}`, `{link}`, `{sender}`.

## The welcome skeleton

```
{Title: what it is about, for them, ≤ 8 words}
{Who is asking} + {who it is for} + {why it matters / what changes}.     ← one or two sentences
• Takes about {minutes} minutes
• {Privacy line}
• {Consent line}                         (research only)
• {Incentive: what + how + when}         (only if real)
• Open until {deadline}. Questions? {contact}
[Start]
```

Order matters: motivation first, rules after (`E4_welcome_motivates`). One fact per bullet keeps purpose, time and privacy findable at a glance (`E7_welcome_scannable`). Target ≤ 80 words; the hard lint cap is 120 (`S50_welcome_too_long`).

## Proven openers

Lead with who is asking and why the respondent's view matters. (A3, A6, A9, E4)

- "We're {sponsor}, and we want to hear from {audience}."
- "You {did the thing} recently, so you know better than anyone what works and what doesn't."
- "Your answers decide {change}."
- "We're deciding {change} this {quarter / month}, and we'd rather decide with you than guess."
- "This is a short check-in about {topic} from {sponsor}."
- Formal: "{sponsor} is conducting a study of {topic} among {audience}. Your responses will inform {change}."

Openers that don't work: "We value your opinion" (says nothing), "Dear valued customer" (form letter), "Quick question!" (it is never one question), anything starting with rules ("You must be 18+ and…").

## WIIFM by survey kind

What's in it for me: say what the respondent gets or sees change. Concrete beats vague (`A8_respondent_benefit` level 2 vs 1).

| Kind | Concrete benefit lines | Avoid |
| --- | --- | --- |
| **Customer** (feedback, NPS, CSAT, product research) | "Your answers decide which two features we fix next." · "We'll share what we learned and what we changed in our {results_when} update." · "Tell us what slows you down, and we'll work on that first." | "Help us improve our services." |
| **Employee** (engagement, pulse, exit) | "Results go to the leadership team as themes, never as names, and we'll share them with everyone by {results_when}." · "Last year's survey led to {real change}; this one sets next year's priorities." · "Your manager sees team totals only, and only for teams of 5 or more." | Promising action you can't guarantee; "anonymous" when HR can see names. |
| **Event** (post-event, pre-event) | "Your answers shape the agenda for {next event}." · "Tell us which sessions to keep and which to cut." · "Slides and recordings are on their way; this is how we make the next one better." | "How was it?" with no reason to answer. |
| **Research** (academic, UX, market study) | "Your answers add to {what the study will produce}." · "Results will be published in aggregate in {where}; a summary is available on request from {contact}." · "{incentive} for completing, sent by {delivery}." | Overstating impact ("help cure…"); hiding the sponsor. |
| **Lead-gen** (quiz, assessment, benchmark) | "Get your {score / benchmark / personalised report} at the end." · "See how you compare with {n} other {audience}." · "Answers stay with {sponsor}; we'll email the report only if you ask." | Gating the result behind an email without saying so up front. |

## Privacy one-liners

Say how answers are handled in one line (`A5_privacy_stated`). Pick the one that is **true**. These are plain-language summaries, not legal advice; if you process personal data under GDPR or similar law, link your privacy notice and check with whoever owns data protection.

- Anonymous (no names, emails, phones or tracking links collected): "Anonymous: we don't collect your name or email."
- Anonymous to the team, identified to the tool: "Your answers are not linked to your name in the results."
- Confidential (PII collected): "Confidential: only {team} sees individual answers; results are reported in aggregate."
- With retention: "We keep responses for {period}, then delete them."
- GDPR-friendly (identified data): "{sponsor} uses your answers only for {purpose}. You can ask us to see or delete them at {contact}. Privacy notice: {url}."
- Employee: "Results are reported for groups of 5 or more; nobody sees individual answers."

Never write "anonymous" when the survey asks for an email, phone number, name or uses a personalised link that identifies the respondent (`S21_anonymous_but_pii`). "Confidential" is the honest word then.

## Consent one-liners (research)

For research with people, one line in the welcome (`F2_consent_language`):

- "Taking part is voluntary; you can skip any question or stop at any time."
- "Taking part is voluntary. By continuing, you agree to take part; you can stop at any time without giving a reason."
- Formal: "Participation is voluntary and you may withdraw at any time. Selecting Start indicates your consent to participate."
- If an ethics board approved the study: "Approved by {board}, reference {ref}. Questions about your rights: {contact}."

If the study needs explicit written consent, use a `consent` question as the first entry rather than relying on the welcome text.

## Incentive lines

Mention an incentive only if there is one (`F3a_incentive_mentioned`); always say what, how and when (`F3b_incentive_delivery_clear`), on the welcome **and** the thank-you screen.

- Welcome: "As a thank-you, you'll get a {incentive}, emailed within {n} days of completing."
- Welcome, prize draw: "Complete it by {deadline} to enter a draw for one of {n} {prizes}. Winners are emailed by {date}; terms: {url}."
- Thank-you: "Your {incentive} is on its way: watch for an email from {sender address} within {n} days. Nothing by {date}? Write to {contact}."
- Thank-you, donation: "We've donated {amount} to {charity} for your response."

Be specific about the sender address; vague delivery lines create support emails and spam-folder losses.

## Thank-you patterns

Thanks + what happens next + incentive delivery + contact (`E3_thank_you_quality` level 2, `F3b`, `F5_contact_provided`).

- "Thank you, that's everything. We read every answer, and you'll see what we changed in our {results_when} update. Questions? {contact}"
- "Thanks for your time. Results go to {team} on {date}; we'll share a summary with everyone by {results_when}."
- "All done, thank you. {Incentive delivery line}. Questions or second thoughts? {contact}"
- Research: "Thank you for taking part. If you want a summary of the findings, or want your answers withdrawn, write to {contact} and quote {reference}."

## Contact lines

- "Questions? {contact}"
- "Questions about this survey: {name}, {contact}."
- Email: "Reply to this email; it reaches a person." (only if true)

## Subject-line formulas

≤ 50 characters (about what a phone inbox shows), sentence case, no ALL CAPS, no "URGENT", no emoji. Lead with the time or the outcome.

| Formula | Example |
| --- | --- |
| `{minutes} minutes to shape {thing}` | 3 minutes to shape Acme Invoicing |
| `What should we {decide} next?` | What should we fix next? |
| `Your view on {topic}, by {deadline}` | Your view on the offsite, by Friday |
| `{sponsor} wants your take on {topic}` | Northwind HR wants your take on hybrid work |
| `Help us decide {change}` | Help us decide next year's training |
| `{incentive} for {minutes} minutes of feedback` | A $10 voucher for 5 minutes of feedback |
| Reminder 1: `Still open: {topic} survey` | Still open: Acme Invoicing survey |
| Reminder 1: `Halfway there: {n} replies so far` (true numbers only) | Halfway there: 212 replies so far |
| Reminder 2: `{topic} survey closes tonight` | Acme survey closes tonight |
| Reminder 2: `Last day to share your view on {topic}` | Last day to share your view on the offsite |

## Reminder rules

- Day 3 ("halfway"): restate the why, not the ask. One new detail helps (replies so far, a deadline that is getting closer).
- Last day ("closes tonight"): one sentence on the deadline, one on the why, the link. Send in the morning of the closing day.
- Send to non-respondents only; if the tool cannot filter, add "If you've already answered, thank you, and please ignore this."
- Two reminders is the norm; a third rarely earns its unsubscribes.
- No deadline? Don't invent one. Reminder 2 becomes "A final reminder: {why}. {link}".

## SMS and chat

≤ 160 characters including the link and, for SMS, the opt-out the channel requires.

- "{sponsor}: {minutes}-min survey on {topic}. Your answers decide {change}. {link} Reply STOP to opt out"
- Chat (Slack / Teams): "Hi team, {sponsor} here. {minutes}-minute {privacy} survey on {topic}, open until {deadline}: {link}. Results shared {results_when}."

## Tone

| Tone | Use for | Signs |
| --- | --- | --- |
| warm | customers, events, communities | contractions, "you" and "we", one friendly line, first names |
| neutral | employees, general feedback, B2B users | plain sentences, no exclamation marks, no jokes |
| formal | academic research, healthcare, government, senior executives | no contractions, full names and titles, "participate", ethics references |

Tone changes the wording, never the facts or the limits.

## Words to avoid

Pressure, guilt, flattery and fake urgency bias answers and cost trust (`F4_manipulative_framing`, `L_pressuring`).

| Avoid | Why | Instead |
| --- | --- | --- |
| "It only takes a second", "quick" (when it is 5 minutes) | False; people notice and quit | "Takes about {minutes} minutes" |
| "Last chance!", "Hurry", "Only today" (when untrue) | Fake urgency | "Closes {deadline}" |
| "We're counting on you", "Don't let us down" | Guilt | "Your answers decide {change}" |
| "As one of our most valued customers…" | Flattery reads as a form letter | Say why they in particular were asked |
| "URGENT", ALL CAPS, "!!!", emoji in subjects | Spam filters and shouting (`S42`) | Sentence case |
| "Help us improve" (alone) | Vague benefit, `A8` level 1 | Name the concrete change |
| "Survey" as the whole subject ("Customer survey") | Says nothing about why it is worth opening | Lead with the outcome or time |
| "Anonymous" when you collect an email | Untrue (`S21`) | "Confidential" + who sees it |
| "Tell us how great we did" | Leading | "Tell us how it went" |
| "Required", "mandatory", "must" in the welcome | A bouncer, not a host (`E4` level 0) | Put rules after the why, briefly |

## Before / after

**Before** (welcome, 63 words; scores A3 1, A8 0, A9 no, A5 no, E4 0, E7 0):

> PLEASE COMPLETE THIS SURVEY. All fields are mandatory. This survey is about our services and it only takes a second. We value your opinion and are counting on your participation. Your responses will be used for internal purposes. The survey must be completed by all customers who received this email. Thank you in advance for your cooperation and for being a valued customer!

Problems: no sponsor, no reason, rules first, shouting, "only takes a second" with no real time, guilt and flattery, nothing on privacy, no deadline or contact.

**After** (50 words; A3 3, A8 2, A9 yes, A5 yes, A10 yes, F5 yes, E4 2, E7 2):

> We're the Acme support team, and we want to hear from customers who contacted us this month. Your answers decide which two support problems we fix first; we'll share what changed in June.
> • Takes about 4 minutes
> • Confidential: only the support team sees answers
> • Open until 20 May. Questions? support-research@acme.example
