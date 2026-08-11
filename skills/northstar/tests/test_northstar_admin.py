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
        ns.add_item(args(
            root=self.root,
            title="Team invitations",
            priority="P1",
            status="Ready",
            story="As a workspace admin, I want to invite teammates, so that I can onboard them without support.",
            acceptance=["Admin can invite an email address"],
            origin="native",
            origin_url="",
            home="local",
        ))

    def tearDown(self):
        self.temporary.cleanup()

    def test_audit_chain_is_tamper_evident(self):
        self.assertEqual(admin.verify_audit(self.root), [])
        path = self.root / "roadmap" / "audit.chain.jsonl"
        record = json.loads(path.read_text().splitlines()[0])
        record["actor"] = "Mallory"
        ns.atomic_write(path, json.dumps(record) + "\n")
        self.assertTrue(any("record hash mismatch" in error for error in admin.verify_audit(self.root)))

    def test_failed_sync_creates_durable_outbox_operation(self):
        ns.journal(self.root, "RM-001", "updated", [{"service": "github", "status": "error", "detail": "offline"}])
        records = list((self.root / "roadmap" / "outbox").glob("*.json"))
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0].read_text())["status"], "Error")
        self.assertEqual(admin.retry(self.root, "all"), 1)
        self.assertTrue(records[0].is_file())

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
        ns.pickup_item(args(root=self.root, item="RM-001", owner="Maya", branch="feat/rm-001", home=None, plan="", planning=False))
        brief = self.root / "roadmap" / "items" / "RM-001.md"
        ns.atomic_write(brief, brief.read_text().replace("- [ ]", "- [x]"))
        ns.close_item(args(root=self.root, item="RM-001", context="Repository: PR #1", evidence="PR #1"))
        future = admin.dt.datetime(2100, 1, 1, tzinfo=admin.dt.timezone.utc)
        self.assertEqual(admin.archive(self.root, future, {"Done"}, apply=True), 0)
        self.assertEqual(ns.Roadmap.load(self.root / "ROADMAP.md").items, [])
        self.assertTrue((self.root / "roadmap" / "items" / "RM-001.md").is_file())
        roadmap = ns.Roadmap.load(self.root / "ROADMAP.md")
        self.assertEqual(ns.next_id(roadmap, self.root), "RM-002")

    def test_operational_asset_installer_previews_then_preserves_existing_files(self):
        preview = subprocess.run([sys.executable, str(INSTALLER_PATH), "--root", str(self.root), "--service", "github"], text=True, stdout=subprocess.PIPE, check=False)
        self.assertEqual(preview.returncode, 0)
        self.assertFalse((self.root / ".github" / "workflows").exists())
        applied = subprocess.run([sys.executable, str(INSTALLER_PATH), "--root", str(self.root), "--service", "github", "--apply"], text=True, stdout=subprocess.PIPE, check=False)
        self.assertEqual(applied.returncode, 0)
        conflict = subprocess.run([sys.executable, str(INSTALLER_PATH), "--root", str(self.root), "--service", "github", "--apply"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(conflict.returncode, 1)


if __name__ == "__main__":
    unittest.main()
