#!/usr/bin/env python3
"""Opt-in live contract against a dedicated GitHub sandbox repository. Creates, comments on, and closes one temporary issue."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path

ENGINE = Path(__file__).parents[1] / "scripts" / "northstar.py"
SPEC = importlib.util.spec_from_file_location("northstar_engine", ENGINE)
assert SPEC and SPEC.loader
ns = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ns
SPEC.loader.exec_module(ns)


def main() -> int:
    if os.environ.get("NORTHSTAR_LIVE_CONTRACTS") != "1":
        print("SKIP: set NORTHSTAR_LIVE_CONTRACTS=1 and NORTHSTAR_GITHUB_SANDBOX=owner/repo for a dedicated sandbox")
        return 0
    repo = os.environ["NORTHSTAR_GITHUB_SANDBOX"]
    marker = f"[northstar-contract] {uuid.uuid4()}"
    created = json.loads(ns.command(["gh", "api", "--method", "POST", f"repos/{repo}/issues", "--input", "-"], {"title": marker, "body": "Northstar live contract; safe to close."}))
    url = created["html_url"]
    try:
        viewed = json.loads(ns.command(["gh", "issue", "view", url, "--json", "state,title,url"]))
        if viewed["title"] != marker or viewed["state"].lower() != "open":
            raise RuntimeError(f"unexpected GitHub issue state: {viewed}")
        ns.command(["gh", "issue", "comment", url, "--body", f"[northstar-contract:{marker}] update"])
    finally:
        ns.command(["gh", "issue", "close", url, "--comment", f"[northstar-contract:{marker}] cleanup"])
    print("OK: live GitHub contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
