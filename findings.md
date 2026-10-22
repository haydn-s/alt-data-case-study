# Findings — Southwest Q3 2026 case study

Shared working document. **One section per role.** Each role owns its own section and
records what it found, what it decided, and what the rest of the team needs to know.
Keep method detail in the role's own folder and keep this document to findings.

- Target quarter: **Q3 2026 (Jul–Sep)**, reported after the close on **Oct 21 2026**
- Forecast form closes **12:00 noon Eastern, Oct 21 2026**
- Rule: free and public data only; nothing published after the form closes

## Team forecast

**As submitted on the form** (points from the roles; intervals on Evaluation's harmonised rule; see
[Integration](#integration)):

| Figure | Point | 80% interval | Owner | Status |
|---|---|---|---|---|
| Revenue passengers carried (000s) | **32,912** | **31,912 – 33,912** | Traffic | ✅ done |
| Average passenger fare ($) | **$229.34** | **$215.87 – $242.81** | Price | ✅ done |
| **Implied passenger revenue ($M)** | **7,548** | **7,136 – 7,955** | Integration | ✅ inside the guided band |

Baselines to beat: **B0** = Q3 2025 (34,581 passengers / $182.56 fare); **B1** = Q3 2025 scaled
by the Q2 2026 YoY change (33,436 passengers / $220.67 fare; **$228.78** rebuilt ex-breakage —
see [Evaluation E2](#e2-on-a-fair-basis-the-fare-forecast-is-the-naive-forecast)).

> ⚠️ **Cross-role dependency — read before multiplying.** Q2 2026's reported fare of $225.61 is
> depressed by a one-off $285M breakage reversal. Ex-breakage it was **$233.90** (+25.3% YoY, not
> +20.9%). If Price forecasts off the reported figure, the team's product falls below the guided
> band for a reason that has nothing to do with traffic. See [Traffic §8](Traffic/README.md).

---

## Traffic

**Deliverable: Q3 2026 revenue passengers = 32,912 thousand, 80% interval 32,237 – 33,589, −4.8% YoY.**
Below both baselines (−1,669 vs B0, −524 vs B1).
Full method and reproducible code: [`Traffic/README.md`](Traffic/README.md).

### F1. A checkpoint count measures boardings, not revenue passengers — and the gap is widening fast

This is the finding the whole case turns on. **Q2 2026: enplaned passengers +0.30% YoY, revenue
passengers −3.31% YoY.** The entire wedge is the trip factor (enplaned ÷ revenue passengers):

| | 2025Q2 | 2025Q3 | 2025Q4 | 2026Q1 | 2026Q2 |
|---|---|---|---|---|---|
| Trip factor | 1.2500 | 1.2668 | 1.2636 | 1.2777 | 1.2967 |
| YoY | −0.80% | +0.63% | +1.25% | **+3.18%** | **+3.74%** |

Assigned seating and the fare bundles (Jan 27 2026) moved travellers onto more connecting
itineraries, so each paying trip now consumes more boardings — and more checkpoint scans.
Distance per boarding held flat at 830–840 miles throughout, which confirms the change is
**itinerary structure, not a different kind of flying**.

A TSA count is therefore closest to **enplaned** passengers and is drifting away from **revenue**
passengers by roughly 3.5 points a year. Any pipeline mapping throughput straight onto the
reported passenger count gets the magnitude wrong, and in Q2 2026 would have called the direction
of *revenue* wrong while the passenger count fell.

### F2. The trip factor is unobservable in public alternative data — this is the signal's structural limit

T-100 reports boardings. TSA reports boardings. **No free public source reports how many one-way
O&D trips those boardings represent.** The conversion has to be extrapolated from Southwest's own
quarterly releases — which is precisely the term that broke in 2026, and which we extrapolate from
only four post-break quarters.

The alternative data is the *reliable* part of this pipeline; the accounting bridge sitting on top
of it is the *fragile* part. That is the opposite of how a signal like this normally gets sold, and
it is the core of our debate position.

### F3. Neither funding lapse depresses throughput in the file we were given

The packet's "known problem" note says both lapse periods distort the count. Tested two ways on
the national series — they do not.

| Test | Lapse 1 (Oct 1 – Nov 12 2025, 43d) | Lapse 2 (Feb 14 – Apr 30 2026, 76d) |
|---|---|---|
| Event study vs 49 days either side (7-day donut) | **+1.08pp** (t = +1.11) | **+0.25pp** (t = +0.25) |
| Dummy regression **with** linear trend | **+1.99%** (t = +1.78) | **+1.71%** (t = +1.91) |

**The trap:** the same dummy regression *without* a trend term reports lapse 2 at **−2.65%,
t = −3.0**. That reads as a textbook shutdown effect and is not one — YoY throughput growth was
fading at ~2.5pp/yr and lapse 2 sits late in the sample. Adding the trend flips the sign. Worth
about 2.7 points of forecast error to anyone who skips the control.

We flagged both windows and **repaired nothing**. Imputing a drop we cannot measure would inject
the exact bias the flag is meant to warn about.

### F4. The packet's cited throughput collapse does not appear in the data

The timeline cites Upgraded Points: average daily throughput **−6.7% for Mar–May 2026 and −9.8%
in May**. The file we were given says **+0.34%** and **−0.74%** — a 7-to-9 point disagreement.

We went with the data and documented the conflict rather than bending the file toward the article.
The Upgraded Points piece is airport-level, and the packet itself notes one airport's 76.9% drop
was *partly a data-collection artefact*. If the series we hold is the corrected national backfill,
it is the right input and the article is stale.

**Why it does not change the answer:** Q3 2026 and its Q3 2025 base contain **zero lapse-flagged
days**. The lapses touch our estimates only through the Q4'25–Q2'26 quarters used to fit share
drift. Re-estimating with every lapse-affected month dropped moves the forecast by **9 thousand
passengers (0.03%)**. The regime flag is live; it is simply not load-bearing for this quarter.

### F5. Southwest's share of national throughput flipped regime in Sep 2025

The share fell 5–12% YoY every month through Aug 2025, then turned positive and has stayed there.

| | Sep'25 | Oct'25 | Jan'26 | Apr'26 | May'26 | Jun'26 | **Jul'26** |
|---|---|---|---|---|---|---|---|
| Share YoY | +0.8% | +2.8% | −1.2% | −1.0% | +1.5% | +2.6% | **+1.6%** |

**July 2026 is the single cleanest datapoint in the packet: Southwest boardings −0.46% YoY while
national throughput fell 2.06%.** Southwest is outperforming the industry — consistent with a fuel
shock in which it guided capacity down only 1% while competitors cut harder. Using the pre-2025
average share drift (≈ −3pp/quarter) would have under-forecast by roughly one million passengers.

### F6. The best-fitting model is the wrong model

`revpax_yoy ~ a + b·tsa_yoy` fits beautifully — **R² = 0.98**, b = 1.06 — and forecasts 32,097,
close to our answer. It is still wrong. It forces a single slope across the share regime break
*and* the 2026 trip-factor break, so one coefficient absorbs three distinct mechanisms. It lands
near the right place this quarter by coincidence and cannot explain why it moved.

**High R² on a structurally-broken series is a warning, not a validation.** We carry it as a
labelled benchmark, outside the blend.

### F7. Method and backtest

One identity, so each term can be estimated and challenged separately:

```
revenue passengers = TSA throughput  ×  Southwest share  ×  uplift  ÷  trip factor
                     (measured)         (nowcast)          (small)    (judgement call)
```

| | Estimate | Weight | Anchored on |
|---|---|---|---|
| **M1** TSA → share → boardings chain | 32,772 | 65% | Measured throughput; Jul is a hard T-100 filing, Aug/Sep nowcast |
| **M2** capacity identity `ASM × LF ÷ haul` | 33,171 | 35% | Company's guided ASMs (−1% to flat) |
| M3 naive OLS | 32,097 | — | Benchmark only (see F6) |

Backtest replays the real information set each quarter (TSA through quarter-end, T-100 through
**month 1 only**, Southwest's own figures through Q−1), re-estimating every parameter from that vintage:

| Era | n | **M1 MAPE** | B0 MAPE | B1 MAPE |
|---|---|---|---|---|
| 2022–2024 (pre fee change) | 12 | **3.81%** | 11.90% | 10.29% |
| **2025–2026 (fee + model change)** | 6 | **1.50%** | 4.07% | 2.64% |
| Full sample | 18 | **3.04%** | 9.29% | 7.74% |

M1 beats both baselines in both eras, and by most where it counts.

**Two deliberate choices on the interval.** It is sized on the current-regime sd (1.67%), not the
full-sample sd (4.16%) — the older errors come from a different structure and would be wide for the
wrong reason. And M1/M2 errors are correlated at **ρ = 0.7**, because both route through the same
itinerary shift (`haul = distance-per-boarding × trip factor`); treating them as independent would
have produced [32,338, 33,490], about 20% too narrow. Method error is Student-t with 5 df, not
normal, since it rests on only six current-regime quarters.

### F8. Where the uncertainty really sits

| Share growth ↓ / Trip factor → | E2 seasonal | **blend (chosen)** | E1 YoY-carry | no 2026 step |
|---|---|---|---|---|
| post-flip 11m (+0.32%) | 32,801 | 32,694 | 32,587 | 33,805 |
| **last 6m (+0.69%) — chosen** | 32,878 | **32,771** | 32,664 | 33,884 |
| last 3m (+1.92%) | 33,134 | 33,026 | 32,918 | 34,148 |
| zero drift | 32,735 | 32,627 | 32,521 | 33,736 |

**The trip factor swings the answer by ~1,000; share growth by ~450.** Had the trip factor not
stepped up, the forecast would be ~33,800 — above B1 and near B0. One unobservable ratio,
extrapolated from four post-break quarters, is the entire call.

### F9. Cleaning decisions

| Decision | Reason |
|---|---|
| **No TSA day imputed, winsorised or dropped** | The file is structurally clean: 2,830 rows for 2,830 calendar days, no missing dates, duplicates, nulls or non-positive counts. There is no defect to repair. |
| Outlier scan calibrated on 2023-07 onward | Scaling the MAD on full history lets the 2020–21 collapse inflate it and hide ordinary outliers. 24 of 1,188 recent days exceed \|z\|>4; each is a single day bracketed by normal days (holiday drift across a 364-day lag) and cannot move a 92-day sum. |
| Both lapse windows flagged, neither repaired | See F3. |
| Per-day normalisation for all trend work | Q1 2024 had 91 days, Q1 2025 had 90 — a 1.1% artefact in sum-to-sum YoY. Q3 is 92 days in both years. |
| **No calendar adjustment inside the forecast chain** | The chain multiplies *this* year's actual TSA month by *last* year's share; a share is a ratio over the same days, so day-of-week composition cancels. Computed anyway for *reading* the series (Aug 2026's −4.41% headline is −4.30% like-for-like). |
| Comparisons at 364-day lag, not 365 | 52 weeks keeps weekdays aligned; 365 days compares Tuesdays to Mondays. |

### F10. PoV for the debate — Team Flag

**Ship it, with a regime flag.** The signal beat both baselines in every backtest era and by 1.1
points of MAPE in the current one. But what makes it work is not the alternative data — it is the
bridge on top, and that bridge is the fragile part (F1, F2).

Conditions under which we would tell a client to stop trusting it:

1. **Trip factor moves more than ±1.5pp from trend in any reported quarter** → the bridge is unstable; downgrade to boardings-only and stop forecasting revenue passengers.
2. **Southwest's share of TSA goes negative YoY for two consecutive months** → the Sep 2025 regime flip has unwound; re-estimate, do not extrapolate.
3. **Another funding lapse, or any TSA collection change** → the national series stops being a demand measure. We have now seen that a lapse signature can be invisible in the data and still be real in the narrative, which is the worse failure mode.
4. **Southwest stops disclosing enplaned passengers** → the trip factor becomes unobservable entirely and the signal is dead, not degraded.

The honest sales line is narrow: *this nowcasts Southwest boardings from public data to about 1.5%,
and converts to revenue passengers using a ratio you must keep re-estimating from the company's own
releases.* Sold that way it clears the bar. Sold as "we count passengers from checkpoint data" it
does not — and Q2 2026 is the proof.

### Open questions for the team

- **The F4 conflict is our biggest unresolved item** and should lead the readout. Did any other role find corroboration for the −6.7% Mar–May figure in a different source?
- Price needs to settle the **$285M breakage basis** before the two forecasts are multiplied (see the warning at the top).
- Our passenger forecast requires a **$226–232** fare for the product to sit inside the guided band. If Price lands materially below that, one of the two halves needs revisiting — and the split tells you which, where the band alone cannot.

---

## Price

**Deliverable: Q3 2026 average passenger fare = $229.34, 80% interval $212.92 – $245.75, +25.6% YoY.**
Full method and code: [`Price/README.md`](Price/README.md).

*The Price work was merged without filling in this section. Integration summarised it here from
Price's README; the Price owner should check it.*

- **Basis: ex-breakage.** The Q2 2026 fare is recomputed with the $285M added back ($233.90), as
  Traffic flagged. Using the reported $225.61 would cost ~$10 on the forecast (P1 → $219.11).
- **Three methods on three different signals, all within 1.6% of each other:** P1 industry anchor
  (BLS CPI + last quarter's premium) $227.16; P2 seasonal step $229.02; P3 fuel pass-through $230.79.
  They are blended 0.24/0.33/0.43 on current-era inverse MSE, shrunk halfway to equal.
- **Southwest now moves 1-for-1 with the industry index.** The naive regression (M4) fits a slope of
  ~0.35 on 2022–25, then misses 2026Q1/Q2 by −7%/−9%. That fits the hedges ending in Q2 2025: the
  2026 fuel shock reached Southwest's fares the way it reached everyone's.
- **Attribution of the Q2 2026 rise (ex-breakage):** industry CPI explains almost all of it, and
  Southwest's own premium is +0.5 pt. That does not support management's claim that its own
  initiatives explain most of the gain. About 56% of the dollar increase matches higher fuel cost per
  passenger, and about a fifth of the % increase is longer trips (the itinerary shift Traffic found).
- **PoV:** sellable as attribution, less so as a point forecast; Evaluation's backtest agrees (E1, E2).

---

## Evaluation

**Deliverable: one backtest table by period, 2022Q1–2026Q2, covering both targets and the
passenger-revenue product against B0 and B1.** Full method and code:
[`Evaluation/README.md`](Evaluation/README.md).

Every method was **re-implemented from the roles' write-ups**, not copied. The re-implementation
matches Traffic's committed backtest exactly and Price's to $0.0005. Both backtests reproduce, and
both Q3 2026 forecasts reproduce.

### The table (MAPE %)

| Period | n | **Passengers: M1** | Traffic blend | B1 | **Fare: blend (OOS)** | P3 | B1 | **Product: team** | B1 |
|---|---|---|---|---|---|---|---|---|---|
| 2022–2024 (pre fee change) | 12 | **3.81** | 4.82 | 10.29 | **4.30** | 5.74 | 5.39 | **5.70** | 10.89 |
| ‣ 2022 only (COVID base) | 4 | 6.38 | 8.20 | 21.56 | 5.49 | 7.74 | 9.41 | 11.10 | 23.16 |
| ‣ 2023–2024 | 8 | **2.52** | 3.13 | 4.65 | 3.71 | 4.74 | **3.39** | **3.00** | 4.76 |
| **2025–2026 (fee + model change)** | 6 | **1.50** | **1.12** | 2.64 | **4.42** | 3.67 | 4.95 | **3.51** | 3.86 |

Fare scored against the ex-breakage Q2 2026 fare. "OOS" means the blend's weights use only errors
from earlier quarters; Price's own blend is in-sample, and the difference is 0.12 points.

### E1. Only the passenger half has a demonstrated edge over the naive forecast

| DM test vs B1, 2025–2026, n=6 | M1 | Traffic blend | Price OOS blend | **Product** |
|---|---|---|---|---|
| Quarters beating B1 | 5/6 | 5/6 | 3/6 | 4/6 |
| p-value (HLN-corrected) | 0.08 | **0.05** | 0.44 | **0.53** |

The TSA chain beats B1 in 16 of 18 quarters and in every period. The fare does not reliably beat B1:
in 2023–2024 B1 wins outright, and the "2022–2024" aggregate is flattered by 2022's COVID bases. So
the **revenue product, the client's number, has no statistically distinguishable edge over
"last year × last quarter's YoY"**.

### E2. On a fair basis, the fare forecast *is* the naive forecast

The packet's B1 fare ($220.67) is built on the reported Q2 fare, which carries the $285M one-off.
Ex-breakage, B1 = **$228.78**. The team's $229.34 is **0.24%** above it. Scoring against the packet's
B1 would credit the model with a 4% edge that comes entirely from the breakage adjustment.

### E3. The two 80% intervals are miscalibrated in opposite directions

| | Delivered | Covers, 14 post-COVID quarters | Why |
|---|---|---|---|
| Passengers | ±2.05% | **50%** | Sized on the current era's six quarters, which are M1's calmest window on record |
| Fare | ±7.16% | **93%** | "Student-t, 5 df" implemented with the sd as the t's scale, 29% wider than Traffic's convention |

**Recommended harmonised rule:** error sd over 2023Q1–2026Q2 (n=14), Student-t rescaled to that sd.
Passengers **31,912 – 33,912** (±3.0%); fare **$215.87 – $242.81** (±5.9%).

### E4. Passenger and fare errors are negatively correlated, so the product is tighter than the halves

ρ = **−0.38** over 2023Q1–2026Q2 and **−0.76** in the current era. The cause is mechanical. The fare
is revenue ÷ passengers, and the fare methods never see the count, so a passenger shortfall shows up
as a fare overshoot. Independence would put the product's sd at 5.3%; the realised sd is 4.0%.
**Integration should combine with ρ ≈ −0.4, not 0.** Traffic's own M1/M2 ρ = 0.7 is conservative:
the realised correlation is about zero since 2025.

### E5. Two flags on the Q3 2026 passenger point, both pointing down

- **The naive regression disagrees by 2.1%.** M3, refitted each quarter, scores within 0.24 points
  of M1 out of sample, and for Q3 it says **32,097k**. It has under-forecast three of the last four
  quarters (it cannot see the share flip), so we read it as biased low, but the gap is bigger than
  either method's typical error.
- **July's T-100 capacity is −1.84% YoY, below the guided −1% to flat.** At the July run-rate, M2
  gives 32,718k instead of 33,171k, and the blend moves to ~32,753k (−0.5%).

### E6. PoV — Flag, and specific about what is sold

Sell the **passenger nowcast**: it has the evidence behind it. Sell the **fare attribution**
(Price §8) as explanation. Do **not** sell the revenue point as beating a naive model, because six
quarters cannot show that it does. Downgrade triggers beyond Traffic's and Price's:
(1) M1 loses to B1 two quarters running; (2) the product misses its harmonised interval twice in
four quarters; (3) M1 and M3 diverge by more than 2%, which is **already raised for Q3**.

---

## Integration

**Deliverable: the form values (top of this document), the guidance check, and the five-slide deck
[`Presentation/southwest_q3_2026_presentation.pptx`](Presentation/southwest_q3_2026_presentation.pptx).**
Full method and code: [`Integration/README.md`](Integration/README.md).

### I1. The product is $7,548M and sits inside the guided band — on either share assumption

Guidance (RASM +17.5–19.5%, ASMs −1% to flat) implies operating revenue of $8,083–8,304M.

| Passenger share | Band | Team $7,548M |
|---|---|---|
| Packet's flat 92% (a Q2 number) | $7,437 – 7,640M | inside, 55% up |
| Seasonal 91.48% (Q3 runs lower) | $7,395 – 7,596M | inside, 76% up |

Implied RASM is **+19.3% YoY**, in the upper part of the +17.5–19.5% guide. **But only 25% of our own
product distribution falls inside the band**, so landing in it is a consistency check, not evidence.

### I2. One change from the roles' handoffs: the intervals

Points are the roles' own. The intervals follow Evaluation's harmonised rule (E3), because the
delivered bands covered 50% (passengers) and 93% (fare) of post-COVID quarters. The product interval
uses **ρ = −0.4** between the halves' errors (E4): **$7,136 – 7,955M** (±5.4%). Assuming
independence would give ±6.6%.

### I3. The split says yield, and both naive forecasts miss the band

The band admits flat passengers at $214–220 *or* −4.8% passengers at $225–231. Our split says the
second. The packet's B1 (33,436k × $220.67 = $7,378M) lands **below** the band. B1 rebuilt
ex-breakage (× $228.78 = $7,649M) lands **above** it. The split also says which half to suspect if
revenue misses: the fare, which has no demonstrated edge over naive.

### I4. The market agrees on the centre and is more confident

Kalshi's Q3 fare contracts on Oct 20, ~9:30pm ET: P(> $225) 77%, P(> $230) 50%, P(> $235) 19%. That
gives a median of **$229.71** against our $229.34, and an 80% band of $221.81–237.62 against our
$215.87–242.81. Benchmark only; it does not enter the forecast.

### I5. What is not submitted, and what happens after the print

- **Share price (optional): left blank.** With no demonstrated edge on revenue we have no informed view
  on the reaction. Random-walk would be the honest entry.
- **After the print:** `Integration/actuals.json` now carries the Q3 release; see I6.

### I6. Against the print: inside every band, a little low, and the bridge missed

| | Forecast | Actual | Error | In 80%? | B1 error |
|---|---|---|---|---|---|
| Revenue passengers | 32,912k | 33,467k | 1.7% low | ✓ | 0.1% low |
| Average fare | $229.34 | $231.69 | 1.0% low | ✓ | 4.8% low (1.3% ex-breakage) |
| Passenger revenue | $7,548M | $7,754M | 2.7% low | ✓ | 4.8% low |

- **The test of F1/F2 came out the Flag way.** The passenger miss splits into boardings 0.5% low (the
  TSA and T-100 chain) and trip factor 1.2% low (the bridge). The trip factor rose 2.2% YoY, not the
  3.4% we extrapolated: 1.2941 against our 1.3098, slightly below Q2's 1.2967.
- **Southwest beat its own guide.** Unit revenue rose 21.6% against +17.5–19.5%, so passenger revenue
  landed above the guided band that our forecast sat inside.
- **B1 beat our passenger count** this quarter; we beat it on fare. Kalshi's fare median ($229.71) was
  a touch closer than our $229.34.
- **Downgrade triggers.** The trip factor was 1.2% off forecast, inside Traffic's 1.5-point trigger.
  But Evaluation's trigger (1) **has fired**: B1 also beat our passenger method in Q2 2026 (0.6% high
  against the blend's 0.9% low, and M1's 1.6% low), so it has now lost to naive two quarters running.
  For the Q4 decision exercise: keep selling the boardings nowcast, and downgrade the revenue-passenger
  number to boardings-only until the trip factor is re-estimated.
