"""Tests for shared/scripts/survey_export.py (markdown / csv / text export, markdown import)."""
import csv
import io
import json
import pathlib
import subprocess
import sys

import pytest

from survey_common import TYPES, load_survey, normalise
from survey_export import from_markdown, to_csv, to_markdown, to_text

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPORT = ROOT / "shared" / "scripts" / "survey_export.py"
FIXTURES = ROOT / "tests" / "fixtures"

SURVEY_FIELDS = ("title", "description", "kind", "audience")
Q_FIELDS = ("ref", "type", "label", "description", "required", "options", "has_other", "has_none",
            "has_prefer_not_to_answer", "rows", "columns", "scale", "selection", "shown_when", "jumps", "group")
BOOL_FIELDS = {"required", "has_other", "has_none", "has_prefer_not_to_answer"}
LIST_FIELDS = {"options", "rows", "columns", "jumps"}


def _canon_q(q, field):
    v = q.get(field)
    if field in BOOL_FIELDS:
        return v is True
    if field in LIST_FIELDS:
        if field == "options" and q.get("type") == "yes_no" and v == ["Yes", "No"]:
            return []                                 # implicit Yes / No (written out by to_markdown)
        return v or []
    if field == "description":
        return v or ""
    if field in ("scale", "selection"):
        return v or None
    return v


def assert_round_trip(survey):
    back = from_markdown(to_markdown(survey))
    for f in SURVEY_FIELDS:
        assert back.get(f) == survey.get(f), f
    assert (back.get("settings") or {}).get("stated_minutes") == (survey.get("settings") or {}).get("stated_minutes")
    assert back.get("welcome") == survey.get("welcome")
    assert back.get("thank_you") == survey.get("thank_you")
    assert len(back["questions"]) == len(survey["questions"])
    for orig, got in zip(survey["questions"], back["questions"]):
        for f in Q_FIELDS:
            assert _canon_q(got, f) == _canon_q(orig, f), (orig["ref"], f, _canon_q(got, f), _canon_q(orig, f))
        assert not got.get("inferred"), "canonical markdown types are not guessed"
    return back


# One representative question per portable type.
ALL_TYPES_SURVEY = {
    "title": "Every type, once",
    "description": "A survey that uses all twenty portable types.",
    "kind": "research",
    "audience": "Testers",
    "settings": {"stated_minutes": 7},
    "welcome": {"title": "Hello", "description": "Line one.\nLine two.", "button": "Start"},
    "thank_you": {"title": "Thanks", "description": "We read every answer."},
    "questions": [
        {"ref": "Q1", "type": "single_choice", "label": "How often do you invoice?", "required": True,
         "description": "Count every invoice.", "options": ["Weekly", "Monthly"], "has_other": True,
         "has_none": True, "has_prefer_not_to_answer": True},
        {"ref": "Q2", "type": "multi_choice", "label": "Which do you use?", "options": ["A", "B", "C"],
         "selection": {"min": 1, "max": 2}, "shown_when": "Q1 is 'Weekly'",
         "jumps": [{"when": "Q2 contains 'A'", "to": "Q5"}, {"when": None, "to": "Q4"}]},
        {"ref": "Q3", "type": "dropdown", "label": "Which industry?", "options": ["Retail", "Tech"]},
        {"ref": "Q4", "type": "yes_no", "label": "Do you use Acme?", "required": True,
         "jumps": [{"when": "Q4 is 'No'", "to": "end"}]},
        {"ref": "Q5", "type": "short_text", "label": "Which tool do you use?"},
        {"ref": "Q6", "type": "long_text", "label": "Why?", "description": "Be honest."},
        {"ref": "Q7", "type": "number", "label": "How many invoices a month?", "scale": {"min": 0, "max": 1000}},
        {"ref": "Q8", "type": "rating", "label": "How satisfied are you?",
         "scale": {"min": 1, "max": 5, "labels": {"1": "Very unhappy", "5": "Very happy"}}},
        {"ref": "Q9", "type": "nps", "label": "How likely are you to recommend us?",
         "scale": {"min": 0, "max": 10, "labels": {"0": "Not at all likely", "10": "Extremely likely"}}},
        {"ref": "Q10", "type": "likert", "label": "Invoicing is easy.",
         "options": ["Disagree", "Neutral", "Agree"]},
        {"ref": "Q11", "type": "matrix", "label": "Rate each part.", "rows": ["Setup", "Billing"],
         "columns": ["Bad", "OK", "Good"], "required": True},
        {"ref": "Q12", "type": "ranking", "label": "Rank these.", "options": ["Price", "Speed", "Support"]},
        {"ref": "Q13", "type": "slider", "label": "How much time does it take?",
         "scale": {"min": 0, "max": 100}},
        {"ref": "Q14", "type": "date", "label": "When did you start?"},
        {"ref": "Q15", "type": "email", "label": "Your email?"},
        {"ref": "Q16", "type": "phone", "label": "Your phone?"},
        {"ref": "Q17", "type": "file", "label": "Upload a sample invoice."},
        {"ref": "Q18", "type": "statement", "label": "Next, a few questions about you.",
         "description": "All optional."},
        {"ref": "Q19", "type": "consent", "label": "Do you agree to the terms?", "options": ["I agree"],
         "required": True},
        {"ref": "Q20", "type": "group", "label": "About your team"},
        {"ref": "Q20.1", "type": "likert", "label": "Agree with each.", "rows": ["Fast", "Cheap"],
         "columns": ["No", "Yes"], "group": "Q20"},
    ],
}


