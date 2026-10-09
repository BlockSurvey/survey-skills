"""Tests for shared/scripts/survey_common.py and survey_lint.py (static checks, bs-skills-1.0)."""
import json
import pathlib
import subprocess
import sys

import pytest

from survey_common import load_survey, normalise
from survey_lint import numeric_range_issues, parse_range, run

ROOT = pathlib.Path(__file__).resolve().parents[1]
LINT = ROOT / "shared" / "scripts" / "survey_lint.py"
FIXTURES = ROOT / "tests" / "fixtures"


def q(ref, type="single_choice", label="Q?", options=None, **kw):
    return {"ref": ref, "type": type, "label": label, "options": options or ["A", "B"], "required": True, **kw}


def ids(s):
    return {f["id"] for f in run(s)}


def find(s, check_id):
    return [f for f in run(s) if f["id"] == check_id]


def one(s, check_id):
    hits = find(s, check_id)
    assert hits, f"{check_id} not raised"
    return hits[0]


def many(n, type="single_choice", **kw):
    """n distinct questions of one type."""
    return [q(f"Q{i + 1}", type=type, label=f"Question number {i + 1}?", **kw) for i in range(n)]


def mixed(n, required=True):
    """n distinct questions that never form a monotony run (alternate single/multi choice)."""
    types = ["single_choice", "dropdown"]
    return [q(f"Q{i + 1}", type=types[i % 2], label=f"Question number {i + 1}?", required=required)
            for i in range(n)]


# --- brief tests (verbatim) --------------------------------------------------------------

def test_no_title_is_blocker():
    f = [x for x in run({"title": "", "questions": [q("Q1")]}) if x["id"] == "S01_no_title"][0]
    assert f["severity"] == "blocker"


def test_numeric_range_gap():
    s = {"title": "T", "questions": [q("Q1", options=["Under 25", "26-35", "36-45", "Over 45"])]}
    assert "S12_numeric_range_gap" in ids(s)


def test_currency_suffix_ranges_touching_no_gap():
    s = {"title": "T", "questions": [q("Q1", options=["£25-40k", "£40-60k", "£60-80k"])]}
    assert any("both contain 40" in f["roast"] for f in run(s) if f["id"] == "S12_numeric_range_gap")


def test_decimal_comma_not_a_range():
    s = {"title": "T", "questions": [q("Q1", options=["0-0,5", "0,5-1", "1-2"])]}
    assert "S12_numeric_range_gap" not in ids(s)


def test_select_multiple_on_single_choice():
    s = {"title": "T", "questions": [q("Q1", label="Select all that apply")]}
    assert "S13_selection_hint_type_mismatch" in ids(s)


def test_unreachable_with_unknown_target():
    s = {"title": "T", "questions": [q("Q1", jumps=[{"when": None, "to": "Q99"}]), q("Q2"), q("Q3")]}
    f = [x for x in run(s) if x["id"] == "S28_unreachable_question"]
    assert f and set(f[0]["evidence"]["refs"]) == {"Q2", "Q3"}


def test_statements_only_is_blocker():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "statement", "label": "Hi"}]}
    assert "S02_no_questions" in ids(s)
    f = one(s, "S02_no_questions")
    assert f["severity"] == "blocker" and 'kind: "information"' in f["fix"]


def test_statements_only_information_kind_is_medium():
    s = {"title": "T", "kind": "information", "questions": [{"ref": "Q1", "type": "statement", "label": "Hi"}]}
    f = one(s, "S02_no_questions")
    assert f["severity"] == "medium"
    assert f["roast"] == "Nothing here asks for an answer, so no responses will be collected."


def test_matrix_too_large():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "matrix", "label": "Rate", "rows": list("abcdefghi"),
                                      "columns": list("123456")}]}
    assert "S30_matrix_too_large" in ids(s)


def test_null_safety():
    run({"title": None, "questions": [None, 1, "x", {}, {"ref": "Q1", "type": None, "label": None, "options": None,
                                                        "jumps": [None, {}]}]})


# --- numeric ranges (port of static_checks tests) -----------------------------------------

def test_numeric_range_issue_strings():
    assert numeric_range_issues(["Under 25", "26-35", "36-45", "46-60", "Over 60"]) == \
        ["'Under 25' then '26-35' — where does 25 go?"]
    assert numeric_range_issues(["£25-40k", "£40-60k", "£60-80k"]) == \
        ["'£25-40k' and '£40-60k' both contain 40000", "'£40-60k' and '£60-80k' both contain 60000"]
    assert numeric_range_issues(["18–24", "25–34", "35–44", "45+"]) == []
    assert numeric_range_issues(["Under 18", "18-24", "25-34", "35+"]) == []
    assert numeric_range_issues(["Daily", "Weekly", "Monthly"]) == []
    assert numeric_range_issues(["Under 25", "Other"]) == []
    assert len(numeric_range_issues(["18-25", "25-35", "35+"])) == 2
    assert numeric_range_issues(["1-10", "20-30", "31-40"]) == ["'1-10' then '20-30' — where does 11–19 go?"]


