#!/usr/bin/env python3
"""Validate skills/*/SKILL.md against the Agent Skills standard plus project rules.

Stdlib only. The frontmatter parser supports `key: value` lines, quoted strings
and a single one-level nested `metadata:` block; anything else is rejected.
"""
import argparse
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
CATEGORIES = {"create", "validate", "improve", "ship"}
MAX_BODY_LINES = 500
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$")


class FrontmatterError(ValueError):
    pass


def _scalar(raw, where):
    raw = raw.strip()
    if not raw:
        raise FrontmatterError(f"{where}: empty value")
    if raw[0] in "\"'":
        q = raw[0]
        if len(raw) < 2 or raw[-1] != q:
            raise FrontmatterError(f"{where}: unterminated quoted string")
        inner = raw[1:-1]
        if q in inner and q == "'" and "''" not in inner:
            raise FrontmatterError(f"{where}: unescaped quote in string")
        if q == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        else:
            inner = inner.replace("''", "'")
        return inner
    if raw[0] in "[{|>&*!%@`" or raw.startswith("- "):
        raise FrontmatterError(f"{where}: unsupported YAML syntax '{raw[0]}' (use a plain or quoted string)")
    if " #" in raw:
        raise FrontmatterError(f"{where}: inline comments are not supported")
    return raw


def parse_frontmatter(lines):
    """Parse frontmatter lines (without the --- fences) into a dict."""
    data = {}
    nested = None  # key of the open nested block
    for n, line in enumerate(lines, 2):
        where = f"frontmatter line {n}"
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indented = line[0] in " \t"
        m = KEY_RE.match(line.strip())
        if not m:
            raise FrontmatterError(f"{where}: unsupported syntax '{line.strip()}'")
        key, val = m.group(1), m.group(2)
        if indented:
            if nested is None:
                raise FrontmatterError(f"{where}: unexpected indentation")
            if val is None:
                raise FrontmatterError(f"{where}: nesting deeper than one level is not supported")
            if key in data[nested]:
                raise FrontmatterError(f"{where}: duplicate key '{key}'")
            data[nested][key] = _scalar(val, where)
            continue
        if key in data:
            raise FrontmatterError(f"{where}: duplicate key '{key}'")
        if val is None or not val.strip():
            if key != "metadata":
                raise FrontmatterError(f"{where}: '{key}' has no value (only 'metadata' may be a block)")
            data[key] = {}
            nested = key
        else:
            nested = None
            data[key] = _scalar(val, where)
    return data


def split_skill(text):
    """Return (frontmatter_lines, body_lines); raises FrontmatterError."""
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("frontmatter missing (file must start with '---')")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], lines[i + 1:]
    raise FrontmatterError("frontmatter not closed (missing second '---')")


def _check_links(skill_dir, body):
    problems = []
    in_fence = False
    seen = set()
    for line in body:
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK_RE.findall(line):
            if target.startswith(("http", "#", "mailto:")) or target in seen:
                continue
            seen.add(target)
            path = target.split("#", 1)[0]
            if not path:
                continue
            parts = [p for p in path.split("/") if p not in ("", ".")]
            if ".." in parts or path.startswith("/"):
                problems.append(f"link '{target}' must stay inside the skill directory")
            elif len(parts) > 2:
                problems.append(f"link '{target}' is too deep (at most one directory level, e.g. references/x.md)")
            elif not (skill_dir / path).is_file():
                problems.append(f"link '{target}' does not resolve to an existing file")
    return problems


def validate_skill(skill_dir):
    problems = []
    try:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm_lines, body = split_skill(text)
        fm = parse_frontmatter(fm_lines)
    except OSError as exc:
        return [f"cannot read SKILL.md: {exc}"]
    except FrontmatterError as exc:
        return [str(exc)]

    name = fm.get("name")
    if not isinstance(name, str) or not name:
        problems.append("name is required")
    else:
        if len(name) > 64:
            problems.append("name must be 1-64 characters")
        if not NAME_RE.match(name):
            problems.append(f"name '{name}' must be lowercase letters/digits separated by single hyphens")
        if name != skill_dir.name:
            problems.append(f"name '{name}' must equal the directory name '{skill_dir.name}'")
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        problems.append("description is required and must be non-empty")
    elif len(desc) > 1024:
        problems.append(f"description is {len(desc)} characters (max 1024)")
    if fm.get("license") != "MIT":
        problems.append("license must be MIT")
    meta = fm.get("metadata")
    if not isinstance(meta, dict):
        problems.append("metadata block is required (author, version, category)")
        meta = {}
    if meta.get("author") != "blocksurvey":
        problems.append("metadata.author must be blocksurvey")
    if not VERSION_RE.match(str(meta.get("version", ""))):
        problems.append("metadata.version must look like 1.2.3")
    if meta.get("category") not in CATEGORIES:
        problems.append(f"metadata.category must be one of {sorted(CATEGORIES)}")

    if len(body) > MAX_BODY_LINES:
        problems.append(f"body is {len(body)} lines (max {MAX_BODY_LINES})")
    if not any(re.match(r"^##\s+Next\s*$", ln) for ln in body):
        problems.append("body must contain a '## Next' heading")
    problems.extend(_check_links(skill_dir, body))
    return problems


def validate(skills_dir):
    """Validate every <skills_dir>/*/SKILL.md. Returns {skill: [problems]}."""
    skills_dir = Path(skills_dir)
    if not skills_dir.is_dir():
        return {}
    return {d.name: validate_skill(d) for d in sorted(skills_dir.iterdir())
            if d.is_dir() and (d / "SKILL.md").is_file()}


def render_table(results):
    rows = [("skill", "status", "problems")]
    for skill, probs in results.items():
        rows.append((skill, "FAIL" if probs else "ok", "; ".join(probs) or "-"))
    w = max(len(r[0]) for r in rows)
    return "\n".join(f"{a.ljust(w)} | {b.ljust(6)} | {c}" for a, b, c in rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root")
    ap.add_argument("--skills-dir", type=Path, default=None, help="skills directory (default: <root>/skills)")
    args = ap.parse_args(argv)
    results = validate(args.skills_dir or args.root / "skills")
    if not results:
        print("no skills found (no skills/*/SKILL.md)")
        return 0
    print(render_table(results))
    return 1 if any(results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
