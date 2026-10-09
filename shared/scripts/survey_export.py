#!/usr/bin/env python3
"""Convert the portable survey JSON to markdown / CSV / plain text, and markdown (or a pasted list) back to JSON.

    python survey_export.py survey.json --format md|csv|txt|json [--out file]
    python survey_export.py survey.md --format json

    to_markdown(survey) -> str     canonical markdown form (shared/survey-format.md#markdown-form)
    from_markdown(text) -> dict    reads the canonical form back; also tolerant of loosely pasted question lists
    to_csv(survey)      -> str     ref,type,label,required,options,rows,columns,shown_when,jumps
    to_text(survey)     -> str     a clean numbered questionnaire for any tool's "import from text"

Exit codes: 0 ok, 2 invalid input. Stdlib only, Python >= 3.9. Never crashes on None / wrong types: a field of the
wrong type counts as missing.
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from survey_common import REF_RE, _d, _l, _num, _text, load_survey  # noqa: E402

OTHER = "Other (please specify)"
NONE = "None of the above"
PNA = "Prefer not to answer"
FLAG_OPTIONS = (("has_other", OTHER), ("has_none", NONE), ("has_prefer_not_to_answer", PNA))
EXCLUSIVE_MARK = " *(exclusive)*"
SETTINGS_DEFAULTS = (("progress_bar", True), ("anonymous", False), ("randomize_questions", False),
                     ("sign_in_required", False), ("captcha", False), ("multiple_submissions", False))
QUESTION_FLAGS = ("sensitive", "collects_pii", "has_image")
NON_NUMBERED = {"statement", "group"}

HEADING_RE = re.compile(r"^###\s+(\S+?)\.\s+(.*?)\s+`([A-Za-z_]+)`\s*(\(required\))?\s*$")
_ARROW = r"\s*(?:→|->)\s*"
JUMP_IF_RE = re.compile(r"^if\s+(.*?)" + _ARROW + r"(\S+)\s*$", re.I)
JUMP_ELSE_RE = re.compile(r"^otherwise" + _ARROW + r"(\S+)\s*$", re.I)
NUM_RE = r"-?\d+(?:\.\d+)?"
RANGE_RE = re.compile(r"^(" + NUM_RE + r")?\s*(?:–|—|-|to)\s*(" + NUM_RE + r")?$")


# --- small helpers --------------------------------------------------------------------------

def _one_line(x: Any) -> str:
    return " ".join(_text(x).split())


def _lines(x: Any) -> List[str]:
    """Non-empty, stripped lines of a multi-line text."""
    return [ln.strip() for ln in _text(x).splitlines() if ln.strip()]


def _strs(x: Any) -> List[str]:
    out = []
    for item in _l(x):
        if isinstance(item, (int, float)) and not isinstance(item, bool) and _num(item) is not None:
            item = _fmt(item)
        s = _one_line(item)
        if s:
            out.append(s)
    return out


def _fmt(n: Any) -> str:
    n = _num(n)
    if n is None:
        return ""
    return str(int(n)) if n == int(n) else str(n)


def _parse_num(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return int(f) if f == int(f) else f


def _questions(survey: Dict) -> List[Dict]:
    """The questions as dicts, flat (children nested in a group's `questions` / `children` follow it)."""
    out: List[Dict] = []
    for q in _l(survey.get("questions")):
        if not isinstance(q, dict):
            continue
        out.append(q)
        if q.get("type") == "group":
            nested = q.get("questions") if isinstance(q.get("questions"), list) else q.get("children")
            for c in _l(nested):
                if isinstance(c, dict):
                    out.append(c if _text(c.get("group")).strip() else {**c, "group": _text(q.get("ref"))})
    return out


def _refs(qs: List[Dict]) -> List[str]:
    out, n = [], 0
    for q in qs:
        n += 1
        out.append(_one_line(q.get("ref")) or f"Q{n}")
    return out


def _jumps(q: Dict) -> List[Dict]:
    out = []
    for j in _l(q.get("jumps")):
        j = _d(j)
        to = _one_line(j.get("to"))
        if to:
            out.append({"when": _one_line(j.get("when")) or None, "to": to})
    return out


def _options(q: Dict) -> List[str]:
    opts = _strs(q.get("options"))
    if not opts and q.get("type") == "yes_no":
        opts = ["Yes", "No"]
    return opts


def _has_table(q: Dict) -> bool:
    return bool(_strs(q.get("rows")) or _strs(q.get("columns")))


# --- markdown export ------------------------------------------------------------------------

def _cell(s: str) -> str:
    return s.replace("|", "\\|")


def _scale_line(scale: Any) -> Optional[str]:
    scale = _d(scale)
    lo, hi = _fmt(scale.get("min")), _fmt(scale.get("max"))
    labels = [(str(k), _one_line(v)) for k, v in _d(scale.get("labels")).items() if _one_line(v)]
    if not (lo or hi or labels):
        return None
    return "> Scale: " + f"{lo}–{hi}" + "".join(f" · {k} = {v}" for k, v in labels)


def _select_line(sel: Any) -> Optional[str]:
    sel = _d(sel)
    parts = [f"{k} {_fmt(sel.get(k))}" for k in ("min", "max") if _fmt(sel.get(k))]
    return "> Select: " + " · ".join(parts) if parts else None


def _question_md(q: Dict, ref: str) -> List[str]:
    qtype = _text(q.get("type")).strip()
    qtype = qtype if re.fullmatch(r"[A-Za-z_]+", qtype) else "unknown"
    out = [f"### {ref}. {_one_line(q.get('label'))}  `{qtype}`" + (" (required)" if q.get("required") is True else "")]
    out += _lines(q.get("description"))
    exclusive = set(_strs(q.get("exclusive_options")))
    for opt in _options(q):
        out.append(f"- [ ] {opt}" + (EXCLUSIVE_MARK if opt in exclusive else ""))
    for flag, text in FLAG_OPTIONS:
        if q.get(flag) is True:
            out.append(f"- [ ] {text}")
    if _has_table(q):
        cols, rows = _strs(q.get("columns")), _strs(q.get("rows"))
        out.append("| |" + "".join(f" {_cell(c)} |" for c in cols))
        out += [f"| {_cell(r)} |" + " |" * len(cols) for r in rows]
    meta = [_scale_line(q.get("scale")), _select_line(q.get("selection"))]
    if q.get("randomize_options") is True:
        meta.append("> Randomize options")
    grp = q.get("group")
    if isinstance(grp, (str, int)) and not isinstance(grp, bool) and _one_line(str(grp)):
        meta.append(f"> Group: {_one_line(str(grp))}")
    if _one_line(q.get("intent")):
        meta.append(f"> Intent: {_one_line(q.get('intent'))}")
    role = _one_line(q.get("role"))
    if role and role != "question":
        meta.append(f"> Role: {role}")
    flags = [f for f in QUESTION_FLAGS if q.get(f) is True]
    if flags:
        meta.append("> Flags: " + " · ".join(flags))
    if _one_line(q.get("shown_when")):
        meta.append(f"> Shown when: {_one_line(q.get('shown_when'))}")
    for j in _jumps(q):
        meta.append(f"> Jump: if {j['when']} → {j['to']}" if j["when"] else f"> Jump: otherwise → {j['to']}")
    return out + [m for m in meta if m]


def _screen_md(heading: str, screen: Any) -> List[str]:
    if not isinstance(screen, dict):
        return []
    out = [heading]
    if _one_line(screen.get("title")):
        out.append(f"**{_one_line(screen.get('title'))}**")
    out += _lines(screen.get("description"))
    if _one_line(screen.get("button")):
        out.append(f"[{_one_line(screen.get('button'))}]")
    return out


def to_markdown(survey: Any) -> str:
    """The canonical markdown form (shared/survey-format.md#markdown-form)."""
    s = _d(survey)
    out = [f"# {_one_line(s.get('title'))}".rstrip()]
    out += [f"> {ln}" for ln in _lines(s.get("description"))]
    settings = _d(s.get("settings"))
    minutes = _fmt(settings.get("stated_minutes"))
    head = [("Audience", _one_line(s.get("audience"))), ("Kind", _one_line(s.get("kind"))),
            ("Time", f"~{minutes} min" if minutes else "")]
    head2 = [("Sponsor", _one_line(s.get("sponsor"))), ("Purpose", _one_line(s.get("purpose"))),
             ("Language", _one_line(s.get("language")))]
    for parts in (head, head2):
        line = " · ".join(f"**{k}:** {v}" for k, v in parts if v)
        if line:
            out.append(line)
    changed = [f"{k}={'true' if settings.get(k) else 'false'}" for k, default in SETTINGS_DEFAULTS
               if isinstance(settings.get(k), bool) and settings.get(k) is not default]
    if changed:
        out.append("**Settings:** " + " · ".join(changed))
    out += _screen_md("## Welcome", s.get("welcome"))
    qs = _questions(s)
    out.append("## Questions")
    for q, ref in zip(qs, _refs(qs)):
        out += _question_md(q, ref)
    out += _screen_md("## Thank you", s.get("thank_you"))
    return "\n".join(out) + "\n"


# --- markdown import (canonical) ------------------------------------------------------------

def _split_row(line: str) -> List[str]:
    cells = re.split(r"(?<!\\)\|", line.strip())
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [c.strip().replace("\\|", "|") for c in cells]


def _parse_screen(lines: List[str]) -> Optional[Dict]:
    lines = [ln.strip() for ln in lines if ln.strip()]
    screen: Dict[str, str] = {}
    if lines and re.fullmatch(r"\*\*(.+)\*\*", lines[0]):
        screen["title"] = lines.pop(0)[2:-2].strip()
    button = None
    if lines and re.fullmatch(r"\[(.*)\]", lines[-1]):
        button = lines.pop()[1:-1].strip()
    if lines:
        screen["description"] = "\n".join(lines)
    if button:
        screen["button"] = button
    return screen


def _parse_header_meta(line: str, out: Dict) -> bool:
    parts = [p.strip() for p in line.split(" · ")]
    pairs = [re.fullmatch(r"\*\*([A-Za-z ]+):\*\*\s*(.*)", p) for p in parts]
    if not pairs or not all(pairs):
        return False
    settings = out.setdefault("settings", {})
    for m in pairs:
        key, val = m.group(1).strip().lower(), m.group(2).strip()
        if key == "time":
            mm = re.search(NUM_RE, val)
            if mm:
                settings["stated_minutes"] = _parse_num(mm.group(0))
        elif key == "settings":
            for item in val.split(" · "):
                if "=" in item:
                    k, v = (x.strip() for x in item.split("=", 1))
                    if k and v.lower() in ("true", "false"):
                        settings[k] = v.lower() == "true"
        elif key in ("audience", "kind", "sponsor", "purpose", "language") and val:
            out[key] = val
    return True


def _new_question(m: "re.Match") -> Dict:
    return {"ref": m.group(1), "type": m.group(3), "label": m.group(2).strip(), "required": bool(m.group(4)),
            "_desc": [], "_opts": [], "_table": [], "_meta": []}


def _finish_question(raw: Dict) -> Dict:
    q: Dict[str, Any] = {k: raw[k] for k in ("ref", "type", "label", "required")}
    if raw["_desc"]:
        q["description"] = "\n".join(raw["_desc"])
    options, exclusive = [], []
    for opt in raw["_opts"]:
        flag = next((f for f, text in FLAG_OPTIONS if opt.lower() == text.lower()), None)
        if flag:
            q[flag] = True
            continue
        if opt.endswith(EXCLUSIVE_MARK.strip()):
            opt = opt[: -len(EXCLUSIVE_MARK.strip())].strip()
            exclusive.append(opt)
        if opt:
            options.append(opt)
    if options:
        q["options"] = options
    if exclusive:
        q["exclusive_options"] = exclusive
    table = [_split_row(ln) for ln in raw["_table"]]
    table = [t for t in table if not (t and all(re.fullmatch(r":?-{3,}:?", c) for c in t if c) and any(t))]
    if table:
        cols = [c for c in table[0][1:] if c]
        rows = [t[0] for t in table[1:] if t and t[0]]
        if cols:
            q["columns"] = cols
        if rows:
            q["rows"] = rows
    jumps = []
    for meta in raw["_meta"]:
        key, _, val = meta.partition(":")
        key, val = key.strip().lower(), val.strip()
        if key == "scale":
            _parse_scale(val, q)
        elif key == "select":
            sel = {}
            for part in val.split(" · "):
                mm = re.fullmatch(r"(min|max)\s+(" + NUM_RE + r")", part.strip())
                if mm:
                    sel[mm.group(1)] = int(float(mm.group(2)))
            if sel:
                q["selection"] = sel
        elif key == "randomize options":
            q["randomize_options"] = True
        elif key == "group" and val:
            q["group"] = val
        elif key == "intent" and val:
            q["intent"] = val
        elif key == "role" and val:
            q["role"] = val
        elif key == "flags":
            for f in val.split(" · "):
                if f.strip() in QUESTION_FLAGS:
                    q[f.strip()] = True
        elif key == "shown when" and val:
            q["shown_when"] = val
        elif key == "jump":
            mi, me = JUMP_IF_RE.match(val), JUMP_ELSE_RE.match(val)
            if mi and mi.group(1).strip():
                jumps.append({"when": mi.group(1).strip(), "to": mi.group(2)})
            elif me:
                jumps.append({"when": None, "to": me.group(1)})
    if jumps:
        q["jumps"] = jumps
    return q


def _parse_scale(val: str, q: Dict) -> None:
    parts = [p.strip() for p in val.split(" · ")]
    scale: Dict[str, Any] = {}
    mm = RANGE_RE.match(parts[0]) if parts else None
    if mm:
        for key, g in (("min", 1), ("max", 2)):
            n = _parse_num(mm.group(g))
            if n is not None:
                scale[key] = n
    labels = {}
    for p in parts[1:] if mm else parts:
        lm = re.fullmatch(r"(.+?)\s*=\s*(.+)", p)
        if lm:
            labels[lm.group(1).strip()] = lm.group(2).strip()
    if labels:
        scale["labels"] = labels
    if scale:
        q["scale"] = scale


def _from_canonical(lines: List[str]) -> Dict:
    out: Dict[str, Any] = {"title": ""}
    desc: List[str] = []
    section = "header"
    screens: Dict[str, List[str]] = {"welcome": [], "thank_you": []}
    seen_screens = set()
    raws: List[Dict] = []
    cur: Optional[Dict] = None
    for line in lines:
        s = line.strip()
        m = HEADING_RE.match(s)
        if m:
            cur = _new_question(m)
            raws.append(cur)
            section = "questions"
            continue
        if s.startswith("## "):
            name = s[3:].strip().lower()
            cur = None
            if name == "welcome":
                section = "welcome"
            elif name in ("thank you", "thanks", "thank-you"):
                section = "thank_you"
            elif name == "questions":
                section = "questions"
            else:
                section = "other"
            if section in screens:
                seen_screens.add(section)
            continue
        if s.startswith("# ") and section == "header" and not out["title"]:
            out["title"] = s[2:].strip()
            continue
        if section == "header":
            if s.startswith(">"):
                desc.append(s[1:].strip())
            elif s and not _parse_header_meta(s, out):
                desc.append(s)
        elif section in screens:
            screens[section].append(line)
        elif section == "questions" and cur is not None and s:
            if re.match(r"^[-*]\s+", s):
                opt = re.sub(r"^[-*]\s+(\[[ xX]?\]\s*)?", "", s).strip()
                if opt:
                    cur["_opts"].append(opt)
            elif s.startswith("|"):
                cur["_table"].append(s)
            elif s.startswith(">"):
                cur["_meta"].append(s[1:].strip())
            else:
                cur["_desc"].append(s)
    desc = [d for d in desc if d]
    if desc:
        out["description"] = "\n".join(desc)
    for name in ("welcome", "thank_you"):
        if name in seen_screens:
            out[name] = _parse_screen(screens[name])
    out["questions"] = [_finish_question(r) for r in raws]
    out.setdefault("settings", {})
    return out


# --- markdown import (loose: pasted question lists) -----------------------------------------

Q_LINE_RE = re.compile(r"^(?:Q(?:uestion)?\s*)?\d+\s*[.):]\s*(.+)$", re.I)
BULLET_RE = re.compile(r"^[-*•+○●☐□◯]\s+(\[[ xX]?\]\s*)?(.*)$")
LETTER_RE = re.compile(r"^\(?[A-Za-z][).]\s+(.+)$")
HINT_RE = re.compile(r"\(([^()]*)\)")
SCREEN_RE = re.compile(r"^(welcome|thank[- ]?you)(?:\s+(?:screen|message|page))?\s*(?::\s*(.*))?$", re.I)
SHOW_RE = re.compile(r"^show (?:only )?(?:if|when)\s+(.+)$", re.I)
GOTO_RE = re.compile(r"^if\s+(.+?)\s*(?:,\s*)?(?:go|skip|jump) to\s+(.+?)\.?$", re.I)
ELSE_RE = re.compile(r"^otherwise(?:,)?\s*(?:go|skip|jump) to\s+(.+?)\.?$", re.I)

HINTS = {
    "select one": "single_choice", "choose one": "single_choice", "pick one": "single_choice",
    "select all that apply": "multi_choice", "check all": "multi_choice", "check all that apply": "multi_choice",
    "choose all that apply": "multi_choice", "select multiple": "multi_choice", "select all": "multi_choice",
    "yes/no": "yes_no", "y/n": "yes_no",
    "short answer": "short_text", "short text": "short_text",
    "long answer": "long_text", "long text": "long_text", "open": "long_text", "open-ended": "long_text",
    "open ended": "long_text", "paragraph": "long_text",
    "date": "date", "email": "email", "email address": "email", "phone": "phone", "phone number": "phone",
    "number": "number", "rank the items": "ranking", "rank": "ranking", "ranking": "ranking",
    "rate each row": "matrix", "file upload": "file", "upload": "file", "dropdown": "dropdown",
    "slider": "slider", "check to agree": "consent",
}


def _strip_hints(label: str) -> Dict[str, Any]:
    """Pull recognised parenthesised hints out of a label: type, scale range, required."""
    info: Dict[str, Any] = {"type": None, "scale": None, "required": False}

    def repl(m: "re.Match") -> str:
        key = " ".join(m.group(1).lower().replace(" / ", "/").split())
        if key == "required":
            info["required"] = True
            return ""
        if key in HINTS:
            info["type"] = info["type"] or HINTS[key]
            return ""
        rm = RANGE_RE.match(key)
        if rm and rm.group(1) and rm.group(2):
            lo, hi = _parse_num(rm.group(1)), _parse_num(rm.group(2))
            info["type"] = info["type"] or ("nps" if (lo, hi) == (0, 10) else "rating")
            info["scale"] = {"min": lo, "max": hi}
            return ""
        return m.group(0)

    label = HINT_RE.sub(repl, label)
    label = " ".join(label.split())
    if label.endswith(" *") or label.endswith("*") and not label.endswith("**"):
        label, info["required"] = label.rstrip("*").rstrip(), True
    info["label"] = label
    return info


def _infer(raw: Dict) -> Dict:
    info = _strip_hints(raw["label"])
    label, opts, rows, cols = info["label"], raw["options"], raw["rows"], raw["columns"]
    low = label.lower()
    qtype = info["type"]
    scale = info["scale"]
    if qtype is None:
        if rows and cols:
            qtype = "matrix"
        elif len(opts) == 2 and sorted(o.lower() for o in opts) == ["no", "yes"]:
            qtype = "yes_no"
        elif "recommend" in low and (re.search(r"\b0\s*(?:–|—|-|to)\s*10\b", low) or not opts):
            qtype = "nps"
        elif opts:
            qtype = "single_choice"
        elif low.rstrip().endswith("why?") or re.search(r"\b(describe|explain)\b", low):
            qtype = "long_text"
        else:
            qtype = "short_text"
    if qtype == "nps" and scale is None:
        scale = {"min": 0, "max": 10}
    q: Dict[str, Any] = {"ref": "", "type": qtype, "label": label, "required": info["required"], "inferred": True}
    if raw["desc"]:
        q["description"] = "\n".join(raw["desc"])
    options = []
    for o in opts:
        flag = next((f for f, text in FLAG_OPTIONS if o.lower() == text.lower()), None)
        if flag is None and re.fullmatch(r"other\s*(?:\(please specify\)|:|\.\.\.|…)?", o.lower()):
            flag = "has_other"
        if flag:
            q[flag] = True
        else:
            options.append(o)
    if options:
        q["options"] = options
    if rows:
        q["rows"] = rows
    if cols:
        q["columns"] = cols
    if scale:
        q["scale"] = scale
    if raw["shown_when"]:
        q["shown_when"] = raw["shown_when"]
    if raw["jumps"]:
        q["jumps"] = raw["jumps"]
    return q


def _goto_target(t: str) -> str:
    t = t.strip().strip(".").strip()
    return "end" if t.lower() in ("the end", "end", "the end of the survey", "end of survey") else t


def _from_loose(lines: List[str]) -> Dict:
    out: Dict[str, Any] = {"title": ""}
    desc: List[str] = []
    raws: List[Dict] = []
    cur: Optional[Dict] = None
    mode = "body"                       # body | welcome | thank_you
    screens: Dict[str, Dict[str, Any]] = {}
    sub = "options"                     # options | rows | columns (after "Rows:" / "Columns:")

    def start(label: str) -> Dict:
        nonlocal mode, sub
        mode, sub = "body", "options"
        q = {"label": label, "options": [], "rows": [], "columns": [], "desc": [], "shown_when": None, "jumps": []}
        raws.append(q)
        return q

    for line in lines:
        s = line.strip().replace("**", "")
        if not s:
            continue
        if s.startswith("#"):
            level = len(s) - len(s.lstrip("#"))
            s = s.lstrip("#").strip()
            if level == 1 and not out["title"] and not raws:
                out["title"] = s
                continue
            if not s:
                continue
            if not Q_LINE_RE.match(s) and not SCREEN_RE.match(s):
                continue                # a section heading ("## Questions")
        sm = SCREEN_RE.match(s)
        if sm:
            mode = "welcome" if sm.group(1).lower().startswith("w") else "thank_you"
            screens[mode] = {"title": (sm.group(2) or "").strip(), "desc": []}
            cur = None
            continue
        qm = Q_LINE_RE.match(s)
        if qm:
            cur = start(qm.group(1).strip())
            continue
        bm = BULLET_RE.match(s)
        if bm:
            text, checkbox = bm.group(2).strip(), bool(bm.group(1))
            if not text:
                continue
            if cur is None and mode != "body":
                screens[mode]["desc"].append(s)
                continue
            if cur is None or (not checkbox and _strip_hints(text)["label"].endswith("?") and sub == "options"):
                cur = start(text)
                continue
            cur[sub].append(text)
            continue
        lm = LETTER_RE.match(s)
        if lm and cur is not None:
            cur[sub].append(lm.group(1).strip())
            continue
        if cur is not None:
            low = s.lower().rstrip(":")
            if low in ("rows", "columns", "options"):
                sub = low
                continue
            show, goto, other = SHOW_RE.match(s), GOTO_RE.match(s), ELSE_RE.match(s)
            if show:
                cur["shown_when"] = show.group(1).strip().rstrip(".")
                continue
            if goto:
                cur["jumps"].append({"when": goto.group(1).strip(), "to": _goto_target(goto.group(2))})
                continue
            if other:
                cur["jumps"].append({"when": None, "to": _goto_target(other.group(1))})
                continue
        if re.match(r"^section\s*:", s, re.I):
            continue
        if mode != "body" and cur is None:
            screens[mode]["desc"].append(s)
            continue
        if _strip_hints(s)["label"].endswith("?") and (cur is not None or out["title"]):
            cur = start(s)
            continue
        if cur is not None:
            cur["desc"].append(s)
        elif not out["title"]:
            out["title"] = s
        else:
            desc.append(s)
    if desc:
        out["description"] = "\n".join(desc)
    for name, scr in screens.items():
        screen: Dict[str, str] = {}
        if scr["title"]:
            screen["title"] = scr["title"]
        if scr["desc"]:
            screen["description"] = "\n".join(scr["desc"])
        out[name] = screen
    qs = [_infer(r) for r in raws]
    for i, q in enumerate(qs, 1):
        q["ref"] = f"Q{i}"
    out["questions"] = qs
    out["settings"] = {}
    return out


def from_markdown(text: Any) -> Dict:
    """Markdown (canonical form) or a loosely pasted question list -> survey dict. Never raises."""
    if not isinstance(text, str):
        return {"title": "", "settings": {}, "questions": []}
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if any(HEADING_RE.match(ln.strip()) for ln in lines):
        return _from_canonical(lines)
    return _from_loose(lines)


# --- csv ------------------------------------------------------------------------------------

CSV_COLUMNS = ["ref", "type", "label", "required", "options", "rows", "columns", "shown_when", "jumps"]


def _jumps_cell(q: Dict) -> str:
    return "; ".join(f"if {j['when']} → {j['to']}" if j["when"] else f"otherwise → {j['to']}" for j in _jumps(q))


def to_csv(survey: Any) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    w.writerow(CSV_COLUMNS)
    qs = _questions(_d(survey))
    for q, ref in zip(qs, _refs(qs)):
        w.writerow([ref, _one_line(q.get("type")), _one_line(q.get("label")),
                    "true" if q.get("required") is True else "false",
                    "|".join(_strs(q.get("options"))), "|".join(_strs(q.get("rows"))),
                    "|".join(_strs(q.get("columns"))), _one_line(q.get("shown_when")), _jumps_cell(q)])
    return buf.getvalue()


# --- plain text -----------------------------------------------------------------------------

def _range_hint(q: Dict, default: str) -> str:
    scale = _d(q.get("scale"))
    lo, hi = _fmt(scale.get("min")), _fmt(scale.get("max"))
    return f"({lo}–{hi})" if lo and hi else default


def _type_hint(q: Dict) -> str:
    t = _text(q.get("type"))
    if t == "matrix" or (t == "likert" and _strs(q.get("rows"))):
        return "(rate each row)"
    if t == "likert":
        return "(select one)" if _strs(q.get("options")) else _range_hint(q, "(1–5)")
    return {
        "single_choice": "(select one)", "dropdown": "(select one)", "multi_choice": "(select all that apply)",
        "nps": "(0–10)", "rating": _range_hint(q, "(1–5)"), "slider": _range_hint(q, "(slider)"),
        "ranking": "(rank the items)", "yes_no": "(yes/no)", "short_text": "(short answer)",
        "long_text": "(long answer)", "date": "(date)", "email": "(email)", "phone": "(phone)",
        "number": "(number)", "file": "(file upload)", "consent": "(check to agree)",
    }.get(t, "")


def to_text(survey: Any) -> str:
    """A numbered plain-text questionnaire: title, intro, questions with type hints and options, logic, screens."""
    s = _d(survey)
    qs = _questions(s)
    refs = _refs(qs)
    number: Dict[str, str] = {}
    n = 0
    for q, ref in zip(qs, refs):
        if _text(q.get("type")) not in NON_NUMBERED:
            n += 1
            number[ref] = f"Q{n}"

    def cond(text: str) -> str:
        return REF_RE.sub(lambda m: number.get(m.group(0), m.group(0)), text)

    out: List[str] = [_one_line(s.get("title")) or "Untitled survey", ""]
    intro = _lines(s.get("description"))
    if intro:
        out += intro + [""]
    welcome = s.get("welcome")
    if isinstance(welcome, dict) and (_one_line(welcome.get("title")) or _lines(welcome.get("description"))):
        out.append(f"Welcome: {_one_line(welcome.get('title'))}".rstrip())
        out += _lines(welcome.get("description")) + [""]
    for q, ref in zip(qs, refs):
        qtype = _text(q.get("type"))
        label = _one_line(q.get("label"))
        if qtype == "group":
            out += [f"Section: {label}", ""]
            continue
        if qtype == "statement":
            out += [label] + _lines(q.get("description")) + [""]
            continue
        head = f"{number[ref][1:]}. {label}"
        hint = _type_hint(q)
        if hint:
            head += f" {hint}"
        if q.get("required") is True:
            head += " (required)"
        block = [head] + [f"   {ln}" for ln in _lines(q.get("description"))]
        opts = _strs(q.get("options"))
        if qtype == "yes_no" and [o.lower() for o in opts] == ["yes", "no"]:
            opts = []
        opts += [text for flag, text in FLAG_OPTIONS if q.get(flag) is True]
        block += [f"   - {o}" for o in opts]
        if _strs(q.get("rows")):
            block += ["   Rows:"] + [f"   - {r}" for r in _strs(q.get("rows"))]
        if _strs(q.get("columns")):
            block += ["   Columns:"] + [f"   - {c}" for c in _strs(q.get("columns"))]
        labels = [(str(k), _one_line(v)) for k, v in _d(_d(q.get("scale")).get("labels")).items() if _one_line(v)]
        if labels:
            block.append("   Scale: " + " · ".join(f"{k} = {v}" for k, v in labels))
        sel = _d(q.get("selection"))
        lo, hi = _fmt(sel.get("min")), _fmt(sel.get("max"))
        if lo or hi:
            block.append("   Choose " + " and ".join(p for p in (f"at least {lo}" if lo else "",
                                                                   f"at most {hi}" if hi else "") if p) + ".")
        if _one_line(q.get("shown_when")):
            block.append(f"   Show only if {cond(_one_line(q.get('shown_when')))}")
        for j in _jumps(q):
            to = "the end" if j["to"].lower() == "end" else number.get(j["to"], j["to"])
            block.append(f"   If {cond(j['when'])} go to {to}" if j["when"] else f"   Otherwise go to {to}")
        out += block + [""]
    thanks = s.get("thank_you")
    if isinstance(thanks, dict) and (_one_line(thanks.get("title")) or _lines(thanks.get("description"))):
        out.append(f"Thank you: {_one_line(thanks.get('title'))}".rstrip())
        out += _lines(thanks.get("description")) + [""]
    while out and not out[-1]:
        out.pop()
    return "\n".join(out) + "\n"


# --- CLI ------------------------------------------------------------------------------------

FORMATS = {"md": to_markdown, "csv": to_csv, "txt": to_text,
           "json": lambda s: json.dumps(s, indent=2, ensure_ascii=False) + "\n"}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Convert a survey between JSON, markdown, CSV and plain text.")
    ap.add_argument("survey", help="survey file: .json or .md (canonical markdown or a pasted question list)")
    ap.add_argument("--format", choices=sorted(FORMATS), help="output format (default: md for JSON input, "
                                                              "json otherwise)")
    ap.add_argument("--out", help="write here instead of stdout")
    args = ap.parse_args(argv)
    try:
        survey = load_survey(args.survey)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    fmt = args.format or ("md" if args.survey.lower().endswith(".json") else "json")
    text = FORMATS[fmt](survey)
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
        except OSError as e:
            print(f"error: cannot write {args.out}: {e}", file=sys.stderr)
            return 2
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