def test_parse_range_forms():
    assert parse_range("Under 25") == (None, 25, True, False)
    assert parse_range("26-35") == (26, 35, True, True)
    assert parse_range("Over 60") == (60, None, False, True)
    assert parse_range("65+") == (65, None, True, True)
    assert parse_range("10 or less") == (None, 10, True, True)
    assert parse_range("up to 5") == (None, 5, True, True)
    assert parse_range("50 or more") == (50, None, True, True)
    assert parse_range("1,000-2,000") == (1000, 2000, True, True)
    assert parse_range("0-0,5") is None
    assert parse_range("Weekly") is None


def test_s12_finding_text():
    s = {"title": "T", "questions": [q("Q1", options=["Under 25", "26-35", "36-45", "Over 45"])]}
    f = one(s, "S12_numeric_range_gap")
    assert f["severity"] == "medium" and f["category"] == "questions"
    assert f["roast"] == "Q1: 'Under 25' then '26-35' — where does 25 go?"
    assert f["fix"].startswith("Rewrite Q1's ranges")
    assert f["question_ref"] == "Q1" and f["scope"] == "question" and f["evidence"]["kind"] == "static"


# --- finding shape -----------------------------------------------------------------------

def test_finding_shape():
    for f in run({"title": "", "questions": [q("Q1", label="")]}):
        for key in ("id", "severity", "category", "scope", "question_ref", "question_label", "roast", "fix",
                    "evidence"):
            assert key in f
        assert f["evidence"]["kind"] == "static"
        assert "{" not in f["roast"] and "{" not in f["fix"]


# --- shipped checks ------------------------------------------------------------------------

def test_s02_empty_is_blocker():
    f = one({"title": "T", "kind": "information", "questions": []}, "S02_no_questions")
    assert f["severity"] == "blocker" and f["roast"] == "There is nothing in this survey yet."


def test_s03_label_empty():
    f = one({"title": "T", "questions": [q("Q1", label="  ")]}, "S03_label_empty")
    assert f["severity"] == "blocker" and f["question_ref"] == "Q1"


def test_s03_html_only_label_is_empty():
    assert "S03_label_empty" in ids({"title": "T", "questions": [q("Q1", label="<p>&nbsp;</p>")]})


def test_s04_options_too_few():
    f = one({"title": "T", "questions": [q("Q1", options=["Only", ""])]}, "S04_options_too_few")
    assert f["severity"] == "blocker" and "1 option(s)" in f["roast"]
    # has_other counts as an option
    assert "S04_options_too_few" not in ids({"title": "T", "questions": [q("Q1", options=["Only"], has_other=True)]})
    # yes_no has implicit options
    assert "S04_options_too_few" not in ids({"title": "T", "questions": [{"ref": "Q1", "type": "yes_no",
                                                                          "label": "Do you?"}]})


def test_s04_selection_min_impossible():
    s = {"title": "T", "questions": [q("Q1", type="multi_choice", options=["A", "B", "C"], selection={"min": 4})]}
    f = one(s, "S04_options_too_few")
    assert f["severity"] == "blocker" and "at least 4 picks from 3 options" in f["roast"]


def test_s05_matrix_empty():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "matrix", "label": "Rate", "rows": ["a"], "columns": []}]}
    assert one(s, "S05_matrix_empty")["severity"] == "blocker"


def test_s06_group_empty_and_s44_single_child():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "group", "label": "Empty"}, q("Q2")]}
    assert one(s, "S06_group_empty")["severity"] == "low"
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "group", "label": "Solo"},
                                     q("Q1.1", group="Q1"), q("Q2", label="Other?")]}
    assert one(s, "S44_group_single_child")["severity"] == "low"
    assert "S06_group_empty" not in ids(s)


def test_group_children_by_label():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "group", "label": "About you"},
                                     q("Q1.1", group="About you", label="A?"),
                                     q("Q1.2", group="About you", label="B?")]}
    found = ids(s)
    assert "S06_group_empty" not in found and "S44_group_single_child" not in found


def test_s07_s08_s09_framing():
    s = {"title": "T", "questions": [q("Q1")]}
    found = {f["id"]: f for f in run(s)}
    assert found["S07_no_description"]["severity"] == "medium"
    assert found["S08_no_welcome"]["severity"] == "low" and found["S08_no_welcome"]["category"] == "purpose"
    assert found["S09_no_thank_you"]["severity"] == "low"
    assert "S15_no_time_expectation" not in found      # S08 covers it


