# Capability Inventory — what the autoresearch loop can actually reach

**Purpose:** Stop tribal knowledge. This is the durable, committed inventory of every tool, SDK,
CLI, and connector the Fund's agents can use, plus the open question of who can use what. Both
Computer and Teammate read this when planning a research tick so the loop uses the full toolset
instead of a tiny slice of it. Update it whenever a capability is added, retired, or the
Computer↔Teammate boundary is reconciled.

Last verified: 2026-06-28 (probed from the live sandbox).

---

## 1. pplx_sdk — the in-sandbox retrieval + extraction engine (Python, `import pplx_sdk`)

Installed as a compiled package (`/usr/local/lib/python3.14/site-packages/pplx_sdk/`). Auth is via
env vars (`PPLX_SDK_API_KEY`, `PPLX_SDK_BASE_URL`) injected **only** by the `pplx-sdk` credential
preset on a bash call. Without the preset it raises `AuthenticationError [401] PPLX_SDK_API_KEY is
not set`.

**`pplx_sdk.search`** — typed, multi-vertical, each with a batched `_many` fan-out variant:
- `web` / `web_many` — open-web search (THE current live signal substrate; we use only this today)
- `secgov` / `secgov_many` — SEC/EDGAR filings (point-in-time, fund-relevant — UNUSED)
- `academic` / `academic_many` — research papers (mechanism literature for dossiers — UNUSED)
- `patents` / `patents_many` — patent search (UNUSED)
- `people` / `people_many` — typed people records (`PeopleGithub`, `PeopleTwitter`, `PeopleEmail`) (UNUSED)
- `images`, `videos`, `shopping` (+ `_many`) — other verticals (UNUSED)

**`pplx_sdk.llm`** — `extract` / `extract_many`: structured LLM extraction over fetched content,
returns typed `ExtractResult`. **High-leverage and UNUSED:** would replace the brittle regex/lexical
bull-bear scorer in `execution/web_sentiment.py` with schema-based extraction.

**`pplx_sdk.content`** — fetch/snippet pages. **Pipeline utils:** `fanout`,
`flatten_fanout_rows`, `dedup_by_url`, `dedup_by_field`, `read_jsonl`, `write_jsonl`, typed hit
classes (`WebHit`, `SecgovHit`, `AcademicHit`, ...).

**Idiomatic pipeline:** `search.web_many(queries)` → `dedup_by_url` → `llm.extract_many(schema)` →
`write_jsonl`. All in-process, no connector round-trips.

**Current Fund usage:** exactly one call — `pplx_sdk.search.web(q, limit=6)` in
`scripts/capture_web_tick.py`. We use ~1 of ~10 capabilities. The three highest-leverage unused ones
map onto open queue items: `web_many`/`fanout` → cross-sectional breadth (STRAT-WIDE);
`llm.extract` → signal quality (fixes single-source fragility); `secgov`/`academic` → research evidence.

---

## 2. Open web from the sandbox — REACHABLE TODAY (this resolves the "can the harness explore the web?" question)

Probed 2026-06-28: the sandbox is **NOT** network-isolated.
- `curl` / `wget` reach the open web directly: `github.com → HTTP 200`, `arxiv.org → HTTP 200`.
- General CLIs present: `gh`, `git`, `curl`, `wget`, `yt-dlp`, `ffmpeg`, `node`, `python`, `pip`, `jq`,
  `pplx-tool`, `external-tool`.

**Implication:** open-source work and peer materials (arXiv papers, GitHub repos/source, vendor docs,
public datasets) are fetchable from inside the sandbox with plain `curl`/`wget`/`gh`/`pip` — no special
credential. The belief that "Teammate can't explore the web" is a *credential/contract* artifact
(pplx_sdk needs the Computer-side `pplx-sdk` key), NOT a hard sandbox limit.

---

## 3. The agent toolset (Computer-side, via the agent interface, not raw CLI)
- `pplx_sdk` verticals (above), research subagents (deep multi-source falsification),
  `wide_browse` (cross-sectional coverage at scale), `browser_task` (authenticated/JS pages),
  `search_web` / `search_vertical` (academic/people/video/shopping/image), `fetch_url`.
- `finance_*` connector tools (analyst research, estimates, earnings/PEAD, OHLCV, institutional
  holders, macro, SEC) — Computer-side; the point-in-time market data Teammate cannot fetch.
- `pplx-tool schedule_cron` (the heartbeat), `external-tool` CLI (programmatic connector calls).

## 4. Connectors available (Computer identity)
Slack, GitHub, Notion, Linear, Google Drive/Sheets/Slides, Datadog, Snowflake, Plaid, Robinhood,
finance, YouTube, Carta, and more (see `list_external_tools`). Robinhood is the only trade-placing
surface and is LAW-restricted to account 696264779.

---

## 5. The Computer↔Teammate boundary — OPEN, to be reconciled (see Slack #sal-teammate)

Current HANDOFF contract (Teammate's stated boundary): live web search = C (not available),
external finance feeds = C; Slack/GitHub/repo = A, Notion = A, Linear = A, Snowflake = A (read-only),
Datadog = A (read-only). So today: **Computer captures external evidence and commits it; Teammate
structures it.**

But the probe above shows the sandbox can reach the open web with curl/wget/gh. So the real questions
to reconcile with Teammate are:
1. Does Teammate's execution identity actually have a network-capable shell? (If yes, Teammate can
   `curl arxiv.org` / `gh` clone OSS repos directly for literature + peer-implementation research.)
2. Can Teammate's identity be granted the `pplx-sdk` credential preset, or does that stay Computer-only?
3. What stays Computer-exclusive by LAW regardless of capability: anything touching `execution/`,
   `state/`, Robinhood/account/order APIs, sizing, or state promotion. Capability for *research* is
   separable from authority to *trade* — the rails are about authority, not about web access.

The principle: capability to LEARN (read the web, OSS, papers, our own tools) should be as wide as
possible for both agents; authority to ACT (place/size/promote a trade) stays Computer-only and
rail-bound. Reconcile the research-capability boundary explicitly rather than inheriting it by accident.
