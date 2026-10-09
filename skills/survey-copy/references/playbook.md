# Survey playbook

Rules to write by. This is the [rubric](rubric.md) and the [static checks](static-checks.md) turned inside out: every rule names the ids it satisfies, so a survey written by these rules scores well by construction. Sections follow the respondent's path (the funnel): **start** (will they click Start?) → **continue** (will they get past the first three questions?) → **finish** (will they reach Submit?) → **answer quality** (are the answers usable?) → **actionability** (can you decide from them?).

Format: `- **Rule.** Why. (satisfies ids)`. Defaults are for a general audience on a phone; a rule can bend when the brief says so, but say why.

## 1. Decide before you write

- **Write the decision first.** One sentence: "After this survey I will decide ___." Every question must serve it. A survey without a decision collects trivia. (satisfies A7_objective_inferable, C1_objective_coverage, Q5_relevance, Q23_actionable)
- **Name the kind.** research, feedback, form, quiz, assessment or information. It decides which checks apply (a form needs no outcome question) and the scoring weights. (satisfies K_survey_kind)
- **Name the audience precisely.** "Small-business owners who invoiced with us in the last 3 months", not "users". It sets the screener, the vocabulary and the tone. (satisfies X2_audience_kind, A6_audience_stated, Q4_jargon)
- **List the 3–5 things the decision needs to know** and give each at least one question. Then ask: what would a colleague expect this survey to cover? (satisfies C1_objective_coverage, C5_obvious_gap, C5_gap_topic)
- **Include one direct outcome question** (overall satisfaction, NPS, intent, preference) for research and feedback. Without it you have context and no verdict. (satisfies C3_has_outcome_question, Q24_intent)
- **Give every entry a role.** A question collects an answer; a statement informs; a consent asks for agreement. Don't disguise a statement as a question. (satisfies R_role, Q24_intent)

## 2. Title

- **Say what it is about and what it is for, to the respondent.** "Help shape Acme Invoicing: 3-minute customer check-in", not "Q3 Invoicing Survey v2". (satisfies A1_title_specific, A2_title_respondent_facing)
- **Never leave it empty.** No title is a blocker. (satisfies S01_no_title)

## 3. Welcome screen

The welcome screen decides whether people start. Keep it under 120 words, scannable on a phone: one short paragraph plus bullets.