def test_s10_duplicate_labels():
    s = {"title": "T", "questions": [q("Q1", label="Age?"), q("Q2", label="age? ", options=["C", "D"])]}
    f = one(s, "S10_duplicate_labels")
    assert f["severity"] == "medium" and f["evidence"]["refs"] == ["Q1", "Q2"]
    assert f["roast"].startswith("Q1, Q2 have identical question text")


def test_s10_conditional_or_different_group_is_fine():
    s = {"title": "T", "questions": [q("Q1", label="Why?"), q("Q2", label="Why?", shown_when="Q1 is 'A'")]}
    assert "S10_duplicate_labels" not in ids(s)
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "group", "label": "Product A"},
                                     q("Q1.1", group="Q1", label="How satisfied?"), q("Q1.2", group="Q1", label="x?"),
                                     {"ref": "Q2", "type": "group", "label": "Product B"},
                                     q("Q2.1", group="Q2", label="How satisfied?"), q("Q2.2", group="Q2", label="y?")]}
    assert "S10_duplicate_labels" not in ids(s)


def test_s11_duplicate_options():
    f = one({"title": "T", "questions": [q("Q1", options=["Red", "red", "Blue"])]}, "S11_duplicate_options")
    assert f["severity"] == "medium" and "Red" in f["roast"]


def test_s13_single_hint_on_multi():
    s = {"title": "T", "questions": [q("Q1", type="multi_choice", label="Pick one of these")]}
    f = one(s, "S13_selection_hint_type_mismatch")
    assert f["severity"] == "high" and "several" in f["roast"]


def test_s13_number_words_and_no_false_positive():
    s = {"title": "T", "questions": [q("Q1", label="Choose three of the following")]}
    assert one(s, "S13_selection_hint_type_mismatch")["severity"] == "high"
    s = {"title": "T", "questions": [q("Q1", label="Which plan do you use?")]}
    assert "S13_selection_hint_type_mismatch" not in ids(s)


def test_s14_selection_count_unenforced():
    s = {"title": "T", "questions": [q("Q1", type="multi_choice", label="Select 3 features you use",
                                        options=["A", "B", "C", "D"])]}
    f = one(s, "S14_selection_count_unenforced")
    assert f["severity"] == "low" and "pick 3" in f["roast"]
    s["questions"][0]["selection"] = {"min": 3, "max": 3}
    assert "S14_selection_count_unenforced" not in ids(s)


def test_s15_no_time_expectation():
    s = {"title": "T", "welcome": {"title": "Hi", "description": "Tell us things."}, "questions": [q("Q1")]}
    assert one(s, "S15_no_time_expectation")["severity"] == "low"
    s["welcome"]["description"] = "Takes about 4 minutes."
    assert "S15_no_time_expectation" not in ids(s)
    s["welcome"]["description"] = "Tell us things."
    s["settings"] = {"stated_minutes": 4}
    assert "S15_no_time_expectation" not in ids(s)


def test_s16_time_mismatch():
    s = {"title": "T", "settings": {"stated_minutes": 1},
         "questions": [q(f"Q{i}", type="long_text", label=f"Tell me {i}") for i in range(1, 11)]}
    f = one(s, "S16_time_mismatch")
    assert f["severity"] == "medium" and "~1 minutes" in f["roast"] and "~10-minute" in f["roast"]
    s["settings"]["stated_minutes"] = 10
    assert "S16_time_mismatch" not in ids(s)


def test_s17_length_fatigue():
    assert one({"title": "T", "questions": mixed(31)}, "S17_length_fatigue")["severity"] == "medium"
    f = one({"title": "T", "questions": mixed(51)}, "S17_length_fatigue")
    assert f["severity"] == "high" and f["roast"] == "51 questions. That's not a survey, that's a shift."
    qs = mixed(51)
    qs[3]["shown_when"] = "Q1 is 'A'"
    f = one({"title": "T", "questions": qs}, "S17_length_fatigue")
    assert f["severity"] == "medium" and f["roast"].startswith("Up to 51 questions")


def test_s18_all_required_long():
    f = one({"title": "T", "questions": mixed(21)}, "S18_all_required_long")
    assert f["severity"] == "low" and f["roast"].startswith("21 of 21 questions are required")
    # v2 tier: n > 15 and >= 80 %
    qs = mixed(16)
    for x in qs[:3]:
        x["required"] = False
    assert "S18_all_required_long" in ids({"title": "T", "questions": qs})
    assert "S18_all_required_long" not in ids({"title": "T", "questions": mixed(15)})


