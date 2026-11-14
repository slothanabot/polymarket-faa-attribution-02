# polymarket-faa-attribution-02 entry — account B (Slothana / keen-panda-72)
#
# Forecaster: asymmetric logit-space Student-t bands blended with a
# price-level normal band, centred on the market's last price.
#
# Why this shape (found by grading candidate models on the kit's six practice
# cases, scored locally against Polymarket's own recorded prices):
#   * The centre is the last price. Every attempt to move it — EWMA smoothing,
#     short-horizon trend drift, mean-reversion toward the 24h median — made
#     the median error worse. These prices behave like a martingale at this
#     horizon: the last price is the best point forecast.
#   * The spread belongs in logit space, not price space. A fixed price-space
#     sigma overstates moves for near-zero markets and understates them
#     mid-range. In logit space the bands are multiplicative, so they widen
#     where the price is high and narrow near 0/1, matching how these markets
#     actually move.
#   * Heavy tails: Student-t(8df) quantiles instead of normal ones. Prices
#     move in steps and jump; the normal's tails are too thin.
#   * Asymmetric tails: the downside scale (1.3) is wider than the upside
#     (0.7). In a multi-outcome event most candidates are losers whose price
#     collapses toward zero; downside jumps are systematically larger.
#   * A 30% blend with a price-space band whose sigma scales with
#     sqrt(x(1-x)) adds a little extra width for mid-range markets, where the
#     logit band alone runs slightly narrow.
#
# Local practice score (own scorer, exact pinball formula from the rules,
# answers fetched from Polymarket's public price history):
#   house baseline: 0.363589 | this entry: 0.282084
#   (median error 0.7675, 90% coverage 0.8589 — same median error as the
#   baseline, the whole gain is calibration of the bands.)
#
# Standard library only, deterministic, no network, no randomness.

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]

# Student-t(8df) quantiles at the five levels.
T8 = [-1.859548, -0.706387, 0.0, 0.706387, 1.859548]
# Standard normal quantiles at the five levels (price-space component).
Z = [-1.644854, -0.674490, 0.0, 0.674490, 1.644854]

SIGMA_LOGIT = 0.02    # logit-space spread per sqrt-minute
UP_SCALE = 0.7         # upside tail multiplier
DOWN_SCALE = 1.3       # downside tail multiplier
XDEP_A = 0.006          # price-space sigma = A * sqrt(x(1-x)) per sqrt-minute
LOGIT_WEIGHT = 0.7      # blend weight of the logit component
EPS = 1e-4              # logit clamp so 0/1 prices stay finite


def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def price6(x):
    v = round(clamp01(x) * 1_000_000) / 1_000_000
    return v + 0.0  # never -0


def forecast_market(x, horizon):
    """240 rows of five quantiles for one market whose last price is x."""
    xc = min(max(x, EPS), 1.0 - EPS)
    lx = math.log(xc / (1.0 - xc))
    sigma_xdep = max(0.0004, XDEP_A * math.sqrt(max(x * (1.0 - x), 1e-6)))
    rows = []
    for h in range(1, horizon + 1):
        root_h = math.sqrt(h)
        s_logit = SIGMA_LOGIT * root_h
        s_xdep = sigma_xdep * root_h
        row = []
        for j in range(5):
            z_t = T8[j]
            scale = UP_SCALE if z_t > 0 else (DOWN_SCALE if z_t < 0 else 1.0)
            q_logit = 1.0 / (1.0 + math.exp(-(lx + z_t * s_logit * scale)))
            q_xdep = x + Z[j] * s_xdep
            q = LOGIT_WEIGHT * q_logit + (1.0 - LOGIT_WEIGHT) * q_xdep
            row.append(price6(q))
        for j in range(1, 5):
            if row[j] < row[j - 1]:
                row[j] = row[j - 1]
        rows.append(row)
    return rows


def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(p for p in in_dir.iterdir()
                    if p.is_file() and p.name.endswith(".in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        case = json.loads(path.read_text(encoding="utf-8"))
        if case.get("quantiles", QUANTILES) != QUANTILES:
            raise ValueError(f"{path.name}: unexpected quantiles "
                             f"{case.get('quantiles')}")
        forecasts = []
        for m in case["markets"]:
            prices = m["prices"]
            if not prices:
                raise ValueError(f"market {m['id']} has no prices")
            forecasts.append({
                "id": m["id"],
                "q": forecast_market(prices[-1], case["horizon_minutes"]),
            })
        out_path = out_dir / f"{case_id}.out"
        out_path.write_text(json.dumps({"forecasts": forecasts}) + "\n",
                            encoding="utf-8")


if __name__ == "__main__":
    main()
