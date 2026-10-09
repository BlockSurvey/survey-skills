#!/usr/bin/env python3
"""Render the skills catalog tables into README.md and README.zh-CN.md.

Reads every skills/*/SKILL.md frontmatter (name, description, metadata.category)
plus scripts/catalog_meta.json ({skill: {"try": "...", "rank": 1}}; rank is optional
and orders skills inside a category, lowest first, then by name) and writes one table per
category between the catalog markers. With --check nothing is written; exit 1 if
a README block differs from what would be generated.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from validate_skills import FrontmatterError, parse_frontmatter, split_skill

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
START = "<!-- catalog:start -->"
END = "<!-- catalog:end -->"
META = Path("scripts") / "catalog_meta.json"
CATEGORY_ORDER = ("create", "validate", "improve", "ship")
# category -> (emoji, English blurb)
CATEGORIES = {
    "create": ("✍️", "Start from a brief or a proven template."),
    "validate": ("✅", "Know if it is ready before anyone sees it."),
    "improve": ("🔧", "Fix the problems, route the right people, test it on simulated respondents."),
    "ship": ("🚀", "Get people to start it, then get it into your survey tool."),
}
LANG = {
    "en": {"README": "README.md", "summary": "**{n} skills** in {c} categories. Each one is a folder with a `SKILL.md`.",
           "cols": ("Skill", "What it does", "Try saying"), "names": {}},
    "zh": {"README": "README.zh-CN.md", "summary": "**{n} 个技能**，分为 {c} 类。每个技能是一个含 `SKILL.md` 的文件夹。",
           "cols": ("技能 Skill", "功能 What it does", "试着说 Try saying"),
           "names": {"create": "创建", "validate": "验证", "improve": "改进", "ship": "发布"}},
}


class CatalogError(Exception):
    pass


def load_skills(root):
    """Return [{name, description, category}] for every skills/*/SKILL.md, sorted by name."""
    skills = []
    skills_dir = Path(root) / "skills"
    for d in sorted(p for p in skills_dir.iterdir() if (p / "SKILL.md").is_file()):
        try:
            fm_lines, _ = split_skill((d / "SKILL.md").read_text(encoding="utf-8"))
            fm = parse_frontmatter(fm_lines)
        except FrontmatterError as exc:
            raise CatalogError(f"skills/{d.name}/SKILL.md: {exc}")
        category = (fm.get("metadata") or {}).get("category")
        if category not in CATEGORY_ORDER:
            raise CatalogError(f"skills/{d.name}: metadata.category '{category}' is not one of {CATEGORY_ORDER}")
        skills.append({"name": fm.get("name", d.name), "description": fm.get("description", ""),
                       "category": category})
    return skills


def load_meta(root):
    path = Path(root) / META
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogError(f"cannot read {META}: {exc}")
    if not isinstance(data, dict):
        raise CatalogError(f"{META} must be a JSON object")
    return data


SHORT_MAX = 160


def short_description(desc):
    """Catalog blurb: first sentence of the description, cut at the first ' - ' aside,
    then truncated at a word boundary to SHORT_MAX characters with an ellipsis."""
    first = re.split(r"(?<=[.!?])\s", desc.strip(), maxsplit=1)[0]
    first = first.split(" - ", 1)[0].strip()
    if len(first) > SHORT_MAX:
        cut = first[:SHORT_MAX].rsplit(" ", 1)[0].rstrip(",;:")
        return cut + "…"
    return first if first.endswith((".", "!", "?")) else first + "."


def _cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


def render(skills, meta, lang="en", root=None):
    """Return the markdown that goes between the catalog markers."""
    L = LANG[lang]
    missing = [s["name"] for s in skills
               if not isinstance(meta.get(s["name"], {}).get("try"), str) or not meta[s["name"]]["try"].strip()]
    if missing:
        raise CatalogError(f"{META}: no 'try' sentence for {', '.join(missing)}")
    by_cat = {c: [s for s in skills if s["category"] == c] for c in CATEGORY_ORDER}
    used = [c for c in CATEGORY_ORDER if by_cat[c]]
    out = [L["summary"].format(n=len(skills), c=len(used)), ""]
    for c in used:
        emoji, blurb = CATEGORIES[c]
        local = L["names"].get(c)
        title = f"{local} {c.title()}" if local else c.title()
        out += [f"### {emoji} {title} ({len(by_cat[c])})", "", f"_{blurb}_", "",
                f"| {' | '.join(L['cols'])} |", "| --- | --- | --- |"]
        for s in sorted(by_cat[c], key=lambda s: (meta[s["name"]].get("rank", 99), s["name"])):
            what = _cell(short_description(s["description"]))
            gif = Path("assets") / "previews" / f"{s['name']}.gif"
            if root is not None and (Path(root) / gif).is_file():
                what += f"<br><img src=\"{gif.as_posix()}\" alt=\"{s['name']} preview\" width=\"360\">"
            link = f"[**{s['name']}**](skills/{s['name']}/SKILL.md)"
            out.append(f"| {link} | {what} | “{_cell(meta[s['name']]['try'].strip())}” |")
        out.append("")
    return "\n".join(out).rstrip("\n")


def splice(text, block):
    """Replace the content between the markers; raises CatalogError if they are missing."""
    i, j = text.find(START), text.find(END)
    if i < 0 or j < 0 or j < i:
        raise CatalogError(f"markers {START} / {END} not found in order")
    return text[:i + len(START)] + "\n" + block + "\n" + text[j:]


def run(root, check=False, out=print):
    root = Path(root)
    skills = load_skills(root)
    meta = load_meta(root)
    problems = []
    for lang, L in LANG.items():
        path = root / L["README"]
        try:
            text = path.read_text(encoding="utf-8")
            new = splice(text, render(skills, meta, lang, root))
        except OSError as exc:
            problems.append(f"{L['README']}: {exc}")
            continue
        except CatalogError as exc:
            problems.append(f"{L['README']}: {exc}")
            continue
        if new == text:
            out(f"{L['README']}: catalog in sync ({len(skills)} skills)")
        elif check:
            problems.append(f"{L['README']}: catalog is out of date (run: python scripts/build_catalog.py)")
        else:
            path.write_text(new, encoding="utf-8")
            out(f"{L['README']}: catalog written ({len(skills)} skills)")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if a README catalog differs")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root")
    args = ap.parse_args(argv)
    try:
        problems = run(args.root, check=args.check)
    except CatalogError as exc:
        problems = [str(exc)]
    for p in problems:
        print(f"error: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