def test_s19_no_open_ended():
    assert one({"title": "T", "questions": mixed(16)}, "S19_no_open_ended")["severity"] == "low"
    assert "S19_no_open_ended" not in ids({"title": "T", "kind": "form", "questions": mixed(16)})


def test_s21_anonymous_but_pii():
    s = {"title": "T", "settings": {"anonymous": True},
         "questions": [{"ref": "Q1", "type": "email", "label": "Email?"}]}
    f = one(s, "S21_anonymous_but_pii")
    assert f["severity"] == "high" and f["category"] == "trust"
    s["questions"] = [q("Q1", label="Wallet?", collects_pii=True)]
    assert "S21_anonymous_but_pii" in ids(s)


def test_s24_no_progress_bar_long():
    s = {"title": "T", "settings": {"progress_bar": False}, "questions": mixed(21)}
    assert one(s, "S24_no_progress_bar_long")["severity"] == "low"
    s["settings"]["progress_bar"] = True
    assert "S24_no_progress_bar_long" not in ids(s)


def test_s27_monotony_run():
    f = one({"title": "T", "questions": many(8)}, "S27_monotony_run")
    assert f["severity"] == "low" and f["roast"].startswith("Q1–Q8: 8 single_choice questions in a row")
    assert "S27_monotony_run" not in ids({"title": "T", "questions": many(7)})
    qs = many(8)
    qs[4]["shown_when"] = "Q1 is 'A'"
    assert "S27_monotony_run" not in ids({"title": "T", "questions": qs})


def test_s28_dead_run_text():
    s = {"title": "T", "questions": [q("Q1", label="First?", jumps=[{"when": None, "to": "end"}]),
                                     q("Q2", label="Dead 1"), q("Q3", label="Dead 2"), q("Q4", label="Dead 3")]}
    hits = find(s, "S28_unreachable_question")
    assert len(hits) == 1 and hits[0]["severity"] == "high" and hits[0]["question_ref"] == "Q2"
    assert hits[0]["evidence"]["refs"] == ["Q2", "Q3", "Q4"]
    assert hits[0]["roast"].startswith("Q2–Q4 (3 questions") and "Q1 always jumps past them" in hits[0]["roast"]


def test_s28_single_and_skipped_when_randomised():
    s = {"title": "T", "questions": [q("Q1", label="First?", jumps=[{"when": None, "to": "Q3"}]),
                                     q("Q2", label="Skipped forever"), q("Q3", label="Third?")]}
    hits = find(s, "S28_unreachable_question")
    assert [h["question_ref"] for h in hits] == ["Q2"] and "always jumps past it" in hits[0]["roast"]
    s["settings"] = {"randomize_questions": True}
    assert "S28_unreachable_question" not in ids(s)


# --- reachability --------------------------------------------------------------------------

def _by_ref(s):
    return {x["ref"]: x for x in normalise(s)["questions"]}


def test_reachability_conditional_jump_is_possible_path():
    s = {"title": "T", "questions": [q("Q1", jumps=[{"when": "Q1 is 'A'", "to": "Q3"}]), q("Q2"), q("Q3")]}
    qs = _by_ref(s)
    assert not any(x["unreachable"] for x in qs.values())
    assert qs["Q3"]["reached_from"] == [{"from": "Q1", "when": "Q1 is 'A'"}]


def test_reachability_backward_jump_and_jump_target_rescue():
    s = {"title": "T", "questions": [q("Q1", jumps=[{"when": "Q1 is 'A'", "to": "Q3"}, {"when": None, "to": "end"}]),
                                     q("Q2"), q("Q3")]}
    qs = _by_ref(s)
    assert qs["Q2"]["unreachable"] and not qs["Q3"]["unreachable"]


def test_reachability_default_jump_to_next_is_fall_through():
    s = {"title": "T", "questions": [q("Q1", jumps=[{"when": None, "to": "Q2"}]), q("Q2"), q("Q3")]}
    assert not any(x["unreachable"] for x in _by_ref(s).values())


def test_group_reachable_when_jump_lands_on_child():
    s = {"title": "T", "questions": [
        q("Q1", label="Pick", jumps=[{"when": "Q1 is 'A'", "to": "Q2.1"}, {"when": None, "to": "end"}]),
        {"ref": "Q2", "type": "group", "label": "Details"},
        q("Q2.1", label="Child 1", group="Q2"), q("Q2.2", label="Child 2", group="Q2")]}
    qs = _by_ref(s)
    assert not qs["Q2"]["unreachable"] and not qs["Q2.1"]["unreachable"] and not qs["Q2.2"]["unreachable"]
    assert "S28_unreachable_question" not in ids(s)


