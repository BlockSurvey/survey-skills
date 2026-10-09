# Survey score: 11/100 · F · not_ready

11/100. 40 questions, 30 serious and 85 moderate issues. Biggest one: Q11 is ambiguous — two respondents could read it two different ways, and you'll never know which.

## Categories

| Category | Weight | Score | Findings |
| --- | --- | --- | --- |
| Purpose & framing | 0.15 | 0 | 11 |
| Structure & flow | 0.10 | 0 | 10 |
| Coverage & gaps | 0.15 | 40 | 4 |
| Question quality | 0.20 | 23 | 117 |
| Respondent experience | 0.20 | 0 | 15 |
| Trust & ethics | 0.05 | 3 | 5 |
| Conversion | 0.15 | 0 | 16 |

## Funnel (predicted completion: low)

| Stage | Score | Drivers |
| --- | --- | --- |
| start | 0 | A1_title_specific, A3_purpose_explained, A8_respondent_benefit |
| continue | 0 | B3_demographics_placement, Q15_abandon_risk:Q1, B2_opening_question |
| finish | 0 | B1_logical_order, E6_length_feels_justified, E8_straightlining_risk |
| answer_quality | 30 | S13_selection_hint_type_mismatch, S12_numeric_range_gap, S45_yesno_type_mismatch |
| actionability | 62 | C1_objective_coverage, C4_missing_why, A7_objective_inferable |

## Top findings

1. high · Q11 · Q11 is ambiguous — two respondents could read it two different ways, and you'll never know which. → Rewrite Q11 as one short sentence with one plain meaning.
2. high · Q15 · Q15 is ambiguous — two respondents could read it two different ways, and you'll never know which. → Rewrite Q15 as one short sentence with one plain meaning.
3. high · Q31 · Q31 is ambiguous — two respondents could read it two different ways, and you'll never know which. → Rewrite Q31 as one short sentence with one plain meaning.
4. high · survey · Your title "Customer Satisfaction Survey Q3 v2" tells respondents nothing about what they're walking into. → Rewrite the title as what the respondent gets or gives, e.g. "Help us design a simpler UK mortgage app".
5. high · survey · There is no explanation of why this survey exists. Respondents are being asked to care about a mystery. → Add two sentences to the welcome screen: why you're asking, and what you'll do with the answers.
6. high · Q33, Q8, Q2, Q3 · The question order is a shuffle. Related questions are scattered so respondents keep re-orienting. See: Q33, Q8, Q2, Q3. → Group questions by topic and order sections general -> specific, easy -> demanding.
7. high · Q1 · Q1 ("What is your age?") asks for more than you've earned at this point. That's where the funnel dies. → Make Q1 optional, move it to the end, or explain why it's needed.
8. high · Q2 · Q2 ("Please describe in detail your overall experience with our product and our suppo") asks for more than you've earned at this point. That's where the funnel dies. → Make Q2 optional, move it to the end, or explain why it's needed.
9. high · Q3 · Q3 ("What is your gender?") asks for more than you've earned at this point. That's where the funnel dies. → Make Q3 optional, move it to the end, or explain why it's needed.
10. high · Q4 · Q4 ("What is your annual household income?") asks for more than you've earned at this point. That's where the funnel dies. → Make Q4 optional, move it to the end, or explain why it's needed.

…and 152 more (see --json).

## Questions

