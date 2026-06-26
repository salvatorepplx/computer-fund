# RFC-001: Source-Agnostic Sentiment Ingestion

- Status: Proposed
- Owner: Shared: Computer owns live connector adapters; Teammate owns offline contracts, fixtures, and evals
- Created: 2026-06-26
- Related Beads: `teammate-uyp.11`, partially `teammate-uyp.10`
- Scope Boundary: this RFC does not implement live connector calls, Robinhood access, live market data access, order sizing, ARMED handoffs, or execution behavior

## Problem

The Fund's mission is to generate alpha by predicting and predating public sentiment, but the current
sentiment input is the weakest factor in the loop. The graph has only hand-seeded sentiment history,
finance ticker sentiment is derived/lagging/coarse, and Computer web search is useful but not a
firehose. The sentiment lead-lag falsifier should reject thin, stale, or lagging inputs; if it does,
the Fund cannot trust simulation momentum or CAP calibration.

We need an arbitrary-source ingestion architecture: each source fetches records in its native shape,
normalizes them into one timestamped event schema, and feeds the graph through a single scoring and
quality-weighting path. The design must preserve the repo boundary: Computer may use live connectors
and commit observed artifacts back; Teammate can only design interfaces, create offline fixtures, and
run connector-free evals.

## Context and Constraints

- `CHARTER.md` is LAW: no look-ahead, no fabrication, every signal timestamped, and simulated
  sentiment must remain labeled.
- `HANDOFF.md` separates roles: Computer owns live connectors and execution; Teammate owns offline
  engineering/research/evals and must not touch connector-only account, market-data, or order state.
- Current connector context includes usable or candidate sentiment/context inputs: finance ticker
  sentiment, Computer web search, Semrush premium data as a search-attention proxy, Statista as
  market/statistics/demographics/industry context, Bluesky, Mastodon, and Finnhub. There is no native
  X/Twitter or Reddit firehose.
- `state/knowledge_graph.json` stores `sentiment_history` on graph nodes with `score`, `confidence`,
  `source`, `simulated`, and `observed_at`; this is sufficient for a seed but too thin for source
  quality, lag, venue, raw provenance, and deduplication.
- `evals/falsification_playbook.md`, `evals/leadlag_placebo.py`, and `evals/cap_calibration.md`
  already define the direction: sentiment must lead observed proxies, survive placebos, and eventually
  calibrate conviction to realized outcomes.
- This RFC is design-only. Any adapter that needs live social, search, news, finance, broker, or
  account data runs on Computer's side and writes sanitized observed fixtures/artifacts back to git.

## Source Inventory and Constraints

| Source | Owner | Shape | Expected Strength | Primary Constraint |
|---|---|---|---|---|
| Bluesky | Computer live adapter | public posts, authors, timestamps, engagement | early social chatter in selected communities | connector is connect-ready but not present in Teammate; coverage may be niche |
| Mastodon | Computer live adapter | federated posts, instances, timestamps, engagement | decentralized social chatter and niche technical communities | fragmented venues and duplicate cross-posts |
| Finnhub social sentiment | Computer live adapter | ticker-level social sentiment aggregates | fast bootstrap for ticker entities | aggregate, vendor-scored, may lag public posts |
| Finnhub news sentiment | Computer live adapter | article/news sentiment by ticker/entity | stronger provenance than social aggregate | news is often downstream of sentiment, not leading |
| Statista | Computer live adapter / sanitized artifact | market statistics, demographics, industry datasets, reports | context for venue/entity priors, market sizing, demographic exposure, and narrative plausibility | not a firehose and not direct sentiment; may be aggregated, lagged, licensed, and provenance-sensitive |
| Semrush | Computer live adapter | keyword/search/traffic attention proxy | attention inflection before mainstream narrative | attention is not sentiment; requires polarity inference |
| Finance ticker sentiment | Computer live adapter | ticker-level sentiment already available to Computer | existing baseline and fallback | coarse, derived, likely lagging |
| Computer web search | Computer live adapter | searched snippets/pages with timestamps when available | broad discovery and narrative context | not a firehose; query choice can bias evidence |
| Offline fixtures | Teammate | deterministic JSONL examples | contract and eval development | simulated or sanitized only; never represented as live data |

The system should treat every source as provisional until it proves lead time, coverage, stability,
and calibration value. The first goal is not to maximize source count; it is to make weak sources fail
loudly and comparable sources compete on measured quality.

## Options Considered

1. **Hard-code each source into graph ingestion.** This is fast for one connector but creates separate
   schemas, separate quality knobs, and repeated no-look-ahead risks. Reject.
