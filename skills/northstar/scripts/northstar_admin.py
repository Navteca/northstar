#!/usr/bin/env python3
"""Operational reliability commands for Northstar repositories."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ENGINE_PATH = Path(__file__).with_name("northstar.py")
SPEC = importlib.util.spec_from_file_location("northstar_engine", ENGINE_PATH)
assert SPEC and SPEC.loader
ns = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ns
SPEC.loader.exec_module(ns)

ALLOWED_TRANSITIONS = {
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


def verify_audit(root: Path) -> list[str]:
    path = root / "roadmap" / "audit.chain.jsonl"
    if not path.is_file():
        return []
    errors: list[str] = []
    previous = "0" * 64
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            actual = record.pop("hash")
            expected = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if record.get("previous") != previous:
                errors.append(f"audit chain line {number}: previous hash mismatch")
            if actual != expected:
                errors.append(f"audit chain line {number}: record hash mismatch")
            previous = actual
        except (KeyError, json.JSONDecodeError) as exc:
            errors.append(f"audit chain line {number}: {exc}")
    return errors


def policy(root: Path, base: Path | None) -> int:
    errors = ns.validate(root) + verify_audit(root)
    active = ns.Roadmap.load(root / "ROADMAP.md")
    maximum = int(ns.load_config(root).get("policy", {}).get("max_active_items", 150))
    if len(active.items) > maximum:
        errors.append(f"ROADMAP.md has {len(active.items)} active items; policy maximum is {maximum}; archive completed or inactive work")
    if base and base.is_file():
        current = active
        previous = ns.Roadmap.load(base)
        current_by_id = {item["ID"]: item for item in current.items}
        archive_text = "\n".join(path.read_text(encoding="utf-8") for path in (root / "roadmap" / "archive").glob("*.md")) if (root / "roadmap" / "archive").is_dir() else ""
        for old in previous.items:
            new = current_by_id.get(old["ID"])
            if not new:
                if old["ID"] not in archive_text:
                    errors.append(f"{old['ID']}: removed without an archive entry")
                continue
            if new["Status"] not in ALLOWED_TRANSITIONS.get(old["Status"], set()):
                errors.append(f"{old['ID']}: illegal transition {old['Status']} → {new['Status']}")
            if old["Owner"] != new["Owner"] and old["Owner"] != ns.EMPTY:
                brief = ns.brief_path(root, new).read_text(encoding="utf-8")
                if "| Handoff" not in brief and "| Handoff override" not in brief:
                    errors.append(f"{old['ID']}: owner changed without a handoff history event")
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print("OK: Northstar policy is valid")
    return 0


def retry(root: Path, operation: str) -> int:
    outbox = root / "roadmap" / "outbox"
    paths = [outbox / f"{operation}.json"] if operation != "all" else sorted(outbox.glob("*.json"))
    roadmap = ns.Roadmap.load(root / "ROADMAP.md")
    config = ns.load_config(root)
    failures = 0
    for path in paths:
        if not path.is_file():
            failures += 1
            print(f"ERROR: missing outbox operation {path}", file=sys.stderr)
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        item = roadmap.find(record["item"])
        failed = {result["service"] for result in record.get("results", []) if result.get("status") == "error"}
        event = record["event"]
        if event == "created":
            results = ns.create_remotes(config, item, ns.brief_path(root, item).read_text(encoding="utf-8"), failed)
        else:
            mapped = {"picked-up": "claimed", "plan-linked": "updated", "reconcile-canonical": "updated"}.get(event, event)
            previous = record.get("transition", {}).get("from", "") if event == "handoff" else ""
            results = ns.update_remotes(config, item, mapped, item["Owner"], previous=previous, detail=f"retry {record['operation_id']}", services=failed, operation_id=record["operation_id"])
        returned = {result.get("service") for result in results}
        old_by_service = {result.get("service"): result for result in record.get("results", [])}
        results.extend(old_by_service[service] for service in failed - returned if service in old_by_service)
        preserved = [result for result in record.get("results", []) if result.get("service") not in failed]
        record["results"] = preserved + results
        record["attempts"] = int(record.get("attempts", 1)) + 1
        record["status"] = ns.sync_state(record["results"])
        old_sync = item["Sync"]
        item["Sync"] = record["status"]
        if record["status"] in {"Synced", "Local"}:
            path.unlink()
        else:
            ns.atomic_write(path, json.dumps(record, indent=2) + "\n")
            failures += 1
        ns.audit(root, item["ID"], "Sync retry", old_sync, item["Sync"], "northstar-retry", item["Plan"], record["operation_id"])
    roadmap.save()
    return 1 if failures else 0


def reconcile_all(root: Path, strategy: str, actor: str) -> int:
    ns.preflight(root)
    roadmap = ns.Roadmap.load(root / "ROADMAP.md")
    config = ns.load_config(root)
    reports = []
    for item in list(roadmap.items):
        if item["GitHub"] == ns.EMPTY and item["GitLab"] == ns.EMPTY:
            continue
        snapshots = ns.inspect_remotes(config, item)
        report = ns.reconciliation_report(config, item, snapshots)
        reports.append(report)
        if strategy != "report" and report["differences"]:
            ns.reconcile_item(argparse.Namespace(root=root, item=item["ID"], strategy=strategy, actor=actor, reason="fleet reconciliation", apply=True))
    print(json.dumps({"items": reports, "drift_count": sum(bool(report["differences"]) for report in reports)}, indent=2))
    return 1 if strategy == "report" and any(report["differences"] for report in reports) else 0


def item_timestamp(root: Path, item: dict[str, str]) -> dt.datetime | None:
    text = ns.brief_path(root, item).read_text(encoding="utf-8")
    matches = re.findall(r"^\| (\d{4}-\d{2}-\d{2}T[^| ]+) \|", text, re.M)
    if not matches:
        return None
    return dt.datetime.fromisoformat(matches[-1].replace("Z", "+00:00"))


def archive(root: Path, before: dt.datetime, statuses: set[str], apply: bool) -> int:
    ns.preflight(root)
    roadmap = ns.Roadmap.load(root / "ROADMAP.md")
    selected = [item for item in roadmap.items if item["Status"] in statuses and (stamp := item_timestamp(root, item)) and stamp < before]
    preview = {"before": before.isoformat(), "items": [item["ID"] for item in selected]}
    if not apply:
        print(json.dumps(preview, indent=2))
        return 0
    grouped: dict[str, list[dict[str, str]]] = {}
    for item in selected:
        stamp = item_timestamp(root, item)
        grouped.setdefault(str(stamp.year), []).append(item)
    for year, items in grouped.items():
        path = root / "roadmap" / "archive" / f"{year}.md"
        existing = []
        if path.is_file():
            existing = ns.Roadmap.load(path).items
        archived = existing + [dict(item) for item in items]
        for item in archived:
            match = ns.LINK_RE.fullmatch(item["Story"])
            if match:
                item["Story"] = f"[{match.group(1)}](../items/{item['ID']}.md)"
        lines = [f"# Northstar archive — {year}", "", ns.render_row(ns.HEADER), ns.render_row(["---"] * len(ns.HEADER))]
        lines.extend(ns.render_row([item[column] for column in ns.HEADER]) for item in archived)
        ns.atomic_write(path, "\n".join(lines) + "\n")
    selected_ids = {item["ID"] for item in selected}
    roadmap.items = [item for item in roadmap.items if item["ID"] not in selected_ids]
    roadmap.save()
    render(root, check=False)
    print(json.dumps(preview, indent=2))
    return 0


def render(root: Path, check: bool) -> int:
    roadmap = ns.Roadmap.load(root / "ROADMAP.md")
    groups = {"owner": {}, "status": {}, "priority": {}}
    for item in roadmap.items:
        for key, column in (("owner", "Owner"), ("status", "Status"), ("priority", "P")):
            groups[key].setdefault(item[column], []).append(item)
    outputs: dict[Path, str] = {}
    for key, values in groups.items():
        lines = [f"# Roadmap by {key}", "", "Generated by Northstar; do not edit manually.", ""]
        for value in sorted(values):
            lines.extend([f"## {value}", "", ns.render_row(ns.HEADER), ns.render_row(["---"] * len(ns.HEADER))])
            for item in values[value]:
                row = dict(item)
                match = ns.LINK_RE.fullmatch(row["Story"])
                if match:
                    row["Story"] = f"[{match.group(1)}](../items/{item['ID']}.md)"
                lines.append(ns.render_row([row[column] for column in ns.HEADER]))
            lines.append("")
        outputs[root / "roadmap" / "views" / f"by-{key}.md"] = "\n".join(lines).rstrip() + "\n"
    def cell(column: str, value: str, item_id: str) -> str:
        match = ns.LINK_RE.fullmatch(value)
        if not match:
            return html.escape(value)
        href = f"items/{item_id}.md" if column == "Story" else match.group(2)
        return f"<a href='{html.escape(href, quote=True)}'>{html.escape(match.group(1))}</a>"
    rows = "".join("<tr>" + "".join(f"<td>{cell(column, item[column], item['ID'])}</td>" for column in ns.HEADER) + "</tr>" for item in roadmap.items)
    dashboard = "<!doctype html><meta charset='utf-8'><title>Northstar roadmap</title><style>body{font:14px system-ui;margin:2rem;color:#172033}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd3df;padding:.45rem;text-align:left}th{background:#eef2f7;position:sticky;top:0}tr:nth-child(even){background:#f8fafc}</style><h1>Northstar roadmap</h1><p>Generated from ROADMAP.md. Do not edit manually.</p><table><thead><tr>" + "".join(f"<th>{html.escape(column)}</th>" for column in ns.HEADER) + "</tr></thead><tbody>" + rows + "</tbody></table>"
    outputs[root / "roadmap" / "dashboard.html"] = dashboard + "\n"
    drift = [str(path.relative_to(root)) for path, content in outputs.items() if not path.is_file() or path.read_text(encoding="utf-8") != content]
    if check:
        if drift:
            print("ERROR: generated views are stale: " + ", ".join(drift), file=sys.stderr)
            return 1
        return 0
    for path, content in outputs.items():
        ns.atomic_write(path, content)
    return 0


def compatibility(root: Path) -> int:
    manifest = Path(__file__).parents[1] / "COMPATIBILITY.toml"
    with manifest.open("rb") as stream:
        data = ns.tomllib.load(stream)
    report = {}
    config = ns.load_config(root)
    for name, spec in data["tools"].items():
        command_name = str(spec.get("command", name))
        available = shutil.which(command_name) is not None
        version = ""
        if available:
            try:
                process = subprocess.run([command_name, "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                version = (process.stdout or process.stderr).splitlines()[0] if process.stdout or process.stderr else ""
                available = process.returncode == 0
            except OSError:
                available = False
        required = bool(config.get(name, {}).get("enabled", False)) if name in {"github", "gitlab"} else bool(config.get("companions", {}).get(name, False))
        report[name] = {"available": available, "version": version, "required": required}
    report["rpi"] = {"available": (root / ".claude" / "commands" / "bootstrap").is_file() or (root / "AGENTS.md").is_file(), "required": bool(config.get("companions", {}).get("rpi", False))}
    print(json.dumps(report, indent=2))
    return 1 if any(value["required"] and not value["available"] for value in report.values()) else 0


def notify(root: Path, dry_run: bool) -> int:
    config = ns.load_config(root).get("notifications", {})
    if not dry_run and not bool(config.get("enabled", False)):
        print("SKIP: notifications are disabled in roadmap/northstar.toml")
        return 0
    variable = str(config.get("webhook_url_env", "NORTHSTAR_WEBHOOK_URL"))
    webhook = os.environ.get(variable, "")
    notification_format = str(config.get("format", "generic"))
    chain = root / "roadmap" / "audit.chain.jsonl"
    cursor = root / "roadmap" / ".notification-cursor"
    sent = int(cursor.read_text().strip()) if cursor.is_file() else 0
    records = [json.loads(line) for line in chain.read_text(encoding="utf-8").splitlines()[sent:]] if chain.is_file() else []
    if dry_run:
        print(json.dumps(records, indent=2))
        return 0
    if records and not webhook:
        raise ns.NorthstarError(f"Notification webhook environment variable {variable} is not set")
    for record in records:
        message = f"Northstar {record['event']}: {record['item']} {record['from']} → {record['to']} — {record['detail']}"
        if notification_format == "slack":
            payload = {"text": message}
        elif notification_format == "teams":
            payload = {"@type": "MessageCard", "@context": "https://schema.org/extensions", "summary": message, "text": message}
        else:
            payload = record
        request = urllib.request.Request(webhook, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status >= 300:
                raise ns.NorthstarError(f"Webhook returned HTTP {response.status}")
        sent += 1
        ns.atomic_write(cursor, f"{sent}\n")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="northstar-admin")
    result.add_argument("--root", type=Path, default=Path.cwd())
    commands = result.add_subparsers(dest="command", required=True)
    policy_parser = commands.add_parser("policy")
    policy_parser.add_argument("--base", type=Path)
    retry_parser = commands.add_parser("retry")
    retry_parser.add_argument("operation", nargs="?", default="all")
    reconcile_parser = commands.add_parser("reconcile-all")
    reconcile_parser.add_argument("--strategy", choices=["report", "canonical", "ignore"], default="report")
    reconcile_parser.add_argument("--actor", default="northstar-ci")
    archive_parser = commands.add_parser("archive")
    archive_parser.add_argument("--before")
    archive_parser.add_argument("--status", action="append", choices=["Done", "Deferred", "Retired"], default=[])
    archive_parser.add_argument("--apply", action="store_true")
    render_parser = commands.add_parser("render")
    render_parser.add_argument("--check", action="store_true")
    commands.add_parser("compatibility")
    notify_parser = commands.add_parser("notify")
    notify_parser.add_argument("--dry-run", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "policy":
            return policy(root, args.base)
        if args.command == "retry":
            return retry(root, args.operation)
        if args.command == "reconcile-all":
            return reconcile_all(root, args.strategy, args.actor)
        if args.command == "archive":
            days = int(ns.load_config(root).get("policy", {}).get("archive_after_days", 90))
            before = dt.datetime.fromisoformat(args.before).replace(tzinfo=dt.timezone.utc) if args.before else dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
            return archive(root, before, set(args.status or ["Done", "Deferred", "Retired"]), args.apply)
        if args.command == "render":
            return render(root, args.check)
        if args.command == "compatibility":
            return compatibility(root)
        if args.command == "notify":
            return notify(root, args.dry_run)
        return 0
    except (ns.NorthstarError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
