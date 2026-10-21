# Evaluation role — baselines and backtest, 2022Q1 to 2026Q2

**Handoff to the team. Built only from the public files in `../data/` and the two roles' committed
outputs. Nothing dated after Oct 21 2026.**

Reproduce with `python Evaluation/evaluation.py` (pandas, numpy, scipy, matplotlib; scipy ships with
statsmodels). Full printed log: [`outputs/run_log.txt`](outputs/run_log.txt). Charts:
[`outputs/evaluation_diagnostics.png`](outputs/evaluation_diagnostics.png).

---

## 1. What this role adds

The packet asks Evaluation to *compute the baselines and backtest the traffic and price methods
quarter by quarter from 2022 to Q2 2026*. Both roles had already backtested their own core method,
so this role does not just copy their numbers. Instead it:

1. **Re-implements every method from the roles' write-ups and checks the output against their
   committed backtests.** If the re-implementation matches, the backtests are reproducible from the
   write-ups alone. Otherwise the gap shows where a write-up and its code differ.
2. **Runs the packet's full window.** Price started at 2023Q1; the packet asks for 2022.
3. **Backtests what the roles blended but never scored:** Traffic's M2 and its 65/35 blend, and a
   Price blend with weights it could have known at the time. Price's own blend is in-sample.
4. **Runs the two "naive regression" benchmarks out of sample** (Traffic M3, Price M4). Both roles
   fitted them once, on the whole sample.
5. **Checks that the intervals are calibrated**, i.e. that an 80% band covers about 80% of outcomes.
6. **Scores the product.** Passenger revenue = passengers × fare is the number the client and the
   guidance check care about. This role measures how the two halves' errors combine.

---

## 2. Reproduction audit

| Role | Series | Quarters | Max abs difference |
|---|---|---|---|
| Traffic | M1, B0, B1 | 2022Q1–2026Q2 (18) | **0** (exact) |
| Price | P1, P2, P3, M4, B0, B1 | 2023Q1–2026Q2 (14) | **$0.0005** (CSV rounding) |
| Price | delivered blend | 2023Q1–2026Q2 (14) | $0.009 (weights rounded to 3 dp in `forecast.csv`) |

Both roles' backtests reproduce from their write-ups. The Q3 2026 forecasts also reproduce: M1
32,771k (Traffic 32,772k), M2 33,165k (33,171k), M3 32,097k, and P1/P2/P3 $227.16/$229.02/$230.79,
identical to Price.

---

## 3. The backtest table by period (the deliverable)

Every quarter replays the information an analyst actually had: TSA and EIA through quarter-end, BLS
CPI through month 3, T-100 through **month 1 only**, and Southwest's own figures through Q−1. All
parameters are re-estimated from that vintage.
Quarter by quarter: [`outputs/backtest_quarterly.csv`](outputs/backtest_quarterly.csv).
All statistics (MAPE, bias, RMSE, sd, wins vs B1): [`outputs/backtest_by_period.csv`](outputs/backtest_by_period.csv).

The packet asks for **2022–2024** and **2025–2026** to appear separately. 2022 is also broken out,
because its baselines are computed off COVID-depressed 2021 bases and on their own would make any
method look good.

### Revenue passengers — MAPE %

| Period | n | **M1** TSA chain | M2 capacity | **Traffic blend** | M3 naive OLS (OOS) | B0 | B1 |
|---|---|---|---|---|---|---|---|
| 2022–2024 (pre fee change) | 12 | **3.81** | 7.96 | 4.82 | 2.65 *(n=8)* | 11.90 | 10.29 |
| ‣ of which 2022 (COVID base) | 4 | 6.38 | 12.89 | 8.20 | — | 23.02 | 21.56 |
| ‣ of which 2023–2024 | 8 | **2.52** | 5.50 | 3.13 | 2.65 | 6.34 | 4.65 |
| **2025–2026 (fee + model change)** | 6 | **1.50** | 2.18 | **1.12** | 1.74 | 4.07 | 2.64 |
| Full sample | 18 | **3.04** | 6.03 | 3.59 | 2.26 *(n=14)* | 9.29 | 7.74 |

### Average fare — MAPE % (2026Q2 scored on the ex-breakage $233.90, the basis both roles forecast)

