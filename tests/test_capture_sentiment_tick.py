from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.capture_sentiment_tick import capture, capture_sentiment_with_retry


VALID_SENTIMENT = """
Issue 1
Bull case: analysts raised estimates after stronger demand, record results, and a buy upgrade.
Bear case: skeptics warn of a slowdown and possible drawdown.
"""


class CaptureSentimentRetryTests(unittest.TestCase):
    def test_retries_empty_and_no_signal_before_success(self) -> None:
        responses = [
            {"content": ""},
            {"content": "rate limit: no data available"},
            {"content": VALID_SENTIMENT},
        ]
        calls = []
        sleeps = []

        def fake_call_tool(source_id: str, tool_name: str, arguments: dict) -> dict:
            calls.append((source_id, tool_name, arguments))
            return responses.pop(0)

        with patch("scripts.capture_sentiment_tick.persist_raw") as persist_raw:
            result = capture_sentiment_with_retry(
                "TICKER:NVDA",
                "NVDA",
                call_tool_fn=fake_call_tool,
                sleep_fn=sleeps.append,
                backoff_seconds=(0.1, 0.2),
            )

        self.assertTrue(result["captured"])
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [0.1, 0.2])
        self.assertEqual(calls[0][0], "finance")
        self.assertEqual(calls[0][1], "finance_ticker_sentiment")
        self.assertEqual(calls[0][2]["ticker_symbol"], "NVDA")
        self.assertEqual(calls[0][2]["query"], "NVDA bull vs bear")
        persist_raw.assert_called_once()

    def test_all_failures_return_captured_false_without_persisting(self) -> None:
        def fake_call_tool(source_id: str, tool_name: str, arguments: dict) -> dict:
            return {"content": "temporarily unavailable"}

        with patch("scripts.capture_sentiment_tick.persist_raw") as persist_raw:
            result = capture_sentiment_with_retry(
                "TICKER:NVDA",
                "NVDA",
                call_tool_fn=fake_call_tool,
                sleep_fn=lambda _seconds: None,
                max_attempts=2,
                backoff_seconds=(0.1,),
            )

        self.assertFalse(result["captured"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual([failure["attempt"] for failure in result["failures"]], [1, 2])
        persist_raw.assert_not_called()

    def test_retry_cap_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            capture_sentiment_with_retry("TICKER:NVDA", "NVDA", max_attempts=0)

    def test_capture_appends_only_after_successful_retry(self) -> None:
        finance_responses = iter([
            {"content": ""},
            {"content": VALID_SENTIMENT},
        ])

        def fake_call_tool(source_id: str, tool_name: str, arguments: dict) -> dict:
            if source_id == "finance":
                return next(finance_responses)
            return {"data": {"results": [{"quote": {"last_trade_price": "123.45"}}]}}

        with (
            patch("scripts.capture_sentiment_tick.call_tool", side_effect=fake_call_tool),
            patch("scripts.capture_sentiment_tick.time.sleep"),
            patch("scripts.capture_sentiment_tick.persist_raw"),
            patch("scripts.capture_sentiment_tick.load_series", return_value=[]),
            patch("scripts.capture_sentiment_tick.append_observation", return_value="runs/sentiment/series/TICKER_NVDA.jsonl") as append_observation,
            patch("scripts.capture_sentiment_tick.series_length", return_value=1),
        ):
            result = capture("TICKER:NVDA", "NVDA")

        self.assertTrue(result["captured"])
        self.assertEqual(result["sentiment_attempts"], 2)
        append_observation.assert_called_once()

    def test_capture_does_not_append_when_all_retries_fail(self) -> None:
        def fake_call_tool(source_id: str, tool_name: str, arguments: dict) -> dict:
            return {"content": ""}

        with (
            patch("scripts.capture_sentiment_tick.call_tool", side_effect=fake_call_tool),
            patch("scripts.capture_sentiment_tick.time.sleep"),
            patch("scripts.capture_sentiment_tick.persist_raw"),
            patch("scripts.capture_sentiment_tick.load_series", return_value=[]),
            patch("scripts.capture_sentiment_tick.append_observation") as append_observation,
        ):
            result = capture("TICKER:NVDA", "NVDA")

        self.assertFalse(result["captured"])
        self.assertEqual(result["attempts"], 3)
        append_observation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
