#!/usr/bin/env python3
"""Preview or install Northstar CI templates into a product repository."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--service", choices=["github", "gitlab"], required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    assets = Path(__file__).parents[1] / "assets" / args.service
    if args.service == "github":
        mappings = [(source, root / ".github" / "workflows" / source.name) for source in sorted(assets.glob("*.yml"))]
    else:
        mappings = [(assets / "northstar.gitlab-ci.yml", root / ".gitlab-ci.northstar.yml")]
    conflicts = [str(target) for _, target in mappings if target.exists() and not args.force]
    preview = {"service": args.service, "files": [str(target.relative_to(root)) for _, target in mappings], "conflicts": conflicts}
    print(json.dumps(preview, indent=2))
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
