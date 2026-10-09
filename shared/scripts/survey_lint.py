#!/usr/bin/env python3
"""Deterministic static checks for a portable survey (shared/static-checks.md, bs-skills-1.0).

No LLM: counts, thresholds and structure. The only source of blockers. Hybrid checks (S22, S23, S25, S26)
need judge evidence and live in the score calculator, not here.

    python survey_lint.py survey.json [--json] [--polite]

Exit codes: 0 ok, 1 any blocker/high finding, 2 invalid input.
Stdlib only, Python >= 3.9.
"""

import json
import os
import re
import sys
from collections import Counter
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from survey_common import (CHOICE, OPEN_ENDED, _d, _l, _text, collects_pii, is_answerable,  # noqa: E402
                           is_matrix, load_survey, normalise)

MONOTONY_RUN = 8   # consecutive answerable questions of one type before it counts as a wall
SEVERITY_ORDER = {"blocker": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

# --- numeric ranges (S12): port of static_checks.parse_range / numeric_range_issues -----------

_NUM = r"(?:£|\$|€)?\s*(\d+(?:[.,]\d+)?)\s*(k|m)?"
_RANGE = re.compile(rf"^\s*{_NUM}\s*(?:-|–|—|to)\s*{_NUM}\s*(?:\w+)?\s*$", re.I)
_UNDER = re.compile(rf"^\s*(?:under|below|less than|fewer than|<)\s*{_NUM}", re.I)
_UP_TO = re.compile(rf"^\s*(?:up to|<=|≤)\s*{_NUM}", re.I)
_DECIMAL_COMMA = re.compile(r"\d,\d{1,2}(?!\d)")
_OVER = re.compile(rf"^\s*(?:over|above|more than|greater than|>)\s*{_NUM}", re.I)
_PLUS = re.compile(rf"^\s*{_NUM}\s*\+\s*(?:\w+)?\s*$", re.I)
_OR_MORE = re.compile(rf"^\s*{_NUM}\s*(?:\w+\s+)?(?:or more|and over|and above|or over)", re.I)
_OR_LESS = re.compile(rf"^\s*{_NUM}\s*(?:\w+\s+)?(?:or less|and under|or fewer|and below)", re.I)


def _n(v: str, suffix: Optional[str]) -> float:
    n = float(v.replace(",", ""))
    if suffix:
        n *= {"k": 1_000, "m": 1_000_000}[suffix.lower()]
    return n


def parse_range(option) -> Optional[Tuple[Optional[float], Optional[float], bool, bool]]:
    """-> (low, high, low_inclusive, high_inclusive), or None when the option is not a numeric range."""
    text = _text(option).strip()
    if _DECIMAL_COMMA.search(text):
        return None                             # '0-0,5': a decimal, not a thousands separator
    m = _RANGE.match(text)
    if m:
        lo, hi = _n(m.group(1), m.group(2)), _n(m.group(3), m.group(4))
        if m.group(4) and not m.group(2):       # '£25-40k': the suffix on the second number applies to both
            lo = _n(m.group(1), m.group(4))
        return (lo, hi, True, True)
    m = _UNDER.match(text)
    if m:
        return (None, _n(m.group(1), m.group(2)), True, False)
    m = _OR_LESS.match(text) or _UP_TO.match(text)
    if m:
        return (None, _n(m.group(1), m.group(2)), True, True)
    m = _OVER.match(text)
    if m:
        return (_n(m.group(1), m.group(2)), None, False, True)
    m = _PLUS.match(text) or _OR_MORE.match(text)
    if m:
        return (_n(m.group(1), m.group(2)), None, True, True)
    return None


def numeric_range_issues(options) -> List[str]:
    """Gap/overlap descriptions between consecutive numeric-range options."""
    options = [o for o in _l(options) if isinstance(o, str)]
    ranges = [(o, r) for o, r in ((o, parse_range(o)) for o in options) if r]
    if len(ranges) < 3 or len(ranges) < 0.6 * len(options):
        return []
    for _, (lo, hi, _, _) in ranges:            # only whole-number buckets are safe (ages, years, money in k)
        for b in (lo, hi):
            if b is not None and b != int(b):
                return []

    def eff_low(r):
        lo, _, lo_inc, _ = r
        return None if lo is None else (lo if lo_inc else lo + 1)

    def eff_high(r):
        _, hi, _, hi_inc = r
        return None if hi is None else (hi if hi_inc else hi - 1)

    ordered = sorted(ranges, key=lambda x: (-1e18 if eff_low(x[1]) is None else eff_low(x[1])))
    issues = []
    for (o1, r1), (o2, r2) in zip(ordered, ordered[1:]):
        h1, l2 = eff_high(r1), eff_low(r2)
        if h1 is None or l2 is None:
            continue
        if l2 > h1 + 1:
            missing = f"{int(h1) + 1}" if l2 - h1 == 2 else f"{int(h1) + 1}–{int(l2) - 1}"
            issues.append(f"'{o1}' then '{o2}' — where does {missing} go?")
        elif l2 <= h1:
            issues.append(f"'{o1}' and '{o2}' both contain {int(l2)}")
    return issues


# --- wording patterns (English-only pre-filters) -------------------------------------------

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                 "nine": 9, "ten": 10}
_NW = "|".join(_NUMBER_WORDS)
_MULTI_HINT = re.compile(r"\b(select all|select multiple|check all|tick all|choose all|all that apply|"
                         r"select up to|choose up to)\b", re.I)
