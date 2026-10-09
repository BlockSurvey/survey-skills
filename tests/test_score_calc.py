"""Tests for shared/scripts/survey_score_calc.py (deterministic score calculator, bs-skills-1.0)."""
import copy
import json
import pathlib
import subprocess
import sys

import pytest

from survey_score_calc import (ITEMS, WEIGHT_PROFILES, calc, grade_for, normalise_noul, normalise_score,
                               run_lint, static_deduction, to_markdown, weight_profile)

ROOT = pathlib.Path(__file__).resolve().parents[1]
CALC = ROOT / "shared" / "scripts" / "survey_score_calc.py"
FIXTURES = ROOT / "tests" / "fixtures"

SEV_RANK = {"blocker": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


# --- fixtures and helpers -------------------------------------------------------------------

SURVEY_MIN = {
    "title": "Help us make invoicing simpler",
    "description": "We want to learn how you send invoices today so we can fix what slows you down.",
    "kind": "research",
    "welcome": {"title": "Help us make invoicing simpler", "description": "Takes about 2 minutes."},
    "thank_you": {"title": "Thank you", "description": "We'll share what we learn next month."},
    "settings": {"stated_minutes": 2},
    "questions": [
        {"ref": "Q1", "type": "single_choice", "label": "How often do you send invoices?",
         "options": ["Weekly", "Monthly", "Rarely"], "required": True},
        {"ref": "Q2", "type": "rating", "label": "How satisfied are you with invoicing today?",
         "options": ["1", "2", "3", "4", "5"], "required": True},
        {"ref": "Q3", "type": "long_text", "label": "What makes it hard?", "shown_when": "Q2 <= 2",
         "required": False},
    ],
}


def best_answer(item):
    """The best possible answer to an item (what a flawless survey would get)."""
    if item["primitive"] == "score":
        return {"level": item["levels"] - 1, "confidence": 0.9}
    if item["primitive"] == "noul":
        return {"p": 1.0 if item["good_when_yes"] else 0.0}
    return None


SURVEY_CHOICES = {"C5_gap_topic": "none", "K_survey_kind": "research", "X2_audience_kind": "existing_customers"}
QUESTION_CHOICES = {"Q19_recall_period": "stated", "Q25_best_type": "current_type_is_best",
                    "Q24_intent": "outcome", "R_role": "question"}


def perfect_judgments(survey):
    from survey_common import normalise
    s = normalise(survey)
    sv, qv = {}, {}
    for iid, item in ITEMS.items():
        if item["scope"] != "survey":
            continue
        a = best_answer(item)
        if a is None:
            a = {"choice": SURVEY_CHOICES[iid], "confidence": 0.9}
        sv[iid] = a
    for q in s["questions"]:
        d = {}
        for iid, item in ITEMS.items():
            if item["scope"] != "question":
                continue
            a = best_answer(item)
            if a is None:
                a = {"choice": QUESTION_CHOICES[iid], "confidence": 0.9}
            d[iid] = a
        qv[q["ref"]] = d
    return {"rubric_version": "bs-skills-1.0", "survey": sv, "questions": qv}


@pytest.fixture
def survey_min():
    return copy.deepcopy(SURVEY_MIN)


@pytest.fixture
def judgments_perfect():
    return perfect_judgments(SURVEY_MIN)


def with_survey(j, **items):
    j = copy.deepcopy(j)
    j["survey"].update(items)
    return j


def with_q(j, ref, **items):
    j = copy.deepcopy(j)
    j["questions"].setdefault(ref, {}).update(items)
    return j


NEEDS_WORK = {**{k: {"level": 0, "confidence": 0.9} for k in
                  ("A1_title_specific", "A3_purpose_explained", "A7_objective_inferable", "C1_objective_coverage",
                   "B1_logical_order", "E6_length_feels_justified")},
              "C3_has_outcome_question": {"p": 0.0}, "C2_has_screener": {"p": 0.0}, "C4_missing_why": {"p": 1.0}}


def findings(r, fid, ref=None):
    return [f for f in r["findings"] if f["id"] == fid and (ref is None or f["question_ref"] == ref)]


def one(r, fid, ref=None):
    hits = findings(r, fid, ref)
    assert len(hits) == 1, f"{fid} {ref}: {len(hits)} findings"
    return hits[0]


def static(fid, severity, category="questions", ref=None, funnel="answer_quality"):
    return {"id": fid, "severity": severity, "category": category, "scope": "question" if ref else "survey",
            "question_ref": ref, "question_label": None, "question_refs": [ref] if ref else [],
            "roast": f"{fid} roast", "fix": f"{fid} fix", "funnel": funnel, "evidence": {"kind": "static"}}


def survey_n(n, **extra):
    """A survey with n plain single-choice questions."""
    s = copy.deepcopy(SURVEY_MIN)
    s["questions"] = [{"ref": f"Q{i + 1}", "type": "single_choice", "label": f"Question number {i + 1}?",
                       "options": ["A", "B", "C"], "required": True} for i in range(n)]
    s.update(extra)
    return s


# --- brief tests ----------------------------------------------------------------------------

def test_rubric_md_matches_items():
    import re
    md_ids = set(re.findall(r"^\| `([A-Z]\d{1,2}[a-z]?_[a-z_]+|[A-Z]_[a-z_]+)`",
                            (ROOT / "shared" / "rubric.md").read_text(encoding="utf-8"), re.M))
    assert len(md_ids) == 77
    assert md_ids == set(ITEMS)


def test_items_consistent():
    stages = {"start", "continue", "finish", "answer_quality", "actionability", None}
    for iid, it in ITEMS.items():
        assert it["category"] in {"purpose", "structure", "coverage", "questions", "experience", "trust"}, iid
        assert it["funnel"] in stages, iid
        assert "*(" not in (it["fix"] or "") and "*(" not in str(it["roast"]), iid      # source marks stripped
        if it["primitive"] == "score":
            assert 2 <= it["levels"] == len(it["criteria"]), iid
            assert set(it["severity"]) <= set(range(it["levels"])) and set(it["severity"]) == set(it["roast"]), iid
        else:
            assert it["levels"] is None, iid
    assert ITEMS["A1_title_specific"]["severity"] == {0: "high", 1: "low"} and ITEMS["A1_title_specific"]["weight"] == 3
    assert ITEMS["C2_has_screener"]["kinds"] == ["research"] and ITEMS["A6_audience_stated"]["good_when_yes"]
    assert ITEMS["L_needs_why"]["locates"] == "C4_missing_why" and ITEMS["Q12_sensitive"]["informational"]
    assert sum(1 for it in ITEMS.values() if it["scope"] == "survey") == 42


def test_weights_sum_to_one_per_profile():
    for k, w in WEIGHT_PROFILES.items():
        assert abs(sum(w.values()) - 1) < 1e-6, k
    assert len(WEIGHT_PROFILES) == 8


def test_score_normalisation():
    assert normalise_score(1, 3) == 0.5
    assert normalise_score(3, 4) == 1.0 and normalise_score(0, 4) == 0.0


def test_noul_good_when_yes():
    assert normalise_noul(0.9, True) == 0.9 and normalise_noul(0.9, False) == pytest.approx(0.1)


def test_grades():
    assert grade_for(90, False) == ("A", "ready") and grade_for(74, False) == ("C", "needs_work")
    assert grade_for(95, True) == ("F", "not_ready")
    assert grade_for(89, False) == ("B", "ready") and grade_for(75, False) == ("C", "ready")
    assert grade_for(60, False) == ("D", "needs_work") and grade_for(50, False) == ("E", "needs_work")
    assert grade_for(49, False) == ("F", "not_ready")


def test_blocker_caps_at_49(survey_min, judgments_perfect):
    r = calc(survey_min | {"title": ""}, judgments_perfect,
             [{"id": "S01_no_title", "severity": "blocker", "category": "purpose", "scope": "survey", "roast": "",
               "fix": ""}])
    assert r["score"] <= 49 and r["verdict"] == "not_ready" and r["grade"] == "F"


def test_noul_strong_band_downgrades(survey_min, judgments_perfect):
    r = calc(survey_min, with_q(judgments_perfect, "Q1", Q2_double_barreled={"p": 0.75}), [])
    f = one(r, "Q2_double_barreled", "Q1")
    assert f["severity"] == "medium" and f["uncertain"] is True and "Probably" in f["roast"]
    r = calc(survey_min, with_q(judgments_perfect, "Q1", Q2_double_barreled={"p": 0.9}), [])
    f = one(r, "Q2_double_barreled", "Q1")
    assert f["severity"] == "high" and f["uncertain"] is False
    r = calc(survey_min, with_q(judgments_perfect, "Q1", Q2_double_barreled={"p": 0.6}), [])
    assert not findings(r, "Q2_double_barreled")


def test_repeat_dampening():
    six = [static("S11_duplicate_options", "high", ref=f"Q{i}") for i in range(6)]
    assert static_deduction(six) == pytest.approx(0.12 * 2)            # capped at 2x the base
    two = six[:2]
    assert static_deduction(two) == pytest.approx(0.12 * 1.25)
    assert static_deduction(six, "purpose") == 0                      # other category


def test_calc_tolerates_bad_judgments(survey_min):
    r = calc(survey_min, {"survey": {"A1_title_specific": {"level": 9}},
                          "questions": {"Q1": {"Q2_double_barreled": {"p": 1.4}}}}, [])
    assert r["meta"]["partial"] is True and 0 <= r["score"] <= 100
    assert "A1_title_specific" in r["meta"]["missing_items"]
    assert "Q1:Q2_double_barreled" in r["meta"]["missing_items"]


def test_finding_order(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect,
                    A1_title_specific={"level": 0, "confidence": 0.9},     # high, weight 3
                    A2_title_respondent_facing={"level": 0, "confidence": 0.9},  # medium, weight 1
                    A8_respondent_benefit={"level": 0, "confidence": 0.9},  # medium, weight 2
                    A6_audience_stated={"p": 0.05},                        # low
                    E3_thank_you_quality={"level": 0, "confidence": 0.2})  # info (unsure)
    j = with_q(j, "Q1", Q2_double_barreled={"p": 0.95},                    # high, weight 2
               Q3a_leading={"p": 0.75})                                   # medium, uncertain
    r = calc(survey_min, j, [static("S03_label_empty", "blocker", ref="Q2")])
    ids = [f["id"] for f in r["findings"]]
    assert ids[0] == "S03_label_empty"
    assert ids.index("A1_title_specific") < ids.index("Q2_double_barreled")     # same severity, weight 3 > 2
    assert ids.index("A8_respondent_benefit") < ids.index("A2_title_respondent_facing")  # weight 2 > 1
    assert ids.index("A2_title_respondent_facing") < ids.index("Q3a_leading")   # confident before hunch
    assert ids.index("Q3a_leading") < ids.index("A6_audience_stated") < ids.index("E3_thank_you_quality")
    keys = [(SEV_RANK[f["severity"]], f["uncertain"]) for f in r["findings"]]
    assert keys == sorted(keys)


def test_funnel_keys(survey_min, judgments_perfect):
    r = calc(survey_min, judgments_perfect, [])
    assert set(r["funnel"]) == {"start", "continue", "finish", "answer_quality", "actionability",
                                "predicted_completion_band"}
    for stage in ("start", "continue", "finish", "answer_quality", "actionability"):
        assert 0 <= r["funnel"][stage]["score"] <= 100 and isinstance(r["funnel"][stage]["drivers"], list)


# --- report shape and the clean case ----------------------------------------------------------

def test_perfect_survey_is_clean(survey_min, judgments_perfect):
    r = calc(survey_min, judgments_perfect, [])
    assert r["score"] == 100 and r["grade"] == "A" and r["verdict"] == "ready"
    assert r["meta"] == {"rubric_version": "bs-skills-1.0", "survey_kind": "research",
                         "audience_kind": "existing_customers", "weight_profile": "market_research",
                         "partial": False, "missing_items": []}
    assert [f for f in r["findings"] if f["severity"] != "info"] == []
    assert r["summary"] == "100/100. Clean, focused, and ready to publish. Nothing worth roasting."
    assert r["funnel"]["predicted_completion_band"] == "high"


def test_report_shape(survey_min, judgments_perfect):
    j = with_q(judgments_perfect, "Q1", Q2_double_barreled={"p": 0.95})
    r = calc(survey_min, j, [])
    assert set(r) >= {"score", "grade", "verdict", "summary", "categories", "funnel", "findings",
                      "findings_by_id", "questions", "stats", "meta"}
    assert [c["id"] for c in r["categories"]] == ["purpose", "structure", "coverage", "questions", "experience",
                                                 "trust", "conversion"]
    assert r["categories"][0] == {"id": "purpose", "label": "Purpose & framing", "weight": 0.15, "score": 100,
                                  "findings": 0}
    f = one(r, "Q2_double_barreled", "Q1")
    assert set(f) == {"id", "severity", "category", "scope", "question_ref", "question_label", "roast", "fix",
                      "evidence", "uncertain", "question_refs", "checklist", "target", "funnel"}
    assert f["question_refs"] == ["Q1"] and f["target"] == "question" and f["funnel"] == "answer_quality"
    assert f["checklist"] == ['Q1 "How often do you send invoices?": Split Q1 into one question per thing.']
    assert 'Q1 asks two things at once ("How often do you send invoices?")' in f["roast"]
    row = next(x for x in r["findings_by_id"] if x["id"] == "Q2_double_barreled")
    assert row["count"] == 1 and row["question_refs"] == ["Q1"]
    assert set(row) == {"id", "severity", "category", "target", "count", "question_refs", "fix", "checklist"}
    qrow = r["questions"][0]
    assert set(qrow) == {"ref", "type", "role", "label", "required", "score", "finding_ids"}
    assert qrow["finding_ids"] == ["Q2_double_barreled"] and qrow["score"] < 100
    assert r["stats"]["answerable_questions"] == 3


def test_score_confidence_bands(survey_min, judgments_perfect):
    r = calc(survey_min, with_survey(judgments_perfect, A1_title_specific={"level": 0, "confidence": 0.9}), [])
    f = one(r, "A1_title_specific")
    assert f["severity"] == "high" and not f["uncertain"] and '"Help us make invoicing simpler"' in f["roast"]
    assert f["target"] == "title" and f["checklist"] == [f["fix"]]
    r = calc(survey_min, with_survey(judgments_perfect, A1_title_specific={"level": 0, "confidence": 0.5}), [])
    f = one(r, "A1_title_specific")
    assert f["severity"] == "medium" and f["uncertain"] and "Probably" in f["roast"]
    r = calc(survey_min, with_survey(judgments_perfect, A1_title_specific={"level": 0, "confidence": 0.2}), [])
    f = one(r, "A1_title_specific")
    assert f["severity"] == "info" and f["uncertain"] and "wasn't sure" in f["roast"]
    r = calc(survey_min, with_survey(judgments_perfect, A1_title_specific={"level": 0}), [])  # default 0.7
    assert one(r, "A1_title_specific")["severity"] == "high"


def test_low_certainty_carries_no_weight(survey_min, judgments_perfect):
    # A coin-flip Noul is no evidence: it neither helps nor hurts
    r1 = calc(survey_min, judgments_perfect, [])
    r2 = calc(survey_min, with_survey(judgments_perfect, B5_redundant_questions={"p": 0.52}), [])
    assert r1["categories"][1]["score"] == r2["categories"][1]["score"] == 100


def test_calc_never_crashes_on_garbage():
    for survey in (None, {}, {"questions": None}, {"questions": [None, 3, {"type": None, "label": 5}]},
                   {"title": 7, "questions": [{"ref": "Q1", "type": "single_choice", "options": "x"}]}):
        for j in (None, [], "x", {"survey": [], "questions": "y"}, {"questions": {"Q1": 5}},
                  {"survey": {"A1_title_specific": {"level": True}, "B5_redundant_questions": {"p": "0.9"},
                              "K_survey_kind": {"choice": "nope"}}, "survey_kind": 4},
                  {"questions": {"Q1": {"Q1_clarity": {"level": 1.5}, "Q25_best_type": {"choice": 3}}}}):
            r = calc(survey, j, [None, {"id": 5}, {"id": "S99_x", "severity": "weird"}])
            assert 0 <= r["score"] <= 100 and r["grade"] in "ABCDEF"


def test_missing_items_listed(survey_min, judgments_perfect):
    j = copy.deepcopy(judgments_perfect)
    del j["survey"]["A1_title_specific"]
    del j["questions"]["Q2"]["Q1_clarity"]
    del j["survey"]["K_survey_kind"]          # informational: never "missing"
    r = calc(survey_min, j, [])
    assert r["meta"]["partial"] is True
    assert r["meta"]["missing_items"] == ["A1_title_specific", "Q2:Q1_clarity"]
    assert r["score"] == 100                  # absent evidence neither helps nor hurts


def test_unknown_items_and_refs_ignored(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect, Z9_made_up={"level": 0})
    j = with_q(j, "Q99", Q1_clarity={"level": 0})
    r = calc(survey_min, j, [])
    assert r["meta"]["partial"] is False and r["score"] == 100


# --- applicability ------------------------------------------------------------------------------

def test_shown_when_skips_q3b_and_q5(survey_min, judgments_perfect):
    j = with_q(judgments_perfect, "Q3", Q3b_presuming={"p": 0.99}, Q5_relevance={"level": 0, "confidence": 0.9})
    r = calc(survey_min, j, [])
    assert not findings(r, "Q3b_presuming") and not findings(r, "Q5_relevance")
    j2 = copy.deepcopy(judgments_perfect)
    del j2["questions"]["Q3"]["Q3b_presuming"], j2["questions"]["Q3"]["Q5_relevance"]
    assert calc(survey_min, j2, [])["meta"]["missing_items"] == []      # not applicable, so not missing
    # Without shown_when both apply
    s = copy.deepcopy(survey_min)
    del s["questions"][2]["shown_when"]
    r = calc(s, j, [])
    assert one(r, "Q3b_presuming", "Q3")["severity"] == "high" and one(r, "Q5_relevance", "Q3")


def test_information_role(survey_min, judgments_perfect):
    s = copy.deepcopy(survey_min)
    s["questions"][0]["role"] = "information"
    j = with_q(judgments_perfect, "Q1", Q2_double_barreled={"p": 0.99}, Q1_clarity={"level": 0, "confidence": 0.9},
               R_role={"choice": "information", "confidence": 0.9})
    r = calc(s, j, [])
    assert not findings(r, "Q2_double_barreled")
    f = one(r, "Q1_clarity", "Q1")
    assert f["fix"].startswith("Keep the explanation in Q1")
    assert r["questions"][0]["role"] == "information"
    rs = calc(s, with_survey(j, **NEEDS_WORK), [])
    assert rs["verdict"] == "needs_work" and "2 questions and 1 information step, " in rs["summary"]


def test_r_role_judgment_overrides_survey_role(survey_min, judgments_perfect):
    j = with_q(judgments_perfect, "Q1", R_role={"choice": "consent", "confidence": 0.9},
               Q1_clarity={"level": 0, "confidence": 0.9}, Q6_options_not_exhaustive={"p": 0.99})
    r = calc(survey_min, j, [])
    assert one(r, "Q1_clarity", "Q1")["fix"].startswith("State in Q1 exactly what the respondent is agreeing to")
    assert not findings(r, "Q6_options_not_exhaustive")


def test_statements_get_only_context_items(survey_min, judgments_perfect):
    s = copy.deepcopy(survey_min)
    s["questions"].insert(0, {"ref": "S1", "type": "statement", "label": "A few quick questions first."})
    j = with_q(judgments_perfect, "S1", Q1_clarity={"level": 0, "confidence": 0.9},
               Q4_jargon={"level": 0, "confidence": 0.9})
    r = calc(s, j, [])
    assert one(r, "Q1_clarity", "S1") and not findings(r, "Q4_jargon", "S1")
    assert [q["ref"] for q in r["questions"]] == ["Q1", "Q2", "Q3"]


def test_kinds_gating(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect, C3_has_outcome_question={"p": 0.0})
    r = calc(survey_min, j, [])
    assert one(r, "C3_has_outcome_question")["severity"] == "high"
    jf = dict(j, survey_kind="form")
    r = calc(survey_min, jf, [static("S19_no_open_ended", "low", "coverage")])
    assert not findings(r, "C3_has_outcome_question") and not findings(r, "S19_no_open_ended")
    assert r["meta"]["survey_kind"] == "form"
    # K_survey_kind below 0.5 confidence does not gate: falls back to the survey's own kind (research)
    jk = with_survey(j, K_survey_kind={"choice": "form", "confidence": 0.4})
    assert findings(calc(survey_min, jk, []), "C3_has_outcome_question")


def test_applies_families(survey_min, judgments_perfect):
    s = copy.deepcopy(survey_min)
    s["questions"].append({"ref": "Q4", "type": "multi_choice", "label": "Which tools do you use?",
                           "options": ["A", "B", "C"]})
    s["questions"].append({"ref": "Q5", "type": "number", "label": "How many invoices last month?"})
    j = perfect_judgments(s)
    j = with_q(j, "Q4", Q7_options_overlap={"p": 0.99}, Q8_scale_unbalanced={"p": 0.99})
    j = with_q(j, "Q5", Q22_units_stated={"p": 0.0}, Q6_options_not_exhaustive={"p": 0.99})
    j = with_q(j, "Q1", Q7_options_overlap={"p": 0.99}, Q8_scale_unbalanced={"p": 0.99})
    j = with_q(j, "Q2", Q22_units_stated={"p": 0.0})
    r = calc(s, j, [])
    assert not findings(r, "Q7_options_overlap", "Q4") and not findings(r, "Q8_scale_unbalanced", "Q4")
    assert one(r, "Q7_options_overlap", "Q1") and one(r, "Q8_scale_unbalanced", "Q1")   # 3 options = scale
    assert one(r, "Q22_units_stated", "Q5") and not findings(r, "Q22_units_stated", "Q2")
    assert not findings(r, "Q6_options_not_exhaustive", "Q5")


def test_gates(judgments_perfect):
    s = copy.deepcopy(SURVEY_MIN)
    j = with_q(judgments_perfect, "Q1", Q16_sensitive_reassured={"p": 0.0})
    assert not findings(calc(s, j, []), "Q16_sensitive_reassured")
    j = with_q(j, "Q1", Q12_sensitive={"p": 0.75})
    assert one(calc(s, j, []), "Q16_sensitive_reassured", "Q1")["severity"] == "medium"
    j = with_survey(judgments_perfect, F3b_incentive_delivery_clear={"p": 0.0})
    assert not findings(calc(s, j, []), "F3b_incentive_delivery_clear")
    j = with_survey(j, F3a_incentive_mentioned={"p": 0.9})
    assert one(calc(s, j, []), "F3b_incentive_delivery_clear")["severity"] == "medium"
    # F3 is ignored when F3a and F3b are both judged
    j = with_survey(judgments_perfect, F3_incentive_clear={"p": 0.0})
    assert not findings(calc(s, j, []), "F3_incentive_clear")
    j2 = copy.deepcopy(j)
    del j2["survey"]["F3a_incentive_mentioned"], j2["survey"]["F3b_incentive_delivery_clear"]
    assert one(calc(s, j2, []), "F3_incentive_clear")
    # C7 only for more than 25 answerable questions
    j = with_survey(judgments_perfect, C7_has_attention_check={"p": 0.0})
    assert not findings(calc(s, j, []), "C7_has_attention_check")
    big = survey_n(26)
    jb = with_survey(perfect_judgments(big), C7_has_attention_check={"p": 0.0})
    assert one(calc(big, jb, []), "C7_has_attention_check")["severity"] == "low"


# --- item-specific rules ------------------------------------------------------------------------

def test_q15_abandon_risk_position():
    s = survey_n(7)
    j = perfect_judgments(s)
    j = with_q(j, "Q2", Q15_abandon_risk={"level": 0, "confidence": 0.9})
    j = with_q(j, "Q7", Q15_abandon_risk={"level": 0, "confidence": 0.9})
    r = calc(s, j, [])
    assert one(r, "Q15_abandon_risk", "Q2")["severity"] == "high"
    assert one(r, "Q15_abandon_risk", "Q7")["severity"] == "medium"


def test_profile_specific_severity(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect, A10_deadline_stated={"p": 0.0})
    assert one(calc(survey_min, j, []), "A10_deadline_stated")["severity"] == "low"
    je = dict(j, survey_kind="feedback", audience_kind="event_attendees")
    r = calc(survey_min, je, [])
    assert r["meta"]["weight_profile"] == "event_feedback"
    assert one(r, "A10_deadline_stated")["severity"] == "info"
    j = with_q(judgments_perfect, "Q1", Q21_social_desirability={"p": 0.95})
    assert one(calc(survey_min, j, []), "Q21_social_desirability")["severity"] == "low"
    ja = dict(j, audience_kind="students")
    assert one(calc(survey_min, ja, []), "Q21_social_desirability")["severity"] == "medium"


def test_weight_profiles():
    assert weight_profile("research", "employees") == "employee_engagement"
    assert weight_profile("research", "students") == "academic_research"
    assert weight_profile("research", "unclear") == "market_research"
    assert weight_profile("feedback", "employees") == "employee_engagement"
    assert weight_profile("feedback", "event_attendees") == "event_feedback"
    assert weight_profile("feedback", "existing_customers") == "customer_satisfaction"
    assert weight_profile("form", "prospects_or_general_public") == "lead_generation"
    assert weight_profile("form", "employees") == "registration_or_form"
    assert weight_profile("quiz", "students") == "default"
    assert weight_profile(None, "students") == "default"


def test_profile_from_x2_companion(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect, X2_audience_kind={"choice": "employees", "confidence": 0.8})
    r = calc(survey_min, j, [])
    assert r["meta"]["weight_profile"] == "employee_engagement" and r["meta"]["audience_kind"] == "employees"
    assert r["categories"][5]["weight"] == 0.20
    j = with_survey(judgments_perfect, X2_audience_kind={"choice": "employees", "confidence": 0.3})
    assert calc(survey_min, j, [])["meta"]["audience_kind"] == "unclear"


def test_q25_replaces_q9_fix_and_q19(survey_min, judgments_perfect):
    j = with_q(judgments_perfect, "Q1", Q9_type_fit={"level": 0, "confidence": 0.9},
               Q25_best_type={"choice": "dropdown", "confidence": 0.8},
               Q19_recall_period={"choice": "missing_but_needed", "confidence": 0.8})
    r = calc(survey_min, j, [])
    q25 = one(r, "Q25_best_type", "Q1")
    assert q25["severity"] == "medium" and "is a single_choice but" in q25["roast"] and "dropdown" in q25["roast"]
    assert one(r, "Q9_type_fit", "Q1")["fix"] == "Change Q1 to a dropdown question."
    assert one(r, "Q19_recall_period", "Q1")["severity"] == "medium"
    # Low confidence or naming the current type: no finding
    j = with_q(judgments_perfect, "Q1", Q25_best_type={"choice": "dropdown", "confidence": 0.5},
               Q19_recall_period={"choice": "missing_but_needed", "confidence": 0.5})
    r = calc(survey_min, j, [])
    assert not findings(r, "Q25_best_type") and not findings(r, "Q19_recall_period")
    j = with_q(judgments_perfect, "Q1", Q25_best_type={"choice": "single_choice", "confidence": 0.9})
    assert not findings(calc(survey_min, j, []), "Q25_best_type")


def test_q5_follow_ups(survey_min, judgments_perfect):
    j = with_q(judgments_perfect, "Q2", Q5_relevance={"level": 0, "confidence": 0.9})
    f = one(calc(survey_min, j, []), "Q5_relevance", "Q2")
    assert f["question_refs"] == ["Q2", "Q3"]
    assert "Its follow-ups (Q3) only show after it and go with it." in f["roast"]
    assert "Q3: shown only after Q2; keep or remove them together." in f["checklist"]


def test_gap_topic_named_or_hunch(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect, C5_obvious_gap={"level": 0, "confidence": 0.9},
                    C5_gap_topic={"choice": "pricing", "confidence": 0.8})
    f = one(calc(survey_min, j, []), "C5_obvious_gap")
    assert f["severity"] == "high" and "Most likely missing: willingness to pay, budget, or price sensitivity." \
        in f["roast"]
    assert f["checklist"] == ["Add a question about: willingness to pay, budget, or price sensitivity."]
    j = with_survey(j, C5_gap_topic={"choice": "none", "confidence": 0.8})
    f = one(calc(survey_min, j, []), "C5_obvious_gap")
    assert f["severity"] == "medium" and f["uncertain"] and "couldn't name the missing topic" in f["roast"]


def test_c5_evidence_halved_when_topic_unnamed(survey_min, judgments_perfect):
    base = with_survey(judgments_perfect, C5_obvious_gap={"level": 0, "confidence": 1.0})
    named = calc(survey_min, with_survey(base, C5_gap_topic={"choice": "pricing", "confidence": 0.9}), [])
    unnamed = calc(survey_min, with_survey(base, C5_gap_topic={"choice": "none", "confidence": 0.9}), [])
    cov = lambda r: r["categories"][2]["score"]  # noqa: E731
    # coverage evidence weights: C1 4 x 0.9 = 3.6, C2 2, C3 3, C4 2 (Nouls at p 0/1 are certain), C6 1 x 0.9,
    # C5 3 x 1.0 (value 0) -> halved to 1.5 when the topic is not named
    assert cov(named) == round(100 * 11.5 / 14.5) and cov(unnamed) == round(100 * 11.5 / 13.0)


# --- locators -----------------------------------------------------------------------------------

def test_locator_attachment(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect, B5_redundant_questions={"p": 0.95})
    j = with_q(j, "Q2", L_duplicate_of_earlier={"p": 0.9})
    f = one(calc(survey_min, j, []), "B5_redundant_questions")
    assert f["question_refs"] == ["Q2"] and f["roast"].endswith(" See: Q2.")
    assert f["checklist"] == ['Q2 "How satisfied are you with invoicing today?": merge it with the earlier '
                              'question that asks the same thing, or reword it to ask something distinct.']
    assert f["evidence"]["located"] == [{"ref": "Q2", "p": 0.9}] and f["severity"] == "medium"
    # fallback: nothing at 0.7, best at or above 0.5 -> "Most likely"
    j = with_q(j, "Q2", L_duplicate_of_earlier={"p": 0.6})
    f = one(calc(survey_min, j, []), "B5_redundant_questions")
    assert f["roast"].endswith(" Most likely: Q2.") and f["question_refs"] == ["Q2"]
    # nothing to point at: a hunch, one severity lower
    j = with_q(j, "Q2", L_duplicate_of_earlier={"p": 0.1})
    f = one(calc(survey_min, j, []), "B5_redundant_questions")
    assert f["severity"] == "low" and f["uncertain"] and "treat it as a hunch" in f["roast"]
    assert f["evidence"]["located"] == []


def test_locator_ordering_and_alias(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect, C6_demographics_proportionate={"level": 0, "confidence": 0.9})
    j = with_q(j, "Q1", L_is_demographic={"p": 0.8})
    j = with_q(j, "Q3", L_is_demographic={"p": 0.95})
    f = one(calc(survey_min, j, []), "C6_demographics_proportionate")
    assert f["question_refs"] == ["Q3", "Q1"] and f["roast"].endswith(" See: Q3, Q1.")


def test_b2_points_at_first_answerable(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect, B2_opening_question={"level": 0, "confidence": 0.9})
    f = one(calc(survey_min, j, []), "B2_opening_question")
    assert f["question_refs"] == ["Q1"] and f["target"] == "question" and f["roast"].endswith(" See: Q1.")
    assert f["checklist"] == ['Q1 "How often do you send invoices?": open with an easy, on-topic question '
                              'instead; move this one later.']


# --- code rules over informational items ----------------------------------------------------

def test_intent_mix_rules():
    s = survey_n(8)
    j = perfect_judgments(s)
    for i in range(1, 9):
        j = with_q(j, f"Q{i}", Q24_intent={"choice": "attitude", "confidence": 0.9})
    r = calc(s, j, [])
    f = one(r, "Q24_intent")
    assert f["severity"] == "medium" and f["evidence"]["rule"] == "no_outcome"
    # a C3 finding already covers it
    assert not findings(calc(s, with_survey(j, C3_has_outcome_question={"p": 0.0}), []), "Q24_intent")
    # demographics heavy + outcome buried
    for i in (1, 2, 3):
        j = with_q(j, f"Q{i}", Q24_intent={"choice": "demographic", "confidence": 0.9})
    j = with_q(j, "Q8", Q24_intent={"choice": "outcome", "confidence": 0.9})
    rules = {f["evidence"]["rule"]: f for f in findings(calc(s, j, []), "Q24_intent")}
    assert set(rules) == {"demographics_heavy", "outcome_buried"}
    assert rules["demographics_heavy"]["roast"] == "3 of 8 questions are demographics. That's a census, not a survey."
    assert rules["demographics_heavy"]["severity"] == "low" and rules["outcome_buried"]["severity"] == "low"
    # survey intent wins when no judgment, low-confidence judgment ignored
    s2 = copy.deepcopy(s)
    s2["questions"][0]["intent"] = "outcome"
    j2 = perfect_judgments(s2)
    for i in range(1, 9):
        j2 = with_q(j2, f"Q{i}", Q24_intent={"choice": "attitude", "confidence": 0.4})
    del j2["questions"]["Q1"]["Q24_intent"]
    assert not findings(calc(s2, j2, []), "Q24_intent")


def test_no_outcome_skipped_for_forms():
    s = survey_n(4)
    j = perfect_judgments(s)
    for i in range(1, 5):
        j = with_q(j, f"Q{i}", Q24_intent={"choice": "contact_or_admin", "confidence": 0.9})
    assert findings(calc(s, j, []), "Q24_intent")
    assert not findings(calc(s, dict(j, survey_kind="form"), []), "Q24_intent")


def test_only_outcome_hypothetical(survey_min, judgments_perfect):
    j = copy.deepcopy(judgments_perfect)
    for ref in ("Q1", "Q2", "Q3"):
        j = with_q(j, ref, Q18_hypothetical={"p": 0.9})
    f = one(calc(survey_min, j, []), "Q18_hypothetical")
    assert f["severity"] == "medium" and f["scope"] == "survey" and f["evidence"]["rule"] == "only_outcome_hypothetical"
    j = with_q(j, "Q2", Q18_hypothetical={"p": 0.1})
    assert not findings(calc(survey_min, j, []), "Q18_hypothetical")


def test_informational_items_produce_no_finding(survey_min, judgments_perfect):
    j = with_survey(judgments_perfect, F1_sensitive_topics={"p": 0.99})
    j = with_q(j, "Q1", Q12_sensitive={"p": 0.5}, L_hard_to_read={"p": 0.99})
    r = calc(survey_min, j, [])
    assert not findings(r, "F1_sensitive_topics") and not findings(r, "Q12_sensitive")
    assert not findings(r, "L_hard_to_read")


# --- hybrid checks --------------------------------------------------------------------------

def hybrid_survey():
    return {"title": "T", "questions": [
        {"ref": "Q1", "type": "yes_no", "label": "Do you own a car?", "options": ["Yes", "No"], "required": True},
        {"ref": "Q2", "type": "single_choice", "label": "If yes, which brand?", "options": ["A", "B"],
         "required": True},
        {"ref": "Q3", "type": "single_choice", "label": "What is your income?", "options": ["Low", "High"],
         "required": True},
        {"ref": "Q4", "type": "single_choice", "label": "Which logo do you prefer?", "options": ["Left", "Right"]},
    ]}


def test_s22_conditional_without_logic():
    s = hybrid_survey()
    j = with_q(perfect_judgments(s), "Q2", Q10_depends_on_prior={"p": 0.9})
    f = one(calc(s, j, []), "S22_conditional_without_logic", "Q2")
    assert f["severity"] == "high" and not f["uncertain"] and f["category"] == "structure"
    assert f["checklist"] == ["Q2: " + f["fix"]] and f["evidence"]["kind"] == "hybrid"
    assert f["funnel"] == "answer_quality"
    j75 = with_q(j, "Q2", Q10_depends_on_prior={"p": 0.75})
    f = one(calc(s, j75, []), "S22_conditional_without_logic", "Q2")
    assert f["severity"] == "medium" and f["uncertain"] and "Probably" in f["roast"]
    # own jumps do not count
    s_own = copy.deepcopy(s)
    s_own["questions"][1]["jumps"] = [{"when": "Q2 is 'A'", "to": "Q4"}]
    assert findings(calc(s_own, j, []), "S22_conditional_without_logic")
    # shown_when, conditional jump to it, or the previous question jumping elsewhere suppress it
    s_sw = copy.deepcopy(s)
    s_sw["questions"][1]["shown_when"] = "Q1 is 'Yes'"
    assert not findings(calc(s_sw, j, []), "S22_conditional_without_logic")
    s_prev = copy.deepcopy(s)
    s_prev["questions"][0]["jumps"] = [{"when": "Q1 is 'No'", "to": "Q3"}]
    assert not findings(calc(s_prev, j, []), "S22_conditional_without_logic")
    s_to = copy.deepcopy(s)
    s_to["questions"][3]["jumps"] = [{"when": "Q4 is 'Left'", "to": "Q2"}]
    assert not findings(calc(s_to, j, []), "S22_conditional_without_logic")


def test_s23_sensitive_without_optout():
    s = hybrid_survey()
    j = with_q(perfect_judgments(s), "Q3", Q12_sensitive={"p": 0.9})
    f = one(calc(s, j, []), "S23_sensitive_without_optout", "Q3")
    assert f["severity"] == "low" and f["category"] == "trust" and f["funnel"] == "continue"
    assert not findings(calc(s, with_q(j, "Q3", Q12_sensitive={"p": 0.75}), []), "S23_sensitive_without_optout")
    s2 = copy.deepcopy(s)
    s2["questions"][2]["has_prefer_not_to_answer"] = True
    assert not findings(calc(s2, j, []), "S23_sensitive_without_optout")
    s3 = copy.deepcopy(s)
    s3["questions"][2]["required"] = False
    assert not findings(calc(s3, j, []), "S23_sensitive_without_optout")


def test_s25_s26_visual():
    s = hybrid_survey()
    j = with_q(perfect_judgments(s), "Q4", Q11_requires_visual={"p": 0.9})
    f = one(calc(s, j, []), "S26_visual_missing", "Q4")
    assert f["severity"] == "medium" and f["category"] == "questions"
    s2 = copy.deepcopy(s)
    s2["questions"][3]["has_image"] = True
    r = calc(s2, j, [])
    assert one(r, "S25_visual_not_described", "Q4")["severity"] == "low" and not findings(r, "S26_visual_missing")
    f = one(calc(s, with_q(j, "Q4", Q11_requires_visual={"p": 0.8}), []), "S26_visual_missing", "Q4")
    assert f["severity"] == "low" and f["uncertain"]


def test_hybrids_skip_information_steps():
    s = hybrid_survey()
    s["questions"][1]["role"] = "information"
    j = with_q(perfect_judgments(s), "Q2", Q10_depends_on_prior={"p": 0.95}, Q11_requires_visual={"p": 0.95},
               R_role={"choice": "information", "confidence": 0.9})
    r = calc(s, j, [])
    assert not findings(r, "S22_conditional_without_logic") and not findings(r, "S26_visual_missing")


# --- static findings ------------------------------------------------------------------------

def test_static_findings_deduct_and_get_checklists(survey_min, judgments_perfect):
    r = calc(survey_min, judgments_perfect, [static("S11_duplicate_options", "medium", ref="Q1")])
    assert r["categories"][3]["score"] == 94
    f = one(r, "S11_duplicate_options")
    assert f["checklist"] == ["Q1: S11_duplicate_options fix"] and f["target"] == "question"
    assert f["uncertain"] is False
    r = calc(survey_min, judgments_perfect, [static("S07_no_description", "medium", "purpose", funnel="start")])
    f = one(r, "S07_no_description")
    assert f["target"] == "welcome" and f["checklist"] == ["S07_no_description fix"]
    assert r["categories"][0]["score"] == 94 and r["funnel"]["start"]["score"] == 94
    assert "S07_no_description" in r["funnel"]["start"]["drivers"]


def test_static_deduction_cap():
    many = [static(f"S{30 + i}_x", "high") for i in range(5)]
    assert static_deduction(many) == pytest.approx(0.35)


def test_conversion_takes_g_static_deductions(survey_min, judgments_perfect):
    r = calc(survey_min, judgments_perfect, [static("S51_early_friction", "high", "structure", ref="Q1",
                                                    funnel="continue")])
    cats = {c["id"]: c for c in r["categories"]}
    assert cats["structure"]["score"] == 88 and cats["conversion"]["score"] == 88


def test_question_high_penalty(survey_min, judgments_perfect):
    j = judgments_perfect
    for ref in ("Q1", "Q2", "Q3"):
        j = with_q(j, ref, Q2_double_barreled={"p": 1.0})
    r = calc(survey_min, j, [])
    # each question: Q2 item value 0 at weight 2; other items perfect -> mean minus 3 x 0.02
    per_q = [q["score"] for q in r["questions"]]
    assert all(s < 100 for s in per_q)
    assert abs(r["categories"][3]["score"] - (sum(per_q) / 3 - 6)) <= 1


def test_s35_confirmed_or_dropped(survey_min, judgments_perfect):
    lint = [static("S35_loaded_words", "info", ref="Q1")]
    assert not findings(calc(survey_min, judgments_perfect, lint), "S35_loaded_words")
    j = with_q(judgments_perfect, "Q1", Q3a_leading={"p": 0.8})
    assert one(calc(survey_min, j, lint), "S35_loaded_words")["severity"] == "low"


def test_run_lint_uses_judged_intent():
    s = hybrid_survey()
    j = with_q(perfect_judgments(s), "Q1", Q24_intent={"choice": "screener", "confidence": 0.9})
    assert any(f["id"] == "S41_screener_without_exit" for f in run_lint(s, j))
    j = with_q(j, "Q1", Q24_intent={"choice": "screener", "confidence": 0.5})
    assert not any(f["id"] == "S41_screener_without_exit" for f in run_lint(s, j))


# --- funnel -----------------------------------------------------------------------------------

def test_funnel_band_and_drivers(survey_min, judgments_perfect):
    worst = {iid: {"level": 0, "confidence": 0.9} if ITEMS[iid]["primitive"] == "score"
             else {"p": 0.0 if ITEMS[iid]["good_when_yes"] else 1.0}
             for iid in ("B1_logical_order", "B4_sections_signposted", "B5_redundant_questions", "B7_end_loading",
                         "E1_tone_consistent", "E3_thank_you_quality", "E6_length_feels_justified",
                         "E8_straightlining_risk")}
    r = calc(survey_min, with_survey(judgments_perfect, **worst), [])
    assert r["funnel"]["finish"]["score"] == 0 and r["funnel"]["predicted_completion_band"] == "low"
    assert r["funnel"]["finish"]["drivers"][0] == "B1_logical_order" and len(r["funnel"]["finish"]["drivers"]) == 3
    j = with_q(judgments_perfect, "Q2", Q15_abandon_risk={"level": 0, "confidence": 0.9})
    assert "Q15_abandon_risk:Q2" in calc(survey_min, j, [])["funnel"]["continue"]["drivers"]
    half = {k: v for k, v in worst.items() if k in ("B1_logical_order", "B5_redundant_questions")}
    band = calc(survey_min, with_survey(judgments_perfect, **half), [])["funnel"]
    assert band["predicted_completion_band"] == "medium" and 50 <= band["finish"]["score"] < 75


def test_lint_only_preview_uses_neutral_base(survey_min):
    r = calc(survey_min, {}, [])
    assert r["score"] == 70 and r["meta"]["partial"] is True
    assert all(c["score"] == 70 for c in r["categories"])


# --- summary, markdown, polite -------------------------------------------------------------------

def test_summary_lines(survey_min, judgments_perfect):
    r = calc(survey_min, judgments_perfect, [static("S03_label_empty", "blocker", ref="Q2")])
    assert r["summary"].startswith(f"{r['score']}/100. Not publishable yet — 1 blocker(s). Start here: ")
    j = with_survey(judgments_perfect, A1_title_specific={"level": 0, "confidence": 0.9})
    r = calc(survey_min, j, [])
    assert r["verdict"] == "ready" and "Ready to publish; one thing to polish first: Your title" in r["summary"]
    j = with_survey(judgments_perfect, **{k: {"level": 0, "confidence": 0.9} for k in
                                          ("A1_title_specific", "A3_purpose_explained", "C1_objective_coverage",
                                           "A7_objective_inferable", "B1_logical_order",
                                           "E6_length_feels_justified")})
    j = with_survey(j, C3_has_outcome_question={"p": 0.0}, C2_has_screener={"p": 0.0}, C4_missing_why={"p": 1.0})
    r = calc(survey_min, j, [])
    assert r["verdict"] == "needs_work"
    assert "3 questions, " in r["summary"] and "serious and" in r["summary"] and "Biggest one:" in r["summary"]


def test_markdown_render(survey_min, judgments_perfect):
    j = with_q(judgments_perfect, "Q1", Q2_double_barreled={"p": 0.95})
    r = calc(survey_min, j, [static("S11_duplicate_options", "medium", ref="Q1")])
    md = to_markdown(r)
    assert md.startswith(f"# Survey score: {r['score']}/100 · {r['grade']} · {r['verdict']}\n")
    assert r["summary"] in md
    for part in ("| Category |", "| Stage |", "## Top findings", "## Questions", "## What to do first",
                 "high · Q1 · Q1 asks two things at once", "→ Split Q1 into one question per thing."):
        assert part in md, part
    polite = to_markdown(r, polite=True)
    assert "asks two things at once" not in polite and "Split Q1 into one question per thing." in polite


# --- CLI ------------------------------------------------------------------------------------------

def run_cli(*args):
    return subprocess.run([sys.executable, str(CALC), *map(str, args)], capture_output=True, text=True)


def test_cli_exit_codes(tmp_path):
    sp, jp = tmp_path / "s.json", tmp_path / "j.json"
    sp.write_text(json.dumps(SURVEY_MIN))
    jp.write_text(json.dumps(perfect_judgments(SURVEY_MIN)))
    p = run_cli(sp, jp, "--json")
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout)
    assert out["score"] == 100 and out["findings"] == []
    # blocker via --lint (no title) -> 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(dict(SURVEY_MIN, title="")))
    p = run_cli(bad, jp, "--lint", "--json")
    assert p.returncode == 1 and json.loads(p.stdout)["verdict"] == "not_ready"
    # invalid input -> 2
    nj = tmp_path / "nj.json"
    nj.write_text("{not json")
    assert run_cli(sp, nj).returncode == 2
    assert run_cli(tmp_path / "missing.json", jp).returncode == 2
    assert run_cli(sp).returncode == 2


