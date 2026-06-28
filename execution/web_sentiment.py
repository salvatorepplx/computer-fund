"""
Computer Fund — WebSearchSentimentSource (Computer-side only).

A robust, no-auth sentiment substrate built on the search/web layer instead of
the flaky finance_ticker_sentiment connector (which 401s under load and is a
static summarizer, not a moving signal). The web corpus is timestamped, evolves
between captures as news moves, and frequently carries explicit, parseable
sentiment readings (e.g. "58% bullish across 3 sources", "extremely bearish on
Stocktwits", "Strong Sell" technical ratings).

Design:
- fetch(): Computer injects a `search` callable -> list of {title, summary, date, domain}.
- normalize(): PURE. Scores a corpus into a single [-1..+1] sentiment + confidence.
  Two signals are blended:
    (a) EXPLICIT readings parsed from text ("X% bullish", "Strong Buy/Sell",
        "extremely bearish", consensus ratings) — high weight when present.
    (b) LEXICAL bull/bear balance across all summaries — always available.
- EWMA smoothing via prior_score damps single-capture noise.

This module has NO hard dependency on any connector: the search callable is
injected so normalize() stays pure and unit-testable from fixtures.
"""
from __future__ import annotations
import re, math, datetime as dt
from dataclasses import dataclass
from typing import Callable, Optional


# ---- explicit-reading parsers -------------------------------------------------

_PCT_BULL = re.compile(r"([0-9]{1,3})\s*%\s*bullish", re.I)
_PCT_BEAR = re.compile(r"([0-9]{1,3})\s*%\s*bearish", re.I)

# Ordered strongest->weakest so we match the most specific phrase first.
_RATING_MAP = [
    (re.compile(r"strong\s+buy", re.I), 0.85),
    (re.compile(r"strong\s+sell", re.I), -0.85),
    (re.compile(r"very\s+bearish", re.I), -0.75),
    (re.compile(r"very\s+bullish", re.I), 0.75),
    (re.compile(r"extremely\s+bearish", re.I), -0.8),
    (re.compile(r"extremely\s+bullish", re.I), 0.8),
    (re.compile(r"moderate\s+buy", re.I), 0.45),
    (re.compile(r"moderate\s+sell", re.I), -0.45),
    (re.compile(
        r"\b(?:rated|rating|consensus|recommendation)\s+(?:a\s+)?buy\b|"
        r"\bbuy\s+(?:rating|recommendation)\b", re.I), 0.4),
    (re.compile(
        r"\b(?:rated|rating|consensus|recommendation)\s+(?:a\s+)?sell\b|"
        r"\bsell\s+(?:rating|recommendation)\b", re.I), -0.4),
    (re.compile(
        r"\b(?:rated|rating|consensus|recommendation)\s+(?:a\s+)?(?:hold|neutral)\b|"
        r"\b(?:hold|neutral)\s+(?:rating|recommendation)\b", re.I), 0.0),
]

# Lexical balance terms (broad, domain-tuned for equities commentary).
_BULL = re.compile(
    r"\b(bull|bullish|upgrade|outperform|accelerat\w*|record|beat\w*|"
    r"upside|rally|rebound|breakout|strong\w*|support holds|reclaim\w*|"
    r"constructive|overweight|undervalued|momentum up)\b", re.I)
_BEAR = re.compile(
    r"\b(bear|bearish|downgrade|underperform|slowdown|decelerat\w*|"
    r"miss\w*|downside|selloff|sell-off|breakdown|weak\w*|drop\w*|slip\w*|"
    r"slid\w*|cut\w*|overvalued|oversold|pressure|headwind\w*|probe|scrutiny)\b", re.I)

# Source-quality weights: dedicated sentiment aggregators > technicals blogs.
def _domain_weight(domain: str) -> float:
    d = (domain or "").lower()
    if any(k in d for k in ("stocktwits", "adanos", "marketbeat", "stockanalysis")):
        return 1.4
    if any(k in d for k in ("investing.com", "yahoo", "nasdaq", "fxleaders", "tradingnews")):
        return 1.1
    if "youtube" in d:
        return 0.7
    return 1.0