_MULTI_HINT_N = re.compile(rf"\b(?:select|choose|pick)\s+(\d+|{_NW})\b", re.I)
_SINGLE_HINT = re.compile(r"\b(select one|choose one|pick one|only one)\b", re.I)
_COUNT_HINT = re.compile(rf"\b(?:select|choose|pick|up to|at least)\s+(\d+|{_NW})\b", re.I)
_DURATION = re.compile(r"\b\d+\s*(?:-|–|to)?\s*\d*\s*(?:min|mins|minute|minutes)\b", re.I)
_LOADED = ["obviously", "clearly", "don't you agree", "wouldn't you", "everyone knows", "always", "never",
           "should", "unfortunately"]
_LOADED_RE = [(w, re.compile(rf"(?<!\w){re.escape(w)}(?!\w)", re.I)) for w in _LOADED]
_NONE_OPT = re.compile(r"^(?:none of the above|none|n/a|not applicable)(?!\w)", re.I)
_OTHER_OPT = re.compile(r"^other", re.I)
_ORDINAL = re.compile(r"\b(never|rarely|sometimes|often|always|agree|disagree|satisfied|dissatisfied|very|"
                      r"extremely|not at all|somewhat|slightly)\b", re.I)
_YESNO_START = re.compile(r"^\W*(do|does|did|are|is|have|has|can|will|would|could|should)\b", re.I)
_HAS_ALNUM = re.compile(r"[^\W_]")
_THING = {"long_text": "an essay", "file": "a file", "email": "an email address", "phone": "a phone number",
          "ranking": "a ranking"}

# question families by check
_SINGLE_TYPES = {"single_choice", "dropdown", "yes_no"}
_SCALE_POINT_TYPES = {"likert", "rating", "slider"}

_FUNNEL = {
    "S01": "start", "S02": "start", "S03": "answer_quality", "S04": "answer_quality", "S05": "answer_quality",
    "S06": "finish", "S07": "start", "S08": "start", "S09": "finish", "S10": "finish", "S11": "answer_quality",
    "S12": "answer_quality", "S13": "answer_quality", "S14": "answer_quality", "S15": "start", "S16": "start",
    "S17": "finish", "S18": "finish", "S19": "actionability", "S21": "start", "S24": "finish", "S27": "finish",
    "S28": "finish", "S30": "finish", "S31": "finish", "S32": "finish", "S33": "finish", "S34": "finish",
    "S35": "answer_quality", "S36": "answer_quality", "S37": "answer_quality", "S38": "answer_quality",
    "S39": "answer_quality", "S40": "answer_quality", "S41": "actionability", "S42": "answer_quality",
    "S43": "finish", "S44": "finish", "S45": "answer_quality", "S46": "continue", "S47": "finish",
    "S48": "continue", "S50": "start", "S51": "continue",
}


