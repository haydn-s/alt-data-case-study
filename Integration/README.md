# Integration role — the combined forecast, the guidance check, the form and the slides

**Built only from the team's committed outputs and the public files in `../data/`. Nothing dated
after Oct 21 2026 enters the forecast.**

Reproduce with `python Integration/integrate.py`. The slide deck is built from these outputs by
`python Presentation/build_presentation.py` (needs `python-pptx`); see [`../Presentation/`](../Presentation/README.md). Full printed log:
[`outputs/run_log.txt`](outputs/run_log.txt).

---

## 1. The submission

**Form closes Oct 21 2026, 12:00 noon ET. One submission per team.** The form itself is an external
web form, so a teammate enters these values by hand. They are also in
[`outputs/form.md`](outputs/form.md).

| Field | Point | 80% interval |
|---|---|---|
| Revenue passengers carried (000s) | **32,912** | **31,912 – 33,912** |
| Average passenger fare ($) | **229.34** | **215.87 – 242.81** |
| Implied passenger revenue ($M) | **7,548** | **7,136 – 7,955** |
| Share price, Oct 22 close (optional) | not submitted | see §6 |

The implied passenger revenue is **inside the guided band** on the packet's 92% share
($7,437M – $7,640M) and on the seasonal 91.5% share ($7,395M – $7,596M).

---

## 2. How the two halves were combined

**Points: the roles' own, unchanged.** 32,912k from Traffic, $229.34 from Price.

