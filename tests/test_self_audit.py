import tempfile
import unittest
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

        self.assertEqual(health, 2 / 6)
        self.assertIn("4 configured names", note)
        self.assertIn("2 observed series with rows", note)
        self.assertIn("2 rows total", note)
        self.assertIn("pending/no rows: CRM, PATH", note)
        self.assertNotIn("2 names tracked", note)


if __name__ == "__main__":
    unittest.main()