def _f(id: str, severity: str, category: str, roast: str, fix: str, q: Optional[Dict] = None,
       refs: Optional[List[str]] = None, **evidence) -> Dict:
    qrefs = refs if refs is not None else ([q["ref"]] if q else [])
    ev = {"kind": "static", **evidence}
    if refs is not None:
        ev["refs"] = refs
    return {"id": id, "severity": severity, "category": category, "scope": "question" if q else "survey",
            "question_ref": q["ref"] if q else None, "question_label": q["label"] if q else None,
            "question_refs": qrefs, "funnel": _FUNNEL.get(id[:3]),
            "roast": roast, "fix": fix, "evidence": ev}


def _fmt(x) -> str:
    """3.0 -> '3', 3.25 -> '3.2'."""
    if x is None:
        return "?"
    x = round(float(x), 1)
    return str(int(x)) if x == int(x) else str(x)


def _words(s: str) -> int:
    return len(_text(s).split())


def _lbl(q: Dict) -> str:
    return q["label"][:80]


def _option_count(q: Dict) -> int:
    return len(q["options"]) + sum(1 for k in ("has_other", "has_none", "has_prefer_not_to_answer") if q[k])


def _matrix_dims(q: Dict) -> Tuple[int, int]:
    rows = len(q["rows"])
    cols = len(q["columns"])
    if not cols and q["type"] == "likert":
        lo, hi = q["scale"]["min"], q["scale"]["max"]
        cols = int(hi - lo + 1) if lo is not None and hi is not None and hi >= lo else len(q["options"])
    return rows, cols


# --- the checks -----------------------------------------------------------------------------

