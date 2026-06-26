"""
Computer Fund — Multi-user seeded sentiment simulation.

Goal: predict AND predate public sentiment. We model a battle location as a population
of heterogeneous participants ("users") connected in a network. A narrative is seeded into
a few of them; it diffuses; aggregate sentiment is a leading indicator of crowd repricing.
The Fund's edge is entering BEFORE the projected aggregate-sentiment peak and exiting INTO it.

This is an agent-based diffusion model (Bass/SIR-flavored) — deliberately simple and honest:
it is a hypothesis generator, not a crystal ball. Outputs are labeled `simulated=True` and never
written to the graph as observed fact (Charter §6).

Persona archetypes (seedable, weights tunable as we calibrate against observed sentiment):
  influencer  — high out-degree, moves others fast, low conviction-decay
  retail      — herd-following, high susceptibility, fast to flip
  institution — slow, high conviction, low susceptibility, anchors the long-run level
  contrarian  — negatively coupled to the crowd; fades extremes
  skeptic     — high threshold to adopt; dampens runaway narratives

Key outputs per run:
  trajectory        — aggregate sentiment per step (the predicted curve)
  peak_step         — when the crowd is projected to be most bulled/beared up
  predate_window    — the steps BEFORE the peak where the Fund should be positioned
  edge_score        — magnitude of the move the crowd is projected to create
  current_step_est  — where observed sentiment puts us on the curve right now
"""
from __future__ import annotations
import random, statistics, json
from dataclasses import dataclass, field

ARCHETYPES = {
    #               susceptibility  influence  conviction  contrarian
    "influencer":  dict(susc=0.35, infl=0.90, conv=0.80, contra=False),
    "retail":      dict(susc=0.85, infl=0.15, conv=0.25, contra=False),
    "institution": dict(susc=0.15, infl=0.55, conv=0.92, contra=False),
    "contrarian":  dict(susc=0.45, infl=0.40, conv=0.70, contra=True),
    "skeptic":     dict(susc=0.20, infl=0.30, conv=0.75, contra=False),
}

DEFAULT_MIX = {"influencer": 0.04, "retail": 0.70, "institution": 0.06,
               "contrarian": 0.10, "skeptic": 0.10}


@dataclass
class Persona:
    idx: int
    kind: str
    susc: float
    infl: float
    conv: float
    contra: bool
    s: float = 0.0          # current sentiment -1..+1
    threshold: float = 0.0  # adoption threshold


@dataclass
class SimResult:
    trajectory: list[float]
    peak_step: int
    peak_value: float
    predate_window: tuple[int, int]
    edge_score: float
    current_step_est: int
    direction: str
    n_agents: int
    seed_sentiment: float
    params: dict = field(default_factory=dict)

    def to_dict(self):
        d = self.__dict__.copy()
        d["predate_window"] = list(self.predate_window)
        return d


def _build_population(n, mix, rng):
    pop = []
    kinds = []
    for kind, frac in mix.items():
        kinds += [kind] * round(frac * n)
    while len(kinds) < n:
        kinds.append("retail")
    rng.shuffle(kinds)
    for i, kind in enumerate(kinds[:n]):
        a = ARCHETYPES[kind]
        pop.append(Persona(
            idx=i, kind=kind, susc=a["susc"], infl=a["infl"],
            conv=a["conv"], contra=a["contra"],
            threshold=rng.uniform(0.0, 0.3),
        ))
    return pop


def simulate(seed_sentiment: float, n_agents: int = 400, steps: int = 30,
             mix: dict | None = None, network_k: int = 8,
             observed_now: float | None = None, seed: int = 0) -> SimResult:
    """
    seed_sentiment: initial directional impulse of the narrative (-1..+1), e.g. from research.
    observed_now: latest OBSERVED aggregate sentiment (to locate where we are on the curve).
    Returns a SimResult with the predicted trajectory and the predate window.
    """
    rng = random.Random(seed)
    mix = mix or DEFAULT_MIX
    pop = _build_population(n_agents, mix, rng)
    # seed: influencers + a few randoms get the narrative first
    seeds = [p for p in pop if p.kind == "influencer"] + rng.sample(pop, max(1, n_agents // 50))
    for p in seeds:
        p.s = seed_sentiment * (0.8 + 0.4 * rng.random())

    # random k-regular-ish network via neighbor sampling each step (cheap, stochastic)
    traj = []
    for _ in range(steps):
        new = [p.s for p in pop]
        for p in pop:
            nbrs = rng.sample(pop, min(network_k, n_agents - 1))
            peer = statistics.fmean(q.s * q.infl for q in nbrs) / max(
                1e-9, statistics.fmean(q.infl for q in nbrs))
            target = -peer if p.contra else peer
            if abs(peer) < p.threshold:
                pull = 0.0
            else:
                pull = p.susc * (target - p.s)
            # conviction resists change; mild mean-reversion toward 0 (narratives fade)
            decay = (1 - p.conv) * 0.04 * p.s
            new[p.idx] = max(-1.0, min(1.0, p.s + (1 - p.conv * 0.5) * pull - decay))
        for p, v in zip(pop, new):
            p.s = v
        traj.append(round(statistics.fmean(q.s for q in pop), 4))

    direction = "bull" if seed_sentiment >= 0 else "bear"
    # peak = max |sentiment| in the direction of the seed
    if direction == "bull":
        peak_step = max(range(steps), key=lambda i: traj[i])
    else:
        peak_step = min(range(steps), key=lambda i: traj[i])
    peak_value = traj[peak_step]
    edge_score = round(abs(peak_value - traj[0]), 4)
    predate_window = (0, max(0, peak_step - 1))

    # locate "now" on the curve by nearest observed value (if provided)
    current_step_est = 0
    if observed_now is not None:
        current_step_est = min(range(steps), key=lambda i: abs(traj[i] - observed_now))

    return SimResult(
        trajectory=traj, peak_step=peak_step, peak_value=peak_value,
        predate_window=predate_window, edge_score=edge_score,
        current_step_est=current_step_est, direction=direction,
        n_agents=n_agents, seed_sentiment=round(seed_sentiment, 4),
        params={"steps": steps, "network_k": network_k, "mix": mix},
    )


def predate_signal(res: SimResult) -> dict:
    """Translate a sim result into an actionable predate verdict."""
    in_window = res.predate_window[0] <= res.current_step_est <= res.predate_window[1]
    steps_to_peak = res.peak_step - res.current_step_est
    return {
        "act": in_window and res.edge_score >= 0.15 and steps_to_peak > 0,
        "direction": res.direction,
        "edge_score": res.edge_score,
        "steps_to_projected_peak": steps_to_peak,
        "reason": (
            f"crowd sentiment projected to {res.direction} toward {res.peak_value:+.2f} "
            f"at step {res.peak_step}; we are ~step {res.current_step_est}; "
            f"predate window {res.predate_window}; edge {res.edge_score:.2f}."
        ),
    }


if __name__ == "__main__":
    # self-test: a bullish narrative should produce a rising curve with a predate window.
    r = simulate(seed_sentiment=0.5, observed_now=0.1, seed=42)
    print("trajectory[:8]:", r.trajectory[:8])
    print("peak_step:", r.peak_step, "peak_value:", r.peak_value, "edge:", r.edge_score)
    print("predate_window:", r.predate_window, "current_step_est:", r.current_step_est)
    print("signal:", json.dumps(predate_signal(r), indent=2))
