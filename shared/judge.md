# Optional: judge the rubric with an API (`survey_judge.py`)

You do not need this. By default the chat assistant you are talking to judges the rubric ([scoring.md](scoring.md#pipeline)) and the calculator does the arithmetic. `scripts/survey_judge.py` replaces only the judging step with an API call, for when no chat is in the loop.

## When to use it

- **CI**: score every survey file in a pull request and fail the build below a grade.
- **Batch runs**: score or re-score many surveys at once (for example after the rubric changes).
- **Repeatable runs**: the same judge model and settings every time, without copy-pasting into a chat.

For one survey you are working on now, just ask your assistant to score it.

## Setup

```bash
cp .env.example .env      # then fill in the key for the provider you will use
```

Keys are read from the environment first, then from a `.env` file in the folder you run the command from. The script never prints key values. `.env` is git-ignored; never commit it.

| Provider | `--provider` | Key | Default model | Price (USD per million tokens, verify current pricing) |
| --- | --- | --- | --- | --- |
| TypeSafe Jev | `jev` | `TYPESAFE_API_KEY` | `jev-latest` | $0.042 input, output free |
| OpenAI | `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` | $0.15 input, $0.60 output |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | `claude-haiku-5-5` | $0.10 input, $0.50 output |

Override the model with `--model` or the `*_MODEL` variable in `.env`. For the most accurate Anthropic judge use `--model claude-opus-5-5` ($4 / $20), or `claude-sonnet-5-5` ($2 / $10) in between.

**Cost of a 12-question survey** (the script's own estimate at 4 characters per token; prices as of 2026-10-09):

| Run | Requests | Estimate |
| --- | --- | --- |
| `jev` | 3 (survey items + 2 batches of 6 questions) | ~49k input tokens ≈ $0.002 |
| `openai` (`gpt-4o-mini`) | 2 (survey items, all questions) | ~13k in + ~6k out ≈ $0.006 |
| `anthropic` (`claude-haiku-5-5`) | 2 | ~13k in + ~6k out ≈ $0.004 |
| `anthropic --model claude-opus-5-5` | 2 | ~13k in + ~6k out ≈ $0.17 |

Jev sends more input because its API takes each item per question with its own instructions, but it charges for input only and is the cheapest per token.

## Commands

From your survey's folder (`<skill-dir>` is the folder of the installed `survey-score` skill):

```bash
# 1. See the plan and the cost. Nothing is sent.
python <skill-dir>/scripts/survey_judge.py survey.json --provider anthropic --dry-run

# 2. Judge.
python <skill-dir>/scripts/survey_judge.py survey.json --provider anthropic --out judgments.json

# 3. Score (as usual).
python <skill-dir>/scripts/survey_score_calc.py survey.json judgments.json --lint
```

Swap `anthropic` for `jev` or `openai`. Options:

- `--dry-run` prints every request it would send (`--show-requests` adds the full bodies), the estimated input tokens and the cost, then exits without any network call.
- Every real run prints the same estimate first. If it is above **$1**, or the model is not in the script's price table, the script refuses (exit 2) until you add `--yes`. `--max-cost 0.25` lowers the cap.
- Nothing is sent unless you name `--provider`.

Exit codes: `0` complete, `1` partial (some requests failed), `2` usage error, missing key, or cost refusal.

## What it sends and returns

- One request for all survey-level items. Per-question items: all questions in one request for OpenAI and Anthropic; batches of 6 questions for Jev (the question context goes in `state.questions[i]`, answers come back as `<item>__<ref>`). The survey is never re-sent once per item.
- Only the items that apply to each question are asked (the calculator's applicability rules, widened so one pass covers kind, incentive and sensitivity gates).
- Answers are converted to the [judgments contract](scoring.md#judgments-json-contract): Score → integer `level` (Jev's fractional score is rounded) with `confidence`; Noul → `p`; Choice → `choice` with `confidence`. Out-of-range values are clamped; unknown choices and items are dropped.
- Rate limits and overloads (HTTP 429, 503, 529) are retried up to 3 attempts with exponential backoff. A request that still fails, a reply cut off at the token limit, a refusal or a reply that is not valid JSON leaves its items out: the file gets `meta.partial: true` and `meta.errors`, and the calculator lists the gaps in its own `meta.missing_items`.

## Limitations

- **LLM judges vary.** Different models, and the same model on different days, can give different answers on borderline items. Compare scores from the same provider and model; for decisions, read the findings, not just the number.
- **Jev is calibrated but needs its own key.** Its probabilities are tuned for judgments like these; chat models report a confidence that is a self-estimate.
- The token estimate is approximate (4 characters per token), and prices change: check your provider's current pricing.
- Very long surveys: chat providers get questions in chunks of 50 above 150 questions; a reply cut at `max_tokens` is reported as partial rather than retried.

## Privacy

Your survey text (title, welcome, questions, options) is sent to the provider you choose and handled under that provider's terms. Do not use this script on surveys you cannot share with a third party; your chat assistant, or the manual tally in [scoring.md](scoring.md#manual-tally-fallback-no-python), keeps it where it is.