**Intervals: Evaluation's harmonised rule, not the roles' delivered bands.** Evaluation found the two
delivered bands miscalibrated in opposite directions
([Evaluation §5](../Evaluation/README.md#5-intervals--do-the-80-bands-cover-80)):

| | Delivered | Covered, 14 post-COVID quarters | On the form |
|---|---|---|---|
| Passengers | 32,237 – 33,589 (±2.05%) | 50% | **31,912 – 33,912** (±3.04%) |
| Fare | $212.92 – $245.75 (±7.16%) | 93% | **$215.87 – $242.81** (±5.88%) |

The causes are different for each half. Traffic sized its band on its six calmest quarters on
record. Price used a t-distribution convention that is 29% wider than Traffic's for the same
evidence. The form puts both halves on one rule: the error sd over all 14 post-COVID backtest
quarters, with a Student-t on 13 df rescaled to that sd. **This is the only place Integration
departs from a role's handoff.** If the team disagrees, the delivered bands are one edit away
(`integrate.py` §1).

**The product interval uses ρ = −0.4 between the two halves' errors, not independence.** The fare is
passenger revenue ÷ revenue passengers, and the fare methods never see the passenger count. When
passengers come in low, the same revenue is spread over fewer of them and the fare comes in high.
Evaluation measured ρ = −0.38 across 14 post-COVID quarters and −0.76 in the current era (E9). The
interval is a bivariate Student-t (13 df), 400k draws:

| Product interval variant | 80% interval ($M) | ± |
|---|---|---|
| **Harmonised halves, ρ = −0.4 (chosen)** | **7,134 – 7,954** | **5.4%** |
| Harmonised halves, ρ = 0 (independent) | 7,050 – 8,053 | 6.6% |
| Harmonised halves, ρ = −0.76 (current era only) | 7,232 – 7,847 | 4.1% |
| Roles' delivered widths, ρ = 0 | 6,988 – 8,112 | 7.4% |

As a cross-check, the product's *own* backtest errors give ±4.9%, between the chosen variant and the
current-era one. Assuming independence would overstate the uncertainty.

---

## 3. The guidance check

| | Low | High |
|---|---|---|
| RASM, Q3 2025 15.25¢ × (1 + 17.5% … 19.5%) | 17.92¢ | 18.22¢ |
| ASMs, Q3 2025 45,567M × (1 − 1% … 0%) | 45,111M | 45,567M |
| **Operating revenue implied** | **$8,083M** | **$8,304M** |
| Passenger revenue at the packet's flat 92% | $7,437M | $7,640M |
| **Passenger revenue at the seasonal 91.48% share** | **$7,395M** | **$7,596M** |

The packet's 92% is a Q2 share. Q3 runs seasonally lower: Q3 2025 was 90.85% against Q2 2025's
91.48%. The seasonal row carries Q3 2025's share forward by Q2 2026's YoY change, measured ex-breakage
(as Price §9 did).

| Check | Result |
|---|---|
| Team product $7,548M inside the 92% band? | **Yes**, 55% of the way up |
| Inside the seasonal band? | **Yes**, 76% of the way up |
| Fare the seasonal band needs at our 32,912k passengers | $224.68 – $230.81. Ours is $229.34 |
| Passengers the seasonal band needs at our $229.34 fare | 32,243 – 33,123k. Ours is 32,912k |
| Implied RASM, seasonal share, mid-guide ASMs | 18.20¢, **+19.3% YoY** (guide +17.5% to +19.5%) |
| Probability mass of our own product interval inside the band | **25%** |

The last row matters most. **The guidance band is far narrower than our uncertainty about the
product.** Landing inside the band is a consistency check, not a validation: three-quarters of our
own distribution sits outside it. The implied RASM is in the upper part of the guide, so we lean to
the optimistic side of management's range.

---

## 4. What the split tells you that the band does not

The packet asks this question directly. Plot passengers against fare and the guidance band becomes a
thin curved strip ([slide 3](../Presentation/southwest_q3_2026_presentation.pptx)):

| Point | Passengers | Fare | Revenue | vs seasonal band |
|---|---|---|---|---|
| **Team** | 32,912k | $229.34 | $7,548M | **inside** |
| B0, same quarter last year | 34,581k | $182.56 | $6,313M | below |
| B1, packet basis (reported Q2) | 33,436k | $220.67 | $7,378M | **below** |
| B1, rebuilt ex-breakage | 33,436k | $228.78 | $7,649M | **above** |

- **The band cannot tell a volume story from a yield story.** Flat passengers at $214–220 satisfies it.
  So do 4.8% fewer passengers at $225–231. Those are different businesses with different implications
  for the stock. Our split says yield.
- **Both naive forecasts miss the band, on opposite sides.** The packet's B1 carries the $285M one-off
  into the fare and lands below. The ex-breakage B1 carries Q2's full fare growth into Q3, which
  management said would slow, and lands above.
- **The split tells you which half to blame when the print misses.** The passenger count has a
  demonstrated edge over the naive baseline; the fare does not (Evaluation E1/E2). A miss on revenue
  is, on the evidence, more likely a fare miss.

---

## 5. The market's view — Kalshi, as a benchmark only

The packet names Kalshi's *Southwest Airlines average passenger fare in Q3* market (KXLUV-26OCTFARE)
as a priced benchmark. Read from the public market page on **Oct 20 2026, about 9:30pm ET**, before
the form closes. Nothing from it enters the forecast, and no account was opened.

| | P(fare > $225) | P(fare > $230) | P(fare > $235) | Median | 80% interval |
|---|---|---|---|---|---|
| **Kalshi** | 77% | 50% | 19% | **$229.71** (normal fit) | $221.81 – $237.62 |
| **Team** | 66% | 47% | 29% | **$229.34** | $215.87 – $242.81 |

**The market and our model agree on the centre to within 40 cents.** The market is 1.7× more
confident. Our band is sized on what our methods' backtest errors actually were, and a one-off
revenue item in the print (Evaluation E7) is a real tail that public data cannot see. If the print
lands between $216 and $222, our interval holds where the market's misses.

---

## 6. The optional share-price forecast — deliberately not submitted

Evaluation found that the revenue product has **no statistically distinguishable edge** over the
naive baseline (DM p = 0.53, E1). Our product also sits inside management's own band. So we have no
informed view on whether the print surprises the market's revenue expectations, which is what would
move the stock. Fuel is a known earnings risk: spot implies about $4.06/gal against the $3.70–3.75
guide (Price §9). But the CFO said on Sep 16 that guidance is still reachable, and the market has had
a month to price that. Submitting a random-walk number would add nothing the TA can't compute, so
the field is left blank. If the team wants to fill it anyway, the honest entry is the Oct 21 close.

---

## 7. The slides

**The deck now lives in [`../Presentation/`](../Presentation/README.md)**: generator, placeholders and
the post-print steps are documented there. What stays here is
[`slides/southwest_q3_2026_readout.pptx`](slides/southwest_q3_2026_readout.pptx), **frozen** as the
pre-print record. It is the deck that went with the form, and its slide 5 lists the four risks we
registered before the print. It is no longer regenerated; to rebuild it, run `build_deck.py` from
commit `6c65ca3`.

The five slides, the packet's maximum, one per required topic:

| # | Packet topic | Slide title | Message |
|---|---|---|---|
| 1 | Forecast against actual | Fewer passengers, a much higher fare | The three numbers with intervals, the actuals, and four benchmarks |
| 2 | Data and cleaning decisions | TSA counts boardings, not passengers | Q2: enplaned +0.3% vs revenue passengers −3.3%; one cleaning decision per source |
| 3 | Model and baselines | The split says yield, not volume | Method in three steps; both baselines miss the guidance band |
| 4 | Backtest by period | Passengers beat naive; fares don't yet | 2023–24 vs 2025–26 MAPE against B1, with DM p-values |
| 5 | What we got wrong and why | What would make us wrong (frozen) / What we got wrong, and why (presentation) | Scorecard, the four pre-registered risks and what each became, PoV with each downgrade trigger's status |

**After the print (Oct 21, after the close):** fill [`actuals.json`](actuals.json) from the Q3 2026
release, then re-run `integrate.py` and `Presentation/build_presentation.py`. **Enplaned passengers**
is the field that matters most: it lets the scorecard split the passenger miss into a boardings error
(the TSA chain) and a trip-factor error (the accounting bridge). The form numbers never read
`actuals.json`, so this cannot move the locked forecast.
The decomposition is exact in logs: `log(F/A) = log(enplaned F/A) − log(trip factor F/A)`.

---

## 8. Decisions and the reason for each

| Decision | Reason |
|---|---|
| Roles' points used unchanged | Points are each role's call. Evaluation's flags on the passenger point (M3 −2.1%, July ASMs below guide, both downward) are shown on slide 5 as pre-registered risks, not applied. |
| Harmonised intervals on the form | One calibration rule for both halves. The delivered bands covered 50% and 93% of post-COVID quarters. |
| ρ = −0.4 for the product | Measured, with a mechanical cause; independence overstates the product's uncertainty by ~20%. |
| Seasonal passenger share used alongside the packet's 92% | Q3's share runs ~0.7 points below Q2's. Both bands reported; the team is inside both. |
| Kalshi as benchmark only | The packet's rule. Read before the form closes; no account, no trade. |
| Share price left blank | No demonstrated edge on revenue, so no informed view on the reaction (§6). |
| Deck generated, not hand-built | Every number traces to a pipeline output, and the post-print version is one re-run away. |

---

## 9. Files

| File | Contents |
|---|---|
| [`integrate.py`](integrate.py) | Combination, product interval, guidance check, split, Kalshi benchmark, form and post-print scorecard |
| [`actuals.json`](actuals.json) | The reported Q3 figures: **null until the print** |
| [`slides/southwest_q3_2026_readout.pptx`](slides/southwest_q3_2026_readout.pptx) | The pre-print readout, **frozen** as the record of what we registered before the print |
| [`outputs/form.md`](outputs/form.md) | The values to enter on the forecast form |
| [`outputs/integration_summary.json`](outputs/integration_summary.json) | Every number the deck uses |
| [`outputs/guidance_check.csv`](outputs/guidance_check.csv) | Both guidance bands, position, probability inside, implied fare and passengers |
| [`outputs/product_interval_sensitivity.csv`](outputs/product_interval_sensitivity.csv) | Product interval under four assumptions |
| [`outputs/split_vs_band.csv`](outputs/split_vs_band.csv) | Team and baselines against the band |
| `outputs/scorecard.csv` | Written only once `actuals.json` is filled |
| [`outputs/run_log.txt`](outputs/run_log.txt) | Complete printed output of the run |
