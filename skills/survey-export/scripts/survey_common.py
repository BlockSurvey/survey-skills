"""Shared helpers for blocksurvey-skills scripts: load and normalise the portable survey JSON.

Stdlib only, Python >= 3.9. Never crashes on None / wrong types: a field of the wrong type counts as missing.

    load_survey(path_or_text) -> dict      JSON file, JSON string, or markdown (via survey_export.from_markdown)
    normalise(survey)         -> dict      defaults, refs, clean text, logic graph, stats (input is not mutated)
"""

import copy
import html
import json
import math
import os
import re
from typing import Any, Dict, List, Optional

TYPES = ("single_choice", "multi_choice", "dropdown", "yes_no", "short_text", "long_text", "number", "rating",
         "nps", "likert", "matrix", "ranking", "slider", "date", "email", "phone", "file", "statement",
         "consent", "group")
NON_ANSWERABLE = {"statement", "group"}
OPEN_ENDED = {"short_text", "long_text"}
CHOICE = {"single_choice", "multi_choice", "dropdown", "ranking"}
PII_TYPES = {"email", "phone"}

# Seconds per type (shared/question-types.md#seconds-per-type, from BlockSurvey's SECONDS_PER_BTYPE)
SECONDS = {"single_choice": 10, "multi_choice": 15, "dropdown": 10, "yes_no": 10, "short_text": 30,
           "long_text": 60, "number": 15, "rating": 8, "nps": 8, "likert": 8, "ranking": 25, "slider": 10,
           "date": 12, "email": 15, "phone": 15, "file": 60, "statement": 8, "consent": 6, "group": 5}
DEFAULT_SECONDS = 12
MATRIX_SECONDS_PER_ROW = 8

REF_RE = re.compile(r"\bQ\d+(?:\.\d+)?\b")
_TAG_RE = re.compile(r"<[^>]*>")
_WS_RE = re.compile(r"\s+")


# --- null-safe accessors --------------------------------------------------------------------

def _d(x: Any) -> Dict:
    return x if isinstance(x, dict) else {}


def _l(x: Any) -> List:
    return x if isinstance(x, list) else []


def _text(x: Any) -> str:
    return x if isinstance(x, str) else ""