def test_condition_refs_parsed():
    s = {"title": "T", "questions": [q("Q1"), q("Q2", shown_when="Q1 is 'A' and Q1.2 is not empty",
                                                 jumps=[{"when": "Q2 is 'B'", "to": "end"}])]}
    q2 = _by_ref(s)["Q2"]
    assert q2["shown_when_refs"] == ["Q1", "Q1.2"]
    assert q2["jumps"][0]["when_refs"] == ["Q2"]
    assert q2["has_logic"] is True


# --- normalise / stats ----------------------------------------------------------------------

def test_normalise_assigns_refs_and_strips_html():
    s = {"title": "<b>Hello</b> &amp; welcome", "questions": [
        {"type": "single_choice", "label": "<p>Pick   one</p>", "options": ["A", "", "  ", "<i>B</i>", None]},
        {"type": "group", "label": "Sec"},
        {"type": "short_text", "label": "Name?", "group": "Sec"},
        {"type": "short_text", "label": "City?", "group": "Sec"},
        {"type": "long_text", "label": "More?"}]}
    n = normalise(s)
    assert n["title"] == "Hello & welcome"
    assert [x["ref"] for x in n["questions"]] == ["Q1", "Q2", "Q2.1", "Q2.2", "Q3"]
    assert n["questions"][0]["label"] == "Pick one"
    assert n["questions"][0]["options"] == ["A", "B"]
    assert n["questions"][0]["required"] is False
    assert s["questions"][0]["label"] == "<p>Pick   one</p>"     # input not mutated


def test_normalise_stats():
    s = {"title": "T", "settings": {"stated_minutes": 3}, "questions": [
        q("Q1", type="yes_no", label="Do you?"),
        q("Q2", type="email", label="Email?", required=False),
        q("Q3", type="long_text", label="Why?", shown_when="Q1 is 'Yes'"),
        {"ref": "Q4", "type": "matrix", "label": "Rate", "rows": ["a", "b", "c"], "columns": ["1", "2"]},
        {"ref": "Q5", "type": "statement", "label": "Thanks"}]}
    st = normalise(s)["stats"]
    assert st["top_level_questions"] == 5
    assert st["answerable_questions"] == 4
    assert st["required_answerable"] == 2
    assert st["open_ended_questions"] == 1
    assert st["pii_questions"] == 1
    assert st["questions_with_logic"] == 1
    assert st["estimated_minutes"] == round((10 + 15 + 60 + 24 + 8) / 60, 1)
    assert st["stated_minutes"] == 3


def test_normalise_garbage():
    n = normalise({"title": 5, "questions": "nope", "settings": [], "welcome": "x"})
    assert n["title"] == "" and n["questions"] == [] and isinstance(n["stats"], dict)
    assert normalise(None)["questions"] == []


def test_null_safety_everywhere():
    junk = [None, 1, "x", [], {}, {"type": 3, "label": ["x"], "options": [None, 1, {"a": 1}], "rows": 5,
                                   "columns": None, "scale": [], "selection": "x", "jumps": "x",
                                   "shown_when": 7, "group": 9, "exclusive_options": None},
            {"ref": "Q9", "type": "matrix", "label": "M", "rows": None, "columns": [None]},
            {"ref": "Q10", "type": "likert", "label": "L", "rows": ["a"], "scale": {"min": "x", "max": None,
                                                                                    "labels": []}},
            {"ref": "Q11", "type": "nps", "label": "recommend", "scale": {"min": 1, "max": 5, "labels": None}},
            {"ref": "Q12", "type": "multi_choice", "label": "x", "selection": {"min": "3", "max": None}},
            {"ref": "Q13", "type": "group", "label": None}]
    for title in (None, "", 3):
        for settings in (None, [], {"stated_minutes": "five", "anonymous": "yes"}):
            run({"title": title, "questions": junk, "settings": settings, "welcome": 3, "thank_you": [1]})
    run({})
    run(None)
    run([])


# --- v2 checks ------------------------------------------------------------------------------

def test_s30_matrix_columns_medium_rows_high():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "matrix", "label": "Rate", "rows": list("abc"),
                                      "columns": list("123456")}]}
    f = one(s, "S30_matrix_too_large")
    assert f["severity"] == "medium" and "3×6" in f["roast"]
    s["questions"][0]["rows"] = list("abcdefghi")
    assert one(s, "S30_matrix_too_large")["severity"] == "high"
    assert len(find(s, "S30_matrix_too_large")) == 1


def test_s30_likert_battery_uses_scale_points():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "likert", "label": "Agree?", "rows": ["a", "b"],
                                      "scale": {"min": 1, "max": 7}}]}
    assert "S30_matrix_too_large" in ids(s)


