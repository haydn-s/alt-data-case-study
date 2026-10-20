"""
Price role -- Q3 2026 average passenger fare forecast (Southwest Airlines)

Idea: forecast the fare three different ways, each anchored on a different
public signal, backtest all three on the same vintage-consistent footing,
then blend them by current-regime backtest error.

  P1  Industry anchor     fare YoY = BLS airfare CPI YoY + Southwest's premium last quarter
  P2  Seasonal step       Q3 = Q2 x exp(season effect + beta x CPI's Q2->Q3 step),
                          beta fitted by pooled regression (Southwest swings less than CPI)
  P3  Fuel pass-through   fare = last year + change in fuel cost per passenger
                                 + last quarter's non-fuel change
  M4  Naive regression    fare YoY ~ CPI YoY -- benchmark only, not blended

Plus: a guidance cross-check and a three-lens attribution of the fare jump
(industry vs own, fuel vs non-fuel, longer trips vs price per mile).

Run:  python Price/price_forecast.py
Needs: pandas, numpy, matplotlib  (same as Traffic)
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)

TARGET = pd.Period("2026Q3", "Q")
BREAKAGE_Q2_2026 = 285          # $M one-off breakage reversal in Q2 2026 (see Traffic §8)
TRAFFIC_PAX = 32912             # thousand, Traffic role's point forecast
GUIDE_OPREV = (8080, 8300)      # $M, Q3 operating revenue implied by RASM x ASM guidance
GUIDE_FUEL = (3.70, 3.75)       # $/gal, Q3 fuel guidance given Jul 22

log_lines = []
def log(text=""):
    print(text)
    log_lines.append(str(text))

def header(title):
    log("")
    log("=" * 78)
    log(title)
    log("=" * 78)


# =============================================================================
# 1. LOAD AND CLEAN
# =============================================================================
header("1. LOAD AND CLEAN")

# --- Southwest quarterly ------------------------------------------------------
sw = pd.read_csv(DATA / "southwest_quarterly_stats_2019Q1_2026Q2.csv")
sw.index = pd.PeriodIndex(sw["quarter"], freq="Q")

# Cleaning decision 1: add back the $285M one-off in Q2 2026 to get the underlying fare
# (same basis as Traffic).
sw["pax_rev"] = sw["passenger_revenue_musd"].astype(float)
sw["op_rev"] = sw["operating_revenue_musd"].astype(float)
sw.loc["2026Q2", "pax_rev"] += BREAKAGE_Q2_2026
sw.loc["2026Q2", "op_rev"] += BREAKAGE_Q2_2026

# Recompute fare from revenue / passengers instead of using the printed column,
# so the adjustment flows through every derived figure.
sw["fare"] = sw["pax_rev"] / sw["revenue_passengers_000"] * 1000          # $
sw["yield"] = sw["pax_rev"] / sw["rpm_millions"] * 100                    # cents per mile
sw["haul"] = sw["rpm_millions"] / sw["revenue_passengers_000"] * 1000     # miles per trip
sw["pax_share"] = sw["pax_rev"] / sw["op_rev"]                            # passenger rev / op rev
sw["gal_per_pax"] = sw["fuel_gallons_millions"] / sw["revenue_passengers_000"] * 1000
sw["fuel_px"] = sw["fuel_per_gallon_usd"]

log(f"Southwest rows: {len(sw)}  ({sw.index[0]} .. {sw.index[-1]})")
log(f"Q2 2026 fare reported ${sw.loc['2026Q2','avg_passenger_fare_usd']:.2f}  "
    f"-> ex-breakage ${sw.loc['2026Q2','fare']:.2f}")
log("Q4 2024 also carries a $116M breakage item; left as reported (direction not")
log("stated in the file). It touches only the 2025Q4 base of the backtest.")

# --- BLS airline fare CPI -----------------------------------------------------
cpi = pd.read_csv(DATA / "bls_airline_fares_cpi_CUUR0000SETG01_2018-01_2026-09.csv",
                  parse_dates=["observation_date"])
cpi = cpi.rename(columns={"CUUR0000SETG01": "cpi"}).set_index("observation_date")
n_missing = cpi["cpi"].isna().sum()
missing_months = list(cpi.index[cpi["cpi"].isna()].strftime("%Y-%m"))
# Cleaning decision 2: Oct 2025 is blank (federal shutdown) -> linear interpolation.
cpi["cpi"] = cpi["cpi"].interpolate()
log(f"CPI months: {len(cpi)}, missing: {n_missing} {missing_months} -> linear interpolation "
    f"({cpi.loc['2025-10-01','cpi']:.3f})")
# Cleaning decision 3: the index is not seasonally adjusted, so average months to
# quarters and only compare like seasons (YoY, or season-controlled steps).
cpi_q = cpi["cpi"].groupby(cpi.index.to_period("Q")).mean()

# Robustness: BLS prices advance-purchase quotes, which may lead travel by ~1 month.
# Build a version shifted back one month.
cpi_lag = cpi["cpi"].shift(1)
cpi_q_lag1 = cpi_lag.groupby(cpi.index.to_period("Q")).mean()

# --- EIA jet fuel spot ---------------------------------------------------------
fuel = pd.read_csv(DATA / "eia_jet_fuel_gulf_coast_daily_DJFUELUSGULF_2019-01-01_2026-09-30.csv",
                   parse_dates=["observation_date"])
fuel = fuel.rename(columns={"DJFUELUSGULF": "spot"}).set_index("observation_date")
n_blank = fuel["spot"].isna().sum()
# Cleaning decision 4: drop market-holiday blanks; a quarterly mean is unaffected.
fuel = fuel.dropna()
spot_q = fuel["spot"].groupby(fuel.index.to_period("Q")).mean()
log(f"Jet fuel weekdays: {len(fuel) + n_blank}, blank (holidays) dropped: {n_blank}")

# --- one quarterly panel --------------------------------------------------------
q = sw[["fare", "yield", "haul", "pax_share", "gal_per_pax", "fuel_px",
        "revenue_passengers_000", "pax_rev", "op_rev"]].copy()
q = q.reindex(pd.period_range("2019Q1", TARGET, freq="Q"))
q["cpi"] = cpi_q
q["cpi_lag1"] = cpi_q_lag1
q["spot"] = spot_q
q["premium_spot"] = q["fuel_px"] - q["spot"]      # what Southwest pays above spot

# log growth rates (a log difference ~ % change, and log pieces add up exactly)
def lg(col, lag):
    return np.log(q[col] / q[col].shift(lag))

for c in ["fare", "yield", "haul", "cpi"]:
    q[c + "_yoy"] = lg(c, 4)
    q[c + "_qoq"] = lg(c, 1)
q["gap"] = q["fare_yoy"] - q["cpi_yoy"]           # Southwest premium over industry

show = q.loc["2023Q1":, ["fare", "fare_yoy", "cpi_yoy", "gap", "haul_yoy", "yield_yoy",
                         "spot", "fuel_px"]].copy()
for c in ["fare_yoy", "cpi_yoy", "gap", "haul_yoy", "yield_yoy"]:
    show[c] = show[c] * 100
log("")
log("Quarterly panel (YoY in log %; fare ex-breakage):")
log(show.round(2).to_string())


# =============================================================================
# 2. THE THREE METHODS
# Each function forecasts quarter t using only what was public before t's print:
# Southwest figures through t-1, CPI and fuel spot through the end of t.
# =============================================================================

NORMAL_YEARS = [2019, 2022, 2023, 2024, 2025]     # skip 2020-21 (COVID)

def p1_industry_anchor(t, cpi_col="cpi"):
    """fare growth = CPI growth this quarter + last quarter's Southwest premium."""
    cpi_g = np.log(q.loc[t, cpi_col] / q.loc[t - 4, cpi_col])
    prem = (np.log(q.loc[t - 1, "fare"] / q.loc[t - 5, "fare"])
            - np.log(q.loc[t - 1, cpi_col] / q.loc[t - 5, cpi_col]))
    return q.loc[t - 4, "fare"] * np.exp(cpi_g + prem)

