#!/usr/bin/env python3
"""Deterministic survey score calculator (shared/scoring.md, bs-skills-1.0).

The judging LLM answers the rubric (shared/rubric.md) once and writes a judgments JSON; this script does all the
arithmetic: applicability, values, findings, locators, hybrid checks, category and funnel scores, grade, verdict.

    python survey_score_calc.py survey.json judgments.json [--lint] [--json|--md] [--polite]
    python survey_score_calc.py --print-items          # the rubric table as JSON

    calc(survey, judgments, lint_findings) -> report dict

Exit codes: 0 ok, 1 verdict not_ready or any blocker/high finding, 2 invalid input.
Stdlib only, Python >= 3.9. Never crashes on malformed judgments or survey fields: a value of the wrong shape is
treated as missing and reported in meta.missing_items.
"""

import copy
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import survey_lint  # noqa: E402
from survey_common import _d, _l, _num, _text, is_answerable, load_survey  # noqa: E402
from survey_common import normalise as normalise_survey  # noqa: E402

RUBRIC_VERSION = "bs-skills-1.0"

# --- constants (scoring.md#constants) ---------------------------------------------------------

NOUL_YES = 0.7
NOUL_NO = 0.3
NOUL_STRONG = 0.85
NOUL_WEAK = 0.15
SENSITIVE_YES = 0.8
LOW_CONFIDENCE = 0.35
SCORE_CONFIDENT = 0.6
GAP_TOPIC_CONFIDENT = 0.5
MIN_CERTAINTY = 0.1
DEFAULT_CONFIDENCE = 0.7
LOCATE_YES = 0.7
LOCATE_FALLBACK = 0.5
LOCATE_MAX = 8
STATIC_DEDUCTION = {"blocker": 0.0, "high": 0.12, "medium": 0.06, "low": 0.02, "info": 0.0}
STATIC_REPEAT_FACTOR = 0.25
STATIC_REPEAT_CAP = 2.0
STATIC_DEDUCTION_CAP = 0.35
QUESTION_HIGH_PENALTY = 0.02
QUESTION_HIGH_PENALTY_CAP = 0.20
NEUTRAL_BASE = 0.70
BLOCKER_SCORE_CAP = 49
READY_AT = 75
NOT_READY_BELOW = 50
GRADES = [(90, "A"), (80, "B"), (70, "C"), (60, "D"), (50, "E")]

SEVERITIES = ("blocker", "high", "medium", "low", "info")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}
SEVERITY_DOWNGRADE = {"blocker": "blocker", "high": "medium", "medium": "low", "low": "low", "info": "info"}

PROBABLY = " (Probably — the judge leans this way but isn't certain.)"
NOT_SURE = " (The judge wasn't sure about this one.)"
HUNCH_LOCATE = (" (The judge flagged this survey-wide but couldn't point at a specific question — treat it as a "
                "hunch.)")
HUNCH_GAP = " (The judge couldn't name the missing topic — treat it as a hunch.)"

CATEGORIES = [("purpose", "Purpose & framing"), ("structure", "Structure & flow"), ("coverage", "Coverage & gaps"),
              ("questions", "Question quality"), ("experience", "Respondent experience"),
              ("trust", "Trust & ethics"), ("conversion", "Conversion")]
CATEGORY_IDS = [c for c, _ in CATEGORIES]
SURVEY_CATEGORIES = ("purpose", "structure", "coverage", "experience", "trust")
STAGES = ("start", "continue", "finish", "answer_quality", "actionability")

_P = ("purpose", "structure", "coverage", "questions", "experience", "trust", "conversion")
WEIGHT_PROFILES: Dict[str, Dict[str, float]] = {
    name: dict(zip(_P, row)) for name, row in {
        "default": (.20, .15, .20, .25, .15, .05, .00),
        "customer_satisfaction": (.15, .10, .15, .20, .20, .05, .15),
        "market_research": (.15, .10, .25, .25, .10, .05, .10),
        "employee_engagement": (.10, .10, .15, .20, .15, .20, .10),
        "academic_research": (.10, .15, .20, .30, .05, .20, .00),
        "lead_generation": (.15, .10, .05, .15, .20, .15, .20),
        "registration_or_form": (.10, .10, .00, .30, .30, .20, .00),
        "event_feedback": (.10, .10, .15, .20, .30, .05, .10),
    }.items()}

# G. Conversion: rubric items (at these weights) + the mean of Q15 across questions, and these static deductions
CONVERSION_ITEMS = {"A8_respondent_benefit": 2, "A9_sponsor_named": 2, "E7_welcome_scannable": 1,
                    "E8_straightlining_risk": 2, "B7_end_loading": 1}
CONVERSION_Q15_WEIGHT = 3
CONVERSION_STATIC = {"S30", "S31", "S32", "S33", "S34", "S46", "S47", "S48", "S50", "S51"}

# Applicability (scoring.md#applicability)
NON_ANSWERABLE_ITEMS = {"Q1_clarity", "Q2_double_barreled", "Q3a_leading", "Q3b_presuming", "Q13_grammar"}
NON_QUESTION_ITEMS = {"Q1_clarity", "Q4_jargon", "Q5_relevance", "Q13_grammar", "L_hard_to_read", "L_pressuring"}
SINGLE_CHOICE_TYPES = {"single_choice", "dropdown", "yes_no", "consent"}
SCALE_TYPES = {"rating", "nps", "likert", "slider", "matrix"}
QUANTITY_TYPES = {"number", "slider", "date", "short_text"}
ROLES = ("question", "information", "consent")

# Locators (scoring.md#locating-survey-level-findings)
LOCATORS = {"C4_missing_why": "L_needs_why", "E2_burden": "L_hard_to_recall", "B1_logical_order": "L_topic_jump",
            "B3_demographics_placement": "L_is_demographic", "C6_demographics_proportionate": "L_is_demographic",
            "F4_manipulative_framing": "L_pressuring", "E5_reading_level": "L_hard_to_read",
            "F1_sensitive_topics": "L_sensitive_topic", "B5_redundant_questions": "L_duplicate_of_earlier"}

# Static checks gated by survey kind, and the hybrid checks' funnel stages
STATIC_KINDS = {"S19_no_open_ended": {"research", "feedback"}}
STATIC_FUNNEL = {**getattr(survey_lint, "_FUNNEL", {}), "S22": "answer_quality", "S23": "continue",
                 "S25": "answer_quality", "S26": "answer_quality"}

# Intent-mix code rules (scoring.md#findings-from-judgments): authored texts
INTENT_RULES = {
    "no_outcome": ("medium", "Nothing here measures the outcome. You'll have context and no verdict.",
                   "Add one direct outcome question (overall satisfaction, likelihood, intent) tied to the purpose."),
    "demographics_heavy": ("low", "{k} of {n} questions are demographics. That's a census, not a survey.",
                           "Keep only the demographics you will cut the data by."),
    "outcome_buried": ("low", "The question that matters most is near the very end, where the tired and the hurried "
                              "have already left.", "Move the main outcome question into the first half."),
}
NO_OUTCOME_EXEMPT_KINDS = {"form", "quiz", "information"}

# --- the rubric (transcribed from shared/rubric.md; a test checks the ids match) ------------------------
# instructions/criteria are kept for --print-items; roast/fix/severity/weights drive the report.

