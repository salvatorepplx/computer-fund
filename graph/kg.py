"""
Computer Fund — Knowledge Graph.

A constantly-updating graph of the entities that drive sentiment-based repricing.
Stored as JSON on disk (single source of truth) so every tick reads + enriches it.

Node types:
  ticker     — a tradeable instrument (symbol, sector, last seen price)
  narrative  — a story/thesis circulating about an entity ("AI capex peak", "short squeeze")
  catalyst   — a dated event (earnings, FOMC, product launch, expiry)
  actor      — a sentiment mover (analyst, influencer, fund, subreddit, news outlet)
  battle     — a "battle location": a contested arena = ticker × narrative cluster where
               bull/bear views collide and sentiment is being repriced

Edge types (directed): MENTIONS, DRIVES, CONTRADICTS, TARGETS, SCHEDULED_FOR, PART_OF

Every node carries a sentiment vector with provenance + timestamp:
  sentiment = {score: -1..+1, confidence: 0..1, source: str, observed_at: iso, simulated: bool}

`simulated=True` marks sentiment that has NOT been observed yet (sim output) — never
conflated with observed fact (Charter §6: no look-ahead, no fabrication).
"""
from __future__ import annotations
import json, datetime as dt
from pathlib import Path

GRAPH_PATH = Path(__file__).resolve().parent.parent / "state" / "knowledge_graph.json"
NODE_TYPES = {"ticker", "narrative", "catalyst", "actor", "battle"}
EDGE_TYPES = {"MENTIONS", "DRIVES", "CONTRADICTS", "TARGETS", "SCHEDULED_FOR", "PART_OF"}


def _now() -> str:
    return dt.datetime.utcnow().isoformat() + "Z"


class KnowledgeGraph:
    def __init__(self, path: Path = GRAPH_PATH):
        self.path = path
        self.data = {"nodes": {}, "edges": [], "meta": {"created": _now(), "ticks": 0}}
        if path.exists():
            self.data = json.loads(path.read_text())

    # ---- nodes ----
    def upsert_node(self, node_id: str, ntype: str, **attrs) -> dict:
        assert ntype in NODE_TYPES, f"bad node type {ntype}"
        n = self.data["nodes"].get(node_id, {
            "id": node_id, "type": ntype, "created": _now(),
            "sentiment_history": [], "attrs": {},
        })
        n["type"] = ntype
        n["updated"] = _now()
        n["attrs"].update(attrs)
        self.data["nodes"][node_id] = n
        return n

    def add_sentiment(self, node_id: str, score: float, confidence: float,
                      source: str, simulated: bool = False) -> None:
        n = self.data["nodes"].get(node_id)
        if not n:
            raise KeyError(f"node {node_id} not found")
        n["sentiment_history"].append({
            "score": round(float(score), 4),
            "confidence": round(float(confidence), 4),
            "source": source, "simulated": bool(simulated),
            "observed_at": _now(),
        })

    def latest_sentiment(self, node_id: str, observed_only: bool = True) -> dict | None:
        n = self.data["nodes"].get(node_id)
        if not n or not n["sentiment_history"]:
            return None
        hist = n["sentiment_history"]
        if observed_only:
            hist = [s for s in hist if not s["simulated"]]
        return hist[-1] if hist else None

    def sentiment_momentum(self, node_id: str, observed_only: bool = True) -> float | None:
        """Latest observed score minus the prior one — proxy for sentiment velocity."""
        n = self.data["nodes"].get(node_id)
        if not n:
            return None
        hist = [s for s in n["sentiment_history"] if (not observed_only or not s["simulated"])]
        if len(hist) < 2:
            return None
        return round(hist[-1]["score"] - hist[-2]["score"], 4)

    # ---- edges ----
    def add_edge(self, src: str, etype: str, dst: str, **attrs) -> dict:
        assert etype in EDGE_TYPES, f"bad edge type {etype}"
        e = {"src": src, "type": etype, "dst": dst, "attrs": attrs, "created": _now()}
        # dedupe identical (src,type,dst); update attrs instead
        for ex in self.data["edges"]:
            if ex["src"] == src and ex["type"] == etype and ex["dst"] == dst:
                ex["attrs"].update(attrs); ex["updated"] = _now()
                return ex
        self.data["edges"].append(e)
        return e

    def neighbors(self, node_id: str, etype: str | None = None) -> list[str]:
        out = []
        for e in self.data["edges"]:
            if e["src"] == node_id and (etype is None or e["type"] == etype):
                out.append(e["dst"])
        return out

    # ---- battle locations ----
    def battles(self) -> list[dict]:
        return [n for n in self.data["nodes"].values() if n["type"] == "battle"]

    def hottest_battles(self, k: int = 5) -> list[dict]:
        """Rank battles by |sentiment momentum| × contestedness (edge count)."""
        scored = []
        for b in self.battles():
            mom = self.sentiment_momentum(b["id"]) or 0.0
            contest = len(self.neighbors(b["id"])) + sum(
                1 for e in self.data["edges"] if e["dst"] == b["id"])
            heat = abs(mom) * (1 + contest) + b["attrs"].get("priority_boost", 0)
            scored.append((heat, b))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [b for _, b in scored[:k]]

    # ---- persistence ----
    def save(self, bump_tick: bool = True) -> Path:
        if bump_tick:
            self.data["meta"]["ticks"] = self.data["meta"].get("ticks", 0) + 1
        self.data["meta"]["last_saved"] = _now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2))
        return self.path

    def summary(self) -> dict:
        nt = {}
        for n in self.data["nodes"].values():
            nt[n["type"]] = nt.get(n["type"], 0) + 1
        return {"nodes": len(self.data["nodes"]), "by_type": nt,
                "edges": len(self.data["edges"]), "ticks": self.data["meta"].get("ticks", 0)}


if __name__ == "__main__":
    kg = KnowledgeGraph()
    kg.upsert_node("TICKER:NVDA", "ticker", sector="Semiconductors")
    kg.upsert_node("NARR:ai-capex-peak", "narrative",
                   label="AI capex is peaking; hyperscaler spend will roll over")
    kg.upsert_node("BATTLE:NVDA-capex", "battle",
                   label="Is NVDA's demand durable or a capex bubble?")
    kg.add_edge("BATTLE:NVDA-capex", "TARGETS", "TICKER:NVDA")
    kg.add_edge("NARR:ai-capex-peak", "DRIVES", "BATTLE:NVDA-capex")
    kg.add_sentiment("BATTLE:NVDA-capex", -0.2, 0.5, "seed:self-test")
    kg.add_sentiment("BATTLE:NVDA-capex", 0.1, 0.6, "seed:self-test-2")
    print("summary:", kg.summary())
    print("momentum:", kg.sentiment_momentum("BATTLE:NVDA-capex"))
    print("hottest:", [b["id"] for b in kg.hottest_battles()])
    kg.save()
    print("saved ->", kg.path)
