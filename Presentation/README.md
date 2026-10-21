# Presentation — the five-slide deck for the Oct 28 readout

**[`southwest_q3_2026_presentation.pptx`](southwest_q3_2026_presentation.pptx)** is the deck to upload.
Slides are due **Oct 27 2026, 11:59 PM**; the in-class readout is 6 minutes plus 2 of questions on Oct 28.

Until Southwest's Q3 2026 release is entered, every slot that needs a reported figure shows an
**amber [bracketed] placeholder**, and the regions waiting on the print are outlined in amber dashes.
There are 34 placeholders; the build prints how many are left.

Rebuild with `python Presentation/build_presentation.py`, after `python Integration/integrate.py`.
Every number on the slides is read from the pipeline's outputs, never typed in, and the build is
byte-reproducible.

---

## 1. One slide per required topic

The packet asks for at most five slides covering: forecast against actual, data and cleaning
decisions, model and baselines, backtest by period, and what we got wrong and why.

| # | Packet topic | Slide title | What it carries | Placeholders |
|---|---|---|---|---|
| 1 | **Forecast against actual** | Fewer passengers, a much higher fare | The three forecasts with 80% intervals, each actual with its error and whether it landed inside the band, and four benchmarks (B0, both B1s, Kalshi) with their own errors | 14 |
| 2 | **Data and cleaning decisions** | TSA counts boardings, not passengers | Q2: enplaned +0.3% vs revenue passengers −3.3% (the trip factor); one cleaning decision per source, and why | 0 |
| 3 | **Model and baselines** | The split says yield, not volume | Method in three steps; passengers × fare against the guidance band, where both naive baselines miss on opposite sides | 1 |
| 4 | **Backtest by period** | Passengers beat naive; fares don't yet | MAPE vs B1 for 2023–24 and 2025–26, with Diebold-Mariano p-values | 0 |
| 5 | **What we got wrong and why** | What we got wrong, and why | Scorecard; the four risks registered before the print and what each became; the passenger miss split into boardings vs trip factor; PoV with each downgrade trigger's status for the Q4 decision exercise | 19 |

Speaker notes carry the narration for each slide. At about 70 seconds per slide, the deck fits the
6-minute readout.

---

## 2. Placeholders, and where each value comes from

| Slide | Placeholder | Filled from |
|---|---|---|
| 1 | `[team name]` | `deck_inputs.json` → `team_name` |
| 1 | `[from the Q3 release]` ×3, `[—]` ×6 | `Integration/actuals.json`: the actual, error and in-80% for passengers, fare and passenger revenue |
| 1 | `[error vs actual]` ×4 | computed: each benchmark's error against the actual |
| 3 | `[the actual is plotted here after the print]` | computed: the actual is added to the chart as a triangle |
| 5 | `[—]` ×9 (scorecard) | computed from `actuals.json`: actual, error and in-80%, B1's error |
| 5 | `[after the print]` ×4 (risk ledger) | `actuals.json`: trip factor (`enplaned_passengers_000`), one-off (`special_items_musd`), capacity (`asm_millions`), and which forecast the actual was closer to |
| 5 | `[total]` `[TSA chain]` `[the bridge]` | computed: the passenger miss decomposed exactly in logs; needs `enplaned_passengers_000` |
| 5 | `[after the print]` ×2 (triggers) | computed: trip factor off forecast by >1.5 pt; TSA chain vs B1 this quarter |
| 5 | `[one sentence: which risk hit…]` | `deck_inputs.json` → `why`, **the team's own judgement** |

Two of the five downgrade triggers can't be read from the print. "Southwest's TSA share negative two
months" needs the Aug–Sep T-100 filings, which BTS publishes around mid-November; the slide says
"check T-100". "A funding lapse or TSA collection change" is shown as "none in Q3".

---

## 3. After the print — three steps

1. **Fill [`../Integration/actuals.json`](../Integration/actuals.json)** from the Q3 2026 earnings
   release:

   | Field | Release line |
   |---|---|
   | `revenue_passengers_000` | Revenue passengers carried (000s) |
   | `avg_passenger_fare_usd` | Average passenger fare |
   | `enplaned_passengers_000` | Enplaned passengers (000s). **The most important one**: it splits the passenger miss |
   | `passenger_revenue_musd` | Passenger revenue ($M) |
   | `operating_revenue_musd` | Total operating revenue ($M) |
   | `asm_millions` | Available seat miles (millions) |
   | `special_items_musd` | Any one-off in passenger revenue, like Q2's $285M breakage; `0` if none |

2. **Re-run** `python Integration/integrate.py`, then `python Presentation/build_presentation.py`.
   Slides 1, 3 and 5 fill in, and the build reports the placeholders left (should be 2: team name and why).
3. **Write the team name and the one-sentence "why"** into [`deck_inputs.json`](deck_inputs.json),
   re-run the build, and check it prints **0 placeholders left**.

The "why" is the one thing the pipeline cannot write. The ledger and the decomposition say *what*
happened. The sentence says which pre-registered risk explains the miss, and whether that confirms or
breaks the Flag position. If the boardings held and the trip factor missed, the bridge failed and the
alternative data did not, which is the Flag case in one line.

The form values never read `actuals.json`, so filling it in cannot move the submitted forecast.

---

## 4. Relationship to the Integration deck

[`../Integration/slides/southwest_q3_2026_readout.pptx`](../Integration/slides/southwest_q3_2026_readout.pptx)
is the deck committed with the forecast on Oct 20. It is **frozen** as the record of what we registered
before the print: its slide 5 lists the four risks. This deck keeps its slides 2–4 (slide 3 adds the actual
to the chart) and replaces slides 1 and 5 with the post-print layouts, so it is the one to upload. The generator moved here
from `Integration/build_deck.py`, and git history follows the move.

---

## 5. Files

| File | Contents |
|---|---|
| [`build_presentation.py`](build_presentation.py) | Generates the deck from the Integration and Evaluation outputs |
| [`deck_inputs.json`](deck_inputs.json) | Team name and the "why" sentence (null until filled) |
| [`southwest_q3_2026_presentation.pptx`](southwest_q3_2026_presentation.pptx) | The deck: five slides, native charts, speaker notes |