ITEMS: Dict[str, Dict[str, Any]] = {
    'A1_title_specific': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 3,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'high', 1: 'low'},
        'roast': {0: 'Your title "{title}" tells respondents nothing about what they\'re walking '
                     'into.',
                  1: '"{title}" names a topic, not a purpose. People answer better when they know why '
                     "they're asked."},
        'fix': ('Rewrite the title as what the respondent gets or gives, e.g. "Help us design a '
                'simpler UK mortgage app".'),
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'title',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Generic or internal-sounding; a respondent could not guess the topic from it',
                     'Names the topic but not what the survey is for',
                     'Names the topic and its purpose specifically'],
        'instructions': 'How clearly does `title` tell a respondent what the survey is about?',
    },
    'A2_title_respondent_facing': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium'},
        'roast': {0: '"{title}" reads like the file name on your desktop, not something a stranger '
                     'wants to open.'},
        'fix': "Name the survey for the respondent: what it's about and what's in it for them.",
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'title',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Reads like an internal file or project name, for example it contains words such as '
                     "'new', 'v2', 'product', 'internal', 'draft', or describes the company's work "
                     'rather than addressing the respondent',
                     'Neutral; neither inviting nor internal',
                     'Addresses the respondent and invites participation'],
        'instructions': 'Is `title` written for the respondent, or is it an internal project name?',
    },
    'A3_purpose_explained': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 4,
        'weight': 3,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'high', 1: 'medium'},
        'roast': {0: 'There is no explanation of why this survey exists. Respondents are being asked '
                     'to care about a mystery.',
                  1: 'The intro names the topic but never says why answering matters or what happens '
                     'with the answers.'},
        'fix': ("Add two sentences to the welcome screen: why you're asking, and what you'll do "
                'with the answers.'),
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['No explanation of purpose anywhere',
                     'States the topic only',
                     'States the topic and why the answers matter',
                     'States the topic, why the answers matter, and how the answers will be used'],
        'instructions': ('Considering `description` and every `welcome.description`, how well is the purpose '
                         'of the survey explained to the respondent?'),
    },
    'A5_privacy_stated': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ("Not a word about what happens to people's answers. Silence on privacy reads as 'we "
                  "didn't think about it'."),
        'fix': ("Add one line: whether responses are anonymous, who sees them, and how long they're "
                'kept.'),
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does any welcome or description text tell the respondent how their data will be '
                         'handled (privacy, anonymity, confidentiality, or consent)?'),
    },
    'A6_audience_stated': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': ('The intro never says who this is for, so the wrong people will answer and the '
                  "right ones won't know they qualify."),
        'fix': 'Say who you want to hear from in the first sentence of the welcome screen.',
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does the welcome or description say who the survey is for (the intended '
                         'respondents)?'),
    },
    'A7_objective_inferable': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 3,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': ['feedback', 'research'],
        'severity': {0: 'high', 1: 'medium'},
        'roast': {0: "Reading the questions, it's impossible to tell what decision this survey is "
                     'meant to inform.',
                  1: "There's a theme, but no single question this survey is built to answer. Data "
                     'without a decision is trivia.'},
        'fix': ('Write the one sentence you want to be able to say after the survey closes, then '
                "cut every question that doesn't serve it."),
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['No coherent objective; the questions look unrelated to each other',
                     'A broad theme is evident but not a specific decision or research question the '
                     'survey would answer',
                     'A specific decision or research question is evident from the questions'],
        'instructions': ('Looking at the whole `questions` list, can one infer a single clear objective the '
                         'survey serves?'),
    },
    'A8_respondent_benefit': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium'},
        'roast': {0: "You're asking for {stated_minutes} minutes and offering nothing back — not even "
                     "'we'll share what we learn'."},
        'fix': 'Add one sentence on what happens because of their answers.',
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'v2',
        'criteria': ['Nothing is offered or promised; the text only asks for time',
                     'A vague promise ("help us improve")',
                     'A concrete outcome or reward (results shared, a specific improvement to something '
                     'they use, a named incentive)'],
        'instructions': ('Considering `welcome` and `description`, what does the respondent gain or see '
                         'happen as a result of answering?'),
    },
    'A9_sponsor_named': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': "Nobody knows who's asking. Anonymous senders read as phishing.",
        'fix': 'Name the team and, ideally, why they care.',
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'v2',
        'criteria': {'true': 'an organisation, brand, team or person is named',
                     'false': 'no sender is identifiable'},
        'instructions': ('Does `title`, `description` or any `welcome.description` name the organisation, '
                         'team or person running the survey?'),
    },
    'A10_deadline_stated': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': 'No closing date anywhere. "Whenever" is the easiest deadline to never get round to.',
        'fix': ('Say when the survey closes ("Open until Friday 14 November"); keep it honest, not '
                'fake urgency.'),
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'v2',
        'criteria': None,
        'instructions': ('Does any `welcome.description` or `description` state when the survey closes or by '
                         'when responses are needed?'),
    },
    'B1_logical_order': {
        'category': 'structure',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 3,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'high', 1: 'low'},
        'roast': {0: 'The question order is a shuffle. Related questions are scattered so respondents '
                     'keep re-orienting.',
                  1: 'Mostly grouped, but a few topic jumps will make respondents feel like the '
                     'survey lost its train of thought.'},
        'fix': 'Group questions by topic and order sections general -> specific, easy -> demanding.',
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Topics jump around; related questions are scattered across the survey',
                     'Mostly grouped by topic, with some jarring jumps between unrelated topics',
                     'Grouped by topic and moves from general to specific, or from easy to demanding'],
        'instructions': ('How logically are the `questions` ordered for a respondent reading them top to '
                         'bottom?'),
    },
    'B2_opening_question': {
        'category': 'structure',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium', 1: 'low'},
        'roast': {0: "You open with a personal question and no explanation. That's asking for a phone "
                     'number before saying hello.',
                  1: 'The opener is fine but flat. First questions set the mood; this one sets none.'},
        'fix': ('Open with an easy, on-topic question; move personal or demographic questions to '
                'the end.'),
        'fix_by_role': {},
        'funnel': 'continue',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Sensitive, hard, or personal, for example income, age, or health, with no '
                     'explanation of why it is asked',
                     'Neutral but dull',
                     'Easy, non-sensitive, and relevant to the survey topic'],
        'instructions': 'How suitable is the first answerable question in `questions` as an opening question?',
    },
    'B3_demographics_placement': {
        'category': 'structure',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium', 1: 'low'},
        'roast': {0: 'A wall of demographics before a single interesting question. Respondents '
                     "haven't earned trust yet and you're already asking for income.",
                  1: "Demographics sit early or mid-survey without a reason. They'd cost you fewer "
                     'drop-offs at the end.'},
        'fix': ('Move demographics to the end, or add a one-line reason ("so we can compare answers '
                'across groups").'),
        'fix_by_role': {},
        'funnel': 'continue',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['At the very start, several in a row, with no explanation of why they are needed',
                     'At the start but brief, or in the middle of the survey',
                     'At the end, or introduced with a reason for asking; or there are no demographic '
                     'questions'],
        'instructions': ('Where do demographic questions (age, income, education, employment status) sit in '
                         '`questions`, and is a reason for asking them given?'),
    },
    'B4_sections_signposted': {
        'category': 'structure',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': ('Topics change with no signpost. Respondents feel each switch as a small jolt, and '
                  'jolts add up to abandons.'),
        'fix': ('Add a short statement or section title where the topic changes ("Next, a few '
                'questions about advice").'),
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('When the topic of the questions changes, is there a statement, group title, or '
                         'question text that signals the new section to the respondent?'),
    },
    'B5_redundant_questions': {
        'category': 'structure',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ('At least two questions ask the same thing in different clothes. Respondents '
                  'notice, and it reads as carelessness.'),
        'fix': 'Merge or delete the duplicate; keep the better-worded one.',
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': {'true': 'At least one pair of questions would collect the same information',
                     'false': 'Every question asks for something distinct'},
        'instructions': ('Are there two or more `questions` that ask essentially the same thing of the '
                         'respondent?'),
    },
    'B7_end_loading': {
        'category': 'structure',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium'},
        'roast': {0: 'You saved the essays for the end. The end is where people are least willing to '
                     'write.'},
        'fix': ('Move the demanding items (long free text, large matrices, ranking) earlier or cut '
                'them; end on something quick.'),
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'questions',
        'locates': None,
        'source': 'v2',
        'criteria': ['The hardest items (long free text, large matrices, ranking) are concentrated at '
                     'the end',
                     'A single demanding item at the end',
                     'The end is as easy as, or easier than, the middle'],
        'instructions': ('Considering the last third of `questions`, how demanding are they compared with '
                         'the rest of the survey?'),
    },
    'B8_scale_direction_consistent': {
        'category': 'structure',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ('One scale runs good→bad, another runs bad→good. Respondents on autopilot will '
                  'answer one of them backwards.'),
        'fix': 'Pick one direction.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'questions',
        'locates': None,
        'source': 'v2',
        'criteria': {'true': 'at least two scales run in opposite directions',
                     'false': 'all scales run the same way'},
        'instructions': ('State field `scales` lists every rating/likert/matrix scale in order with its '
                         'options. Do any two scales run in opposite directions (for example one where the '
                         'first option is the most positive and another where the first option is the most '
                         'negative)?'),
    },
    'C1_objective_coverage': {
        'category': 'coverage',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 4,
        'weight': 4,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'high', 1: 'medium'},
        'roast': {0: "The questions and the stated purpose barely overlap. You'll close this survey "
                     'with data about something else.',
                  1: 'The questions cover part of the purpose. Big pieces of what you said you wanted '
                     'to learn are never asked.'},
        'fix': ('List the 3–5 things the purpose needs to know; make sure each has at least one '
                'question.'),
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['The questions barely touch the stated purpose',
                     'The questions cover part of the purpose; major aspects are missing',
                     'The questions cover the main aspects; minor aspects are missing',
                     'The questions cover the purpose thoroughly'],
        'instructions': ('Given the purpose stated in `title`, `description` and `welcome`, how completely '
                         'do the `questions` cover what that purpose needs?'),
    },
    'C2_has_screener': {
        'category': 'coverage',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': ['research'],
        'severity': {'noul': 'medium'},
        'roast': ("Nothing screens out people who aren't your audience. Every off-target response you "
                  "collect is noise you'll have to explain away."),
        'fix': 'Add a qualifying question early and route non-qualifiers to a polite exit.',
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does the survey contain a question whose answer would identify whether the '
                         'respondent belongs to the intended audience, that is a screening or qualifying '
                         'question?'),
    },
    'C3_has_outcome_question': {
        'category': 'coverage',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 3,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': ['feedback', 'research'],
        'severity': {'noul': 'high'},
        'roast': ("There's no question that measures the thing you actually want to know. Lots of "
                  'context, no verdict.'),
        'fix': 'Add a direct outcome question (intent, preference, likelihood) tied to the purpose.',
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does the survey contain at least one question that directly measures the key '
                         'outcome the purpose implies, for example intent, preference, satisfaction, '
                         'likelihood, or a decision?'),
    },
    'C4_missing_why': {
        'category': 'coverage',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': ['feedback', 'research'],
        'severity': {'noul': 'medium'},
        'roast': ("Closed questions collect the 'what' and never the 'why'. You'll know 40% said "
                  "'unclear' and have no idea what to fix."),
        'fix': ("Add an optional 'Why?' text box after the two or three most decision-relevant "
                'closed questions.'),
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ("Are there closed questions where a respondent's reason would clearly matter to the "
                         "survey's purpose, but no follow-up asks why and no free-text explanation is "
                         'offered?'),
    },
    'C5_obvious_gap': {
        'category': 'coverage',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 3,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': ['assessment', 'feedback', 'research'],
        'severity': {0: 'high', 1: 'low'},
        'roast': {0: "There's an obvious topic your audience would expect and you never ask about it.",
                  1: 'A minor expected topic is missing. Not fatal, but reviewers will ask why.'},
        'fix': ("Ask a colleague what they'd expect this survey to cover; compare against the "
                'question list.'),
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['A major expected topic is absent',
                     'A minor expected topic is absent',
                     'Nothing obviously missing'],
        'instructions': ('Given the purpose, is there an obvious topic that a respondent or a researcher '
                         'would expect to be asked about but that is absent from `questions`?'),
    },
    'C6_demographics_proportionate': {
        'category': 'coverage',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': ['feedback', 'research'],
        'severity': {0: 'medium', 1: 'low'},
        'roast': {0: "The demographics don't match the purpose — either collecting personal data you "
                     "won't use, or missing what you'd need to segment.",
                  1: 'One or two demographics look unnecessary (or one is missing). Every extra '
                     'personal question costs completions.'},
        'fix': 'Keep only the demographics you will actually cut the data by.',
        'fix_by_role': {},
        'funnel': 'continue',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Asks for demographics the purpose does not need, or asks none when analysis '
                     'clearly needs them',
                     'Roughly right, but one or two demographics are unnecessary or missing',
                     'Only the demographics the analysis needs'],
        'instructions': 'Are the demographic questions proportionate to the purpose?',
    },
    'C7_has_attention_check': {
        'category': 'coverage',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': ("A long survey with no attention check. You won't be able to tell careful answers "
                  'from autopilot ones.'),
        'fix': ('Add one instructed-response item mid-survey ("Select \'Agree\' for this row") or a '
                'consistency pair.'),
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'questions',
        'locates': None,
        'source': 'v2',
        'criteria': None,
        'instructions': ('Does the survey contain a question whose purpose is to check that the respondent '
                         'is reading (for example "select \'Agree\' for this item") or a pair of questions '
                         'that should give consistent answers?'),
    },
    'Q1_clarity': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'score',
        'levels': 4,
        'weight': 4,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'high', 1: 'medium'},
        'roast': {0: '{ref} is ambiguous — two respondents could read it two different ways, and '
                     "you'll never know which.",
                  1: '{ref} takes a second read to understand. Every re-read is a respondent deciding '
                     'whether to bother.'},
        'fix': 'Rewrite {ref} as one short sentence with one plain meaning.',
        'fix_by_role': {'information': 'Keep the explanation in {ref}, but end it with one plain line that '
                                       "says what to do next (for example 'Choose what you'd like to do').",
                        'consent': 'State in {ref} exactly what the respondent is agreeing to, in one plain '
                                   'sentence, before the agree/disagree options.'},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Ambiguous or confusing; two readers could reasonably read it differently',
                     'Understandable, but only with effort or re-reading',
                     'Clear',
                     'Clear, concise, and specific about what is wanted'],
        'instructions': ('How clearly would a typical member of the intended audience understand '
                         "`question.label`: what it asks when `question.role` is 'question', or what it "
                         'tells them and what they are meant to do next when `question.role` is '
                         "'information' or 'consent'? Length that explains something clearly is not a "
                         'defect; judge only whether the meaning and the expected action are clear.'),
    },
    'Q2_double_barreled': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'high'},
        'roast': ('{ref} asks two things at once ("{label}"). Anyone who\'d answer them differently '
                  'has nowhere to go.'),
        'fix': 'Split {ref} into one question per thing.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': {'true': "Two distinct things joined by 'and' or 'or', or a two-part question such "
                             "as 'do you have X, and if so, which'",
                     'false': 'One thing is asked'},
        'instructions': ('Does `question.label` ask about two or more separate things that a respondent '
                         'might answer differently?'),
    },
    'Q3a_leading': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'high'},
        'roast': '{ref} leads the witness — the wording nudges respondents toward one answer.',
        'fix': 'Reword {ref} neutrally; drop the loaded or one-sided phrase.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': {'true': "Loaded or one-sided wording, such as 'how much do you like…', 'don't you "
                             "agree…', or an emotive description of one option",
                     'false': 'Neutral wording that gives every answer equal footing'},
        'instructions': ('Does the wording of `question.label` or `question.description` push the respondent '
                         'toward one particular answer through loaded, emotive or one-sided language?'),
    },
    'Q3b_presuming': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'high'},
        'roast': ('{ref} assumes something about the respondent ("{label}"). Anyone it isn\'t true '
                  "for can't answer honestly."),
        'fix': ('Ask the assumption as its own question before {ref} and show {ref} only to those '
                "it applies to (display logic), or add a 'Does not apply' option."),
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': {'true': "Presupposes a fact about the respondent, such as 'assuming you use…', "
                             "'which podcast did you hear us on', or 'how often do you drive your car', "
                             'that nothing earlier establishes',
                     'false': 'No assumption, or the assumption is established by the previous question, '
                              'the group, or the condition under which the question is reached'},
        'instructions': ("Does `question.label` assume something about the respondent's situation, behaviour "
                         'or ownership that may not be true for everyone who sees it, and that '
                         '`previous_question`, `parent_group` and `reached_from` do not establish?'),
    },
    'Q4_jargon': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'score',
        'levels': 3,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium'},
        'roast': {0: "{ref} uses jargon or acronyms with no explanation. Respondents who don't know "
                     'the term will guess.'},
        'fix': 'Define the term inline in {ref} or replace it with plain language.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Uses specialist terms or acronyms with no explanation',
                     'Uses specialist terms but explains them',
                     'Plain language only'],
        'instructions': ('Does `question.label` use terms that the audience described in `survey.purpose`, '
                         'or a general adult if no audience is described, may not understand without an '
                         'explanation? A term is explained when `question.description` or '
                         "`question.previous_question` defines it. Answer 'plain language only' when the "
                         'question itself asks whether the respondent has heard of the term, since defining '
                         'it would defeat the question.'),
    },
    'Q5_relevance': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'score',
        'levels': 3,
        'weight': 3,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium', 1: 'low'},
        'roast': {0: '{ref} has nothing to do with the stated purpose. Cut it or explain it.',
                  1: "{ref} is only loosely connected to the purpose. If you can't say how you'll use "
                     'the answer, drop it.'},
        'fix': ("For {ref}, write the analysis you'd run on the answer; if you can't, remove the "
                'question.'),
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Unrelated to the purpose',
                     'Loosely related; how it would be used in analysis is unclear',
                     'Directly serves the purpose'],
        'instructions': "How relevant is `question` to the survey's `survey.purpose` and `survey.title`?",
    },
    'Q6_options_not_exhaustive': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'options',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ("{ref}'s options don't cover everyone. Respondents with no fitting option pick at "
                  'random or quit.'),
        'fix': "Add an 'Other' / 'None of these' / 'Not sure' option to {ref}, or widen the options.",
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Could a plausible respondent find that none of `question.options` fits them, given '
                         "that there is no 'Other', 'None', 'Not sure' or 'Prefer not to answer' option? "
                         'Consider `has_other`, `has_none` and `has_prefer_not_to_answer`.'),
    },
    'Q7_options_overlap': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'single_choice',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ("{ref}'s options overlap — a respondent could honestly tick two, so the data won't "
                  'be clean.'),
        'fix': "Make {ref}'s options mutually exclusive.",
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Do two or more of `question.options` overlap, so that a respondent could '
                         'truthfully pick more than one when only one is expected?'),
    },
    'Q8_scale_unbalanced': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'scale',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': ("{ref}'s scale is lopsided — more options on one side than the other, so the "
                  'results will lean that way too.'),
        'fix': ("Balance {ref}'s scale: equal positive and negative points, with a neutral midpoint "
                'if appropriate.'),
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Is the answer scale in `question.options` (or `question.columns`) unbalanced, with '
                         'more positive than negative options or vice versa, or with no neutral midpoint '
                         'where one would be expected? Answer no if the options are not an ordered scale at '
                         'all (for example a list of products, places or reasons).'),
    },
    'Q9_type_fit': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'score',
        'levels': 3,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'high', 1: 'low'},
        'roast': {0: "{ref}'s question type contradicts its wording. Respondents will fight the form.",
                  1: '{ref} works, but a different question type would capture the answer better.'},
        'fix': "Change {ref}'s type to match what the wording asks the respondent to do.",
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ["The type conflicts with the wording, for example the wording says 'select all that "
                     "apply' but the type allows one choice, or asks for an explanation but the type is "
                     'a single choice',
                     'Workable, but a more suitable type exists',
                     'The type fits the wording'],
        'instructions': ('Does `question.type` fit what `question.label` asks for? Types: single_choice = '
                         'pick one option; yes_no = answer yes or no; multi_choice = pick several; dropdown '
                         '= pick one from a list; short_text = short free text; long_text = long free text; '
                         'number = a number; matrix = rate several rows on one scale; rating or likert or '
                         'nps or slider = one value on a scale; ranking = order the options; date = a date; '
                         'email = an email address; phone = a phone number; file = a file.'),
    },
    'Q10_depends_on_prior': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'high'},
        'roast': '{ref} only applies after a specific earlier answer, but everyone sees it.',
        'fix': ("Add skip logic so {ref} only shows to the respondents it applies to, or add a 'Not "
                "applicable' option."),
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Is `question` meant only for respondents who gave a specific answer to an earlier '
                         "question (for example it begins 'If yes' or 'If so'), so that a respondent who "
                         'answered that earlier question differently could not answer it truthfully with any '
                         "of `question.options` (or 'Other', 'None' or 'Prefer not to answer' when "
                         '`question.has_other`, `question.has_none` or `question.has_prefer_not_to_answer` '
                         'is true)? Use `question.previous_question` for context. Answer no when the '
                         'question just follows up on an earlier question that everyone answers, for example '
                         "'it' refers to the topic of the previous question, or when an option already fits "
                         "the respondents it does not apply to, such as 'Never', 'None' or 'Not applicable' "
                         'in whatever language the survey uses.'),
    },
    'Q11_requires_visual': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'high'},
        'roast': "{ref} can't be answered without a visual.",
        'fix': ("Describe the visual in {ref}'s text (or its description) so the question stands on "
                'its own.'),
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Can `question.label` only be answered by looking at an image, screen, or video '
                         'that is not described in the text?'),
    },
    'Q12_sensitive': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': ('{ref} asks for sensitive personal information and is required with no way to '
                  'decline.'),
        'fix': "Add a 'Prefer not to answer' option to {ref} or make it optional.",
        'fix_by_role': {},
        'funnel': 'continue',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does `question` ask for sensitive personal information, such as income, health, '
                         'finances, ethnicity, religion, sexuality, precise location, or identifiers, '
                         'without any of `question.options` letting the respondent decline to share it (such '
                         "as 'Prefer not to say' or 'I'd rather not answer', in whatever language the survey "
                         'uses)?'),
    },
    'Q13_grammar': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'score',
        'levels': 3,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium', 1: 'low'},
        'roast': {0: '{ref} has errors that get in the way of understanding it.',
                  1: '{ref} has minor spelling or grammar slips. Small, but respondents judge '
                     'credibility by them.'},
        'fix': 'Proofread {ref}.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Errors that hinder understanding',
                     'Minor errors that do not hinder understanding',
                     'No errors'],
        'instructions': ('Are there spelling, grammar, or punctuation errors in `question.label`, '
                         '`question.description`, or `question.options`?'),
    },
    'Q14_options_parallel': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'options',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': ("{ref}'s options are written in mismatched styles, so they're harder to scan than "
                  'they should be.'),
        'fix': ("Rewrite {ref}'s options in one parallel form (same case, same length, same "
                'grammatical shape).'),
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Are `question.options` written in inconsistent forms, such as mixed sentence '
                         'fragments and full sentences, mixed capitalisation, or mixed tense, in a way that '
                         'makes them harder to scan?'),
    },
    'Q15_abandon_risk': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'score',
        'levels': 3,
        'weight': 3,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'high'},
        'roast': {0: '{ref} ("{label}") asks for more than you\'ve earned at this point. That\'s '
                     'where the funnel dies.'},
        'fix': "Make {ref} optional, move it to the end, or explain why it's needed.",
        'fix_by_role': {},
        'funnel': 'continue',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': ['Very likely to quit: demanding (long free text, file upload, ranking many items, '
                     'big matrix) or intrusive (contact details, income, health) and required',
                     'Some friction: demanding or intrusive but optional, or mildly demanding and '
                     'required',
                     'Little friction: quick and unintrusive'],
        'instructions': ('If a respondent has reached `question`, how likely are they to close the survey '
                         'here rather than answer it? Consider effort, intrusiveness and whether it is '
                         '`question.required`.'),
    },
    'Q16_sensitive_reassured': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ("{ref} asks something sensitive without a word on why it's needed or who will see "
                  'the answer.'),
        'fix': ("Add one line to {ref}'s description: why you ask, that it's optional, and who sees "
                'the answer.'),
        'fix_by_role': {},
        'funnel': 'continue',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': None,
        'instructions': ('Does `question.description` or `question.label` reassure the respondent about how '
                         'this sensitive answer will be handled (anonymous, confidential, optional, why it '
                         'is needed)?'),
    },
    'Q17_negative_wording': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'scale',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ('{ref} is worded in the negative ("{label}"). Agreeing means disagreeing, and some '
                  'respondents will get it backwards.'),
        'fix': 'Reword {ref} positively so agreeing means what it sounds like.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': None,
        'instructions': ('Is `question.label` phrased negatively or with a double negative (for example "I '
                         'do not find it hard to…", "It is not unusual that…") so that agreeing means the '
                         'opposite of what it sounds like?'),
    },
    'Q18_hypothetical': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': ('Your only outcome measure is a hypothetical. Stated intent over-predicts real '
                  'behaviour.'),
        'fix': ('Add an outcome question about actual behaviour or current opinion (what they did, '
                'use or think now).'),
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': {'true': 'asks about a hypothetical or future action',
                     'false': 'asks about actual behaviour, experience or current opinion'},
        'instructions': ('Does `question.label` ask what the respondent *would* do, buy, or feel in a '
                         'situation they have not been in, rather than what they have done or currently '
                         'think?'),
    },
    'Q19_recall_period': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'choice',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'missing_but_needed': 'medium'},
        'roast': {'missing_but_needed': '{ref} "{label}" — per week? ever? Add a window.'},
        'fix': 'Add a time window to {ref} ("in the last 30 days").',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': {'stated': 'a time window is given ("in the last 30 days", "since January", "at your '
                               'last visit")',
                     'missing_but_needed': 'it asks about frequency, amount or experience over time but '
                                           'gives no window',
                     'not_applicable': 'the question is not about behaviour over time (opinion, fact '
                                       'about the person, one-off event with an obvious time)'},
        'instructions': ("`question.label` asks about the respondent's behaviour, frequency or experience "
                         'over time. Which applies?'),
    },
    'Q20_option_double_barreled': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'options',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ("One of {ref}'s options bundles two things. Anyone who feels differently about each "
                  'half has nowhere to go.'),
        'fix': ('Split the combined option in {ref} into separate options, or keep only the half '
                'you need.'),
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': None,
        'instructions': ('Do any of `question.options` combine two separate things that a respondent might '
                         'feel differently about (for example "Fast and affordable", "Friendly and '
                         'knowledgeable staff")?'),
    },
    'Q21_social_desirability': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': "{ref} has an obviously 'right' answer. People will give it whether or not it's true.",
        'fix': 'Indirect phrasing ("Some people… how about you?") or normalising preamble.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': {'true': 'one answer is clearly the approved one',
                     'false': 'no answer is socially favoured'},
        'instructions': ('Is there an obviously "good" or socially approved answer to `question.label` such '
                         'that respondents may answer to look good rather than truthfully?'),
    },
    'Q22_units_stated': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'quantity',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': '{ref} asks "{label}" — per week? per month? in what currency?',
        'fix': 'State the unit or format in {ref} ("in £ per month", "DD/MM/YYYY").',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': None,
        'instructions': ('Where `question` asks for a number, amount, date or duration, is the expected unit '
                         'or format clear from `question.label`, `question.description` or the scale labels '
                         '(for example "in £", "per month", "DD/MM/YYYY", "hours per week")?'),
    },
    'Q23_actionable': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'score',
        'levels': 3,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'low'},
        'roast': {0: "{ref} is a 'nice to know'. If no decision changes based on the answer, cut it — "
                     'every question costs completions.'},
        'fix': "Write down the decision {ref} informs; if there isn't one, remove it.",
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': ['No decision would change whatever the answers are (nice-to-know only)',
                     'Loosely informs a decision but the owner would need to ask something else to act',
                     'The answer directly informs a specific decision or change'],
        'instructions': ('If the survey owner saw the distribution of answers to `question`, could they make '
                         'a decision or take an action because of it, given `survey.purpose`?'),
    },
    'Q24_intent': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'choice',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'choice': 'info'},
        'roast': None,
        'fix': None,
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': {'screener': 'decides whether the respondent belongs in the survey or a section',
                     'demographic': 'age, gender, location, income, job, tenure',
                     'behaviour': 'what the respondent does or has done',
                     'attitude': 'opinion, satisfaction, agreement, preference',
                     'outcome': 'the key measure the purpose implies (intent, NPS, overall satisfaction, '
                                'decision)',
                     'open_feedback': 'free-text comments',
                     'contact_or_admin': 'email, phone, consent, name',
                     'instruction_only': 'not really a question (a statement disguised as one)'},
        'instructions': 'What role does `question` play in the survey?',
    },
    'Q25_best_type': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'choice',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'any_other': 'medium'},
        'roast': {'any_other': '{ref} ("{label}") is a {type} but the answer would be easier to '
                               'analyse as a {choice}.'},
        'fix': 'Change {ref} to a {choice} question.',
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'question',
        'locates': None,
        'source': 'v2',
        'criteria': {'single_choice': 'pick exactly one of a few options',
                     'multi_choice': 'pick any number of options',
                     'dropdown': 'pick one from a long list (roughly 8 or more, e.g. country)',
                     'rating': 'how much/how satisfied on a short scale',
                     'nps': 'likelihood to recommend on 0–10',
                     'matrix': 'rate several listed items on the same scale',
                     'ranking': 'order several items',
                     'number': 'a numeric amount',
                     'date': 'a date',
                     'short_text': 'a short free answer that cannot be listed in advance',
                     'long_text': "an explanation or opinion in the respondent's own words",
                     'email': 'contact detail: an email address',
                     'phone': 'contact detail: a phone number',
                     'current_type_is_best': 'the existing `question.type` is the right one'},
        'instructions': ('Given what `question.label` asks for and its current `question.type`, which '
                         'question type would capture the answer best for analysis?'),
    },
    'E1_tone_consistent': {
        'category': 'experience',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium', 1: 'low'},
        'roast': {0: 'The survey changes voice mid-way — it reads like three people wrote it and '
                     'nobody edited.',
                  1: 'Mostly one voice, with a few slips in tone or person.'},
        'fix': 'Pick one voice (second person, one formality level) and edit every screen to match.',
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Mixed voices or registers that feel like different authors',
                     'Mostly consistent with a few slips',
                     'Consistent throughout'],
        'instructions': ('How consistent are voice and register across `questions`, `welcome` and '
                         "`thank_you`, for example consistently addressing the respondent as 'you' and "
                         'keeping the same level of formality?'),
    },
    'E2_burden': {
        'category': 'experience',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ("Some questions expect people to recall or calculate things they won't know "
                  "offhand. They'll guess, and you'll analyse the guesses."),
        'fix': ("Offer ranges or 'not sure' options, or drop the question if the precise answer "
                "isn't essential."),
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Do any questions ask the respondent to recall, look up, or calculate something '
                         'they are unlikely to know offhand?'),
    },
    'E3_thank_you_quality': {
        'category': 'experience',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium', 1: 'low'},
        'roast': {0: 'The survey ends with a shrug. No thanks, no what-next.',
                  1: 'The thank-you is polite but tells people nothing about what happens with their '
                     'input.'},
        'fix': ('Add one line on what happens next: when results are shared, how the incentive is '
                'paid, or who to contact.'),
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'thank_you',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Missing, or a bare thank-you with nothing else',
                     'Thanks the respondent',
                     'Thanks the respondent and says what happens next, for example results, an '
                     'incentive, or a contact'],
        'instructions': 'How well does `thank_you` close the survey?',
    },
    'E4_welcome_motivates': {
        'category': 'experience',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium', 1: 'low'},
        'roast': {0: "The welcome screen leads with rules and restrictions. It's a bouncer, not a "
                     'host.',
                  1: 'The welcome is polite but gives nobody a reason to care.'},
        'fix': 'Lead with why their input matters; put rules and requirements after that, briefly.',
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Cold or bureaucratic, or lists only rules and restrictions',
                     'Polite but flat',
                     "Explains why the respondent's input matters and sets a friendly tone"],
        'instructions': 'How motivating is the `welcome` text for someone deciding whether to start?',
    },
    'E5_reading_level': {
        'category': 'experience',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium', 1: 'low'},
        'roast': {0: 'The text reads like a policy document. Respondents skim, misread, and answer '
                     'the question they think you asked.',
                  1: 'Some passages are heavy going. Each one is a place people slow down or bail.'},
        'fix': 'Shorten sentences, swap jargon for plain words, and define any term you must keep.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Dense, with long sentences and technical vocabulary throughout',
                     'Some passages are demanding',
                     'Plain language throughout'],
        'instructions': 'How demanding is the reading level of the survey text for a general adult audience?',
    },
    'E6_length_feels_justified': {
        'category': 'experience',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'high', 1: 'low'},
        'roast': {0: 'This is far longer than its purpose warrants. Completion rates fall off a cliff '
                     'after ~20 questions.',
                  1: "A bit long for what it's trying to learn. Every non-essential question is paid "
                     'for in drop-offs.'},
        'fix': ("Cut questions that don't map to a decision; aim for the shortest survey that "
                'answers the objective.'),
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': ['Far longer than the purpose warrants',
                     'Somewhat long for the purpose',
                     'An appropriate length for the purpose'],
        'instructions': ('Given the stated purpose, does the number of questions feel justified to a '
                         'respondent? `stats.answerable_questions` is the count of questions they must '
                         'answer.'),
    },
    'E7_welcome_scannable': {
        'category': 'experience',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium'},
        'roast': {0: 'The welcome screen is a wall with the useful bits buried inside. On a phone, '
                     'nobody digs.'},
        'fix': ("Cut the welcome to three short lines: why you're asking, how long it takes, what "
                'happens to the answers.'),
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'v2',
        'criteria': ['One or more dense paragraphs; key facts (purpose, time, privacy) are buried',
                     'Readable but longer than needed',
                     'Short, with the purpose, time and privacy each findable in a sentence or bullet'],
        'instructions': 'How easy is the `welcome` text to take in at a glance on a phone screen?',
    },
    'E8_straightlining_risk': {
        'category': 'experience',
        'scope': 'survey',
        'primitive': 'score',
        'levels': 3,
        'weight': 2,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {0: 'medium'},
        'roast': {0: 'Long runs of identical scales in a row. Halfway through, people stop reading.'},
        'fix': 'Break batteries with a different type, reverse-key one item, or cut.',
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'questions',
        'locates': None,
        'source': 'v2',
        'criteria': ['Long runs of identically formatted items (matrix rows or repeated scales) with '
                     'similar wording',
                     'Some repeated formats but broken up by different question types',
                     'Formats vary; no long run of look-alike items'],
        'instructions': ('Looking at the sequence of `questions`, how likely is a tired respondent to start '
                         'giving the same answer to every item without reading?'),
    },
    'E9_language_consistent': {
        'category': 'experience',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': ('The survey switches language or spelling mid-way (colour, color). Respondents '
                  'notice, and it reads as unedited.'),
        'fix': 'Pick one language and one spelling system and edit every screen to match.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'survey',
        'locates': None,
        'source': 'v2',
        'criteria': {'true': 'mixed languages or spelling systems',
                     'false': 'one language and one spelling system throughout'},
        'instructions': ('Are the `questions`, `welcome` and `thank_you` written in a mix of languages, or a '
                         'mix of spelling systems (for example British and American English), that a '
                         'respondent would notice?'),
    },
    'F1_sensitive_topics': {
        'category': 'trust',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': ("The survey asks about sensitive personal matters. That's fine — but only with a "
                  'privacy line and a way to skip.'),
        'fix': "Add a privacy statement and a 'prefer not to say' option on sensitive questions.",
        'fix_by_role': {},
        'funnel': 'continue',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does the survey ask about sensitive personal matters such as finances, health, '
                         'ethnicity, religion, sexuality, legal issues, or precise location?'),
    },
    'F2_consent_language': {
        'category': 'trust',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': ['research'],
        'severity': {'noul': 'low'},
        'roast': ("No consent language anywhere. For research with real people that's a compliance "
                  'gap, not a style choice.'),
        'fix': ('Add a line: participation is voluntary, you can stop at any time, continuing means '
                'you agree.'),
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does the welcome or description contain consent language, for example that '
                         'participation is voluntary, that the respondent can withdraw, or that continuing '
                         'means they agree?'),
    },
    'F3_incentive_clear': {
        'category': 'trust',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': "An incentive is mentioned but how to claim it isn't clear. Expect support emails.",
        'fix': 'State exactly how and when the incentive is delivered, on the thank-you screen.',
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'thank_you',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('If an incentive or reward is mentioned anywhere in the survey text, is it clear '
                         'how the respondent receives it? Answer yes if no incentive is mentioned at all.'),
    },
    'F3a_incentive_mentioned': {
        'category': 'trust',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': None,
        'fix': None,
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'thank_you',
        'locates': None,
        'source': 'v2',
        'criteria': None,
        'instructions': ('Is an incentive, reward, prize draw or payment for completing the survey mentioned '
                         'anywhere in `welcome`, `description` or `thank_you`?'),
    },
    'F3b_incentive_delivery_clear': {
        'category': 'trust',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': "An incentive is mentioned but how to claim it isn't clear. Expect support emails.",
        'fix': 'State exactly how and when the incentive is delivered, on the thank-you screen.',
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'thank_you',
        'locates': None,
        'source': 'v2',
        'criteria': None,
        'instructions': ('Where an incentive is mentioned, does the text say how and when the respondent '
                         'receives it?'),
    },
    'F4_manipulative_framing': {
        'category': 'trust',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': False,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'medium'},
        'roast': ('Some of the wording leans on respondents — guilt, urgency or flattery. It biases '
                  'answers and people notice.'),
        'fix': 'Keep framing neutral; motivate with purpose, not pressure.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does any welcome, description, or question text pressure the respondent toward a '
                         'particular answer or toward completing, for example through guilt, urgency, or '
                         'flattery?'),
    },
    'F5_contact_provided': {
        'category': 'trust',
        'scope': 'survey',
        'primitive': 'noul',
        'levels': None,
        'weight': 1,
        'good_when_yes': True,
        'informational': False,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'low'},
        'roast': ('No way to reach whoever runs this. Questions go unanswered, and trust goes with '
                  'them.'),
        'fix': ('Add a contact line to the welcome or thank-you screen ("Questions? Email '
                'research@yourco.com").'),
        'fix_by_role': {},
        'funnel': 'start',
        'target': 'welcome',
        'locates': None,
        'source': 'v2',
        'criteria': None,
        'instructions': ('Does any `welcome.description`, `description` or `thank_you` give a way to contact '
                         'the survey owner (email, name, link)?'),
    },
    'L_needs_why': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'with_options_or_columns',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': '{ref} "{label}": add an optional \'Why?\' text box after it.',
        'fix': '{ref} "{label}": add an optional \'Why?\' text box after it.',
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'question',
        'locates': 'C4_missing_why',
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Is `question` a closed question (options, scale, or matrix) whose answer would '
                         "leave the survey's purpose unexplained without knowing the respondent's reason, "
                         'and there is no free-text follow-up asking why?'),
    },
    'L_hard_to_recall': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': '{ref} "{label}": offer ranges or a \'Not sure\' option, or drop the precision.',
        'fix': '{ref} "{label}": offer ranges or a \'Not sure\' option, or drop the precision.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': 'E2_burden',
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does `question` ask the respondent to recall, look up, or calculate something a '
                         'typical person would not know offhand (exact figures, dates, totals, past '
                         'details)?'),
    },
    'L_topic_jump': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': ('{ref} "{label}": move it next to related questions, or add a short section intro '
                  'before it.'),
        'fix': ('{ref} "{label}": move it next to related questions, or add a short section intro '
                'before it.'),
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'question',
        'locates': 'B1_logical_order',
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does `question` switch to a clearly different topic from `previous_question` '
                         'without any transition?'),
    },
    'L_is_demographic': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': '{ref} "{label}": move it to the end of the survey or explain why it is asked.',
        'fix': '{ref} "{label}": move it to the end of the survey or explain why it is asked.',
        'fix_by_role': {},
        'funnel': 'continue',
        'target': 'question',
        'locates': 'B3_demographics_placement',
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Is `question` a demographic or background question (age, gender, income, '
                         'education, employment, location, household)?'),
    },
    'L_pressuring': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': '{ref} "{label}": reword neutrally.',
        'fix': '{ref} "{label}": reword neutrally.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': 'F4_manipulative_framing',
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does the wording of `question` pressure the respondent toward an answer or toward '
                         'continuing, through guilt, urgency, or flattery?'),
    },
    'L_hard_to_read': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': '{ref} "{label}": shorten the sentence and use plain words.',
        'fix': '{ref} "{label}": shorten the sentence and use plain words.',
        'fix_by_role': {},
        'funnel': 'answer_quality',
        'target': 'question',
        'locates': 'E5_reading_level',
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Is `question.label` (with `question.description`) hard to read for a general '
                         'adult: long sentences, dense wording, or technical vocabulary?'),
    },
    'L_sensitive_topic': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': '{ref} "{label}": add a \'Prefer not to say\' option and a privacy line.',
        'fix': '{ref} "{label}": add a \'Prefer not to say\' option and a privacy line.',
        'fix_by_role': {},
        'funnel': 'continue',
        'target': 'question',
        'locates': 'F1_sensitive_topics',
        'source': 'shipped-1.2',
        'criteria': None,
        'instructions': ('Does `question` ask about a sensitive personal matter (finances, health, '
                         'ethnicity, religion, sexuality, legal issues, precise location)?'),
    },
    'L_duplicate_of_earlier': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'noul',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'noul': 'info'},
        'roast': ('{ref} "{label}": merge it with the earlier question that asks the same thing, or '
                  'reword it to ask something distinct.'),
        'fix': ('{ref} "{label}": merge it with the earlier question that asks the same thing, or '
                'reword it to ask something distinct.'),
        'fix_by_role': {},
        'funnel': 'finish',
        'target': 'question',
        'locates': 'B5_redundant_questions',
        'source': 'shipped-1.2',
        'criteria': {'true': 'An earlier entry already collects this same answer, only worded '
                             'differently or at a different granularity',
                     'false': 'No earlier entry asks for this; it is a related but distinct question, or '
                              'the first of its kind'},
        'instructions': ('Does `question` ask for the same fact or opinion as an entry that appears before '
                         'it in the `questions` list, so a respondent who answered the earlier one would be '
                         'repeating themselves?'),
    },
    'C5_gap_topic': {
        'category': 'coverage',
        'scope': 'survey',
        'primitive': 'choice',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {},
        'roast': None,
        'fix': None,
        'fix_by_role': {},
        'funnel': 'actionability',
        'target': 'questions',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': {'none': 'Nothing obviously missing given the stated purpose',
                     'screening': 'A qualifying question that confirms the respondent belongs to the '
                                  'intended audience',
                     'current_behaviour': 'What the respondent currently does or uses (frequency, '
                                          'habits, current provider or product)',
                     'satisfaction': 'How satisfied they are with the current experience, product or '
                                     'service',
                     'pain_points': 'What frustrates them, what goes wrong, or what is hard',
                     'needs': 'What they need, expect or value most',
                     'intent': 'Whether they would buy, switch, recommend, or continue (likelihood or '
                               'intent)',
                     'preference': 'Which option, feature or design they prefer, or how they compare '
                                   'alternatives',
                     'pricing': 'Willingness to pay, budget, or price sensitivity',
                     'awareness': 'How they heard about it, or what they already know',
                     'open_feedback': 'A free-text question for anything the survey did not cover',
                     'demographics': 'Background facts needed to segment the analysis (age, role, '
                                     'region…)',
                     'follow_up_consent': 'Permission or contact details for follow-up',
                     'experience_outcome': 'How something went for them or what the result was (an '
                                           'experience, visit, event, treatment or course)',
                     'understanding': 'What they understood or know about the subject, or what is still '
                                      'unclear to them',
                     'concerns_risks': 'Worries, risks, side-effects or safety questions they have',
                     'logistics': 'Practical details such as timing, location, access or availability',
                     'suggestions': 'What would make it better or what they would change',
                     'other_unlisted': 'Something important is missing but it is not one of the topics '
                                       'listed here'},
        'instructions': ('Given the purpose stated in `title`, `description` and `welcome`, which expected '
                         "topic is most clearly absent from `questions`? Choose 'none' if nothing important "
                         'is missing.'),
    },
    'K_survey_kind': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'choice',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {},
        'roast': None,
        'fix': None,
        'fix_by_role': {},
        'funnel': None,
        'target': 'survey',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': {'research': 'Market, user or academic research: it measures opinions, behaviour, '
                                 'preference or intent across respondents to inform a decision',
                     'feedback': 'Feedback or satisfaction on a product, service, event, course or '
                                 'experience (CSAT, NPS, post-event)',
                     'form': 'A form that collects details from each person: registration, application, '
                             'intake, booking, order, contact details',
                     'quiz': 'A quiz, test or exam with right and wrong answers',
                     'assessment': 'A self-assessment, screening or check-in that gives the respondent '
                                   'guidance about themselves (health, wellbeing, readiness, skills)',
                     'information': 'Mostly information, consent or instructions for the respondent, '
                                    'with little or nothing measured'},
        'instructions': ('Judging by `title`, `description`, `welcome` and the `questions` (their `role` and '
                         'content), which kind of survey is this?'),
    },
    'X2_audience_kind': {
        'category': 'purpose',
        'scope': 'survey',
        'primitive': 'choice',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {'choice': 'info'},
        'roast': None,
        'fix': None,
        'fix_by_role': {},
        'funnel': None,
        'target': 'survey',
        'locates': None,
        'source': 'v2',
        'criteria': {'existing_customers': 'People who already use the product or service the survey is '
                                           'about',
                     'prospects_or_general_public': 'Potential customers or members of the public with '
                                                    'no existing relationship',
                     'employees': 'Staff of the organisation running the survey',
                     'students': 'Students or learners on a course or programme',
                     'experts_or_professionals': 'Practitioners or specialists answering from '
                                                 'professional knowledge',
                     'event_attendees': 'People who attended a specific event, webinar or session',
                     'unclear': 'The intended respondents cannot be told from the survey'},
        'instructions': ('Judging by `title`, `description`, `audience`, `welcome` and the `questions`, who '
                         'is this survey meant to be answered by?'),
    },
    'R_role': {
        'category': 'questions',
        'scope': 'question',
        'primitive': 'choice',
        'levels': None,
        'weight': 0,
        'good_when_yes': False,
        'informational': True,
        'applies': 'all',
        'kinds': None,
        'severity': {},
        'roast': None,
        'fix': None,
        'fix_by_role': {},
        'funnel': None,
        'target': 'question',
        'locates': None,
        'source': 'shipped-1.2',
        'criteria': {'question': 'Asks the respondent for a fact, opinion, rating, choice or free text '
                                 'that will be analysed',
                     'information': 'Mainly tells or explains something; any options only acknowledge it '
                                    "or pick what to do next (for example 'Got it', 'I understand', "
                                    "'Tell me more')",
                     'consent': 'Asks for agreement or permission: consent, terms, acknowledgement of a '
                                'policy'},
        'instructions': ('What is `question` for? Decide from `question.label`, `question.description` and '
                         '`question.options`.'),
    },
}