def _num(x: Any) -> Optional[float]:
    """A finite real number (not a bool), else None. json.loads accepts 1e999 (inf) and NaN; both count as missing."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def clean(x: Any) -> str:
    """Strip HTML tags, decode entities, collapse whitespace, trim. Non-strings become ''."""
    s = _text(x)
    if not s:
        return ""
    s = _TAG_RE.sub(" ", s)
    s = html.unescape(s).replace(" ", " ")
    return _WS_RE.sub(" ", s).strip()


def refs_in(text: Any) -> List[str]:
    """Question refs named in a condition, in order, without duplicates."""
    out: List[str] = []
    for r in REF_RE.findall(_text(text)):
        if r not in out:
            out.append(r)
    return out


def is_answerable(q: Dict) -> bool:
    return _d(q).get("type") not in NON_ANSWERABLE


def is_matrix(q: Dict) -> bool:
    q = _d(q)
    return q.get("type") == "matrix" or (q.get("type") == "likert" and bool(_l(q.get("rows"))))


def collects_pii(q: Dict) -> bool:
    q = _d(q)
    return q.get("collects_pii") is True or q.get("type") in PII_TYPES


def question_seconds(q: Dict) -> float:
    q = _d(q)
    if is_matrix(q):
        return MATRIX_SECONDS_PER_ROW * max(1, len(_l(q.get("rows"))))
    return SECONDS.get(q.get("type"), DEFAULT_SECONDS)


# --- loading --------------------------------------------------------------------------------

def load_survey(path_or_text: Any) -> Dict:
    """A path to a JSON/markdown file, a JSON string, or markdown text -> survey dict. Raises ValueError."""
    if isinstance(path_or_text, dict):
        return path_or_text
    if isinstance(path_or_text, os.PathLike):
        path_or_text = os.fspath(path_or_text)
    if not isinstance(path_or_text, str):
        raise ValueError(f"not a survey: expected a path or text, got {type(path_or_text).__name__}")
    text = path_or_text
    looks_like_path = "\n" not in text and len(text) < 4096 and not text.lstrip().startswith(("{", "["))
    if looks_like_path:
        if os.path.isfile(text):
            try:
                with open(text, encoding="utf-8") as fh:
                    text = fh.read()
            except (OSError, UnicodeDecodeError) as e:
                raise ValueError(f"not a survey: cannot read {path_or_text}: {e}")
        elif text.lower().endswith((".json", ".md", ".markdown", ".txt")):
            raise ValueError(f"not a survey: no such file {path_or_text}")
    try:
        data = json.loads(text)
    except ValueError:
        data = None
        try:
            from survey_export import from_markdown  # provided by Task 5; optional here
        except ImportError:
            raise ValueError(f"not a survey: not JSON and markdown import is unavailable ({text[:60]!r})")
        data = from_markdown(text)
    if not isinstance(data, dict):
        raise ValueError(f"not a survey: expected a JSON object, got {type(data).__name__}")
    return data


# --- normalising ----------------------------------------------------------------------------

def _str_list(x: Any) -> List[str]:
    out = []
    for item in _l(x):
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            item = str(item)
        s = clean(item)
        if s:
            out.append(s)
    return out


def _flatten(raw_questions: List) -> List[Dict]:
    """Drop non-dicts; lift children nested inside a group (`questions` / `children`) into the flat list."""
    flat: List[Dict] = []
    for raw in _l(raw_questions):
        if not isinstance(raw, dict):
            continue
        item = copy.deepcopy(raw)
        nested = None
        if item.get("type") == "group":
            nested = item.pop("questions", None) if isinstance(item.get("questions"), list) else None
            if nested is None and isinstance(item.get("children"), list):
                nested = item.pop("children")
        flat.append(item)
        for child in _l(nested):
            if isinstance(child, dict):
                child = copy.deepcopy(child)
                child["_nested_in"] = id(item)
                flat.append(child)
    return flat


def _norm_question(raw: Dict) -> Dict:
    q = dict(raw)
    q["type"] = _text(raw.get("type")).strip()
    q["label"] = clean(raw.get("label"))
    q["description"] = clean(raw.get("description"))
    q["required"] = raw.get("required") is True
    for flag in ("has_other", "has_none", "has_prefer_not_to_answer", "randomize_options", "sensitive",
                 "has_image", "collects_pii"):
        q[flag] = raw.get(flag) is True
    for key in ("options", "rows", "columns", "exclusive_options"):
        q[key] = _str_list(raw.get(key))
    scale = _d(raw.get("scale"))
    labels = {str(k): clean(v) for k, v in _d(scale.get("labels")).items() if clean(v)}
    q["scale"] = {**scale, "min": _num(scale.get("min")), "max": _num(scale.get("max")), "labels": labels}
    if q["type"] == "nps":
        if q["scale"]["min"] is None and q["scale"]["max"] is None:
            q["scale"]["min"], q["scale"]["max"] = 0, 10
    sel = _d(raw.get("selection"))
    q["selection"] = {**sel, "min": _int_or_none(sel.get("min")), "max": _int_or_none(sel.get("max"))}
    sw = _text(raw.get("shown_when")).strip()
    q["shown_when"] = sw or None
    q["shown_when_refs"] = refs_in(sw)
    jumps = []
    for j in _l(raw.get("jumps")):
        j = _d(j)
        to = _text(j.get("to")).strip()
        if not to:
            continue                        # a jump with no target is ignored (as the runtime does)
        when = _text(j.get("when")).strip() or None
        jumps.append({**j, "when": when, "to": to, "when_refs": refs_in(when)})
    q["jumps"] = jumps
    grp = raw.get("group")
    q["group"] = (str(grp).strip() or None) if isinstance(grp, (str, int)) and not isinstance(grp, bool) else None
    q["role"] = _text(raw.get("role")).strip() or "question"
    q["intent"] = _text(raw.get("intent")).strip() or None
    return q


def _int_or_none(x: Any) -> Optional[int]:
    n = _num(x)
    return int(n) if n is not None and n == int(n) else None


def _screen(x: Any) -> Optional[Dict]:
    if not isinstance(x, dict):
        return None
    return {**x, "title": clean(x.get("title")), "description": clean(x.get("description")),
            "button": clean(x.get("button"))}


def normalise(survey: Any) -> Dict:
    """Return a cleaned copy of the survey with derived logic facts and `stats`. Never mutates the input."""
    src = _d(survey)
    out = {k: copy.deepcopy(v) for k, v in src.items() if k != "questions"}
    out["title"] = clean(src.get("title"))
    out["description"] = clean(src.get("description"))
    out["kind"] = _text(src.get("kind")).strip() or None
    out["language"] = _text(src.get("language")).strip() or "en"
    out["welcome"] = _screen(src.get("welcome"))
    out["thank_you"] = _screen(src.get("thank_you"))
    st = _d(src.get("settings"))
    out["settings"] = {**st,
                       "stated_minutes": _num(st.get("stated_minutes")),
                       "progress_bar": st.get("progress_bar") is not False,
                       "anonymous": st.get("anonymous") is True,
                       "randomize_questions": st.get("randomize_questions") is True,
                       "sign_in_required": st.get("sign_in_required") is True,
                       "captcha": st.get("captcha") is True,
                       "multiple_submissions": st.get("multiple_submissions") is True}

    flat = _flatten(src.get("questions"))
    nested_owner = {i: q.pop("_nested_in", None) for i, q in enumerate(flat)}
    qs = [_norm_question(raw) for raw in flat]
    _assign_parents_and_refs(qs, flat, nested_owner)
    _apply_flow(qs, out["settings"]["randomize_questions"])
    out["questions"] = qs
    out["has_logic"] = any(q["shown_when"] or q["jumps"] for q in qs)
    out["stats"] = _stats(qs, out["settings"]["stated_minutes"])
    return out


def _assign_parents_and_refs(qs: List[Dict], flat: List[Dict], nested_owner: Dict[int, Any]) -> None:
    """Resolve each question's parent group, then fill missing refs: Q1.. for top level, Qn.m for children."""
    raw_ref = [_text(f.get("ref")).strip() for f in flat]
    groups = [i for i, q in enumerate(qs) if q["type"] == "group"]
    owner_index = {id(flat[i]): i for i in groups}

    # parent index for each question: nested placement, else `group` matching a group's ref, else its label
    parent: List[Optional[int]] = [None] * len(qs)
    for i, q in enumerate(qs):
        if q["type"] == "group":
            continue
        if nested_owner.get(i) in owner_index:
            parent[i] = owner_index[nested_owner[i]]
            continue
        key = q["group"]
        if not key:
            continue
        hit = next((g for g in groups if raw_ref[g] and raw_ref[g] == key), None)
        if hit is None:
            hit = next((g for g in groups if qs[g]["label"] and qs[g]["label"] == key), None)
        parent[i] = hit

    taken = {r for r in raw_ref if r}
    top_n = 0
    for i, q in enumerate(qs):
        if parent[i] is not None:
            continue
        top_n += 1
        ref = raw_ref[i]
        if not ref:
            ref = f"Q{top_n}"
            while ref in taken:
                ref += "'"
            taken.add(ref)
        q["ref"] = ref
    child_n: Dict[int, int] = {}
    for i, q in enumerate(qs):
        p = parent[i]
        if p is None:
            continue
        child_n[p] = child_n.get(p, 0) + 1
        ref = raw_ref[i]
        if not ref:
            ref = f"{qs[p]['ref']}.{child_n[p]}"
            while ref in taken:
                ref += "'"
            taken.add(ref)
        q["ref"] = ref
    for i, q in enumerate(qs):
        q["parent"] = qs[parent[i]]["ref"] if parent[i] is not None else None
    for g in groups:
        qs[g]["children"] = [qs[i]["ref"] for i in range(len(qs)) if parent[i] == g]