2. **Only ingest vendor aggregate sentiment.** This bootstraps quickly but doubles down on derived,
   lagging, ticker-only inputs. Reject as the primary architecture; keep as one adapter.
3. **Use a source-agnostic adapter contract with normalized events.** This adds a small interface and
   normalization discipline, but lets every connector, web search output, and offline fixture feed the
   same graph/eval path. Adopt.

## Decision

Adopt a source-agnostic `SentimentSource` contract and a normalized `SentimentEvent` schema. Live
adapters run only on Computer's side. Teammate develops the schema, offline fixture examples,
normalization rules, quality/lag weighting, and falsification/CAP eval hooks without fetching live
data.

The graph ingestion path should append observed sentiment events to graph nodes, preserve raw
provenance by reference or sanitized payload, compute a per-event effective weight, and expose enough
metadata for lead-lag falsification and CAP calibration to attribute which sources helped or hurt.

## Adapter Contract

Adapters implement a fetch-normalize boundary. `fetch` is connector-specific and Computer-side when
it requires live data. `normalize` is deterministic and can be tested offline with sanitized fixtures.

```python
class SentimentSource(Protocol):
    source_id: str
    venue: str

    def fetch(self, since: datetime, until: datetime, query: SentimentQuery) -> Iterable[RawRecord]:
        """Computer-side for live connectors; forbidden in Teammate-only offline evals."""

    def normalize(self, record: RawRecord) -> Iterable[SentimentEvent]:
        """Pure transformation into the canonical schema; safe to test from fixtures."""
```

Minimum query fields:

```json
{
  "entities": ["TICKER:NVDA", "NARR:ai-capex-peak", "BATTLE:NVDA-capex"],
  "keywords": ["NVDA", "AI capex", "Blackwell demand"],
  "since": "2026-06-26T00:00:00Z",
  "until": "2026-06-26T01:00:00Z",
  "max_records": 500
}
```

Adapters may emit zero, one, or many normalized events per raw record because one post/article/search
result can mention multiple entities or battles.

## Normalized Event Schema

Canonical event shape:

```json
{
  "event_id": "sha256:source_id:raw_id:entity:observed_at",
  "entity": "BATTLE:NVDA-capex",
  "entity_type": "battle",
  "score": 0.42,
  "confidence": 0.68,
  "ts": "2026-06-26T00:37:12Z",
  "observed_at": "2026-06-26T00:37:12Z",
  "ingested_at": "2026-06-26T00:40:00Z",
  "source": "bluesky",
  "venue": "social.bluesky",
  "raw_ref": "runs/sentiment/raw/bluesky/2026-06-26T00.jsonl#sha256:...",
  "raw": {
    "sanitized": true,
    "record_id": "at://example/post/abc",
    "text_excerpt": "short bounded excerpt or null",
    "author_hash": "sha256:...",
    "url_hash": "sha256:..."
  },
  "quality": {
    "source_quality_prior": 0.45,
    "lag_seconds": 168,
    "coverage": 0.3,
    "dedupe_weight": 1.0,
    "entity_resolution_confidence": 0.8,
    "effective_weight": 0.29
  },
  "labels": {
    "simulated": false,
    "attention_proxy": false,
    "vendor_scored": false
  }
}
```

Field rules:

- `score` is normalized to `[-1.0, 1.0]`, where positive means sentiment supports the entity's
  bullish/positive narrative and negative means opposition or bearish pressure. For battle nodes,
  adapters must document which side of the battle the score supports.
- `confidence` is normalized to `[0.0, 1.0]` and measures extraction confidence, not expected alpha.
- `ts` is the source event timestamp. `observed_at` is the best available public-observation time.
  `ingested_at` is when Computer wrote the event. Evals use `observed_at` and must never use data with
  `observed_at` after the decision time.
- `raw` is optional and sanitized. Large or sensitive payloads should be referenced by `raw_ref`, not
  copied into graph nodes.
- `labels.simulated` must be `true` for offline synthetic fixtures and simulation outputs. Simulated
  events cannot overwrite observed records or satisfy observed-history requirements.
- `labels.attention_proxy` marks sources like Semrush, and sometimes Statista-derived context, where
  attention or market context exists without native polarity; downstream scoring must not confuse
  context with sentiment unless a documented mapping or polarity model is applied.
- Statista-like records should preserve dataset/report provenance, publication period, retrieval time,
  and licensing constraints in `raw_ref`/`raw`. They cannot be treated as sentiment events unless a
  documented mapper converts a statistic into an entity-context, attention, or polarity feature with
  explicit confidence and lag penalties.