def p2_fit(t):
    """Pooled regression on quarter-to-quarter steps, normal years only, data before t:
         log(SW step) = season dummy + beta * log(CPI step)
       Southwest's seasonal swings are damped compared with the industry index
       (beta < 1), so the season effect depends on how much CPI moved."""
    d = q.loc[:t - 1].copy()
    d = d[d.index.year.isin(NORMAL_YEARS + [2026])]
    d = d.dropna(subset=["fare_qoq", "cpi_qoq"])
    d = d[d.index > pd.Period("2019Q1", "Q")]          # 2019Q1's step comes from 2018Q4 (no SW data)
    X = np.column_stack([(d.index.quarter == k).astype(float) for k in [1, 2, 3, 4]]
                        + [d["cpi_qoq"].values])
    coef = np.linalg.lstsq(X, d["fare_qoq"].values, rcond=None)[0]
    return coef          # [season Q1..Q4, beta]

def p2_sequential(t):
    """Q(t) = Q(t-1) x exp(season effect + beta x CPI step this year)."""
    coef = p2_fit(t)
    step = coef[t.quarter - 1] + coef[4] * q.loc[t, "cpi_qoq"]
    return q.loc[t - 1, "fare"] * np.exp(step)

def m4_naive_regression(t):
    """BENCHMARK ONLY: fare YoY ~ a + b * CPI YoY on 2022Q2..t-1.
       Fits a historical slope of ~0.35, which broke in 2026 (see log)."""
    d = q.loc[pd.Period("2022Q2", "Q"):t - 1].dropna(subset=["fare_yoy", "cpi_yoy"])
    X = np.column_stack([np.ones(len(d)), d["cpi_yoy"].values])
    a, b = np.linalg.lstsq(X, d["fare_yoy"].values, rcond=None)[0]
    return q.loc[t - 4, "fare"] * np.exp(a + b * q.loc[t, "cpi_yoy"])