def _apply_flow(qs: List[Dict], shuffled: bool) -> None:
    """Jump graph -> reached_from / follows_unless / unreachable / has_logic (shared/static-checks.md#reachability-s28).

    After a question the first matching conditional jump wins, else the default (`when: null`), else the next
    question. Conditions are not evaluated: every conditional jump is a possible path. A jump to `end` or to an
    unknown ref ends the survey. A group is reached when any of its children is."""
    by_ref = {q["ref"]: q for q in qs}
    for q in qs:
        q["reached_from"] = []
    for q in qs:
        for j in q["jumps"]:
            target = by_ref.get(j["to"])
            if target is not None and target is not q:
                target["reached_from"].append({"from": q["ref"], "when": j["when"]})
    # follows_unless: the previous top-level question's conditional jumps that go somewhere else, i.e. "this
    # question follows Qn unless that jump fires" (top-level questions only; children and the first get []).
    prev_top: Optional[Dict] = None
    for q in qs:
        q["follows_unless"] = []
        if q["parent"] is not None:
            continue
        if prev_top is not None:
            q["follows_unless"] = [{"from": prev_top["ref"], "when": j["when"]} for j in prev_top["jumps"]
                                   if j["when"] is not None and j["to"] != q["ref"]]
        prev_top = q
    for q in qs:
        q["has_logic"] = bool(q["shown_when"] or q["jumps"] or q["reached_from"])
        q["unreachable"] = False
    if shuffled:
        return                          # "the question before it" is whatever the shuffle put there

    top = [q for q in qs if q["parent"] is None]
    nxt = {top[i]["ref"]: (top[i + 1]["ref"] if i + 1 < len(top) else None) for i in range(len(top))}

    def exits_always(q: Dict) -> bool:
        default = next((j for j in q["jumps"] if j["when"] is None), None)
        return default is not None and default["to"] != nxt.get(q["ref"])

    fall_through = {top[i]["ref"]: (i == 0 or not exits_always(top[i - 1])) for i in range(len(top))}
    top_pos = {q["ref"]: i for i, q in enumerate(top)}
    reachable = {q["ref"]: False for q in qs}
    changed = True
    while changed:
        changed = False
        for q in qs:
            ref = q["ref"]
            if reachable[ref]:
                continue
            if q["parent"] is None:
                i = top_pos[ref]
                ok = i == 0 or (fall_through[ref] and reachable[top[i - 1]["ref"]])
            else:
                ok = reachable.get(q["parent"], False)
            ok = ok or any(reachable.get(r["from"]) for r in q["reached_from"])
            if not ok and q["type"] == "group":
                ok = any(reachable.get(c) for c in q.get("children", []))
            if ok:
                reachable[ref] = changed = True
    for q in qs:
        q["unreachable"] = not reachable[q["ref"]]


def _stats(qs: List[Dict], stated: Optional[float]) -> Dict:
    answerable = [q for q in qs if is_answerable(q)]
    return {
        "top_level_questions": sum(1 for q in qs if q["parent"] is None),
        "answerable_questions": len(answerable),
        "required_answerable": sum(1 for q in answerable if q["required"]),
        "open_ended_questions": sum(1 for q in answerable if q["type"] in OPEN_ENDED),
        "pii_questions": sum(1 for q in answerable if collects_pii(q)),
        "questions_with_logic": sum(1 for q in qs if q["shown_when"] or q["jumps"]),
        "estimated_minutes": round(sum(question_seconds(q) for q in qs) / 60, 1),
        "stated_minutes": stated,
    }
