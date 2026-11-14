# polymarket-faa-attribution-02 — Slothana entry (keen-panda-72)

Forecasts Polymarket's FAA outage attribution prices minute by minute, 4 hours
ahead, as five quantiles per market per minute.

## Method

Asymmetric logit-space Student-t bands blended with a price-level normal band,
centred on each market's last price. The last price is the centre because every
attempt to move it (EWMA smoothing, trend drift, mean-reversion) made the
median error worse on the practice cases — at this horizon these prices behave
like a martingale. The spread lives in logit space (multiplicative moves:
narrow near 0/1, wide mid-range), uses Student-t(8df) quantiles for the
jump-heavy tails, widens the downside tail (×1.3) relative to the upside (×0.7)
because in a multi-outcome event most candidates collapse toward zero, and
blends 30% of a price-space band whose sigma scales with sqrt(x(1−x)).

See the header comment in `main.py` for the full reasoning and the local
practice numbers.

## Local practice score

Own scorer, exact pinball formula from the rules, answers fetched from
Polymarket's public price history:

| | pinball loss |
|---|---|
| house baseline | 0.363589 |
| this entry | 0.281893 |

Median error 0.7675, 90% coverage 0.8571.

**Revision 2026-11-14:** upside tail multiplier narrowed 0.7 → 0.6 after a
one-parameter sweep on the practice cases (0.5 scored 0.281669 in-sample,
0.6 scored 0.281893, 0.7 scored 0.282383; 5 of 6 cases improve at 0.6).
0.6 was chosen over the in-sample argmin 0.5 to limit damage on the one
upside-move practice case (p02) and the coverage loss — a guard against
overfitting the practice set.

## Run

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13 standard library only. Deterministic, no network, ~0.06 s per case.
