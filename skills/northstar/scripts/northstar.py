#!/usr/bin/env python3
"""Deterministic roadmap engine for the Northstar skill."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

HEADER = ["ID", "P", "Status", "Story", "Owner", "Branch", "GitHub", "GitLab", "Wayfinder", "Sync"]
STATUSES = {"Candidate", "Planned", "Ready", "In Progress", "Done", "Deferred", "Retired"}
SYNC_STATES = {"Local", "Synced", "Drift", "Partial", "Error"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
EMPTY = "—"
ID_RE = re.compile(r"RM-(\d{3,})$")
STORY_RE = re.compile(r"As (?:a|an|the) .+?, I want .+?, so that .+?\.?$", re.I)
LINK_RE = re.compile(r"\[(.+)]\((.+)\)$")


class NorthstarError(RuntimeError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def md_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def split_row(line: str) -> list[str]:
    text = line.strip()
    if not (text.startswith("|") and text.endswith("|")):
        raise NorthstarError(f"Invalid Markdown table row: {line}")
    values, current, escaped = [], [], False
    for char in text[1:-1]:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            current.append(char)
            escaped = True
        elif char == "|":
            values.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    values.append("".join(current).strip())
    return values


def render_row(values: list[str]) -> str:
    return "| " + " | ".join(values) + " |"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)
        raise


@contextlib.contextmanager
def workspace_lock(root: Path) -> Iterator[None]:
    lock = root / "roadmap" / ".northstar.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise NorthstarError(f"Another Northstar mutation is active: {lock}") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()} timestamp={now()}\n".encode())
        os.close(descriptor)
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            lock.unlink()


@dataclass
class Roadmap:
    path: Path
    lines: list[str]
    header_index: int
    end_index: int
    items: list[dict[str, str]]

    @classmethod
    def load(cls, path: Path) -> "Roadmap":
        if not path.is_file():
            raise NorthstarError(f"Missing roadmap: {path}")
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if line.strip().startswith("|") and split_row(line) == HEADER:
                break
        else:
            raise NorthstarError("ROADMAP.md does not contain the Northstar table header")
        if index + 1 >= len(lines) or not lines[index + 1].strip().startswith("|"):
            raise NorthstarError("ROADMAP.md is missing its table separator")
        end = index + 2
        items: list[dict[str, str]] = []
        while end < len(lines) and lines[end].strip().startswith("|"):
            values = split_row(lines[end])
            if len(values) != len(HEADER):
                raise NorthstarError(f"Roadmap row {end + 1} has {len(values)} columns; expected {len(HEADER)}")
            items.append(dict(zip(HEADER, values)))
            end += 1
        return cls(path, lines, index, end, items)

    def find(self, item_id: str) -> dict[str, str]:
        for item in self.items:
            if item["ID"] == item_id:
                return item
        raise NorthstarError(f"Unknown roadmap item: {item_id}")

    def save(self) -> None:
        table = [render_row(HEADER), render_row(["---"] * len(HEADER))]
        table.extend(render_row([item[column] for column in HEADER]) for item in self.items)
        lines = self.lines[: self.header_index] + table + self.lines[self.end_index :]
        atomic_write(self.path, "\n".join(lines).rstrip() + "\n")
        self.lines, self.end_index = lines, self.header_index + len(table)


def brief_path(root: Path, item: dict[str, str]) -> Path:
    match = LINK_RE.fullmatch(item["Story"])
    if not match:
        raise NorthstarError(f"{item['ID']}: Story must be a Markdown link to its item brief")
    return root / match.group(2)


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else ""


def field(text: str, name: str) -> str:
    match = re.search(rf"^- {re.escape(name)}:\s*(.*)$", text, re.M)
    return match.group(1).strip() if match else ""


def replace_field(text: str, name: str, value: str) -> str:
    pattern = re.compile(rf"^- {re.escape(name)}:\s*.*$", re.M)
    if not pattern.search(text):
        raise NorthstarError(f"Item brief is missing '- {name}:'")
    return pattern.sub(f"- {name}: {value}", text, count=1)


def append_history(text: str, event: str, actor: str, detail: str) -> str:
    if "## History" not in text:
        raise NorthstarError("Item brief is missing its History section")
    return text.rstrip() + f"\n| {now()} | {md_escape(event)} | {md_escape(actor)} | {md_escape(detail)} |\n"


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        roadmap = Roadmap.load(root / "ROADMAP.md")
    except NorthstarError as exc:
        return [str(exc)]
    seen: set[str] = set()
    previous = 0
    for item in roadmap.items:
        item_id = item["ID"]
        match = ID_RE.fullmatch(item_id)
        if not match or item_id in seen:
            errors.append(f"{item_id}: invalid or duplicate ID")
        elif int(match.group(1)) <= previous:
            errors.append(f"{item_id}: IDs must be ascending")
        else:
            previous = int(match.group(1))
            seen.add(item_id)
        if item["P"] not in PRIORITIES:
            errors.append(f"{item_id}: invalid priority {item['P']!r}")
        if item["Status"] not in STATUSES:
            errors.append(f"{item_id}: invalid work status {item['Status']!r}")
        if item["Sync"] not in SYNC_STATES:
            errors.append(f"{item_id}: invalid sync state {item['Sync']!r}")
        try:
            path = brief_path(root, item)
        except NorthstarError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append(f"{item_id}: missing item brief {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        story = section(text, "User story")
        if not STORY_RE.fullmatch(" ".join(story.split())):
            errors.append(f"{item_id}: invalid or missing As a/an/the … I want … so that … user story")
        criteria = re.findall(r"^- \[([ xX])] .+$", section(text, "Acceptance criteria"), re.M)
        if not criteria:
            errors.append(f"{item_id}: at least one checkbox acceptance criterion is required")
        if item["Status"] == "In Progress":
            for column in ("Owner", "Branch", "Wayfinder"):
                if item[column] == EMPTY:
                    errors.append(f"{item_id}: In Progress requires {column}")
        if item["Status"] == "Done":
            if any(value == " " for value in criteria):
                errors.append(f"{item_id}: Done requires all acceptance criteria checked")
            graphify = field(text, "Graphify")
            if not (graphify.startswith("Updated:") or graphify.startswith("Verified-no-change:")):
                errors.append(f"{item_id}: Done requires Graphify update evidence")
    return errors


def init_workspace(root: Path) -> None:
    roadmap = root / "ROADMAP.md"
    config = root / "roadmap" / "northstar.toml"
    audit = root / "roadmap" / "audit.md"
    if roadmap.exists():
        raise NorthstarError(f"Refusing to overwrite existing {roadmap}")
    atomic_write(roadmap, "# Product roadmap\n\n" + render_row(HEADER) + "\n" + render_row(["---"] * len(HEADER)) + "\n")
    atomic_write(config, CONFIG_TEMPLATE)
    atomic_write(audit, AUDIT_TEMPLATE)


def next_id(roadmap: Roadmap) -> str:
    numbers = [int(match.group(1)) for item in roadmap.items if (match := ID_RE.fullmatch(item["ID"]))]
    return f"RM-{max(numbers, default=0) + 1:03d}"


def new_brief(item_id: str, title: str, priority: str, story: str, criteria: list[str], origin: str, origin_url: str) -> str:
    checks = "\n".join(f"- [ ] {value.strip()}" for value in criteria)
    return f"""# {item_id} — {title}

