# Traffic role — Q3 2026 revenue-passenger forecast

**Handoff to the team. Built only from the public files in `../data/`, nothing dated after Oct 21 2026.**

Reproduce with `python Traffic/traffic_forecast.py` (needs pandas, numpy, matplotlib).
Full printed log: [`outputs/run_log.txt`](outputs/run_log.txt). Charts: [`outputs/traffic_diagnostics.png`](outputs/traffic_diagnostics.png).

---

## 1. The number

| | Revenue passengers carried, Q3 2026 |
|---|---|
| **Point forecast** | **32,912 thousand** |
| **80% interval** | **32,237 – 33,589 thousand** |
| Implied YoY | **−4.8%** (Q3 2025 = 34,581) |
| vs baseline B0 (Q3 2025) | −1,669 |
| vs baseline B1 (Q3 2025 × Q2'26 YoY = 33,436) | −524 |

We forecast a **bigger decline than either baseline**. Both baselines are too high because
they carry forward a trip-factor effect that is still growing, and they ignore a national
throughput series that turned down hard in August.

---

## 2. How it is built

Everything runs through one identity, so each piece can be estimated — and argued about — separately:

```
revenue passengers = TSA throughput  ×  Southwest share  ×  uplift  ÷  trip factor
                     (measured)         (nowcast)          (small)    (THE judgement call)
```

| Term | Q3 2026 value | Source | YoY |
|---|---|---|---|
| TSA throughput | 230,749,661 | measured, all 92 days present | −2.85% |
| Southwest share | Jul actual; Aug/Sep at last year's share × 1.0069 | T-100 + TSA | +0.69% |
| Uplift (reported enplanements ÷ T-100 domestic) | 1.0106 | Southwest vs BTS | −0.19% |
| **Trip factor (enplaned ÷ revenue passengers)** | **1.3098** | Southwest reported history only | **+3.40%** |

Three estimates, blended 65/35 (M3 is a benchmark only, not in the blend):

| | Estimate | What it leans on |
|---|---|---|
| **M1** TSA chain | 32,772 | Measured throughput. July is a hard T-100 filing; Aug/Sep are nowcast. |
| **M2** capacity identity `ASM × LF ÷ haul` | 33,171 | Company's own guided ASMs (−1% to flat). |
| M3 naive OLS `revpax_yoy ~ tsa_yoy` | 32,097 | Cautionary benchmark — see §5. |

M1 gets 65% because its inputs are measured rather than guided. M2 keeps 35% because it is
the only route anchored to something the company has publicly committed to. They are **not**
independent — M1 divides by the trip factor, M2 divides by haul, and `haul = distance-per-boarding
× trip factor` — so the interval imposes ρ = 0.7 between their errors. Treating them as
independent would have produced [32,338, 33,490], about 20% too narrow.

The interval's method-error term is a **Student-t with 5 df**, not a normal: it is scaled on a
6-quarter current-regime backtest, and with n=6 the tails are genuinely not pinned down.

---

## 3. The finding that matters: a checkpoint counts boardings, not passengers

This is the whole case. **Q2 2026: enplaned passengers +0.30% YoY, revenue passengers −3.31% YoY.**
The entire wedge is the trip factor, up 3.74%.

| | 2025Q2 | 2025Q3 | 2025Q4 | 2026Q1 | 2026Q2 |
|---|---|---|---|---|---|
| Trip factor | 1.2500 | 1.2668 | 1.2636 | 1.2777 | 1.2967 |
| YoY | −0.80% | +0.63% | +1.25% | **+3.18%** | **+3.74%** |

Assigned seating and the fare bundles (Jan 27 2026) moved travellers onto more connecting
itineraries. Each paying trip now consumes more boardings — and more checkpoint scans.
Distance per boarding is flat at 830–840 miles throughout, which confirms the change is
**itinerary structure, not a different kind of flying**.

**So a TSA checkpoint count is closest to *enplaned* passengers, and it is drifting further
from *revenue* passengers every quarter.** Any pipeline that maps throughput straight onto the
reported passenger count gets the sign right by luck and the magnitude wrong by ~3.5 points a year.

And the sting: **the trip factor is not observable in any public alternative data.** T-100 gives
boardings. TSA gives boardings. Nothing free tells you how many one-way O&D trips those boardings
represent. It has to be extrapolated from Southwest's own quarterly releases — which is exactly
the term that broke. That is the structural limit of this signal, and §7 prices it.

---

## 4. The other finding: the TSA→Southwest share flipped regime in Sep 2025

Southwest's share of national throughput fell 5–12% YoY every month to Aug 2025, then went
positive and has stayed there.

| | Sep'25 | Oct'25 | Jan'26 | Apr'26 | May'26 | Jun'26 | **Jul'26** |
|---|---|---|---|---|---|---|---|
| Share YoY | +0.8% | +2.8% | −1.2% | −1.0% | +1.5% | +2.6% | **+1.6%** |

July 2026 is the cleanest datapoint in the whole packet: **Southwest boardings −0.46% YoY while
national throughput fell 2.06%.** Southwest is outperforming the industry — consistent with a
fuel shock in which it guided capacity down only 1% while others cut harder.

We use the **last 6 months (+0.69%)** for Aug/Sep. Using the pre-2025 average share drift
(≈ −3pp/quarter) would have under-forecast by roughly 1 million passengers.

---

## 5. Cleaning decisions, and the reason for each

| Decision | Reason |
|---|---|
| **No imputation, winsorising or dropping of any TSA day.** | The file is structurally clean: 2,830 rows, 2,830 calendar days, zero missing dates, zero duplicates, zero nulls, zero non-positive counts, integer dtype. There is no defect to repair. |
| Outlier scan calibrated on **2023-07 onward**, not full history. | Scaling the MAD on the full series lets the 2020–21 collapse inflate it and hide ordinary outliers. 24 of 1,188 recent days exceed \|z\|>4; every one is a single day bracketed by normal days (fixed-date vs floating holidays landing on different weekdays across a 364-day lag). A 92-day quarterly sum cannot be moved materially by these, and editing them would inject judgement where the raw file has none. |
| **Flag both lapse windows, repair neither.** | See below. |
| Day counts normalised **per day** for all trend work. | Q1 2024 had 91 days, Q1 2025 had 90 — a 1.1% artefact in a sum-to-sum YoY. Q3 is 92 days in both years, so the target quarter is unaffected either way. |
| **No calendar adjustment inside the forecast chain.** | The chain multiplies *this* year's actual TSA month by *last* year's Southwest share. A share is a ratio over the same days, so day-of-week composition cancels by construction. The adjustment is computed anyway (`cal_effect_pct`) but used only for *reading* the TSA series — e.g. August 2026's −4.41% headline is −4.30% on a like-for-like week. |
| Comparisons at **364-day lag**, not 365. | 52 weeks keeps the weekday aligned; a 365-day lag compares Tuesdays to Mondays. |

### The two funding lapses — flagged, tested, and left alone

Both windows are flagged in [`outputs/tsa_daily_clean.csv`](outputs/tsa_daily_clean.csv)
(`lapse1_shutdown_2025`, 2025-10-01→11-12, 43 days; `lapse2_dhs_2026`, 2026-02-14→04-30, 76 days).

**They do not depress throughput in this file.** Two tests:

- *Event study*, window vs the 49 days either side with a 7-day donut: lapse 1 **+1.08pp** (t=+1.11), lapse 2 **+0.25pp** (t=+0.25).
- *Dummy regression with a linear trend*, 2024-07 onward: lapse 1 **+1.99%** (t=+1.78), lapse 2 **+1.71%** (t=+1.91).

A naive dummy regression *without* the trend term reports lapse 2 at **−2.65%, t=−3.0** — which
looks like a real shutdown effect and is not one. YoY throughput growth was fading at ~2.5pp/yr
and lapse 2 sits late in the sample. Adding the trend flips the sign. **This is the trap in the
packet's "known problem" note, and it is worth 2.7 points of forecast if you fall into it.**

### The packet contradicts the data, and we went with the data

The timeline cites Upgraded Points: average daily throughput **−6.7% for Mar–May 2026, −9.8% in May**.
This file says **+0.34%** and **−0.74%**. That is a 7-to-9 point disagreement.

We did not reconcile it, and we did not adjust the file towards the article. Three reasons:
the Upgraded Points piece is airport-level and the packet itself notes one airport's 76.9% drop
was *partly a data-collection artefact*; the national series here shows no lapse signature under
either test; and imputing a −6.7% that we cannot see would inject the exact bias the flag is
supposed to warn about. **If the series we were handed is the corrected national backfill, it is
the right input and the article is stale.** This is the single biggest open question in our work
and the first thing to say in the readout.

**Why it mostly does not bite:** Q3 2026 and its Q3 2025 base both lie **entirely outside both
lapse windows** (0 flagged days in either). The lapses touch our estimates only through the
Q4'25–Q2'26 quarters used to fit share drift. Re-estimating share growth with every lapse-affected
month dropped gives +0.65% against +0.69% — a forecast difference of 9 thousand passengers, or 0.03%.
**The regime flag is live; it just is not load-bearing for this particular quarter.**

---

## 6. Backtest — 2022Q1 to 2026Q2

Replays the real information set each quarter: TSA daily through quarter-end, T-100 through
**month 1 only** (BTS runs ~3 months late), Southwest's own figures through Q−1. All three
parameters re-estimated from that vintage.

| Era | n | **M1 MAPE** | B0 MAPE | B1 MAPE | M1 bias | M1 sd |
|---|---|---|---|---|---|---|
| 2022–2024 (pre fee change) | 12 | **3.81%** | 11.90% | 10.29% | +2.19% | 4.80% |
| **2025–2026 (fee + model change)** | 6 | **1.50%** | 4.07% | 2.64% | −0.39% | 1.67% |
| Full sample | 18 | **3.04%** | 9.29% | 7.74% | +1.33% | 4.16% |

M1 beats both baselines in both eras, and beats them by most where it counts — the current regime.
The 2022 quarters are COVID-base nonsense for the baselines (B1 errs by 29% and 44%); ignore them.

**The interval uses the current-regime sd (1.67%), not the full-sample sd (4.16%).** The 2022–2024
errors come from a different structure. Using them would have produced a wide interval that is
wide for the wrong reason, and would hide how much of today's risk sits in one unobservable ratio.

M1's bias in the current regime is −0.39%; correcting for it would move the point to 33,039.
Not applied — on 6 quarters at this sd that bias is indistinguishable from noise.

### Why M3 (the obvious regression) is only a benchmark
`revpax_yoy ~ a + b·tsa_yoy` fits beautifully — R² = 0.98, b = 1.06 — and forecasts **32,097**.
It is still the wrong model. It forces one slope across the share regime break *and* the 2026
trip-factor break, so a single coefficient is absorbing three different mechanisms. It happens
to land near our answer this quarter; it will not next quarter, and it cannot tell you why it moved.
**High R² on a structurally-broken series is a warning, not a validation.**

---

## 7. Where the uncertainty actually lives

Monte Carlo, 200k draws. Contribution to M1's sd (thousands of passengers):

| Source | sd |
|---|---|
| All sources | 627 |
| Method / backtest residual | 547 |
| Share growth | 218 |
| Trip factor (parameter only) | 195 |
| Uplift | 80 |

That understates the trip factor, because its *parameter* error is small but its *specification*
error is not. The sensitivity grid is the honest view:

| Share growth ↓ / Trip factor → | E2 seasonal | **blend (chosen)** | E1 YoY-carry | no 2026 step |
|---|---|---|---|---|
| post-flip 11m (+0.32%) | 32,801 | 32,694 | 32,587 | 33,805 |
| **last 6m (+0.69%) — chosen** | 32,878 | **32,771** | 32,664 | 33,884 |
| last 3m (+1.92%) | 33,134 | 33,026 | 32,918 | 34,148 |
| zero drift | 32,735 | 32,627 | 32,521 | 33,736 |

**The trip factor swings the answer by ~1,000; share growth by ~450.** If the trip factor had not
stepped up, the forecast would be ~33,800 — above B1 and close to B0. One unobservable ratio,
extrapolated from four post-break quarters, is the entire call.

---

## 8. For Integration and Price — read this before multiplying

Guidance implies Q3 operating revenue of ~$8.08–8.30bn; passenger revenue was ~92% of that in
Q2 2026, so ~$7.43–7.64bn. Against our 32,912 that requires an average fare of **$225.75–$232.13**
(+23.7% to +27.2% YoY).

**That looks like fare acceleration. It is not — but only once the $285M breakage reversal is handled.**

| Q2 2026 average fare | Value | YoY |
|---|---|---|
| As reported | $225.60 | +20.9% |
| **Ex-breakage reversal** | **$233.90** | **+25.3%** |

The reported +20.9% is depressed by a one-off. The underlying run rate was ~+25%, so the $226–232
our forecast implies is a slight **deceleration** — exactly what management flagged ("held back by
the comparison with a quarter that already had bag fees") and what the RASM guide says
(+17.5–19.5% vs +20.1% underlying in Q2). **The two halves of the team's forecast are consistent.**

> ⚠️ **If Price builds its fare forecast off the reported $225.61 rather than the ex-breakage
> $233.90, it will understate the fare, and the product will fall below the guided band for a
> reason that has nothing to do with traffic. Agree the basis before multiplying.**

Passenger counts the guidance band implies, at fares Price might choose:

| Fare | Passengers implied by the band |
|---|---|
| $215 | 34,558 – 35,535 |
| $220 | 33,773 – 34,727 |
| **$226** | **32,876 – 33,805** ← our forecast sits here |
| $232 | 32,026 – 32,931 |

**What splitting the band tells you that the band does not:** the band is satisfied by roughly flat
passengers at a $215 fare *or* by −5% passengers at a $230 fare. Those are completely different
businesses — one is a volume story, the other is a mix-and-yield story — and the band cannot tell
them apart. Our split says it is the second.

---

## 9. PoV for the debate — Team Flag

**Ship it, with a regime flag.** The signal beat both baselines in every backtest era and by 1.1
points of MAPE in the current one. But the thing that makes it work is not the alternative data.

The TSA and T-100 feeds nowcast **boardings** well. The step from boardings to the reported
**revenue passenger** count runs entirely through the trip factor — which no free public source
observes, which moved 3.7% in a single year, and which we extrapolate from four post-break
quarters. **The alternative data is the reliable part; the accounting bridge on top of it is the
fragile part**, and that is the opposite of how this kind of signal is usually sold.

Conditions under which we would tell a client to stop trusting it:

1. **Trip factor moves more than ±1.5pp from trend in any reported quarter** → the bridge is unstable, downgrade to boardings-only and stop forecasting revenue passengers.
2. **Southwest's share of TSA reverts to negative YoY for two consecutive months** → the Sep 2025 regime flip has unwound; re-estimate, do not extrapolate.
3. **Another funding lapse, or any TSA collection change** → the national series stops being a demand measure. We have now seen that the lapse signature can be *invisible* in the data and still be real in the narrative, which is the worse failure mode.
4. **Southwest stops disclosing enplaned passengers** → the trip factor becomes unobservable entirely and the signal is dead, not degraded.

The honest sales line is narrow: *this nowcasts Southwest boardings from public data to about
1.5%, and converts to revenue passengers using a ratio you must keep re-estimating from the
company's own releases.* Sold that way it clears the bar. Sold as "we count passengers from
checkpoint data" it does not, and Q2 2026 is the proof — that framing would have called the
direction of revenue wrong while the passenger count fell.

---

## 10. Files

| File | Contents |
|---|---|
| [`traffic_forecast.py`](traffic_forecast.py) | Full reproducible pipeline, prints the whole log |
| [`outputs/forecast.csv`](outputs/forecast.csv) | The handoff number, interval and every component |
| [`outputs/tsa_daily_clean.csv`](outputs/tsa_daily_clean.csv) | 2,830 days + lapse flags + 52-week ratio + robust z |
| [`outputs/tsa_quarterly.csv`](outputs/tsa_quarterly.csv) | Quarterly sums, day counts, lapse-day counts, YoY |
| [`outputs/monthly_share_panel.csv`](outputs/monthly_share_panel.csv) | T-100 vs TSA monthly, share and share YoY |
| [`outputs/quarterly_panel.csv`](outputs/quarterly_panel.csv) | Southwest reported + trip factor + haul + uplift |
| [`outputs/backtest.csv`](outputs/backtest.csv) | Quarter-by-quarter M1 vs B0 vs B1, 2022Q1–2026Q2 |
| [`outputs/backtest_by_era.csv`](outputs/backtest_by_era.csv) | Error summary split by era |
| [`outputs/traffic_diagnostics.png`](outputs/traffic_diagnostics.png) | Four diagnostic charts |
| [`outputs/run_log.txt`](outputs/run_log.txt) | Complete printed output of the run |
