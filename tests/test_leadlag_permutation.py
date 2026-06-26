import unittest
from unittest.mock import patch

from evals import leadlag_permutation as permutation


ENTITY = "TICKER:UNIT"


def leading_points(n=12):
    sent = [0, 1] * (n // 2)
    if len(sent) < n:
        sent.append(0)
    dsent = [right - left for left, right in zip(sent, sent[1:])]
    price_deltas = [0] + dsent[:-1]
    price = [100]
    for delta in price_deltas:
        price.append(price[-1] + delta)
    return list(zip(sent, price))


def flat_price_points(n=12):
    return list(zip(([0, 1] * ((n + 1) // 2))[:n], [100] * n))


class LeadLagPermutationTest(unittest.TestCase):
    def run_with_points(self, points, **kwargs):
        with patch.object(permutation, "_spaced_points", return_value=points):
            return permutation.permutation_test(ENTITY, **kwargs)

    def test_insufficient_spaced_points_fail_closed(self):
        result = self.run_with_points([(0.1, 100), (0.2, 101), (0.3, 102)])

        self.assertEqual(result["entity"], ENTITY)
        self.assertEqual(result["n"], 3)
        self.assertEqual(result["verdict"], "INSUFFICIENT")
        self.assertFalse(result["authoritative"])
        self.assertIn(">=4 spaced points", result["note"])

    def test_seeded_permutation_output_is_deterministic(self):
        points = leading_points()

        first = self.run_with_points(points, k=200, max_lag=2, min_n=12, seed=17)
        second = self.run_with_points(points, k=200, max_lag=2, min_n=12, seed=17)

        self.assertEqual(first, second)
        self.assertEqual(first["k_shuffles"], 200)
        self.assertEqual(first["observed_best_poslag_corr"], 1.0)

    def test_min_n_controls_authoritative_verdict_prefix(self):
        points = flat_price_points()

        preliminary = self.run_with_points(points, k=40, max_lag=2, min_n=13, seed=3)
        authoritative = self.run_with_points(points, k=40, max_lag=2, min_n=12, seed=3)

        self.assertEqual(preliminary["n"], 12)
        self.assertFalse(preliminary["authoritative"])
        self.assertEqual(preliminary["verdict"], "PRELIMINARY_NULL")
        self.assertIn("PRELIMINARY", preliminary["note"])
        self.assertTrue(authoritative["authoritative"])
        self.assertEqual(authoritative["verdict"], "EDGE_IS_NOISE")
        self.assertEqual(authoritative["min_n"], 12)

    def test_positive_lag_edge_can_survive_permutation_null(self):
        result = self.run_with_points(leading_points(), k=500, max_lag=2, min_n=12, seed=3)

        self.assertTrue(result["authoritative"])
        self.assertEqual(result["observed_best_poslag_corr"], 1.0)
        self.assertLessEqual(result["p_value"], 0.10)
        self.assertTrue(result["significant_at_0.10"])
        self.assertEqual(result["verdict"], "EDGE_SURVIVES_NULL")

    def test_best_poslag_corr_ignores_contemporaneous_only_alignment(self):
        self.assertAlmostEqual(
            permutation._best_poslag_corr([-2, -2, -2, -2, -1], [-2, -2, -2, -2, -1], max_lag=2),
            0.0,
        )
        self.assertAlmostEqual(
            permutation._best_poslag_corr([-2, -2, -2, -1, -2], [-2, -2, -2, -2, -1], max_lag=2),
            1.0,
        )

    def test_non_predictive_series_fails_permutation_null(self):
        result = self.run_with_points(flat_price_points(), k=100, max_lag=2, min_n=12, seed=3)

        self.assertTrue(result["authoritative"])
        self.assertEqual(result["observed_best_poslag_corr"], 0.0)
        self.assertEqual(result["p_value"], 1.0)
        self.assertFalse(result["significant_at_0.10"])
        self.assertEqual(result["verdict"], "EDGE_IS_NOISE")


if __name__ == "__main__":
    unittest.main()
