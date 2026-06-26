"""Offline diagnostics for the sentiment simulator's saturation and edge behavior.

These metrics are deliberately fixture-only. They use deterministic seeds and simulated
sentiment labels; no broker connectors, live market data, or account state are touched.
"""
from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from typing import Any

from sim.sentiment_sim import simulate


@dataclass(frozen=True)
class Scenario:
    name: str
    seed_sentiment: float
    observed_now: float | None
    network_mode: str
    influencer_cascade: float


SCENARIOS = (
    Scenario("baseline_resampled", 0.5, 0.1, "resampled", 1.0),
    Scenario("persistent_network", 0.5, 0.1, "persistent", 1.0),
    Scenario("persistent_influencer_cascade", 0.5, 0.1, "persistent", 2.5),
    Scenario("max_seed_baseline", 1.0, 0.1, "resampled", 1.0),
)


def _quantiles(values: list[float]) -> dict[str, float]:
    sorted_values = sorted(values)
    return {
        "p10": round(sorted_values[int(0.10 * (len(sorted_values) - 1))], 4),
        "p50": round(statistics.median(sorted_values), 4),
        "p90": round(sorted_values[int(0.90 * (len(sorted_values) - 1))], 4),
    }


def measure_scenario(scenario: Scenario, *, seeds: int, steps: int, n_agents: int, saturation_threshold: float) -> dict[str, Any]:
    rows = []
    for seed in range(seeds):
        result = simulate(
            seed_sentiment=scenario.seed_sentiment,
            observed_now=scenario.observed_now,
            seed=seed,
            steps=steps,
            n_agents=n_agents,
            network_mode=scenario.network_mode,
            influencer_cascade=scenario.influencer_cascade,
        )
        abs_traj = [abs(value) for value in result.trajectory]
        saturated_steps = [step for step, value in enumerate(abs_traj) if value >= saturation_threshold]
        rows.append(
            {
                "edge_score": result.edge_score,
                "peak_step": result.peak_step,
                "peak_value": result.peak_value,
                "current_step_est": result.current_step_est,
                "time_to_saturation": saturated_steps[0] if saturated_steps else None,
                "saturated": bool(saturated_steps),
                "terminal_abs_sentiment": abs_traj[-1],
            }
        )

    saturation_times = [row["time_to_saturation"] for row in rows if row["time_to_saturation"] is not None]
    edges = [row["edge_score"] for row in rows]
    peak_steps = [row["peak_step"] for row in rows]
    current_steps = [row["current_step_est"] for row in rows]
    terminals = [row["terminal_abs_sentiment"] for row in rows]

    return {
        "name": scenario.name,
        "params": {
            "seed_sentiment": scenario.seed_sentiment,
            "observed_now": scenario.observed_now,
            "network_mode": scenario.network_mode,
            "influencer_cascade": scenario.influencer_cascade,
            "seeds": seeds,
            "steps": steps,
            "n_agents": n_agents,
            "saturation_threshold_abs": saturation_threshold,
        },
        "saturation_rate": round(sum(row["saturated"] for row in rows) / seeds, 4),
        "time_to_saturation_mean": round(statistics.fmean(saturation_times), 4) if saturation_times else None,
        "edge_score_mean": round(statistics.fmean(edges), 4),
        "edge_score_quantiles": _quantiles(edges),
        "peak_step_mean": round(statistics.fmean(peak_steps), 4),
        "peak_step_quantiles": _quantiles([float(value) for value in peak_steps]),
        "current_step_est_mean": round(statistics.fmean(current_steps), 4),
        "terminal_abs_sentiment_mean": round(statistics.fmean(terminals), 4),
    }


def run_metrics(*, seeds: int = 30, steps: int = 30, n_agents: int = 400, saturation_threshold: float = 0.18) -> dict[str, Any]:
    return {
        "label": "simulated_sentiment_offline_fixture",
        "note": "All values are deterministic simulated sentiment diagnostics, not observed facts or trading advice.",
        "scenarios": [
            measure_scenario(
                scenario,
                seeds=seeds,
                steps=steps,
                n_agents=n_agents,
                saturation_threshold=saturation_threshold,
            )
            for scenario in SCENARIOS
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline sentiment-sim fidelity diagnostics.")
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--n-agents", type=int, default=400)
    parser.add_argument("--saturation-threshold", type=float, default=0.18)
    args = parser.parse_args()
    print(
        json.dumps(
            run_metrics(
                seeds=args.seeds,
                steps=args.steps,
                n_agents=args.n_agents,
                saturation_threshold=args.saturation_threshold,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
