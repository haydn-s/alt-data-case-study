# Alternative Data Case Study — Southwest's Q3 2026 print

**AIPI 590: Alternative Data.** Forecast two figures Southwest Airlines (NYSE: LUV) will report
for Q3 2026, using only free and public data, before the company reports after the close on
**October 21 2026**.

We are analysts at an alternative data vendor. A hedge fund client holds LUV into the print and
wants a read beforehand.

## The two targets

| # | Figure | Q3 2025 actual | Guidance given |
|---|---|---|---|
| 1 | Revenue passengers carried (000s) | 34,581 | none |
| 2 | Average passenger fare ($) | $182.56 | none |

Their product is the passenger revenue forecast, checked against the band implied by guidance
(~$7.43–7.64bn). Southwest guides RASM +17.5–19.5% and ASMs −1% to flat, but gives no guidance
on either target directly.

**Baselines to beat**
- **B0** — same quarter last year: 34,581 passengers, $182.56
- **B1** — last year scaled by the Q2 2026 YoY change: 33,436 passengers, $220.67

## Current status

| Role | Deliverable | Status |
|---|---|---|
| **Traffic** | Q3 passenger forecast + 80% interval | ✅ **32,912k, 80% CI 32,237–33,589 (−4.8% YoY)** |
| Price | Q3 fare forecast + 80% interval | ⬜ not started |
| Evaluation | Backtest table by period | ⬜ not started |
| Integration | Combined forecast, form, slides | ⬜ not started |

👉 **[`findings.md`](findings.md) is the shared findings document.** One section per role.
Read the Traffic section before building the fare forecast — there is a
[$285M breakage adjustment](findings.md#traffic) that changes the fare basis.

## Why this company is a useful test

Southwest's revenue and its passenger count now move in **opposite directions**. In Q2 2026 the
airline carried 3.3% *fewer* revenue passengers and reported 16.4% *more* operating revenue.
A pipeline that counts people gets the direction wrong unless it also explains price — and, as
the Traffic work shows, a pipeline that counts *boardings* does not even get the passenger count
right, because the boardings-per-trip ratio moved 3.7% in a year.

Three causes overlap in the same quarters: a business-model change (bag fees from May 2025,
assigned seating from Jan 2026), a fuel shock, and two federal funding lapses.

## Repository layout

```
.
├── Case Study Guidelines.pdf   instructor packet: timeline, numbers, roles, reading list
├── findings.md                 SHARED findings document — one section per role
├── data/                       instructor-provided data files (read-only)
├── Traffic/                    Traffic role (complete)
│   ├── README.md               method, cleaning decisions, backtest, PoV
│   ├── traffic_forecast.py     reproducible pipeline
│   └── outputs/                forecast, panels, backtest, charts, run log
├── Price/                      (to be added)
├── Evaluation/                 (to be added)
└── Integration/                (to be added)
```

## Data provided

| File | What it gives | Known problem |
|---|---|---|
| `tsa_daily_checkpoint_*.csv` | 2,830 days of national TSA checkpoint throughput | All airlines combined; two funding lapses said to distort it — [but see Traffic F3/F4](findings.md#traffic) |
| `southwest_quarterly_stats_*.csv` | 30 quarters of Southwest's reported figures, incl. both targets | Includes the 2020 collapse; several years come from prior-year columns of later releases |
| `bts_t100_domestic_segment_southwest_WN_monthly_*.csv` | 91 months of Southwest's own DOT filings | Domestic only (~97% of capacity); counts boardings, not revenue passengers; ~3 months late, so covers only July of Q3 |
| `bls_airline_fares_cpi_*.csv` | 105 months of the BLS airline fare index | All carriers; monthly; advance-purchase quotes; Oct 2025 blank |
| `eia_jet_fuel_gulf_coast_daily_*.csv` | 2,022 weekdays of Gulf Coast jet fuel spot | Wholesale price, ~30c below Southwest's reported cost; 87 holidays blank |
| `google_trends_southwest_airlines_US_*.csv` | Search interest, monthly from 2019 and weekly for 5 years | 0–100 index rescaled per file, so the two files are not comparable; resampled on each pull |

Any other free public source is permitted, provided it is disclosed and nothing published after
the form closes enters the model.

## Reproducing the Traffic analysis

```bash
python3 -m venv .venv && .venv/bin/pip install pandas numpy matplotlib statsmodels
.venv/bin/python Traffic/traffic_forecast.py
```

Prints the full analysis log and refreshes everything in `Traffic/outputs/`. The run is
deterministic (seeded Monte Carlo), so the committed outputs should reproduce exactly.

## Key dates

| Date | What |
|---|---|
| Oct 16 2026 | Packet and data released |
| **Oct 21 2026, 12:00 noon ET** | **Forecast form closes — one submission per team** |
| Oct 21 2026, after close | Southwest reports Q3 2026 |
| Oct 27 2026, 11:59 PM | Slides due (5 max) |
| Oct 28 2026, in class | Results reveal, readouts, debate, decision exercise |

The debate motion: *a signal built from free public data on Southwest is good enough to sell to a
client.* Factions are Ship, Kill and Flag — our Traffic position is **Flag**, with four stated
downgrade conditions ([findings.md, F10](findings.md#traffic)).