SURVEY_ITEM_IDS = [i for i, it in ITEMS.items() if it["scope"] == "survey"]
QUESTION_ITEM_IDS = [i for i, it in ITEMS.items() if it["scope"] == "question"]
SURVEY_KINDS = tuple(ITEMS["K_survey_kind"]["criteria"])
AUDIENCE_KINDS = tuple(ITEMS["X2_audience_kind"]["criteria"])
GAP_TOPICS = dict(ITEMS["C5_gap_topic"]["criteria"])


# --- small pure helpers (scoring.md#from-answer-to-value) -------------------------------------

def normalise_score(level: int, levels: int) -> float:
    """Score level -> value in [0, 1] (0 = worst level)."""
    return max(0.0, min(1.0, level / (levels - 1))) if levels > 1 else 1.0


def normalise_noul(p: float, good_when_yes: bool) -> float:
    """Noul p -> value in [0, 1] (1 = best)."""
    return p if good_when_yes else 1.0 - p


def grade_for(score: int, has_blocker: bool) -> Tuple[str, str]:
    """(grade, verdict) for an overall score (scoring.md#overall-grade-and-verdict)."""
    if has_blocker:
        return "F", "not_ready"
    grade = next((g for floor, g in GRADES if score >= floor), "F")
    if score < NOT_READY_BELOW:
        return grade, "not_ready"
    return grade, "ready" if score >= READY_AT else "needs_work"