def test_all_types_covered():
    assert {q["type"] for q in ALL_TYPES_SURVEY["questions"]} == set(TYPES)


def test_round_trip_every_type():
    assert_round_trip(ALL_TYPES_SURVEY)


@pytest.mark.parametrize("q", ALL_TYPES_SURVEY["questions"], ids=lambda q: q["type"] + "-" + q["ref"])
def test_round_trip_single_question(q):
    assert_round_trip({"title": "One", "questions": [q]})


def test_round_trip_acme_fixture():
    survey = json.loads((FIXTURES / "acme_feedback.json").read_text())
    back = assert_round_trip(survey)
    assert back["sponsor"] == survey["sponsor"] and back["purpose"] == survey["purpose"]
    assert back["settings"].get("anonymous") is True


def test_markdown_canonical_form():
    md = to_markdown(ALL_TYPES_SURVEY)
    lines = md.splitlines()
    assert lines[0] == "# Every type, once"
    assert lines[1] == "> A survey that uses all twenty portable types."
    assert lines[2] == "**Audience:** Testers · **Kind:** research · **Time:** ~7 min"
    assert "## Welcome" in lines and "## Questions" in lines and "## Thank you" in lines
    assert "### Q1. How often do you invoice?  `single_choice` (required)" in lines
    assert "- [ ] Weekly" in lines and "- [ ] Other (please specify)" in lines
    assert "> Shown when: Q1 is 'Weekly'" in lines
    assert "> Jump: if Q2 contains 'A' → Q5" in lines
    assert "> Jump: otherwise → Q4" in lines
    assert "| | Bad | OK | Good |" in lines
    assert "| Setup | | | |" in lines
    assert "> Scale: 0–10 · 0 = Not at all likely · 10 = Extremely likely" in lines
    assert "> Select: min 1 · max 2" in lines
    assert "> Group: Q20" in lines
    assert "- [ ] Yes" in lines and "- [ ] No" in lines


def test_markdown_accepts_table_separator_row():
    md = ("# T\n## Questions\n### Q1. Rate it.  `matrix`\n| | A | B |\n| --- | --- | --- |\n| R1 | | |\n")
    q = from_markdown(md)["questions"][0]
    assert q["rows"] == ["R1"] and q["columns"] == ["A", "B"]


def test_markdown_escapes_pipes_in_matrix():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "matrix", "label": "L", "rows": ["a|b"],
                                      "columns": ["x", "y|z"]}]}
    assert_round_trip(s)


# --- loose import ---------------------------------------------------------------------------

PASTED = """Customer check-in

1. Which plan are you on? (select one)
- Free
- Pro
- Business
2. Which features do you use? (select all that apply)
* Reports
* Reminders
3. How likely are you to recommend us to a friend? (0-10)
4. How would you rate support? (1-5)
5. Have you contacted support? (yes/no)
6. What is your company name? (short answer)
7. Anything else? (long answer)
8. When did you sign up? (date)
9. What is your email? (email)
10. Why?
11. Which device do you use most?
a) Phone
b) Laptop
12. What is your role?
"""