def test_s31_consecutive_matrices():
    m = lambda r: {"ref": r, "type": "matrix", "label": f"Rate {r}", "rows": ["a"], "columns": ["1", "2"]}
    s = {"title": "T", "questions": [m("Q1"), {"ref": "Q2", "type": "statement", "label": "x"}, m("Q3"), q("Q4")]}
    f = one(s, "S31_consecutive_matrices")
    assert f["severity"] == "medium" and f["evidence"]["refs"] == ["Q1", "Q3"]


def test_s32_ranking_too_many():
    s = {"title": "T", "questions": [q("Q1", type="ranking", label="Rank", options=list("abcdefgh"))]}
    f = one(s, "S32_ranking_too_many")
    assert f["severity"] == "medium" and "8 items" in f["roast"]


def test_s33_long_radio_list():
    s = {"title": "T", "questions": [q("Q1", options=[f"Option {c}" for c in "abcdefghijk"])]}
    assert one(s, "S33_long_radio_list")["severity"] == "low"


def test_s34_open_ended_overload():
    s = {"title": "T", "questions": [q("Q1", label="Pick?"), q("Q2", type="long_text", label="Why?")]}
    f = one(s, "S34_open_ended_overload")
    assert f["severity"] == "medium" and f["roast"].startswith("1 of 2 questions")


def test_s35_loaded_words_is_info():
    s = {"title": "T", "questions": [q("Q1", label="Don't you agree our app is great?")]}
    f = one(s, "S35_loaded_words")
    assert f["severity"] == "info" and "don't you agree" in f["roast"].lower()
    assert "S35_loaded_words" not in ids({"title": "T", "questions": [q("Q1", label="Do you shoulder bags?")]})


def test_s36_scale_endpoints_only():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "likert", "label": "Agree?", "required": True,
                                      "scale": {"min": 1, "max": 7, "labels": {"1": "No", "7": "Yes"}}}]}
    assert one(s, "S36_scale_endpoints_only")["severity"] == "low"
    s["questions"][0]["scale"]["labels"]["4"] = "Neutral"
    assert "S36_scale_endpoints_only" not in ids(s)


def test_s37_nps_nonstandard():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "rating", "label": "Would you recommend us?",
                                      "scale": {"min": 1, "max": 5}}]}
    assert one(s, "S37_nps_nonstandard")["severity"] == "medium"
    ok = {"title": "T", "questions": [{"ref": "Q1", "type": "nps",
                                       "label": "How likely are you to recommend us to a friend?",
                                       "scale": {"min": 0, "max": 10}}]}
    assert "S37_nps_nonstandard" not in ids(ok)


def test_s38_none_not_exclusive():
    s = {"title": "T", "questions": [q("Q1", type="multi_choice", options=["A", "B", "None of the above"])]}
    f = one(s, "S38_none_not_exclusive")
    assert f["severity"] == "medium" and "'None of the above'" in f["roast"]
    s["questions"][0]["exclusive_options"] = ["None of the above"]
    assert "S38_none_not_exclusive" not in ids(s)
    s = {"title": "T", "questions": [q("Q1", type="multi_choice", options=["A", "Nonetheless useful"])]}
    assert "S38_none_not_exclusive" not in ids(s)


def test_s39_other_without_text():
    s = {"title": "T", "questions": [q("Q1", options=["A", "B", "Other"])]}
    assert one(s, "S39_other_without_text")["severity"] == "low"
    s["questions"][0]["has_other"] = True
    assert "S39_other_without_text" not in ids(s)


def test_s40_long_list_not_randomised():
    s = {"title": "T", "questions": [q("Q1", options=["Apples", "Pears", "Plums", "Kiwis", "Figs", "Limes", "Dates"])]}
    assert one(s, "S40_long_list_not_randomised")["severity"] == "low"
    s["questions"][0]["randomize_options"] = True
    assert "S40_long_list_not_randomised" not in ids(s)
    ordinal = {"title": "T", "questions": [q("Q1", options=["Never", "Rarely", "Sometimes", "Often", "Very often",
                                                            "Always", "Daily"])]}
    assert "S40_long_list_not_randomised" not in ids(ordinal)


def test_s41_screener_without_exit():
    s = {"title": "T", "questions": [q("Q1", type="yes_no", label="Do you drive?", intent="screener"), q("Q2")]}
    assert one(s, "S41_screener_without_exit")["severity"] == "high"
    s["questions"][0]["jumps"] = [{"when": "Q1 is 'No'", "to": "end"}]
    assert "S41_screener_without_exit" not in ids(s)
    s["questions"][0]["jumps"] = []
    s["questions"][1]["shown_when"] = "Q1 is 'Yes'"
    assert "S41_screener_without_exit" not in ids(s)