@dataclass
class WebSentimentResult:
    score: float          # [-1..+1]
    confidence: float     # [0..1]
    n_docs: int
    n_explicit: int       # how many explicit readings were parsed
    method: str
    detail: dict


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def normalize(corpus: list[dict], prior_score: Optional[float] = None,
              ewma_alpha: float = 0.5) -> WebSentimentResult:
    """Score a web corpus into one sentiment point. PURE.

    corpus: list of {title, summary, domain, date}
    """
    if not corpus:
        return WebSentimentResult(0.0, 0.0, 0, 0, "empty", {})

    explicit_vals: list[float] = []
    explicit_w: list[float] = []
    lex_num = 0.0   # weighted (bull-bear)
    lex_den = 0.0   # weighted (bull+bear)

    for doc in corpus:
        text = f"{doc.get('title','')} {doc.get('summary','')}"
        w = _domain_weight(doc.get("domain", ""))

        # (a) explicit % readings
        pb = _PCT_BULL.search(text)
        if pb:
            frac = int(pb.group(1)) / 100.0
            explicit_vals.append(_clip(2 * frac - 1))  # 50%->0, 100%->+1, 0%->-1
            explicit_w.append(w * 1.3)
        pr = _PCT_BEAR.search(text)
        if pr:
            frac = int(pr.group(1)) / 100.0
            explicit_vals.append(_clip(-(2 * frac - 1)))
            explicit_w.append(w * 1.3)

        # (a) rating phrases (take the single strongest match per doc)
        for rx, val in _RATING_MAP:
            if rx.search(text):
                explicit_vals.append(val)
                explicit_w.append(w)
                break

        # (b) lexical balance
        nb = len(_BULL.findall(text))
        ne = len(_BEAR.findall(text))
        if nb + ne > 0:
            lex_num += w * (nb - ne)
            lex_den += w * (nb + ne)

    parts: list[tuple[float, float]] = []  # (value, weight)
    if explicit_vals:
        ew = sum(explicit_w)
        e_score = sum(v * w for v, w in zip(explicit_vals, explicit_w)) / ew
        # explicit gets high weight, scaled by how many we found (capped)
        parts.append((e_score, min(3.0, 0.8 * len(explicit_vals))))
    if lex_den > 0:
        l_score = _clip(lex_num / lex_den)
        parts.append((l_score, 1.0))

    if not parts:
        raw = 0.0
        method = "no_signal"
    else:
        tw = sum(w for _, w in parts)
        raw = _clip(sum(v * w for v, w in parts) / tw)
        method = "explicit+lexical" if explicit_vals else "lexical"

    # EWMA smoothing against prior
    if prior_score is not None:
        score = _clip(ewma_alpha * raw + (1 - ewma_alpha) * prior_score)
        method += "+ewma"
    else:
        score = raw

    # confidence: more docs + explicit readings + agreement => higher
    n = len(corpus)
    base_conf = min(0.9, 0.2 + 0.08 * n)
    explicit_bonus = min(0.3, 0.06 * len(explicit_vals))
    confidence = _clip(base_conf + explicit_bonus, 0.0, 0.95)

    return WebSentimentResult(
        score=round(score, 4),
        confidence=round(confidence, 4),
        n_docs=n,
        n_explicit=len(explicit_vals),
        method=method,
        detail={
            "raw_score": round(raw, 4),
            "lex_num": round(lex_num, 3),
            "lex_den": round(lex_den, 3),
            "explicit_vals": [round(v, 3) for v in explicit_vals],
        },
    )


class WebSearchSentimentSource:
    """Live web-search sentiment. fetch() needs an injected `search` callable."""
    source_id = "web_search_sentiment"
    venue = "web.search"

    def __init__(self, search: Optional[Callable[[list[str]], list[dict]]] = None):
        self._search = search

    def queries_for(self, symbol: str, name: str = "") -> list[str]:
        """Freshness-biased, rotating queries so the corpus TRACKS news drift
        instead of returning a static set each tick (otherwise EWMA converges to
        a fixed point and lead-lag is untestable). Strategy:
          - always include fast-moving live-sentiment sources (Stocktwits/Adanos/
            Perplexity Finance) that update intraday;
          - stamp the current date + an hour-rotating freshness token so repeated
            captures pull genuinely different fresh coverage.
        """
        nm = name or symbol
        now = dt.datetime.now(dt.timezone.utc)
        datestamp = now.strftime("%B %d %Y")          # e.g. 'June 26 2026'
        # rotate the freshness phrasing by hour so the corpus composition shifts
        fresh_tokens = ["today", "this morning", "right now", "latest",
                        "this afternoon", "breaking", "intraday", "this hour"]
        fresh = fresh_tokens[now.hour % len(fresh_tokens)]
        return [
            f"{symbol} {nm} stock price quote today closed at",  # clean live quote doc
            f"{symbol} stocktwits sentiment {fresh}",          # fast intraday gauge
            f"{nm} stock bull bear sentiment {datestamp}",     # date-pinned fresh news
            f"{symbol} stock bullish bearish analyst {fresh}",
            f"{nm} stock news {datestamp}",                    # raw fresh headlines
        ]

    def fetch(self, symbol: str, name: str = "") -> list[dict]:
        if self._search is None:
            raise RuntimeError("WebSearchSentimentSource.fetch needs an injected search callable")
        return self._search(self.queries_for(symbol, name))


# ---- self-test ----------------------------------------------------------------
if __name__ == "__main__":
    bull_corpus = [
        {"title": "RDDT Strong Buy", "summary": "58% bullish across 3 sources, consensus Strong Buy, 21 buy ratings", "domain": "adanos.org"},
        {"title": "Reddit upgrade", "summary": "analysts raise target, rebound and breakout, constructive", "domain": "marketbeat.com"},
    ]
    bear_corpus = [
        {"title": "TSLA probe", "summary": "extremely bearish on Stocktwits, selloff, downgrade, weak momentum, Sell rating", "domain": "stocktwits.com"},
        {"title": "Tesla slides", "summary": "TSLA slides 5.8%, bearish, headwinds, scrutiny, drop below support", "domain": "fxleaders.com"},
    ]
    mixed = [
        {"title": "NVDA mixed", "summary": "Very Bearish technical rating but analysts Strong Buy with 50% upside, oversold, support holds", "domain": "moneycontrol.com"},
    ]
    for nm, c in [("bull", bull_corpus), ("bear", bear_corpus), ("mixed", mixed)]:
        r = normalize(c)
        print(f"{nm:5s} score={r.score:+.3f} conf={r.confidence:.2f} method={r.method} n_explicit={r.n_explicit} detail={r.detail}")
    # EWMA: a single bull reading after a bear prior should move up but stay damped
    r = normalize(bull_corpus, prior_score=-0.5)
    print(f"ewma  score={r.score:+.3f} (bull corpus, prior=-0.5) method={r.method}")
    assert normalize(bull_corpus).score > 0.2, "bull corpus must score positive"
    assert normalize(bear_corpus).score < -0.2, "bear corpus must score negative"
    print("OK: web_sentiment self-tests pass")