def fuel_price_estimate(t):
    """Southwest's own fuel price for t = EIA spot in t + its recent premium over spot."""
    prem = q.loc[t - 4:t - 1, "premium_spot"].mean()
    return q.loc[t, "spot"] + prem

def p3_fuel_passthrough(t, fuel_px_t=None):
    """fare = last year + change in fuel cost per passenger + last quarter's non-fuel change."""
    if fuel_px_t is None:
        fuel_px_t = fuel_price_estimate(t)
    gpp = q.loc[t - 4, "gal_per_pax"] * q.loc[t - 1, "gal_per_pax"] / q.loc[t - 5, "gal_per_pax"]
    d_fuel = (fuel_px_t - q.loc[t - 4, "fuel_px"]) * gpp
    d_fuel_prev = (q.loc[t - 1, "fuel_px"] - q.loc[t - 5, "fuel_px"]) * q.loc[t - 1, "gal_per_pax"]
    nonfuel_prev = (q.loc[t - 1, "fare"] - q.loc[t - 5, "fare"]) - d_fuel_prev
    return q.loc[t - 4, "fare"] + d_fuel + nonfuel_prev

def b0(t):
    return q.loc[t - 4, "fare"]

def b1(t):
    return q.loc[t - 4, "fare"] * q.loc[t - 1, "fare"] / q.loc[t - 5, "fare"]

METHODS = {"P1": p1_industry_anchor, "P2": p2_sequential, "P3": p3_fuel_passthrough}
BASELINES = {"B0": b0, "B1": b1}
BENCHMARKS = {"M4": m4_naive_regression}   # shown, not blended


# =============================================================================
# 3. BACKTEST 2023Q1 - 2026Q2
# =============================================================================
header("3. BACKTEST 2023Q1 - 2026Q2 (vintage-consistent)")

rows = []
for t in pd.period_range("2023Q1", "2026Q2", freq="Q"):
    r = {"quarter": str(t), "actual": q.loc[t, "fare"]}
    for name, f in {**METHODS, **BENCHMARKS, **BASELINES}.items():
        r[name] = f(t)
    rows.append(r)
bt = pd.DataFrame(rows).set_index("quarter")
for name in list(METHODS) + list(BENCHMARKS) + list(BASELINES):
    bt[name + "_err%"] = (bt[name] / bt["actual"] - 1) * 100
bt["era"] = np.where(bt.index < "2025Q1", "2023-2024 (pre fee change)",
                     "2025-2026 (fee + model change)")

def era_table(df, cols):
    out = []
    for era, g in list(df.groupby("era")) + [("full sample", df)]:
        r = {"era": era, "n": len(g)}
        for c in cols:
            e = g[c + "_err%"]
            r[c + "_MAPE"] = e.abs().mean()
        out.append(r)
    return pd.DataFrame(out).set_index("era")

# --- blend weights from the current era only (inverse MSE, shrunk to equal) ---
cur = bt[bt["era"].str.startswith("2025")]
mse = {m: (cur[m + "_err%"] ** 2).mean() for m in METHODS}
inv = {m: 1 / mse[m] for m in METHODS}
w_raw = {m: inv[m] / sum(inv.values()) for m in METHODS}
SHRINK = 0.5        # only 6 quarters: shrink halfway to equal weights
w = {m: SHRINK * w_raw[m] + (1 - SHRINK) / len(METHODS) for m in METHODS}

