#!/usr/bin/env python3
"""Preview or install Northstar's engine and GitHub workflow templates into a product repository.

The engine is vendored to roadmap/bin/ so CI does not depend on where the skills installer put the skill.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SKILLS = Path(__file__).parents[2]
ENGINE_FILES = [SKILLS / "northstar" / "scripts" / "northstar.py", SKILLS / "northstar" / "scripts" / "northstar_admin.py"]
WORKFLOWS = sorted((SKILLS / "setup-northstar" / "assets" / "github").glob("*.yml"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--workflow", action="append", default=[], help="install only these workflow names (repeatable); default installs all")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true", help="overwrite existing workflow files after the user approved each conflict")
    args = parser.parse_args()
    root = args.root.resolve()
    workflows = [path for path in WORKFLOWS if not args.workflow or path.stem in args.workflow or path.stem.removeprefix("northstar-") in args.workflow]
    mappings = [(source, root / "roadmap" / "bin" / source.name) for source in ENGINE_FILES]
    mappings += [(source, root / ".github" / "workflows" / source.name) for source in workflows]
    # The engine is always refreshed; only workflow files count as conflicts because teams edit them.
    conflicts = [str(target.relative_to(root)) for source, target in mappings if target.exists() and target.parent.name == "workflows" and not args.force]
    print(json.dumps({"files": [str(target.relative_to(root)) for _, target in mappings], "conflicts": conflicts}, indent=2))
    if not args.apply:
        return 0
    if conflicts:
        print("ERROR: refusing to overwrite existing workflow files without --force", file=sys.stderr)
        return 1
    for source, target in mappings:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    ignore = root / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    if "roadmap/.northstar.lock" not in text.splitlines():
        ignore.write_text(text.rstrip() + "\nroadmap/.northstar.lock\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
