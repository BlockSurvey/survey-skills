# Judging guide (`bs-skills-1.0`)

A one-line cheat sheet for every rubric item, so you can judge a whole survey in one pass. The full wording, criteria, severities and roasts are in [rubric.md](rubric.md); open it only when a line here leaves you unsure.

How to answer:

- **score `0–N`**: an integer `level`, 0 = worst. Pick the level whose description matches the situation; do not average. Add `confidence` (0–1).
- **p**: a calibrated probability that the question in the line is **true**. 0.9 = clearly yes, 0.5 = unsure, 0.1 = clearly no. Most items: yes = problem. Items marked **(yes = good)** are the reverse.
- **choice**: one key from the list.
- `note`: ≤ 200 characters, quote the survey words that decided it.

## Classify first (survey level)

| id | answer | ask yourself |
| --- | --- | --- |
| `K_survey_kind` | choice | What is this? `research` · `feedback` · `form` · `quiz` · `assessment` · `information`. Also write it as top-level `survey_kind`. |
| `X2_audience_kind` | choice | Who answers? `existing_customers` · `prospects_or_general_public` · `employees` · `students` · `experts_or_professionals` · `event_attendees` · `unclear`. Also top-level `audience_kind`. |
| `C5_gap_topic` | choice | Which expected topic is most clearly absent? `none` or one key from rubric.md §Gap topics (e.g. `pricing`, `satisfaction`, `open_feedback`). |

## A. Purpose & framing (survey level)

| id | answer | ask yourself |
| --- | --- | --- |
| `A1_title_specific` | score 0–2 | Does the title say what it is about? 0 generic/internal · 1 topic only · 2 topic + purpose. |
| `A2_title_respondent_facing` | score 0–2 | Written for the respondent? 0 internal name ("v2", "draft", "new product") · 1 neutral · 2 invites them. |
| `A3_purpose_explained` | score 0–3 | Description + welcome: 0 no purpose · 1 topic only · 2 + why answers matter · 3 + how answers are used. |
| `A5_privacy_stated` | p (yes = good) | Does any intro text say how data is handled (anonymous, confidential, who sees it)? |
| `A6_audience_stated` | p (yes = good) | Does the intro say who the survey is for? |
| `A7_objective_inferable` | score 0–2 | From the questions alone: 0 no coherent aim · 1 broad theme · 2 a specific decision is evident. *research, feedback only.* |
| `A8_respondent_benefit` | score 0–2 | What do they get? 0 nothing, just a time ask · 1 "help us improve" · 2 concrete outcome or reward. |
| `A9_sponsor_named` | p (yes = good) | Is the organisation, team or person running it named? |
| `A10_deadline_stated` | p (yes = good) | Is a closing date or "respond by" stated? |

## B. Structure & flow (survey level)

| id | answer | ask yourself |
| --- | --- | --- |
| `B1_logical_order` | score 0–2 | Top to bottom: 0 topics scattered · 1 mostly grouped, some jumps · 2 grouped, general → specific. |
| `B2_opening_question` | score 0–2 | First answerable question: 0 personal/sensitive, unexplained · 1 neutral but dull · 2 easy and on-topic. |
| `B3_demographics_placement` | score 0–2 | 0 several at the start, no reason · 1 brief at start or mid-survey · 2 at the end, explained, or none. |
| `B4_sections_signposted` | p (yes = good) | When the topic changes, is there a statement or section title signalling it? (p 0.9 if it never changes topic.) |
| `B5_redundant_questions` | p | Do two questions collect the same information? |
| `B7_end_loading` | score 0–2 | Last third: 0 the hardest items piled at the end · 1 one demanding item at the end · 2 end is easy. |
| `B8_scale_direction_consistent` | p | Do any two scales run in opposite directions (good→bad vs bad→good)? p 0.05 if fewer than two scales. |

## C. Coverage & gaps (survey level)

| id | answer | ask yourself |
| --- | --- | --- |
| `C1_objective_coverage` | score 0–3 | Against the stated purpose: 0 barely touched · 1 major aspects missing · 2 minor missing · 3 thorough. |
| `C2_has_screener` | p (yes = good) | Is there a question that confirms the respondent is in the target audience? *research only.* |
| `C3_has_outcome_question` | p (yes = good) | Is there a direct outcome measure (satisfaction, intent, likelihood, preference, decision)? *research, feedback.* |
| `C4_missing_why` | p | Are there decision-relevant closed questions with no "why?" follow-up or free text? *research, feedback.* |
| `C5_obvious_gap` | score 0–2 | 0 a major expected topic absent · 1 a minor one absent · 2 nothing missing. Name it in `C5_gap_topic`. *research, feedback, assessment.* |
| `C6_demographics_proportionate` | score 0–2 | 0 demographics the purpose doesn't need (or none when needed) · 1 one or two off · 2 just right. *research, feedback.* |
| `C7_has_attention_check` | p (yes = good) | Is there an instructed-response item or consistency pair? Only counts when > 25 answerable questions. |