## Knowledge Graph Ingestion Path

1. Computer-side adapters fetch live records and write normalized JSONL artifacts under a future path
   such as `runs/sentiment/observed/<source>/<window>.jsonl`. Teammate-side fixtures use a separate
   path such as `runs/sentiment/fixtures/*.jsonl` and set `labels.simulated=true` when synthetic.
2. A connector-free ingest step validates schema, deduplicates events, resolves entities to graph node
   IDs, computes quality fields, and appends compact sentiment entries to node `sentiment_history`.
3. The graph keeps the current compact fields for backwards compatibility while adding optional
   provenance fields:

```json
{
  "score": 0.42,
  "confidence": 0.68,
  "source": "bluesky",
  "venue": "social.bluesky",
  "simulated": false,
  "observed_at": "2026-06-26T00:37:12Z",
  "event_id": "sha256:...",
  "effective_weight": 0.29,
  "lag_seconds": 168,
  "raw_ref": "runs/sentiment/raw/bluesky/2026-06-26T00.jsonl#sha256:..."
}
```

4. Momentum and battle-ranking code should be updated to prefer observed, non-simulated events and to
   support weighted windows instead of latest-minus-prior only.
5. Falsification and CAP evals consume the same normalized event history, grouped by `source`,
   `venue`, `entity`, and decision timestamp.

This keeps graph nodes reviewable and small while preserving enough provenance to audit bad signals.

## Quality and Lag Weighting

Every event gets an `effective_weight` used for aggregation, momentum, and source attribution. The
initial formula should be simple and pre-registered:

```text
effective_weight = confidence
  * source_quality_prior
  * lag_decay(lag_seconds)
  * coverage_weight
  * dedupe_weight
  * entity_resolution_confidence
```

Where:

- `source_quality_prior` starts conservative and source-specific. Example initial priors: direct social
  post source `0.45`, vendor social aggregate `0.35`, news sentiment `0.30`, search-attention proxy
  `0.25`, finance ticker sentiment `0.25`, manually reviewed web search excerpt `0.40`. These are not
  alpha claims; they are starting weights until CAP evidence updates them.
- `lag_decay(lag_seconds)` penalizes stale records. A starter decay is `exp(-lag_seconds / half_life)`,
  with shorter half-lives for social posts and longer half-lives for news or search-attention windows.
- `coverage_weight` penalizes sources that only sporadically cover an entity or venue.
- `dedupe_weight` discounts near-duplicates, syndicated articles, reposts, and cross-posts.
- `entity_resolution_confidence` discounts weak ticker/narrative/battle matches.

Weights must be logged, not hidden. CAP calibration should later update source priors using realized
lead-lag and outcome evidence. A source with high volume but no lead should decay toward zero; a
source that consistently leads observed sentiment peaks should earn weight even if its raw coverage is
small.

## Deduplication and Entity Resolution

Deduplication should happen before graph append:

- Compute `event_id` from stable source identity, raw record ID when available, normalized entity, and
  source timestamp.
- Compute a `content_fingerprint` from canonicalized text/title/url hash for sources without stable IDs.
- Collapse exact duplicates; downweight near-duplicates and syndicated copies rather than deleting all
  of them, because repetition can measure attention but should not masquerade as independent sentiment.
- Track cross-source duplicate groups so the same news article surfaced by web search and Finnhub does
  not double-count as two independent observations.

Entity resolution should emit confidence and explanation metadata:

- Ticker aliases map to `TICKER:*` nodes only when the mention is finance-specific enough to avoid
  collisions.
- Narrative phrases map to `NARR:*` nodes when they express a reusable causal claim.
- Battle nodes receive sentiment only when the record can be assigned to a side or direction of the
  contested question.
- Ambiguous records are retained in raw artifacts but either dropped from graph sentiment or ingested
  with low `entity_resolution_confidence`.

## Offline Fixtures and Evals

Teammate can build confidence without live data by using deterministic fixtures that exercise the
contract:

- Schema fixtures: one normalized JSONL row per source shape, including synthetic Bluesky/Mastodon,
  vendor aggregate, news, Statista-style contextual statistic, search-attention proxy, and finance
  ticker-sentiment examples.
- Dedup fixtures: exact duplicate, near-duplicate, syndicated news, and social repost cases.
- Entity fixtures: clean ticker match, ambiguous ticker word, narrative match, battle-side match, and
  unresolved record.
- Lead-lag fixtures: observed sentiment events that intentionally lead, coincide with, and lag a later
  proxy so `evals/leadlag_placebo.py` can be extended from synthetic arrays to normalized event JSONL.
