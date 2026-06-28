import tempfile
import unittest
import json
from pathlib import Path
from unittest import mock

from scripts import self_audit


class SelfAuditUniverseTests(unittest.TestCase):
    def test_universe_distinguishes_configured_names_from_observed_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            series_dir = root / "runs" / "sentiment" / "series"
            series_dir.mkdir(parents=True)
            (series_dir / "TICKER_NVDA.jsonl").write_text('{"score": 0.1}\n')
            (series_dir / "TICKER_RDDT.jsonl").write_text('{"score": 0.2}\n\n')
            (series_dir / "TICKER_CRM.jsonl").write_text("")

            names = ["TICKER:NVDA", "TICKER:RDDT", "TICKER:CRM", "TICKER:PATH"]
            with mock.patch.object(self_audit, "ROOT", root), \
                 mock.patch.object(self_audit, "_tracked_universe_names", return_value=names):
                health, note = self_audit.axis_universe()

        expected_health = 0.5 * (3 / 6) + 0.5 * (2 / 6)
        self.assertAlmostEqual(health, expected_health)
        self.assertIn("4 configured names", note)
        self.assertIn("3 wired series files", note)
        self.assertIn("2 observed series with rows", note)
        self.assertIn("2 rows total", note)
        self.assertIn("pending/no rows: CRM, PATH", note)
        self.assertNotIn("2 names tracked", note)


class SelfAuditParkedAxisTests(unittest.TestCase):
    def test_parked_axes_stay_visible_but_do_not_force_queue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "runs").mkdir()
            (root / "sim").mkdir()
            (root / "graph").mkdir()
            (root / "sim" / "RETIRED.md").write_text("PARKED\n")
            (root / "graph" / "RETIRED.md").write_text("PARKED\n")
            (root / "runs" / "QUEUE.json").write_text('{"items": []}')

            axes = [
                ("sim", lambda: (0.1, "sim parked note")),
                ("graph", lambda: (0.2, "graph parked note")),
                ("universe", lambda: (0.5, "active universe note")),
            ]

            with mock.patch.object(self_audit, "ROOT", root), \
                 mock.patch.object(self_audit, "AXES", axes):
                weakest = self_audit.run()

            audit = (root / "runs" / "SELF_AUDIT.md").read_text()
            queue = (root / "runs" / "QUEUE.json").read_text()

        self.assertEqual(weakest["axis"], "universe")
        self.assertIn("| sim | 0.1 | parked by sim/RETIRED.md", audit)
        self.assertIn("| graph | 0.2 | parked by graph/RETIRED.md", audit)
        self.assertIn("## Weakest actionable axis -> forcing function", audit)
        self.assertIn('"id": "AUDIT-universe"', queue)
        self.assertNotIn("AUDIT-sim", queue)
        self.assertNotIn("AUDIT-graph", queue)

    def test_stale_pending_parked_axis_items_are_removed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "runs").mkdir()
            (root / "sim").mkdir()
            (root / "graph").mkdir()
            (root / "sim" / "RETIRED.md").write_text("PARKED\n")
            (root / "graph" / "RETIRED.md").write_text("PARKED\n")
            (root / "runs" / "QUEUE.json").write_text(json.dumps({"items": [
                {"id": "AUDIT-sim", "status": "pending"},
                {"id": "AUDIT-graph", "status": "pending"},
                {"id": "AUDIT-signal", "status": "done"},
                {"id": "Q-001", "status": "pending"},
            ]}))

            axes = [
                ("sim", lambda: (0.1, "sim parked note")),
                ("graph", lambda: (0.2, "graph parked note")),
                ("universe", lambda: (0.5, "active universe note")),
            ]

            with mock.patch.object(self_audit, "ROOT", root), \
                 mock.patch.object(self_audit, "AXES", axes):
                weakest = self_audit.run()

            queue = json.loads((root / "runs" / "QUEUE.json").read_text())

        self.assertEqual(weakest["axis"], "universe")
        self.assertEqual(queue["items"][0]["id"], "AUDIT-universe")
        pending_ids = {item["id"] for item in queue["items"] if item.get("status") == "pending"}
        self.assertNotIn("AUDIT-sim", pending_ids)
        self.assertNotIn("AUDIT-graph", pending_ids)
        self.assertIn("Q-001", pending_ids)

    def test_all_non_actionable_axes_skip_queue_insertion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "runs").mkdir()
            (root / "sim").mkdir()
            (root / "graph").mkdir()
            (root / "sim" / "RETIRED.md").write_text("PARKED\n")
            (root / "graph" / "RETIRED.md").write_text("PARKED\n")
            (root / "runs" / "QUEUE.json").write_text(json.dumps({"items": [
                {"id": "AUDIT-sim", "status": "pending"},
                {"id": "Q-001", "status": "pending"},
            ]}))

            axes = [
                ("sim", lambda: (0.1, "sim parked note")),
                ("graph", lambda: (0.2, "graph parked note")),
            ]

            with mock.patch.object(self_audit, "ROOT", root), \
                 mock.patch.object(self_audit, "AXES", axes):
                weakest = self_audit.run()

            audit = (root / "runs" / "SELF_AUDIT.md").read_text()
            queue = json.loads((root / "runs" / "QUEUE.json").read_text())

        self.assertIsNone(weakest)
        self.assertIn("No actionable axis found; queue insertion skipped", audit)
        self.assertEqual([item["id"] for item in queue["items"]], ["Q-001"])


if __name__ == "__main__":
    unittest.main()