def test_s42_shouting_or_noise():
    for label, opts in (("WHAT DO YOU THINK OF US", ["A", "B"]), ("Really??", ["A", "B"]),
                        ("Great!!!", ["A", "B"]), ("Mood?", ["😀", "😡"])):
        s = {"title": "T", "questions": [q("Q1", label=label, options=opts)]}
        assert one(s, "S42_shouting_or_noise")["severity"] == "low", label
    assert "S42_shouting_or_noise" not in ids({"title": "T", "questions": [q("Q1", label="How is NASA doing?")]})


def test_s43_label_too_long():
    s = {"title": "T", "questions": [q("Q1", label=" ".join(["word"] * 36) + "?")]}
    assert one(s, "S43_label_too_long")["severity"] == "medium"


def test_s45_yesno_type_mismatch():
    s = {"title": "T", "questions": [q("Q1", type="yes_no", label="Your favourite colour")]}
    assert one(s, "S45_yesno_type_mismatch")["severity"] == "medium"
    assert "S45_yesno_type_mismatch" not in ids({"title": "T", "questions": [q("Q1", type="yes_no",
                                                                               label="Do you drive?")]})


def test_s46_first_question_open_text():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "statement", "label": "Hi"},
                                     q("Q2", type="short_text", label="Name?", required=False), q("Q3")]}
    f = one(s, "S46_first_question_open_text")
    assert f["severity"] == "medium" and f["question_ref"] == "Q2"


def test_s47_no_logic_long_survey():
    assert one({"title": "T", "questions": mixed(31)}, "S47_no_logic_long_survey")["severity"] == "low"
    qs = mixed(31)
    qs[1]["jumps"] = [{"when": "Q2 is 'A'", "to": "Q4"}]
    assert "S47_no_logic_long_survey" not in ids({"title": "T", "questions": qs})


def test_s48_pii_before_content():
    s = {"title": "T", "questions": [{"ref": "Q1", "type": "email", "label": "Email?"},
                                     q("Q2", type="nps", label="How likely are you to recommend us?", intent="outcome",
                                       scale={"min": 0, "max": 10})]}
    f = one(s, "S48_pii_before_content")
    assert f["severity"] == "medium" and f["question_ref"] == "Q1"
    del s["questions"][1]["intent"]
    assert "S48_pii_before_content" not in ids(s)


def test_s50_welcome_too_long():
    s = {"title": "T", "welcome": {"title": "Hi", "description": " ".join(["word"] * 121)}, "questions": [q("Q1")]}
    f = one(s, "S50_welcome_too_long")
    assert f["severity"] == "medium" and "121-word" in f["roast"]


def test_s51_early_friction():
    s = {"title": "T", "questions": [q("Q1", type="long_text", label="Tell us everything"), q("Q2"),
                                     q("Q3", label="x?"), q("Q4", type="file", label="Upload")]}
    hits = find(s, "S51_early_friction")
    assert [h["question_ref"] for h in hits] == ["Q1"] and hits[0]["severity"] == "high"
    assert "an essay" in hits[0]["roast"]


# --- clean example passes ------------------------------------------------------------------

def test_annotated_example_is_clean():
    s = load_survey(str(FIXTURES / "acme_feedback.json"))
    found = run(s)
    assert not [f for f in found if f["severity"] in ("blocker", "high", "medium", "low")], found
    assert normalise(s)["stats"]["estimated_minutes"] == 3.3


# --- load_survey / CLI -------------------------------------------------------------------

def test_load_survey_json_string_and_path(tmp_path):
    text = json.dumps({"title": "T", "questions": []})
    assert load_survey(text)["title"] == "T"
    p = tmp_path / "s.json"
    p.write_text(text)
    assert load_survey(str(p))["title"] == "T"


def test_load_survey_rejects_garbage():
    with pytest.raises(ValueError):
        load_survey("[1, 2, 3]")


def _cli(*args):
    return subprocess.run([sys.executable, str(LINT), *args], capture_output=True, text=True)


def test_cli_exit_codes_and_formats(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"title": "", "questions": [q("Q1")]}))
    r = _cli(str(bad), "--json")
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert any(f["id"] == "S01_no_title" for f in data)
    r = _cli(str(bad))
    assert r.returncode == 1 and "| blocker | S01_no_title |" in r.stdout
    r = _cli(str(bad), "--polite")
    assert "Give the survey a title." in r.stdout and "can't tell what it is" not in r.stdout
    r = _cli(str(FIXTURES / "acme_feedback.json"))
    assert r.returncode == 0, r.stdout
    missing = _cli(str(tmp_path / "nope.json"))
    assert missing.returncode == 2
    junk = tmp_path / "junk.json"
    junk.write_text("[1,2]")
    assert _cli(str(junk)).returncode == 2