def run(survey) -> List[Dict]:
    """All non-hybrid static checks on a survey (raw or normalised). Returns a list of Finding dicts."""
    s = normalise(survey)
    out: List[Dict] = []
    qs = s["questions"]
    answerable = [q for q in qs if is_answerable(q)]
    n = len(answerable)
    st = s["stats"]
    settings = s["settings"]
    welcome, thank_you = s["welcome"], s["thank_you"]

    # Survey-level -----------------------------------------------------------------------
    if not s["title"]:
        out.append(_f("S01_no_title", "blocker", "purpose",
                      "The survey has no title, so respondents can't tell what it is.", "Give the survey a title."))
    if not qs:
        out.append(_f("S02_no_questions", "blocker", "coverage",
                      "There is nothing in this survey yet.", "Add at least one question."))
    elif n == 0:
        out.append(_f("S02_no_questions", "medium", "coverage",
                      "Nothing here asks for an answer, so no responses will be collected.",
                      "Add a question if you want responses; otherwise this is fine as an information page."))

    # Element integrity (S03-S06) --------------------------------------------------------------
    for q in answerable:
        ref = q["ref"]
        if not q["label"]:
            out.append(_f("S03_label_empty", "blocker", "questions",
                          f"{ref} has no question text. Respondents get an empty box and a shrug.",
                          f"Write the question for {ref}, or delete it.", q))
        if q["type"] in CHOICE:
            k = _option_count(q)
            if k < 2:
                out.append(_f("S04_options_too_few", "blocker", "questions",
                              f"{ref} gives respondents {k} option(s) to choose from. That's not a choice.",
                              f"Give {ref} at least two options, or change its type.", q, option_count=k))
        if q["type"] == "multi_choice" and q["required"]:
            k, mn = _option_count(q), q["selection"]["min"]
            if mn is not None and mn > k:
                out.append(_f("S04_options_too_few", "blocker", "questions",
                              f"{ref} requires at least {mn} picks from {k} options. Nobody can submit.",
                              f"Lower {ref}'s `selection.min` to at most the number of options.", q,
                              option_count=k, selection_min=mn))
        if q["type"] == "matrix" and (not q["rows"] or not q["columns"]):
            out.append(_f("S05_matrix_empty", "blocker", "questions", f"{ref} is a grid with nothing to rate.",
                          f"Add the rows (items) and columns (scale points) to {ref}, or delete it.", q))
    for g in (q for q in qs if q["type"] == "group"):
        kids = g.get("children") or []
        if not kids:
            out.append(_f("S06_group_empty", "low", "structure",
                          f"Group {g['ref']} (\"{_lbl(g)}\") has no questions in it.",
                          f"Move questions into {g['ref']} or remove it.", g))
        elif len(kids) == 1:
            out.append(_f("S44_group_single_child", "low", "structure",
                          f"Group {g['ref']} holds a single question. A section of one is just an extra click.",
                          "Remove the group around it, or merge it into a neighbouring section.", g, children=kids))

    # Framing ----------------------------------------------------------------------------------
    w_desc = welcome["description"] if welcome else ""
    if not s["description"] and not w_desc:
        out.append(_f("S07_no_description", "medium", "purpose",
                      "You haven't told people why they're here. No description, no welcome text.",
                      "Add a welcome screen that explains the purpose in two sentences."))
    has_welcome = bool(welcome and (welcome["title"] or welcome["description"]))
    if not has_welcome:
        out.append(_f("S08_no_welcome", "low", "purpose",
                      "No welcome screen, so respondents start cold and aren't shown how long the survey takes.",
                      "Add a welcome screen; it shows the purpose and the time to complete."))
    elif settings["stated_minutes"] is None and not _DURATION.search(w_desc) \
            and not _DURATION.search(s["description"]):
        out.append(_f("S15_no_time_expectation", "low", "purpose",
                      "Respondents aren't told how long this takes.",
                      "Set `settings.stated_minutes` and say the time on the welcome screen "
                      "(\"Takes about 4 minutes\")."))
    if not (thank_you and (thank_you["title"] or thank_you["description"])):
        out.append(_f("S09_no_thank_you", "low", "experience",
                      "No thank-you screen of your own, so respondents aren't told what happens next.",
                      "Add a thank-you screen that says what happens next."))
    if _words(w_desc) > 120:
        k = _words(w_desc)
        out.append(_f("S50_welcome_too_long", "medium", "purpose",
                      f"A {k}-word welcome is a wall. Nobody reads walls on a phone.",
                      "Cut the welcome to under 120 words: why you're asking, how long it takes, what happens to "
                      "the answers.", words=k))

    stated, estimated = settings["stated_minutes"], st["estimated_minutes"]
    if stated is not None and (stated > 2 * estimated + 3 or estimated > 2 * stated + 3):
        out.append(_f("S16_time_mismatch", "medium", "experience",
                      f"You promise ~{_fmt(stated)} minutes; by a rough estimate this is a ~{_fmt(estimated)}-minute "
                      "survey.",
                      "Update `settings.stated_minutes` to the estimate, or cut questions until the promise is true.",
                      stated_minutes=stated, estimated_minutes=estimated))

    # Flow (S28): one finding per dead run of top-level questions ----------------------------------
    if not settings["randomize_questions"]:
        top = [q for q in qs if q["parent"] is None]
        i = 0
        while i < len(top):
            if not top[i]["unreachable"]:
                i += 1
                continue
            j = i
            while j + 1 < len(top) and top[j + 1]["unreachable"]:
                j += 1
            dead = top[i:j + 1]
            first = dead[0]
            before = top[i - 1]["ref"] if i > 0 else None
            pron = "it" if len(dead) == 1 else "them"
            what = (f"{first['ref']} (\"{_lbl(first)}\")" if len(dead) == 1 else
                    f"{first['ref']}–{dead[-1]['ref']} ({len(dead)} questions, starting \"{first['label'][:60]}\")")
            why = f"{before} always jumps past {pron} and nothing jumps to {pron}" if before else "nothing leads there"
            out.append(_f("S28_unreachable_question", "high", "structure", f"{what} can never be shown: {why}.",
                          f"Point a jump at {first['ref']}, or remove the default jump (`when: null`) on "
                          f"{before or 'the question before it'}.", first, refs=[x["ref"] for x in dead]))
            i = j + 1

    # Duplicates (S10, S11) ------------------------------------------------------------------------
    plain = [q for q in answerable if q["label"] and not q["shown_when"] and not q["reached_from"]]
    key = lambda q: (q["parent"] or q["group"], q["label"].lower())  # noqa: E731
    counts = Counter(key(q) for q in plain)
    reported = set()
    for q in plain:
        k = key(q)
        if counts[k] > 1 and k not in reported:
            reported.add(k)
            refs = [x["ref"] for x in plain if key(x) == k]
            out.append(_f("S10_duplicate_labels", "medium", "structure",
                          f"{', '.join(refs)} have identical question text (\"{_lbl(q)}\").",
                          "Merge them, or reword each so they clearly ask different things.", q, refs=refs))
    for q in answerable:
        seen: Dict[str, str] = {}
        dupes: List[str] = []
        for o in q["options"]:
            lo = o.lower()
            if lo in seen and seen[lo] not in dupes:
                dupes.append(seen[lo])
            seen.setdefault(lo, o)
        if dupes:
            out.append(_f("S11_duplicate_options", "medium", "questions",
                          f"{q['ref']} lists the same option twice ({', '.join(dupes)}).",
                          f"Remove the duplicate option(s) in {q['ref']}.", q, duplicates=dupes))

    # Per-question option and wording checks ------------------------------------------------------
    for q in answerable:
        ref, t, label = q["ref"], q["type"], q["label"]
        opts = q["options"]
        if opts:
            issues = numeric_range_issues(opts)
            if issues:
                out.append(_f("S12_numeric_range_gap", "medium", "questions", f"{ref}: " + "; ".join(issues),
                              f"Rewrite {ref}'s ranges so every value lands in exactly one bucket "
                              "(no gaps, no shared boundaries).", q, issues=issues))

        hint, want = _selection_hint(t, label)
        if hint:
            out.append(_f("S13_selection_hint_type_mismatch", "high", "questions",
                          f"{ref} says \"{hint}\" but the question type lets respondents pick {want}. "
                          "They'll fight the form.",
                          f"Change {ref}'s type (single_choice ↔ multi_choice) or reword the instruction to match.",
                          q, hint=hint))
        if t == "multi_choice" and q["selection"]["min"] is None and q["selection"]["max"] is None:
            m = _COUNT_HINT.search(label)
            if m:
                out.append(_f("S14_selection_count_unenforced", "low", "questions",
                              f"{ref} says to pick {m.group(1)} but nothing stops anyone picking more or fewer.",
                              f"Set `selection.min` / `selection.max` on {ref} to match the instruction.", q,
                              hint=m.group(0)))

        if is_matrix(q):
            r, c = _matrix_dims(q)
            sev = "high" if r > 8 else ("medium" if c > 5 else None)
            if sev:
                out.append(_f("S30_matrix_too_large", sev, "experience",
                              f"{ref} is a {r}×{c} grid. On a phone that's a scroll-and-guess exercise.",
                              f"Split {ref} into smaller grids (at most 5 columns and 8 rows) or separate questions.",
                              q, rows=r, columns=c))
        if t == "ranking" and len(opts) > 7:
            out.append(_f("S32_ranking_too_many", "medium", "experience",
                          f"{ref} asks people to rank {len(opts)} items. Past seven, the bottom half is noise.",
                          "Ask for the top 3, or cut the list to 7 or fewer.", q, options=len(opts)))
        if t == "single_choice" and len(opts) > 10:
            out.append(_f("S33_long_radio_list", "low", "questions",
                          f"{ref} lists {len(opts)} options as radio buttons. That's a scroll, not a choice.",
                          "Use a dropdown.", q, options=len(opts)))

        norm_label = label.replace("’", "'")
        word = next((w for w, rx in _LOADED_RE if rx.search(norm_label)), None)
        if word:
            out.append(_f("S35_loaded_words", "info", "questions", f"{ref} uses a loaded word (\"{word}\"). "
                          "It nudges the answer.", f"Reword {ref} without \"{word}\".", q, word=word))

        if t in _SCALE_POINT_TYPES:
            lo, hi = q["scale"]["min"], q["scale"]["max"]
            if lo is not None and hi is not None and hi - lo + 1 >= 7:
                interior = [k for k in q["scale"]["labels"] if _between(k, lo, hi)]
                if not interior:
                    out.append(_f("S36_scale_endpoints_only", "low", "questions",
                                  "Label the middle too; endpoint-only scales drift.",
                                  f"Label every point of {ref}'s scale, or at least the midpoint.", q,
                                  points=int(hi - lo + 1)))
        is_recommend = t in {"rating", "likert", "slider", "single_choice"} and "recommend" in label.lower()
        if t == "nps" or is_recommend:
            if q["scale"]["min"] != 0 or q["scale"]["max"] != 10 or "likely" not in label.lower():
                out.append(_f("S37_nps_nonstandard", "medium", "questions",
                              f"{ref} is a recommend question that isn't standard NPS. Its number won't compare with "
                              "anyone else's.",
                              "Use the standard wording and a 0–10 scale: \"How likely are you to recommend … to a "
                              "friend or colleague?\"", q, scale={"min": q["scale"]["min"], "max": q["scale"]["max"]}))
        if t == "multi_choice":
            excl = {e.lower() for e in q["exclusive_options"]}
            none_opt = next((o for o in opts if _NONE_OPT.match(o) and o.lower() not in excl), None)
            if none_opt:
                out.append(_f("S38_none_not_exclusive", "medium", "questions",
                              f"'{none_opt}' can be ticked alongside other options. Make it exclusive.",
                              f"Add '{none_opt}' to {ref}'s `exclusive_options`.", q, option=none_opt))
        if not q["has_other"] and any(_OTHER_OPT.match(o) for o in opts):
            out.append(_f("S39_other_without_text", "low", "questions",
                          f"{ref} has an 'Other' option with nowhere to say what 'other' is.",
                          f"Remove the plain 'Other' option and set `has_other: true` on {ref} (it adds a text box).",
                          q))
        if t in {"single_choice", "multi_choice"} and len(opts) > 6 and not q["randomize_options"]:
            parsed = sum(1 for o in opts if parse_range(o))
            if parsed < 0.6 * len(opts) and not any(_ORDINAL.search(o) for o in opts):
                out.append(_f("S40_long_list_not_randomised", "low", "questions",
                              "Order bias: the first three options get picked more.",
                              f"Set `randomize_options: true` on {ref} (keep 'Other' and 'None' last).", q,
                              options=len(opts)))
        if q["intent"] == "screener" and not q["jumps"]:
            later = qs[qs.index(q) + 1:]
            if not any(ref in x["shown_when_refs"] for x in later):
                out.append(_f("S41_screener_without_exit", "high", "structure",
                              f"{ref} screens people out but nothing happens when they fail it. They keep answering "
                              "questions that don't apply.",
                              f"Add a jump on {ref}: non-qualifying answers → `end` (or to a short exit statement).",
                              q))
        if _shouting(label, opts):
            out.append(_f("S42_shouting_or_noise", "low", "questions",
                          f"{ref} is shouting (capitals, '??', '!!!' or emoji-only options). It reads as spam.",
                          "Use sentence case, one question mark, and words in the options.", q))
        if _words(label) > 35:
            out.append(_f("S43_label_too_long", "medium", "questions",
                          f"{ref} is a paragraph, not a question.",
                          f"Cut {ref} to one sentence under 35 words; move the context into its description.", q,
                          words=_words(label)))
        if t == "yes_no" and label and not _YESNO_START.match(label):
            out.append(_f("S45_yesno_type_mismatch", "medium", "questions",
                          f"{ref} is a yes/no question that doesn't read as one (\"{_lbl(q)}\").",
                          f"Rephrase {ref} as a yes/no question (\"Do you…?\") or change its type.", q))

    # Length and load ------------------------------------------------------------------------------
    branching = bool(s["has_logic"])
    if n > 50:
        out.append(_f("S17_length_fatigue", "medium" if branching else "high", "experience",
                      (f"Up to {n} questions, depending on the path. Long paths lose people."
                       if branching else f"{n} questions. That's not a survey, that's a shift."),
                      "Cut to the questions that map to a decision; split the rest into a follow-up survey."))
    elif n > 30:
        out.append(_f("S17_length_fatigue", "medium", "experience",
                      f"{n} questions is long. Expect drop-off after the 20th.",
                      "Trim non-essential questions; consider a progress bar and section breaks."))
    req = st["required_answerable"]
    if (n > 20 and req >= 0.95 * n) or (n > 15 and req >= 0.8 * n):
        out.append(_f("S18_all_required_long", "low", "experience",
                      f"{req} of {n} questions are required. Every mandatory question is a place to quit instead of "
                      "skip.", "Make non-critical questions optional.", required=req))
    if n > 15 and st["open_ended_questions"] == 0 and s["kind"] in (None, "research", "feedback"):
        out.append(_f("S19_no_open_ended", "low", "coverage",
                      f"{n} closed questions and not one place to say 'actually…'.",
                      "Add one optional open text question near the end."))
    if n > 20 and not settings["progress_bar"]:
        out.append(_f("S24_no_progress_bar_long", "low", "experience",
                      f"{n} questions and the progress bar is hidden. Respondents can't see the finish line.",
                      "Turn the progress bar on in survey settings."))
    open_q = [q for q in answerable if q["type"] in OPEN_ENDED]
    open_req = sum(1 for q in open_q if q["required"])
    if n and (len(open_q) > 0.3 * n or open_req > 3):
        out.append(_f("S34_open_ended_overload", "medium", "experience",
                      f"{len(open_q)} of {n} questions ask people to type. Typing is the most expensive thing you can "
                      "ask for.",
                      "Keep open text to at most 30 % of questions and at most 3 required; turn the rest into "
                      "choices.", open_ended=len(open_q), required_open_ended=open_req))
    if n > 30 and not branching:
        out.append(_f("S47_no_logic_long_survey", "low", "structure",
                      f"Everyone sees all {n} questions. Branching would let most people finish sooner.",
                      "Add `shown_when` / `jumps` so respondents skip what doesn't apply to them."))

    # Runs: monotony (S27) and consecutive matrices (S31) -------------------------------------------
    run_: List[Dict] = []

    def flush():
        if len(run_) >= MONOTONY_RUN:
            refs = [x["ref"] for x in run_]
            out.append(_f("S27_monotony_run", "low", "experience",
                          f"{refs[0]}–{refs[-1]}: {len(run_)} {run_[0]['type']} questions in a row. By the tenth one "
                          "respondents stop reading.",
                          "Break the run with a different format, a short statement, or by trimming it.",
                          run_[0], refs=refs))

    for q in answerable:
        if run_ and q["type"] == run_[-1]["type"] and q["parent"] == run_[-1]["parent"] \
                and q["group"] == run_[-1]["group"] and not q["shown_when"]:
            run_.append(q)
        else:
            flush()
            run_ = [q]
    flush()

    mats: List[Dict] = []
    for q in answerable + [None]:
        if q is not None and is_matrix(q):
            mats.append(q)
            continue
        if len(mats) >= 2:
            refs = [x["ref"] for x in mats]
            out.append(_f("S31_consecutive_matrices", "medium", "experience",
                          f"{', '.join(refs)} are grids back to back. This is where straight-lining starts.",
                          "Put a different question type between them, or merge and trim.", mats[0], refs=refs))
        mats = []

    # Order: first question, early friction, PII before content --------------------------------------
    if answerable and answerable[0]["type"] in OPEN_ENDED:
        q = answerable[0]
        out.append(_f("S46_first_question_open_text", "medium", "structure",
                      "Opening with an essay question. Start with a click.",
                      f"Move {q['ref']} later and open with a quick closed question.", q))
    for q in answerable[:3]:
        if not q["required"]:
            continue
        thing = "a grid of ratings" if is_matrix(q) else _THING.get(q["type"])
        if thing:
            out.append(_f("S51_early_friction", "high", "structure",
                          f"{q['ref']} asks for {thing} before the respondent has invested anything. Move it later or "
                          "make it optional.",
                          f"Move {q['ref']} after the first few easy questions, or make it optional.", q, thing=thing))
    first_outcome = next((i for i, q in enumerate(answerable) if q["intent"] == "outcome"), None)
    if first_outcome is not None:
        for q in answerable[:first_outcome]:
            if collects_pii(q):
                out.append(_f("S48_pii_before_content", "medium", "structure",
                              "You ask for their email before you ask what they think.",
                              f"Move {q['ref']} after the first outcome question, or to the end.", q,
                              outcome_ref=answerable[first_outcome]["ref"]))

    # Trust ------------------------------------------------------------------------------------------
    if settings["anonymous"] and st["pii_questions"]:
        refs = [q["ref"] for q in answerable if collects_pii(q)]
        out.append(_f("S21_anonymous_but_pii", "high", "trust",
                      "The survey is marked anonymous but collects personally identifying answers (email, phone, "
                      "wallet…). That's a promise you can't keep.",
                      "Remove the identifying questions or turn off the anonymous setting.", pii_refs=refs))
    return out


