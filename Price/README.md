# Price role — Q3 2026 average passenger fare forecast

**Handoff to the team. Built only from the public files in `../data/`, nothing dated after Oct 21 2026.**

Reproduce with `python Price/price_forecast.py` (needs pandas, numpy, matplotlib — same as Traffic).
Full printed log: [`outputs/run_log.txt`](outputs/run_log.txt). Charts: [`outputs/price_diagnostics.png`](outputs/price_diagnostics.png).

---

## 1. The number

| | Average passenger fare, Q3 2026 |
|---|---|
| **Point forecast** | **$229.34** |
| **80% interval** | **$212.92 – $245.75** |
| Implied YoY | **+25.6%** (Q3 2025 = $182.56) |
| vs baseline B0 (Q3 2025) | +$46.78 |
| vs baseline B1 (packet, Q3 2025 × reported Q2'26 YoY = $220.67) | +$8.67 |
| vs B1 rebuilt on the ex-breakage Q2 fare ($228.78) | +$0.56 |

**Team product:** $229.34 × Traffic's 32,912k passengers = **$7,548M passenger revenue**, inside the
guided band on both the packet's 92% share and a seasonally adjusted share (§6).

Most of the gap to the packet's B1 comes from fixing the Q2 basis, not from the models. The value
the models add is that three unrelated signals agree, a defensible interval, and an attribution of
*why* the fare rose (§7).

---

## 2. How it is built

Three methods, each anchored on a different public signal, backtested the same way and blended:

| | Idea | Formula | Q3 2026 |
|---|---|---|---|
| **P1** Industry anchor | Southwest tracks the industry plus its own premium | fare YoY = BLS airfare CPI YoY + last quarter's Southwest premium | $227.16 |
| **P2** Seasonal step | Start from Q2, walk to Q3 the way Southwest normally does | Q3 = Q2 × exp(season effect + β × CPI's Q2→Q3 step) | $229.02 |
| **P3** Fuel pass-through | The fare has to cover the new fuel cost per passenger | fare = last year + Δ fuel cost per passenger + last quarter's non-fuel change | $230.79 |
| M4 Naive regression | Benchmark only, not blended (see §4) | fare YoY ~ a + b · CPI YoY | $210.60 |

**The three blended methods land within 1.6% of each other** while leaning on industry prices,
seasonality and unit cost respectively. That agreement is the main evidence for the point.

Inputs that drive Q3:

| Input | Value | Source |
|---|---|---|
| BLS airfare CPI, Q3 YoY | +21.33% (log) | all three months of Q3 already published |
| Southwest premium over CPI, Q2 2026 | +0.53pp | ex-breakage Q2 fare |
| P2 season effect / slope β | −1.00% / **0.42** | pooled regression, normal years only |
| Southwest Q3 fuel price | **$4.06/gal** | EIA spot $3.83 + Southwest's average premium over spot in the last 4 quarters |
| Fuel gallons per passenger | 16.4 | Q3 2025 × last quarter's YoY change |

**Blend weights** are inverse current-era MSE, shrunk 50% toward equal because they rest on only six
quarters: **P1 0.24, P2 0.33, P3 0.43**.

---

## 3. The finding that matters: Southwest now moves 1-for-1 with the industry

The obvious regression (M4: fare YoY on CPI YoY, 2022–2025) fits a slope of only **~0.35**: in calm
years Southwest's fare barely followed the industry index. Then it misses **2026Q1 by −7.1% and
2026Q2 by −8.8%**.

| | 2025Q3 | 2025Q4 | 2026Q1 | 2026Q2 (ex-breakage) |
|---|---|---|---|---|
| Southwest fare YoY | +3.7% | +7.6% | +15.4% | **+22.6%** |
| BLS airfare CPI YoY | +2.4% | −4.2% | +7.6% | **+22.1%** |
| Southwest premium | +1.3pp | +11.8pp | +7.7pp | **+0.5pp** |

(log %; 2025Q4 CPI uses the interpolated October)

In 2026 the two series lock together. The timeline explains why: **Southwest terminated its fuel
hedges in Q2 2025**, so the 2026 fuel shock reached its fares the same way it reached every other
carrier's. This is why P1 carries the premium with an implied slope of 1, not 0.35.

**A high-fit historical relationship is exactly the wrong tool across a regime break.** M4 is kept
as a labelled benchmark, outside the blend — the same lesson Traffic found with its M3.

---

## 4. The second finding: Southwest's seasonal swings are damped

P2's first version assumed Southwest's usual Q2→Q3 step on top of CPI's step. It came out at $237.70,
clearly too high. The seasonal "extra" turned out not to be constant:

| Year | Southwest Q3/Q2 | CPI Q3/Q2 | Extra (log) |
|---|---|---|---|
| 2019 | 0.993 | 0.948 | +0.046 |
| 2022 | 0.885 | 0.892 | −0.008 |
| 2023 | 0.932 | 0.855 | +0.086 |
| 2024 | 0.983 | 0.898 | +0.091 |
| 2025 | 0.978 | 0.981 | −0.003 |
| **2026** | ? | **0.974** | |

When the industry index drops hard in summer, Southwest drops less; when CPI barely moves, the two
match. So P2 was rebuilt as a pooled regression with season dummies and a slope on CPI's step,
which estimates **β = 0.42**. 2026's CPI step looks like 2025's, so Southwest's Q3 is roughly flat on Q2.
This version is also the best performer in the full backtest (§5).

---

## 5. Backtest — 2023Q1 to 2026Q2

Each quarter replays the real information set: Southwest's own figures through Q−1, BLS CPI and EIA
spot through the end of the quarter. Every parameter is re-estimated from that vintage.
The 2026Q2 actual is the ex-breakage fare, since that is what the methods forecast.

| Era | n | P1 | **P2** | **P3** | Blend* | M4 | B0 | B1 |
|---|---|---|---|---|---|---|---|---|
| 2023–2024 (pre fee change) | 8 | 7.10% | **2.09%** | 4.74% | 3.90% | 8.06% | 3.52% | 3.39% |
| **2025–2026 (fee + model change)** | 6 | 6.70% | 4.41% | **3.67%** | 4.30% | 4.86% | 9.96% | 4.95% |
| Full sample | 14 | 6.93% | **3.09%** | 4.28% | 4.07% | 6.69% | 6.28% | 4.06% |

MAPE. *The blend uses weights fitted on 2025–26, so its current-era figure is in-sample;
every other column is fully out-of-sample. Quarter-by-quarter errors: [`outputs/backtest.csv`](outputs/backtest.csv).

Reading it honestly:

- **In the current regime P2 and P3 beat both baselines.** P1 does not — carrying one quarter's premium is noisy.
- **In 2023–2024 only P2 beats the baselines.** In calm years the fare barely moved and "same as last year" was hard to beat.
- 2023Q2 is the worst quarter for every CPI-based method: the industry index fell 12% while Southwest's fare fell 3%.

---

## 6. Cleaning decisions, and the reason for each

| Decision | Reason |
|---|---|
| **Q2 2026 passenger revenue +$285M** (breakage reversal added back) | A one-off. Reported fare $225.61 → underlying **$233.90**. Same basis as Traffic. Using the reported figure drags P1 down to $219.11. |
| **Fare recomputed** as passenger revenue ÷ revenue passengers, not taken from the printed column | So the adjustment flows into every derived figure (yield, premium, non-fuel change). |
| Q4 2024 $116M breakage item **left as reported** | The file does not state its direction; it only touches the 2025Q4 base of the backtest. |
| **BLS Oct 2025 blank → linear interpolation** (256.48) | Not published during the shutdown. Affects only Q4 2025, never Q3 2026. |
| BLS **monthly → quarterly mean**, compared only within the same season | The index is not seasonally adjusted. YoY, or season-controlled steps in P2. |
| **EIA holiday blanks dropped** (87 days) | A quarterly mean is unaffected. |
| Southwest fuel price = **EIA spot + its average premium over spot** (last 4 quarters) | Spot is wholesale; Southwest's reported cost runs above it. The premium varies (+$0.03 to +$0.33), so a 4-quarter average. |
| **2020–2021 excluded** from P2's regression and from the backtest | COVID quarters are a different business. |
| All growth in **log differences** | They add up exactly, which makes the attribution in §8 clean. |

---

## 7. Where the uncertainty lives

The interval combines two sources:

| Source | sd |
|---|---|
| Normal forecast noise — the blend's current-era backtest errors | 4.79% |
| Model disagreement — spread across P1/P2/P3 for Q3 | 0.79% |
| **Combined** | **4.85%** |

Drawn from a **Student-t with 5 df** (200k draws), because the error sd rests on six quarters.
The result is about **±7%**, much wider than Traffic's ±2%: the fare was simply harder to forecast
than boardings through 2025.

Sensitivity:

| Change | Fare |
|---|---|
| **Chosen blend** | **$229.34** |
| P1 with CPI lagged one month (BLS prices advance-purchase quotes) | $237.02 |
| P3 at the company's guided fuel price ($3.725) instead of spot-implied $4.06 | $225.25 |
| P1 on the reported, not ex-breakage, Q2 fare | $219.11 |

**The Q2 basis is the single biggest swing (~$10).** The CPI timing assumption is next.

---

## 8. Who raised the fare? Three lenses

The packet asks whether the fare rise is Southwest's own initiatives or industry-wide. Three ways
to split the same increase:

| | 2026Q1 | **2026Q2** (ex-breakage) | 2026Q3 (forecast) |
|---|---|---|---|
| Fare change | +$32.15 | **+$47.26** | +$46.79 |
| Fare YoY (log) | +15.4% | **+22.6%** | +22.8% |
| **A.** Industry (BLS CPI) | +7.6% | **+22.0%** | +21.3% |
| **A.** Southwest's own premium | +7.7% | **+0.5%** | +1.5% |
| **B.** Fuel cost per passenger | +$4.08 | **+$26.29** | +$27.26 |
| **B.** Everything else | +$28.07 | **+$20.97** | +$19.52 |
| **C.** Longer trips (haul) | +4.4% | **+4.6%** | +4.3% |
| **C.** Higher price per mile (yield) | +10.9% | **+18.0%** | +18.5% |

What it says:

- **Lens A:** in Q1 2026 half the rise was Southwest-specific — bag fees were still lapping a quarter
  without them. By Q2 the industry index explains almost all of it. **Southwest's own premium is under
  1 point**, which does not support management's claim that its initiatives explain most of the gain.
- **Lens B:** about **56% of Q2's dollar increase** matches the rise in fuel cost per passenger.
- **Lens C:** about **a fifth of the % increase is longer trips**, not price. This is the same
  itinerary shift Traffic found in the trip factor — more connections per paying trip.
- **Caveat:** the BLS index includes the first checked bag but not seat-selection fees, so Southwest's
  new seat products may be under-counted on the industry side.

---

## 9. For Integration — read this before multiplying

**The 92% share in the packet is a Q2 number. Q3 runs lower.**

| | Share of operating revenue | Passenger revenue band | Fare implied at Traffic's 32,912k |
|---|---|---|---|
| Packet's flat 92% | 0.9200 | $7,434M – $7,636M | $225.86 – $232.01 |
| Seasonal (Q3'25 × Q2's YoY change) | 0.9148 | $7,392M – $7,593M | $224.58 – $230.70 |

Q3 2025's share was 0.9085 against Q2 2026's 0.9212 (ex-breakage). The team product of **$7,548M**
sits inside both bands, so the halves are consistent either way — but the seasonal band is the
fairer test.

**Fuel risk for the optional share-price call:** spot implies Southwest's Q3 fuel at about **$4.06/gal**,
above the $3.70–3.75 guided on July 22 (September spot averaged ~$4.4). That barely moves the fare, but
it is a downside risk to Q3 earnings.

---

## 10. PoV for the debate

**The price signal is sellable as an attribution tool, less so as a point forecast.**

- The **point** barely beats a rebuilt naive baseline ($229.34 vs $228.78). A client could get close
  with one spreadsheet line, provided they caught the breakage reversal.
- The **interval** is honest at ±7%, which is wide for a fare.
- What public data does well is **explain** the fare: industry vs own, fuel vs non-fuel, mix vs price.
  That is what a hedge fund needs to judge whether management's story holds.

Conditions under which we would tell a client to stop trusting it:

1. **Southwest's premium over the BLS index moves more than ±5pp in a quarter without a known product change** → the industry anchor has decoupled; drop P1.
2. **Southwest re-hedges fuel** → the 2026 1-for-1 relationship will weaken again, and the historical slope (~0.35) comes back into play.
3. **A one-off revenue item appears in the print** (another breakage adjustment) → every method forecasts the underlying fare; the reported fare can differ by ~$8.
4. **BLS misses months or changes what the index includes** (e.g. starts pricing seat fees) → the industry series is no longer comparable over time.

---

## 11. Files

| File | Contents |
|---|---|
| [`price_forecast.py`](price_forecast.py) | Full reproducible pipeline, prints the whole log |
| [`outputs/forecast.csv`](outputs/forecast.csv) | The handoff number, interval, each method and weights |
| [`outputs/quarterly_panel.csv`](outputs/quarterly_panel.csv) | Southwest fare, yield, haul, CPI, fuel by quarter, with growth rates |
| [`outputs/backtest.csv`](outputs/backtest.csv) | Quarter-by-quarter P1/P2/P3/blend/M4 vs B0/B1, 2023Q1–2026Q2 |
| [`outputs/backtest_by_era.csv`](outputs/backtest_by_era.csv) | MAPE by era |
| [`outputs/attribution.csv`](outputs/attribution.csv) | The three-lens split of the fare change |
| [`outputs/price_diagnostics.png`](outputs/price_diagnostics.png) | Four diagnostic charts |
| [`outputs/run_log.txt`](outputs/run_log.txt) | Complete printed output of the run |