# --- non-finite numbers (json.loads accepts 1e999 and NaN) ----------------------------------

@pytest.mark.parametrize("bad", ["1e999", "-1e999", "NaN"])
def test_non_finite_numbers_never_crash(bad):
    text = ('{"title": "T", "settings": {"stated_minutes": %s}, "questions": ['
            '{"ref": "Q1", "type": "multi_choice", "label": "Pick", "required": true, "options": ["A", "B"],'
            ' "selection": {"min": %s, "max": %s}},'
            '{"ref": "Q2", "type": "likert", "label": "Agree?", "scale": {"min": %s, "max": %s}},'
            '{"ref": "Q3", "type": "likert", "label": "Battery", "rows": ["a", "b"], "scale": {"min": 1, "max": %s}},'
            '{"ref": "Q4", "type": "rating", "label": "Rate", "scale": {"min": 1, "max": %s, "labels": {"1": "x"}}}'
            ']}') % ((bad,) * 7)
    s = load_survey(text)
    n = normalise(s)
    assert n["settings"]["stated_minutes"] is None
    assert n["questions"][0]["selection"] == {"min": None, "max": None}
    assert n["questions"][1]["scale"]["max"] is None
    run(s)


def test_cli_non_finite_exits_cleanly(tmp_path):
    p = tmp_path / "inf.json"
    p.write_text('{"title": "T", "questions": [{"ref": "Q1", "type": "likert", "label": "L", "rows": ["a"],'
                 ' "scale": {"min": 1, "max": 1e999}}]}')
    r = _cli(str(p), "--json")
    assert r.returncode in (0, 1) and "Traceback" not in r.stderr


def test_cli_unexpected_error_exits_2(monkeypatch, capsys):
    import survey_lint

    def boom(_):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(survey_lint, "run", boom)
    monkeypatch.setattr(survey_lint, "load_survey", lambda _: {"title": "T", "questions": []})
    assert survey_lint.main(["x.json"]) == 2
    err = capsys.readouterr().err
    assert "kaboom" in err and len(err.strip().splitlines()) == 1


# --- unit words after numbers are not k/m suffixes (S12) -----------------------------------

def test_unit_word_starting_with_m_is_not_millions():
    assert numeric_range_issues(["5–14 minutes", "15–29 minutes", "30+ minutes"]) == []
    assert numeric_range_issues(["Less than 3 months", "3–11 months", "12–24 months", "More than 24 months"]) == []
    assert parse_range("5–14 minutes")[:2] == (5.0, 14.0)


def test_millions_and_thousands_suffixes_still_parse():
    assert parse_range("£25-40k")[:2] == (25000.0, 40000.0)
    assert parse_range("5m+")[:2] == (5000000.0, None)
    issues = numeric_range_issues(["0–1m", "1–5m", "5m+"])
    assert issues and all("000000" in i for i in issues)


# --- --stats ---------------------------------------------------------------------------------

STATS_KEYS = {"answerable_questions", "required_answerable", "open_ended_questions", "open_ended_share",
              "pii_questions", "questions_with_logic", "estimated_minutes", "estimated_minutes_rounded_up",
              "stated_minutes"}


def test_stats_cli_json_keys_and_values():
    r = subprocess.run([sys.executable, str(LINT), str(FIXTURES / "acme_feedback.json"), "--stats", "--json"],
                       capture_output=True, text=True)
    assert r.returncode == 0
    st = json.loads(r.stdout)
    assert set(st) == STATS_KEYS
    # survey-format.md: 10 + 15 + 8 + 60 + 8*3 + 60 + 10 + 10 = 197 s ≈ 3.3 min
    assert st["estimated_minutes"] == 3.3
    assert st["estimated_minutes_rounded_up"] == 4
    assert st["stated_minutes"] == 3
    assert st["answerable_questions"] == 8 and st["open_ended_questions"] == 2
    assert st["open_ended_share"] == 0.25


def test_stats_cli_table():
    r = subprocess.run([sys.executable, str(LINT), str(FIXTURES / "acme_feedback.json"), "--stats"],
                       capture_output=True, text=True)
    assert r.returncode == 0
    assert "| estimated_minutes_rounded_up | 4 |" in r.stdout


def test_stats_empty_survey():
    from survey_lint import stats
    st = stats({"title": "x", "questions": []})
    assert st["open_ended_share"] == 0.0 and st["estimated_minutes_rounded_up"] == 0