# the blend has to be backtested with weights it could have known... with n=6
# that is not possible, so we report the blend as in-sample and say so.
bt["BLEND"] = sum(w[m] * bt[m] for m in METHODS)
bt["BLEND_err%"] = (bt["BLEND"] / bt["actual"] - 1) * 100

cols = ["P1", "P2", "P3", "BLEND", "M4", "B0", "B1"]
by_era = era_table(bt, cols)
log("Quarter-by-quarter error (forecast / actual - 1, %):")
log(bt[[c + "_err%" for c in cols]].round(1).to_string())
log("")
log("MAPE by era (%):")
log(by_era.round(2).to_string())
log("")
log("Blend weights (current-era inverse MSE, shrunk 50% toward equal):")
for m in METHODS:
    log(f"  {m}: raw {w_raw[m]:.2f} -> used {w[m]:.2f}   (current-era RMSE {np.sqrt(mse[m]):.2f}%)")
log("Note: the BLEND row uses weights fitted on 2025-26, so its current-era MAPE is")
log("in-sample. P1/P2/P3, M4 and the baselines are fully out-of-sample.")
log("")
log("M4 (fare YoY ~ CPI YoY) fits a slope of only ~0.35 on 2022-25 and then misses")
log("2026Q1 and 2026Q2 by -7% and -9%: Southwest now moves ~1:1 with the industry.")
log("Consistent with the timeline: Southwest ended its fuel hedges in Q2 2025, so the")
log("2026 fuel shock reached its fares the same way it reached everyone else's.")
log("This is why P1 carries the premium with an implied slope of 1, not 0.35.")


# =============================================================================
# 4. Q3 2026 FORECAST
# =============================================================================
header("4. Q3 2026 FORECAST")

t = TARGET
fc = {m: f(t) for m, f in METHODS.items()}
blend = sum(w[m] * fc[m] for m in METHODS)

log(f"Q3 2026 CPI YoY {q.loc[t,'cpi_yoy']*100:+.2f}% (log)   "
    f"Q2 premium carried by P1 {q.loc[t-1,'gap']*100:+.2f}pp")
log(f"Q3 fuel: EIA spot ${q.loc[t,'spot']:.3f} + recent premium -> "
    f"${fuel_price_estimate(t):.3f}/gal   (company guided ${GUIDE_FUEL[0]:.2f}-{GUIDE_FUEL[1]:.2f})")
log("")
for m in METHODS:
    log(f"  {m}: ${fc[m]:.2f}   ({(fc[m]/q.loc[t-4,'fare']-1)*100:+.1f}% YoY)")
log(f"  BLEND: ${blend:.2f}   ({(blend/q.loc[t-4,'fare']-1)*100:+.1f}% YoY)")
coef = p2_fit(t)
log(f"  P2 fit: Q3 season {coef[2]*100:+.2f}%, beta {coef[4]:.2f}  (beta<1: SW swings less than CPI)")
log(f"  M4 naive regression (benchmark, not blended): ${m4_naive_regression(t):.2f}")
log(f"  B0 ${b0(t):.2f}   B1 ${b1(t):.2f}  (B1 on ex-breakage basis; packet's B1 is $220.67)")

# --- sensitivity rows -----------------------------------------------------------
sens = {
    "P1 with CPI lagged 1 month": p1_industry_anchor(t, cpi_col="cpi_lag1"),
    "P3 at guided fuel $3.725": p3_fuel_passthrough(t, fuel_px_t=np.mean(GUIDE_FUEL)),
    "P1 on reported (not ex-breakage) Q2": None,
}
# P1 using the reported Q2 fare instead of ex-breakage (the trap Traffic warned about)
rep_q2 = sw.loc["2026Q2", "avg_passenger_fare_usd"]
prem_rep = np.log(rep_q2 / q.loc[t - 5, "fare"]) - np.log(q.loc[t - 1, "cpi"] / q.loc[t - 5, "cpi"])
sens["P1 on reported (not ex-breakage) Q2"] = q.loc[t - 4, "fare"] * np.exp(q.loc[t, "cpi_yoy"] + prem_rep)
log("")
log("Sensitivity:")
for k, v in sens.items():
    log(f"  {k:40s} ${v:.2f}")

