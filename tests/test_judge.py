"""Tests for shared/scripts/survey_judge.py (optional API judge). No network: urllib.request.urlopen is faked."""
import copy
import io
import json
import pathlib
import urllib.error
import urllib.request

import pytest

import survey_judge as sj
from survey_score_calc import ITEMS, calc

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SURVEY = json.loads((FIXTURES / "acme_feedback.json").read_text())


# --- fakes ------------------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode() if not isinstance(payload, bytes) else payload

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code, body=b"{}"):
    return urllib.error.HTTPError("https://example.test", code, "error", {}, io.BytesIO(body))


def jev_answer(spec):
    if spec["type"] == "score":
        top = len(spec["criteria"]) - 1
        return {"type": "score", "score": top - 0.4, "confidence": 0.8}       # rounds to `top`
    if spec["type"] == "noul":
        return {"type": "noul", "noul": 0.2}
    return {"type": "choice", "choice": next(iter(spec["criteria"])), "confidence": 0.9}


def fake_jev(calls):
    def urlopen(req, timeout=None):
        calls.append(req)
        body = json.loads(req.data)
        return FakeResponse({"model": "jev-test", "answers": {k: jev_answer(v) for k, v in body["questions"].items()},
                             "usage": {"input_tokens": 100, "output_tokens": 5}})
    return urlopen


CHAT_SURVEY = {"survey": {"A1_title_specific": {"level": 7, "confidence": 1.4, "note": "x" * 300},
                          "A5_privacy_stated": {"p": 1.3},
                          "K_survey_kind": {"choice": "feedback", "confidence": 0.9},
                          "C5_gap_topic": {"choice": "not-a-topic", "confidence": 0.9},
                          "Z9_unknown": {"p": 0.5}}}
CHAT_QUESTIONS = {"questions": {"Q1": {"Q1_clarity": {"level": 2.6, "confidence": 0.9},
                                       "Q2_double_barreled": {"p": -0.1},
                                       "R_role": {"choice": "question", "confidence": 0.95}},
                                "Q99": {"Q1_clarity": {"level": 3}}}}


def chat_reply(req):
    body = json.loads(req.data)
    text = body["messages"][-1]["content"]
    return CHAT_SURVEY if sj.TASK_SURVEY in text else CHAT_QUESTIONS


def fake_openai(calls, content=None):
    def urlopen(req, timeout=None):
        calls.append(req)
        msg = content if content is not None else json.dumps(chat_reply(req))
        return FakeResponse({"choices": [{"message": {"content": msg}, "finish_reason": "stop"}],
                             "usage": {"prompt_tokens": 1000, "completion_tokens": 100}})
    return urlopen


