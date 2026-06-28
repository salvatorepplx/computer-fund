import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from evals import leadlag_real


ENTITY = "TICKER:TEST"
BASE_TS = datetime(2026, 6, 26, tzinfo=timezone.utc)


def ts_at(seconds):
    return (BASE_TS + timedelta(seconds=seconds)).isoformat()


def row(score, price, *, seconds=0, score_raw=None, ts=None):
    data = {"price_proxy": price, "ts": ts if ts is not None else ts_at(seconds)}
    if score is not None:
        data["score"] = score
    if score_raw is not None:
        data["score_raw"] = score_raw
    return data


def series_from_diffs(sentiment_diffs, price_diffs, *, score_key="score", gap_s=180):
    sentiment = [0.0]
    price = [100.0]
    for delta in sentiment_diffs:
        sentiment.append(sentiment[-1] + delta)
    for delta in price_diffs:
        price.append(price[-1] + delta)

    rows = []
    for index, (score, price_proxy) in enumerate(zip(sentiment, price)):
        data = {"price_proxy": price_proxy, "ts": ts_at(index * gap_s)}
        data[score_key] = score
        rows.append(data)
    return rows


class LeadLagRealProbeTests(unittest.TestCase):
    def probe_with_series(self, series, **kwargs):
        with patch.object(leadlag_real, "load_series", return_value=series):
            return leadlag_real.probe(ENTITY, **kwargs)

    def test_fewer_than_three_time_spaced_points_is_insufficient(self):
        result = self.probe_with_series([
            row(0.1, 100.0, seconds=0),
            row(0.2, 101.0, seconds=180),
            {"score": 0.3, "ts": ts_at(360)},
            {"price_proxy": 103.0, "ts": ts_at(540)},
        ])

        self.assertEqual(result["verdict"], "INSUFFICIENT")
        self.assertEqual(result["n"], 2)
        self.assertFalse(result["authoritative"])
        self.assertIn("need >=3 aligned points", result["note"])

    def test_below_min_n_edge_is_preliminary_and_non_authoritative(self):
        series = series_from_diffs(
            [-0.3, -0.3, -0.2, 0.1],
            [0.5, -0.3, -0.3, -0.2],
        )

        result = self.probe_with_series(series, min_n=6, max_lag=1, min_corr=0.9)

        self.assertEqual(result["n_raw_points"], 5)
        self.assertEqual(result["n"], 5)
        self.assertEqual(result["verdict"], "PRELIMINARY_EDGE")
        self.assertEqual(result["best_lag"], 1)
        self.assertFalse(result["circularity_flag"])
        self.assertLess(abs(result["contemp_corr"]), 0.6)
        self.assertFalse(result["authoritative"])
        self.assertIn("Not a basis for capital", result["note"])

    def test_at_or_above_min_n_authoritative_edge_and_kill(self):
        edge_series = series_from_diffs(
            [-0.3, -0.3, -0.3, -0.1, 0.1],
            [1.0, -0.3, -0.3, -0.3, -0.1],
        )
        kill_series = series_from_diffs(
            [-0.3, -0.3, -0.3, -0.1, 0.1],
            [1.0, -1.0, 1.0, -1.0, 1.0],
        )

        edge = self.probe_with_series(edge_series, min_n=6, max_lag=1, min_corr=0.9)
        kill = self.probe_with_series(kill_series, min_n=6, max_lag=1, min_corr=0.9)

        self.assertEqual(edge["n_raw_points"], 6)
        self.assertEqual(edge["n"], 6)
        self.assertEqual(edge["verdict"], "EDGE")
        self.assertTrue(edge["authoritative"])
        self.assertEqual(edge["best_lag"], 1)
        self.assertGreaterEqual(edge["best_corr"], 0.9)
        self.assertFalse(edge["circularity_flag"])
        self.assertLess(abs(edge["contemp_corr"]), 0.6)
        self.assertEqual(edge["note"], "Authoritative read.")

        self.assertEqual(kill["n_raw_points"], 6)
        self.assertEqual(kill["n"], 6)
        self.assertEqual(kill["verdict"], "KILL")
        self.assertTrue(kill["authoritative"])
        self.assertEqual(kill["note"], "Authoritative read.")

    def test_positive_lag_wins_tie_break_for_edge_selection(self):
        series = series_from_diffs(
            [-0.3, -0.3, -0.2, 0.1],
            [0.5, -0.3, -0.3, -0.2],
        )

        result = self.probe_with_series(series, min_n=5, max_lag=1, min_corr=0.9)

        self.assertEqual(result["n_raw_points"], 5)
        self.assertEqual(result["n"], 5)
        self.assertEqual(result["verdict"], "EDGE")
        self.assertEqual(result["best_lag"], 1)
        self.assertGreaterEqual(result["best_corr"], 0.9)
        self.assertFalse(result["circularity_flag"])

    def test_prefers_score_raw_and_falls_back_to_score(self):
        raw_edge_with_score_fallback = [
            {"score_raw": 0.0, "score": 0.0, "price_proxy": 100.0, "ts": ts_at(0)},
            {"score_raw": -0.3, "score": 0.9, "price_proxy": 100.5, "ts": ts_at(180)},
            {"score_raw": -0.6, "score": -0.8, "price_proxy": 100.2, "ts": ts_at(360)},
            {"score": -0.8, "price_proxy": 99.9, "ts": ts_at(540)},
            {"score_raw": -0.7, "score": 0.6, "price_proxy": 99.7, "ts": ts_at(720)},
        ]

        result = self.probe_with_series(
            raw_edge_with_score_fallback,
            min_n=5,
            max_lag=1,
            min_corr=0.99,
        )

        self.assertEqual(result["n_raw_points"], 5)
        self.assertEqual(result["n"], 5)
        self.assertEqual(result["verdict"], "EDGE")
        self.assertEqual(result["best_lag"], 1)
        self.assertEqual(result["best_corr"], 1.0)
        self.assertFalse(result["circularity_flag"])

    def test_rows_missing_score_price_or_parseable_ts_are_ignored(self):
        series = [
            row(0.0, 100.0, seconds=0),
            {"score": 999.0, "ts": ts_at(180)},
            {"price_proxy": 999.0, "ts": ts_at(360)},
            {"score_raw": None, "price_proxy": 1000.0, "ts": ts_at(540)},
            row(0.5, 1000.0, ts="not-a-timestamp"),
            row(-0.3, 100.5, seconds=720),
            row(-0.6, 100.2, seconds=900),
            row(-0.8, 99.9, seconds=1080),
            row(-0.7, 99.7, seconds=1260),
        ]

        result = self.probe_with_series(series, min_n=5, max_lag=1, min_corr=0.9)

        self.assertEqual(result["n_raw_points"], 6)
        self.assertEqual(result["n"], 5)
        self.assertEqual(result["verdict"], "EDGE")
        self.assertTrue(result["authoritative"])
        self.assertEqual(result["best_lag"], 1)
        self.assertFalse(result["circularity_flag"])

    def test_burst_points_are_collapsed_to_last_point_in_cluster(self):
        series = [
            row(0.8, 500.0, seconds=0),
            row(0.5, 500.0, seconds=60),
            row(0.0, 100.0, seconds=120),
            row(-0.3, 101.0, seconds=300),
            row(-0.6, 100.7, seconds=480),
            row(-0.9, 100.4, seconds=660),
            row(0.9, 999.0, seconds=840),
            row(-1.0, 100.1, seconds=860),
            row(-0.9, 100.0, seconds=1040),
        ]

        result = self.probe_with_series(series, min_n=6, max_lag=1, min_corr=0.9)

        self.assertEqual(result["n_raw_points"], 9)
        self.assertEqual(result["n"], 6)
        self.assertEqual(result["verdict"], "EDGE")
        self.assertTrue(result["authoritative"])
        self.assertEqual(result["best_lag"], 1)
        self.assertEqual(result["best_corr"], 1.0)
        self.assertFalse(result["circularity_flag"])

    def test_circularity_guard_kills_high_lag_correlation(self):
        circular_series = series_from_diffs(
            [0.05, 0.1, 0.15, 0.2],
            [0.0, 1.0, 2.0, 3.0],
        )

        result = self.probe_with_series(
            circular_series,
            min_n=5,
            max_lag=1,
            min_corr=0.9,
        )

        self.assertEqual(result["n_raw_points"], 5)
        self.assertEqual(result["n"], 5)
        self.assertEqual(result["best_lag"], 1)
        self.assertEqual(result["best_corr"], 1.0)
        self.assertGreaterEqual(abs(result["contemp_corr"]), 0.6)
        self.assertTrue(result["circularity_flag"])
        self.assertEqual(result["verdict"], "KILL")


if __name__ == "__main__":
    unittest.main()
