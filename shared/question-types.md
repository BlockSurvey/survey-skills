# Question types

The 20 portable question types used in the [survey JSON](survey-format.md), what each is for, which fields it uses, how long it takes to answer, and its name in BlockSurvey, Typeform and Google Forms. Static checks and scoring use the families defined here.

## Type reference

| Portable type | Use it for | Fields it uses | BlockSurvey `bType` | Seconds |
| --- | --- | --- | --- | --- |
| `single_choice` | Pick exactly one of a few (2–10) options. | `options`, `has_other`, `has_none`, `has_prefer_not_to_answer`, `randomize_options` | `multiplechoice` | 10 |
| `multi_choice` | Pick any number of options ("select all that apply"). | as `single_choice` + `exclusive_options`, `selection.min/max` | `checkboxes` | 15 |
| `dropdown` | Pick one from a long list (roughly 8+; country, industry). | `options`, `has_other`, `has_prefer_not_to_answer` | `dropdown` | 10 |
| `yes_no` | A question that reads as yes/no ("Do you…?"). | `options` optional (defaults to Yes, No) | `multiplechoice` with options Yes / No | 10 |
| `short_text` | A short free answer that cannot be listed in advance (a name, a product). | — | `singletextbox` | 30 |
| `long_text` | An explanation or opinion in the respondent's own words. | — | `commentbox` | 60 |
| `number` | A numeric amount (say the unit). | `scale.min/max` optional as bounds | `number` | 15 |
| `rating` | How much / how satisfied on a short scale (stars, 1–5). | `scale.min/max/labels` | `starrating` | 8 |
| `nps` | Likelihood to recommend, 0–10. | `scale` = 0–10 with endpoint labels | `customerexperience` (`exType: nps`) | 8 |
| `likert` | Agreement / frequency on a labelled ordered scale; with `rows`, a battery of statements on the same scale. | `scale.min/max/labels`, or ordered `options`; `rows` for a battery | `numberrating` with labels (or `multiplechoice` with ordered options); with `rows`: `matrixrating` | 8 |
| `matrix` | Rate several listed items (rows) on the same scale (columns). | `rows`, `columns` | `matrixrating` | 8 × rows |
| `ranking` | Put several items in order. | `options` (7 at most) | `ranking` | 25 |
| `slider` | One value on a continuous scale. | `scale.min/max/labels` | `slider` | 10 |
| `date` | A date (say the format). | — | `date` | 12 |
| `email` | An email address (collects PII). | — | `email` | 15 |
| `phone` | A phone number (collects PII). | — | `phonenumber` | 15 |
| `file` | A file or photo upload. | — | `fileupload` | 60 |
| `statement` | Information only, no answer (section intro, instructions). | `label`, `description` | `statement` | 8 |
| `consent` | Agreement to terms / participation. | `options` (e.g. "I agree"), `role: consent` | `consent` | 6 |
| `group` | A section that holds several questions on one page. | `label`; children point at it with `group` | `questiongroup` | 5 |

## Seconds per type

Used by `S16_time_mismatch` and by `survey-create` to state an honest time. Ported from BlockSurvey's `SECONDS_PER_BTYPE` through the mapping above:

```
estimated_minutes = round( Σ seconds(question) / 60 , 1 )      over every question, statements and groups included
seconds(matrix)   = 8 × max(1, number of rows)                  (MATRIX_SECONDS_PER_ROW)
seconds(likert with rows) = 8 × number of rows                  (it is a matrix)
seconds(unknown type)     = 12                                   (DEFAULT_SECONDS)
```

Rule of thumb for writing: ten closed questions ≈ 2 minutes; every `long_text` adds a minute.

## Families

