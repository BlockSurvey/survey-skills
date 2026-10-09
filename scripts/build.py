#!/usr/bin/env python3
"""Sync shared knowledge files into each skill.

For every skills/<skill>/skill.manifest.json, copy the listed files from
shared/ (references) and shared/scripts/ (scripts) into the skill directory,
byte for byte. With --check nothing is written; drift is reported instead.
"""
import argparse
import json
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = "skill.manifest.json"
# manifest key -> (source dir under root, destination dir under the skill)
KINDS = {"references": ("shared", "references"), "scripts": ("shared/scripts", "scripts")}


def _load_manifest(skill_dir, label):
    try:
        data = json.loads((skill_dir / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"{label}: cannot read {MANIFEST}: {exc}"]
    if not isinstance(data, dict):
        return None, [f"{label}: {MANIFEST} must be a JSON object"]
    problems = []
    for key in data:
        if key not in KINDS:
            problems.append(f"{label}: {MANIFEST} has unknown key '{key}'")
    for key in KINDS:
        names = data.get(key, [])
        if not isinstance(names, list) or not all(isinstance(n, str) and n for n in names):
            problems.append(f"{label}: '{key}' in {MANIFEST} must be a list of file names")
        elif any("/" in n or "\\" in n or n.startswith(".") for n in names):
            problems.append(f"{label}: '{key}' in {MANIFEST} must list bare file names")
    return (None if problems else data), problems


def _sync_skill(root, skill_dir, check):
    label = f"skills/{skill_dir.name}"
    manifest, problems = _load_manifest(skill_dir, label)
    if manifest is None:
        return problems, 0
    total = 0
    for key, (src_rel, dst_rel) in KINDS.items():
        for name in manifest.get(key, []):
            total += 1
            src = root / src_rel / name
            dst = skill_dir / dst_rel / name
            shown = f"{label}/{dst_rel}/{name}"
            if not src.is_file():
                problems.append(f"{label}: source file {src_rel}/{name} not found (listed under '{key}')")
                continue
            data = src.read_bytes()
            in_sync = dst.is_file() and dst.read_bytes() == data
            if in_sync:
                continue
            if check:
                problems.append(f"{shown} is {'out of date' if dst.exists() else 'missing'} "
                                f"(run: python scripts/build.py)")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(data)
    return problems, total


def sync(root, check=False, _out=None):
    """Sync (or with check=True, verify) all skills under root. Returns problems."""
    root = Path(root)
    problems = []
    skills_dir = root / "skills"
    dirs = sorted(p for p in skills_dir.iterdir()
                  if p.is_dir() and (p / MANIFEST).is_file()) if skills_dir.is_dir() else []
    for d in dirs:
        found, total = _sync_skill(root, d, check)
        problems.extend(found)
        if _out is not None:
            status = "FAIL" if found else ("in sync" if check else "synced")
            _out(f"{d.name}: {status} ({total} file(s))")
    if not dirs and _out is not None:
        _out("no skills found (no skills/*/skill.manifest.json)")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="copy nothing; exit 1 if any copy is missing or differs")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root")
    args = ap.parse_args(argv)
    problems = sync(args.root, check=args.check, _out=print)
    for p in problems:
        print(f"error: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