def _selection_hint(t: str, label: str) -> Tuple[Optional[str], Optional[str]]:
    """(matched hint, what the type allows) when the label's selection instruction contradicts the type."""
    if t in _SINGLE_TYPES:
        m = _MULTI_HINT.search(label)
        if m:
            return m.group(0), "one"
        for m in _MULTI_HINT_N.finditer(label):
            v = m.group(1).lower()
            if (_NUMBER_WORDS.get(v) or (int(v) if v.isdigit() else 0)) >= 2:
                return m.group(0), "one"
    elif t == "multi_choice":
        m = _SINGLE_HINT.search(label)
        if m:
            return m.group(0), "several"
    return None, None


def _between(key: str, lo: float, hi: float) -> bool:
    try:
        v = float(key)
    except (TypeError, ValueError):
        return False
    return lo < v < hi


def _shouting(label: str, opts: List[str]) -> bool:
    letters = [c for c in label if c.isalpha()]
    if letters and label == label.upper() and any(c.isupper() for c in letters) and _words(label) > 3:
        return True
    if label.count("?") >= 2 or label.count("!") >= 3:
        return True
    return any(o and not _HAS_ALNUM.search(o) for o in opts)


# --- CLI ------------------------------------------------------------------------------------

def _cell(x) -> str:
    return _text(x).replace("|", "\\|").replace("\n", " ") if x is not None else ""


