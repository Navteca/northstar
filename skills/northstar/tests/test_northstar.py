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

    def add_ready(self):
        northstar.add_item(args(
            root=self.root,
            title="Team invitations",
            priority="P1",
            status="Ready",
            story="As a workspace admin, I want to invite teammates, so that I can onboard them without support.",
            acceptance=["Admin can invite an email address", "Invitation can be accepted once"],
            origin="native",
            origin_url="",
            home="local",
        ))

    def pickup(self, **overrides):
        values = dict(root=self.root, item="RM-001", owner="Maya", branch="feat/rm-001-invitations", home=None, plan="", planning=False)
        values.update(overrides)
        northstar.pickup_item(args(**values))

    def test_init_and_add_produce_valid_compact_roadmap(self):
        self.add_ready()
        self.assertEqual(northstar.validate(self.root), [])
        header = (self.root / "ROADMAP.md").read_text().splitlines()[2]
        self.assertEqual(northstar.split_row(header), northstar.HEADER)
        self.assertEqual(northstar.HEADER, ["ID", "P", "Status", "Story", "Owner", "Branch", "Home", "GitHub", "GitLab", "Plan", "Sync"])

    def test_user_story_accepts_a_an_and_the(self):
        for index, article in enumerate(("a developer", "an administrator", "the account owner")):
            northstar.add_item(args(
                root=self.root,
                title=f"Story {index}",
                priority="P2",
                status="Planned",
                story=f"As {article}, I want a capability, so that I receive value.",
                acceptance=["The outcome is observable"],
                origin="native",
                origin_url="",
                home="local",
            ))
        self.assertEqual(northstar.validate(self.root), [])

    def test_pickup_is_exclusive_without_requiring_wayfinder(self):
        self.add_ready()
        self.pickup()
        with self.assertRaises(northstar.NorthstarError):
            self.pickup(owner="Iker")
        item = northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        self.assertEqual((item["Status"], item["Owner"], item["Branch"], item["Home"], item["Plan"]), ("In Progress", "Maya", "feat/rm-001-invitations", "local", "—"))

    def test_wayfinder_planning_requires_and_records_one_plan(self):
        self.add_ready()
        with self.assertRaises(northstar.NorthstarError):
            self.pickup(planning=True)
        self.pickup(planning=True, plan="https://github.com/acme/product/issues/77")
        item = northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        self.assertEqual((item["Status"], item["Plan"]), ("Planning", "https://github.com/acme/product/issues/77"))
        northstar.link_plan(args(
            root=self.root,
            item="RM-001",
            plan="https://github.com/acme/product/issues/77",
            status="Ready",
            reason="The map has no remaining fog or open decisions",
        ))
        self.assertEqual(northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")["Status"], "Ready")
        self.pickup(owner="Maya")
        self.assertEqual(northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")["Status"], "In Progress")

    def test_handoff_requires_owner_or_audited_override(self):
        self.add_ready()
        self.pickup()
        with self.assertRaises(northstar.NorthstarError):
            northstar.handoff_item(args(root=self.root, item="RM-001", to="Iker", actor="Product", reason="Maya unavailable", override=False))
        northstar.handoff_item(args(root=self.root, item="RM-001", to="Iker", actor="Product", reason="Maya unavailable", override=True))
        item = northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        self.assertEqual(item["Owner"], "Iker")
        self.assertIn("Handoff override", (self.root / "roadmap" / "audit.md").read_text())

    def test_close_requires_acceptance_and_durable_context(self):
        self.add_ready()
        self.pickup()
        with self.assertRaises(northstar.NorthstarError):
            northstar.close_item(args(root=self.root, item="RM-001", context="Repository: PR #42", evidence="PR #42"))
        brief = self.root / "roadmap" / "items" / "RM-001.md"
        northstar.atomic_write(brief, brief.read_text().replace("- [ ]", "- [x]"))
        northstar.close_item(args(root=self.root, item="RM-001", context="Repository: PR #42 and docs/architecture.md", evidence="PR #42"))
        self.assertEqual(northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")["Status"], "Done")
        self.assertEqual(northstar.validate(self.root), [])

    def test_import_keeps_provenance_and_source_link(self):
        northstar.add_item(args(
            root=self.root,
            title="Imported work",
            priority="P2",
            status="Candidate",
            story="As a maintainer, I want imported work tracked, so that the roadmap remains canonical.",
            acceptance=["Original source is linked"],
            origin="github",
            origin_url="https://github.com/example/product/issues/42",
            home="github",
        ))
        item = northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        self.assertIn("github.com/example/product/issues/42", item["GitHub"])
        self.assertEqual(item["Home"], "github")
        brief = (self.root / "roadmap" / "items" / "RM-001.md").read_text()
        self.assertIn("- Origin: github", brief)

    def test_home_tracker_must_have_its_link(self):
        with self.assertRaises(northstar.NorthstarError):
            northstar.add_item(args(
                root=self.root,
                title="Missing GitHub home",
                priority="P2",
                status="Ready",
                story="As a maintainer, I want a home issue, so that work has one authority.",
                acceptance=["A home issue exists"],
                origin="native",
                origin_url="",
                home="github",
            ))

    def test_sync_state_does_not_replace_work_status(self):
        self.add_ready()
        roadmap = northstar.Roadmap.load(self.root / "ROADMAP.md")
        item = roadmap.find("RM-001")
        item["Sync"] = northstar.sync_state([{"service": "github", "status": "ok"}, {"service": "gitlab", "status": "error"}])
        roadmap.save()
        updated = northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        self.assertEqual((updated["Status"], updated["Sync"]), ("Ready", "Partial"))

    def test_update_reprioritizes_and_records_reason(self):
        self.add_ready()
        northstar.update_item(args(root=self.root, item="RM-001", priority="P0", status="Deferred", title=None, reason="Dependency moved to next quarter"))
        item = northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        self.assertEqual((item["P"], item["Status"]), ("P0", "Deferred"))
        self.assertIn("Dependency moved", (self.root / "roadmap" / "audit.md").read_text())

    def test_reconciliation_reports_drift_without_changing_work_status(self):
        self.add_ready()
        item = northstar.Roadmap.load(self.root / "ROADMAP.md").find("RM-001")
        report = northstar.reconciliation_report({}, item, [{"service": "github", "status": "ok", "state": "closed", "assignees": [], "title": "External edit"}])
        self.assertEqual(report["canonical"]["status"], "Ready")
        self.assertEqual(report["differences"][0]["field"], "state")


if __name__ == "__main__":
    unittest.main()
