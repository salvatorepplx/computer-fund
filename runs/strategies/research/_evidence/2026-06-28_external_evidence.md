# Committed external evidence snapshot — 2026-06-28T00:55Z

**Captured by:** Computer (sole connector holder). **Provider:** Perplexity Finance (`finance_*` tools).
**Why this file exists:** Teammate's workers cannot fetch live external market data (tool boundary = C
for finance feeds). Per HANDOFF Failure 3, Computer captures point-in-time raw evidence and commits it
so Teammate can structure mechanism research, design falsifiers, and make kill/keep calls offline.

**Boundary:** This is observed, timestamped, point-in-time data. It is NOT a signal, NOT a proposal,
and authorizes nothing. Universe here is the 4 currently-tracked battle names (NVDA, RDDT, TSLA, SNDK);
the dossiers should generalize mechanisms to a ≥30-name selector, not to this trophy list.

Raw CSVs (where downloaded) live in `runs/strategies/research/_evidence/csv/`.

---

## Mechanism 1 — Analyst-revision breadth / PEAD (post-earnings-announcement drift)

### Analyst consensus (point-in-time 2026-06-28)
| ticker | consensus | total | bull% | neut% | bear% | avg PT | median PT | high PT | low PT |
|---|---|---|---|---|---|---|---|---|---|
| NVDA | strong_buy | 25 | 100.0 | 0 | 0 | 320.72 | 307 | 500 | 265 |
| RDDT | buy | 23 | 65.2 | 34.8 | 0 | 236.13 | 245 | 300 | 175 |
| TSLA | buy | 19 | 52.6 | 36.8 | 10.5 | 429.68 | 475 | 600 | 24.86 |
| SNDK | strong_buy | 15 | 86.7 | 13.3 | 0 | 1693.33 | 1700 | 3250 | 450 |

Observations for the mechanism worker:
- **TSLA is the cleanest "battle location" on revision breadth:** 52.6% bull / 10.5% bear, and an
  extreme PT dispersion ($24.86 low [GLJ/Gordon Johnson, persistent Sell] vs $600 high). This is a
  live disagreement, not consensus drift. Cross-source-divergence mechanism (M4) overlaps here.
- **SNDK shows a massive upward PT revision wave** (see rating rows): Goldman $55→$140→$700,
  Citi $125→$150→$2500, B of A $1550→$2100, Mizuho $1825→$2200 across 2025-10 → 2026-06. This is a
  textbook analyst-revision-breadth signal (many firms revising the same direction over weeks).
- **NVDA:** uniform 100% bull, PT creeping up (Wells $265→$315, Rosenblatt $245→$300, Tigress
  $360→$425). High breadth, low dispersion — the question is whether breadth still predicts drift when
  it is already saturated (a falsifier the worker should pre-register).

### Post-earnings drift inputs (epsSurprise → 1-day post-earnings move)
NVDA (quarterly): Q1'27 eps surprise +0.10 → −1.77%; Q4'26 +0.2383 → −5.46%; Q3'26 0.0 → −3.15%;
Q2'26 −0.01 → −0.79%; Q1'26 −0.08 → +3.24%. (NVDA repeatedly BEATS but sells off 1-day — drift sign
is ambiguous; a worker should test multi-day drift, not 1-day.)
RDDT: Q1'26 +0.39 → +13.07%; Q4'25 +0.28 → −7.43%; Q3'25 +0.28 → +7.47%; Q2'25 +0.25 → +17.47%;
Q1'25 +0.11 → −4.18%. (Large positive surprises, large but sign-inconsistent 1-day moves.)
TSLA: Q1'26 −0.18 → −3.56%; Q4'25 −0.14 → −3.45%; Q3'25 −0.16 → +2.28%; Q2'25 −0.12 → −8.20%;
Q1'25 −0.29 → +5.37%. (TSLA persistently MISSES EPS — interesting asymmetry vs its bullish PTs.)
SNDK: Q3'26 +8.92 → +8.25%; Q2'26 +2.29 → +6.85%; Q1'26 +0.05 → +15.31%; Q4'25 0.0 → −4.58%;
Q3'25 −0.21 → +4.83%. (Huge beats, positive drift — the cleanest PEAD candidate of the four.)

**Mechanism note for the worker:** 1-day post-earnings move is noisy and sign-inconsistent here. The
real PEAD literature is about the 1–60 day DRIFT after the announcement, not the announcement-day jump.
Design the falsifier on multi-day cumulative abnormal return conditioned on standardized surprise (SUE),
and pre-register that the 1-day move is NOT the test.

---

## Mechanism 2 — Short-interest squeeze asymmetry
Not directly in the finance toolset as a first-class field. Proxies Computer CAN commit later:
`finance_institutional_holders` (ownership concentration), `finance_quotes` (float via shares
outstanding), and float-vs-volume from `finance_ohlcv_histories`. **Worker action:** mark data
availability as PARTIAL/PROXY-ONLY; define what point-in-time short-interest source would be needed
(bi-monthly exchange short-interest with publication lag), and whether a borrow-fee / days-to-cover
proxy is constructible from committed OHLCV + shares outstanding. If no point-in-time SI path exists,
the ladder says recommend `kill` or `needs_more_research`, not `keep_for_testing`.

## Mechanism 3 — Mention-velocity acceleration
Data path = the live web-sentiment substrate Computer already captures
(`runs/sentiment/series/TICKER_*.jsonl`, `n_docs` per tick). Acceleration = 2nd derivative of n_docs /
mention count over time. **Worker action:** this is the one mechanism with a live committed series
already growing; design the test on `n_docs`/`n_explicit` deltas, and pre-register the circularity
guard (mention velocity must lead price, not co-move).

## Mechanism 4 — Cross-source sentiment divergence
Evidence above shows it concretely on TSLA (analyst PT $24.86 vs $600; bull 52.6% / bear 10.5%) and
on the web-sentiment series (TSLA web score 0.18 — much lower than NVDA 0.39). **Worker action:**
define divergence = z-score gap between analyst-consensus sentiment and web/retail sentiment; test
whether the gap predicts convergence direction. TSLA is the natural first case; generalize to a
selector of names with high analyst-vs-retail sentiment spread.

## Mechanism 5 — Vol-regime-gated reversion
Data path = `finance_ohlcv_histories` (Computer can commit daily OHLCV per name). Regime = realized
vol percentile; reversion = mean-reversion of returns conditional on regime. **Worker action:** specify
the OHLCV window and fields you need committed (I'll pull `close`+`volume` for a 1–2yr daily window on
request); pre-register the null (permutation of regime labels) and the cross-sectional generalization
bar (≥30% of universe).

---

## Provenance
- `finance_analyst_research` (consensus + 48–59 individual ratings per name) — 2026-06-28T00:55Z.
- `finance_earnings_history` (6 quarters actuals vs consensus + post-earnings moves) — 2026-06-28T00:55Z.
- Per-name CSVs (consensus, price_targets_n60, quarterly_earnings_history) available in `csv/` for the
  ones downloaded; full tabular content reproduced above for offline reasoning without the CSVs.
- All figures are point-in-time as of the capture timestamp; analyst rows carry their own `date` field
  so the worker can build a true point-in-time revision series (watch publication lag).
