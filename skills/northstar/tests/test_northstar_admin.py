from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ADMIN_PATH = Path(__file__).parents[1] / "scripts" / "northstar_admin.py"
INSTALLER_PATH = Path(__file__).parents[2] / "setup-northstar" / "scripts" / "install_operational_assets.py"
SPEC = importlib.util.spec_from_file_location("northstar_admin", ADMIN_PATH)
assert SPEC and SPEC.loader
admin = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = admin
SPEC.loader.exec_module(admin)
ns = admin.ns


def args(**values):
    defaults = {"apply": True, "local_only": True, "actor": "Maya"}
    defaults.update(values)
    return argparse.Namespace(**defaults)


class NorthstarAdminTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        ns.init_workspace(self.root)
        ns.add_item(args(root=self.root, title="Team invitations", priority="P1", status="Ready", story="As a workspace admin, I want to invite teammates, so that I can onboard them without support.", acceptance=["Admin can invite an email address"], origin="native", origin_url=""))

    def tearDown(self):
        self.temporary.cleanup()

    def enable_github(self):
        config = self.root / "roadmap" / "northstar.toml"
        config.write_text(config.read_text().replace("enabled = false\nrepository", "enabled = true\nrepository") + '\n[identities.Maya]\ngithub = "maya-gh"\n')

    def test_audit_chain_is_tamper_evident(self):
        self.assertEqual(admin.verify_audit(self.root), [])
        path = self.root / "roadmap" / "audit.chain.jsonl"
        record = json.loads(path.read_text().splitlines()[0])
        record["actor"] = "Mallory"
        ns.atomic_write(path, json.dumps(record) + "\n")
        self.assertTrue(any("record hash mismatch" in error for error in admin.verify_audit(self.root)))

    def test_failed_sync_is_journaled_and_retry_replays_the_event(self):
        self.enable_github()
        calls: list[list[str]] = []

        def failing(command_args, stdin=None):
            calls.append(command_args)
            raise ns.NorthstarError("offline")

        with mock.patch.object(ns, "command", failing):
            ns.pickup_item(args(root=self.root, item="RM-001", owner="Maya", branch="feat/rm-001", plan="", planning=False, local_only=False))
        item = ns.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        self.assertEqual((item["Status"], item["Sync"]), ("In Progress", "Error"))
        record = ns.latest_journal(self.root, "RM-001")
        self.assertEqual((record["event"], record["remote_event"], record["status"]), ("picked-up", "claimed", "Error"))

        def working(command_args, stdin=None):
            calls.append(command_args)
            if command_args[:3] == ["gh", "issue", "list"]:
                return "[]"
            if command_args[:2] == ["gh", "api"]:
                return json.dumps({"html_url": "https://github.com/acme/product/issues/7"})
            return ""

        with mock.patch.object(ns, "command", working):
            self.assertEqual(admin.retry(self.root), 0)
        item = ns.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        self.assertEqual((item["Sync"], item["Issue"]), ("Synced", "[#7](https://github.com/acme/product/issues/7)"))
        self.assertIn("--add-assignee", [arg for call in calls for arg in call])
        self.assertIn("- Issue: https://github.com/acme/product/issues/7", (self.root / "roadmap" / "items" / "RM-001.md").read_text())
        self.assertEqual(ns.validate(self.root), [])

    def test_issue_creation_reuses_existing_issue_by_id(self):
        self.enable_github()
        item = ns.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        with mock.patch.object(ns, "command", lambda a, stdin=None: json.dumps([{"url": "https://github.com/acme/product/issues/3"}])) as _:
            ns.ensure_issue(ns.load_config(self.root), item, "")
        self.assertEqual(item["Issue"], "[#3](https://github.com/acme/product/issues/3)")

    def test_render_produces_stable_views_and_dashboard(self):
        self.assertEqual(admin.render(self.root, check=False), 0)
        self.assertEqual(admin.render(self.root, check=True), 0)
        self.assertIn("RM-001", (self.root / "roadmap" / "dashboard.html").read_text())

    def test_policy_rejects_illegal_transition(self):
        base = self.root / "base-roadmap.md"
        shutil.copyfile(self.root / "ROADMAP.md", base)
        roadmap = ns.Roadmap.load(self.root / "ROADMAP.md")
        roadmap.find("RM-001")["Status"] = "Done"
        roadmap.find("RM-001")["Branch"] = "feat/rm-001"
        roadmap.save()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(admin.policy(self.root, base), 1)

    def test_archive_preserves_brief_and_prevents_id_reuse(self):
        ns.pickup_item(args(root=self.root, item="RM-001", owner="Maya", branch="feat/rm-001", plan="", planning=False))
        brief = self.root / "roadmap" / "items" / "RM-001.md"
        ns.atomic_write(brief, brief.read_text().replace("- [ ]", "- [x]"))
        ns.close_item(args(root=self.root, item="RM-001", context="Repository: PR #1", evidence="PR #1"))
        future = admin.dt.datetime(2100, 1, 1, tzinfo=admin.dt.timezone.utc)
        self.assertEqual(admin.archive(self.root, future, {"Done"}, apply=True), 0)
        self.assertEqual(ns.Roadmap.load(self.root / "ROADMAP.md").items, [])
        self.assertTrue(brief.is_file())
        self.assertEqual(ns.next_id(ns.Roadmap.load(self.root / "ROADMAP.md"), self.root), "RM-002")

    def test_installer_vendors_engine_and_preserves_existing_workflows(self):
        run = lambda *extra: subprocess.run([sys.executable, str(INSTALLER_PATH), "--root", str(self.root), *extra], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        preview = run()
        self.assertEqual(preview.returncode, 0)
        self.assertFalse((self.root / "roadmap" / "bin").exists())
        self.assertEqual(run("--apply").returncode, 0)
        self.assertTrue((self.root / "roadmap" / "bin" / "northstar.py").is_file())
        self.assertTrue((self.root / ".github" / "workflows" / "northstar-policy.yml").is_file())
        self.assertIn("roadmap/.northstar.lock", (self.root / ".gitignore").read_text())
        self.assertEqual(run("--apply").returncode, 1)
        # The vendored engine runs standalone.
        vendored = subprocess.run([sys.executable, str(self.root / "roadmap" / "bin" / "northstar_admin.py"), "--root", str(self.root), "policy"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(vendored.returncode, 0, vendored.stderr)


if __name__ == "__main__":
    unittest.main()