| Period | n | P1 | **P2** | **P3** | Blend, in-sample | **Blend, out-of-sample** | Blend, equal | M4 (OOS) | B0 | B1 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022–2024 (pre fee change) | 12 | 8.27 | **3.69** | 5.74 | 4.43 | 4.30 | 4.50 | 8.06 *(n=8)* | 8.16 | 5.39 |
| ‣ of which 2022 (COVID base) | 4 | 10.60 | 6.89 | 7.74 | 5.51 | 5.49 | 5.40 | — | 17.43 | 9.41 |
| ‣ of which 2023–2024 | 8 | 7.10 | **2.09** | 4.74 | 3.90 | 3.71 | 4.04 | 8.06 | 3.52 | 3.39 |
| **2025–2026 (fee + model change)** | 6 | 6.70 | 4.41 | **3.67** | 4.30 | **4.42** | 4.46 | 4.86 | 9.96 | 4.95 |
| Full sample | 18 | 7.74 | **3.93** | 5.05 | 4.39 | 4.34 | 4.48 | 6.69 *(n=14)* | 8.76 | 5.25 |

### Passenger revenue (the product) — MAPE %

| Period | n | **Team product** (Traffic blend × Price OOS blend) | M1 × Price OOS blend | B0 | B1 |
|---|---|---|---|---|---|
| 2022–2024 (pre fee change) | 12 | 5.70 | 5.28 | 17.01 | 10.89 |
| ‣ of which 2022 (COVID base) | 4 | 11.10 | 8.55 | 35.68 | 23.16 |
| ‣ of which 2023–2024 | 8 | **3.00** | 3.64 | 7.68 | 4.76 |
| **2025–2026 (fee + model change)** | 6 | **3.51** | 3.14 | 6.72 | 3.86 |
| Full sample | 18 | 4.97 | 4.56 | 13.58 | 8.54 |

**M2** uses a vintage-legal ASM stand-in: last year's ASMs scaled by the YoY change in T-100 domestic
ASMs for month 1. Southwest's historical ASM guidance is not in the packet. Running M2 on *actual* ASMs
("oracle", in the CSV) does not help: 3.01% in the current era against 2.18%.

---

## 4. What the table says

**E1. The passenger signal beats the baselines everywhere, and in the current era the edge is close
to statistically significant.** M1 beats B1 in 16 of 18 quarters and in every period, including
2023–2024 with COVID bases removed (2.52% vs 4.65%). A Diebold-Mariano test with the small-sample
correction gives p = 0.08 for M1 and p = 0.05 for the Traffic blend against B1 in 2025–2026. With
n = 6, that is as strong as evidence gets.

**E2. The fare half does not reliably beat a one-line naive forecast, and so neither does the
product.** In 2023–2024, B1 (3.39%) beats the out-of-sample blend (3.71%); only P2 beats it. In
2025–2026 the blend's edge over B1 is half a point (4.42% vs 4.95%), it wins 3 of 6 quarters, and
DM p = 0.44. The product wins 4 of 6 quarters, with p = 0.53. **The packet's "2022–2024" aggregate
flatters the price methods:** the blend's pre-fee advantage over B1 comes entirely from 2022's
COVID bases.

| DM test vs B1, 2025–2026 (n=6) | M1 | Traffic blend | P2 | P3 | Price OOS blend | **Product** |
|---|---|---|---|---|---|---|
| p-value | 0.08 | **0.05** | 0.60 | 0.13 | 0.44 | **0.53** |

All periods: [`outputs/dm_tests.csv`](outputs/dm_tests.csv).

**E3. Price's in-sample blend did not flatter its score much.** Weights refitted each quarter from
earlier errors only score 4.42% against the in-sample 4.30%. Equal weights score 4.46%. The weights
barely matter because P1–P3 move together. For Q3 2026 itself, the delivered weights are vintage-legal:
all six current-era errors were known before Q3.

**E4. The naive regression is a closer challenger than Traffic's write-up suggests, and it points
lower for Q3.** Refitted each quarter, M3 scores 1.74% in the current era (M1 1.50%) and 2.65% in
2023–2024 (M1 2.52%). Traffic's case against it (F6) concerns mechanism, not accuracy. But for Q3 2026
M3 says **32,097k, 2.1% below M1**, a gap bigger than either method's typical error. M3 has
under-forecast in three of the last four quarters, which is consistent with it ignoring the Sep 2025
share-regime flip. We read its Q3 call as biased low, but the disagreement is worth naming.

**E5. July's capacity filing sits below the bottom of ASM guidance.** T-100 domestic ASMs for
July 2026 are **−1.84% YoY**; guidance is −1% to flat. Run at the July rate, M2 gives **32,718k**,
not the 33,171k Traffic gets at the guided midpoint. That would move the blend from 32,912k to
about 32,753k (−0.5%). This is a downside skew to the passenger point, inside the interval.

**E6. On a fair basis, the fare forecast is the naive forecast.** The packet's B1 fare ($220.67)
uses the reported Q2 fare, which carries the $285M one-off. On the ex-breakage basis B1 is
**$228.78**, and the team's $229.34 sits **0.24%** above it. Against the packet's B1 the team looks
4% "better", but that comparison is unfair to the baseline. The product is $7,548M, against B1 of
$7,650M ex-breakage and $7,378M as reported.

