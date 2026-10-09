"""Golden examples (examples/*/): schema-valid surveys, lint expectations, and a drift guard that re-runs the
score calculator on the committed judgments and checks it reproduces the committed report.json exactly."""
import json
import pathlib

import pytest

import survey_lint
from survey_score_calc import calc, run_lint

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SCHEMA = json.loads((ROOT / "schemas" / "survey.schema.json").read_text(encoding="utf-8"))

GOOD = ["saas-churn", "event-feedback", "employee-engagement"]
BAD = "bad-survey"
ALL = GOOD + [BAD]
BAD_IDS = {"Q2_double_barreled", "Q3a_leading", "B3_demographics_placement", "S30_matrix_too_large",
           "S17_length_fatigue"}
FILES = ["brief.md", "survey.json", "judgments.json", "report.md", "report.json"]

JSON_TYPES = {"string": str, "boolean": bool, "object": dict, "array": list,
              "number": (int, float), "integer": int, "null": type(None)}


def _load(name, fname):
    return json.loads((EXAMPLES / name / fname).read_text(encoding="utf-8"))


def _type_ok(value, spec_type):
    if isinstance(spec_type, list):                       # e.g. ["string", "null"]
        return any(_type_ok(value, t) for t in spec_type)
    if spec_type in ("number", "integer") and isinstance(value, bool):
        return False
    return isinstance(value, JSON_TYPES[spec_type])


def _check_object(obj, spec, path, errors):
    """Tiny stdlib subset of JSON Schema: required keys, declared property types, enums, nested objects."""
    if not isinstance(obj, dict):
        errors.append(f"{path}: not an object")
        return
    for key in spec.get("required", []):
        if key not in obj:
            errors.append(f"{path}: missing required key {key!r}")
    for key, pspec in spec.get("properties", {}).items():
        if key not in obj or "type" not in pspec:
            continue
        val = obj[key]
        if not _type_ok(val, pspec["type"]):
            errors.append(f"{path}.{key}: expected {pspec['type']}")
            continue
        if "enum" in pspec and val not in pspec["enum"]:
            errors.append(f"{path}.{key}: {val!r} not in enum")
        if pspec["type"] == "object" and "properties" in pspec and isinstance(val, dict):
            _check_object(val, pspec, f"{path}.{key}", errors)


def validate(survey):
    errors = []
    _check_object(survey, SCHEMA, "$", errors)
    qspec = SCHEMA["definitions"]["question"]

    def walk(questions, path):
        for i, q in enumerate(questions or []):
            _check_object(q, qspec, f"{path}[{i}]", errors)
            if isinstance(q, dict) and isinstance(q.get("questions"), list):
                walk(q["questions"], f"{path}[{i}].questions")

    walk(survey.get("questions") if isinstance(survey, dict) else None, "$.questions")
    return errors


def test_examples_directory_has_every_example():
    for name in ALL:
        for fname in FILES:
            assert (EXAMPLES / name / fname).is_file(), f"missing examples/{name}/{fname}"
    assert (EXAMPLES / "README.md").is_file()


def test_validator_catches_errors():
    assert validate({"title": "t", "questions": [{"ref": "Q1", "type": "single_choice", "label": "x"}]}) == []
    assert validate({"questions": []})                                        # no title
    assert validate({"title": "t", "questions": [{"ref": "Q1", "type": "radio", "label": "x"}]})   # bad type
    assert validate({"title": "t", "kind": "poll", "questions": []})          # bad kind
    assert validate({"title": "t", "questions": [{"ref": "Q1", "type": "nps"}]})                  # no label


@pytest.mark.parametrize("name", ALL)
def test_survey_validates_against_schema(name):
    assert validate(_load(name, "survey.json")) == []


@pytest.mark.parametrize("name", GOOD)
def test_good_examples_lint_clean_of_blocker_and_high(name):
    findings = survey_lint.run(_load(name, "survey.json"))
    bad = [(f["id"], f["severity"]) for f in findings if f["severity"] in ("blocker", "high")]
    assert bad == []


def test_bad_survey_has_high_lint_findings():
    findings = survey_lint.run(_load(BAD, "survey.json"))
    assert any(f["severity"] == "high" for f in findings)


@pytest.mark.parametrize("name", ALL)
def test_calculator_reproduces_committed_report(name):
    survey, judgments = _load(name, "survey.json"), _load(name, "judgments.json")
    committed = _load(name, "report.json")
    report = calc(survey, judgments, run_lint(survey, judgments))
    assert (report["score"], report["grade"], report["verdict"]) == \
        (committed["score"], committed["grade"], committed["verdict"])
    assert report["meta"]["partial"] is False, report["meta"]["missing_items"]
    md = (EXAMPLES / name / "report.md").read_text(encoding="utf-8")
    assert f"{report['score']}/100" in md


@pytest.mark.parametrize("name", GOOD)
def test_good_examples_score_at_least_85(name):
    report = _load(name, "report.json")
    assert report["score"] >= 85
    assert report["verdict"] == "ready"


def test_bad_survey_scores_low_with_expected_findings():
    report = _load(BAD, "report.json")
    ids = {f["id"] for f in report["findings"]}
    assert report["score"] <= 60
    assert report["verdict"] in ("not_ready", "needs_work")
    assert BAD_IDS <= ids, BAD_IDS - ids
    assert len(ids) >= 8


@pytest.mark.parametrize("name", ALL)
def test_judgments_follow_contract(name):
    j = _load(name, "judgments.json")
    assert j["rubric_version"] == "bs-skills-1.0"

    def check(items, where):
        for iid, ans in items.items():
            if "level" in ans:
                assert isinstance(ans["level"], int) and not isinstance(ans["level"], bool), (where, iid)
            if "p" in ans:
                assert 0 <= ans["p"] <= 1, (where, iid)
            if "note" in ans:
                assert len(ans["note"]) <= 200, (where, iid)

    check(j["survey"], "survey")
    for iid, ans in j["survey"].items():
        if iid not in ("C5_gap_topic", "K_survey_kind", "X2_audience_kind"):
            assert ans.get("note"), f"survey-level {iid} has no note"
    for ref, items in j["questions"].items():
        check(items, ref)