# --- 80% interval ------------------------------------------------------------------
# two sources of uncertainty:
#   (a) normal forecast noise  -> sd of the blend's current-era backtest errors
#   (b) model disagreement in a regime break -> sd across the three methods
# combined in quadrature; Student-t because the error sd rests on only 6 quarters
sd_bt = cur.pipe(lambda d: (sum(w[m] * d[m] for m in METHODS) / d["actual"] - 1) * 100).std()
sd_spread = np.std([fc[m] / blend * 100 - 100 for m in METHODS], ddof=1)
sd_total = np.sqrt(sd_bt ** 2 + sd_spread ** 2)
n_cur = len(cur)

rng = np.random.default_rng(590)
draws = blend * (1 + sd_total / 100 * rng.standard_t(df=n_cur - 1, size=200_000))
lo, hi = np.percentile(draws, [10, 90])

log("")
log(f"Interval: backtest sd {sd_bt:.2f}% , method spread sd {sd_spread:.2f}% "
    f"-> combined {sd_total:.2f}%, Student-t df={n_cur-1}, 200k draws")
log(f"POINT ${blend:.2f}   80% INTERVAL ${lo:.2f} - ${hi:.2f}")


# =============================================================================
# 5. CROSS-CHECK AGAINST GUIDANCE
# =============================================================================
header("5. GUIDANCE CROSS-CHECK")

# passenger share of operating revenue: Q3 is seasonally lower than Q2 (90.8% in Q3'25)
share_q3 = q.loc[t - 4, "pax_share"] * q.loc[t - 1, "pax_share"] / q.loc[t - 5, "pax_share"]
band_flat = [x * 0.92 for x in GUIDE_OPREV]
band_seas = [x * share_q3 for x in GUIDE_OPREV]
log(f"Passenger share of op revenue: Q2'26 {q.loc[t-1,'pax_share']:.4f}, "
    f"Q3'25 {q.loc[t-4,'pax_share']:.4f} -> Q3'26 est {share_q3:.4f}")
log(f"Passenger revenue band at packet's 92%     : ${band_flat[0]:,.0f}M - ${band_flat[1]:,.0f}M")
log(f"Passenger revenue band at seasonal share   : ${band_seas[0]:,.0f}M - ${band_seas[1]:,.0f}M")
for label, band in [("92%", band_flat), ("seasonal", band_seas)]:
    f_lo, f_hi = band[0] / TRAFFIC_PAX * 1000, band[1] / TRAFFIC_PAX * 1000
    log(f"  fare the band implies at Traffic's {TRAFFIC_PAX:,}k pax ({label}): ${f_lo:.2f} - ${f_hi:.2f}")
prod = blend * TRAFFIC_PAX / 1000
log(f"Team product: ${blend:.2f} x {TRAFFIC_PAX:,}k = ${prod:,.0f}M passenger revenue")
log(f"  inside 92% band? {band_flat[0] <= prod <= band_flat[1]}   "
    f"inside seasonal band? {band_seas[0] <= prod <= band_seas[1]}")


# =============================================================================
# 6. WHO RAISED THE FARE? THREE LENSES
# =============================================================================
header("6. ATTRIBUTION OF THE FARE JUMP -- three lenses")

att_rows = []
for p in [pd.Period("2026Q1", "Q"), pd.Period("2026Q2", "Q"), TARGET]:
    fare_p = q.loc[p, "fare"] if p != TARGET else blend
    base = q.loc[p - 4, "fare"]
    total = np.log(fare_p / base)
    # lens A: industry vs Southwest-specific
    ind = q.loc[p, "cpi_yoy"]
    # lens B: fuel cost per passenger vs everything else (dollars)
    fp = q.loc[p, "fuel_px"] if p != TARGET else fuel_price_estimate(p)
    gpp = q.loc[p, "gal_per_pax"] if p != TARGET else \
        q.loc[p - 4, "gal_per_pax"] * q.loc[p - 1, "gal_per_pax"] / q.loc[p - 5, "gal_per_pax"]
    d_fuel = (fp - q.loc[p - 4, "fuel_px"]) * gpp
    # lens C: longer trips vs higher price per mile
    haul_g = (np.log(q.loc[p, "haul"] / q.loc[p - 4, "haul"]) if p != TARGET
              else np.log(1097.6 / q.loc[p - 4, "haul"]))      # Traffic's Q3 haul estimate
    att_rows.append({
        "quarter": str(p) + (" (forecast)" if p == TARGET else ""),
        "fare_change_$": fare_p - base,
        "fare_yoy_%": total * 100,
        "A_industry_cpi_%": ind * 100,
        "A_southwest_own_%": (total - ind) * 100,
        "B_fuel_cost_per_pax_$": d_fuel,
        "B_non_fuel_$": (fare_p - base) - d_fuel,
        "C_longer_trips_%": haul_g * 100,
        "C_price_per_mile_%": (total - haul_g) * 100,
    })