| Ref | Type | Label | Score | Findings |
| --- | --- | --- | --- | --- |
| Q1 | single_choice | What is your age? | 69 | Q15_abandon_risk, Q6_options_not_exhaustive, S12_numeric_range_gap, Q16_sensitive_reassured, Q5_relevance, Q23_actionable, Q7_options_overlap, S23_sensitive_without_optout |
| Q2 | long_text | Please describe in detail your overall experience with our p | 65 | Q15_abandon_risk, Q2_double_barreled, S51_early_friction, Q1_clarity, Q19_recall_period |
| Q3 | single_choice | What is your gender? | 71 | Q15_abandon_risk, Q6_options_not_exhaustive, Q16_sensitive_reassured, Q5_relevance, Q23_actionable, S23_sensitive_without_optout |
| Q4 | single_choice | What is your annual household income? | 69 | Q15_abandon_risk, Q5_relevance, Q6_options_not_exhaustive, S12_numeric_range_gap, Q16_sensitive_reassured, Q23_actionable, S23_sensitive_without_optout |
| Q5 | short_text | What is your job title? | 85 | Q25_best_type |
| Q6 | single_choice | How many employees does your company have? | 87 | Q7_options_overlap, S12_numeric_range_gap, Q5_relevance |
| Q7 | single_choice | What is your highest level of education? | 82 | Q5_relevance, Q23_actionable, Q6_options_not_exhaustive |
| Q8 | single_choice | How much do you love our amazing new dashboard? | 75 | Q3a_leading, Q6_options_not_exhaustive, Q3b_presuming, Q8_scale_unbalanced |
| Q9 | single_choice | How fast and reliable is our platform? | 74 | Q2_double_barreled, Q1_clarity, Q8_scale_unbalanced, Q6_options_not_exhaustive |
| Q10 | single_choice | Which features do you use? Select all that apply. | 77 | Q9_type_fit, S13_selection_hint_type_mismatch, Q7_options_overlap, Q25_best_type |
| Q11 | yes_no | Don't you agree that our pricing is fair and our support is  | 58 | Q1_clarity, Q2_double_barreled, Q3a_leading, Q25_best_type, S45_yesno_type_mismatch, Q9_type_fit, S35_loaded_words |
| Q12 | rating | How satisfied are you with our SSO, SCIM provisioning and RB | 62 | Q2_double_barreled, Q1_clarity, Q4_jargon, Q3b_presuming, S36_scale_endpoints_only |
| Q13 | matrix | Please rate the following aspects of our product. | 76 | S30_matrix_too_large, Q15_abandon_risk, Q8_scale_unbalanced |
| Q14 | nps | How likely is it that you would recommend us? | 90 | Q1_clarity, S37_nps_nonstandard |
| Q15 | yes_no | How often do you use the mobile app? | 57 | Q1_clarity, Q9_type_fit, Q6_options_not_exhaustive, Q25_best_type, S45_yesno_type_mismatch, Q19_recall_period, Q3b_presuming |
| Q16 | single_choice | How often do you use our API endpoints and webhooks? | 72 | Q2_double_barreled, Q3b_presuming, Q4_jargon, Q6_options_not_exhaustive, Q19_recall_period |
| Q17 | likert | Our support team is always helpful and responsive. | 79 | Q2_double_barreled, Q3a_leading, Q3b_presuming, S35_loaded_words, S27_monotony_run |
| Q18 | likert | The product is easy to use and has all the features I need. | 86 | Q2_double_barreled, S10_duplicate_labels |
| Q19 | likert | I would never consider switching to a competitor. | 81 | Q1_clarity, Q3a_leading, S35_loaded_words |
| Q20 | likert | Our onboarding process was excellent. | 87 | Q3a_leading |
| Q21 | likert | The documentation is clear. | 92 |  |
| Q22 | likert | The UI is intuitive. | 90 |  |
| Q23 | likert | Our release cadence meets my needs. | 75 | Q1_clarity, Q4_jargon |
| Q24 | likert | The product clearly provides great value for money. | 85 | Q3a_leading, S35_loaded_words |
| Q25 | rating | Rate our reporting module. | 80 | Q1_clarity |
| Q26 | rating | Rate our alerting module. | 80 | Q1_clarity |
| Q27 | rating | Rate our integrations. | 80 | Q1_clarity |
| Q28 | rating | Rate our billing experience. | 81 | Q1_clarity |
| Q29 | yes_no | Would you pay more for advanced analytics? | 83 | Q1_clarity |
| Q30 | single_choice | You should upgrade to Premium. How likely are you to do so? | 67 | Q3a_leading, Q1_clarity, Q6_options_not_exhaustive, Q3b_presuming, Q5_relevance, S35_loaded_words, Q8_scale_unbalanced |
| Q31 | number | How much time do you spend in the app? | 73 | Q1_clarity, Q19_recall_period, Q22_units_stated |
| Q32 | number | How many support tickets did you open last year? | 90 |  |
| Q33 | single_choice | How did you hear about us? | 82 | Q6_options_not_exhaustive, Q5_relevance |
| Q34 | single_choice | Which region are you located in? | 82 | Q6_options_not_exhaustive, Q5_relevance |
| Q35 | single_choice | What is your role in purchasing decisions? | 90 |  |
| Q36 | likert | The product is easy to use and has all the features I need. | 79 | Q2_double_barreled, Q23_actionable |
| Q37 | single_choice | How satisfied are you with our ETL pipeline latency SLAs? | 70 | Q1_clarity, Q4_jargon, Q6_options_not_exhaustive, Q3b_presuming, Q8_scale_unbalanced |
| Q38 | email | What is your email address? | 72 | Q15_abandon_risk, Q16_sensitive_reassured, Q5_relevance, Q23_actionable |
| Q39 | phone | What is your phone number? | 68 | Q5_relevance, Q15_abandon_risk, Q16_sensitive_reassured, Q23_actionable |
| Q40 | long_text | Any other comments? | 85 | Q15_abandon_risk |

## What to do first

1. Rewrite Q11 as one short sentence with one plain meaning. (Q11, Q15, Q31, Q2, Q9, Q12, Q14, Q19, Q23, Q25, Q26, Q27, Q28, Q29, Q30, Q37)
2. Rewrite the title as what the respondent gets or gives, e.g. "Help us design a simpler UK mortgage app".
3. Add two sentences to the welcome screen: why you're asking, and what you'll do with the answers.

_Rubric bs-skills-1.0 · profile customer_satisfaction_