## User story

{story.rstrip('.') + '.'}

## Acceptance criteria

{checks}

## Planning

- Priority: {priority}
- Dependencies: None
- Target: Optional
- Origin: {origin}
- Origin URL: {origin_url or EMPTY}

## Execution

- Owner: {EMPTY}
- Collaborators: {EMPTY}
- Branch: {EMPTY}
- GitHub: {EMPTY}
- GitLab: {EMPTY}
- Wayfinder: {EMPTY}
- Graphify: Pending

## Completion evidence

- Pull request / merge request: {EMPTY}
- Roadmap and trackers updated: No

## History

| Timestamp | Event | Actor | Detail |
|---|---|---|---|
| {now()} | Created | northstar | {md_escape(origin)} roadmap item. |
"""


def audit(root: Path, item_id: str, event: str, old: str, new: str, actor: str, branch: str, detail: str) -> None:
    path = root / "roadmap" / "audit.md"
    if not path.exists():
        atomic_write(path, AUDIT_TEMPLATE)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(render_row([now(), item_id, event, old, new, actor, branch or EMPTY, md_escape(detail)]) + "\n")


def load_config(root: Path) -> dict[str, Any]:
    path = root / "roadmap" / "northstar.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as stream:
        return tomllib.load(stream)


def command(args: list[str], stdin: dict[str, Any] | None = None) -> str:
    process = subprocess.run(
        args,
        input=json.dumps(stdin) if stdin is not None else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode:
        raise NorthstarError(f"{' '.join(args[:3])} failed: {process.stderr.strip()}")
    return process.stdout.strip()


def enabled(config: dict[str, Any], service: str) -> bool:
    return bool(config.get(service, {}).get("enabled", False))


def identity(config: dict[str, Any], owner: str, service: str) -> str:
    login = config.get("identities", {}).get(owner, {}).get(service)
    if not login:
        raise NorthstarError(f"No {service} identity mapping for owner {owner!r}")
    return str(login)


def github_issue_parts(url: str) -> tuple[str, str]:
    match = re.search(r"github\.com/([^/]+/[^/]+)/issues/(\d+)", url)
    if not match:
        raise NorthstarError(f"Invalid GitHub issue URL: {url}")
    return match.group(1), match.group(2)


def gitlab_iid(url: str) -> str:
    match = re.search(r"/-/issues/(\d+)", url)
    if not match:
        raise NorthstarError(f"Invalid GitLab issue URL: {url}")
    return match.group(1)


def create_remotes(config: dict[str, Any], item: dict[str, str], brief: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    title = LINK_RE.fullmatch(item["Story"]).group(1)  # validated before mutation
    body = f"Northstar item: `{item['ID']}`\n\n{section(brief, 'User story')}\n\n## Acceptance criteria\n{section(brief, 'Acceptance criteria')}"
    if enabled(config, "github") and item["GitHub"] == EMPTY:
        try:
            repo = config["github"]["repository"]
            output = command(["gh", "api", "--method", "POST", f"repos/{repo}/issues", "--input", "-"], {"title": f"[{item['ID']}] {title}", "body": body})
            url = json.loads(output)["html_url"]
            project = config["github"].get("project_title")
            if project:
                command(["gh", "issue", "edit", url, "--add-project", str(project)])
            item["GitHub"] = f"[#{url.rsplit('/', 1)[-1]}]({url})"
            results.append({"service": "github", "status": "ok", "url": url})
        except Exception as exc:
            results.append({"service": "github", "status": "error", "detail": str(exc)})
    if enabled(config, "gitlab") and item["GitLab"] == EMPTY:
        try:
            project = config["gitlab"]["project"]
            endpoint = f"projects/{urllib.parse.quote(project, safe='')}/issues"
            output = command(["glab", "api", "--method", "POST", endpoint, "--input", "-"], {"title": f"[{item['ID']}] {title}", "description": body})
            data = json.loads(output)
            url = data["web_url"]
            item["GitLab"] = f"[#{data['iid']}]({url})"
            results.append({"service": "gitlab", "status": "ok", "url": url})
        except Exception as exc:
            results.append({"service": "gitlab", "status": "error", "detail": str(exc)})
    return results


def mark_import(config: dict[str, Any], item: dict[str, str], origin: str) -> list[dict[str, str]]:
    message = f"[northstar:{item['ID']}] This work was created outside Northstar and imported into the canonical ROADMAP.md. Future planning changes are governed by Northstar."
    try:
        if origin == "github":
            url = LINK_RE.fullmatch(item["GitHub"]).group(2)
            command(["gh", "issue", "comment", url, "--body", message])
        else:
            url = LINK_RE.fullmatch(item["GitLab"]).group(2)
            command(["glab", "issue", "note", gitlab_iid(url), "-R", config["gitlab"]["project"], "-m", message])
        return [{"service": origin, "status": "ok", "url": url}]
    except Exception as exc:
        return [{"service": origin, "status": "error", "detail": str(exc)}]


def update_remotes(config: dict[str, Any], item: dict[str, str], event: str, owner: str, previous: str = "", detail: str = "") -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    marker = f"[northstar:{item['ID']}] {event}: {detail}".strip()
    if item["GitHub"] != EMPTY:
        try:
            url = LINK_RE.fullmatch(item["GitHub"]).group(2)
            if event in {"claimed", "handoff"}:
                login = identity(config, owner, "github")
                args = ["gh", "issue", "edit", url, "--add-assignee", login]
                if previous:
                    args.extend(["--remove-assignee", identity(config, previous, "github")])
                command(args)
                command(["gh", "issue", "comment", url, "--body", marker])
            elif event == "closed":
                command(["gh", "issue", "close", url, "--comment", marker])
            else:
                command(["gh", "issue", "comment", url, "--body", marker])
            results.append({"service": "github", "status": "ok", "url": url})
        except Exception as exc:
            results.append({"service": "github", "status": "error", "detail": str(exc)})
    if item["GitLab"] != EMPTY:
        try:
            url = LINK_RE.fullmatch(item["GitLab"]).group(2)
            project = config["gitlab"]["project"]
            iid = gitlab_iid(url)
            if event in {"claimed", "handoff"}:
                login = identity(config, owner, "gitlab")
                command(["glab", "issue", "update", iid, "-R", project, "--assignee", login])
                command(["glab", "issue", "note", iid, "-R", project, "-m", marker])
            elif event == "closed":
                command(["glab", "issue", "note", iid, "-R", project, "-m", marker])
                command(["glab", "issue", "close", iid, "-R", project])
            else:
                command(["glab", "issue", "note", iid, "-R", project, "-m", marker])
            results.append({"service": "gitlab", "status": "ok", "url": url})
        except Exception as exc:
            results.append({"service": "gitlab", "status": "error", "detail": str(exc)})
    return results


def sync_state(results: list[dict[str, str]]) -> str:
    if not results:
        return "Local"
    successes = sum(result["status"] == "ok" for result in results)
    if successes == len(results):
        return "Synced"
    return "Partial" if successes else "Error"


def journal(root: Path, item_id: str, event: str, results: list[dict[str, str]]) -> None:
    stamp = now().replace(":", "").replace("-", "")
    path = root / "roadmap" / "journal" / f"{stamp}-{item_id}-{event}.json"
    atomic_write(path, json.dumps({"timestamp": now(), "item": item_id, "event": event, "results": results}, indent=2) + "\n")


def inspect_remotes(config: dict[str, Any], item: dict[str, str]) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    if item["GitHub"] != EMPTY:
        try:
            url = LINK_RE.fullmatch(item["GitHub"]).group(2)
            data = json.loads(command(["gh", "issue", "view", url, "--json", "state,assignees,title,url"]))
            snapshots.append({"service": "github", "status": "ok", "url": url, "state": data["state"].lower(), "assignees": [entry["login"] for entry in data.get("assignees", [])], "title": data["title"]})
        except Exception as exc:
            snapshots.append({"service": "github", "status": "error", "detail": str(exc)})
    if item["GitLab"] != EMPTY:
        try:
            url = LINK_RE.fullmatch(item["GitLab"]).group(2)
            project = config["gitlab"]["project"]
            endpoint = f"projects/{urllib.parse.quote(project, safe='')}/issues/{gitlab_iid(url)}"
            data = json.loads(command(["glab", "api", endpoint]))
            snapshots.append({"service": "gitlab", "status": "ok", "url": url, "state": data["state"].lower(), "assignees": [entry["username"] for entry in data.get("assignees", [])], "title": data["title"]})
        except Exception as exc:
            snapshots.append({"service": "gitlab", "status": "error", "detail": str(exc)})
    return snapshots


def reconciliation_report(config: dict[str, Any], item: dict[str, str], snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    expected_state = "closed" if item["Status"] == "Done" else "open"
    differences: list[dict[str, str]] = []
    for snapshot in snapshots:
        if snapshot["status"] != "ok":
            differences.append({"service": snapshot["service"], "field": "connection", "roadmap": "available", "remote": snapshot.get("detail", "error")})
            continue
        remote_state = "open" if snapshot["state"] in {"open", "opened"} else "closed"
        if remote_state != expected_state:
            differences.append({"service": snapshot["service"], "field": "state", "roadmap": expected_state, "remote": remote_state})
        if item["Owner"] != EMPTY:
            try:
                expected_owner = identity(config, item["Owner"], snapshot["service"])
                if expected_owner not in snapshot["assignees"]:
                    differences.append({"service": snapshot["service"], "field": "owner", "roadmap": expected_owner, "remote": ", ".join(snapshot["assignees"]) or EMPTY})
            except NorthstarError as exc:
                differences.append({"service": snapshot["service"], "field": "identity", "roadmap": item["Owner"], "remote": str(exc)})
    return {"item": item["ID"], "canonical": {"status": item["Status"], "owner": item["Owner"], "sync": item["Sync"]}, "remotes": snapshots, "differences": differences}


def reconcile_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    preflight(root)
    roadmap = Roadmap.load(root / "ROADMAP.md")
    item = roadmap.find(args.item)
    config = load_config(root)
    snapshots = inspect_remotes(config, item)
    report = reconciliation_report(config, item, snapshots)
    if not args.apply:
        report["choices"] = {
            "canonical": "restore ROADMAP.md owner/state to every linked tracker",
            "remote": "use add --origin, claim, handoff, update, or close to import the chosen change through its normal gate",
            "ignore": "leave remote changes untouched and mark this row Drift",
        }
        print(json.dumps(report, indent=2))
        return
    if not args.strategy:
        raise NorthstarError("--strategy canonical or ignore is required with --apply")
    with workspace_lock(root):
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        if args.strategy == "ignore":
            item["Sync"] = "Drift"
            roadmap.save()
            audit(root, args.item, "Reconcile ignored", item["Status"], item["Status"], args.actor, item["Branch"], args.reason)
            journal(root, args.item, "reconcile-ignore", snapshots)
            return
        brief = brief_path(root, item).read_text(encoding="utf-8")
        results = create_remotes(config, item, brief)
        event = "closed" if item["Status"] == "Done" else "claimed" if item["Status"] == "In Progress" else "updated"
        results.extend(update_remotes(config, item, event, item["Owner"], detail=f"canonical reconciliation by {args.actor}: {args.reason}"))
        item["Sync"] = sync_state(results)
        roadmap.save()
        audit(root, args.item, "Reconciled canonical", "Drift", item["Sync"], args.actor, item["Branch"], args.reason)
        journal(root, args.item, "reconcile-canonical", results)


def preflight(root: Path) -> None:
    errors = validate(root)
    if errors:
        raise NorthstarError("Roadmap validation failed:\n- " + "\n- ".join(errors))


def add_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    if not args.apply:
        print(json.dumps({"action": "add", "title": args.title, "priority": args.priority, "remote": not args.local_only}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item_id = next_id(roadmap)
        relative = Path("roadmap") / "items" / f"{item_id}.md"
        item = {"ID": item_id, "P": args.priority, "Status": args.status, "Story": f"[{md_escape(args.title)}]({relative.as_posix()})", "Owner": EMPTY, "Branch": EMPTY, "GitHub": EMPTY, "GitLab": EMPTY, "Wayfinder": EMPTY, "Sync": "Local"}
        if args.origin != "native":
            if not args.origin_url:
                raise NorthstarError("--origin-url is required when importing external work")
            number = args.origin_url.rstrip("/").rsplit("/", 1)[-1]
            item["GitHub" if args.origin == "github" else "GitLab"] = f"[#{number}]({args.origin_url})"
        brief = new_brief(item_id, args.title, args.priority, args.story, args.acceptance, args.origin, args.origin_url)
        atomic_write(root / relative, brief)
        config = load_config(root)
        results = [] if args.local_only else create_remotes(config, item, brief)
        if args.origin != "native" and not args.local_only:
            results.extend(mark_import(config, item, args.origin))
        item["Sync"] = sync_state(results)
        roadmap.items.append(item)
        roadmap.save()
        audit(root, item_id, "Created", EMPTY, args.status, args.actor, EMPTY, args.origin)
        journal(root, item_id, "created", results)
        print(item_id)


def claim_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    if not args.apply:
        print(json.dumps({"action": "claim", "item": args.item, "owner": args.owner, "branch": args.branch, "wayfinder": args.wayfinder}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        if item["Status"] != "Ready":
            raise NorthstarError(f"{args.item} must be Ready before it can be claimed")
        if item["Owner"] != EMPTY:
            raise NorthstarError(f"{args.item} is locked to {item['Owner']}")
        item.update({"Status": "In Progress", "Owner": args.owner, "Branch": args.branch, "Wayfinder": args.wayfinder, "Sync": "Local"})
        path = brief_path(root, item)
        brief = path.read_text(encoding="utf-8")
        for name, value in (("Owner", args.owner), ("Branch", args.branch), ("Wayfinder", args.wayfinder)):
            brief = replace_field(brief, name, value)
        brief = append_history(brief, "Claimed", args.actor, f"Owner {args.owner}; branch {args.branch}; Wayfinder {args.wayfinder}")
        atomic_write(path, brief)
        results = [] if args.local_only else update_remotes(load_config(root), item, "claimed", args.owner, detail=f"claimed by {args.owner} on {args.branch}")
        item["Sync"] = sync_state(results)
        roadmap.save()
        audit(root, args.item, "Claimed", EMPTY, args.owner, args.actor, args.branch, args.wayfinder)
        journal(root, args.item, "claimed", results)


def update_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    requested = {key: value for key, value in {"priority": args.priority, "status": args.status, "title": args.title}.items() if value}
    if not requested:
        raise NorthstarError("Update requires --priority, --status, or --title")
    if not args.apply:
        print(json.dumps({"action": "update", "item": args.item, "changes": requested, "reason": args.reason}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        if item["Status"] in {"In Progress", "Done"} and args.status:
            raise NorthstarError("Use claim, handoff, or close for active/completed lifecycle transitions")
        before = f"P={item['P']}; Status={item['Status']}"
        path = brief_path(root, item)
        brief = path.read_text(encoding="utf-8")
        if args.priority:
            item["P"] = args.priority
            brief = replace_field(brief, "Priority", args.priority)
        if args.status:
            item["Status"] = args.status
        if args.title:
            link = LINK_RE.fullmatch(item["Story"])
            item["Story"] = f"[{md_escape(args.title)}]({link.group(2)})"
        after = f"P={item['P']}; Status={item['Status']}"
        brief = append_history(brief, "Updated", args.actor, f"{before} to {after}; {args.reason}")
        atomic_write(path, brief)
        item["Sync"] = "Local"
        results = [] if args.local_only else update_remotes(load_config(root), item, "updated", item["Owner"], detail=f"{before} → {after}; {args.reason}")
        item["Sync"] = sync_state(results)
        roadmap.save()
        audit(root, args.item, "Updated", before, after, args.actor, item["Branch"], args.reason)
        journal(root, args.item, "updated", results)


def handoff_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    if not args.apply:
        print(json.dumps({"action": "handoff", "item": args.item, "to": args.to, "actor": args.actor, "override": args.override, "reason": args.reason}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        if item["Status"] != "In Progress" or item["Owner"] == EMPTY:
            raise NorthstarError(f"{args.item} is not actively owned")
        previous = item["Owner"]
        if args.actor != previous and not args.override:
            raise NorthstarError("Only the current owner may hand off; a maintainer override requires --override")
        if not args.reason.strip():
            raise NorthstarError("A handoff reason is mandatory")
        item["Owner"], item["Sync"] = args.to, "Local"
        path = brief_path(root, item)
        brief = replace_field(path.read_text(encoding="utf-8"), "Owner", args.to)
        brief = append_history(brief, "Handoff override" if args.override else "Handoff", args.actor, f"{previous} to {args.to}: {args.reason}")
        atomic_write(path, brief)
        results = [] if args.local_only else update_remotes(load_config(root), item, "handoff", args.to, previous, args.reason)
        item["Sync"] = sync_state(results)
        roadmap.save()
        audit(root, args.item, "Handoff override" if args.override else "Handoff", previous, args.to, args.actor, item["Branch"], args.reason)
        journal(root, args.item, "handoff", results)


def close_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    if not args.apply:
        print(json.dumps({"action": "close", "item": args.item, "graphify": args.graphify, "evidence": args.evidence}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        if item["Status"] != "In Progress":
            raise NorthstarError(f"{args.item} must be In Progress before closeout")
        path = brief_path(root, item)
        brief = path.read_text(encoding="utf-8")
        unchecked = re.findall(r"^- \[ ] .+$", section(brief, "Acceptance criteria"), re.M)
        if unchecked:
            raise NorthstarError(f"{args.item} has {len(unchecked)} unchecked acceptance criteria")
        if not (args.graphify.startswith("Updated:") or args.graphify.startswith("Verified-no-change:")):
            raise NorthstarError("Graphify evidence must start with 'Updated:' or 'Verified-no-change:'")
        brief = replace_field(brief, "Graphify", args.graphify)
        brief = replace_field(brief, "Pull request / merge request", args.evidence)
        brief = replace_field(brief, "Roadmap and trackers updated", "Yes")
        brief = append_history(brief, "Closed", args.actor, f"Graphify {args.graphify}; evidence {args.evidence}")
        atomic_write(path, brief)
        item["Status"], item["Sync"] = "Done", "Local"
        results = [] if args.local_only else update_remotes(load_config(root), item, "closed", item["Owner"], detail=f"completed by {item['Owner']}; {args.evidence}")
        item["Sync"] = sync_state(results)
        roadmap.save()
        audit(root, args.item, "Closed", "In Progress", "Done", args.actor, item["Branch"], args.evidence)
        journal(root, args.item, "closed", results)
        post_errors = validate(root)
        if post_errors:
            raise NorthstarError("Closeout produced invalid state:\n- " + "\n- ".join(post_errors))


def doctor(root: Path) -> int:
    report: dict[str, Any] = {"root": str(root.resolve()), "roadmap": (root / "ROADMAP.md").is_file(), "config": (root / "roadmap" / "northstar.toml").is_file()}
    for executable in ("gh", "glab", "graphify"):
        try:
            process = subprocess.run([executable, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            report[executable] = {"available": process.returncode == 0, "version": process.stdout.splitlines()[0] if process.stdout else ""}
        except FileNotFoundError:
            report[executable] = {"available": False}
    print(json.dumps(report, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="northstar", description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    commands.add_parser("doctor")
    init = commands.add_parser("init")
    init.add_argument("--apply", action="store_true")
    add = commands.add_parser("add")
    add.add_argument("--title", required=True)
    add.add_argument("--priority", choices=sorted(PRIORITIES), required=True)
    add.add_argument("--status", choices=["Candidate", "Planned", "Ready"], default="Planned")
    add.add_argument("--story", required=True)
    add.add_argument("--acceptance", action="append", required=True)
    add.add_argument("--origin", choices=["native", "github", "gitlab"], default="native")
    add.add_argument("--origin-url", default="")
    add.add_argument("--actor", default="northstar")
    add.add_argument("--local-only", action="store_true")
    add.add_argument("--apply", action="store_true")
    claim = commands.add_parser("claim")
    claim.add_argument("item")
    claim.add_argument("--owner", required=True)
    claim.add_argument("--branch", required=True)
    claim.add_argument("--wayfinder", required=True)
    claim.add_argument("--actor", required=True)
    claim.add_argument("--local-only", action="store_true")
    claim.add_argument("--apply", action="store_true")
    update = commands.add_parser("update")
    update.add_argument("item")
    update.add_argument("--priority", choices=sorted(PRIORITIES))
    update.add_argument("--status", choices=["Candidate", "Planned", "Ready", "Deferred", "Retired"])
    update.add_argument("--title")
    update.add_argument("--actor", required=True)
    update.add_argument("--reason", required=True)
    update.add_argument("--local-only", action="store_true")
    update.add_argument("--apply", action="store_true")
    handoff = commands.add_parser("handoff")
    handoff.add_argument("item")
    handoff.add_argument("--to", required=True)
    handoff.add_argument("--actor", required=True)
    handoff.add_argument("--reason", required=True)
    handoff.add_argument("--override", action="store_true")
    handoff.add_argument("--local-only", action="store_true")
    handoff.add_argument("--apply", action="store_true")
    close = commands.add_parser("close")
    close.add_argument("item")
    close.add_argument("--actor", required=True)
    close.add_argument("--graphify", required=True)
    close.add_argument("--evidence", required=True)
    close.add_argument("--local-only", action="store_true")
    close.add_argument("--apply", action="store_true")
    reconcile = commands.add_parser("reconcile")
    reconcile.add_argument("item")
    reconcile.add_argument("--strategy", choices=["canonical", "ignore"])
    reconcile.add_argument("--actor", default="northstar")
    reconcile.add_argument("--reason", default="explicit reconciliation")
    reconcile.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            errors = validate(args.root.resolve())
            if errors:
                print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
                return 1
            print("OK: roadmap is valid")
        elif args.command == "doctor":
            return doctor(args.root)
        elif args.command == "init":
            if not args.apply:
                print(json.dumps({"action": "init", "root": str(args.root.resolve())}, indent=2))
            else:
                init_workspace(args.root.resolve())
        elif args.command == "add":
            add_item(args)
        elif args.command == "claim":
            claim_item(args)
        elif args.command == "update":
            update_item(args)
        elif args.command == "handoff":
            handoff_item(args)
        elif args.command == "close":
            close_item(args)
        elif args.command == "reconcile":
            reconcile_item(args)
        return 0
    except (NorthstarError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


CONFIG_TEMPLATE = """version = 1

[github]
enabled = false
repository = "owner/repository"
project_title = ""

[gitlab]
enabled = false
project = "group/project"

# Map the roadmap's stable teammate name to service usernames.
# [identities.Maya]
# github = "maya-gh"
# gitlab = "maya-gl"
"""

AUDIT_TEMPLATE = """# Northstar audit log

Append-only history of ownership and roadmap transitions.

| Timestamp | Item | Event | From | To | Actor | Branch | Reason / evidence |
|---|---|---|---|---|---|---|---|
"""


if __name__ == "__main__":
    raise SystemExit(main())