## E. Respondent experience (survey level)

| id | answer | ask yourself |
| --- | --- | --- |
| `E1_tone_consistent` | score 0–2 | Voice and formality across screens: 0 feels like several authors · 1 a few slips · 2 consistent. |
| `E2_burden` | p | Does any question make people recall, look up or calculate something they won't know offhand? |
| `E3_thank_you_quality` | score 0–2 | 0 missing or bare · 1 thanks them · 2 thanks + what happens next. |
| `E4_welcome_motivates` | score 0–2 | 0 cold, rules first · 1 polite but flat · 2 says why their input matters, friendly. |
| `E5_reading_level` | score 0–2 | For a general adult: 0 dense throughout · 1 some heavy passages · 2 plain throughout. |
| `E6_length_feels_justified` | score 0–2 | Question count vs purpose: 0 far too long · 1 somewhat long · 2 appropriate. |
| `E7_welcome_scannable` | score 0–2 | On a phone: 0 dense paragraphs, key facts buried · 1 readable but long · 2 short; purpose, time, privacy each findable. |
| `E8_straightlining_risk` | score 0–2 | 0 long runs of look-alike scales/matrix rows · 1 some repeats, broken up · 2 formats vary. |
| `E9_language_consistent` | p | Mixed languages or spelling systems (colour/color) a respondent would notice? |

## F. Trust & ethics (survey level)

| id | answer | ask yourself |
| --- | --- | --- |
| `F1_sensitive_topics` | p | Does the survey ask about finances, health, ethnicity, religion, sexuality, legal issues or precise location? (info only.) |
| `F2_consent_language` | p (yes = good) | Is there consent language (voluntary, can stop, continuing = agreeing)? *research only.* |
| `F3a_incentive_mentioned` | p | Is an incentive, reward, prize draw or payment mentioned anywhere? |
| `F3b_incentive_delivery_clear` | p (yes = good) | If one is mentioned, does it say how and when they receive it? (Judge it anyway; code uses it only when F3a ≥ 0.7.) |
| `F3_incentive_clear` | skip | Superseded by F3a + F3b. Do not judge. |
| `F4_manipulative_framing` | p | Does any text pressure toward an answer or toward completing (guilt, urgency, flattery)? |
| `F5_contact_provided` | p (yes = good) | Is there a way to contact the owner (email, name, link)? |

## Per question (judge on each question where it applies)

`applies` shorthand: **all**; **opts** = has options or columns; **single** = options + type single_choice/dropdown/yes_no/consent; **scale** = rating/nps/likert/slider/matrix (or single_choice/dropdown with 3+ options) **and** has options or columns; **qty** = number/slider/date/short_text.