| Q3 2026 baselines | B0 | B1 (packet basis) | B1 (ex-breakage) | Team | Team vs fair B1 |
|---|---|---|---|---|---|
| Revenue passengers (000s) | 34,581 | 33,436 | 33,436 | 32,912 | −1.57% |
| Average fare ($) | 182.56 | 220.67 | **228.78** | 229.34 | **+0.24%** |
| Passenger revenue ($M) | 6,313 | 7,378 | 7,650 | 7,548 | −1.33% |

**E7. A one-off in the print would double the fare error.** Every method forecasts the underlying
fare. In 2026Q2 the out-of-sample blend erred +3.7% against the ex-breakage fare and **+7.5%**
against the reported one. If Q3 carries a similar item, the reported number moves by ~$8 for a
reason no public signal sees.

---

## 5. Intervals — do the 80% bands cover 80%?

Each role's delivered half-width, applied to the errors its own method made:

| | Half-width | 2023–2024 | 2025–2026 | **All 14 post-COVID quarters** |
|---|---|---|---|---|
| Traffic (M1 errors) | ±2.05% | 2/8 | 5/6 | **50%** |
| Price (OOS blend errors) | ±7.16% | 7/8 | 6/6 | **93%** |

**E8. Traffic's band is too narrow and Price's too wide, for different reasons.**
- Traffic sized its band on the current era's six quarters. These are the **calmest six-quarter
  stretch in M1's record**: rolling sd runs 1.67–3.33% across post-COVID windows, and the latest is
  the minimum. The band assumes that calm continues straight after a structural break.
- Both roles say "Student-t, 5 df", but they implement it differently. Traffic rescales the t to
  have the backtest sd, so the 80% half-width is 1.14 sd. Price uses the sd as the t's scale, so the
  half-width is 1.48 sd, **29% wider** for the same evidence.

A vintage-legal rolling rule (half-width = k × sd of the previous six errors) confirms both
problems. Results: [`outputs/interval_calibration.csv`](outputs/interval_calibration.csv).