def to_markdown(findings: List[Dict], polite: bool = False) -> str:
    if not findings:
        return "No static findings."
    rows = sorted(findings, key=lambda f: SEVERITY_ORDER.get(f["severity"], 9))
    if polite:
        lines = ["| Severity | Check | Question | Fix |", "| --- | --- | --- | --- |"]
        lines += [f"| {f['severity']} | {f['id']} | {_cell(f['question_ref'])} | {_cell(f['fix'])} |" for f in rows]
    else:
        lines = ["| Severity | Check | Question | Roast | Fix |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {f['severity']} | {f['id']} | {_cell(f['question_ref'])} | {_cell(f['roast'])} | "
                  f"{_cell(f['fix'])} |" for f in rows]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in args
    polite = "--polite" in args
    paths = [a for a in args if not a.startswith("--")]
    if len(paths) != 1:
        print("usage: survey_lint.py survey.json [--json] [--polite]", file=sys.stderr)
        return 2
    try:
        survey = load_survey(paths[0])
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    findings = run(survey)
    if as_json:
        if polite:
            findings_out = [{k: v for k, v in f.items() if k != "roast"} for f in findings]
        else:
            findings_out = findings
        print(json.dumps(findings_out, indent=2, ensure_ascii=False))
    else:
        print(to_markdown(findings, polite))
    return 1 if any(f["severity"] in ("blocker", "high") for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