def weight_profile(kind: Optional[str], audience: Optional[str]) -> str:
    """Weight profile from survey kind x audience (scoring.md#weight-profiles)."""
    if kind == "research":
        return {"employees": "employee_engagement", "students": "academic_research"}.get(audience, "market_research")
    if kind == "feedback":
        return {"employees": "employee_engagement", "event_attendees": "event_feedback"}.get(
            audience, "customer_satisfaction")
    if kind == "form":
        return "lead_generation" if audience == "prospects_or_general_public" else "registration_or_form"
    return "default"


_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def render(text: Any, ctx: Dict[str, Any]) -> str:
    """Fill {placeholders} present in ctx; leave unknown ones as they are."""
    return _PLACEHOLDER.sub(lambda m: str(ctx[m.group(1)]) if m.group(1) in ctx else m.group(0), _text(text))


def _fmt_num(x: Any) -> str:
    n = _num(x)
    if n is None:
        return "a few"
    n = round(float(n), 1)
    return str(int(n)) if n == int(n) else str(n)


def _weighted_mean(pairs: List[Tuple[float, float]]) -> Optional[float]:
    total = sum(w for w, _ in pairs)
    return sum(w * v for w, v in pairs) / total if total > 0 else None


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# --- judgments: parse and validate ------------------------------------------------------------

