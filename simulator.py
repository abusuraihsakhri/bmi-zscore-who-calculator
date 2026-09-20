#!/usr/bin/env python3
"""Deterministic stress/smoke simulator for the BMI calculator."""

from __future__ import annotations

import argparse
import random
import time

from bmi_zscore import calculate_patient


def run_simulation(iterations: int = 1000, seed: int = 2026) -> dict[str, float]:
    """Run randomized valid calculations through the current core engine."""
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    rng = random.Random(seed)
    start = time.perf_counter()
    pediatric = adult = warnings = 0

    for index in range(iterations):
        if index % 4:
            age_months = rng.uniform(0.0, 228.9)
            sex = rng.choice(("M", "F"))
            height_m = rng.uniform(0.50, 1.90)
            weight_kg = rng.uniform(3.0, 100.0)
        else:
            age_months = rng.uniform(240.0, 900.0)
            sex = None
            height_m = rng.uniform(1.40, 2.05)
            weight_kg = rng.uniform(40.0, 160.0)

        result = calculate_patient(
            patient_id=f"SIM-{index + 1:05d}",
            weight_kg=weight_kg,
            height_m=height_m,
            age_months=age_months,
            sex=sex,
        )
        if result.is_child:
            pediatric += 1
        else:
            adult += 1
        warnings += len(result.warnings)

    elapsed = time.perf_counter() - start
    return {
        "iterations": iterations,
        "pediatric": pediatric,
        "adult": adult,
        "warnings": warnings,
        "elapsed_seconds": round(elapsed, 4),
        "calculations_per_second": round(iterations / max(elapsed, 1e-9), 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iterations", nargs="?", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    summary = run_simulation(args.iterations, args.seed)
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
