"""Tests for scripts/build_catalog.py and scripts/build_prompts.py."""
import json
import shutil
from pathlib import Path

import pytest

import build_catalog
import build_prompts

REPO = Path(__file__).resolve().parent.parent
SKILLS = sorted(p.name for p in (REPO / "skills").iterdir() if (p / "SKILL.md").is_file())
READMES = ("README.md", "README.zh-CN.md")


def _copy_root(tmp_path):
    """A throwaway repo root with the real skills, READMEs and catalog meta."""
    shutil.copytree(REPO / "skills", tmp_path / "skills",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "scripts").mkdir()
    shutil.copy(REPO / "scripts" / "catalog_meta.json", tmp_path / "scripts" / "catalog_meta.json")
    for name in READMES:
        shutil.copy(REPO / name, tmp_path / name)
    return tmp_path


# --- catalog ----------------------------------------------------------------------------------

def test_repo_catalog_is_in_sync():
    assert build_catalog.main(["--check"]) == 0


def test_repo_prompts_are_in_sync():
    assert build_prompts.main(["--check"]) == 0


def test_catalog_has_every_skill_once_across_four_categories():
    skills = build_catalog.load_skills(REPO)
    assert sorted(s["name"] for s in skills) == SKILLS
    assert len(SKILLS) == 9
    block = build_catalog.render(skills, build_catalog.load_meta(REPO), "en")
    rows = [ln for ln in block.splitlines() if ln.startswith("| [")]
    assert len(rows) == 9
    for name in SKILLS:
        assert sum(f"[**{name}**]" in r for r in rows) == 1
    headings = [ln for ln in block.splitlines() if ln.startswith("### ")]
    assert len(headings) == 4
    order = [h for cat in build_catalog.CATEGORY_ORDER for h in headings if cat.title() in h]
    assert order == headings  # create -> validate -> improve -> ship


def test_category_headings_carry_counts():
    skills = build_catalog.load_skills(REPO)
    block = build_catalog.render(skills, build_catalog.load_meta(REPO), "en")
    for cat in build_catalog.CATEGORY_ORDER:
        n = sum(s["category"] == cat for s in skills)
        assert any(ln.startswith("### ") and cat.title() in ln and f"({n})" in ln
                   for ln in block.splitlines())


def test_every_skill_has_a_try_sentence():
    meta = json.loads((REPO / "scripts" / "catalog_meta.json").read_text(encoding="utf-8"))
    assert sorted(meta) == SKILLS
    for name, entry in meta.items():
        assert isinstance(entry.get("try"), str) and len(entry["try"].strip()) > 10, name


def test_short_description_comes_from_frontmatter():
    for s in build_catalog.load_skills(REPO):
        short = build_catalog.short_description(s["description"])
        assert short and len(short) <= build_catalog.SHORT_MAX + 1
        assert s["description"].startswith(short.rstrip(".…"))


def test_short_description_truncates_at_word_boundary():
    long = "Score any survey " + "word " * 60 + "end."
    short = build_catalog.short_description(long)
    assert short.endswith("…") and len(short) <= build_catalog.SHORT_MAX + 1
    assert long.startswith(short[:-1]) and not short[:-1].endswith(" ")


def test_build_then_check_is_stable(tmp_path):
    root = _copy_root(tmp_path)
    assert build_catalog.main(["--root", str(root)]) == 0
    first = [(root / n).read_text(encoding="utf-8") for n in READMES]
    assert build_catalog.main(["--root", str(root)]) == 0
    assert [(root / n).read_text(encoding="utf-8") for n in READMES] == first
    assert build_catalog.main(["--root", str(root), "--check"]) == 0


def test_check_detects_drift_and_missing_markers(tmp_path):
    root = _copy_root(tmp_path)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    readme.write_text(text.replace("survey-lint", "survey-lnit", 1), encoding="utf-8")
    assert build_catalog.main(["--root", str(root), "--check"]) == 1
    readme.write_text(text.replace(build_catalog.START, ""), encoding="utf-8")
    assert build_catalog.main(["--root", str(root), "--check"]) == 1
    assert build_catalog.main(["--root", str(root)]) == 1  # cannot write without markers


def test_missing_try_sentence_is_an_error(tmp_path):
    root = _copy_root(tmp_path)
    meta_path = root / "scripts" / "catalog_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    del meta["survey-fix"]
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    assert build_catalog.main(["--root", str(root), "--check"]) == 1


# --- prompts ----------------------------------------------------------------------------------

@pytest.mark.parametrize("name", SKILLS)
def test_prompt_file_exists_and_fits(name):
    path = REPO / "prompts" / f"{name}.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert len(text.splitlines()) <= build_prompts.MAX_LINES
    assert text.startswith(f"# {name}")
    assert "No-Python fallback" in text
    assert "\n---\nname:" not in text  # frontmatter stripped


def test_score_prompt_inlines_judging_guide_and_manual_tally():
    text = (REPO / "prompts" / "survey-score.md").read_text(encoding="utf-8")
    assert "## Reference: judging-guide.md" in text
    assert "## Reference: scoring.md (Manual tally fallback)" in text
    assert "Points = `100 − 6·H − 3·M − 1·L`" in text
    assert "## Reference: rubric.md" not in text  # large synced file excluded


def test_prompts_exclude_synced_shared_files():
    for name in SKILLS:
        manifest = json.loads((REPO / "skills" / name / "skill.manifest.json").read_text(encoding="utf-8"))
        text = (REPO / "prompts" / f"{name}.md").read_text(encoding="utf-8")
        for ref in manifest.get("references", []):
            assert f"## Reference: {ref}\n" not in text, (name, ref)


def test_prompt_build_then_check_is_stable(tmp_path):
    root = _copy_root(tmp_path)
    assert build_prompts.main(["--root", str(root)]) == 0
    files = sorted((root / "prompts").glob("*.md"))
    assert [f.stem for f in files] == SKILLS
    first = [f.read_text(encoding="utf-8") for f in files]
    assert build_prompts.main(["--root", str(root)]) == 0
    assert [f.read_text(encoding="utf-8") for f in files] == first
    assert build_prompts.main(["--root", str(root), "--check"]) == 0


def test_prompt_check_detects_drift_and_strays(tmp_path):
    root = _copy_root(tmp_path)
    assert build_prompts.main(["--root", str(root)]) == 0
    target = root / "prompts" / "survey-lint.md"
    target.write_text(target.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
    assert build_prompts.main(["--root", str(root), "--check"]) == 1
    assert build_prompts.main(["--root", str(root)]) == 0
    (root / "prompts" / "old-skill.md").write_text("stale\n", encoding="utf-8")
    assert build_prompts.main(["--root", str(root), "--check"]) == 1