| id | applies | answer | ask yourself |
| --- | --- | --- | --- |
| `R_role` | all | choice | `question` (collects data) · `information` (tells or explains) · `consent` (asks agreement). Decides what else applies. |
| `Q1_clarity` | all | score 0–3 | 0 two readers could read it differently · 1 needs a re-read · 2 clear · 3 clear, concise, specific. Info/consent: is the next action clear? |
| `Q2_double_barreled` | all | p | Does it ask two things someone could answer differently ("X and Y", "do you have X, and if so…")? |
| `Q3a_leading` | all | p | Does the wording push toward one answer ("how much do you love…", "don't you agree")? |
| `Q3b_presuming` | all | p | Does it assume a fact about the respondent that nothing earlier establishes? Skip when `shown_when` is set. |
| `Q4_jargon` | all | score 0–2 | 0 unexplained specialist terms/acronyms · 1 terms explained · 2 plain only (also 2 for "have you heard of X?"). |
| `Q5_relevance` | all | score 0–2 | 0 unrelated to the purpose · 1 loosely related · 2 directly serves it. Skip when `shown_when` names an earlier ref. |
| `Q6_options_not_exhaustive` | opts | p | Could a plausible respondent find no option that fits (no Other/None/Not sure/Prefer not)? |
| `Q7_options_overlap` | single | p | Could someone truthfully pick two options when only one is allowed? |
| `Q8_scale_unbalanced` | scale | p | More positive than negative points (or no midpoint where one is expected)? p 0.05 if not an ordered scale. |
| `Q9_type_fit` | all | score 0–2 | 0 type contradicts the wording ("select all" but single pick) · 1 workable, a better type exists · 2 fits. |
| `Q10_depends_on_prior` | all | p | Is it only for people who gave a specific earlier answer ("If yes…"), with no option for everyone else? |
| `Q11_requires_visual` | all | p | Can it only be answered by looking at an image, screen or video not described in the text? |
| `Q12_sensitive` | all | p | Sensitive personal data (income, health, ethnicity, identifiers) with no option to decline? |
| `Q13_grammar` | all | score 0–2 | 0 errors that hurt understanding · 1 minor slips · 2 clean (label, description, options). |
| `Q14_options_parallel` | opts | p | Are the options written in mismatched forms (case, tense, fragments vs sentences)? |
| `Q15_abandon_risk` | all | score 0–2 | Would people quit here? 0 demanding or intrusive **and** required · 1 one of those but optional, or mild and required · 2 quick. |
| `Q16_sensitive_reassured` | all | p (yes = good) | Does it say why a sensitive answer is needed, that it's optional, or who sees it? (Only used when Q12 ≥ 0.7.) |
| `Q17_negative_wording` | scale | p | Is it phrased negatively or with a double negative, so "agree" means the opposite of what it sounds like? |
| `Q18_hypothetical` | all | p | Does it ask what they *would* do in a situation they haven't been in? (info; feeds an outcome rule.) |
| `Q19_recall_period` | all | choice | `stated` (time window given) · `missing_but_needed` (frequency/experience over time, no window) · `not_applicable`. |
| `Q20_option_double_barreled` | opts | p | Does any option bundle two things ("Fast and affordable")? |
| `Q21_social_desirability` | all | p | Is there an obviously "good" answer people will give to look good? |
| `Q22_units_stated` | qty | p (yes = good) | Is the unit or format clear (£, per month, DD/MM/YYYY)? p 1.0 for a short_text that does not ask for an amount. |
| `Q23_actionable` | all | score 0–2 | 0 nice-to-know, no decision changes · 1 loosely informs · 2 directly informs a decision. |
| `Q24_intent` | all | choice | `screener` · `demographic` · `behaviour` · `attitude` · `outcome` · `open_feedback` · `contact_or_admin` · `instruction_only`. |
| `Q25_best_type` | all | choice | Best type for analysis: `current_type_is_best`, or a type key (`single_choice`, `multi_choice`, `dropdown`, `rating`, `nps`, `matrix`, `ranking`, `number`, `date`, `short_text`, `long_text`, `email`, `phone`). |

## Locators (per question; they point survey-level findings at questions)

Answer each on every question it applies to. They never change the score, but without them a survey-level finding becomes a vague hunch.

| id | applies | answer | ask yourself |
| --- | --- | --- | --- |
| `L_needs_why` | opts | p | Closed question whose answer is useless without the reason, and no "why?" follows? |
| `L_hard_to_recall` | all | p | Asks for exact figures, dates, totals or past details a typical person won't know offhand? |
| `L_topic_jump` | all | p | Switches to a clearly different topic from the previous question with no transition? |
| `L_is_demographic` | all | p | Is it a demographic or background question (age, gender, income, education, job, location, household)? |
| `L_pressuring` | all | p | Does the wording pressure toward an answer or toward continuing? |
| `L_hard_to_read` | all | p | Long sentences, dense wording or technical vocabulary for a general adult? |
| `L_sensitive_topic` | all | p | Asks about finances, health, ethnicity, religion, sexuality, legal issues or precise location? |
| `L_duplicate_of_earlier` | all | p | Does an earlier question already collect this same answer? (Judge with every earlier label in view.) |

## Which per-question items to judge

| Question | Judge |
| --- | --- |
| `statement` or `group` | `R_role`, `Q1`, `Q2`, `Q3a`, `Q3b`, `Q13` only. |
| role `information` or `consent` | `R_role`, `Q1`, `Q4`, `Q5`, `Q13`, `L_hard_to_read`, `L_pressuring` only. |
| `shown_when` set | everything that applies, minus `Q3b`; minus `Q5` when the condition names an earlier ref. |
| any other question | every row above whose `applies` matches. |