def _confidence(x: Any) -> float:
    n = _num(x)
    return DEFAULT_CONFIDENCE if n is None else _clamp01(float(n))


def parse_answer(item_id: str, raw: Any) -> Tuple[Optional[Dict[str, Any]], bool]:
    """-> (answer, invalid). An answer of the wrong shape is (None, True): treated as missing."""
    item = ITEMS[item_id]
    if raw is None:
        return None, False
    if not isinstance(raw, dict):
        return None, True
    prim = item["primitive"]
    if prim == "score":
        n = _num(raw.get("level"))
        if n is None or n != int(n) or not 0 <= n <= item["levels"] - 1:
            return None, True
        return {"level": int(n), "confidence": _confidence(raw.get("confidence"))}, False
    if prim == "noul":
        p = _num(raw.get("p"))
        if p is None or not 0 <= p <= 1:
            return None, True
        return {"p": float(p)}, False
    choice = raw.get("choice")
    if not isinstance(choice, str) or choice not in (item["criteria"] or {}):
        return None, True
    return {"choice": choice, "confidence": _confidence(raw.get("confidence"))}, False


def value_of(item_id: str, ans: Optional[Dict[str, Any]], qtype: Optional[str] = None
             ) -> Tuple[Optional[float], float]:
    """(value in [0, 1] or None, certainty in [0, 1])."""
    if not ans:
        return None, 0.0
    item = ITEMS[item_id]
    prim = item["primitive"]
    if prim == "score":
        return normalise_score(ans["level"], item["levels"]), ans["confidence"]
    if prim == "noul":
        p = ans["p"]
        return normalise_noul(p, item["good_when_yes"]), min(1.0, abs(p - 0.5) / 0.5)
    if item_id == "Q19_recall_period":
        return (0.0 if ans["choice"] == "missing_but_needed" else 1.0), ans["confidence"]
    if item_id == "Q25_best_type":
        if ans["confidence"] < SCORE_CONFIDENT:
            return None, 0.0
        return (1.0 if ans["choice"] in ("current_type_is_best", qtype) else 0.0), ans["confidence"]
    return None, 0.0


def evidence_weight(item_id: str, certainty: float) -> float:
    w = ITEMS[item_id]["weight"]
    return w * certainty if certainty >= MIN_CERTAINTY else 0.0


def _scored(item_id: str) -> bool:
    it = ITEMS[item_id]
    return not it["informational"] and it["weight"] > 0


# --- the calculation context ------------------------------------------------------------------

class _Ctx:
    """Everything calc() derives once: normalised survey, parsed judgments, roles, kind, profile."""

    def __init__(self, survey: Any, judgments: Any):
        self.s = normalise_survey(survey)
        self.qs: List[Dict] = self.s["questions"]
        self.by_ref = {q["ref"]: q for q in self.qs}
        self.answerable = [q for q in self.qs if is_answerable(q)]
        self.answerable_index = {q["ref"]: i for i, q in enumerate(self.answerable)}
        self.position = {q["ref"]: i for i, q in enumerate(self.qs)}
        self.title = self.s["title"]
        self.stated_minutes = _fmt_num(self.s["settings"].get("stated_minutes"))
        self.invalid: List[str] = []
        self.bad_judgments = not isinstance(judgments, dict)
        j = judgments if isinstance(judgments, dict) else {}
        self.sj: Dict[str, Dict] = {}
        raw_survey = j.get("survey")
        if raw_survey is not None and not isinstance(raw_survey, dict):
            self.bad_judgments = True
        for iid, raw in _d(raw_survey).items():
            if iid in ITEMS and ITEMS[iid]["scope"] == "survey":
                ans, bad = parse_answer(iid, raw)
                if bad:
                    self.invalid.append(iid)
                elif ans:
                    self.sj[iid] = ans
        self.qj: Dict[str, Dict[str, Dict]] = {}
        raw_questions = j.get("questions")
        if raw_questions is not None and not isinstance(raw_questions, dict):
            self.bad_judgments = True
        for ref, answers in _d(raw_questions).items():
            if ref not in self.by_ref:
                continue                                   # unknown refs are ignored
            if not isinstance(answers, dict):
                self.invalid.append(f"{ref}:*")
                continue
            parsed = {}
            for iid, raw in answers.items():
                if iid in ITEMS and ITEMS[iid]["scope"] == "question":
                    ans, bad = parse_answer(iid, raw)
                    if bad:
                        self.invalid.append(f"{ref}:{iid}")
                    elif ans:
                        parsed[iid] = ans
            self.qj[ref] = parsed

        # roles: R_role judgment, else the survey's own role
        self.role: Dict[str, str] = {}
        for q in self.qs:
            r = self.qa(q["ref"], "R_role")
            role = r["choice"] if r else q["role"]
            self.role[q["ref"]] = role if role in ROLES else "question"

        # kind, audience, profile
        k = self.sa("K_survey_kind")
        if j.get("survey_kind") in SURVEY_KINDS:
            self.kind = j["survey_kind"]
        elif k and k["confidence"] >= GAP_TOPIC_CONFIDENT:
            self.kind = k["choice"]
        elif self.s["kind"] in SURVEY_KINDS:
            self.kind = self.s["kind"]
        else:
            self.kind = None
        a = self.sa("X2_audience_kind")
        if j.get("audience_kind") in AUDIENCE_KINDS:
            self.audience = j["audience_kind"]
        elif a and a["confidence"] >= GAP_TOPIC_CONFIDENT:
            self.audience = a["choice"]
        else:
            self.audience = "unclear"
        self.profile = weight_profile(self.kind, self.audience)
        self.weights = WEIGHT_PROFILES[self.profile]

    # answers
    def sa(self, iid: str) -> Optional[Dict]:
        return self.sj.get(iid)

    def qa(self, ref: str, iid: str) -> Optional[Dict]:
        return self.qj.get(ref, {}).get(iid)

    def qp(self, ref: str, iid: str) -> Optional[float]:
        a = self.qa(ref, iid)
        return a["p"] if a and "p" in a else None

    # applicability
    def kind_ok(self, iid: str) -> bool:
        kinds = ITEMS[iid]["kinds"]
        return self.kind is None or kinds is None or self.kind in kinds

    def survey_item_applies(self, iid: str) -> bool:
        if not self.kind_ok(iid):
            return False
        if iid == "C7_has_attention_check":
            return len(self.answerable) > 25
        if iid == "F3b_incentive_delivery_clear":
            f3a = self.sa("F3a_incentive_mentioned")
            return bool(f3a) and f3a["p"] >= NOUL_YES
        if iid == "F3_incentive_clear":
            return not (self.sa("F3a_incentive_mentioned") and self.sa("F3b_incentive_delivery_clear"))
        return True

    def question_item_applies(self, iid: str, q: Dict) -> bool:
        if not self.kind_ok(iid):
            return False
        if not is_answerable(q):
            return iid in NON_ANSWERABLE_ITEMS
        if self.role[q["ref"]] != "question":
            return iid in NON_QUESTION_ITEMS
        if q["shown_when"]:
            if iid == "Q3b_presuming":
                return False
            if iid == "Q5_relevance" and any(self.position.get(r, 1 << 30) < self.position[q["ref"]]
                                             for r in q["shown_when_refs"]):
                return False
        if iid == "Q16_sensitive_reassured":
            p = self.qp(q["ref"], "Q12_sensitive")
            if p is None or p < NOUL_YES:
                return False
        t = q["type"]
        has_options = bool(q["options"]) or bool(q["columns"])
        applies = ITEMS[iid]["applies"]
        if applies in ("options", "with_options_or_columns"):
            return has_options
        if applies == "single_choice":
            return bool(q["options"]) and t in SINGLE_CHOICE_TYPES
        if applies == "scale":
            is_scale = t in SCALE_TYPES or (t in ("single_choice", "dropdown") and len(q["options"]) >= 3)
            return is_scale and has_options
        if applies == "text":
            return t in ("short_text", "long_text")
        if applies == "quantity":
            return t in QUANTITY_TYPES
        return True

    def items_for(self, q: Dict) -> List[str]:
        return [i for i in QUESTION_ITEM_IDS if self.question_item_applies(i, q)]

    def render_ctx(self, q: Optional[Dict] = None, **extra) -> Dict[str, Any]:
        ctx = {"title": self.title, "stated_minutes": self.stated_minutes}
        if q is not None:
            ctx.update(ref=q["ref"], label=q["label"][:80], type=q["type"])
        ctx.update(extra)
        return ctx

    def gap_named(self) -> bool:
        gap = self.sa("C5_gap_topic")
        return bool(gap and gap["choice"] not in ("none", "other_unlisted")
                    and gap["confidence"] >= GAP_TOPIC_CONFIDENT)

    def intent(self, q: Dict) -> Optional[str]:
        if q["intent"]:
            return q["intent"]
        a = self.qa(q["ref"], "Q24_intent")
        return a["choice"] if a and a["confidence"] >= SCORE_CONFIDENT else None

    def missing_items(self) -> List[str]:
        out = list(self.invalid)
        for iid in SURVEY_ITEM_IDS:
            if iid != "F3_incentive_clear" and _scored(iid) and self.survey_item_applies(iid) \
                    and iid not in self.sj and iid not in out:
                out.append(iid)
        for q in self.qs:
            for iid in self.items_for(q):
                name = f"{q['ref']}:{iid}"
                if _scored(iid) and self.qa(q["ref"], iid) is None and name not in out:
                    out.append(name)
        return out


