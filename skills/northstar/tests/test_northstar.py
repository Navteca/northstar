from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "northstar.py"
SPEC = importlib.util.spec_from_file_location("northstar_engine", MODULE_PATH)
assert SPEC and SPEC.loader
northstar = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = northstar
SPEC.loader.exec_module(northstar)

STORY = "As a workspace admin, I want to invite teammates, so that I can onboard them without support."


def args(**values):
    defaults = {"apply": True, "local_only": True, "actor": "Maya"}
    defaults.update(values)
    return argparse.Namespace(**defaults)


class NorthstarTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        northstar.init_workspace(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def add(self, **overrides):
        values = dict(root=self.root, title="Team invitations", priority="P1", status="Ready", story=STORY, acceptance=["Admin can invite an email address", "Invitation can be accepted once"], origin="native", origin_url="")
        values.update(overrides)
        northstar.add_item(args(**values))

    def pickup(self, **overrides):
        values = dict(root=self.root, item="RM-001", owner="Maya", branch="feat/rm-001-invitations", plan="", planning=False)
        values.update(overrides)
        northstar.pickup_item(args(**values))

    def item(self, item_id="RM-001"):
        return northstar.Roadmap.load(self.root / "ROADMAP.md").find(item_id)

    def test_init_and_add_produce_valid_compact_roadmap(self):
        self.add()
        self.assertEqual(northstar.validate(self.root), [])
        header = (self.root / "ROADMAP.md").read_text().splitlines()[2]
        self.assertEqual(northstar.split_row(header), northstar.HEADER)
        self.assertEqual(northstar.HEADER, ["ID", "P", "Status", "Story", "Owner", "Branch", "Issue", "Plan", "Sync"])

    def test_user_story_accepts_a_an_and_the(self):
        for index, article in enumerate(("a developer", "an administrator", "the account owner")):
            self.add(title=f"Story {index}", priority="P2", status="Planned", story=f"As {article}, I want a capability, so that I receive value.", acceptance=["The outcome is observable"])
        self.assertEqual(northstar.validate(self.root), [])

    def test_pickup_is_exclusive_without_requiring_wayfinder(self):
        self.add()
        self.pickup()
        with self.assertRaises(northstar.NorthstarError):
            self.pickup(owner="Iker")
        item = self.item()
        self.assertEqual((item["Status"], item["Owner"], item["Branch"], item["Issue"], item["Plan"], item["Sync"]), ("In Progress", "Maya", "feat/rm-001-invitations", "—", "—", "Local"))

    def test_pickup_resolves_owner_from_github_login(self):
        self.add()
        config = self.root / "roadmap" / "northstar.toml"
        config.write_text(config.read_text() + '\n[identities.Maya]\ngithub = "maya-gh"\n')
        with self.assertRaises(northstar.NorthstarError):
            self.pickup(owner="", owner_login="stranger", actor="")
        self.pickup(owner="", owner_login="maya-gh", actor="")
        self.assertEqual(self.item()["Owner"], "Maya")
        self.assertIn("| Picked up | Maya |", (self.root / "roadmap" / "items" / "RM-001.md").read_text())

    def test_wayfinder_planning_requires_and_records_one_plan(self):
        self.add()
        with self.assertRaises(northstar.NorthstarError):
            self.pickup(planning=True)
        self.pickup(planning=True, plan="https://github.com/acme/product/issues/77")
        self.assertEqual((self.item()["Status"], self.item()["Plan"]), ("Planning", "https://github.com/acme/product/issues/77"))
        northstar.link_plan(args(root=self.root, item="RM-001", plan="https://github.com/acme/product/issues/77", status="Ready", reason="The map has no remaining fog"))
        self.assertEqual(self.item()["Status"], "Ready")
        self.pickup(owner="Maya")
        self.assertEqual(self.item()["Status"], "In Progress")

    def test_spec_kit_route_is_recorded_and_requires_a_plan(self):
        self.add()
        with self.assertRaises(northstar.NorthstarError):
            self.pickup(planning=True, plan_kind="Spec Kit")
        self.pickup(planning=True, plan_kind="Spec Kit", plan="docs/specs/rm-001.md")
        self.assertIn("- Plan kind: Spec Kit", (self.root / "roadmap" / "items" / "RM-001.md").read_text())
        self.assertEqual(northstar.validate(self.root), [])

    def test_rpi_execution_method_is_recorded_separately_from_plan_kind(self):
        self.add()
        self.pickup(execution_method="RPI")
        brief = (self.root / "roadmap" / "items" / "RM-001.md").read_text()
        self.assertIn("- Plan kind: Direct", brief)
        self.assertIn("- Execution method: RPI", brief)
        self.assertEqual(northstar.validate(self.root), [])

    def test_invalid_plan_kind_is_rejected(self):
        self.add()
        brief = self.root / "roadmap" / "items" / "RM-001.md"
        northstar.atomic_write(brief, brief.read_text().replace("- Plan kind: Direct", "- Plan kind: Other"))
        self.assertTrue(any("Plan kind must be" in error for error in northstar.validate(self.root)))

    def test_engine_enforces_lifecycle_transitions(self):
        self.add()
        with self.assertRaises(northstar.NorthstarError):  # Ready → Done must go through pickup and close
            northstar.update_item(args(root=self.root, item="RM-001", priority=None, status="Done", title=None, reason="shortcut"))
        with self.assertRaises(northstar.NorthstarError):  # Ready → Blocked is not a legal move
            northstar.update_item(args(root=self.root, item="RM-001", priority=None, status="Blocked", title=None, reason="shortcut"))
        self.pickup()
        northstar.update_item(args(root=self.root, item="RM-001", priority=None, status="Blocked", title=None, reason="waiting on vendor"))
        self.assertEqual(self.item()["Status"], "Blocked")
        northstar.update_item(args(root=self.root, item="RM-001", priority=None, status="In Progress", title=None, reason="vendor delivered"))
        self.assertEqual(self.item()["Status"], "In Progress")

    def test_handoff_requires_owner_or_audited_override(self):
        self.add()
        self.pickup()
        with self.assertRaises(northstar.NorthstarError):
            northstar.handoff_item(args(root=self.root, item="RM-001", to="Iker", actor="Product", reason="Maya unavailable", override=False))
        northstar.handoff_item(args(root=self.root, item="RM-001", to="Iker", actor="Product", reason="Maya unavailable", override=True))
        self.assertEqual(self.item()["Owner"], "Iker")
        self.assertIn("Handoff override", (self.root / "roadmap" / "audit.md").read_text())

    def test_close_requires_acceptance_and_durable_context(self):
        self.add()
        self.pickup()
        with self.assertRaises(northstar.NorthstarError):
            northstar.close_item(args(root=self.root, item="RM-001", context="Repository: PR #42", evidence="PR #42"))
        brief = self.root / "roadmap" / "items" / "RM-001.md"
        northstar.atomic_write(brief, brief.read_text().replace("- [ ]", "- [x]"))
        northstar.close_item(args(root=self.root, item="RM-001", context="Repository: PR #42 and docs/architecture.md", evidence="PR #42"))
        self.assertEqual(self.item()["Status"], "Done")
        self.assertEqual(northstar.validate(self.root), [])

    def test_import_keeps_provenance_and_source_link(self):
        with self.assertRaises(northstar.NorthstarError):
            self.add(origin="github", origin_url="not-a-github-issue")
        self.add(title="Imported work", priority="P2", status="Candidate", origin="github", origin_url="https://github.com/example/product/issues/42")
        self.assertEqual(self.item()["Issue"], "[#42](https://github.com/example/product/issues/42)")
        brief = (self.root / "roadmap" / "items" / "RM-001.md").read_text()
        self.assertIn("- Origin: github", brief)
        self.assertIn("- Issue: https://github.com/example/product/issues/42", brief)
        self.assertEqual(northstar.validate(self.root), [])

    def test_issue_column_must_be_a_github_issue_link(self):
        self.add()
        roadmap = northstar.Roadmap.load(self.root / "ROADMAP.md")
        roadmap.find("RM-001")["Issue"] = "[#1](https://gitlab.com/acme/product/-/issues/1)"
        roadmap.save()
        self.assertTrue(any("GitHub issue" in error for error in northstar.validate(self.root)))

    def test_story_link_cannot_escape_item_directory(self):
        self.add()
        roadmap = northstar.Roadmap.load(self.root / "ROADMAP.md")
        roadmap.find("RM-001")["Story"] = "[Unsafe](../../outside.md)"
        roadmap.save()
        self.assertTrue(any("must stay under roadmap/items" in error for error in northstar.validate(self.root)))

    def test_sync_state_does_not_replace_work_status(self):
        self.add()
        roadmap = northstar.Roadmap.load(self.root / "ROADMAP.md")
        roadmap.find("RM-001")["Sync"] = northstar.sync_state({"status": "error", "detail": "offline"})
        roadmap.save()
        self.assertEqual((self.item()["Status"], self.item()["Sync"]), ("Ready", "Error"))
        self.assertEqual(northstar.sync_state(None), "Local")
        self.assertEqual(northstar.sync_state({"status": "ok"}), "Synced")

    def test_update_reprioritizes_and_records_reason(self):
        self.add()
        northstar.update_item(args(root=self.root, item="RM-001", priority="P0", status="Deferred", title=None, reason="Dependency moved to next quarter"))
        self.assertEqual((self.item()["P"], self.item()["Status"]), ("P0", "Deferred"))
        self.assertIn("Dependency moved", (self.root / "roadmap" / "audit.md").read_text())

    def test_reconciliation_reports_drift_without_changing_work_status(self):
        self.add()
        report = northstar.reconciliation_report({}, self.item(), {"status": "ok", "state": "closed", "assignees": [], "title": "External edit"})
        self.assertEqual(report["canonical"]["status"], "Ready")
        self.assertEqual(report["differences"][0]["field"], "state")


if __name__ == "__main__":
    unittest.main()
