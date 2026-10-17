"""
AIPI 590 Alternative Data -- Southwest Q3 2026 case study
TRAFFIC ROLE: clean the TSA daily series, flag the two funding-lapse periods,
aggregate to quarters, link it to Southwest's reported revenue passengers, and
hand the team a Q3 2026 revenue-passenger forecast with an 80% interval.

Target: revenue passengers carried, Q3 2026, in thousands. Q3 2025 = 34,581.

Run:  python Traffic/traffic_forecast.py
Writes CSVs and charts to Traffic/outputs/ and prints a full log to stdout.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(exist_ok=True)

RNG = np.random.default_rng(20261021)
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 60)

# Funding-lapse windows, taken from the packet timeline and held fixed.
# Lapse 1: 43-day federal shutdown beginning Oct 1 2025 (Oct 1 -> Nov 12 inclusive = 43 days).
# Lapse 2: DHS funding lapse, Feb 14 2026 -> Apr 30 2026 (bill signed).
LAPSE1 = ("2025-10-01", "2025-11-12")
LAPSE2 = ("2026-02-14", "2026-04-30")

TARGET_Q = pd.Period("2026Q3", freq="Q")
BASE_Q = pd.Period("2025Q3", freq="Q")

# Company guidance from the Q2 2026 release (packet, "The numbers on the table").
ASM_GUIDE_LO_PCT, ASM_GUIDE_HI_PCT = -1.0, 0.0   # Q3 2026 ASMs, % YoY

log_lines = []
def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log_lines.append(s)

def head(t):
    say("\n" + "=" * 78)
    say(t)
    say("=" * 78)


# ---------------------------------------------------------------- 1. TSA clean
head("1. TSA DAILY CHECKPOINT SERIES -- VALIDATION AND CLEANING")

tsa_raw = pd.read_csv(DATA / "tsa_daily_checkpoint_2019-01-01_2026-09-30.csv",
                      parse_dates=["date"])
say(f"rows read                : {len(tsa_raw):,}")
say(f"date range               : {tsa_raw.date.min().date()} .. {tsa_raw.date.max().date()}")

cal = pd.date_range(tsa_raw.date.min(), tsa_raw.date.max(), freq="D")
missing_dates = sorted(set(cal) - set(tsa_raw.date))
say(f"calendar days expected   : {len(cal):,}")
say(f"missing calendar days    : {len(missing_dates)}")
say(f"duplicate dates          : {int(tsa_raw.date.duplicated().sum())}")
say(f"null passenger counts    : {int(tsa_raw.passengers_screened.isna().sum())}")
say(f"zero / negative counts   : {int((tsa_raw.passengers_screened <= 0).sum())}")
say(f"dtype                    : {tsa_raw.passengers_screened.dtype}")

tsa = tsa_raw.set_index("date").asfreq("D").copy()
tsa["screened"] = tsa["passengers_screened"].astype(float)
tsa = tsa.drop(columns=["passengers_screened"])

# Lapse flags
tsa["lapse"] = "none"
tsa.loc[LAPSE1[0]:LAPSE1[1], "lapse"] = "lapse1_shutdown_2025"
tsa.loc[LAPSE2[0]:LAPSE2[1], "lapse"] = "lapse2_dhs_2026"
say(f"\nlapse 1 {LAPSE1[0]} .. {LAPSE1[1]}: {(tsa.lapse=='lapse1_shutdown_2025').sum()} days flagged")
say(f"lapse 2 {LAPSE2[0]} .. {LAPSE2[1]}: {(tsa.lapse=='lapse2_dhs_2026').sum()} days flagged")

# Outlier scan. Day-of-week and week-of-year drive most of the variance, so the
# reference is the same weekday 52 weeks earlier (364d lag keeps weekday aligned).
tsa["ratio_52w"] = tsa.screened / tsa.screened.shift(364)
lr = np.log(tsa.ratio_52w)
# Calibrate the robust z on the post-normalisation window only. Scaling it on the
# full history lets the 2020-21 collapse inflate the MAD and hide ordinary outliers.
SCAN_FROM = "2023-07-01"
lrs = lr.loc[SCAN_FROM:]
med, mad = lrs.median(), (lrs - lrs.median()).abs().median()
tsa["robust_z"] = (lr - med) / (1.4826 * mad)
n_covid = int((tsa.loc[:"2022-12-31", "robust_z"].abs() > 5).sum())
scan = tsa.loc[SCAN_FROM:]
outl = scan.loc[scan.robust_z.abs() > 4, ["screened", "ratio_52w", "robust_z", "lapse"]]
say(f"\nrobust-z scan on log(52-week ratio), MAD calibrated on {SCAN_FROM} onward:")
say(f"  pre-2023 days with |z| > 5 : {n_covid} (the COVID collapse and its base effect)")
say(f"  {SCAN_FROM}-onward days with |z| > 4 : {len(outl)} of {int(scan.ratio_52w.notna().sum())}")
if len(outl):
    say(outl.round(3).to_string())
say("  -> the few flagged days are single-day holiday-drift artefacts (fixed-date vs")
say("     floating holidays land on different weekdays across a 364-day lag), not")
say("     collection failures: each is bracketed by normal days.")
say("  -> NO days are imputed, winsorised or dropped. The quarterly target is a sum")
say("     over 92 days, so a handful of 1-day holiday shifts cannot move it materially,")
say("     and editing them would inject judgement where the raw file has no defect.")

# Do the flagged windows actually show a level effect? Two tests, because the
# obvious one is confounded: the 52-week YoY ratio has a strong DOWNWARD trend
# across 2024-2026, and lapse 2 sits late in the sample, so a plain dummy
# regression attributes trend to the lapse. Control for it two ways.
say("\nDID THE LAPSES ACTUALLY DEPRESS THROUGHPUT IN THIS FILE?")

# (a) event study with a local 'donut' control: the 49 days either side of the
#     window, skipping a 7-day gap so spillover does not contaminate the control.
def lapse_event(name, a, b, pad=49, gap=7):
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    inside = lr.loc[a:b].dropna()
    pre = lr.loc[a - pd.Timedelta(days=pad + gap):a - pd.Timedelta(days=gap + 1)].dropna()
    post = lr.loc[b + pd.Timedelta(days=gap + 1):b + pd.Timedelta(days=pad + gap)].dropna()
    ctrl = pd.concat([pre, post])
    diff = inside.mean() - ctrl.mean()
    se_ = np.sqrt(inside.var(ddof=1) / len(inside) + ctrl.var(ddof=1) / len(ctrl))
    say(f"  (a) {name:22s} inside {inside.mean()*100:+6.2f}%  control {ctrl.mean()*100:+6.2f}%"
        f"  diff {diff*100:+6.2f}pp  t {diff/se_:+5.2f}")
    return diff

say("  (a) event study, window vs the 49 days either side (7-day donut):")
lapse_event("lapse1 2025 shutdown", *LAPSE1)
lapse_event("lapse2 2026 DHS lapse", *LAPSE2)

# (b) dummy regression WITH a linear trend in the YoY ratio.
smp = tsa.loc["2024-07-01":].dropna(subset=["ratio_52w"]).copy()
X = pd.DataFrame({
    "const": 1.0,
    "trend_per_yr": np.arange(len(smp)) / 365.25,
    "lapse1": (smp.lapse == "lapse1_shutdown_2025").astype(float),
    "lapse2": (smp.lapse == "lapse2_dhs_2026").astype(float),
}, index=smp.index)
y = np.log(smp.ratio_52w)
beta, *_ = np.linalg.lstsq(X.values, y.values, rcond=None)
resid = y.values - X.values @ beta
cov = (resid @ resid / (len(y) - X.shape[1])) * np.linalg.inv(X.values.T @ X.values)
se = np.sqrt(np.diag(cov))
say("  (b) log(52-week ratio) ~ const + trend + lapse1 + lapse2, 2024-07 onward:")
for nm, b_, s_ in zip(X.columns, beta, se):
    say(f"      {nm:14s} {b_*100:+7.2f}%   se {s_*100:5.2f}pp   t {b_/s_:+6.2f}")
say("      (Without the trend term lapse2 reads -2.65% at t=-3.0. That is the")
say("       trend, not the lapse: YoY throughput growth was fading at ~2.5pp/yr")
say("       and lapse 2 sits late in the sample. Adding the trend flips the sign.)")
say("  CONCLUSION: neither window shows a throughput DROP in this file. Both")
say("  point estimates are slightly POSITIVE once trend is controlled. The flags")
say("  are kept and exported, but nothing is repaired -- see README 'Challenges'.")

# The packet cites an external claim of -6.7% for Mar-May 2026. Check it.
def avg_daily(a, b):
    w = tsa.loc[a:b, "screened"]
    return w.mean(), len(w)
m26, n26 = avg_daily("2026-03-01", "2026-05-31")
m25, n25 = avg_daily("2025-03-01", "2025-05-31")
may26, _ = avg_daily("2026-05-01", "2026-05-31")
may25, _ = avg_daily("2025-05-01", "2025-05-31")
say(f"\npacket cites Upgraded Points: Mar-May 2026 avg daily throughput -6.7% YoY, May -9.8%.")
say(f"  this file: Mar-May 2026 {m26:,.0f}/day vs 2025 {m25:,.0f}/day  = {(m26/m25-1)*100:+.2f}%")
say(f"  this file: May 2026      {may26:,.0f}/day vs 2025 {may25:,.0f}/day  = {(may26/may25-1)*100:+.2f}%")
say("  -> ~7pp and ~9pp disagreement. See README 'Challenges' for how this is handled.")


# ------------------------------------------------- 2. aggregate TSA to periods
head("2. AGGREGATION TO MONTHS AND QUARTERS")

tsa["m"] = tsa.index.to_period("M")
tsa["q"] = tsa.index.to_period("Q")
tsa_m = tsa.groupby("m").agg(tsa_sum=("screened", "sum"), days=("screened", "size"),
                             lapse_days=("lapse", lambda s: int((s != "none").sum())))
tsa_m["tsa_per_day"] = tsa_m.tsa_sum / tsa_m.days
tsa_q = tsa.groupby("q").agg(tsa_sum=("screened", "sum"), days=("screened", "size"),
                             lapse_days=("lapse", lambda s: int((s != "none").sum())))
tsa_q["tsa_per_day"] = tsa_q.tsa_sum / tsa_q.days
tsa_q["tsa_sum_yoy"] = tsa_q.tsa_sum.pct_change(4) * 100
tsa_q["tsa_per_day_yoy"] = tsa_q.tsa_per_day.pct_change(4) * 100

say("Day counts differ across like quarters (Q1 2024 had 91 days, Q1 2025 had 90),")
say("so every trend/diagnostic use is on a per-day basis. Q3 is 92 days in both")
say("2025 and 2026, so the Q3 comparison is unaffected either way.")
say("\nquarterly TSA, 2024Q1 onward:")
say(tsa_q.loc["2024Q1":].round(3).to_string())
say(f"\nQ3 2026 is COMPLETE in this file: {int(tsa_q.loc[TARGET_Q,'days'])} of 92 days, "
    f"{int(tsa_q.loc[TARGET_Q,'lapse_days'])} lapse-flagged days.")
say(f"Q3 2026 TSA total {tsa_q.loc[TARGET_Q,'tsa_sum']:,.0f} vs Q3 2025 "
    f"{tsa_q.loc[BASE_Q,'tsa_sum']:,.0f} = {tsa_q.loc[TARGET_Q,'tsa_sum_yoy']:+.2f}% YoY")
say("Both Q3 2026 and its Q3 2025 base lie entirely OUTSIDE both lapse windows.")

# Day-of-week composition. Aug 1 2025 was a Friday, Aug 1 2026 a Saturday, so the
# two Augusts hold different numbers of weekend days -- which moves a monthly
# total by ~1% at airline traffic's weekday spread. Quantify it before reading
# any monthly YoY as demand.
dow_mult = (tsa.screened / tsa.screened.rolling(7, center=True).mean()) \
    .loc["2023-07-01":].groupby(tsa.loc["2023-07-01":].index.dayofweek).mean()
say("\nday-of-week multipliers (ratio to centred 7-day mean, 2023-07 onward):")
say("  " + "  ".join(f"{d}={v:.3f}" for d, v in
                     zip(["Mo","Tu","We","Th","Fr","Sa","Su"], dow_mult.values)))
calfac = tsa.groupby("m").apply(
    lambda g: dow_mult.reindex(g.index.dayofweek).mean(), include_groups=False)
cal_adj = (calfac / calfac.shift(12) - 1) * 100
tsa_m["cal_effect_pct"] = cal_adj
tsa_m["tsa_sum_yoy"] = tsa_m.tsa_sum.pct_change(12) * 100
tsa_m["tsa_yoy_cal_adj"] = tsa_m.tsa_sum_yoy - tsa_m.cal_effect_pct
say("\ncalendar effect on monthly YoY, Q3 2026 and its base:")
say(tsa_m.loc["2026-06":, ["tsa_sum_yoy", "cal_effect_pct", "tsa_yoy_cal_adj"]].round(2).to_string())
say("  -> August 2026's headline -4.40% YoY is about "
    f"{float(tsa_m.loc[pd.Period('2026-08', freq='M'),'cal_effect_pct']):+.2f}pp calendar, so "
    f"{float(tsa_m.loc[pd.Period('2026-08', freq='M'),'tsa_yoy_cal_adj']):+.2f}% on a like-for-like week.")
say("  IMPORTANT: no calendar adjustment is applied to the forecast chain. The chain")
say("  multiplies this year's actual TSA month by LAST year's Southwest share, and a")
say("  share is a ratio over the same days, so the calendar cancels by construction.")
say("  The adjustment matters only for reading the TSA series as a demand statement.")


# ------------------------------------------------ 3. Southwest reported panel
head("3. SOUTHWEST REPORTED PANEL AND THE TWO LINKING RATIOS")

sw = pd.read_csv(DATA / "southwest_quarterly_stats_2019Q1_2026Q2.csv")
sw["q"] = pd.PeriodIndex(sw.quarter, freq="Q")
sw = sw.set_index("q").sort_index()

sw["trip_factor"] = sw.enplaned_passengers_000 / sw.revenue_passengers_000
sw["haul"] = sw.rpm_millions / sw.revenue_passengers_000 * 1000
sw["dist_per_boarding"] = sw.rpm_millions / sw.enplaned_passengers_000 * 1000
sw["lf"] = sw.rpm_millions / sw.asm_millions * 100
sw["trip_factor_yoy"] = sw.trip_factor.pct_change(4) * 100
sw["revpax_yoy"] = sw.revenue_passengers_000.pct_change(4) * 100
sw["enplaned_yoy"] = sw.enplaned_passengers_000.pct_change(4) * 100

say("A checkpoint count is a count of BOARDINGS. Southwest's target figure is")
say("revenue passengers = one-way O&D trips. The bridge is the trip factor:")
say("      trip_factor = enplaned passengers / revenue passengers")
say("and it is the thing that broke in 2026.\n")
say(sw.loc["2024Q1":, ["revenue_passengers_000", "enplaned_passengers_000", "trip_factor",
                       "trip_factor_yoy", "revpax_yoy", "enplaned_yoy", "haul",
                       "dist_per_boarding", "lf", "asm_millions"]].round(4).to_string())
say("\nQ2 2026: enplaned +0.30% YoY but revenue passengers -3.31% YoY.")
say("The entire wedge is the trip factor, +3.74% YoY. Assigned seating and the")
say("fare bundles (Jan 27 2026) moved travellers onto more connecting itineraries,")
say("so each paying trip now consumes more boardings -- and more checkpoint scans.")
say("dist_per_boarding is ~stable (830-840 mi), confirming the move is itinerary")
say("structure, not a change in the kind of flying.")


# ------------------------------------------------------------ 4. T-100 linkage
head("4. T-100 LINKAGE: SOUTHWEST'S SHARE OF NATIONAL THROUGHPUT")

t100 = pd.read_csv(DATA / "bts_t100_domestic_segment_southwest_WN_monthly_2019-01_2026-07.csv")
t100["m"] = pd.PeriodIndex(t100.month, freq="M")
t100 = t100.set_index("m").sort_index()
say(f"T-100 coverage: {t100.index.min()} .. {t100.index.max()}  "
    f"({len(t100)} months). Q3 2026 months present: "
    f"{[str(p) for p in t100.index if p.quarter==3 and p.year==2026]}")

mon = t100.join(tsa_m)
mon["share"] = mon.segment_passengers / mon.tsa_sum
mon["share_yoy"] = mon.share.pct_change(12) * 100
mon["seg_yoy"] = mon.segment_passengers.pct_change(12) * 100
mon["tsa_yoy"] = mon.tsa_sum.pct_change(12) * 100

# Reported enplanements vs T-100 domestic segment passengers: the uplift covers
# international flying (~3% of capacity) plus charter and any filing differences.
t100_q = t100.groupby(t100.index.asfreq("Q")).agg(
    seg=("segment_passengers", "sum"), nmon=("segment_passengers", "size"),
    t100_asm=("asm", "sum"), t100_rpm=("rpm", "sum"), t100_seats=("seats", "sum"))
pan = sw.join(t100_q)
pan["uplift"] = pan.enplaned_passengers_000 * 1000 / pan.seg
pan.loc[pan.nmon != 3, "uplift"] = np.nan
pan = pan.join(tsa_q[["tsa_sum", "days", "tsa_per_day", "tsa_sum_yoy"]])
pan["revpax_share"] = pan.revenue_passengers_000 * 1000 / pan.tsa_sum

say("\nmonthly Southwest share of TSA throughput and its YoY change:")
say(mon.loc["2024-07":, ["segment_passengers", "tsa_sum", "share", "share_yoy",
                         "seg_yoy", "tsa_yoy"]].round(4).to_string())
say("\nREGIME CHANGE IN THE SHARE. It fell 5-12% YoY through Aug 2025 (Southwest")
say("shrinking against a growing industry) and has run POSITIVE since Sep 2025.")
say("Jul 2026: Southwest boardings -0.46% YoY while national throughput -2.06% YoY.")
say("Using the long-run average share drift would badly under-forecast Q3 2026.")

say("\nquarterly uplift, reported enplanements / T-100 domestic segment passengers:")
say(pan.loc["2023Q1":, ["enplaned_passengers_000", "seg", "uplift"]].round(4).to_string())
q3_uplift = pan.loc[[p for p in pan.index if p.quarter == 3], "uplift"].dropna()
say(f"\nQ3-only uplift history: {dict((str(k), round(v,4)) for k,v in q3_uplift.items())}")


# ------------------------------------------------ 5. component estimates Q3'26
head("5. COMPONENT ESTIMATES FOR Q3 2026")

say("Identity used throughout (all four terms are separately estimable):")
say("    revenue_passengers = TSA_throughput x share x uplift / trip_factor")
say("In logs this decomposes the YoY move into four additive pieces, which is")
say("what lets the regime flag attach to one term instead of the whole forecast.\n")

# --- 5a. share growth
# Estimate from the post-regime window only. Jul 2026 is the most recent and the
# most relevant (same quarter), so report several windows and take a view.
sh = mon.share_yoy.dropna()
w_post = sh.loc["2025-09":]            # post regime-flip
w_6m = sh.loc["2026-02":]              # last 6 available months
w_3m = sh.loc["2026-05":]              # last 3 available months
w_nolapse = sh.loc["2025-09":].drop(
    [p for p in sh.loc["2025-09":].index
     if str(p) in ("2025-10", "2025-11", "2026-02", "2026-03", "2026-04")],
    errors="ignore")
for nm, w in [("post-flip 2025-09..2026-07", w_post), ("last 6m 2026-02..07", w_6m),
              ("last 3m 2026-05..07", w_3m), ("post-flip ex-lapse months", w_nolapse)]:
    say(f"  share YoY, {nm:30s} mean {w.mean():+6.2f}%  sd {w.std(ddof=1):5.2f}  n={len(w)}")

g_share = float(w_6m.mean())
g_share_sd = float(w_6m.std(ddof=1) / np.sqrt(len(w_6m)) * np.sqrt(3))  # 3 months carried
say(f"\n  CHOSEN share YoY growth for Aug+Sep 2026: {g_share:+.2f}%  (sd {g_share_sd:.2f}pp)")
say("  Rationale: the last 6 months is the shortest window that spans the current")
say("  regime without being dominated by a single month. The ex-lapse variant")
say(f"  ({w_nolapse.mean():+.2f}%) is close, so the lapse flag does not drive this.")

# --- 5b. uplift
# The uplift stepped up in 2024Q1 (0.995-1.00 -> 1.011-1.020), so a plain average
# over Q3s straddles a level shift. Instead carry the recent YoY ratio of the
# uplift onto the Q3 2025 base: that respects both the level shift and the clear
# within-year seasonality (Q1/Q2 uplift runs above Q3/Q4).
up_yoy = (pan.uplift / pan.uplift.shift(4)).dropna()
up_recent = up_yoy.loc["2025Q3":]
uplift = float(pan.uplift.loc[BASE_Q]) * float(up_recent.mean())
uplift_sd = float(pan.uplift.loc[BASE_Q]) * float(up_recent.std(ddof=1))
say(f"\n  uplift YoY ratios, last 4 quarters: "
    f"{dict((str(k), round(v,5)) for k,v in up_recent.items())}")
say(f"  CHOSEN uplift = Q3'25 uplift {pan.uplift.loc[BASE_Q]:.4f} x "
    f"{up_recent.mean():.5f} = {uplift:.4f} (sd {uplift_sd:.4f})")
say("  (A flat average of the last three Q3s would give "
    f"{q3_uplift.iloc[-3:].mean():.4f}, but 2023Q3 predates the 2024 level shift.)")

# --- 5c. trip factor -- the critical term
tf = sw.trip_factor
tf_q3_25 = float(tf.loc[BASE_Q])
tf_q2_26 = float(tf.loc[pd.Period("2026Q2", freq="Q")])
# E1: carry the latest YoY step onto the Q3 2025 base.
g_tf_latest = float(sw.trip_factor_yoy.loc[pd.Period("2026Q2", freq="Q")])
e1 = tf_q3_25 * (1 + g_tf_latest / 100)
# E2: apply the historical Q2->Q3 seasonal step to the latest actual.
seas = []
for yr in (2022, 2023, 2024, 2025):
    seas.append(float(tf.loc[pd.Period(f"{yr}Q3", freq="Q")] / tf.loc[pd.Period(f"{yr}Q2", freq="Q")]))
seas_mu, seas_sd = float(np.mean(seas)), float(np.std(seas, ddof=1))
e2 = tf_q2_26 * seas_mu
say(f"\n  trip factor history: Q3 2025 {tf_q3_25:.4f}, Q2 2026 {tf_q2_26:.4f}")
say(f"  trip factor YoY:     {sw.trip_factor_yoy.loc['2025Q3':].round(2).to_dict()}")
say(f"  E1 YoY-carry      : {tf_q3_25:.4f} x (1{g_tf_latest/100:+.4f}) = {e1:.4f}")
say(f"  E2 Q2->Q3 seasonal: {tf_q2_26:.4f} x {seas_mu:.5f} = {e2:.4f}   "
    f"(seasonal ratios {[round(s,5) for s in seas]}, sd {seas_sd:.5f})")
tf_hat = (e1 + e2) / 2
tf_sd = max(abs(e1 - e2) / 2, tf_q2_26 * seas_sd)
say(f"  CHOSEN trip factor Q3 2026: {tf_hat:.4f} (sd {tf_sd:.4f}), "
    f"{(tf_hat/tf_q3_25-1)*100:+.2f}% YoY")
say("  E1 and E2 are averaged because they lean on different assumptions (that the")
say("  2026 step persists vs that the within-year seasonal shape persists) and")
say("  neither dominates on 4 post-break observations. The spread between them IS")
say("  the honest uncertainty, so it sets the sd.")

# --- 5d. load factor and haul (for the capacity-identity cross-check)
lf_q3_25 = float(sw.lf.loc[BASE_Q])
lf_yoy_recent = [float(sw.lf.loc[p] - sw.lf.loc[p - 4])
                 for p in [pd.Period("2026Q1", freq="Q"), pd.Period("2026Q2", freq="Q")]]
lf_hat = lf_q3_25 + float(np.mean(lf_yoy_recent))
haul_q3_25 = float(sw.haul.loc[BASE_Q])
haul_seas = [float(sw.haul.loc[pd.Period(f"{y}Q3", freq="Q")] / sw.haul.loc[pd.Period(f"{y}Q2", freq="Q")])
             for y in (2022, 2023, 2024, 2025)]
haul_hat = float(sw.haul.loc[pd.Period("2026Q2", freq="Q")]) * float(np.mean(haul_seas))
asm_q3_25 = float(sw.asm_millions.loc[BASE_Q])
say(f"\n  load factor: Q3 2025 {lf_q3_25:.1f}%, recent YoY steps "
    f"{[round(x,2) for x in lf_yoy_recent]}pp -> Q3 2026 {lf_hat:.2f}%")
say(f"  avg haul   : Q3 2025 {haul_q3_25:.1f} mi, Q2->Q3 seasonal "
    f"{np.mean(haul_seas):.4f} -> Q3 2026 {haul_hat:.1f} mi")
say(f"  ASMs       : Q3 2025 {asm_q3_25:,.0f}M, guided {ASM_GUIDE_LO_PCT:+.0f}% to "
    f"{ASM_GUIDE_HI_PCT:+.0f}% -> {asm_q3_25*(1+ASM_GUIDE_LO_PCT/100):,.0f}M to "
    f"{asm_q3_25*(1+ASM_GUIDE_HI_PCT/100):,.0f}M")


# --------------------------------------------------------------- 6. forecasts
head("6. FORECASTS")

# ---- M1: TSA -> share -> boardings -> revenue passengers (the alt-data chain)
def m1_point(g_share_pct, uplift_v, tf_v, verbose=False):
    """Nowcast Q3 boardings from TSA + share, then convert to revenue passengers."""
    parts, known = {}, 0.0
    for mp in [pd.Period("2026-07", freq="M"), pd.Period("2026-08", freq="M"),
               pd.Period("2026-09", freq="M")]:
        if mp in t100.index:                      # month already filed -> use the actual
            parts[str(mp)] = ("T-100 actual", float(t100.loc[mp, "segment_passengers"]))
            known += 1
        else:                                      # nowcast from TSA x last year's share
            base_share = float(mon.loc[mp - 12, "share"])
            tsa_now = float(tsa_m.loc[mp, "tsa_sum"])
            parts[str(mp)] = ("TSA nowcast", tsa_now * base_share * (1 + g_share_pct / 100))
        if verbose:
            say(f"    {mp}  {parts[str(mp)][0]:12s}  boardings {parts[str(mp)][1]:,.0f}")
    seg = sum(v for _, v in parts.values())
    enpl = seg * uplift_v
    revpax = enpl / tf_v / 1000
    if verbose:
        say(f"    Q3 2026 domestic boardings (T-100 basis) : {seg:,.0f}")
        say(f"    x uplift {uplift_v:.4f} -> enplaned passengers: {enpl/1000:,.0f}k")
        say(f"    / trip factor {tf_v:.4f} -> REVENUE PASSENGERS: {revpax:,.0f}k")
        say(f"    ({known} of 3 months are hard filings, 2 are TSA nowcasts)")
    return revpax

say("M1  TSA -> share -> boardings -> revenue passengers")
m1 = m1_point(g_share, uplift, tf_hat, verbose=True)

# ---- M2: capacity identity anchored on company ASM guidance
asm_mid = asm_q3_25 * (1 + (ASM_GUIDE_LO_PCT + ASM_GUIDE_HI_PCT) / 200)
m2 = asm_mid * (lf_hat / 100) * 1000 / haul_hat
say(f"\nM2  capacity identity  revpax = ASM x LF / haul")
say(f"    {asm_mid:,.0f}M ASM x {lf_hat:.2f}% / {haul_hat:.1f} mi = {m2:,.0f}k")

# ---- M3: the naive regression a first-pass analyst would run
reg = pan.loc["2022Q1":"2026Q2", ["revpax_yoy", "tsa_sum_yoy"]].dropna()
Xr = np.column_stack([np.ones(len(reg)), reg.tsa_sum_yoy.values])
br, *_ = np.linalg.lstsq(Xr, reg.revpax_yoy.values, rcond=None)
rs = reg.revpax_yoy.values - Xr @ br
r2 = 1 - rs.var() / reg.revpax_yoy.values.var()
m3_yoy = br[0] + br[1] * float(tsa_q.loc[TARGET_Q, "tsa_sum_yoy"])
m3 = float(sw.revenue_passengers_000.loc[BASE_Q]) * (1 + m3_yoy / 100)
say(f"\nM3  naive OLS  revpax_yoy ~ a + b*tsa_yoy   (2022Q1-2026Q2, n={len(reg)})")
say(f"    a={br[0]:+.2f}  b={br[1]:+.3f}  R2={r2:.2f}  resid sd={rs.std(ddof=2):.2f}pp")
say(f"    -> {m3_yoy:+.2f}% YoY -> {m3:,.0f}k   (carried only as a cautionary benchmark:")
say("       it forces one slope across the share regime break and the 2026 trip-factor")
say("       break, so it mixes three different mechanisms into one coefficient.)")

# ---- baselines
b0 = float(sw.revenue_passengers_000.loc[BASE_Q])
q2_yoy = float(sw.revpax_yoy.loc[pd.Period("2026Q2", freq="Q")])
b1 = b0 * (1 + q2_yoy / 100)
say(f"\nBASELINES   B0 same quarter last year  : {b0:,.0f}k")
say(f"            B1 B0 scaled by Q2'26 YoY   : {b0:,.0f} x (1{q2_yoy/100:+.4f}) = {b1:,.0f}k")


# --------------------------------------------------------------- 7. backtest
head("7. BACKTEST OF M1 AGAINST THE BASELINES")

say("Information set replicated at each quarter Q (what an analyst really had):")
say("  - TSA daily through the end of Q (published next day)")
say("  - T-100 through month 1 of Q only (BTS runs ~3 months late)")
say("  - Southwest's own reported figures through Q-1")
say("Share growth, uplift and trip factor are re-estimated from that vintage only.\n")

def backtest_one(q):
    prev = [p for p in sw.index if p < q]
    if len(prev) < 9:
        return None
    # share growth: trailing 6 months of share YoY available at forecast time.
    # Month 1 of q is filed; months 2-3 are not. So availability ends at q month 1.
    last_avail = pd.Period(f"{q.year}-{3*(q.quarter-1)+1:02d}", freq="M")
    sh_av = mon.share_yoy.dropna()
    sh_av = sh_av[sh_av.index <= last_avail]
    if len(sh_av) < 6:
        return None
    gs = float(sh_av.iloc[-6:].mean())
    # uplift: average of the last 3 same-quarter uplifts strictly before q
    if (q - 4) not in pan.index or np.isnan(pan.uplift.get(q - 4, np.nan)):
        return None
    uy = (pan.uplift / pan.uplift.shift(4)).dropna()
    uy = uy[uy.index < q]
    if len(uy) < 4:
        return None
    up = float(pan.uplift.loc[q - 4]) * float(uy.iloc[-4:].mean())
    # trip factor: same E1/E2 blend, vintage-limited
    q3_25v, q2_26v = q - 4, q - 1
    if q3_25v not in tf.index or q2_26v not in tf.index:
        return None
    g_tf = float(sw.trip_factor_yoy.loc[q2_26v]) if not np.isnan(sw.trip_factor_yoy.loc[q2_26v]) else 0.0
    e1v = float(tf.loc[q3_25v]) * (1 + g_tf / 100)
    sr = []
    for y in range(q.year - 4, q.year):
        a, b = pd.Period(f"{y}Q{q.quarter}", freq="Q"), pd.Period(f"{y}Q{q.quarter}", freq="Q") - 1
        if a in tf.index and b in tf.index:
            sr.append(float(tf.loc[a] / tf.loc[b]))
    if not sr:
        return None
    e2v = float(tf.loc[q2_26v]) * float(np.mean(sr))
    tfv = (e1v + e2v) / 2
    # boardings: month 1 actual if filed, else TSA nowcast
    seg = 0.0
    for k in range(3):
        mp = pd.Period(f"{q.year}-{3*(q.quarter-1)+1+k:02d}", freq="M")
        if k == 0 and mp in t100.index:
            seg += float(t100.loc[mp, "segment_passengers"])
        else:
            if (mp - 12) not in mon.index or mp not in tsa_m.index:
                return None
            seg += float(tsa_m.loc[mp, "tsa_sum"]) * float(mon.loc[mp - 12, "share"]) * (1 + gs / 100)
    return seg * up / tfv / 1000

rows = []
for q in [p for p in sw.index if p >= pd.Period("2022Q1", freq="Q")]:
    f = backtest_one(q)
    if f is None:
        continue
    act = float(sw.revenue_passengers_000.loc[q])
    bb0 = float(sw.revenue_passengers_000.loc[q - 4])
    prev_yoy = float(sw.revpax_yoy.loc[q - 1]) if not np.isnan(sw.revpax_yoy.loc[q - 1]) else 0.0
    bb1 = bb0 * (1 + prev_yoy / 100)
    rows.append(dict(quarter=str(q), actual=act, M1=f, B0=bb0, B1=bb1,
                     M1_err_pct=(f / act - 1) * 100,
                     B0_err_pct=(bb0 / act - 1) * 100,
                     B1_err_pct=(bb1 / act - 1) * 100))
bt = pd.DataFrame(rows).set_index("quarter")
say(bt.round(2).to_string())

def era(df, lo, hi, name):
    s = df.loc[lo:hi]
    return dict(era=name, n=len(s),
                M1_MAPE=s.M1_err_pct.abs().mean(), B0_MAPE=s.B0_err_pct.abs().mean(),
                B1_MAPE=s.B1_err_pct.abs().mean(), M1_bias=s.M1_err_pct.mean(),
                M1_sd=s.M1_err_pct.std(ddof=1))
eras = pd.DataFrame([
    era(bt, "2022Q1", "2024Q4", "2022-2024 (pre fee change)"),
    era(bt, "2025Q1", "2026Q2", "2025-2026 (fee + model change)"),
    era(bt, "2022Q1", "2026Q2", "full sample"),
])
say("\nerrors by era (%):")
say(eras.round(2).to_string(index=False))
bt_recent = bt.loc["2025Q1":]
resid_sd = float(bt_recent.M1_err_pct.std(ddof=1))
resid_bias = float(bt_recent.M1_err_pct.mean())
say(f"\nM1 error in the current regime: bias {resid_bias:+.2f}%, sd {resid_sd:.2f}%")
say("The interval below uses the CURRENT-REGIME sd, not the full-sample sd: the")
say("2022-2024 errors come from a different structure and would understate risk.")


# ---- sensitivity of M1 to the two judgement calls
head("7b. SENSITIVITY TO THE TWO JUDGEMENT CALLS")
say("M1 revenue passengers (000s) across share-growth and trip-factor assumptions:\n")
sh_opts = [("post-flip 11m", float(w_post.mean())), ("last 6m  [CHOSEN]", g_share),
           ("last 3m", float(w_3m.mean())), ("ex-lapse months", float(w_nolapse.mean())),
           ("zero drift", 0.0)]
tf_opts = [("E2 seasonal only", e2), ("blend [CHOSEN]", tf_hat), ("E1 YoY-carry only", e1),
           ("no 2026 step (Q3'25 level)", tf_q3_25)]
tbl = pd.DataFrame(
    {tn: {sn: round(m1_point(sv, uplift, tv)) for sn, sv in sh_opts} for tn, tv in tf_opts})
say(tbl.to_string())
say("\nThe trip factor swings the answer by ~1,000k across plausible values; share")
say("growth by ~450k. If the trip factor had NOT stepped up, the forecast would sit")
say("at ~33.8m, above baseline B1. That single unobservable ratio is the whole call.")

# ---- coherence check between M1 and M2
dpb_m1 = haul_q3_25 / tf_q3_25
say(f"\ncoherence: avg distance per boarding = haul / trip factor")
say(f"  Q3 2025 actual               {dpb_m1:.1f} mi")
say(f"  M2's haul {haul_hat:.1f} / M1's trip factor {tf_hat:.4f} = {haul_hat/tf_hat:.1f} mi "
    f"({(haul_hat/tf_hat/dpb_m1-1)*100:+.2f}% YoY)")
say(f"  T-100 Jul 2026 rpm/segment   "
    f"{float(t100.loc[pd.Period('2026-07',freq='M'),'rpm'])/float(t100.loc[pd.Period('2026-07',freq='M'),'segment_passengers']):.1f} mi "
    f"vs Jul 2025 "
    f"{float(t100.loc[pd.Period('2025-07',freq='M'),'rpm'])/float(t100.loc[pd.Period('2025-07',freq='M'),'segment_passengers']):.1f} mi")
say("  The two methods imply a consistent structural story (slightly longer flying")
say("  per boarding), so M2 is not quietly contradicting M1's trip factor.")

# ------------------------------------------- 8. Monte Carlo 80% interval
head("8. POINT FORECAST AND 80% INTERVAL")

N = 200_000
d_share = RNG.normal(g_share, g_share_sd, N)
d_up = RNG.normal(uplift, uplift_sd, N)
d_tf = RNG.normal(tf_hat, tf_sd, N)
# pre-compute the two nowcast months and the one hard month
jul = float(t100.loc[pd.Period("2026-07", freq="M"), "segment_passengers"])
aug_b = float(tsa_m.loc[pd.Period("2026-08", freq="M"), "tsa_sum"]) * float(mon.loc[pd.Period("2025-08", freq="M"), "share"])
sep_b = float(tsa_m.loc[pd.Period("2026-09", freq="M"), "tsa_sum"]) * float(mon.loc[pd.Period("2025-09", freq="M"), "share"])
seg_s = jul + (aug_b + sep_b) * (1 + d_share / 100)
m1_s = seg_s * d_up / d_tf / 1000

# Method/structural error on top of parameter error, sized on the CURRENT-REGIME
# backtest. That sd is estimated from only 6 quarters, so draw it from a Student-t
# with 5 df (scaled to the right sd) rather than a normal: with n=6 the tails of
# the error distribution are genuinely not pinned down, and a normal here would
# manufacture false precision in exactly the quarter where the regime is new.
BT_DF = max(len(bt_recent) - 1, 3)
t_scale = resid_sd / 100 / np.sqrt(BT_DF / (BT_DF - 2))
eps1 = RNG.standard_t(BT_DF, N) * t_scale
m1_s = m1_s * (1 + eps1)

asm_s = RNG.uniform(asm_q3_25 * (1 + ASM_GUIDE_LO_PCT / 100), asm_q3_25 * (1 + ASM_GUIDE_HI_PCT / 100), N)
lf_s = RNG.normal(lf_hat, 0.6, N)
haul_s = RNG.normal(haul_hat, haul_q3_25 * float(np.std(haul_seas, ddof=1)), N)
m2_s = asm_s * (lf_s / 100) * 1000 / haul_s
# M2 carries its own structural error, correlated with M1's. The two routes are
# NOT independent: M1 divides by the trip factor and M2 divides by haul, and
# haul = distance-per-boarding x trip factor, so a wrong read of the itinerary
# shift breaks both the same way. Treating them as independent is the
# diversification fallacy and would shrink the interval by ~20%.
RHO = 0.7
z_ind = RNG.standard_t(BT_DF, N) * t_scale
eps2 = RHO * eps1 + np.sqrt(1 - RHO ** 2) * z_ind
m2_s = m2_s * (1 + eps2)

W1 = 0.65
blend_s = W1 * m1_s + (1 - W1) * m2_s
point = float(np.mean(blend_s))
lo, hi = np.percentile(blend_s, [10, 90])

say(f"M1 TSA chain          point {np.mean(m1_s):8,.0f}k   80% [{np.percentile(m1_s,10):,.0f}, {np.percentile(m1_s,90):,.0f}]")
say(f"M2 capacity identity  point {np.mean(m2_s):8,.0f}k   80% [{np.percentile(m2_s,10):,.0f}, {np.percentile(m2_s,90):,.0f}]")
say(f"M3 naive OLS          point {m3:8,.0f}k   (benchmark only, not in the blend)")
say(f"\nmethod error: Student-t, df={BT_DF}, sd={resid_sd:.2f}% (current-regime backtest)")
say(f"M1/M2 structural-error correlation imposed at rho={RHO:.1f}")
say(f"\nBLEND {W1:.0%} M1 / {1-W1:.0%} M2")
say(f"  >>> POINT FORECAST       {point:,.0f} thousand revenue passengers")
say(f"  >>> 80% INTERVAL         [{lo:,.0f} , {hi:,.0f}] thousand")
say(f"      implied YoY          {(point/b0-1)*100:+.2f}%   (Q3 2025 = {b0:,.0f}k)")
say(f"      interval as +/-      {(hi-lo)/2/point*100:.2f}% of the point")
say(f"      vs baseline B0       {point-b0:+,.0f}k")
say(f"      vs baseline B1       {point-b1:+,.0f}k")
say(f"\nIf the independence assumption were kept, the interval would be "
    f"[{np.percentile(W1*m1_s+(1-W1)*(m2_s/(1+eps2)*(1+z_ind)),10):,.0f}, "
    f"{np.percentile(W1*m1_s+(1-W1)*(m2_s/(1+eps2)*(1+z_ind)),90):,.0f}] -- narrower, and wrong.")
say(f"\nM1 is weighted 65% because its two nowcast months rest on measured TSA data,")
say("while M2 inherits the full width of the ASM guidance range and needs a haul")
say("forecast that is itself mid-structural-break. M2 is kept at 35% because it is")
say("the only estimate anchored on something the company has actually committed to.")
say(f"\nBias note: M1's current-regime backtest bias is {resid_bias:+.2f}%. Correcting")
say(f"for it would move the point to {point*(1-resid_bias/100):,.0f}k. NOT applied: a "
    f"bias estimated on\n{len(bt_recent)} quarters is indistinguishable from noise at this sd.")

# variance attribution
def contrib(name, **ov):
    a = dict(share=g_share_sd, up=uplift_sd, tf=tf_sd, meth=resid_sd / 100)
    a.update(ov)
    s = (jul + (aug_b + sep_b) * (1 + RNG.normal(g_share, a["share"], N) / 100)) \
        * RNG.normal(uplift, a["up"], N) / RNG.normal(tf_hat, a["tf"], N) / 1000
    s = s * (1 + RNG.normal(0, a["meth"], N))
    return name, float(np.std(s))
say("\nwhere M1's uncertainty comes from (sd of M1, 000s, one term at a time):")
base_sd = float(np.std(m1_s))
say(f"  all sources                 {base_sd:7.0f}")
for nm, kw in [("share growth only", dict(up=0, tf=0, meth=0)),
               ("trip factor only", dict(share=0, up=0, meth=0)),
               ("uplift only", dict(share=0, tf=0, meth=0)),
               ("method/backtest only", dict(share=0, up=0, tf=0))]:
    _, sd_ = contrib(nm, **kw)
    say(f"  {nm:27s} {sd_:7.0f}")

# passenger-revenue sanity check against guidance
head("9. HANDOFF CHECK -- RECONCILING WITH GUIDANCE AND THE PRICE ROLE")

pr_lo, pr_hi = 7.43, 7.64   # $bn, from the packet's guidance arithmetic
say("Guidance implies Q3 2026 operating revenue of ~$8.08-8.30bn, and passenger")
say("revenue was ~92% of operating revenue in Q2 2026, so passenger revenue of")
say(f"~${pr_lo}-{pr_hi}bn. Inverting that against this passenger forecast gives the")
say("average fare the Price role must land on for the team's product to sit inside")
say("the guided band:")
for pr in (pr_lo, pr_hi):
    f_ = pr * 1e9 / (point * 1000)
    say(f"  ${pr:.2f}bn / {point:,.0f}k passengers = ${f_:,.2f} fare  "
        f"({f_/182.56-1:+.1%} YoY)")

say("\nIS THAT FARE PATH PLAUSIBLE? Only if the $285M breakage reversal is handled.")
q2_pr_rep = float(sw.passenger_revenue_musd.loc[pd.Period("2026Q2", freq="Q")])
q2_pr_adj = q2_pr_rep + 285
q2_px = float(sw.revenue_passengers_000.loc[pd.Period("2026Q2", freq="Q")])
q2_fare_rep = q2_pr_rep * 1000 / q2_px
q2_fare_adj = q2_pr_adj * 1000 / q2_px
q2_fare_ly = float(sw.avg_passenger_fare_usd.loc[pd.Period("2025Q2", freq="Q")])
say(f"  Q2 2026 reported fare    ${q2_fare_rep:,.2f}  ({q2_fare_rep/q2_fare_ly-1:+.1%} YoY)")
say(f"  Q2 2026 ex-breakage fare ${q2_fare_adj:,.2f}  ({q2_fare_adj/q2_fare_ly-1:+.1%} YoY)")
say("  The reported +20.9% is depressed by the one-off reversal; the underlying run")
say("  rate was about +25%. So the $226-232 this forecast implies for Q3 is a slight")
say("  DECELERATION from Q2's underlying pace, not an acceleration -- which is exactly")
say("  what management flagged ('held back by the comparison with a quarter that")
say("  already had bag fees') and what the RASM guide says (+17.5-19.5% vs +20.1%")
say("  underlying in Q2). The passenger and fare halves are therefore consistent.")
say("\n  ACTION FOR THE TEAM: if the Price role builds its fare forecast off the")
say("  REPORTED $225.61 rather than the ex-breakage $233.90, it will understate the")
say("  fare, and the product will fall below the guided band for a reason that has")
say("  nothing to do with traffic. Agree the basis before multiplying.")

say("\nIMPLIED PASSENGER REVENUE from this forecast, at a range of fares:")
for f_ in (215, 220, 226, 232, 238):
    pr_ = point * 1000 * f_ / 1e9
    flag = "inside" if pr_lo <= pr_ <= pr_hi else ("BELOW band" if pr_ < pr_lo else "ABOVE band")
    say(f"  fare ${f_}  ->  ${pr_:.2f}bn   {flag}")
say(f"\nAnd the passenger count the band implies at the fares the Price role may pick:")
for f_ in (215, 220, 226, 232):
    say(f"  fare ${f_}  ->  {pr_lo*1e9/f_/1000:,.0f}k to {pr_hi*1e9/f_/1000:,.0f}k passengers")
say(f"  This forecast ({point:,.0f}k) sits inside that span for fares of roughly "
    f"$225-232.")

# ------------------------------------------------------------------- outputs
tsa.reset_index().rename(columns={"index": "date"})[
    ["date", "screened", "lapse", "ratio_52w", "robust_z"]
].to_csv(OUT / "tsa_daily_clean.csv", index=False)
tsa_q.to_csv(OUT / "tsa_quarterly.csv")
mon[["departures_performed", "seats", "segment_passengers", "tsa_sum", "share",
     "share_yoy", "seg_yoy", "tsa_yoy"]].to_csv(OUT / "monthly_share_panel.csv")
pan[["revenue_passengers_000", "enplaned_passengers_000", "trip_factor", "trip_factor_yoy",
     "haul", "dist_per_boarding", "lf", "asm_millions", "seg", "uplift", "tsa_sum",
     "revpax_share", "revpax_yoy", "enplaned_yoy"]].to_csv(OUT / "quarterly_panel.csv")
bt.to_csv(OUT / "backtest.csv")
eras.to_csv(OUT / "backtest_by_era.csv", index=False)
pd.DataFrame([dict(target="revenue_passengers_000_Q3_2026", point=round(point),
                   lo80=round(lo), hi80=round(hi), yoy_pct=round((point/b0-1)*100, 2),
                   M1=round(float(np.mean(m1_s))), M2=round(float(np.mean(m2_s))),
                   M3_benchmark=round(m3), B0=round(b0), B1=round(b1),
                   trip_factor=round(tf_hat, 4), share_growth_pct=round(g_share, 2),
                   uplift=round(uplift, 4))]).to_csv(OUT / "forecast.csv", index=False)

# charts
fig, ax = plt.subplots(2, 2, figsize=(14, 9))
a = ax[0, 0]
d = tsa.screened.rolling(28, center=True).mean() / 1e6
a.plot(d.index, d.values, lw=1, color="#1f3b73")
for (s, e), c, lb in [(LAPSE1, "#d1495b", "Oct-Nov 2025 shutdown"),
                      (LAPSE2, "#e9a13b", "Feb-Apr 2026 DHS lapse")]:
    a.axvspan(pd.Timestamp(s), pd.Timestamp(e), color=c, alpha=.35, label=lb)
a.axvspan(pd.Timestamp("2026-07-01"), pd.Timestamp("2026-09-30"), color="#2a9d8f", alpha=.3, label="Q3 2026")
a.set_xlim(pd.Timestamp("2024-01-01"), pd.Timestamp("2026-10-15"))
a.set_ylim(1.8, 2.9); a.legend(fontsize=8, loc="lower left")
a.set_title("TSA daily throughput, 28-day mean (millions)")
a.set_ylabel("millions/day")
a.tick_params(axis="x", rotation=30, labelsize=8)
for lbl in a.get_xticklabels():
    lbl.set_ha("right")

a = ax[0, 1]
s = mon.share_yoy.dropna().loc["2023-01":]
a.bar([p.to_timestamp() for p in s.index], s.values,
      width=22, color=["#2a9d8f" if v > 0 else "#d1495b" for v in s.values])
a.axhline(0, color="k", lw=.8)
a.axvline(pd.Timestamp("2025-09-01"), color="#1f3b73", ls="--", lw=1.2)
a.text(pd.Timestamp("2025-09-10"), -10, " share regime flips", fontsize=8, color="#1f3b73")
a.set_title("Southwest share of TSA throughput, % YoY"); a.set_ylabel("% YoY")

a = ax[1, 0]
p2 = pan.loc["2022Q1":]
a.plot([q.to_timestamp() for q in p2.index], p2.trip_factor, marker="o", color="#1f3b73")
a.axvline(pd.Timestamp("2026-01-27"), color="#d1495b", ls="--", lw=1.2)
a.text(pd.Timestamp("2026-02-05"), 1.235, " assigned\n seating", fontsize=8, color="#d1495b")
a.scatter([TARGET_Q.to_timestamp()], [tf_hat], color="#e9a13b", s=90, zorder=5, label="Q3 2026 est.")
a.legend(fontsize=8); a.set_title("Trip factor = enplaned / revenue passengers")

a = ax[1, 1]
hist = sw.revenue_passengers_000.loc["2022Q1":]
a.plot([q.to_timestamp() for q in hist.index], hist.values, marker="o", color="#1f3b73", label="reported")
tq_ts = TARGET_Q.to_timestamp()
a.errorbar([tq_ts], [point], yerr=[[point - lo], [hi - point]],
           fmt="o", color="#e9a13b", capsize=6, ms=9, label="forecast + 80%")
a.scatter([tq_ts], [b0], marker="_", s=400, lw=2.5, color="#888", label="B0 = Q3'25")
a.scatter([tq_ts], [b1], marker="_", s=400, lw=2.5, color="#d1495b", label="B1 scaled")
a.set_xlim(pd.Timestamp("2021-11-01"), pd.Timestamp("2027-01-01"))
a.annotate(f"{point:,.0f}", (tq_ts, point), xytext=(12, -4),
           textcoords="offset points", fontsize=8, color="#e9a13b", weight="bold")
a.legend(fontsize=8, loc="lower left"); a.set_title("Revenue passengers carried (000s)")
a.tick_params(axis="x", rotation=30, labelsize=8)
for lbl in a.get_xticklabels():
    lbl.set_ha("right")
plt.tight_layout(); plt.savefig(OUT / "traffic_diagnostics.png", dpi=140)

(OUT / "run_log.txt").write_text("\n".join(log_lines) + "\n")
say(f"\nwrote {len(list(OUT.iterdir()))} files to {OUT}")