| Family | Types | Used by |
| --- | --- | --- |
| answerable | every type except `statement` and `group` | `n` in every count, per-question scores |
| non-answerable | `statement`, `group` | judged only on Q1, Q2, Q3a, Q3b, Q13 |
| choice (has `options`) | `single_choice`, `multi_choice`, `dropdown`, `ranking` (+ `yes_no`, `consent` with implicit options) | `S04`, `S11`, `S12`, option items Q6/Q14/Q20 |
| single-select | `single_choice`, `dropdown`, `yes_no`, `consent` | `Q7_options_overlap`, `S13` |
| multi-select | `multi_choice` | `S13`, `S14`, `S38` |
| scale | `rating`, `nps`, `likert`, `slider`, `matrix`; and `single_choice` / `dropdown` with 3+ options | `Q8`, `Q17` (`applies: scale`) |
| matrix | `matrix`; `likert` with `rows` | `S05`, `S30`, `S31`, `S51`, time estimate |
| open-ended | `short_text`, `long_text` | `S19`, `S34`, `S46`, `applies: text` |
| quantity | `number`, `slider`, `date`; `short_text` asking for an amount | `Q22_units_stated` |
| PII | `email`, `phone`, or any question with `collects_pii: true` | `S21`, `S48`, `Q15` |
| demanding (early-friction) | `long_text`, `file`, `email`, `phone`, matrix, `ranking` | `S51_early_friction` |

## Choosing a type

| The question asks for… | Use | Not |
| --- | --- | --- |
| one answer from a short known list | `single_choice` | `short_text` (unanalysable) |
| one answer from a long known list (countries, 8+ items) | `dropdown` | `single_choice` with 11+ radio buttons (`S33`) |
| every answer that applies | `multi_choice` (+ exclusive "None of these") | `single_choice` (`S13`, `Q9`) |
| a yes/no fact | `yes_no` | `single_choice` with Yes / No / Maybe unless "Not sure" is real |
| satisfaction or agreement | `likert` (5 points, all labelled) or `rating` | `slider` (imprecise), `long_text` |
| likelihood to recommend | `nps` 0–10, "How likely are you to recommend…" | a 1–5 scale (`S37`) |
| the same scale on 3–8 items | `matrix` (≤ 5 columns, ≤ 8 rows) or separate `likert`s on mobile | one grid of 12 rows (`S30`) |
| an order of preference | `ranking` (≤ 7 items) or "pick your top 3" `multi_choice` | ranking 15 items (`S32`) |
| an amount, count or duration | `number` with the unit in the label | `short_text` |
| a date | `date` with the format | `short_text` |
| the reason behind an answer | optional `long_text` after the closed question | a required essay early on (`S51`) |
| contact details for follow-up | `email` / `phone`, optional, at the end | asking before the content (`S48`) |
| a section break or explanation | `statement` (or a `group` title) | a fake question nobody answers |
| agreement to take part | `consent` | burying it in the welcome text |

## Other platforms (approximate)

Names as the platforms show them in their builders, from general knowledge; treat as **approximate** and check before relying on them.

| Portable type | Typeform | Google Forms |
| --- | --- | --- |
| `single_choice` | Multiple Choice | Multiple choice |
| `multi_choice` | Multiple Choice ("Multiple selection" on) | Checkboxes |
| `dropdown` | Dropdown | Dropdown |
| `yes_no` | Yes/No | Multiple choice (Yes / No) |
| `short_text` | Short Text | Short answer |
| `long_text` | Long Text | Paragraph |
| `number` | Number | Short answer + number validation |
| `rating` | Rating | Rating (or Linear scale 1–5) |
| `nps` | Net Promoter Score® | Linear scale 0–10 |
| `likert` | Opinion Scale (single); Matrix (with rows) | Linear scale (single); Multiple choice grid (with rows) |
| `matrix` | Matrix | Multiple choice grid (Checkbox grid for multi) |
| `ranking` | Ranking | No native type; Multiple choice grid (one choice per column) |
| `slider` | Opinion Scale (no true slider) | Linear scale |
| `date` | Date | Date |
| `email` | Email | Short answer + email validation (or "Collect email addresses") |
| `phone` | Phone Number | Short answer + regex validation |
| `file` | File Upload | File upload (respondents must sign in to Google) |
| `statement` | Statement | Title and description |
| `consent` | Legal | Checkboxes with one required "I agree" option |
| `group` | Question Group | Section |

## Not portable

BlockSurvey types with no portable equivalent (score with the closest type, or as `statement`): `dropdownmultiple`, `matrixratingmultiple`, `matrixtext`, `matrixnumber`, `matrixdropdown`, `matrixstarrating` (→ `matrix`), `website`, `country` (→ `short_text` / `dropdown`), `list`, `multipletext`, `multiplenumber`, `imagecapture`, `signature`, `payment`, `cart`, `contactform`, `scheduleAMeeting`, `abtest`, `maxDiff`, `bipolar`, `conjoint`, `vanWestendorp`, `gaborGranger`, and the wallet/social login types.