def test_loose_parse_types():
    s = from_markdown(PASTED)
    assert s["title"] == "Customer check-in"
    types = [q["type"] for q in s["questions"]]
    assert types == ["single_choice", "multi_choice", "nps", "rating", "yes_no", "short_text", "long_text",
                     "date", "email", "long_text", "single_choice", "short_text"]
    assert all(q.get("inferred") is True for q in s["questions"])
    assert [q["ref"] for q in s["questions"]] == [f"Q{i}" for i in range(1, 13)]
    q1 = s["questions"][0]
    assert q1["label"] == "Which plan are you on?"
    assert q1["options"] == ["Free", "Pro", "Business"]
    assert s["questions"][1]["options"] == ["Reports", "Reminders"]
    assert s["questions"][10]["options"] == ["Phone", "Laptop"]
    assert s["questions"][3]["scale"]["min"] == 1 and s["questions"][3]["scale"]["max"] == 5
    assert s["questions"][2]["scale"]["min"] == 0 and s["questions"][2]["scale"]["max"] == 10


def test_loose_parse_other_hints_and_markers():
    s = from_markdown("# My survey\nQ1: Pick a colour (check all)\n- Red\n- Blue\n"
                      "Q2: Would you recommend us to a colleague?\n"
                      "- Do you like it?\n- [ ] Yes\n- [ ] No\n"
                      "4. Please describe your workflow\n5. Your thoughts (open)\n")
    assert s["title"] == "My survey"
    qs = s["questions"]
    assert [q["type"] for q in qs] == ["multi_choice", "nps", "yes_no", "long_text", "long_text"]
    assert qs[0]["label"] == "Pick a colour"
    assert qs[2]["label"] == "Do you like it?"


def test_loose_parse_nps_en_dash_and_choose_one():
    s = from_markdown("1. On a scale of 0–10, how likely are you to recommend us?\n"
                      "2. Your plan (choose one)\n- A\n- B\n")
    assert [q["type"] for q in s["questions"]] == ["nps", "single_choice"]


def test_loose_parse_reads_text_export():
    back = from_markdown(to_text(ALL_TYPES_SURVEY))
    assert back["title"] == "Every type, once"
    labels = [q["label"] for q in back["questions"]]
    assert "How often do you invoice?" in labels
    by_label = {q["label"]: q for q in back["questions"]}
    assert by_label["Which do you use?"]["type"] == "multi_choice"
    assert by_label["How likely are you to recommend us?"]["type"] == "nps"
    assert by_label["Rate each part."]["rows"] == ["Setup", "Billing"]
    assert by_label["Rate each part."]["columns"] == ["Bad", "OK", "Good"]


# --- csv / text -----------------------------------------------------------------------------

def test_csv_columns_and_cells():
    out = to_csv(ALL_TYPES_SURVEY)
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[0] == ["ref", "type", "label", "required", "options", "rows", "columns", "shown_when", "jumps"]
    assert len(rows) == 1 + len(ALL_TYPES_SURVEY["questions"])
    by_ref = {r[0]: r for r in rows[1:]}
    assert by_ref["Q1"][1] == "single_choice" and by_ref["Q1"][3] == "true"
    assert by_ref["Q1"][4] == "Weekly|Monthly"
    assert by_ref["Q11"][5] == "Setup|Billing" and by_ref["Q11"][6] == "Bad|OK|Good"
    assert by_ref["Q2"][7] == "Q1 is 'Weekly'"
    assert by_ref["Q2"][8] == "if Q2 contains 'A' → Q5; otherwise → Q4"
    assert by_ref["Q5"][3] == "false"


def test_csv_quotes_commas():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "short_text", "label": "Name, please"}]}
    rows = list(csv.reader(io.StringIO(to_csv(s))))
    assert rows[1][2] == "Name, please"


def test_text_export():
    txt = to_text(ALL_TYPES_SURVEY)
    lines = txt.splitlines()
    assert lines[0] == "Every type, once"
    assert "A survey that uses all twenty portable types." in txt
    assert "Line one." in txt and "We read every answer." in txt
    assert "1. How often do you invoice? (select one) (required)" in lines
    assert "   - Weekly" in lines and "   - Other (please specify)" in lines
    for hint in ("(select all that apply)", "(0–10)", "(1–5)", "(short answer)", "(long answer)", "(date)",
                 "(email)", "(yes/no)", "(rank the items)", "(rate each row)"):
        assert hint in txt, hint
    assert "Show only if Q1 is 'Weekly'" in txt
    assert "If Q4 is 'No' go to the end" in txt
    assert "`" not in txt and "###" not in txt
    for word in ("multiplechoice", "bType", "BlockSurvey"):
        assert word not in txt


