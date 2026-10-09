#!/usr/bin/env python3
"""Optional API judge: answers the rubric (shared/rubric.md) through an LLM API and writes a judgments JSON.

You do not need this script. By default the chat assistant you are talking to judges the rubric. Use it when you
want scoring without a chat in the loop (CI, batch runs, re-scoring many surveys) and have an API key for one of:

    jev        TypeSafe Jev (calibrated judgments)    TYPESAFE_API_KEY   default model jev-latest
    openai     OpenAI chat completions                OPENAI_API_KEY     default model gpt-4o-mini
    anthropic  Anthropic messages API                 ANTHROPIC_API_KEY  default model claude-haiku-5-5

    python survey_judge.py survey.json --provider anthropic --dry-run          # plan + cost estimate, no network
    python survey_judge.py survey.json --provider anthropic --out judgments.json
    python survey_score_calc.py survey.json judgments.json --lint

    judge(survey, provider, model, api_key) -> judgments dict (shared/scoring.md#judgments-json-contract)

Keys come from the environment or from a `.env` file in the current directory (see .env.example); key values are
never printed. Nothing is sent unless --provider is given. Every run prints an input-token and cost estimate first
and refuses (exit 2) without --yes when it exceeds $1 or the model's price is unknown.

Exit codes: 0 complete, 1 partial judgments (some requests failed; see meta.errors), 2 usage, key or cost refusal.

Stdlib only (urllib.request, json, os, time): a deliberate zero-dependency choice for this public repo, so the
script runs anywhere Python >= 3.9 does without installing an SDK.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import survey_score_calc as calc_mod  # noqa: E402
from survey_common import _d, _l, load_survey, normalise  # noqa: E402
from survey_score_calc import ITEMS, QUESTION_ITEM_IDS, RUBRIC_VERSION, SURVEY_ITEM_IDS  # noqa: E402

PROVIDERS = ("jev", "openai", "anthropic")
DEFAULT_MODELS = {"jev": "jev-latest", "openai": "gpt-4o-mini", "anthropic": "claude-haiku-5-5"}
KEY_ENV = {"jev": "TYPESAFE_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
MODEL_ENV = {"jev": "TYPESAFE_MODEL", "openai": "OPENAI_MODEL", "anthropic": "ANTHROPIC_MODEL"}
JEV_BASE_URL = "https://api.typesafe.ai"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_MAX_TOKENS = 16000

# USD per million tokens (input, output). Verified 2026-10-09; prices change, so output says "verify current pricing".
PRICES = {
    "jev-latest": (0.042, 0.0),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-haiku-5-5": (0.10, 0.50),       # prompts up to 100k tokens
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
}
COST_CAP = 1.0                              # USD; above this (or with an unknown price) a run needs --yes
CHARS_PER_TOKEN = 4
OUTPUT_TOKENS_PER_ANSWER = 15               # chat providers return JSON; rough estimate per judged item

JEV_BATCH = 6                               # questions per Jev request (as the shipped evaluator does)
CHAT_BATCH_LARGE = 50                       # chat: all questions in one request, chunks of 50 above 150 questions
CHAT_ALL_UP_TO = 150
RETRY_STATUS = {429, 503, 529}
ATTEMPTS = 3
BACKOFF = 1.0                               # seconds; doubles each retry (1, 2)
TIMEOUT = 180
NOTE_MAX = 200

TASK_SURVEY = "TASK: judge the survey-level items"
TASK_QUESTIONS = "TASK: judge the per-question items"

NOUL_DEFAULT_CRITERIA = {"true": "Yes, the statement is true", "false": "No, the statement is not true"}


class JudgeError(Exception):
    """A request that failed after retries (message never contains the key)."""

    def __init__(self, message: str, fatal: bool = False):
        super().__init__(message)
        self.fatal = fatal


# --- environment ------------------------------------------------------------------------------

def read_dotenv(path: str = ".env") -> Dict[str, str]:
    """Simple KEY=value parser: comments, blank lines, optional `export ` and surrounding quotes."""
    out: Dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key.strip()] = value
    return out


def setting(name: str, dotenv: Dict[str, str]) -> str:
    """Environment wins over .env; empty values count as unset."""
    return (os.environ.get(name) or dotenv.get(name) or "").strip()


def resolve_model(provider: str, model: Optional[str], dotenv: Optional[Dict[str, str]] = None) -> str:
    return model or setting(MODEL_ENV[provider], dotenv or {}) or DEFAULT_MODELS[provider]


# --- what to ask --------------------------------------------------------------------------------

def applicable_items(s: Dict) -> Tuple[List[str], Dict[str, List[str]]]:
    """Survey-level item ids and per-question item ids worth asking, before any judgment exists.

    Reuses the calculator's applicability rules (survey_score_calc._Ctx), widened so one pass covers whatever the
    judge decides: kinds gating is off (the judge may name a different kind than the survey's `kind` field), the
    F3b gate assumes an incentive was mentioned and the Q16 gate assumes the question is sensitive. The calculator
    ignores answers to items that end up not applying.
    """
    ctx = calc_mod._Ctx(s, {})
    ctx.kind = None
    ctx.sj = {"F3a_incentive_mentioned": {"p": 1.0}}
    ctx.qj = {q["ref"]: {"Q12_sensitive": {"p": 1.0}} for q in ctx.qs}
    survey_items = [i for i in SURVEY_ITEM_IDS if ctx.survey_item_applies(i)]
    per_question = {q["ref"]: ctx.items_for(q) for q in ctx.qs}
    return survey_items, per_question


_Q_FIELDS = ("ref", "type", "role", "label", "description", "options", "rows", "columns", "required", "has_other",
             "has_none", "has_prefer_not_to_answer", "exclusive_options", "group", "shown_when", "jumps",
             "reached_from", "intent", "scale", "selection")


def _compact(x: Any) -> Any:
    """Drop empty values (None, '', [], {}, False) to keep the request small."""
    if isinstance(x, dict):
        out = {k: _compact(v) for k, v in x.items()}
        return {k: v for k, v in out.items() if v not in (None, "", [], {}, False)}
    if isinstance(x, list):
        return [_compact(v) for v in x]
    return x


def _question_digest(q: Dict) -> Dict:
    d = {k: q.get(k) for k in _Q_FIELDS}
    d["jumps"] = [{"when": j.get("when"), "to": j.get("to")} for j in _l(q.get("jumps")) if isinstance(j, dict)]
    if not d["scale"] or not any(v not in (None, {}, "") for v in _d(d["scale"]).values()):
        d["scale"] = None
    if not d["selection"] or not any(v is not None for v in _d(d["selection"]).values()):
        d["selection"] = None
    return _compact(d)


def _purpose(s: Dict) -> str:
    parts = [s.get("purpose") or "", s.get("description") or "", _d(s.get("welcome")).get("description") or ""]
    return " ".join(p for p in parts if p)[:600]


def survey_state(s: Dict) -> Dict:
    """The survey as the judge sees it, with the context paths rubric.md names (`stats`, `scales`, …)."""
    scales = [_compact({"ref": q["ref"], "type": q["type"], "label": q["label"], "options": q["options"],
                        "columns": q["columns"], "scale_labels": _d(q.get("scale")).get("labels")})
              for q in s["questions"]
              if q["type"] in calc_mod.SCALE_TYPES or (q["type"] in ("single_choice", "dropdown")
                                                         and len(q["options"]) >= 3)]
    state = {k: s.get(k) for k in ("title", "description", "kind", "audience", "purpose", "sponsor", "language",
                                    "welcome", "thank_you")}
    state["settings"] = s.get("settings")
    state["stats"] = {"answerable_questions": s["stats"].get("answerable_questions"),
                      "estimated_minutes": s["stats"].get("estimated_minutes")}
    state["scales"] = scales
    state["questions"] = [_question_digest(q) for q in s["questions"]]
    return _compact(state)


def _question_context(s: Dict, q: Dict) -> Dict:
    qs = s["questions"]
    by_ref = {x["ref"]: x for x in qs}
    i = qs.index(q)
    d = _question_digest(q)
    if i > 0:
        p = qs[i - 1]
        d["previous_question"] = _compact({"ref": p["ref"], "type": p["type"], "label": p["label"],
                                           "options": p["options"]})
    g = by_ref.get(q.get("group") or "")
    if g:
        d["parent_group"] = _compact({"ref": g["ref"], "label": g["label"], "description": g["description"]})
    if i + 1 < len(qs):
        d["next_question"] = _compact({"ref": qs[i + 1]["ref"], "label": qs[i + 1]["label"]})
    return d


def _criteria(iid: str) -> Any:
    item = ITEMS[iid]
    if item["primitive"] == "noul":
        return item["criteria"] or NOUL_DEFAULT_CRITERIA
    return item["criteria"]


_REWRITE = re.compile(r"`(question|previous_question|parent_group|reached_from)(\.[^`]*)?`")


def rewrite_for_batch(instructions: str, i: int) -> str:
    """`question.label` -> `questions[i].label`, `previous_question` -> `questions[i].previous_question`, …"""
    def sub(m: "re.Match") -> str:
        head, rest = m.group(1), m.group(2) or ""
        if head == "question":
            return f"`questions[{i}]{rest}`"
        return f"`questions[{i}].{head}{rest}`"
    return _REWRITE.sub(sub, instructions)


def _item_spec(iid: str) -> Dict:
    item = ITEMS[iid]
    spec = {"id": iid, "primitive": item["primitive"], "instructions": item["instructions"]}
    if item["primitive"] == "score":
        spec["levels"] = item["levels"]
        spec["criteria"] = {str(n): c for n, c in enumerate(item["criteria"])}
    elif item["primitive"] == "choice":
        spec["criteria"] = item["criteria"]
    elif item["criteria"]:
        spec["criteria"] = item["criteria"]
    return spec


# --- request bodies ------------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an experienced survey methodologist judging a survey against a rubric.
Read the survey JSON, then answer every listed item, judging only from the survey text.

Answer shapes:
- score item: {"level": <integer 0..levels-1>, "confidence": <0..1>}. Level 0 is the worst criterion, the highest level the best; pick the criterion that fits.
- noul item: {"p": <0..1>} = the probability that the statement asked in the instruction is TRUE.
- choice item: {"choice": "<one of the item's criteria keys>", "confidence": <0..1>}.
- Optional "note" (at most 200 characters) quoting the survey words that led to the answer; add it only where it helps.

Context paths in instructions: `title`, `description`, `welcome`, `thank_you`, `questions`, `stats`, `scales` are top-level fields of the survey JSON. `survey.title` / `survey.purpose` mean `title` / `purpose` + `description` + `welcome.description`. For per-question items, `question` is the question being judged (its fields `label`, `description`, `options`, `type`, `role`, …), `previous_question` is the entry immediately before it in `questions`, `parent_group` is the group named by its `group`, `reached_from` lists the questions that jump to it.

Reply with ONE JSON object and nothing else, exactly in the requested shape. Do not skip items; give your best estimate with a low confidence when unsure."""


def _chat_user(state: Dict, task: str, items: List[str], assignments: Optional[Dict[str, List[str]]]) -> str:
    parts = [task, "", "SURVEY:", json.dumps(state, ensure_ascii=False, separators=(",", ":")), "",
             "ITEMS:", json.dumps([_item_spec(i) for i in items], ensure_ascii=False, separators=(",", ":")), ""]
    if assignments is None:
        parts += ['Reply with: {"survey": {"<item id>": <answer>, ...}} covering every item above.']
    else:
        parts += ["ITEMS TO ANSWER PER QUESTION (question ref -> item ids):",
                  json.dumps(assignments, separators=(",", ":")), "",
                  'Reply with: {"questions": {"<ref>": {"<item id>": <answer>, ...}, ...}} covering every pair above.']
    return "\n".join(parts)


def _chat_body(provider: str, model: str, user: str) -> Dict:
    if provider == "openai":
        return {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]}
    # Anthropic: no thinking / temperature / tool_choice (current models reject or ignore them).
    return {"model": model, "max_tokens": ANTHROPIC_MAX_TOKENS, "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user}]}


def _jev_spec(iid: str, instructions: str) -> Dict:
    return {"type": ITEMS[iid]["primitive"], "instructions": instructions, "criteria": _criteria(iid)}


def _chunks(xs: List, n: int) -> List[List]:
    return [xs[i:i + n] for i in range(0, len(xs), n)] if xs else []


def build_plan(survey: Any, provider: str, model: str) -> List[Dict]:
    """Every request the judge would send: [{scope, refs, answers, url, body}]. No keys, no network."""
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}; use one of {', '.join(PROVIDERS)}")
    s = normalise(survey)
    survey_items, per_q = applicable_items(s)
    state = survey_state(s)
    qs = [q for q in s["questions"] if per_q.get(q["ref"])]
    plan: List[Dict] = []

    if provider == "jev":
        base = (os.environ.get("TYPESAFE_BASE_URL") or JEV_BASE_URL).rstrip("/")
        url = base + "/v1/systemone"
        plan.append({"scope": "survey", "refs": [], "answers": len(survey_items), "url": url,
                     "body": {"state": state, "model": model,
                              "questions": {i: _jev_spec(i, ITEMS[i]["instructions"]) for i in survey_items}}})
        head = {k: s.get(k) for k in ("title", "kind", "audience")}
        head["purpose"] = _purpose(s)
        for batch in _chunks(qs, JEV_BATCH):
            questions: Dict[str, Dict] = {}
            for i, q in enumerate(batch):
                for iid in per_q[q["ref"]]:
                    questions[f"{iid}__{q['ref']}"] = _jev_spec(iid, rewrite_for_batch(ITEMS[iid]["instructions"], i))
            plan.append({"scope": "questions", "refs": [q["ref"] for q in batch], "answers": len(questions),
                         "url": url,
                         "body": {"state": {"survey": _compact(head),
                                            "questions": [_question_context(s, q) for q in batch]},
                                  "model": model, "questions": questions}})
        return plan

    url = OPENAI_URL if provider == "openai" else ANTHROPIC_URL
    plan.append({"scope": "survey", "refs": [], "answers": len(survey_items), "url": url,
                 "body": _chat_body(provider, model, _chat_user(state, TASK_SURVEY, survey_items, None))})
    size = len(qs) if len(qs) <= CHAT_ALL_UP_TO else CHAT_BATCH_LARGE
    for batch in _chunks(qs, max(size, 1)):
        assignments = {q["ref"]: per_q[q["ref"]] for q in batch}
        items = [i for i in QUESTION_ITEM_IDS if any(i in v for v in assignments.values())]
        plan.append({"scope": "questions", "refs": list(assignments), "url": url,
                     "answers": sum(len(v) for v in assignments.values()),
                     "body": _chat_body(provider, model, _chat_user(state, TASK_QUESTIONS, items, assignments))})
    return plan


