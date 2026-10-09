# Golden example: a deliberately bad survey

**This survey is intentionally bad. Do not copy it.** It exists for two reasons:

1. **Acceptance test.** `tests/test_examples.py` checks that the scorer recognises a survey any methodologist would reject: lint must report at least one `high` finding, the score must be 60 or lower, and the findings must include `Q2_double_barreled`, `Q3a_leading`, `B3_demographics_placement`, `S30_matrix_too_large` and `S17_length_fatigue`.
2. **A "before" picture.** Next to the three good examples, it shows what `survey-score` says about the kind of survey people actually send out, and what each roast and fix looks like.

**How this was produced:** the survey was written by hand to plant the defects listed below (this one did not come from `survey-create`, on purpose). It was then judged by following `skills/survey-score/SKILL.md` and `references/judging-guide.md` literally, in one pass, as for any survey a user might paste: every judgment is what the survey's own words support, with a note quoting them on every survey-level item and every flagged question. `report.md` and `report.json` are the unedited output of `shared/scripts/survey_score_calc.py`.

**Result:** 11/100 · F · `not_ready`; 30 high, 85 medium and 47 low findings across 65 distinct ids; predicted completion `low`.

## Planted defects and what caught them

| Planted defect | Where | Caught as |
| --- | --- | --- |
| No description, no welcome, no thank-you | survey | `S07_no_description`, `S08_no_welcome`, `S09_no_thank_you`, `A3_purpose_explained`, `E3_thank_you_quality`, `E4_welcome_motivates` |
| Internal title ("Customer Satisfaction Survey Q3 v2") | survey | `A1_title_specific`, `A2_title_respondent_facing` |
| Demographics first (age, gender, income, job, company size, education) | Q1, Q3–Q7 | `B3_demographics_placement`, `B2_opening_question`, `C6_demographics_proportionate`, `Q15_abandon_risk` |
| Required open text as Q2 (and double-barrelled) | Q2 | `S51_early_friction`, `Q15_abandon_risk`, `Q2_double_barreled` |
| Numeric range gaps and overlaps | Q1, Q4, Q6 | `S12_numeric_range_gap`, `Q6_options_not_exhaustive`, `Q7_options_overlap` |
| Sensitive questions, required, no opt-out | Q1, Q3, Q4, Q38, Q39 | `S23_sensitive_without_optout`, `Q16_sensitive_reassured` |
| Leading questions ("How much do you love our amazing new dashboard?", "Don't you agree…", "You should upgrade…") | Q8, Q11, Q17, Q19, Q20, Q24, Q30 | `Q3a_leading`, `S35_loaded_words`, `F4_manipulative_framing` |
| Double-barrelled questions ("fast and reliable", "pricing is fair and our support is helpful") | Q2, Q9, Q11, Q12, Q16, Q17, Q18, Q36 | `Q2_double_barreled` |
| Unbalanced scales (no negative points) | Q8, Q9, Q13, Q30, Q37 | `Q8_scale_unbalanced` |
| "Select all that apply" on a single_choice | Q10 | `S13_selection_hint_type_mismatch`, `Q9_type_fit` |
| "How often…?" as a yes/no | Q15 | `S45_yesno_type_mismatch`, `Q9_type_fit`, `Q25_best_type` |
| Jargon ("SSO, SCIM provisioning and RBAC", "ETL pipeline latency SLAs", "release cadence") | Q12, Q16, Q23, Q37 | `Q4_jargon`, `E5_reading_level` |
| A 10×8 matrix | Q13 | `S30_matrix_too_large`, `E8_straightlining_risk` |
| Non-standard NPS (1–10, "recommend us") | Q14 | `S37_nps_nonstandard` |
| 7-point scale labelled only at the ends | Q12 | `S36_scale_endpoints_only` |
| 40 questions, all required, no progress bar, no logic, 3 minutes promised | survey | `S17_length_fatigue`, `S18_all_required_long`, `S24_no_progress_bar_long`, `S47_no_logic_long_survey`, `S16_time_mismatch`, `E6_length_feels_justified` |
| Twelve look-alike rating items in a row | Q17–Q28 | `S27_monotony_run`, `E8_straightlining_risk` |
| A repeated question with its scale reversed | Q18 / Q36 | `S10_duplicate_labels`, `B5_redundant_questions`, `B8_scale_direction_consistent` |
| Hard recall, no units | Q31, Q32 | `E2_burden`, `Q22_units_stated`, `Q19_recall_period` |
| Required email and phone at the end, no contact for the owner | Q38, Q39 | `Q15_abandon_risk`, `B7_end_loading`, `F5_contact_provided` |
| No screener | survey | not scored: the judge classified this as a `feedback` survey for existing customers, and `C2_has_screener` applies only to `research` (scoring.md, kinds gating). This is intended; a customer feedback survey sent to customers needs no screener. |

## How to use it

Run `survey-fix` on `report.json` to see the fix skill at work, or score your own survey and compare. Regenerate the report with:

```bash
python3 shared/scripts/survey_score_calc.py examples/bad-survey/survey.json examples/bad-survey/judgments.json --lint --md > examples/bad-survey/report.md
python3 shared/scripts/survey_score_calc.py examples/bad-survey/survey.json examples/bad-survey/judgments.json --lint --json > examples/bad-survey/report.json
```