def test_cli_markdown_polite_and_print_items(tmp_path):
    p = run_cli(FIXTURES / "acme_feedback.json", FIXTURES / "judgments_acme.json", "--lint", "--md")
    assert p.returncode in (0, 1), p.stderr
    assert p.stdout.startswith("# Survey score:") and "## What to do first" in p.stdout
    pj = run_cli(FIXTURES / "acme_feedback.json", FIXTURES / "judgments_acme.json", "--lint", "--json", "--polite")
    data = json.loads(pj.stdout)
    assert all("roast" not in f for f in data["findings"])
    p = run_cli("--print-items")
    assert p.returncode == 0
    items = json.loads(p.stdout)
    assert len(items) == 77 and items["A1_title_specific"]["weight"] == 3


def test_fixture_judgments(tmp_path):
    from survey_common import load_survey
    s = load_survey(str(FIXTURES / "acme_feedback.json"))
    j = json.loads((FIXTURES / "judgments_acme.json").read_text())
    r = calc(s, j, run_lint(s, j))
    assert r["meta"]["weight_profile"] == "customer_satisfaction" and r["meta"]["partial"] is False
    assert r["verdict"] in ("ready", "needs_work") and r["score"] >= 75
    bad = json.loads((FIXTURES / "judgments_malformed.json").read_text())
    r = calc(s, bad, [])
    assert r["meta"]["partial"] is True and 0 <= r["score"] <= 100
