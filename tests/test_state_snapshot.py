import json
import unittest
import tempfile
from pathlib import Path
from unittest import mock

from scripts import state_snapshot


RAW_EDGE = {
    "n": 25,
    "n_raw_points": 30,
    "min_n": 24,
    "verdict": "EDGE",
    "authoritative": True,
    "circularity_flag": False,
    "best_lag": 2,
    "best_corr": 0.51,
}

NOISE_PERM = {
    "verdict": "EDGE_IS_NOISE",
    "p_value": 0.191,
    "significant_at_0.10": False,
}

SURVIVES_PERM = {
    "verdict": "EDGE_SURVIVES_NULL",
    "p_value": 0.04,
    "significant_at_0.10": True,
}

PHASE = {"phase_name": "Unproven", "phase": 0, "caps": {"single_pos": 0.2}}


def verdict(n=10, verdict="PRELIMINARY", authoritative=False):
    return {
        "n": n,
        "n_raw_points": n,
        "min_n": 24,
        "verdict": verdict,
        "authoritative": authoritative,
        "circularity_flag": False,
        "best_lag": None,
        "best_corr": None,
    }


class StateSnapshotEligibilityTest(unittest.TestCase):
    def build_with(self, probes, perms):
        def probe_side_effect(entity):
            return dict(probes.get(entity, verdict()))

        def perm_side_effect(entity, **_kwargs):
            return dict(perms.get(entity, {"significant_at_0.10": False, "p_value": 1.0, "verdict": "PRELIMINARY_NULL"}))

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "state").mkdir()
            (root / "state" / "risk_phase.json").write_text(json.dumps(PHASE))
            with mock.patch.object(state_snapshot, "ROOT", root), \
                 mock.patch.object(state_snapshot, "NAMES", list(probes)), \
                 mock.patch.object(state_snapshot, "probe", side_effect=probe_side_effect), \
                 mock.patch.object(state_snapshot, "permutation_test", side_effect=perm_side_effect), \
                 mock.patch.object(state_snapshot, "_git", return_value="abc123"):
                return state_snapshot.build()

    def test_raw_edge_that_fails_permutation_does_not_promote_or_trade(self):
        output = self.build_with({"TICKER:NVDA": RAW_EDGE}, {"TICKER:NVDA": NOISE_PERM})

        self.assertIn("Raw authoritative EDGE failed the permutation trade gate: TICKER:NVDA", output)
        self.assertIn("Alpha pipeline should have no eligible proposal", output)
        self.assertIn("Respect alpha_pipeline zero-eligible outcome", output)
        self.assertIn("perm=EDGE_IS_NOISE p=0.191 sig=False", output)
        self.assertNotIn("Promote the authoritative EDGE", output)
        self.assertNotIn("review, place", output)
        self.assertNotIn("safety review -> trade", output)

    def test_surviving_permutation_can_trigger_propose_only_action(self):
        output = self.build_with({"TICKER:NVDA": RAW_EDGE}, {"TICKER:NVDA": SURVIVES_PERM})

        self.assertIn("Trade-eligible EDGE exists after permutation gate: TICKER:NVDA", output)
        self.assertIn("run alpha_pipeline for PROPOSED review handoff", output)
        self.assertIn("only PROPOSED artifacts that survive safety review may advance", output)
        self.assertNotIn("review, place", output)
        self.assertNotIn("safety review -> trade", output)


if __name__ == "__main__":
    unittest.main()