# --- cost ----------------------------------------------------------------------------------------

def price_for(provider: str, model: str) -> Optional[Tuple[float, float]]:
    if model in PRICES:
        return PRICES[model]
    if provider == "jev" and model.startswith("jev"):
        return PRICES["jev-latest"]
    return None


def estimate(plan: List[Dict], provider: str, model: str) -> Dict[str, Any]:
    input_tokens = sum(round(len(json.dumps(r["body"])) / CHARS_PER_TOKEN) for r in plan)
    output_tokens = 0 if provider == "jev" else sum(r["answers"] for r in plan) * OUTPUT_TOKENS_PER_ANSWER
    price = price_for(provider, model)
    cost = None
    if price:
        cost = input_tokens * price[0] / 1e6 + output_tokens * price[1] / 1e6
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "price": price, "cost": cost,
            "requests": len(plan)}


def _usd(x: float) -> str:
    return f"${x:.4f}" if x < 1 else f"${x:.2f}"


def _per_m(x: float) -> str:
    text = f"{x:.3f}".rstrip("0")
    return f"${text if len(text.split('.')[1]) >= 2 else f'{x:.2f}'}/M"


def cost_lines(est: Dict[str, Any], provider: str, model: str) -> List[str]:
    if est["price"] is None:
        return [f"~{est['input_tokens']:,} input tokens; no price on file for {model!r} "
                f"(verify current pricing; --yes required)"]
    pin, pout = est["price"]
    line = f"~{est['input_tokens']:,} input tokens × {_per_m(pin)}"
    if est["output_tokens"]:
        line += f" + ~{est['output_tokens']:,} output tokens × {_per_m(pout)}"
    return [f"{line} = {_usd(est['cost'])} ({provider} {model}, {est['requests']} request(s); "
            f"estimate at {CHARS_PER_TOKEN} chars/token, verify current pricing)"]