def fake_anthropic(calls, stop_reason="end_turn"):
    def urlopen(req, timeout=None):
        calls.append(req)
        text = json.dumps(chat_reply(req))
        return FakeResponse({"content": [{"type": "text", "text": "Here you go:\n" + text[:10]},
                                         {"type": "text", "text": text[10:]}],
                             "stop_reason": stop_reason, "usage": {"input_tokens": 1000, "output_tokens": 100}})
    return urlopen


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr(sj.time, "sleep", lambda s: slept.append(s))
    return slept


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for k in ("TYPESAFE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TYPESAFE_MODEL", "OPENAI_MODEL",
              "ANTHROPIC_MODEL", "TYPESAFE_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def assert_contract(j):
    assert j["rubric_version"] == "bs-skills-1.0"
    assert isinstance(j["survey"], dict) and isinstance(j["questions"], dict)
    assert isinstance(j["meta"]["partial"], bool) and isinstance(j["meta"]["errors"], list)

    def check(iid, ans):
        item = ITEMS[iid]
        if item["primitive"] == "score":
            assert isinstance(ans["level"], int) and not isinstance(ans["level"], bool)
            assert 0 <= ans["level"] <= item["levels"] - 1
        elif item["primitive"] == "noul":
            assert 0.0 <= ans["p"] <= 1.0
        else:
            assert isinstance(ans["choice"], str) and ans["choice"] in item["criteria"]
        if "confidence" in ans:
            assert 0.0 <= ans["confidence"] <= 1.0
        if "note" in ans:
            assert len(ans["note"]) <= 200

    for iid, ans in j["survey"].items():
        assert ITEMS[iid]["scope"] == "survey"
        check(iid, ans)
    for ref, answers in j["questions"].items():
        for iid, ans in answers.items():
            assert ITEMS[iid]["scope"] == "question"
            check(iid, ans)


# --- planning ----------------------------------------------------------------------------------

def test_jev_plan_batches_six_questions_and_rewrites_paths():
    survey = copy.deepcopy(SURVEY)
    extra = copy.deepcopy(survey["questions"][-1])
    for n in range(9, 14):                                    # 13 questions -> 3 question batches
        q = copy.deepcopy(extra)
        q["ref"] = f"Q{n}"
        survey["questions"].append(q)
    plan = sj.build_plan(survey, "jev", "jev-latest")
    assert plan[0]["scope"] == "survey"
    q_reqs = [r for r in plan if r["scope"] == "questions"]
    assert [len(r["refs"]) for r in q_reqs] == [6, 6, 1]
    body = q_reqs[0]["body"]
    assert body["model"] == "jev-latest"
    assert len(body["state"]["questions"]) == 6
    assert body["state"]["survey"]["title"] == survey["title"]
    key = "Q1_clarity__Q2"
    assert key in body["questions"]
    instr = body["questions"][key]["instructions"]
    assert "`questions[1].label`" in instr and "`question." not in instr
    assert body["questions"]["Q2_double_barreled__Q1"]["type"] == "noul"
    assert body["state"]["questions"][1]["previous_question"]["ref"] == "Q1"


def test_chat_plan_is_one_survey_request_and_one_question_request():
    for provider in ("openai", "anthropic"):
        plan = sj.build_plan(SURVEY, provider, sj.DEFAULT_MODELS[provider])
        assert [r["scope"] for r in plan] == ["survey", "questions"]
        assert plan[1]["refs"] == [q["ref"] for q in SURVEY["questions"]]
    anth = sj.build_plan(SURVEY, "anthropic", "claude-haiku-5-5")[0]["body"]
    assert anth["max_tokens"] == 16000
    assert not {"thinking", "temperature", "tool_choice"} & set(anth)
    oai = sj.build_plan(SURVEY, "openai", "gpt-4o-mini")[0]["body"]
    assert oai["response_format"] == {"type": "json_object"} and oai["temperature"] == 0


def test_estimate_uses_price_table():
    plan = sj.build_plan(SURVEY, "jev", "jev-latest")
    est = sj.estimate(plan, "jev", "jev-latest")
    chars = sum(len(json.dumps(r["body"])) for r in plan)
    assert est["input_tokens"] == pytest.approx(chars / 4, abs=len(plan))
    assert est["cost"] == pytest.approx(est["input_tokens"] * 0.042 / 1e6)


# --- judge() per provider ----------------------------------------------------------------------

def test_jev_judge_contract_and_full_coverage(monkeypatch):
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_jev(calls))
    j = sj.judge(SURVEY, "jev", None, "sk-test")
    assert len(calls) == 3                                     # 1 survey + 8 questions in batches of 6
    req = calls[0]
    assert req.full_url == "https://api.typesafe.ai/v1/systemone"
    assert req.get_header("Authorization") == "Bearer sk-test"
    assert_contract(j)
    assert j["meta"]["partial"] is False and j["meta"]["provider"] == "jev"
    assert j["survey"]["A1_title_specific"] == {"level": 2, "confidence": 0.8}
    assert j["survey"]["A5_privacy_stated"] == {"p": 0.2}
    assert set(j["questions"]) == {q["ref"] for q in SURVEY["questions"]}
    report = calc(SURVEY, j, [])
    assert report["meta"]["missing_items"] == []               # every applicable item was asked


def test_openai_judge_clamps_and_drops_invalid(monkeypatch):
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_openai(calls))
    j = sj.judge(SURVEY, "openai", None, "sk-test")
    assert len(calls) == 2
    assert calls[0].full_url == "https://api.openai.com/v1/chat/completions"
    assert calls[0].get_header("Authorization") == "Bearer sk-test"
    assert json.loads(calls[0].data)["model"] == "gpt-4o-mini"
    assert_contract(j)
    assert j["survey"]["A1_title_specific"]["level"] == 2      # 7 clamped to levels-1
    assert j["survey"]["A1_title_specific"]["confidence"] == 1.0
    assert j["survey"]["A5_privacy_stated"] == {"p": 1.0}
    assert "C5_gap_topic" not in j["survey"] and "Z9_unknown" not in j["survey"]
    assert j["questions"]["Q1"]["Q1_clarity"]["level"] == 3
    assert j["questions"]["Q1"]["Q2_double_barreled"] == {"p": 0.0}
    assert "Q99" not in j["questions"]


def test_anthropic_judge_headers_and_text_blocks(monkeypatch):
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_anthropic(calls))
    j = sj.judge(SURVEY, "anthropic", None, "sk-ant-test")
    assert calls[0].full_url == "https://api.anthropic.com/v1/messages"
    assert calls[0].get_header("X-api-key") == "sk-ant-test"
    assert calls[0].get_header("Anthropic-version") == "2023-06-01"
    body = json.loads(calls[0].data)
    assert body["model"] == "claude-haiku-5-5" and body["max_tokens"] == 16000
    assert_contract(j)
    assert j["meta"]["partial"] is False
    assert j["survey"]["K_survey_kind"] == {"choice": "feedback", "confidence": 0.9}


