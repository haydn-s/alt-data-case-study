# Presentation — the five-slide deck for the Oct 28 readout

**[`southwest_q3_2026_presentation.pptx`](southwest_q3_2026_presentation.pptx)** is the deck to upload.
Slides are due **Oct 27 2026, 11:59 PM**; the in-class readout is 6 minutes plus 2 of questions on Oct 28.

The deck is scored against Southwest's Q3 2026 release (Oct 21), entered in
[`../Integration/actuals.json`](../Integration/actuals.json). Each slide makes one point with one visual.
The detail is in the speaker notes, about 70 seconds per slide, so the deck fits the 6-minute readout.

Rebuild with `python Presentation/build_presentation.py`, after `python Integration/integrate.py`.
Every number on the slides is read from the pipeline's outputs, never typed in, and the build is
byte-reproducible.

---

## 1. One slide per required topic

The packet asks for at most five slides covering: forecast against actual, data and cleaning
decisions, model and baselines, backtest by period, and what we got wrong and why.

| # | Packet topic | Slide title | The visual |
|---|---|---|---|
| 1 | **Forecast against actual** | Inside every 80% band, a little low | Each figure's 80% band, our forecast and the actual on one bar; the error beside it |
| 2 | **Data and cleaning decisions** | TSA counts boardings, not passengers | Q2: boardings +0.3% vs paying trips −3.3%; one cleaning decision for each of three sources |
| 3 | **Model and baselines** | Naive won on passengers; we won on fare | The two-signal method as a flow; our error vs B1 and B0 against the print |
| 4 | **Backtest by period** | Passengers beat naive; fare barely does | MAPE vs B1 for 2022–2024 and 2025–2026, the packet's two periods |
| 5 | **What we got wrong and why** | The TSA data held; the trip factor didn't | The passenger miss split into boardings and trip factor; three reasons; the PoV |

## 2. What the print showed

| | Forecast | Actual | Error | In 80%? | B1 error |
|---|---|---|---|---|---|
| Revenue passengers | 32,912k | 33,467k | 1.7% low | ✓ | 0.1% low |
| Average fare | $229.34 | $231.69 | 1.0% low | ✓ | 4.8% low (1.3% ex-breakage) |
| Passenger revenue | $7.55bn | $7.75bn | 2.7% low | ✓ | 4.8% low |

- The passenger miss splits exactly, in logs, into **boardings 0.5% low** (the TSA and T-100 chain) and
  **trip factor 1.2% low** (the accounting bridge). The trip factor rose 2.2% year on year, not the 3.4%
  we extrapolated. The alternative data held and the bridge missed, which is the Flag case.
- Passenger revenue landed **above** the band implied by guidance: unit revenue rose 21.6% against a
  +17.5–19.5% guide.
- The naive B1 beat our passenger count, as it did in Q2, so the "loses to B1 two quarters
  running" downgrade trigger has fired. We beat B1 on fare.

## 3. Inputs the pipeline can't compute

[`deck_inputs.json`](deck_inputs.json) holds two lines that are the team's to write:

| Key | Where it shows | Now |
|---|---|---|
| `team_name` | Slide 1 subtitle, as "Team …" | "Thurro EV" |
| `why` | The PoV bar at the foot of slide 5 | A draft: "Team Flag. Keep selling the boardings nowcast; downgrade the passenger count until the trip factor settles." |

Edit either, then re-run the build.

## 4. Relationship to the Integration deck

[`../Integration/slides/southwest_q3_2026_readout.pptx`](../Integration/slides/southwest_q3_2026_readout.pptx)
is the deck committed with the forecast on Oct 20. It is **frozen** as the record of what we registered
before the print, including the four risks on its slide 5. This deck is the one to upload.

## 5. Files

| File | Contents |
|---|---|
| [`build_presentation.py`](build_presentation.py) | Generates the deck from the Integration and Evaluation outputs; stops if `actuals.json` is empty |
| [`deck_inputs.json`](deck_inputs.json) | Team name and the PoV line |
| [`southwest_q3_2026_presentation.pptx`](southwest_q3_2026_presentation.pptx) | The deck: five slides, native charts, speaker notes |