# --- HTTP ----------------------------------------------------------------------------------------

def _headers(provider: str, api_key: str) -> Dict[str, str]:
    if provider == "anthropic":
        return {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"}
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _post(url: str, body: Dict, headers: Dict[str, str]) -> Dict:
    data = json.dumps(body).encode("utf-8")
    last = ""
    for attempt in range(ATTEMPTS):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
            try:
                return json.loads(raw)
            except ValueError:
                raise JudgeError("response was not JSON")
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            last = f"HTTP {e.code}" + (f": {detail}" if detail else "")
            if e.code not in RETRY_STATUS:
                raise JudgeError(last, fatal=e.code in (401, 403))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = f"network error: {getattr(e, 'reason', e)}"
        if attempt < ATTEMPTS - 1:
            time.sleep(BACKOFF * (2 ** attempt))
    raise JudgeError(f"{last} (gave up after {ATTEMPTS} attempts)")


def _extract_json(text: str) -> Dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise JudgeError("model reply contained no JSON object")
    try:
        out = json.loads(text[start:end + 1])
    except ValueError as e:
        raise JudgeError(f"model reply was not valid JSON ({e.msg})")
    if not isinstance(out, dict):
        raise JudgeError("model reply was not a JSON object")
    return out


def _chat_text(provider: str, resp: Dict, errors: List[str], scope: str) -> str:
    if provider == "openai":
        choice = _d((_l(resp.get("choices")) or [{}])[0])
        if choice.get("finish_reason") == "length":
            errors.append(f"{scope}: reply cut off (finish_reason=length); answers may be missing")
        return _d(choice.get("message")).get("content") or ""
    text = "".join(b.get("text", "") for b in _l(resp.get("content"))
                   if isinstance(b, dict) and b.get("type") == "text")
    stop = resp.get("stop_reason")
    if stop == "max_tokens":
        errors.append(f"{scope}: reply cut off (stop_reason=max_tokens); answers may be missing")
    elif stop == "refusal":
        errors.append(f"{scope}: the model declined to judge this survey (stop_reason=refusal)")
    return text


# --- answers -> contract -------------------------------------------------------------------------

def _clamp01(x: Any) -> Optional[float]:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or x != x:
        return None
    return round(min(1.0, max(0.0, float(x))), 4)


def _note(ans: Dict, raw: Dict) -> Dict:
    note = raw.get("note")
    if isinstance(note, str) and note.strip():
        ans["note"] = note.strip()[:NOTE_MAX]
    return ans


def from_chat(iid: str, raw: Any) -> Optional[Dict]:
    """A chat model's answer -> contract shape, clamped; None when it cannot be repaired."""
    if not isinstance(raw, dict):
        return None
    item = ITEMS[iid]
    prim = item["primitive"]
    if prim == "score":
        lvl = raw.get("level")
        if isinstance(lvl, bool) or not isinstance(lvl, (int, float)) or lvl != lvl:
            return None
        ans: Dict[str, Any] = {"level": int(min(item["levels"] - 1, max(0, round(lvl))))}
        c = _clamp01(raw.get("confidence"))
        if c is not None:
            ans["confidence"] = c
        return _note(ans, raw)
    if prim == "noul":
        p = _clamp01(raw.get("p"))
        return None if p is None else _note({"p": p}, raw)
    choice = raw.get("choice")
    if not isinstance(choice, str) or choice not in (item["criteria"] or {}):
        return None
    ans = {"choice": choice}
    c = _clamp01(raw.get("confidence"))
    if c is not None:
        ans["confidence"] = c
    return _note(ans, raw)


def from_jev(iid: str, raw: Any) -> Optional[Dict]:
    """Jev answer -> contract: noul -> p; score -> level = round(score) + confidence; choice -> choice + confidence."""
    if not isinstance(raw, dict):
        return None
    prim = ITEMS[iid]["primitive"]
    if prim == "noul":
        return from_chat(iid, {"p": raw.get("noul")})
    if prim == "score":
        return from_chat(iid, {"level": raw.get("score"), "confidence": raw.get("confidence")})
    return from_chat(iid, {"choice": raw.get("choice"), "confidence": raw.get("confidence")})


def _merge_survey(out: Dict, answers: Dict, conv) -> None:
    for iid, raw in _d(answers).items():
        if iid in ITEMS and ITEMS[iid]["scope"] == "survey":
            ans = conv(iid, raw)
            if ans:
                out["survey"][iid] = ans


def _merge_question(out: Dict, ref: str, iid: str, raw: Any, conv, refs: List[str]) -> None:
    if ref in refs and iid in ITEMS and ITEMS[iid]["scope"] == "question":
        ans = conv(iid, raw)
        if ans:
            out["questions"].setdefault(ref, {})[iid] = ans


def judge(survey: Any, provider: str, model: Optional[str], api_key: str) -> Dict[str, Any]:
    """Judge the survey through `provider`; returns a judgments dict per shared/scoring.md (plus `meta`).

    Never raises on API failures: failed requests leave their items out, set meta.partial and add to meta.errors.
    """
    model = model or DEFAULT_MODELS[provider]
    plan = build_plan(survey, provider, model)
    out: Dict[str, Any] = {"rubric_version": RUBRIC_VERSION, "survey": {}, "questions": {}}
    errors: List[str] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    headers = _headers(provider, api_key)
    for n, req in enumerate(plan):
        scope = req["scope"] if not req["refs"] else f"questions {req['refs'][0]}–{req['refs'][-1]}"
        try:
            resp = _post(req["url"], req["body"], headers)
        except JudgeError as e:
            errors.append(f"{scope}: {e}")
            if e.fatal:
                errors.append(f"stopped: authentication failed; {len(plan) - n - 1} request(s) not sent")
                break
            continue
        u = _d(resp.get("usage"))
        usage["input_tokens"] += int(u.get("input_tokens") or u.get("prompt_tokens") or 0)
        usage["output_tokens"] += int(u.get("output_tokens") or u.get("completion_tokens") or 0)
        if provider == "jev":
            answers = _d(resp.get("answers"))
            if req["scope"] == "survey":
                _merge_survey(out, answers, from_jev)
            else:
                for key, raw in answers.items():
                    iid, _, ref = key.partition("__")
                    _merge_question(out, ref, iid, raw, from_jev, req["refs"])
            continue
        try:
            parsed = _extract_json(_chat_text(provider, resp, errors, scope))
        except JudgeError as e:
            errors.append(f"{scope}: {e}")
            continue
        if req["scope"] == "survey":
            _merge_survey(out, parsed.get("survey", parsed), from_chat)
        else:
            for ref, answers in _d(parsed.get("questions")).items():
                for iid, raw in _d(answers).items():
                    _merge_question(out, ref, iid, raw, from_chat, req["refs"])
    out["meta"] = {"provider": provider, "model": model, "requests": len(plan), "partial": bool(errors),
                   "errors": errors, "usage": usage}
    return out


# --- CLI -----------------------------------------------------------------------------------------

USAGE = ("usage: survey_judge.py survey.json --provider jev|openai|anthropic [--model M] [--out judgments.json] "
         "[--dry-run [--show-requests]] [--yes] [--max-cost USD]")


def _parse_args(argv: List[str]) -> Dict[str, Any]:
    args: Dict[str, Any] = {"survey": None, "provider": None, "model": None, "out": None, "dry_run": False,
                            "show": False, "yes": False, "max_cost": COST_CAP}
    it = iter(argv)
    for a in it:
        if a in ("--provider", "--model", "--out", "--max-cost"):
            v = next(it, None)
            if v is None:
                raise ValueError(f"{a} needs a value")
            if a == "--max-cost":
                args["max_cost"] = float(v)
            else:
                args[a[2:].replace("-", "_")] = v
        elif a == "--dry-run":
            args["dry_run"] = True
        elif a == "--show-requests":
            args["show"] = True
        elif a == "--yes":
            args["yes"] = True
        elif a in ("-h", "--help"):
            raise ValueError("help")
        elif a.startswith("--"):
            raise ValueError(f"unknown option {a}")
        elif args["survey"] is None:
            args["survey"] = a
        else:
            raise ValueError(f"unexpected argument {a}")
    return args


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        args = _parse_args(argv)
    except ValueError as e:
        if str(e) != "help":
            print(f"error: {e}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 0 if str(e) == "help" else 2
    if not args["survey"]:
        print(USAGE, file=sys.stderr)
        return 2
    provider = args["provider"]
    if provider not in PROVIDERS:
        print("error: choose a judge explicitly with --provider jev|openai|anthropic (nothing is sent without it). "
              "No key? Your chat assistant can judge the rubric instead.", file=sys.stderr)
        return 2
    try:
        survey = load_survey(args["survey"])
    except Exception as e:  # noqa: BLE001 - report any unreadable input the same way
        print(f"error: cannot read survey: {e}", file=sys.stderr)
        return 2

    dotenv = read_dotenv(os.path.join(os.getcwd(), ".env"))
    if provider == "jev" and not os.environ.get("TYPESAFE_BASE_URL") and dotenv.get("TYPESAFE_BASE_URL"):
        os.environ["TYPESAFE_BASE_URL"] = dotenv["TYPESAFE_BASE_URL"]
    model = resolve_model(provider, args["model"], dotenv)
    plan = build_plan(survey, provider, model)
    est = estimate(plan, provider, model)

    if args["dry_run"]:
        print(f"Dry run: {provider} {model}, {len(plan)} request(s), nothing sent.")
        for n, r in enumerate(plan, 1):
            refs = f" for {r['refs'][0]}–{r['refs'][-1]} ({len(r['refs'])} questions)" if r["refs"] else ""
            print(f"  {n}. POST {r['url']}  {r['scope']}{refs}: {r['answers']} answers, "
                  f"~{round(len(json.dumps(r['body'])) / CHARS_PER_TOKEN):,} input tokens")
            if args["show"]:
                print(json.dumps(r["body"], indent=1, ensure_ascii=False))
        for line in cost_lines(est, provider, model):
            print(line)
        return 0

    for line in cost_lines(est, provider, model):
        print(line, file=sys.stderr)
    over = est["cost"] is None or est["cost"] > args["max_cost"]
    if over and not args["yes"]:
        why = "the price of this model is unknown" if est["cost"] is None else \
            f"the estimate exceeds the ${args['max_cost']:g} cap"
        print(f"refused: {why}. Re-run with --yes to confirm the spend (or --dry-run to inspect the plan).",
              file=sys.stderr)
        return 2

    key_name = KEY_ENV[provider]
    api_key = setting(key_name, dotenv)
    if not api_key:
        print(f"error: {key_name} is not set. Put it in your environment or in a .env file in this folder "
              f"(cp .env.example .env, then fill {key_name}=). No key? Your chat assistant can judge the rubric "
              f"instead; this script is optional.", file=sys.stderr)
        return 2

    result = judge(survey, provider, model, api_key)
    text = json.dumps(result, indent=1, ensure_ascii=False)
    if args["out"]:
        with open(args["out"], "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"wrote {args['out']}", file=sys.stderr)
    else:
        print(text)
    if result["meta"]["partial"]:
        print("partial judgments: " + "; ".join(result["meta"]["errors"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
