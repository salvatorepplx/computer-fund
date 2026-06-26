import unittest

from execution.web_sentiment import WebSearchSentimentSource, normalize


class WebSentimentNormalizeTest(unittest.TestCase):
    def test_explicit_bullish_reading_scores_positive(self):
        result = normalize([
            {
                "title": "RDDT Strong Buy",
                "summary": "72% bullish across sources, upgrade, rebound, breakout",
                "domain": "adanos.org",
            }
        ])

        self.assertGreater(result.score, 0.5)
        self.assertEqual(result.method, "explicit+lexical")
        self.assertEqual(result.n_docs, 1)
        self.assertEqual(result.n_explicit, 2)
        self.assertTrue(all(0.0 <= value <= 1.0 for value in (result.confidence,)))
        self.assertGreater(result.detail["raw_score"], 0.5)

    def test_explicit_bearish_reading_scores_negative(self):
        result = normalize([
            {
                "title": "TSLA Strong Sell",
                "summary": "68% bearish on Stocktwits, downgrade, selloff, weak headwinds",
                "domain": "stocktwits.com",
            }
        ])

        self.assertLess(result.score, -0.5)
        self.assertEqual(result.method, "explicit+lexical")
        self.assertEqual(result.n_explicit, 2)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertLess(result.detail["raw_score"], -0.5)

    def test_mixed_explicit_readings_stay_near_neutral(self):
        result = normalize([
            {
                "title": "NVDA mixed",
                "summary": "60% bullish but very bearish technical rating, buy rating, downside and upside",
                "domain": "marketbeat.com",
            }
        ])

        self.assertEqual(result.method, "explicit+lexical")
        self.assertEqual(result.n_explicit, 2)
        self.assertGreater(result.score, -0.25)
        self.assertLess(result.score, 0.25)
        self.assertGreater(result.detail["explicit_vals"][0], 0.0)
        self.assertLess(result.detail["explicit_vals"][1], 0.0)

    def test_lexical_only_and_no_signal_paths(self):
        lexical = normalize([
            {
                "title": "Analyst upgrade",
                "summary": "upgrade outperform rebound breakout constructive support holds",
                "domain": "example.com",
            }
        ])
        no_signal = normalize([
            {
                "title": "Company update",
                "summary": "Board meeting scheduled after regular close",
                "domain": "example.com",
            }
        ])
        empty = normalize([])

        self.assertEqual(lexical.method, "lexical")
        self.assertEqual(lexical.n_explicit, 0)
        self.assertGreater(lexical.score, 0.75)
        self.assertEqual(no_signal.method, "no_signal")
        self.assertEqual(no_signal.score, 0.0)
        self.assertEqual(no_signal.n_docs, 1)
        self.assertEqual(empty.method, "empty")
        self.assertEqual(empty.confidence, 0.0)
        self.assertEqual(empty.n_docs, 0)

    def test_ewma_damps_raw_score_toward_prior(self):
        corpus = [
            {
                "title": "RDDT Strong Buy",
                "summary": "72% bullish across sources, upgrade, rebound, breakout",
                "domain": "adanos.org",
            }
        ]
        raw = normalize(corpus)
        smoothed = normalize(corpus, prior_score=-0.5, ewma_alpha=0.25)

        self.assertEqual(smoothed.method, "explicit+lexical+ewma")
        self.assertEqual(smoothed.detail["raw_score"], raw.score)
        self.assertGreater(smoothed.score, -0.5)
        self.assertLess(smoothed.score, raw.score)
        self.assertAlmostEqual(smoothed.score, -0.1837, places=4)

    def test_confidence_is_bounded_even_with_many_explicit_docs(self):
        corpus = [
            {
                "title": "Strong Buy",
                "summary": "100% bullish upgrade rebound",
                "domain": "adanos.org",
            }
            for _ in range(20)
        ]

        result = normalize(corpus)

        self.assertEqual(result.n_docs, 20)
        self.assertEqual(result.n_explicit, 40)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 0.95)
        self.assertEqual(result.confidence, 0.95)


class WebSearchSentimentSourceTest(unittest.TestCase):
    def test_fetch_uses_injected_search_callable_with_generated_queries(self):
        calls = []
        expected_corpus = [
            {
                "title": "NVDA Strong Buy",
                "summary": "65% bullish, breakout",
                "domain": "stockanalysis.com",
            }
        ]

        def fake_search(queries):
            calls.append(list(queries))
            return expected_corpus

        source = WebSearchSentimentSource(search=fake_search)
        corpus = source.fetch("NVDA", "Nvidia")

        self.assertIs(corpus, expected_corpus)
        self.assertEqual(len(calls), 1)
        self.assertGreaterEqual(len(calls[0]), 5)
        self.assertTrue(all("NVDA" in query or "Nvidia" in query for query in calls[0]))
        self.assertTrue(any("stock price quote today closed at" in query for query in calls[0]))
        self.assertTrue(any("stocktwits sentiment" in query for query in calls[0]))
        self.assertTrue(any("bull bear sentiment" in query for query in calls[0]))
        self.assertTrue(any("bullish bearish analyst" in query for query in calls[0]))

    def test_fetch_without_injected_search_fails_closed(self):
        source = WebSearchSentimentSource()

        with self.assertRaisesRegex(RuntimeError, "injected search callable"):
            source.fetch("NVDA")


if __name__ == "__main__":
    unittest.main()