# --- findings -----------------------------------------------------------------------------------

def _finding(fid: str, severity: str, category: str, scope: str, roast: str, fix: str, q: Optional[Dict] = None,
             evidence: Optional[Dict] = None, uncertain: bool = False, target: Optional[str] = None,
             question_refs: Optional[List[str]] = None, checklist: Optional[List[str]] = None,
             funnel: Optional[str] = None, weight: float = 1.0) -> Dict[str, Any]:
    return {"id": fid, "severity": severity, "category": category, "scope": scope,
            "question_ref": q["ref"] if q else None, "question_label": q["label"] if q else None,
            "roast": roast, "fix": fix, "evidence": evidence or {}, "uncertain": uncertain,
            "question_refs": question_refs if question_refs is not None else ([q["ref"]] if q else []),
            "checklist": checklist if checklist is not None else [], "target": target, "funnel": funnel,
            "_weight": weight}


def _base_severity(ctx: _Ctx, iid: str, sev: str, q: Optional[Dict], level: Optional[int] = None) -> str:
    """Item-specific severity rules (scoring.md#item-specific-severity-rules)."""
    if iid == "Q15_abandon_risk" and level == 0 and q is not None:
        return "high" if ctx.answerable_index.get(q["ref"], 99) < 5 else "medium"
    if iid == "A10_deadline_stated" and ctx.profile in ("event_feedback", "employee_engagement"):
        return "info"
    if iid == "Q21_social_desirability" and ctx.profile in ("academic_research", "employee_engagement"):
        return "medium"
    return sev


def item_finding(ctx: _Ctx, iid: str, ans: Optional[Dict], q: Optional[Dict] = None) -> Optional[Dict]:
    """The finding one answer produces, or None when the answer is fine (or the item is informational)."""
    item = ITEMS[iid]
    if not ans or item["informational"]:
        return None
    rctx = ctx.render_ctx(q)
    prim, uncertain, suffix = item["primitive"], False, ""
    if prim == "score":
        level = ans["level"]
        sev, roast_t = item["severity"].get(level), (item["roast"] or {}).get(level)
        if not sev or not roast_t:
            return None
        sev = _base_severity(ctx, iid, sev, q, level)
        conf = ans["confidence"]
        if conf < LOW_CONFIDENCE:
            sev, uncertain, suffix = "info", True, NOT_SURE
        elif conf < SCORE_CONFIDENT:
            sev, uncertain, suffix = SEVERITY_DOWNGRADE[sev], True, PROBABLY
        evidence = {"kind": "score", "level": level, "levels": item["levels"],
                    "normalised": round(normalise_score(level, item["levels"]), 3), "confidence": conf,
                    "criterion": item["criteria"][level]}
    elif prim == "noul":
        p = ans["p"]
        if item["good_when_yes"]:
            problem, strong = p <= NOUL_NO, p <= NOUL_WEAK
        else:
            problem, strong = p >= NOUL_YES, p >= NOUL_STRONG
        sev, roast_t = item["severity"].get("noul"), item["roast"]
        if not problem or not sev or not roast_t:
            return None
        sev = _base_severity(ctx, iid, sev, q)
        if not strong:
            sev, uncertain, suffix = SEVERITY_DOWNGRADE[sev], True, PROBABLY
        evidence = {"kind": "noul", "value": p}
    else:
        choice, conf = ans["choice"], ans["confidence"]
        if conf < SCORE_CONFIDENT:
            return None
        if iid == "Q19_recall_period" and choice == "missing_but_needed":
            sev, roast_t = item["severity"]["missing_but_needed"], item["roast"]["missing_but_needed"]
        elif iid == "Q25_best_type" and q is not None and choice not in ("current_type_is_best", q["type"]):
            sev, roast_t = item["severity"]["any_other"], item["roast"]["any_other"]
            rctx["choice"] = choice
        else:
            return None
        evidence = {"kind": "choice", "choice": choice, "confidence": conf, "current_type": q["type"] if q else None}
    role = ctx.role.get(q["ref"]) if q else None
    fix = render(item["fix_by_role"].get(role) or item["fix"], rctx)
    return _finding(iid, sev, item["category"], item["scope"], render(roast_t, rctx) + suffix, fix, q,
                    evidence=evidence, uncertain=uncertain, target="question" if q else item["target"],
                    checklist=[f"{q['ref']} \"{q['label'][:60]}\": {fix}" if q else fix],
                    funnel=item["funnel"], weight=item["weight"])


def _downgrade(f: Dict, suffix: str) -> None:
    f["severity"] = SEVERITY_DOWNGRADE[f["severity"]]
    f["uncertain"] = True
    f["roast"] += suffix


def localise(ctx: _Ctx, f: Dict) -> None:
    """Point a survey-level finding at the questions its locator flags (scoring.md#locating-survey-level-findings)."""
    iid = f["id"]
    if iid == "B2_opening_question":
        first = ctx.answerable[0] if ctx.answerable else None
        if first:
            f["question_refs"], f["target"] = [first["ref"]], "question"
            f["checklist"] = [f"{first['ref']} \"{first['label'][:60]}\": open with an easy, on-topic question "
                              "instead; move this one later."]
            f["roast"] += f" See: {first['ref']}."
        return
    if iid in ("C1_objective_coverage", "C5_obvious_gap"):
        if ctx.gap_named():
            gap = ctx.sa("C5_gap_topic")
            topic = GAP_TOPICS.get(gap["choice"], gap["choice"]).lower()
            f["roast"] += f" Most likely missing: {topic}."
            f["checklist"] = [f"Add a question about: {topic}."]
            f["evidence"].update(gap_topic=gap["choice"], gap_confidence=gap["confidence"])
        else:
            _downgrade(f, HUNCH_GAP)
        return
    locator = LOCATORS.get(iid)
    if not locator:
        return
    scored: List[Tuple[float, Dict]] = []
    for q in ctx.qs:
        if locator == "L_duplicate_of_earlier" and ctx.role[q["ref"]] != "question":
            continue                                   # two "Got it" steps are not redundant questions
        p = ctx.qp(q["ref"], locator)
        if p is not None:
            scored.append((p, q))
    scored.sort(key=lambda t: -t[0])
    hits = [(p, q) for p, q in scored if p >= LOCATE_YES][:LOCATE_MAX]
    likely = False
    if not hits:
        hits, likely = [(p, q) for p, q in scored if p >= LOCATE_FALLBACK][:3], True
    if not hits:
        if scored:
            _downgrade(f, HUNCH_LOCATE)
            f["evidence"]["located"] = []
        return
    template = ITEMS[locator]["fix"]
    f["question_refs"] = [q["ref"] for _, q in hits]
    f["checklist"] = [render(template, {"ref": q["ref"], "label": q["label"][:60]}) for _, q in hits]
    f["evidence"]["located"] = [{"ref": q["ref"], "p": round(p, 2)} for p, q in hits]
    f["roast"] += (" Most likely: " if likely else " See: ") + ", ".join(q["ref"] for _, q in hits) + "."


def _attach_follow_ups(ctx: _Ctx, findings: List[Dict]) -> None:
    """A Q5 relevance finding on a question others are gated on covers those follow-ups too."""
    follow_ups: Dict[str, List[str]] = {}
    for q in ctx.qs:
        for r in q["shown_when_refs"]:
            if r in ctx.by_ref and r != q["ref"]:
                follow_ups.setdefault(r, []).append(q["ref"])
    for f in findings:
        refs = follow_ups.get(f["question_ref"] or "")
        if f["id"] != "Q5_relevance" or not refs:
            continue
        f["question_refs"] = [f["question_ref"]] + [r for r in refs if r != f["question_ref"]]
        f["roast"] += f" Its follow-ups ({', '.join(refs)}) only show after it and go with it."
        f["checklist"] += [f"{r}: shown only after {f['question_ref']}; keep or remove them together." for r in refs]
        f["evidence"]["follow_ups"] = refs


def code_rule_findings(ctx: _Ctx, findings: List[Dict]) -> List[Dict]:
    """Survey-level findings computed from informational per-question items (Q18, Q24)."""
    out: List[Dict] = []
    intents = {q["ref"]: ctx.intent(q) for q in ctx.answerable}
    outcomes = [q for q in ctx.answerable if intents[q["ref"]] == "outcome"]

    q18 = ITEMS["Q18_hypothetical"]
    if outcomes and all((ctx.qp(q["ref"], "Q18_hypothetical") or 0) >= NOUL_YES for q in outcomes):
        out.append(_finding("Q18_hypothetical", "medium", q18["category"], "survey", q18["roast"], q18["fix"],
                            evidence={"kind": "rule", "rule": "only_outcome_hypothetical",
                                      "outcome_refs": [q["ref"] for q in outcomes]},
                            target="questions", question_refs=[q["ref"] for q in outcomes], checklist=[q18["fix"]],
                            funnel=q18["funnel"], weight=q18["weight"]))

    if not any(intents.values()):
        return out                                     # no intent known anywhere: nothing to judge the mix on
    q24 = ITEMS["Q24_intent"]

    def rule(name: str, refs: List[str], **fmt) -> None:
        sev, roast, fix = INTENT_RULES[name]
        out.append(_finding("Q24_intent", sev, q24["category"], "survey", roast.format(**fmt), fix,
                            evidence={"kind": "rule", "rule": name, **fmt}, target="questions",
                            question_refs=refs, checklist=[fix], funnel=q24["funnel"], weight=q24["weight"]))

    n = len(ctx.answerable)
    c3_fired = any(f["id"] == "C3_has_outcome_question" for f in findings)
    if not outcomes and ctx.kind not in NO_OUTCOME_EXEMPT_KINDS and not c3_fired:
        rule("no_outcome", [])
    demo = [q["ref"] for q in ctx.answerable if intents[q["ref"]] == "demographic"]
    if n and len(demo) > 0.25 * n:
        rule("demographics_heavy", demo, k=len(demo), n=n)
    if outcomes and n:
        before = ctx.answerable_index[outcomes[0]["ref"]]
        if before > 0.8 * n:
            rule("outcome_buried", [outcomes[0]["ref"]])
    return out


def hybrid_findings(ctx: _Ctx) -> List[Dict]:
    """S22, S23, S25, S26: judge evidence + code rule (static-checks.md#hybrid-checks)."""
    out: List[Dict] = []
    for i, q in enumerate(ctx.qs):
        if not is_answerable(q) or ctx.role[q["ref"]] != "question":
            continue
        ref, label = q["ref"], q["label"]

        def add(fid, sev, cat, p, item, roast, fix):
            f = _finding(fid, sev, cat, "question", roast, fix, q,
                         evidence={"kind": "hybrid", "value": p, "item": item}, target="question",
                         checklist=[f"{ref}: {fix}"], funnel=STATIC_FUNNEL[fid[:3]])
            if p < NOUL_STRONG:
                _downgrade(f, PROBABLY)
            out.append(f)

        dep = ctx.qp(ref, "Q10_depends_on_prior")
        if dep is not None and dep >= NOUL_YES:
            prev = ctx.qs[i - 1] if i > 0 else None
            follows_unless = bool(prev) and any(j["when"] is not None and j["to"] != ref for j in prev["jumps"])
            touched = bool(q["shown_when"]) or any(r["when"] is not None for r in q["reached_from"]) \
                or follows_unless
            if not touched:
                add("S22_conditional_without_logic", "high", "structure", dep, "Q10_depends_on_prior",
                    f"{ref} (\"{label[:80]}\") only applies after a specific earlier answer, but everyone sees it and "
                    "none of its options fit the respondents it doesn't apply to.",
                    f"Add skip logic so {ref} shows only when it applies, or add an option for those it doesn't "
                    "apply to.")
        sens = ctx.qp(ref, "Q12_sensitive")
        if sens is not None and sens >= SENSITIVE_YES and q["required"] and not q["has_prefer_not_to_answer"] \
                and q["options"]:
            add("S23_sensitive_without_optout", "low", "trust", sens, "Q12_sensitive",
                f"{ref} asks something personal, is required, and offers no way to decline.",
                f"Turn on 'Prefer not to answer' for {ref} or make it optional.")
        vis = ctx.qp(ref, "Q11_requires_visual")
        if vis is not None and vis >= NOUL_YES:
            if q["has_image"] or q.get("has_video") is True:
                add("S25_visual_not_described", "low", "experience", vis, "Q11_requires_visual",
                    f"{ref} depends on its image. Fine on screen — invisible in exports, on screen readers, and to "
                    "this reviewer.", f"Add a one-line description of the visual to {ref}.")
            else:
                add("S26_visual_missing", "medium", "questions", vis, "Q11_requires_visual",
                    f"{ref} asks about a screen or image that isn't there.",
                    f"Attach the image to {ref} or rewrite it to stand on its own.")
    return out


