"""Tests for scripts/build.py and scripts/validate_skills.py."""
import shutil
from pathlib import Path

import pytest

from build import sync
from validate_skills import validate

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "skills"
SAMPLE = "sample-skill"


def _make_root(tmp_path, with_skill=True):
    """Temp repo root: real shared/ plus a copy of the fixture skill."""
    shutil.copytree(REPO / "shared", tmp_path / "shared")
    skills = tmp_path / "skills"
    skills.mkdir()
    if with_skill:
        shutil.copytree(FIXTURES / SAMPLE, skills / SAMPLE)
    return tmp_path


@pytest.fixture
def root(tmp_path):
    r = _make_root(tmp_path)
    assert sync(r) == []
    return r


def _skill_md(root):
    return root / "skills" / SAMPLE / "SKILL.md"


def _edit(root, old, new):
    p = _skill_md(root)
    text = p.read_text(encoding="utf-8")
    assert old in text
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# --- positive: fixture and real skills -------------------------------------

def test_fixture_validates(root):
    assert validate(root / "skills") == {SAMPLE: []}


def test_fixture_sync_check_clean(root):
    assert sync(root, check=True) == []


REAL = sorted(p.name for p in (REPO / "skills").iterdir()
              if (p / "SKILL.md").is_file()) if (REPO / "skills").is_dir() else []


@pytest.mark.parametrize("name", REAL)
def test_real_skill_validates(name):
    assert validate(REPO / "skills")[name] == []


@pytest.mark.parametrize("name", REAL)
def test_real_skill_in_sync(name):
    problems = [p for p in sync(REPO, check=True) if f"skills/{name}/" in p]
    assert problems == []


def test_repo_wide_checks():
    assert sync(REPO, check=True) == []
    assert all(v == [] for v in validate(REPO / "skills").values())


# --- negative: validator ---------------------------------------------------

def _problems(root):
    return validate(root / "skills")[SAMPLE]


def test_name_casing(root):
    _edit(root, "name: sample-skill", "name: Sample-Skill")
    assert any("name" in p for p in _problems(root))


def test_name_must_match_directory(root):
    _edit(root, "name: sample-skill", "name: other-skill")
    assert any("directory" in p for p in _problems(root))


def test_description_too_long(root):
    _edit(root, "description: Checks", "description: " + "x" * 1025 + " Checks")
    assert any("description" in p for p in _problems(root))


def test_missing_next(root):
    _edit(root, "## Next", "## Afterwards")
    assert any("## Next" in p for p in _problems(root))


def test_broken_link(root):
    _edit(root, "references/rubric.md", "references/nope.md")
    assert any("nope.md" in p for p in _problems(root))


def test_nested_link_depth(root):
    d = root / "skills" / SAMPLE / "references" / "a"
    d.mkdir()
    (d / "b.md").write_text("x", encoding="utf-8")
    _edit(root, "references/rubric.md", "references/a/b.md")
    assert any("deep" in p for p in _problems(root))


def test_external_links_ignored(root):
    _edit(root, "## Next", "[a](https://example.com) [b](#x) [c](mailto:a@b.c)\n\n## Next")
    assert _problems(root) == []


def test_wrong_license_and_category(root):
    _edit(root, "license: MIT", "license: GPL")
    _edit(root, "category: validate", "category: other")
    p = _problems(root)
    assert any("license" in x for x in p) and any("category" in x for x in p)


def test_bad_version(root):
    _edit(root, '"1.0.0"', '"1.0"')
    assert any("version" in x for x in _problems(root))


def test_body_too_long(root):
    p = _skill_md(root)
    p.write_text(p.read_text(encoding="utf-8") + "line\n" * 500, encoding="utf-8")
    assert any("500" in x for x in _problems(root))


def test_unclosed_frontmatter(root):
    p = _skill_md(root)
    p.write_text("---\nname: sample-skill\n", encoding="utf-8")
    assert any("frontmatter" in x for x in _problems(root))


def test_missing_frontmatter(root):
    _skill_md(root).write_text("# no frontmatter\n", encoding="utf-8")
    assert any("frontmatter" in x for x in _problems(root))


def test_unsupported_yaml_rejected(root):
    _edit(root, "license: MIT", "license: MIT\ntags: [a, b]")
    assert any("tags" in x or "unsupported" in x for x in _problems(root))


# --- sync ------------------------------------------------------------------

def test_sync_copies_byte_identical(root):
    d = root / "skills" / SAMPLE
    assert (d / "references" / "rubric.md").read_bytes() == (root / "shared" / "rubric.md").read_bytes()
    assert (d / "scripts" / "survey_lint.py").read_bytes() == \
        (root / "shared" / "scripts" / "survey_lint.py").read_bytes()


def test_missing_shared_source(root):
    m = root / "skills" / SAMPLE / "skill.manifest.json"
    m.write_text('{"references": ["nope.md"], "scripts": []}', encoding="utf-8")
    problems = sync(root)
    assert problems and SAMPLE in problems[0] and "nope.md" in problems[0]


def test_check_reports_missing_copy(tmp_path):
    r = _make_root(tmp_path)
    problems = sync(r, check=True)
    assert len(problems) == 2
    assert not (r / "skills" / SAMPLE / "references").exists()


def test_drift_detected_and_repaired(root):
    dest = root / "skills" / SAMPLE / "references" / "rubric.md"
    dest.write_text("drifted", encoding="utf-8")
    assert any("rubric.md" in p for p in sync(root, check=True))
    assert dest.read_text(encoding="utf-8") == "drifted"
    assert sync(root) == []
    assert sync(root, check=True) == []


def test_empty_skills_dir_ok(tmp_path):
    r = _make_root(tmp_path, with_skill=False)
    assert sync(r, check=True) == []
    assert validate(r / "skills") == {}