def test_text_numbers_skip_statements_and_map_refs():
    s = {"title": "T", "questions": [
        {"ref": "Q1", "type": "statement", "label": "Intro"},
        {"ref": "Q2", "type": "yes_no", "label": "Use it?", "jumps": [{"when": "Q2 is 'No'", "to": "Q4"}]},
        {"ref": "Q3", "type": "short_text", "label": "Which?"},
        {"ref": "Q4", "type": "long_text", "label": "Why?", "shown_when": "Q2 is 'Yes'"}]}
    lines = to_text(s).splitlines()
    assert "1. Use it? (yes/no)" in lines
    assert "3. Why? (long answer)" in lines
    assert "   If Q1 is 'No' go to Q3" in lines
    assert "   Show only if Q1 is 'Yes'" in lines


# --- load_survey wiring, follows_unless -----------------------------------------------------

def test_load_survey_markdown_path(tmp_path):
    p = tmp_path / "s.md"
    p.write_text(to_markdown(ALL_TYPES_SURVEY), encoding="utf-8")
    s = load_survey(str(p))
    assert s["title"] == "Every type, once" and len(s["questions"]) == 21
    assert load_survey(PASTED)["questions"][0]["type"] == "single_choice"


def test_follows_unless_screener_exit():
    s = normalise({"title": "T", "questions": [
        {"ref": "Q1", "type": "yes_no", "label": "Use it?", "jumps": [{"when": "Q1 is 'No'", "to": "end"}]},
        {"ref": "Q2", "type": "short_text", "label": "Which?"},
        {"ref": "Q3", "type": "short_text", "label": "Else?",
         "jumps": [{"when": "Q3 is empty", "to": "Q4"}, {"when": None, "to": "Q5"}]},
        {"ref": "Q4", "type": "short_text", "label": "x"},
        {"ref": "Q5", "type": "short_text", "label": "y"}]})
    qs = {q["ref"]: q for q in s["questions"]}
    assert qs["Q1"]["follows_unless"] == []
    assert qs["Q2"]["follows_unless"] == [{"from": "Q1", "when": "Q1 is 'No'"}]
    assert qs["Q3"]["follows_unless"] == []
    assert qs["Q4"]["follows_unless"] == []          # the only conditional jump targets Q4 itself
    assert qs["Q5"]["follows_unless"] == []


# --- null safety ----------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [None, 3, "", [], {}, {"questions": None}, {"title": 5, "questions": [None, 7]},
                                 {"title": "T", "questions": [{"type": None, "label": None, "options": "x",
                                                               "jumps": [None, {"to": None}], "scale": 5,
                                                               "welcome": 3}]},
                                 {"title": "T", "welcome": "hi", "settings": [], "questions": [
                                     {"ref": "Q1", "type": "matrix", "label": "L", "rows": None,
                                      "columns": [None, 1], "selection": "x", "shown_when": 4}]}])
def test_null_safety(bad):
    for fn in (to_markdown, to_csv, to_text):
        assert isinstance(fn(bad), str)
    s = from_markdown(bad)
    assert isinstance(s, dict) and isinstance(s.get("questions"), list)


def test_from_markdown_of_markdown_never_crashes():
    for bad in [None, 3, {"questions": None}]:
        assert isinstance(from_markdown(to_markdown(bad)), dict)
    junk = "### \n### Q1.  ``\n> Jump: \n> Scale: x\n| |\n- [ ]\n## Welcome\n## Thank you\n[]"
    assert isinstance(from_markdown(junk), dict)


# --- CLI ------------------------------------------------------------------------------------

def run_cli(*args):
    return subprocess.run([sys.executable, str(EXPORT), *map(str, args)], capture_output=True, text=True)


@pytest.mark.parametrize("fmt", ["md", "csv", "txt", "json"])
def test_cli_formats(fmt, tmp_path):
    src = tmp_path / "s.json"
    src.write_text(json.dumps(ALL_TYPES_SURVEY), encoding="utf-8")
    r = run_cli(src, "--format", fmt)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip()
    if fmt == "json":
        assert json.loads(r.stdout)["title"] == "Every type, once"


def test_cli_markdown_to_json_and_out(tmp_path):
    md = tmp_path / "s.md"
    md.write_text(to_markdown(ALL_TYPES_SURVEY), encoding="utf-8")
    out = tmp_path / "out.json"
    r = run_cli(md, "--format", "json", "--out", out)
    assert r.returncode == 0, r.stderr
    assert json.loads(out.read_text())["questions"][10]["rows"] == ["Setup", "Billing"]


def test_cli_invalid_input(tmp_path):
    assert run_cli(tmp_path / "missing.json", "--format", "md").returncode == 2
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2]", encoding="utf-8")
    assert run_cli(bad, "--format", "md").returncode == 2
    assert run_cli(tmp_path / "x.json", "--format", "pdf").returncode == 2