def static_findings(ctx: _Ctx, lint_findings: Any) -> List[Dict]:
    """Lint findings, cleaned: kinds gating (S19), S35 confirmed by Q3a, refs/target/checklist filled in."""
    out: List[Dict] = []
    for raw in _l(lint_findings):
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
            continue
        fid = raw["id"]
        if ctx.kind is not None and fid in STATIC_KINDS and ctx.kind not in STATIC_KINDS[fid]:
            continue
        sev = raw.get("severity") if raw.get("severity") in SEVERITY_RANK else "info"
        qref = raw.get("question_ref") if isinstance(raw.get("question_ref"), str) and raw["question_ref"] else None
        if fid.startswith("S35"):
            p = ctx.qp(qref, "Q3a_leading") if qref else None
            if p is None or p < NOUL_YES:
                continue
            sev = "low"
        cat = raw.get("category") if raw.get("category") in CATEGORY_IDS else "structure"
        fix = _text(raw.get("fix"))
        ev = _d(raw.get("evidence"))
        refs = [r for r in _l(raw.get("question_refs")) if isinstance(r, str) and r]
        if not refs:
            refs = [r for r in _l(ev.get("refs")) if isinstance(r, str) and r] or ([qref] if qref else [])
        target = raw.get("target") if isinstance(raw.get("target"), str) else None
        if not target:
            target = "question" if qref or refs else {"purpose": "welcome", "experience": "survey"}.get(cat, "survey")
        checklist = [c for c in _l(raw.get("checklist")) if isinstance(c, str)] or \
            ([f"{r}: {fix}" for r in refs] or [fix])
        scope = raw.get("scope") if raw.get("scope") in ("survey", "question") else (
            "question" if qref else "survey")
        funnel = raw.get("funnel") if raw.get("funnel") in STAGES else STATIC_FUNNEL.get(fid[:3])
        q = ctx.by_ref.get(qref) if qref else None
        out.append({"id": fid, "severity": sev, "category": cat, "scope": scope, "question_ref": qref,
                    "question_label": raw.get("question_label") if isinstance(raw.get("question_label"), str)
                    else (q["label"] if q else None),
                    "roast": _text(raw.get("roast")), "fix": fix, "evidence": dict(ev),
                    "uncertain": raw.get("uncertain") is True, "question_refs": refs, "checklist": checklist,
                    "target": target, "funnel": funnel, "_weight": 1.0})
    return out


# --- scores -------------------------------------------------------------------------------------

def static_deduction(findings: List[Dict], category: Optional[str] = None) -> float:
    """Deduction from static/hybrid findings (ids starting with S), with repeat dampening and the 0.35 cap.
    With `category`, only findings of that category count; without, all given findings do."""
    per_id: Dict[str, List[Dict]] = {}
    for f in findings:
        if not isinstance(f, dict) or not _text(f.get("id")).startswith("S"):
            continue
        if category is not None and f.get("category") != category:
            continue
        per_id.setdefault(f["id"], []).append(f)
    total = sum(_per_id_deduction(group) for group in per_id.values())
    return min(STATIC_DEDUCTION_CAP, total)


def _per_id_deduction(group: List[Dict]) -> float:
    """Base deduction of the most severe finding in the group (order-independent), times the repeat factor."""
    worst = min((f.get("severity") for f in group), key=lambda s: SEVERITY_RANK.get(s, 9))
    base = STATIC_DEDUCTION.get(worst, 0.0)
    return base * min(STATIC_REPEAT_CAP, 1 + STATIC_REPEAT_FACTOR * (len(group) - 1))


def _survey_pairs(ctx: _Ctx, iids: List[str]) -> List[Tuple[str, float, float]]:
    """(id, evidence weight, value) for applicable, scored survey items with evidence."""
    out = []
    for iid in iids:
        if not _scored(iid) or not ctx.survey_item_applies(iid):
            continue
        v, c = value_of(iid, ctx.sa(iid))
        w = evidence_weight(iid, c)
        if iid == "C5_obvious_gap" and not ctx.gap_named():
            w *= 0.5
        if v is not None and w > 0:
            out.append((iid, w, v))
    return out


def _question_values(ctx: _Ctx, iid: str) -> List[Tuple[str, float, float]]:
    """(ref, value, certainty) of one per-question item across answerable questions where it applies."""
    out = []
    for q in ctx.answerable:
        if not ctx.question_item_applies(iid, q):
            continue
        v, c = value_of(iid, ctx.qa(q["ref"], iid), q["type"])
        if v is not None and c >= MIN_CERTAINTY:
            out.append((q["ref"], v, c))
    return out


def question_score(ctx: _Ctx, q: Dict) -> Optional[float]:
    pairs = []
    for iid in ctx.items_for(q):
        if not _scored(iid):
            continue
        v, c = value_of(iid, ctx.qa(q["ref"], iid), q["type"])
        w = evidence_weight(iid, c)
        if v is not None and w > 0:
            pairs.append((w, v))
    return _weighted_mean(pairs)


def _per_question_pair(ctx: _Ctx, iid: str, weight: float) -> Optional[Tuple[float, float, str]]:
    """(weight x mean certainty, mean value, worst ref) of a per-question item, or None without evidence."""
    vals = _question_values(ctx, iid)
    if not vals:
        return None
    mean_v = sum(v for _, v, _ in vals) / len(vals)
    mean_c = sum(c for _, _, c in vals) / len(vals)
    worst = min(vals, key=lambda t: t[1])[0]
    return weight * mean_c, mean_v, worst


def category_values(ctx: _Ctx, findings: List[Dict], q_scores: Dict[str, Optional[float]]
                    ) -> Tuple[Dict[str, float], set]:
    raw: Dict[str, Optional[float]] = {}
    for cat in SURVEY_CATEGORIES:
        pairs = _survey_pairs(ctx, [i for i in SURVEY_ITEM_IDS if ITEMS[i]["category"] == cat])
        raw[cat] = _weighted_mean([(w, v) for _, w, v in pairs])
    valid = [v for v in q_scores.values() if v is not None]
    if valid:
        high_q = sum(1 for f in findings if f["scope"] == "question" and f["severity"] == "high")
        raw["questions"] = max(0.0, sum(valid) / len(valid)
                               - min(QUESTION_HIGH_PENALTY_CAP, QUESTION_HIGH_PENALTY * high_q))
    else:
        raw["questions"] = None
    g_pairs = []
    for iid, weight in CONVERSION_ITEMS.items():
        if ctx.survey_item_applies(iid):
            v, c = value_of(iid, ctx.sa(iid))
            if v is not None and c >= MIN_CERTAINTY:
                g_pairs.append((weight * c, v))
    q15 = _per_question_pair(ctx, "Q15_abandon_risk", CONVERSION_Q15_WEIGHT)
    if q15 and q15[0] > 0:
        g_pairs.append(q15[:2])
    raw["conversion"] = _weighted_mean(g_pairs)

    evaluated = {c for c, v in raw.items() if v is not None}
    out: Dict[str, float] = {}
    for cat in CATEGORY_IDS:
        base = raw[cat] if raw[cat] is not None else NEUTRAL_BASE
        if cat == "conversion":
            ded = static_deduction([f for f in findings if f["id"][:3] in CONVERSION_STATIC])
        else:
            ded = static_deduction(findings, cat)
        out[cat] = _clamp01(base - ded)
    return out, evaluated