- CAP fixtures: source-attributed event histories joined to simulated closed-outcome rows so
  `evals/cap_calibration.md` can pre-register how source priors will be adjusted once real history
  exists.

The eval rule is strict: offline fixtures may prove plumbing and falsifier behavior, but they do not
prove alpha. Live observed artifacts must be fetched by Computer and committed back with timestamps
before any source earns real CAP calibration credit.

## Support for Lead-Lag Falsification and CAP Calibration

This design supports the existing falsification direction by making time and provenance first-class:

- Lead-lag evals can compare source-attributed sentiment peaks against later observed sentiment or
  price proxies without using future rows at decision time.
- Placebo evals can shuffle labels, swap universes, invert direction, or drop venues while preserving
  the same normalized schema.
- Lag analysis can reject sources whose best correlation is coincident or negative-lag, even if their
  raw sentiment score looks predictive.
- CAP calibration can attribute conviction errors by source mix: if trades with high Finnhub/news
  weight lag but direct social/search-attention mixtures lead, source priors should update accordingly.
- Simulated sentiment remains explicitly labeled and can be evaluated against observed history without
  contaminating the observed graph.

## Implementation Sequence

1. **RFC and process.** Land this RFC plus the minimal `runs/rfcs/` process document.
2. **Schema and fixtures.** Add a JSON Schema or typed dataclass for `SentimentEvent`, plus offline
   fixture JSONL rows that cover source, dedup, entity-resolution, and lead-lag cases.
3. **Connector-free ingest.** Add a validator/ingester that reads normalized JSONL fixtures and appends
   compact, provenance-bearing sentiment entries to an in-memory or test graph. Do not call live
   connectors.
4. **Eval extensions.** Extend lead-lag and CAP fixture evals to consume normalized event JSONL and
   report source/venue attribution.
5. **Computer-side adapter skeletons.** Add adapter stubs or contracts for Computer-owned live sources,
   with `fetch` unimplemented in Teammate contexts and `normalize` testable from sanitized raw samples.
6. **Observed artifact handoff.** Have Computer run one low-volume connector window and commit sanitized
   observed JSONL for review. This is the first step that uses live connector data, and it happens only
   on Computer's side.
7. **Calibration loop.** After enough observed windows and closed outcomes exist, update source priors
   from CAP calibration rather than judgment.

## Falsifiable Success Criteria

This RFC succeeds only if later implementation can pass these checks:

- Schema validation rejects events missing `entity`, `score`, `confidence`, `observed_at`/`ts`,
  `source`, `venue`, and `labels.simulated`.
- Offline evals prove that simulated fixtures remain labeled and never satisfy observed-history gates.
- Lead-lag evals accept a true leading fixture and reject coincident, lagging, random-label,
  wrong-universe, and direction-inverted controls.
- Source reports include event count, coverage, median lag, effective weight, dedupe rate, and
  lead-lag result by source/venue.
- A lagging source's `effective_weight` decreases or its prior is flagged for review before it can
  dominate battle momentum.
- Graph sentiment history remains auditably timestamped and can reconstruct which raw/sanitized event
  moved a battle's weighted momentum.
- CAP calibration can later answer whether source-weighted conviction predicts realized outcomes
  better than equal-weighted or ticker-sentiment-only baselines.

Failure conditions that should force redesign:

- The normalized schema cannot represent at least social posts, vendor aggregates, news sentiment,
  Statista-style contextual statistics, search-attention proxies, and existing finance ticker
  sentiment without source-specific graph code.
- Lead-lag attribution cannot distinguish leading social/search signals from lagging news/ticker
  aggregates.
- Deduplication removes attention information entirely or double-counts syndicated/reposted content as
  independent sentiment.
- Computer-side live artifacts cannot be reviewed offline without leaking connector secrets or relying
  on Teammate live access.

## Open Questions

- What is the first Computer-owned connector window to sanitize and commit: Bluesky/Mastodon social,
  Finnhub aggregate/news, Statista context, or Semrush search-attention?
- Which Statista datasets, if any, are allowed to be represented in git as sanitized metadata versus
  hashes/references only under licensing and provenance constraints?
- Should `raw` excerpts be stored in git at all, or should git keep only hashes and short reviewer-safe
  excerpts?
- Should source priors be global, per entity type, per venue, or per battle class once enough history
  exists?
- What observed proxy should lead-lag use first for battles without enough native sentiment history:
  later source consensus, finance sentiment, attention, or price/volume response?
- How should battle-side polarity be represented when a source mentions the target ticker but not the
  contested narrative?
