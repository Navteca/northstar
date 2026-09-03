#!/usr/bin/env python3
"""Deterministic roadmap engine for the Northstar skill."""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

HEADER = ["ID", "P", "Status", "Story", "Owner", "Branch", "Issue", "Plan", "Sync"]
STATUSES = {"Candidate", "Planned", "Planning", "Ready", "In Progress", "Blocked", "Done", "Deferred", "Retired"}
SYNC_STATES = {"Local", "Synced", "Drift", "Error"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
PLAN_KINDS = {"Direct", "Wayfinder", "Spec Kit"}
EXECUTION_METHODS = {"Native", "RPI"}
OWNED = {"Planning", "In Progress", "Blocked"}
# Legal lifecycle moves. The engine enforces this table on every mutation; CI policy re-checks it per pull request.
TRANSITIONS = {
    "Candidate": {"Candidate", "Planned", "Deferred", "Retired"},
    "Planned": {"Planned", "Ready", "Deferred", "Retired"},
    "Ready": {"Ready", "Planning", "In Progress", "Deferred", "Retired"},
    "Planning": {"Planning", "Ready", "Blocked"},
    "In Progress": {"In Progress", "Blocked", "Done"},
    "Blocked": {"Blocked", "Planning", "In Progress", "Ready"},
    "Done": {"Done"},
    "Deferred": {"Deferred", "Planned", "Retired"},
    "Retired": {"Retired"},
}
EMPTY = "—"
ID_RE = re.compile(r"RM-(\d{3,})$")
STORY_RE = re.compile(r"As (?:a|an|the) .+?, I want .+?, so that .+?\.?$", re.I)
LINK_RE = re.compile(r"\[(.+)]\((.+)\)$")
ISSUE_RE = re.compile(r"github\.com/([^/]+/[^/]+)/issues/(\d+)")


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
    # ponytail: one lock per working tree; the shared default branch is the cross-clone authority.
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
    path = (root / match.group(2)).resolve()
    allowed = (root / "roadmap" / "items").resolve()
    if not path.is_relative_to(allowed):
        raise NorthstarError(f"{item['ID']}: Story brief must stay under roadmap/items")
    return path


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


def check_transition(item: dict[str, str], new_status: str) -> None:
    if new_status not in TRANSITIONS[item["Status"]]:
        raise NorthstarError(f"{item['ID']}: illegal transition {item['Status']} → {new_status}")


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
        if item["Issue"] != EMPTY and not (LINK_RE.fullmatch(item["Issue"]) and ISSUE_RE.search(item["Issue"])):
            errors.append(f"{item_id}: Issue must be a Markdown link to a GitHub issue")
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
        if item["Status"] in OWNED and item["Owner"] == EMPTY:
            errors.append(f"{item_id}: {item['Status']} requires Owner")
        if item["Status"] in OWNED | {"Done"} and item["Branch"] == EMPTY:
            errors.append(f"{item_id}: {item['Status']} requires target Branch")
        if item["Status"] == "Planning" and item["Plan"] == EMPTY:
            errors.append(f"{item_id}: Planning requires Plan")
        plan_kind = field(text, "Plan kind")
        if plan_kind not in PLAN_KINDS:
            errors.append(f"{item_id}: Plan kind must be Direct, Wayfinder, or Spec Kit")
        if item["Status"] in OWNED | {"Ready"} and plan_kind != "Direct" and item["Plan"] == EMPTY:
            errors.append(f"{item_id}: {plan_kind} route requires Plan before active work")
        execution_method = field(text, "Execution method") or "Native"
        if execution_method not in EXECUTION_METHODS:
            errors.append(f"{item_id}: Execution method must be Native or RPI")
        if item["Status"] == "Done":
            if any(value == " " for value in criteria):
                errors.append(f"{item_id}: Done requires all acceptance criteria checked")
            context = field(text, "Context")
            if not context or context in {EMPTY, "Pending"}:
                errors.append(f"{item_id}: Done requires durable context evidence")
    return errors


def init_workspace(root: Path) -> None:
    roadmap = root / "ROADMAP.md"
    if roadmap.exists():
        raise NorthstarError(f"Refusing to overwrite existing {roadmap}")
    atomic_write(roadmap, "# Product roadmap\n\n" + render_row(HEADER) + "\n" + render_row(["---"] * len(HEADER)) + "\n")
    atomic_write(root / "roadmap" / "northstar.toml", CONFIG_TEMPLATE)
    atomic_write(root / "roadmap" / "audit.md", AUDIT_TEMPLATE)


def next_id(roadmap: Roadmap, root: Path | None = None) -> str:
    numbers = [int(match.group(1)) for item in roadmap.items if (match := ID_RE.fullmatch(item["ID"]))]
    if root:
        numbers.extend(int(match.group(1)) for path in (root / "roadmap" / "items").glob("RM-*.md") if (match := ID_RE.fullmatch(path.stem)))
    return f"RM-{max(numbers, default=0) + 1:03d}"


def new_brief(item_id: str, title: str, priority: str, story: str, criteria: list[str], origin: str, origin_url: str, plan_kind: str = "Direct", execution_method: str = "Native") -> str:
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
- Issue: {origin_url if origin == "github" else EMPTY}
- Plan kind: {plan_kind}
- Execution method: {execution_method}
- Plan: {EMPTY}
- Context: Pending

## Completion evidence

- Pull request: {EMPTY}
- Roadmap and tracker updated: No

## History

| Timestamp | Event | Actor | Detail |
|---|---|---|---|
| {now()} | Created | northstar | {md_escape(origin)} roadmap item. |
"""


def audit(root: Path, item_id: str, event: str, old: str, new: str, actor: str, context: str, detail: str) -> None:
    path = root / "roadmap" / "audit.md"
    if not path.exists():
        atomic_write(path, AUDIT_TEMPLATE)
    timestamp = now()
    with path.open("a", encoding="utf-8") as stream:
        stream.write(render_row([timestamp, item_id, event, old, new, actor, context or EMPTY, md_escape(detail)]) + "\n")
    chain = root / "roadmap" / "audit.chain.jsonl"
    previous = "0" * 64
    if chain.is_file():
        lines = [line for line in chain.read_text(encoding="utf-8").splitlines() if line.strip()]
        if lines:
            previous = json.loads(lines[-1])["hash"]
    record = {"timestamp": timestamp, "item": item_id, "event": event, "from": old, "to": new, "actor": actor, "context": context or EMPTY, "detail": detail, "previous": previous}
    record["hash"] = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with chain.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")


# --- GitHub adapter -----------------------------------------------------------


def load_config(root: Path) -> dict[str, Any]:
    path = root / "roadmap" / "northstar.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as stream:
        return tomllib.load(stream)


def command(args: list[str], stdin: dict[str, Any] | None = None) -> str:
    process = subprocess.run(args, input=json.dumps(stdin) if stdin is not None else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if process.returncode:
        raise NorthstarError(f"{' '.join(args[:3])} failed: {process.stderr.strip()}")
    return process.stdout.strip()


def github_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("github", {}).get("enabled", False))


def identity(config: dict[str, Any], owner: str) -> str:
    login = config.get("identities", {}).get(owner, {}).get("github")
    if not login:
        raise NorthstarError(f"No GitHub identity mapping for owner {owner!r}; add [identities.{owner}] github = \"login\" to roadmap/northstar.toml")
    return str(login)


def owner_for_login(config: dict[str, Any], login: str) -> str:
    for owner, logins in config.get("identities", {}).items():
        if logins.get("github") == login:
            return owner
    raise NorthstarError(f"GitHub login {login!r} is not mapped to any teammate in roadmap/northstar.toml")


def unmapped_owners(config: dict[str, Any], roadmap: Roadmap) -> list[str]:
    identities = config.get("identities", {})
    return sorted({item["Owner"] for item in roadmap.items if item["Owner"] != EMPTY and not identities.get(item["Owner"], {}).get("github")})


def issue_url(item: dict[str, str]) -> str:
    match = LINK_RE.fullmatch(item["Issue"])
    if not match or not ISSUE_RE.search(match.group(2)):
        raise NorthstarError(f"{item['ID']}: Issue is not a GitHub issue link")
    return match.group(2)


def link_issue(item: dict[str, str], url: str) -> None:
    item["Issue"] = f"[#{url.rstrip('/').rsplit('/', 1)[-1]}]({url})"


def ensure_issue(config: dict[str, Any], item: dict[str, str], brief: str) -> None:
    """Create the GitHub issue for an item once. Safe to retry: it searches by ID before creating."""
    if item["Issue"] != EMPTY:
        return
    repo = config["github"]["repository"]
    title = LINK_RE.fullmatch(item["Story"]).group(1)
    existing = json.loads(command(["gh", "issue", "list", "-R", repo, "--state", "all", "--limit", "1", "--json", "url", "--search", f'"[{item["ID"]}]" in:title']) or "[]")
    if existing:
        link_issue(item, existing[0]["url"])
        return
    body = f"Northstar item: `{item['ID']}`\n\n{section(brief, 'User story')}\n\n## Acceptance criteria\n{section(brief, 'Acceptance criteria')}"
    output = command(["gh", "api", "--method", "POST", f"repos/{repo}/issues", "--input", "-"], {"title": f"[{item['ID']}] {title}", "body": body})
    url = json.loads(output)["html_url"]
    project = config["github"].get("project_title")
    if project:
        command(["gh", "issue", "edit", url, "--add-project", str(project)])
    link_issue(item, url)


def post_event(config: dict[str, Any], item: dict[str, str], event: str, owner: str = "", previous: str = "", detail: str = "", operation_id: str = "") -> None:
    url = issue_url(item)
    marker = f"[northstar:{item['ID']}]{f'[op:{operation_id}]' if operation_id else ''} {event}: {detail}".strip()
    if event in {"claimed", "handoff"}:
        args = ["gh", "issue", "edit", url, "--add-assignee", identity(config, owner)]
        if previous:
            args.extend(["--remove-assignee", identity(config, previous)])
        command(args)
        command(["gh", "issue", "comment", url, "--body", marker])
    elif event == "closed":
        command(["gh", "issue", "close", url, "--comment", marker])
    elif event == "imported":
        command(["gh", "issue", "comment", url, "--body", f"[northstar:{item['ID']}] This issue was created outside Northstar and imported into the canonical ROADMAP.md. Future planning changes are governed by Northstar."])
    else:
        command(["gh", "issue", "comment", url, "--body", marker])


def sync(config: dict[str, Any], item: dict[str, str], brief: str, event: str | None, owner: str = "", previous: str = "", detail: str = "", operation_id: str = "") -> dict[str, str] | None:
    """Push one lifecycle event to the linked GitHub issue. Returns None when GitHub is not enabled."""
    if not github_enabled(config):
        return None
    try:
        ensure_issue(config, item, brief)
        if event:
            post_event(config, item, event, owner, previous, detail, operation_id)
        return {"status": "ok", "url": issue_url(item)}
    except Exception as exc:  # any adapter failure is a sync error, never a roadmap error
        return {"status": "error", "detail": str(exc)}


def sync_state(result: dict[str, str] | None) -> str:
    if result is None:
        return "Local"
    return "Synced" if result["status"] == "ok" else "Error"


def journal(root: Path, item_id: str, event: str, remote_event: str | None, result: dict[str, str] | None, operation_id: str) -> None:
    timestamp = now()
    stamp = timestamp.replace(":", "").replace("-", "")
    record = {"operation_id": operation_id, "timestamp": timestamp, "item": item_id, "event": event, "remote_event": remote_event, "status": sync_state(result), "result": result}
    atomic_write(root / "roadmap" / "journal" / f"{stamp}-{item_id}-{event}-{operation_id}.json", json.dumps(record, indent=2) + "\n")


def latest_journal(root: Path, item_id: str) -> dict[str, Any] | None:
    paths = sorted((root / "roadmap" / "journal").glob(f"*-{item_id}-*.json"))
    return json.loads(paths[-1].read_text(encoding="utf-8")) if paths else None


def inspect_issue(item: dict[str, str]) -> dict[str, Any]:
    try:
        url = issue_url(item)
        data = json.loads(command(["gh", "issue", "view", url, "--json", "state,assignees,title,url"]))
        return {"status": "ok", "url": url, "state": data["state"].lower(), "assignees": [entry["login"] for entry in data.get("assignees", [])], "title": data["title"]}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def reconciliation_report(config: dict[str, Any], item: dict[str, str], snapshot: dict[str, Any]) -> dict[str, Any]:
    expected_state = "closed" if item["Status"] == "Done" else "open"
    differences: list[dict[str, str]] = []
    if snapshot["status"] != "ok":
        differences.append({"field": "connection", "roadmap": "available", "remote": snapshot.get("detail", "error")})
    else:
        if snapshot["state"] != expected_state:
            differences.append({"field": "state", "roadmap": expected_state, "remote": snapshot["state"]})
        if item["Owner"] != EMPTY:
            try:
                expected_owner = identity(config, item["Owner"])
                if expected_owner not in snapshot["assignees"]:
                    differences.append({"field": "owner", "roadmap": expected_owner, "remote": ", ".join(snapshot["assignees"]) or EMPTY})
            except NorthstarError as exc:
                differences.append({"field": "identity", "roadmap": item["Owner"], "remote": str(exc)})
    return {"item": item["ID"], "canonical": {"status": item["Status"], "owner": item["Owner"], "sync": item["Sync"]}, "remote": snapshot, "differences": differences}


def event_for_status(status: str) -> str:
    return "closed" if status == "Done" else "claimed" if status in OWNED else "updated"


# --- Operations ---------------------------------------------------------------


def preflight(root: Path) -> None:
    errors = validate(root)
    if errors:
        raise NorthstarError("Roadmap validation failed:\n- " + "\n- ".join(errors))


def finish(root: Path, roadmap: Roadmap, item: dict[str, str], event: str, remote_event: str | None, result: dict[str, str] | None, operation_id: str) -> None:
    item["Sync"] = sync_state(result)
    roadmap.save()
    journal(root, item["ID"], event, remote_event, result, operation_id)


def add_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    if not args.apply:
        print(json.dumps({"action": "add", "title": args.title, "priority": args.priority, "remote": not args.local_only}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item_id = next_id(roadmap, root)
        relative = Path("roadmap") / "items" / f"{item_id}.md"
        item = {"ID": item_id, "P": args.priority, "Status": args.status, "Story": f"[{md_escape(args.title)}]({relative.as_posix()})", "Owner": EMPTY, "Branch": EMPTY, "Issue": EMPTY, "Plan": EMPTY, "Sync": "Local"}
        if args.origin == "github":
            if not ISSUE_RE.search(args.origin_url or ""):
                raise NorthstarError("--origin github requires a GitHub issue URL in --origin-url")
            link_issue(item, args.origin_url)
        brief = new_brief(item_id, args.title, args.priority, args.story, args.acceptance, args.origin, args.origin_url, getattr(args, "plan_kind", "Direct"), getattr(args, "execution_method", "Native"))
        atomic_write(root / relative, brief)
        operation_id = uuid.uuid4().hex[:16]
        remote_event = "imported" if args.origin == "github" else None
        result = None if args.local_only else sync(load_config(root), item, brief, remote_event, operation_id=operation_id)
        if item["Issue"] != EMPTY:
            atomic_write(root / relative, replace_field(brief, "Issue", issue_url(item)))
        roadmap.items.append(item)
        audit(root, item_id, "Created", EMPTY, args.status, args.actor, EMPTY, args.origin)
        finish(root, roadmap, item, "created", remote_event, result, operation_id)
        print(item_id)


def pickup_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    config = load_config(root)
    owner = args.owner or (owner_for_login(config, args.owner_login) if getattr(args, "owner_login", "") else "")
    if not owner:
        raise NorthstarError("Pickup requires --owner or --owner-login")
    actor = args.actor or owner
    if not args.apply:
        print(json.dumps({"action": "pickup", "item": args.item, "owner": owner, "branch": args.branch, "planning": args.planning, "plan": args.plan, "execution_method": getattr(args, "execution_method", "Native")}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        if item["Status"] != "Ready":
            raise NorthstarError(f"{args.item} must be Ready before it can be picked up")
        if item["Owner"] not in {EMPTY, owner}:
            raise NorthstarError(f"{args.item} is locked to {item['Owner']}")
        path = brief_path(root, item)
        brief = path.read_text(encoding="utf-8")
        plan_kind = getattr(args, "plan_kind", "") or field(brief, "Plan kind")
        if args.planning and not getattr(args, "plan_kind", ""):
            plan_kind = "Wayfinder"
        if args.planning and not args.plan:
            raise NorthstarError(f"Planning with {plan_kind} requires the canonical plan URL in --plan")
        if args.planning and plan_kind == "Direct":
            raise NorthstarError("--planning requires --plan-kind Wayfinder or Spec Kit")
        status = "Planning" if args.planning else "In Progress"
        check_transition(item, status)
        plan = args.plan or item["Plan"]
        execution_method = getattr(args, "execution_method", "") or field(brief, "Execution method") or "Native"
        item.update({"Status": status, "Owner": owner, "Branch": args.branch, "Plan": plan})
        operation_id = uuid.uuid4().hex[:16]
        result = None if args.local_only else sync(config, item, brief, "claimed", owner, detail=f"picked up by {owner}; status {status}", operation_id=operation_id)
        for name, value in (("Owner", owner), ("Branch", args.branch), ("Issue", item["Issue"] if item["Issue"] == EMPTY else issue_url(item)), ("Plan kind", plan_kind), ("Execution method", execution_method), ("Plan", plan)):
            brief = replace_field(brief, name, value)
        brief = append_history(brief, "Picked up", actor, f"Owner {owner}; branch {args.branch}; status {status}; plan {plan}")
        atomic_write(path, brief)
        audit(root, args.item, "Picked up", "Ready", status, actor, args.branch, f"Owner {owner}; plan {plan}")
        finish(root, roadmap, item, "picked-up", "claimed", result, operation_id)


def link_plan(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    if not args.apply:
        print(json.dumps({"action": "link-plan", "item": args.item, "plan": args.plan, "status": args.status}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        if item["Owner"] == EMPTY:
            raise NorthstarError(f"{args.item} must be owned before linking active planning")
        old = item["Status"]
        check_transition(item, args.status)
        item["Plan"], item["Status"] = args.plan, args.status
        path = brief_path(root, item)
        brief = replace_field(path.read_text(encoding="utf-8"), "Plan kind", getattr(args, "plan_kind", "Wayfinder"))
        brief = replace_field(brief, "Plan", args.plan)
        brief = append_history(brief, "Plan linked", args.actor, f"{args.plan}; {old} to {args.status}; {args.reason}")
        atomic_write(path, brief)
        operation_id = uuid.uuid4().hex[:16]
        result = None if args.local_only else sync(load_config(root), item, brief, "updated", item["Owner"], detail=f"plan {args.plan}; {old} → {args.status}", operation_id=operation_id)
        audit(root, args.item, "Plan linked", old, args.status, args.actor, args.plan, args.reason)
        finish(root, roadmap, item, "plan-linked", "updated", result, operation_id)


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
        if args.status:
            check_transition(item, args.status)
        before = f"P={item['P']}; Status={item['Status']}"
        path = brief_path(root, item)
        brief = path.read_text(encoding="utf-8")
        if args.priority:
            item["P"] = args.priority
            brief = replace_field(brief, "Priority", args.priority)
        if args.status:
            item["Status"] = args.status
        if args.title:
            item["Story"] = f"[{md_escape(args.title)}]({LINK_RE.fullmatch(item['Story']).group(2)})"
        after = f"P={item['P']}; Status={item['Status']}"
        brief = append_history(brief, "Updated", args.actor, f"{before} to {after}; {args.reason}")
        atomic_write(path, brief)
        operation_id = uuid.uuid4().hex[:16]
        result = None if args.local_only else sync(load_config(root), item, brief, "updated", item["Owner"], detail=f"{before} → {after}; {args.reason}", operation_id=operation_id)
        audit(root, args.item, "Updated", before, after, args.actor, item["Plan"], args.reason)
        finish(root, roadmap, item, "updated", "updated", result, operation_id)
        errors = validate(root)
        if errors:
            raise NorthstarError("Update produced invalid state:\n- " + "\n- ".join(errors))


def handoff_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    if not args.apply:
        print(json.dumps({"action": "handoff", "item": args.item, "to": args.to, "actor": args.actor, "override": args.override, "reason": args.reason}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        if item["Status"] not in OWNED or item["Owner"] == EMPTY:
            raise NorthstarError(f"{args.item} is not actively owned")
        previous = item["Owner"]
        if args.actor != previous and not args.override:
            raise NorthstarError("Only the current owner may hand off; a maintainer override requires --override")
        if not args.reason.strip():
            raise NorthstarError("A handoff reason is mandatory")
        item["Owner"] = args.to
        path = brief_path(root, item)
        brief = replace_field(path.read_text(encoding="utf-8"), "Owner", args.to)
        event = "Handoff override" if args.override else "Handoff"
        brief = append_history(brief, event, args.actor, f"{previous} to {args.to}: {args.reason}")
        atomic_write(path, brief)
        operation_id = uuid.uuid4().hex[:16]
        result = None if args.local_only else sync(load_config(root), item, brief, "handoff", args.to, previous, args.reason, operation_id)
        audit(root, args.item, event, previous, args.to, args.actor, item["Plan"], args.reason)
        finish(root, roadmap, item, "handoff", "handoff", result, operation_id)


def close_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    if not args.apply:
        print(json.dumps({"action": "close", "item": args.item, "context": args.context, "evidence": args.evidence}, indent=2))
        return
    with workspace_lock(root):
        preflight(root)
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        check_transition(item, "Done")
        path = brief_path(root, item)
        brief = path.read_text(encoding="utf-8")
        unchecked = re.findall(r"^- \[ ] .+$", section(brief, "Acceptance criteria"), re.M)
        if unchecked:
            raise NorthstarError(f"{args.item} has {len(unchecked)} unchecked acceptance criteria")
        if not args.context.strip():
            raise NorthstarError("Durable context evidence is required")
        brief = replace_field(brief, "Context", args.context)
        brief = replace_field(brief, "Pull request", args.evidence)
        brief = replace_field(brief, "Roadmap and tracker updated", "Yes")
        brief = append_history(brief, "Closed", args.actor, f"Context {args.context}; evidence {args.evidence}")
        atomic_write(path, brief)
        item["Status"] = "Done"
        operation_id = uuid.uuid4().hex[:16]
        result = None if args.local_only else sync(load_config(root), item, brief, "closed", item["Owner"], detail=f"completed by {item['Owner']}; {args.evidence}", operation_id=operation_id)
        audit(root, args.item, "Closed", "In Progress", "Done", args.actor, item["Plan"], args.evidence)
        finish(root, roadmap, item, "closed", "closed", result, operation_id)
        errors = validate(root)
        if errors:
            raise NorthstarError("Closeout produced invalid state:\n- " + "\n- ".join(errors))


def reconcile_item(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    preflight(root)
    roadmap = Roadmap.load(root / "ROADMAP.md")
    item = roadmap.find(args.item)
    if item["Issue"] == EMPTY:
        raise NorthstarError(f"{args.item} has no linked issue to reconcile")
    config = load_config(root)
    report = reconciliation_report(config, item, inspect_issue(item))
    if not args.apply:
        report["choices"] = {
            "canonical": "restore ROADMAP.md owner/state to the linked issue",
            "remote": "use update, handoff, or close to import the chosen change through its normal gate",
            "ignore": "leave the issue untouched and mark this row Drift",
        }
        print(json.dumps(report, indent=2))
        return
    if not args.strategy:
        raise NorthstarError("--strategy canonical or ignore is required with --apply")
    with workspace_lock(root):
        roadmap = Roadmap.load(root / "ROADMAP.md")
        item = roadmap.find(args.item)
        operation_id = uuid.uuid4().hex[:16]
        if args.strategy == "ignore":
            item["Sync"] = "Drift"
            roadmap.save()
            audit(root, args.item, "Reconcile ignored", item["Status"], item["Status"], args.actor, item["Plan"], args.reason)
            journal(root, args.item, "reconcile-ignore", None, report["remote"], operation_id)
            return
        brief = brief_path(root, item).read_text(encoding="utf-8")
        event = event_for_status(item["Status"])
        result = sync(config, item, brief, event, item["Owner"], detail=f"canonical reconciliation by {args.actor}: {args.reason}", operation_id=operation_id)
        audit(root, args.item, "Reconciled canonical", "Drift", sync_state(result), args.actor, item["Plan"], args.reason)
        finish(root, roadmap, item, "reconcile-canonical", event, result, operation_id)


def doctor(root: Path) -> int:
    report: dict[str, Any] = {"root": str(root.resolve()), "roadmap": (root / "ROADMAP.md").is_file(), "config": (root / "roadmap" / "northstar.toml").is_file(), "engine": (root / "roadmap" / "bin" / "northstar.py").is_file()}
    for executable in ("gh", "graphify", "specify"):
        try:
            process = subprocess.run([executable, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            report[executable] = {"available": process.returncode == 0, "version": process.stdout.splitlines()[0] if process.stdout else ""}
        except FileNotFoundError:
            report[executable] = {"available": False}
    agents = root / "AGENTS.md"
    report["cc_rpi"] = {"available": (root / ".claude" / "commands" / "bootstrap").is_file() or (agents.is_file() and "cc-rpi" in agents.read_text(encoding="utf-8", errors="ignore"))}
    config = load_config(root)
    if report["roadmap"] and github_enabled(config):
        with contextlib.suppress(NorthstarError):
            report["unmapped_owners"] = unmapped_owners(config, Roadmap.load(root / "ROADMAP.md"))
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
    add.add_argument("--origin", choices=["native", "github"], default="native")
    add.add_argument("--origin-url", default="")
    add.add_argument("--plan-kind", choices=sorted(PLAN_KINDS), default="Direct")
    add.add_argument("--execution-method", choices=sorted(EXECUTION_METHODS), default="Native")
    add.add_argument("--actor", default="northstar")
    add.add_argument("--local-only", action="store_true")
    add.add_argument("--apply", action="store_true")
    for name in ("pickup", "claim"):
        pickup = commands.add_parser(name)
        pickup.add_argument("item")
        pickup.add_argument("--owner", default="", help="stable teammate name from roadmap/northstar.toml")
        pickup.add_argument("--owner-login", default="", help="GitHub login resolved to a teammate through [identities]")
        pickup.add_argument("--branch", required=True)
        pickup.add_argument("--plan", default="")
        pickup.add_argument("--plan-kind", choices=sorted(PLAN_KINDS), default="")
        pickup.add_argument("--execution-method", choices=sorted(EXECUTION_METHODS), default="")
        pickup.add_argument("--planning", action="store_true")
        pickup.add_argument("--actor", default="", help="defaults to the owner")
        pickup.add_argument("--local-only", action="store_true")
        pickup.add_argument("--apply", action="store_true")
    plan = commands.add_parser("link-plan")
    plan.add_argument("item")
    plan.add_argument("--plan", required=True)
    plan.add_argument("--plan-kind", choices=["Wayfinder", "Spec Kit"], required=True)
    plan.add_argument("--status", choices=["Planning", "Ready"], required=True)
    plan.add_argument("--actor", required=True)
    plan.add_argument("--reason", required=True)
    plan.add_argument("--local-only", action="store_true")
    plan.add_argument("--apply", action="store_true")
    update = commands.add_parser("update")
    update.add_argument("item")
    update.add_argument("--priority", choices=sorted(PRIORITIES))
    update.add_argument("--status", choices=["Candidate", "Planned", "Ready", "Blocked", "In Progress", "Deferred", "Retired"])
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
    close.add_argument("--context", required=True)
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
        elif args.command in {"pickup", "claim"}:
            pickup_item(args)
        elif args.command == "link-plan":
            link_plan(args)
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

[companions]
profile = "Core"
wayfinder = false
speckit = false
graphify = false
rpi = false

[policy]
default_route = "Direct"
archive_after_days = 90
max_active_items = 150

[notifications]
enabled = false
webhook_url_env = "NORTHSTAR_WEBHOOK_URL"
format = "generic" # generic, slack, or teams

# Map each teammate's stable roadmap name to their GitHub login.
# [identities.Maya]
# github = "maya-gh"
"""

AUDIT_TEMPLATE = """# Northstar audit log

Append-only history of ownership and roadmap transitions.

| Timestamp | Item | Event | From | To | Actor | Context | Reason / evidence |
|---|---|---|---|---|---|---|---|
"""


if __name__ == "__main__":
    raise SystemExit(main())
