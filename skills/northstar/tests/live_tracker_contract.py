#!/usr/bin/env python3
"""Opt-in live contracts for dedicated GitHub/GitLab sandbox projects."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import urllib.parse
import uuid
from pathlib import Path

ENGINE = Path(__file__).parents[1] / "scripts" / "northstar.py"
SPEC = importlib.util.spec_from_file_location("northstar_engine", ENGINE)
assert SPEC and SPEC.loader
ns = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ns
SPEC.loader.exec_module(ns)


def github(repo: str, marker: str) -> None:
    created = json.loads(ns.command(["gh", "api", "--method", "POST", f"repos/{repo}/issues", "--input", "-"], {"title": marker, "body": "Northstar live contract; safe to close."}))
    url = created["html_url"]
    try:
        viewed = json.loads(ns.command(["gh", "issue", "view", url, "--json", "state,title,url"]))
        if viewed["title"] != marker or viewed["state"].lower() != "open":
            raise RuntimeError(f"unexpected GitHub issue state: {viewed}")
        ns.command(["gh", "issue", "comment", url, "--body", f"[northstar-contract:{marker}] update"])
    finally:
        ns.command(["gh", "issue", "close", url, "--comment", f"[northstar-contract:{marker}] cleanup"])


def gitlab(project: str, marker: str) -> None:
    endpoint = f"projects/{urllib.parse.quote(project, safe='')}/issues"
    created = json.loads(ns.command(["glab", "api", "--method", "POST", endpoint, "--input", "-"], {"title": marker, "description": "Northstar live contract; safe to close."}))
    iid = str(created["iid"])
    try:
        viewed = json.loads(ns.command(["glab", "api", f"{endpoint}/{iid}"]))
        if viewed["title"] != marker or viewed["state"].lower() not in {"open", "opened"}:
            raise RuntimeError(f"unexpected GitLab issue state: {viewed}")
        ns.command(["glab", "issue", "note", iid, "-R", project, "-m", f"[northstar-contract:{marker}] update"])
    finally:
        ns.command(["glab", "issue", "close", iid, "-R", project])


def main() -> int:
    if os.environ.get("NORTHSTAR_LIVE_CONTRACTS") != "1":
        print("SKIP: set NORTHSTAR_LIVE_CONTRACTS=1 for dedicated sandbox projects")
        return 0
    marker = f"[northstar-contract] {uuid.uuid4()}"
    github_repo = os.environ.get("NORTHSTAR_GITHUB_SANDBOX", "")
    gitlab_project = os.environ.get("NORTHSTAR_GITLAB_SANDBOX", "")
    if not github_repo and not gitlab_project:
        raise RuntimeError("set NORTHSTAR_GITHUB_SANDBOX and/or NORTHSTAR_GITLAB_SANDBOX")
    if github_repo:
        github(github_repo, marker)
    if gitlab_project:
        gitlab(gitlab_project, marker)
    print("OK: live tracker contracts passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