att = pd.DataFrame(att_rows).set_index("quarter")
log(att.round(2).to_string())
log("")
log("Reading: in Q2 2026 (ex-breakage) the BLS index explains almost all of the")
log("fare increase -- Southwest's own premium over the industry is under 1 point.")
log("About half the dollar increase matches the rise in fuel cost per passenger,")
log("and a fifth of the % increase is just longer trips (more connections), not price.")


# =============================================================================
# 7. SAVE
# =============================================================================
pd.DataFrame([{
    "target": "avg_passenger_fare_usd_Q3_2026",
    "point": round(blend, 2), "lo80": round(lo, 2), "hi80": round(hi, 2),
    "yoy_pct": round((blend / q.loc[t - 4, "fare"] - 1) * 100, 2),
    **{m: round(fc[m], 2) for m in METHODS},
    **{"w_" + m: round(w[m], 3) for m in METHODS},
    "B0": round(b0(t), 2), "B1_packet": 220.67,
    "implied_pax_rev_musd_at_traffic": round(prod),
}]).to_csv(OUT / "forecast.csv", index=False)
bt.round(3).to_csv(OUT / "backtest.csv")
by_era.round(3).to_csv(OUT / "backtest_by_era.csv")
att.round(3).to_csv(OUT / "attribution.csv")
q.loc["2019Q1":].round(4).to_csv(OUT / "quarterly_panel.csv")

# --- charts ---------------------------------------------------------------------
fig, ax = plt.subplots(2, 2, figsize=(13, 9))

a = ax[0, 0]
p = q.loc["2023Q1":]
x = [str(i) for i in p.index]
a.plot(x, p["cpi_yoy"] * 100, marker="o", label="BLS airfare CPI YoY")
fy = p["fare_yoy"] * 100
fy.iloc[-1] = np.log(blend / q.loc[t - 4, "fare"]) * 100
a.plot(x, fy, marker="o", label="Southwest fare YoY (ex-breakage; Q3 = forecast)")
a.axhline(0, color="grey", lw=0.8)
a.set_title("Southwest fare vs industry, YoY (log %)")
a.tick_params(axis="x", rotation=60, labelsize=8)
a.legend(fontsize=8)

a = ax[0, 1]
e = bt[[c + "_err%" for c in ["P1", "P2", "P3", "B0", "B1"]]]
for c in e.columns:
    a.plot(e.index, e[c], marker="o", label=c.replace("_err%", ""),
           ls="--" if c.startswith("B") else "-")
a.axhline(0, color="grey", lw=0.8)
a.axvline(7.5, color="grey", ls=":")
a.set_title("Backtest error by quarter (%), dotted line = fee change")
a.tick_params(axis="x", rotation=60, labelsize=8)
a.legend(fontsize=8)

a = ax[1, 0]
names = ["B0", "B1", "P1", "P2", "P3", "BLEND"]
vals = [b0(t), 220.67, fc["P1"], fc["P2"], fc["P3"], blend]
a.bar(names, vals, color=["lightgrey", "lightgrey", "C0", "C0", "C0", "C3"])
a.errorbar(["BLEND"], [blend], yerr=[[blend - lo], [hi - blend]], color="black", capsize=6)
gl, gh = band_seas[0] / TRAFFIC_PAX * 1000, band_seas[1] / TRAFFIC_PAX * 1000
a.axhspan(gl, gh, color="green", alpha=0.15, label="fare implied by guidance at Traffic's pax")
a.set_ylim(170, 255)
a.set_title("Q3 2026 fare forecasts ($)")
a.legend(fontsize=8)

a = ax[1, 1]
a.bar(att.index, att["A_industry_cpi_%"], label="industry (BLS CPI)")
a.bar(att.index, att["A_southwest_own_%"], bottom=att["A_industry_cpi_%"],
      label="Southwest's own premium")
a.set_title("Who raised the fare? YoY (log %)")
a.legend(fontsize=8)

plt.tight_layout()
plt.savefig(OUT / "price_diagnostics.png", dpi=130)

(OUT / "run_log.txt").write_text("\n".join(log_lines) + "\n")
print(f"\nSaved outputs to {OUT}")