def test_anthropic_max_tokens_is_partial(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", fake_anthropic([], stop_reason="max_tokens"))
    j = sj.judge(SURVEY, "anthropic", None, "k")
    assert j["meta"]["partial"] is True
    assert any("max_tokens" in e for e in j["meta"]["errors"])


# --- failure handling --------------------------------------------------------------------------

def test_429_then_200_retries_once(monkeypatch, no_sleep):
    calls = []
    ok = fake_jev(calls)
    state = {"n": 0}

    def urlopen(req, timeout=None):
        state["n"] += 1
        if state["n"] == 1:
            raise http_error(429)
        return ok(req, timeout)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    j = sj.judge(SURVEY, "jev", None, "k")
    assert state["n"] == 4 and len(no_sleep) == 1
    assert j["meta"]["partial"] is False


def test_persistent_503_gives_up_after_three_attempts(monkeypatch, no_sleep):
    n = {"calls": 0}

    def urlopen(req, timeout=None):
        n["calls"] += 1
        raise http_error(503)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    j = sj.judge(SURVEY, "openai", None, "k")
    assert n["calls"] == 6                                     # 2 requests x 3 attempts
    assert no_sleep == [1, 2, 1, 2]
    assert j["meta"]["partial"] is True and len(j["meta"]["errors"]) == 2
    assert_contract(j)


def test_malformed_chat_json_is_partial(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", fake_openai([], content="Sorry, I can't produce JSON {oops"))
    j = sj.judge(SURVEY, "openai", None, "k")
    assert j["meta"]["partial"] is True
    assert j["survey"] == {} and j["questions"] == {}
    assert_contract(j)


def test_auth_error_stops_and_never_leaks_key(monkeypatch):
    n = {"calls": 0}

    def urlopen(req, timeout=None):
        n["calls"] += 1
        raise http_error(401, b'{"error":"bad key"}')

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    j = sj.judge(SURVEY, "jev", None, "sk-secret-123")
    assert n["calls"] == 1
    assert j["meta"]["partial"] is True
    assert "sk-secret-123" not in json.dumps(j)


# --- CLI ----------------------------------------------------------------------------------------

def write_survey(tmp_path, survey=SURVEY):
    p = tmp_path / "survey.json"
    p.write_text(json.dumps(survey))
    return str(p)


def forbid_network(monkeypatch):
    def urlopen(*a, **k):
        raise AssertionError("network call made")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)


@pytest.mark.parametrize("provider,price", [("jev", "$0.042/M"), ("openai", "$0.15/M"),
                                            ("anthropic", "$0.10/M")])
def test_dry_run_prints_cost_and_makes_no_call(monkeypatch, clean_env, capsys, provider, price):
    forbid_network(monkeypatch)
    code = sj.main([write_survey(clean_env), "--provider", provider, "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "input tokens" in out and price in out and "verify current pricing" in out


def test_no_provider_is_usage_error(monkeypatch, clean_env, capsys):
    forbid_network(monkeypatch)
    assert sj.main([write_survey(clean_env)]) == 2
    assert "--provider" in capsys.readouterr().err


def test_missing_key_exits_2_with_clear_message(monkeypatch, clean_env, capsys):
    forbid_network(monkeypatch)
    assert sj.main([write_survey(clean_env), "--provider", "openai"]) == 2
    err = capsys.readouterr().err
    assert "OPENAI_API_KEY" in err and ".env" in err


def test_key_from_dotenv_and_output_file(monkeypatch, clean_env, capsys):
    (clean_env / ".env").write_text('# comment\nexport TYPESAFE_API_KEY="sk-dotenv"\nTYPESAFE_MODEL=\n')
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_jev(calls))
    out = clean_env / "judgments.json"
    code = sj.main([write_survey(clean_env), "--provider", "jev", "--out", str(out)])
    assert code == 0
    assert calls[0].get_header("Authorization") == "Bearer sk-dotenv"
    assert json.loads(calls[0].data)["model"] == "jev-latest"
    j = json.loads(out.read_text())
    assert_contract(j)
    assert "sk-dotenv" not in capsys.readouterr().err


def test_price_cap_refuses_without_yes(monkeypatch, clean_env, capsys):
    forbid_network(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    path = write_survey(clean_env)
    code = sj.main([path, "--provider", "anthropic", "--model", "claude-opus-5-5", "--max-cost", "0.001"])
    assert code == 2
    assert "--yes" in capsys.readouterr().err
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_anthropic(calls))
    code = sj.main([path, "--provider", "anthropic", "--model", "claude-opus-5-5", "--max-cost", "0.001",
                    "--yes"])
    assert code == 0 and len(calls) == 2


def test_default_price_cap_is_one_dollar():
    assert sj.COST_CAP == 1.0


def test_unknown_model_price_needs_yes(monkeypatch, clean_env, capsys):
    forbid_network(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert sj.main([write_survey(clean_env), "--provider", "openai", "--model", "some-new-model"]) == 2
    assert "--yes" in capsys.readouterr().err