def funnel_view(ctx: _Ctx, findings: List[Dict]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for stage in STAGES:
        candidates: List[Tuple[float, str]] = []
        pairs: List[Tuple[float, float]] = []
        named: List[Tuple[float, float, str]] = []      # (item weight, value, driver name)
        for iid, w, v in _survey_pairs(ctx, [i for i in SURVEY_ITEM_IDS if ITEMS[i]["funnel"] == stage]):
            pairs.append((w, v))
            named.append((ITEMS[iid]["weight"], v, iid))
        for iid in QUESTION_ITEM_IDS:
            if ITEMS[iid]["funnel"] != stage or not _scored(iid):
                continue
            pq = _per_question_pair(ctx, iid, ITEMS[iid]["weight"])
            if pq and pq[0] > 0:
                pairs.append(pq[:2])
                named.append((ITEMS[iid]["weight"], pq[1], f"{iid}:{pq[2]}"))
        base = _weighted_mean(pairs)
        base = NEUTRAL_BASE if base is None else base
        stage_static = [f for f in findings if f["funnel"] == stage and f["id"].startswith("S")]
        score = round(100 * _clamp01(base - static_deduction(stage_static)))
        # Drivers: items ranked by weight x (1 - value), expressed as their share of the base so they compare
        # with static deductions (same units: a fraction of the stage score)
        total_w = sum(w for w, _, _ in named)
        for w, v, name in named:
            if total_w > 0 and v < 1:
                candidates.append((w * (1 - v) / total_w, name))
        per_id: Dict[str, List[Dict]] = {}
        for f in stage_static:
            per_id.setdefault(f["id"], []).append(f)
        for fid, group in per_id.items():
            d = _per_id_deduction(group)
            if d > 0:
                candidates.append((d, fid))
        candidates.sort(key=lambda t: -t[0])
        out[stage] = {"score": score, "drivers": [name for _, name in candidates[:3]]}
    fin = out["finish"]["score"]
    out["predicted_completion_band"] = "low" if fin < 50 else ("medium" if fin < 75 else "high")
    return out


# --- report -------------------------------------------------------------------------------------

def _sort_findings(findings: List[Dict]) -> None:
    findings.sort(key=lambda f: (SEVERITY_RANK.get(f["severity"], 9), f["uncertain"], -f["_weight"]))


def findings_by_id(findings: List[Dict]) -> List[Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for f in findings:
        row = rows.setdefault(f["id"], {"id": f["id"], "severity": f["severity"], "category": f["category"],
                                        "target": f["target"], "count": 0, "question_refs": [], "fix": f["fix"],
                                        "checklist": []})
        row["count"] += 1
        for r in f["question_refs"] or ([f["question_ref"]] if f["question_ref"] else []):
            if r not in row["question_refs"]:
                row["question_refs"].append(r)
        for line in f["checklist"]:
            if line not in row["checklist"]:
                row["checklist"].append(line)
    return list(rows.values())


def summary_line(score: int, verdict: str, findings: List[Dict], questions: List[Dict], key: str = "roast") -> str:
    """scoring.md#findings-order-grouping-and-summary. `questions` = the report's answerable-question rows."""
    n_info = sum(1 for q in questions if q.get("role") != "question")
    n_q = len(questions) - n_info
    n = f"{n_q} question{'s' if n_q != 1 else ''}" + \
        (f" and {n_info} information step{'s' if n_info != 1 else ''}" if n_info else "")
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in ("blocker", "high", "medium")}
    top = next((f for f in findings if f["severity"] != "info" and not f["uncertain"]), None) or \
        next((f for f in findings if f["severity"] != "info"), None)
    if verdict == "ready" and not top:
        return f"{score}/100. Clean, focused, and ready to publish. Nothing worth roasting."
    if verdict == "ready":
        return f"{score}/100. Ready to publish; one thing to polish first: {top[key]}"
    if counts["blocker"]:
        return f"{score}/100. Not publishable yet — {counts['blocker']} blocker(s). Start here: {top[key]}"
    if top:
        return (f"{score}/100. {n}, {counts['high']} serious and {counts['medium']} moderate issues. "
                f"Biggest one: {top[key]}")
    return f"{score}/100. {counts['high'] + counts['medium']} issues to fix before publishing."


def calc(survey: Any, judgments: Any, lint_findings: Any) -> Dict[str, Any]:
    """Judgments + lint findings -> the report (scoring.md#report-shape)."""
    ctx = _Ctx(survey, judgments)
    findings: List[Dict] = static_findings(ctx, lint_findings)

    for iid in SURVEY_ITEM_IDS:
        if not ctx.survey_item_applies(iid):
            continue
        f = item_finding(ctx, iid, ctx.sa(iid))
        if f:
            localise(ctx, f)
            findings.append(f)

    q_scores: Dict[str, Optional[float]] = {}
    for q in ctx.qs:
        per_q = []
        for iid in ctx.items_for(q):
            f = item_finding(ctx, iid, ctx.qa(q["ref"], iid), q)
            if f:
                per_q.append(f)
        q25 = next((f for f in per_q if f["id"] == "Q25_best_type"), None)
        if q25:
            for f in per_q:
                if f["id"] == "Q9_type_fit":
                    f["fix"] = q25["fix"]
                    f["checklist"] = [f"{q['ref']} \"{q['label'][:60]}\": {q25['fix']}"]
        findings.extend(per_q)
        if is_answerable(q):
            q_scores[q["ref"]] = question_score(ctx, q)
    _attach_follow_ups(ctx, findings)
    findings.extend(code_rule_findings(ctx, findings))
    findings.extend(hybrid_findings(ctx))

    cat_values, evaluated = category_values(ctx, findings, q_scores)
    weights = {c: ctx.weights[c] for c in CATEGORY_IDS if not evaluated or c in evaluated}
    if sum(weights.values()) <= 0:
        weights = dict(ctx.weights)
    overall = round(100 * sum(w * cat_values[c] for c, w in weights.items()) / sum(weights.values()))
    has_blocker = any(f["severity"] == "blocker" for f in findings)
    if has_blocker:
        overall = min(overall, BLOCKER_SCORE_CAP)
    overall = max(0, min(100, overall))
    grade, verdict = grade_for(overall, has_blocker)

    _sort_findings(findings)
    funnel = funnel_view(ctx, findings)
    conversion_ids = set(CONVERSION_ITEMS) | {"Q15_abandon_risk"}
    categories = []
    for cat, label in CATEGORIES:
        if cat == "conversion":
            n = sum(1 for f in findings if f["severity"] != "info"
                    and (f["id"] in conversion_ids or f["id"][:3] in CONVERSION_STATIC))
        else:
            n = sum(1 for f in findings if f["category"] == cat and f["severity"] != "info")
        categories.append({"id": cat, "label": label, "weight": ctx.weights[cat],
                           "score": round(100 * cat_values[cat]), "findings": n})
    for f in findings:
        f.pop("_weight", None)
    questions = [{"ref": q["ref"], "type": q["type"], "role": ctx.role[q["ref"]], "label": q["label"],
                  "required": q["required"],
                  "score": None if q_scores.get(q["ref"]) is None else round(100 * q_scores[q["ref"]]),
                  "finding_ids": [f["id"] for f in findings if f["question_ref"] == q["ref"]]}
                 for q in ctx.answerable]
    missing = ctx.missing_items()
    return {
        "score": overall, "grade": grade, "verdict": verdict,
        "summary": summary_line(overall, verdict, findings, questions),
        "categories": categories,
        "funnel": funnel,
        "findings": findings,
        "findings_by_id": findings_by_id(findings),
        "questions": questions,
        "stats": ctx.s["stats"],
        "meta": {"rubric_version": RUBRIC_VERSION, "survey_kind": ctx.kind, "audience_kind": ctx.audience,
                 "weight_profile": ctx.profile, "partial": bool(missing) or ctx.bad_judgments,
                 "missing_items": missing},
    }


def run_lint(survey: Any, judgments: Any = None) -> List[Dict]:
    """survey_lint.run with judged intents filled in (Q24_intent, confidence >= 0.6) where the survey has none,
    so S41 / S48 see screeners and outcome questions the judge identified."""
    raw = copy.deepcopy(survey) if isinstance(survey, dict) else survey
    if isinstance(raw, dict) and isinstance(judgments, dict):
        ctx = _Ctx(survey, judgments)
        flat: List[Dict] = []                         # same order as survey_common._flatten
        for item in _l(raw.get("questions")):
            if not isinstance(item, dict):
                continue
            flat.append(item)
            if item.get("type") == "group":
                nested = item.get("questions") if isinstance(item.get("questions"), list) else item.get("children")
                flat.extend(c for c in _l(nested) if isinstance(c, dict))
        if len(flat) == len(ctx.qs):
            for item, q in zip(flat, ctx.qs):
                if not q["intent"]:
                    a = ctx.qa(q["ref"], "Q24_intent")
                    if a and a["confidence"] >= SCORE_CONFIDENT:
                        item["intent"] = a["choice"]
    return survey_lint.run(raw)


# --- rendering ----------------------------------------------------------------------------------

def _cell(x: Any) -> str:
    return "" if x is None else str(x).replace("|", "\\|").replace("\n", " ")


# Neutral one-line problem descriptions for --polite (scoring.md#report-shape). Score items use the criterion
# text of the judged level; these cover Nouls, Choices, code rules, hybrids and static checks.
NEUTRAL_ITEMS = {
    "A5_privacy_stated": "The survey does not say how responses are handled (privacy, anonymity, retention).",
    "A6_audience_stated": "The introduction does not say who the survey is for.",
    "A9_sponsor_named": "The survey does not name who is running it.",
    "A10_deadline_stated": "The survey does not say when it closes.",
    "B4_sections_signposted": "Topic changes are not signposted with a section title or statement.",
    "B5_redundant_questions": "Two or more questions collect the same information.",
    "B8_scale_direction_consistent": "Rating scales run in opposite directions.",
    "C2_has_screener": "No question checks that the respondent belongs to the intended audience.",
    "C3_has_outcome_question": "No question directly measures the key outcome of the stated purpose.",
    "C4_missing_why": "Decision-relevant closed questions have no follow-up asking why.",
    "C7_has_attention_check": "A long survey has no attention or consistency check.",
    "E2_burden": "Some questions ask for recall or calculation respondents are unlikely to manage offhand.",
    "E9_language_consistent": "The survey mixes languages or spelling systems.",
    "F2_consent_language": "The introduction has no consent language (voluntary, can stop at any time).",
    "F3_incentive_clear": "An incentive is mentioned without saying how it is delivered.",
    "F3b_incentive_delivery_clear": "An incentive is mentioned without saying how it is delivered.",
    "F4_manipulative_framing": "Some wording pressures respondents through guilt, urgency or flattery.",
    "F5_contact_provided": "The survey gives no way to contact its owner.",
    "Q2_double_barreled": "{ref} asks about more than one thing in a single question.",
    "Q3a_leading": "{ref} is worded in a way that favours one answer.",
    "Q3b_presuming": "{ref} assumes something about the respondent that earlier questions do not establish.",
    "Q6_options_not_exhaustive": "{ref}'s options may not cover every respondent.",
    "Q7_options_overlap": "{ref}'s options overlap.",
    "Q8_scale_unbalanced": "{ref}'s answer scale is unbalanced.",
    "Q14_options_parallel": "{ref}'s options are written in inconsistent forms.",
    "Q16_sensitive_reassured": "{ref} asks for sensitive information without saying why or who sees it.",
    "Q17_negative_wording": "{ref} is worded negatively, so agreement is easy to misread.",
    "Q20_option_double_barreled": "An option in {ref} combines two separate things.",
    "Q21_social_desirability": "{ref} has a socially favoured answer.",
    "Q22_units_stated": "{ref} does not state the unit or format of the expected answer.",
    "Q19_recall_period": "{ref} asks about behaviour over time without a time window.",
    "Q25_best_type": "{ref} is a {type} question; a {choice} question would capture the answer better.",
}
NEUTRAL_RULES = {
    "only_outcome_hypothetical": "Every outcome question asks about hypothetical behaviour.",
    "no_outcome": "No question measures the outcome the survey's purpose implies.",
    "demographics_heavy": "{k} of {n} questions are demographic.",
    "outcome_buried": "The main outcome question is in the last fifth of the survey.",
}
NEUTRAL_STATIC = {
    "S01": "The survey has no title.", "S02": "The survey has no answerable questions.",
    "S03": "{ref} has no question text.", "S04": "{ref} has too few options (or an impossible selection minimum).",
    "S05": "{ref} is a grid without rows or columns.", "S06": "Group {ref} contains no questions.",
    "S07": "There is no description or welcome text.", "S08": "There is no welcome screen.",
    "S09": "There is no thank-you screen.", "S10": "{refs} have identical question text.",
    "S11": "{ref} lists the same option more than once.", "S12": "{ref}'s numeric ranges have gaps or overlaps.",
    "S13": "{ref}'s wording and question type disagree about how many options can be picked.",
    "S14": "{ref} states a number of picks that is not enforced.",
    "S15": "Respondents are not told how long the survey takes.",
    "S16": "The stated duration differs from the estimated duration.",
    "S17": "The survey is long.", "S18": "Most questions are required.",
    "S19": "There is no open-ended question.", "S21": "The survey is marked anonymous but collects identifying data.",
    "S22": "{ref} depends on an earlier answer but is shown to everyone.",
    "S23": "{ref} asks for sensitive information, is required, and has no opt-out.",
    "S24": "The progress bar is hidden on a long survey.", "S25": "{ref} depends on an image that is not described.",
    "S26": "{ref} refers to a visual that is not attached.",
    "S27": "{refs} are a long run of questions of the same type.", "S28": "{refs} cannot be reached.",
    "S30": "{ref} is a large grid.", "S31": "{refs} are consecutive grids.",
    "S32": "{ref} asks respondents to rank many items.", "S33": "{ref} is a long single-choice list.",
    "S34": "Many questions require typed answers.", "S35": "{ref} contains a loaded word.",
    "S36": "{ref}'s scale labels only the endpoints.", "S37": "{ref} is a recommend question that is not standard NPS.",
    "S38": "A 'none' option in {ref} is not exclusive.", "S39": "{ref} has an 'Other' option without a text box.",
    "S40": "{ref}'s long option list is not randomised.", "S41": "Screener {ref} has no exit for non-qualifiers.",
    "S42": "{ref} uses capitals, repeated punctuation or symbol-only options.",
    "S43": "{ref}'s label is very long.", "S44": "Group {ref} contains a single question.",
    "S45": "{ref} is a yes/no question that is not phrased as one.",
    "S46": "The first question is open-ended.", "S47": "A long survey has no branching logic.",
    "S48": "{ref} asks for personal details before the first outcome question.",
    "S50": "The welcome text is long.", "S51": "{ref} asks for demanding input among the first questions.",
}


def neutral_description(f: Dict[str, Any]) -> str:
    """A neutral one-line description of a finding's problem (the --polite replacement for its roast)."""
    ev = _d(f.get("evidence"))
    ref = f.get("question_ref") or ""
    refs = [r for r in _l(f.get("question_refs")) if isinstance(r, str)]
    ctx = {"ref": ref or ", ".join(refs) or "A question", "refs": ", ".join(refs) or ref or "Several questions",
           "type": ev.get("current_type") or "different", "choice": ev.get("choice") or "different",
           "k": ev.get("k", "?"), "n": ev.get("n", "?")}
    fid = _text(f.get("id"))
    if ev.get("rule") in NEUTRAL_RULES:
        text = NEUTRAL_RULES[ev["rule"]]
    elif fid in ITEMS and ev.get("kind") == "score" and isinstance(ev.get("criterion"), str):
        text = (f"{ref}: " if ref else "") + ev["criterion"].rstrip(".") + "."
    elif fid in NEUTRAL_ITEMS:
        text = NEUTRAL_ITEMS[fid]
    elif fid[:3] in NEUTRAL_STATIC:
        text = NEUTRAL_STATIC[fid[:3]]
    else:
        text = f"Check {fid} flagged {ctx['refs']}." if refs else f"Check {fid} flagged the survey."
    text = render(text, ctx)
    if f.get("scope") == "survey" and fid in ITEMS and refs and not ev.get("rule"):
        text += " Questions: " + ", ".join(refs) + "."
    if f.get("uncertain"):
        text += " (uncertain)"
    return text


def polite_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """The report with every roast replaced by a neutral description; fixes and the finding shape are kept, and
    the summary is rebuilt with the same summary-line forms."""
    r = copy.deepcopy(report)
    for f in r["findings"]:
        f["roast"] = neutral_description(f)
    r["summary"] = summary_line(r["score"], r["verdict"], r["findings"], r["questions"])
    return r


def to_markdown(report: Dict[str, Any], polite: bool = False) -> str:
    r = polite_report(report) if polite else report
    out = [f"# Survey score: {r['score']}/100 · {r['grade']} · {r['verdict']}", "", r["summary"], ""]
    out += ["## Categories", "", "| Category | Weight | Score | Findings |", "| --- | --- | --- | --- |"]
    out += [f"| {c['label']} | {c['weight']:.2f} | {c['score']} | {c['findings']} |" for c in r["categories"]]
    fun = r["funnel"]
    out += ["", f"## Funnel (predicted completion: {fun['predicted_completion_band']})", "",
            "| Stage | Score | Drivers |", "| --- | --- | --- |"]
    out += [f"| {s} | {fun[s]['score']} | {_cell(', '.join(fun[s]['drivers']))} |" for s in STAGES]
    out += ["", "## Top findings", ""]
    top = r["findings"][:10]
    if not top:
        out.append("Nothing to report.")
    for i, f in enumerate(top, 1):
        ref = f["question_ref"] or ", ".join(f["question_refs"]) or "survey"
        out.append(f"{i}. {f['severity']} · {ref} · {f['roast']} → {f['fix']}")
    if len(r["findings"]) > 10:
        out.append(f"\n…and {len(r['findings']) - 10} more (see --json).")
    out += ["", "## Questions", "", "| Ref | Type | Label | Score | Findings |", "| --- | --- | --- | --- | --- |"]
    out += [f"| {q['ref']} | {q['type']} | {_cell(q['label'][:60])} | {'—' if q['score'] is None else q['score']} | "
            f"{_cell(', '.join(q['finding_ids']))} |" for q in r["questions"]]
    out += ["", "## What to do first", ""]
    first = [row for row in r["findings_by_id"] if row["severity"] != "info"][:3]
    if not first:
        out.append("Nothing urgent. Publish.")
    for i, row in enumerate(first, 1):
        refs = f" ({', '.join(row['question_refs'])})" if row["question_refs"] else ""
        out.append(f"{i}. {row['fix']}{refs}")
    meta = r["meta"]
    out += ["", f"_Rubric {meta['rubric_version']} · profile {meta['weight_profile']}"
                + (f" · partial: {len(meta['missing_items'])} item(s) not judged" if meta["partial"] else "") + "_"]
    return "\n".join(out)


# --- CLI ------------------------------------------------------------------------------------------

USAGE = "usage: survey_score_calc.py survey.json judgments.json [--lint] [--json|--md] [--polite] [--print-items]"


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--print-items" in args:
        print(json.dumps(ITEMS, indent=2, ensure_ascii=False))
        return 0
    paths = [a for a in args if not a.startswith("--")]
    if len(paths) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        survey = load_survey(paths[0])
        with open(paths[1], encoding="utf-8") as fh:
            judgments = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"survey_score_calc: invalid input: {e}".replace("\n", " "), file=sys.stderr)
        return 2
    try:
        lint = run_lint(survey, judgments) if "--lint" in args else []
        report = calc(survey, judgments, lint)
    except Exception as e:  # noqa: BLE001 - the CLI never tracebacks
        print(f"survey_score_calc: unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    polite = "--polite" in args
    if "--json" in args:
        print(json.dumps(polite_report(report) if polite else report, indent=2, ensure_ascii=False))
    else:
        print(to_markdown(report, polite))
    bad = report["verdict"] == "not_ready" or any(f["severity"] in ("blocker", "high") for f in report["findings"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