**Recommendation to Integration: put both halves on the same rule.** Use the error sd over all
14 post-COVID quarters (2023Q1–2026Q2, which drops 2022's COVID bases and keeps both regimes), with a
Student-t on 13 df rescaled to that sd:

| | sd (14q) | Half-width | Point | **Harmonised 80% interval** | Delivered interval |
|---|---|---|---|---|---|
| Revenue passengers (M1 errors) | 2.45% | ±3.04% | 32,912 | **31,912 – 33,912** | 32,237 – 33,589 |
| Average fare (OOS blend errors) | 4.73% | ±5.88% | $229.34 | **$215.87 – $242.82** | $212.92 – $245.75 |

[`outputs/interval_recommendation.csv`](outputs/interval_recommendation.csv). M1's errors are used for
Traffic, not the blend's, because the blend's backtest runs on an ASM proxy rather than the guidance
the delivered blend uses.

---

## 6. How the two halves' errors combine

**E9. The passenger and fare errors are negatively correlated, for a mechanical reason.**

| Period | n | ρ (M1, Price OOS blend) | 80% band on ρ | sd pax | sd fare | sd product |
|---|---|---|---|---|---|---|
| 2023–2024 | 8 | −0.21 | −0.65 to +0.35 | 2.97% | 4.71% | 4.11% |
| 2025–2026 | 6 | **−0.76** | −0.94 to −0.24 | 1.67% | 4.91% | 4.03% |
| 2023Q1–2026Q2 | 14 | **−0.38** | −0.66 to −0.01 | 2.45% | 4.73% | 3.98% |

The two halves share no input: Traffic uses TSA and T-100, Price uses BLS and EIA. But Southwest's
fare is *defined* as passenger revenue ÷ revenue passengers, and the fare methods never see the
passenger count. When passengers come in below forecast, the same revenue is spread over fewer of
them, so the fare comes in above forecast. **The 2026 trip-factor shift is exactly this: fewer
revenue passengers and a higher fare.** The current era's −0.76 is the regime where that shift is
live.

The consequence is that **the product is more accurate than the halves imply.** Treating the halves
as independent would give a post-COVID product sd of 5.33%; the realised sd was 3.98%.
**Recommendation: combine with ρ = −0.4** (the 14-quarter estimate, the more conservative one), and
show ρ = 0 as the cautious bound. [`outputs/error_correlation.csv`](outputs/error_correlation.csv).

**E10. Traffic's assumed M1/M2 correlation (ρ = 0.7) is conservative.** The realised correlation
runs +0.2 to +0.6 before 2025 and about zero since. That makes this part of Traffic's interval too
wide, but the backtest-sd choice (E8) is the larger effect and pushes the other way.

---

## 7. Decisions and caveats

| Decision | Reason |
|---|---|
| Both roles' cleaning decisions reused unchanged | Evaluation's job is to score the methods as built, not to re-litigate the inputs. |
| **Re-implemented, not imported** | Both role scripts run end to end at import and overwrite their outputs. A re-implementation also turns the comparison into an audit. |
| Era split at 2025Q1, as both roles did | Bag fees start May 28 2025, so 2025Q1 is technically pre-fee. Kept for comparability; it is one quarter of six. |
| 2022 shown separately inside 2022–2024 | B0/B1 for 2022 compare against COVID-depressed 2021 quarters and err by 20–45%. Folding 2022 in would flatter every method against the baselines. |
| Price's P2 run for 2022 even though its season dummies are thin | For 2022Q1 only three normal-year steps (2019Q2–Q4) exist before it, so the Q1 dummy is unidentified and comes out zero. That is what the method would really have done. |
| M2 backtested with a T-100 ASM proxy | Historical ASM guidance is not in the packet. The month-1 T-100 ASM is the only capacity signal on file at forecast time. |
| **Out-of-sample Price blend** = Price's own rule (inverse MSE within era, shrunk 50%), errors before t only | Isolates the effect of the in-sample weights from everything else. |
| Diebold-Mariano with the Harvey-Leybourne-Newbold correction, t(n−1) | The plain DM statistic over-rejects badly at n = 6. |
| **Not removable: data vintage** | 2023 and H1 2025 Southwest figures come from later releases' prior-year columns (possibly restated), and recent T-100 months can be revised. The backtest uses today's values for both, so it is very slightly optimistic. |

---

## 8. PoV for the debate — Flag, and here is what the evidence supports selling

The scorecard splits cleanly along the line Traffic drew:

- **Sellable: the passenger nowcast.** It beats both baselines in every period, wins 16 of 18
  quarters against B1, and its current-era edge is about as close to significance as six quarters
  allow (p = 0.05–0.08).
- **Not yet sellable on accuracy: the fare, and therefore the revenue figure.** On a fair basis the
  fare forecast sits 0.24% from a one-line naive forecast. The product beats B1 by a third of a point
  in the current era with p = 0.53. The client's number does not have a demonstrated edge.
- **Sellable as attribution, though.** Price's industry/own, fuel/non-fuel and mix/yield split
  ([Price §8](../Price/README.md)) is explanation, and a backtest of the point forecast cannot measure it.

Conditions under which Evaluation would tell the client to stop trusting the signal (in addition to
Traffic's and Price's):

1. **M1 loses to B1 in two consecutive quarters** → the passenger edge, the one thing with evidence
   behind it, is gone. Re-run this backtest each quarter. It takes seconds.
2. **The product's realised error leaves the harmonised interval twice in four quarters** → the
   negative-correlation offset (E9) has broken, and the product interval is understated.
3. **M1 and M3 disagree by more than 2% again** → one of them is missing a regime change. They
   disagree by 2.1% for Q3 2026, so this flag is already raised. Q3's actual will say which one.

---

## 9. Files

| File | Contents |
|---|---|
| [`evaluation.py`](evaluation.py) | Re-implementation, backtest, audit, calibration and correlation; prints the whole log |
| [`outputs/backtest_quarterly.csv`](outputs/backtest_quarterly.csv) | Every method and baseline, both targets and the product, 2022Q1–2026Q2, forecasts and % errors |
| [`outputs/backtest_by_period.csv`](outputs/backtest_by_period.csv) | **The deliverable:** MAPE, bias, RMSE, sd and wins vs B1, by period |
| [`outputs/baselines_q3_2026.csv`](outputs/baselines_q3_2026.csv) | B0/B1 for Q3 2026 on both fare bases, against the team's numbers |
| [`outputs/reproduction_audit.csv`](outputs/reproduction_audit.csv) | Re-implementation vs each role's committed backtest |
| [`outputs/dm_tests.csv`](outputs/dm_tests.csv) | Diebold-Mariano (HLN) tests against B1, by period |
| [`outputs/interval_calibration.csv`](outputs/interval_calibration.csv) | Coverage of the delivered bands and of three rolling rules |
| [`outputs/interval_recommendation.csv`](outputs/interval_recommendation.csv) | Harmonised 80% intervals for both halves |
| [`outputs/error_correlation.csv`](outputs/error_correlation.csv) | Passenger/fare error correlation and product sd, by period |
| [`outputs/price_oos_blend_weights.csv`](outputs/price_oos_blend_weights.csv) | The out-of-sample Price blend's weights, quarter by quarter |
| [`outputs/evaluation_diagnostics.png`](outputs/evaluation_diagnostics.png) | Four diagnostic charts |
| [`outputs/run_log.txt`](outputs/run_log.txt) | Complete printed output of the run |