- **Lead with why their input matters and what changes because of it.** "Your answers decide what we fix next; we'll share results in May." (satisfies A3_purpose_explained, A8_respondent_benefit, E4_welcome_motivates)
- **Say who is asking.** Name the team or organisation; anonymous senders read as phishing. (satisfies A9_sponsor_named)
- **Say who it is for.** "For anyone who has invoiced with Acme in the last 3 months." (satisfies A6_audience_stated)
- **State the time honestly** and set `settings.stated_minutes` to match the estimate in [question-types.md](question-types.md#seconds-per-type). (satisfies S15_no_time_expectation, S16_time_mismatch)
- **Say how answers are handled**: anonymous or not, who sees them, how long they are kept. (satisfies A5_privacy_stated)
- **For research: consent in one line.** "Taking part is voluntary; you can stop at any time." (satisfies F2_consent_language)
- **Give a closing date when there is one**, honestly; no fake urgency. (satisfies A10_deadline_stated, F4_manipulative_framing)
- **Give a contact.** "Questions? research@acme.example". (satisfies F5_contact_provided)
- **If there is an incentive, say what, how and when** it is delivered (and repeat it on the thank-you screen). (satisfies F3a_incentive_mentioned, F3b_incentive_delivery_clear, F3_incentive_clear)
- **Motivate with purpose, never pressure.** No guilt, flattery or "it only takes a second". (satisfies F4_manipulative_framing, L_pressuring)
- **Keep it short and scannable.** Purpose, time and privacy each findable at a glance; ≤ 120 words. (satisfies E7_welcome_scannable, S50_welcome_too_long, S07_no_description, S08_no_welcome)
- **Don't promise anonymity and then ask for an email.** Either drop the identifying questions or drop the promise. (satisfies S21_anonymous_but_pii)

## 4. The first three questions

Most drop-off happens here. Earn trust before asking for effort or personal data.

- **Open with an easy, on-topic, closed question.** One click, clearly about the topic in the title. (satisfies B2_opening_question, S46_first_question_open_text)
- **Nothing demanding and required in the first three**: no required long text, file upload, email, phone, grid or ranking. (satisfies S51_early_friction, Q15_abandon_risk)
- **Ask for contact details after the content, never before.** Ask for an email only once you've asked what they think, and make it optional. (satisfies S48_pii_before_content, Q15_abandon_risk)
- **Demographics go last** (see §11). (satisfies B3_demographics_placement, L_is_demographic)

## 5. Screener and routing

- **Screen when the audience is specific.** One qualifying question early (for research, required). (satisfies C2_has_screener)
- **Give the screener an exit.** A jump to `end` (or to a short "thanks, this one isn't for you" statement) for non-qualifiers; otherwise they answer questions that don't apply. (satisfies S41_screener_without_exit)
- **Gate every follow-up that only applies after a specific answer** with `shown_when`, e.g. `"Q3 <= 6"` for "What's the main reason for your score?". Or give it an option for those it doesn't apply to ("I don't use it"). (satisfies Q10_depends_on_prior, S22_conditional_without_logic, Q3b_presuming)
- **Don't presume.** Ask "Do you use the mobile app?" before "How often do you use the mobile app?" and gate the second. (satisfies Q3b_presuming)
- **Check every question is reachable.** A default jump that skips a block with nothing jumping into it leaves dead questions. (satisfies S28_unreachable_question)
- **Branch long surveys** so most people see fewer questions. Over 30 questions with no logic means everyone gets everything. (satisfies S47_no_logic_long_survey)

## 6. Structure and flow

- **Group by topic; order general → specific and easy → demanding.** (satisfies B1_logical_order, L_topic_jump)
- **Signpost each topic change** with a short statement or a group title: "Next, a few questions about getting paid." (satisfies B4_sections_signposted)
- **Ask each thing once.** Merge near-duplicates; identical labels are never right unless one is a gated follow-up. (satisfies B5_redundant_questions, L_duplicate_of_earlier, S10_duplicate_labels)
- **Keep the end light.** Don't save the essays, big grids and rankings for last; end on something quick. (satisfies B7_end_loading)
- **Vary the format.** Never 8+ questions of the same type in a row; never two grids back to back. (satisfies S27_monotony_run, S31_consecutive_matrices, E8_straightlining_risk)
- **Groups hold at least two questions** and are never empty. (satisfies S44_group_single_child, S06_group_empty)
- **One voice throughout**: "you", one level of formality, one language, one spelling system. (satisfies E1_tone_consistent, E9_language_consistent)

## 7. Writing each question

- **One question, one meaning, one sentence**, under 35 words; context goes in `description`. (satisfies Q1_clarity, S43_label_too_long, S03_label_empty)
- **One thing per question.** "How fast and friendly was support?" is two questions. Watch for "and", "or", "and if so". (satisfies Q2_double_barreled)
- **Neutral wording.** "How satisfied or dissatisfied are you…", not "How much do you love…". Avoid obviously, clearly, don't you agree, always, never, should. (satisfies Q3a_leading, S35_loaded_words)
- **Plain words.** Define any term the audience might not know, inline or in the description. (satisfies Q4_jargon, E5_reading_level, L_hard_to_read)
- **Positive phrasing on agree/disagree items.** No "I do not find it hard to…". (satisfies Q17_negative_wording)
- **Ask about behaviour and experience, not hypotheticals**, when it is the outcome. "Did you…" / "How satisfied are you…" over "Would you…". (satisfies Q18_hypothetical)
- **Give a recall window** for anything over time: "in the last 30 days", "at your last visit". (satisfies Q19_recall_period)
- **Ask for what people know offhand.** Offer ranges or "Not sure" instead of exact figures and dates. (satisfies E2_burden, L_hard_to_recall)
- **State units and formats**: "in £ per month", "hours per week", "DD/MM/YYYY". (satisfies Q22_units_stated)
- **Defuse socially desirable answers** with indirect or normalising wording: "Some people find time to recycle, others don't. How about you?" (satisfies Q21_social_desirability)
- **Proofread** every label, description and option. (satisfies Q13_grammar)
- **No shouting.** Sentence case, one question mark, words (not emoji) in options. (satisfies S42_shouting_or_noise)
- **Every question needs a stated use.** If you can't write the analysis you'd run on it, cut it. (satisfies Q23_actionable, Q5_relevance)

## 8. Options

| Rule | Why | Satisfies |
| --- | --- | --- |
| Cover everyone: add "Other (please specify)", "None of these", "Not sure" or "Prefer not to answer" where someone might not fit. | People with no fitting option guess or quit. | Q6_options_not_exhaustive |
| Make single-choice options mutually exclusive. | Overlaps make the data unclean. | Q7_options_overlap |
| Numeric buckets cover every value exactly once: `Under 25`, `25–34`, `35–44`, `45 or more`. | "Under 25" then "26–35" loses every 25-year-old. | S12_numeric_range_gap |
| One idea per option ("Fast", "Affordable", not "Fast and affordable"). | People feel differently about each half. | Q20_option_double_barreled |
| Same grammatical form, case and length for every option. | Parallel options are faster to scan. | Q14_options_parallel |
| No duplicate options. | Obvious carelessness; splits the data. | S11_duplicate_options |
| At least two options on every choice question. | One option is not a choice. | S04_options_too_few |
| "None of the above" on a multi-select is exclusive (`has_none` or `exclusive_options`). | Otherwise it can be ticked with "Option B". | S38_none_not_exclusive |
| "Other" uses `has_other` (with a text box), not a plain option. | A bare "Other" tells you nothing. | S39_other_without_text |
| More than 6 unordered options: `randomize_options: true` ("Other"/"None" stay last). | The first options get picked more. | S40_long_list_not_randomised |
| More than 10 options: use a `dropdown`. | Radio lists that long are a scroll, not a choice. | S33_long_radio_list |
| Multi-select with a pick limit: state it in the label and set `selection.min/max`; never make `min` more than the options. | Unenforced limits are ignored; impossible ones block submission. | S14_selection_count_unenforced, S04_options_too_few |
| Sensitive questions: add "Prefer not to say" or make them optional. | A required personal question with no way out is a quit point. | Q12_sensitive, S23_sensitive_without_optout |

## 9. Scales

| Rule | Why | Satisfies |
| --- | --- | --- |
| Balanced: as many negative as positive points, with a neutral midpoint where a neutral answer is real. | Lopsided scales lean the results. | Q8_scale_unbalanced |
| Fully labelled on 5-point scales (every point), or at least the midpoint on 7+ points. | Endpoint-only scales drift; people read the middle differently. | S36_scale_endpoints_only |
| Same direction everywhere (e.g. negative → positive, left → right). | Autopilot respondents answer a reversed scale backwards. | B8_scale_direction_consistent |
| NPS exactly: 0–10, "How likely are you to recommend [X] to a friend or colleague?", endpoints "Not at all likely" / "Extremely likely". | Non-standard NPS can't be compared with anyone else's. | S37_nps_nonstandard |
| Grids: at most 5 columns and 8 rows; never two in a row; break batteries with another type. | Big grids are unusable on a phone and invite straight-lining. | S30_matrix_too_large, S31_consecutive_matrices, E8_straightlining_risk |
| Every grid has rows and columns. | An empty grid blocks the survey. | S05_matrix_empty |
| Long surveys (25+ questions): one attention check ("Select 'Agree' for this row") or a consistency pair. | Lets you drop autopilot answers. | C7_has_attention_check |

## 10. Choosing the type

Full table and platform names in [question-types.md](question-types.md).

| The question asks for… | Use |
| --- | --- |
| one of a few known answers | `single_choice` |
| one of many known answers (8+, countries) | `dropdown` |
| every answer that applies | `multi_choice` + exclusive "None of these" |
| a yes/no fact ("Do you…?") | `yes_no` |
| satisfaction / agreement | `likert` (5 points, labelled) or `rating` |
| likelihood to recommend | `nps` (0–10) |
| the same scale on several items | `matrix` (≤ 5 × 8) |
| an order of preference | `ranking` (≤ 7 items) |
| an amount | `number` + unit |
| a date | `date` + format |
| a reason in their own words | optional `long_text` after the closed question |
| a short free answer that can't be listed | `short_text` |
| contact details | optional `email` / `phone`, at the end |

- **Match the type to the wording.** "Select all that apply" needs `multi_choice`; "select one" needs `single_choice`; "why?" needs text. (satisfies Q9_type_fit, Q25_best_type, S13_selection_hint_type_mismatch)
- **A `yes_no` must read as yes/no** ("Do / Are / Have / Can…?"). (satisfies S45_yesno_type_mismatch)
- **Closed beats open for anything you can list.** "Which country?" as free text gives you 'london', 'London' and 'Londn'. (satisfies Q25_best_type)
- **Rank at most 7 items**, or ask for the top 3. (satisfies S32_ranking_too_many)

## 11. Length and effort

| Budget (default) | Limit | Satisfies |
| --- | --- | --- |
| Time | ≤ 10 minutes; 3–5 is best for feedback | E6_length_feels_justified, S16_time_mismatch |
| Answerable questions | ≤ 20 (hard ceilings: 30 medium, 50 high) | E6_length_feels_justified, S17_length_fatigue |
| Open-ended | ≤ 30 % of questions and ≤ 3 required; placed late | S34_open_ended_overload, B7_end_loading |
| At least one open question | when > 15 questions (research, feedback) | S19_no_open_ended |
| Required | only what the decision needs; < 80 % when > 15 questions | S18_all_required_long |
| Progress bar | on when > 20 questions | S24_no_progress_bar_long |
| Welcome text | ≤ 120 words | S50_welcome_too_long |
| Label | ≤ 35 words | S43_label_too_long |
| Grid | ≤ 5 columns, ≤ 8 rows | S30_matrix_too_large |
| Ranking | ≤ 7 items | S32_ranking_too_many |
| Radio list | ≤ 10 options | S33_long_radio_list |

- **Shortest survey that answers the decision.** Every non-essential question is paid for in drop-offs. (satisfies E6_length_feels_justified, Q23_actionable)
- **Ask "why" where it matters.** One optional "What's the main reason?" after the two or three most decision-relevant closed questions. (satisfies C4_missing_why, L_needs_why)
- **Make questions optional by default**; require only what you can't analyse without. (satisfies S18_all_required_long, Q15_abandon_risk)

## 12. Demographics and sensitive questions

- **Demographics last, with a reason.** "So we can compare answers across business sizes." (satisfies B3_demographics_placement, L_is_demographic)
- **Only the demographics you will cut the data by.** Every extra one costs completions and trust; too many reads as a census. (satisfies C6_demographics_proportionate, Q24_intent)
- **Sensitive questions** (income, health, ethnicity, religion, sexuality, legal, precise location): optional or with "Prefer not to say", plus one line on why it is asked and who sees it. (satisfies F1_sensitive_topics, Q12_sensitive, Q16_sensitive_reassured, S23_sensitive_without_optout, L_sensitive_topic)
- **Identifying data only when needed, and never on an anonymous survey.** (satisfies S21_anonymous_but_pii, S48_pii_before_content)

## 13. Thank-you screen

- **Thank them and say what happens next**: when results are shared, what will change, when an incentive arrives. (satisfies E3_thank_you_quality, S09_no_thank_you)
- **Repeat the incentive delivery** (how and when) if there is one. (satisfies F3b_incentive_delivery_clear)
- **Give the contact again.** (satisfies F5_contact_provided)

## 14. Mobile and accessibility

- **Design for a phone first**: small grids (≤ 5 × 8), rankings ≤ 7, dropdowns for long lists, short labels. (satisfies S30_matrix_too_large, S32_ranking_too_many, S33_long_radio_list, S43_label_too_long)
- **No image-only questions.** If a question depends on an image, describe it in the text; if it mentions an image, attach it. (satisfies Q11_requires_visual, S25_visual_not_described, S26_visual_missing)
- **Readable by everyone**: plain language, no ALL CAPS, words not emoji. (satisfies E5_reading_level, S42_shouting_or_noise)

## Roast voice

The report's roasts are a feature, and every skill should sound the same. Be **specific** (name the question and quote the words), **honest** (say what will actually go wrong: drop-offs, unusable data), **witty** (one dry line is enough: "That's not a survey, that's a shift."), and **never cruel** (mock the survey, never the author; no insults, no sarcasm about effort). Each roast is followed by a fix the author can apply in under a minute. In `--polite` mode, drop the joke and keep the fact and the fix.

## Pre-flight checklist

`survey-create` runs this before handing a survey over (and `survey-fix` after patching). One line per id, by funnel stage. Locators (`L_*`) are covered by the item they locate.

### Decide

- [ ] K_survey_kind: kind chosen (research / feedback / form / quiz / assessment / information) and set in `kind`.
- [ ] X2_audience_kind: audience named precisely in `audience`.
- [ ] R_role: every entry is a question, information or consent, and set as such.
- [ ] C5_gap_topic: compared the list against what the audience would expect; nothing obvious missing.

### Start

- [ ] S01_no_title: title present.
- [ ] A1_title_specific: title names the topic and its purpose.
- [ ] A2_title_respondent_facing: title addresses the respondent, not an internal project name.
- [ ] S02_no_questions: at least one answerable question.
- [ ] S07_no_description: description or welcome text present.
- [ ] S08_no_welcome: welcome screen present.
- [ ] A3_purpose_explained: welcome says the topic, why it matters, how answers are used.
- [ ] A8_respondent_benefit: welcome says what the respondent gets or what changes.
- [ ] A9_sponsor_named: the team or organisation is named.
- [ ] A6_audience_stated: welcome says who it is for.
- [ ] A5_privacy_stated: welcome says how answers are handled.
- [ ] A10_deadline_stated: closing date stated (if there is one).
- [ ] F2_consent_language: voluntary / can stop at any time (research).
- [ ] F5_contact_provided: a contact is given.
- [ ] F3_incentive_clear: incentive, if any, is clear.
- [ ] F3a_incentive_mentioned: incentive mentioned only if there really is one.
- [ ] F3b_incentive_delivery_clear: incentive says how and when it is delivered.
- [ ] E4_welcome_motivates: welcome leads with why their input matters.
- [ ] E7_welcome_scannable: purpose, time and privacy findable at a glance.
- [ ] S50_welcome_too_long: welcome ≤ 120 words.
- [ ] S15_no_time_expectation: `settings.stated_minutes` set and time stated.
- [ ] S16_time_mismatch: stated time matches the estimate.
- [ ] S21_anonymous_but_pii: no PII on an anonymous survey.

### Continue

- [ ] B2_opening_question: first question easy, on-topic, closed.
- [ ] S46_first_question_open_text: first question is not open text.
- [ ] S51_early_friction: nothing demanding and required in the first three.
- [ ] Q15_abandon_risk: no required, intrusive or heavy question early.
- [ ] S48_pii_before_content: contact details come after the first outcome question.
- [ ] B3_demographics_placement: demographics at the end, with a reason.
- [ ] C6_demographics_proportionate: only the demographics the analysis needs.
- [ ] F1_sensitive_topics: sensitive topics identified, each with a privacy line.
- [ ] Q12_sensitive: sensitive questions can be declined.
- [ ] Q16_sensitive_reassured: sensitive questions say why and who sees the answer.
- [ ] S23_sensitive_without_optout: no required sensitive question without "Prefer not to say".

### Finish

- [ ] B1_logical_order: grouped by topic, general → specific, easy → demanding.
- [ ] B4_sections_signposted: topic changes are signposted.
- [ ] B5_redundant_questions: nothing asked twice.
- [ ] S10_duplicate_labels: no identical labels.
- [ ] B7_end_loading: the end is not the hardest part.
- [ ] E1_tone_consistent: one voice throughout.
- [ ] E6_length_feels_justified: length fits the purpose (≤ 20 questions, ≤ 10 min by default).
- [ ] E8_straightlining_risk: no long runs of look-alike items.
- [ ] S17_length_fatigue: ≤ 30 answerable questions (or a reason).
- [ ] S18_all_required_long: not almost everything required.
- [ ] S24_no_progress_bar_long: progress bar on for long surveys.
- [ ] S27_monotony_run: no 8+ same-type run.
- [ ] S28_unreachable_question: every question reachable.
- [ ] S30_matrix_too_large: grids ≤ 5 columns, ≤ 8 rows.
- [ ] S31_consecutive_matrices: no grids back to back.
- [ ] S32_ranking_too_many: rankings ≤ 7 items.
- [ ] S33_long_radio_list: radio lists ≤ 10 options.
- [ ] S34_open_ended_overload: open text ≤ 30 % and ≤ 3 required.
- [ ] S43_label_too_long: labels ≤ 35 words.
- [ ] S44_group_single_child: no single-question groups.
- [ ] S06_group_empty: no empty groups.
- [ ] S47_no_logic_long_survey: long surveys branch.
- [ ] E3_thank_you_quality: thank-you says what happens next.
- [ ] S09_no_thank_you: thank-you screen present.

### Answer quality

- [ ] Q1_clarity: every label clear, one meaning.
- [ ] Q2_double_barreled: one thing per question.
- [ ] Q3a_leading: neutral wording.
- [ ] Q3b_presuming: no unestablished assumptions.
- [ ] Q4_jargon: no unexplained jargon.
- [ ] Q13_grammar: proofread.
- [ ] Q17_negative_wording: no negative or double-negative items.
- [ ] Q19_recall_period: time windows on behaviour questions.
- [ ] Q21_social_desirability: no obvious "right" answer.
- [ ] Q22_units_stated: units and formats stated.
- [ ] E2_burden: nothing people can't answer offhand.
- [ ] E5_reading_level: plain language.
- [ ] E9_language_consistent: one language, one spelling system.
- [ ] F4_manipulative_framing: no pressure, guilt or flattery.
- [ ] Q6_options_not_exhaustive: options cover everyone.
- [ ] Q7_options_overlap: single-choice options exclusive.
- [ ] Q14_options_parallel: options parallel.
- [ ] Q20_option_double_barreled: one idea per option.
- [ ] Q8_scale_unbalanced: scales balanced.
- [ ] B8_scale_direction_consistent: all scales run the same way.
- [ ] Q9_type_fit: type matches the wording.
- [ ] Q10_depends_on_prior: conditional questions are gated or have a "not applicable" option.
- [ ] S22_conditional_without_logic: no ungated conditional question.
- [ ] Q11_requires_visual: no question depends on an undescribed visual.
- [ ] S25_visual_not_described: images are described in text.
- [ ] S26_visual_missing: referenced images are attached.
- [ ] C7_has_attention_check: attention check on 25+ question surveys.
- [ ] S03_label_empty: no empty labels.
- [ ] S04_options_too_few: every choice question has 2+ options; pick limits possible.
- [ ] S05_matrix_empty: every grid has rows and columns.
- [ ] S11_duplicate_options: no duplicate options.
- [ ] S12_numeric_range_gap: numeric buckets have no gaps or overlaps.
- [ ] S13_selection_hint_type_mismatch: "select all"/"select one" matches the type.
- [ ] S14_selection_count_unenforced: pick limits set when stated.
- [ ] S35_loaded_words: no loaded words.
- [ ] S36_scale_endpoints_only: 7+ point scales labelled beyond the endpoints.
- [ ] S37_nps_nonstandard: NPS is 0–10 with standard wording.
- [ ] S38_none_not_exclusive: "None" is exclusive.
- [ ] S39_other_without_text: "Other" has a text box.
- [ ] S40_long_list_not_randomised: long unordered lists randomised.
- [ ] S42_shouting_or_noise: no caps, "??", "!!!" or emoji-only options.
- [ ] S45_yesno_type_mismatch: yes/no questions read as yes/no.

### Actionability

- [ ] A7_objective_inferable: one decision evident from the questions.
- [ ] C1_objective_coverage: every need of the purpose has a question.
- [ ] C2_has_screener: screener present (research with a specific audience).
- [ ] S41_screener_without_exit: the screener has an exit.
- [ ] C3_has_outcome_question: a direct outcome question (research, feedback).
- [ ] C4_missing_why: "why" follow-ups on the key closed questions.
- [ ] C5_obvious_gap: nothing obviously missing.
- [ ] Q5_relevance: every question serves the purpose.
- [ ] Q18_hypothetical: the outcome is not only a hypothetical.
- [ ] Q23_actionable: every question informs a decision.
- [ ] Q24_intent: `intent` set on each question; outcome present and early enough; demographics ≤ 25 %.
- [ ] Q25_best_type: each question uses the most analysable type.
- [ ] S19_no_open_ended: one optional open question (research, feedback, > 15 questions).
