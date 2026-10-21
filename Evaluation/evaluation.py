"""
AIPI 590 Alternative Data -- Southwest Q3 2026 case study
EVALUATION ROLE: compute the baselines, and backtest the Traffic and Price
methods quarter by quarter from 2022Q1 to 2026Q2 on one common footing.

What this adds on top of the two roles' own backtests:
  1. An independent re-implementation of every method, checked against the
     numbers each role committed (a reproduction audit, not a copy).
  2. The packet's full window. Price stopped at 2023Q1; the packet asks for 2022.
  3. Methods the roles blended but did not backtest: Traffic's M2 capacity
     identity (and so its 65/35 blend), and Price's blend with weights it could
     actually have known at the time (Price's own blend is in-sample).
  4. The out-of-sample record of both "naive regression" benchmarks (M3, M4),
     which the roles only fitted in-sample.
  5. Interval calibration: do the 80% intervals cover 80%?
  6. The passenger-revenue product -- the number the team is actually judged on
     against guidance -- and how correlated the two halves' errors are.

Run:  python Evaluation/evaluation.py
Needs: pandas, numpy, scipy, matplotlib  (scipy ships with statsmodels)
"""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(exist_ok=True)

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 60)

TARGET = pd.Period("2026Q3", "Q")
BT_START, BT_END = pd.Period("2022Q1", "Q"), pd.Period("2026Q2", "Q")
CURRENT_ERA = pd.Period("2025Q1", "Q")    # same split both roles used
BREAKAGE_Q2_2026 = 285                    # $M one-off reversal, added back (Traffic §8, Price §6)
ASM_GUIDE_MID_PCT = -0.5                  # Q3 2026 ASM guidance, -1% to flat
TRAFFIC_W1 = 0.65                         # Traffic's M1/M2 blend weight
PRICE_SHRINK = 0.5                        # Price's shrink-to-equal on blend weights

# the numbers each role handed over (their forecast.csv)
TRAFFIC_FC = pd.read_csv(ROOT / "Traffic/outputs/forecast.csv").iloc[0]
PRICE_FC = pd.read_csv(ROOT / "Price/outputs/forecast.csv").iloc[0]

log_lines = []
def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log_lines.append(s)

def head(t):
    say("\n" + "=" * 78)
    say(t)
    say("=" * 78)

def era_of(p):
    if p < pd.Period("2023Q1", "Q"):
        return "2022 (COVID-recovery base)"
    if p < CURRENT_ERA:
        return "2023-2024"
    return "2025-2026 (fee + model change)"


# =============================================================================
# 1. LOAD -- the same files and the same cleaning decisions the roles made
# =============================================================================
head("1. LOAD THE SHARED INPUTS (same cleaning as the roles)")

sw = pd.read_csv(DATA / "southwest_quarterly_stats_2019Q1_2026Q2.csv")
sw.index = pd.PeriodIndex(sw["quarter"], freq="Q")
sw["pax"] = sw["revenue_passengers_000"].astype(float)
sw["pax_rev_reported"] = sw["passenger_revenue_musd"].astype(float)
sw["pax_rev"] = sw["pax_rev_reported"]
sw.loc["2026Q2", "pax_rev"] += BREAKAGE_Q2_2026
sw["op_rev"] = sw["operating_revenue_musd"].astype(float)
sw.loc["2026Q2", "op_rev"] += BREAKAGE_Q2_2026
sw["fare"] = sw["pax_rev"] / sw["pax"] * 1000
sw["fare_reported"] = sw["avg_passenger_fare_usd"]
say(f"Southwest quarters: {len(sw)}  ({sw.index[0]} .. {sw.index[-1]})")
say(f"Q2 2026 fare: reported ${sw.loc['2026Q2','fare_reported']:.2f}, "
    f"ex-breakage ${sw.loc['2026Q2','fare']:.2f}  (the basis both roles forecast)")

# --- TSA, monthly and quarterly sums (Traffic: no day imputed or dropped) ------
tsa = pd.read_csv(DATA / "tsa_daily_checkpoint_2019-01-01_2026-09-30.csv", parse_dates=["date"])
tsa = tsa.set_index("date")["passengers_screened"].astype(float)
tsa_m = tsa.groupby(tsa.index.to_period("M")).sum()
tsa_q = tsa.groupby(tsa.index.to_period("Q")).sum()

# --- T-100 and Southwest's share of national throughput -------------------------
t100 = pd.read_csv(DATA / "bts_t100_domestic_segment_southwest_WN_monthly_2019-01_2026-07.csv")
t100.index = pd.PeriodIndex(t100["month"], freq="M")
mon = pd.DataFrame({"seg": t100["segment_passengers"].astype(float),
                    "t100_asm": t100["asm"].astype(float)}).join(tsa_m.rename("tsa"))
mon["share"] = mon["seg"] / mon["tsa"]
mon["share_yoy"] = mon["share"].pct_change(12) * 100

# --- quarterly traffic panel ------------------------------------------------------
pan = sw[["pax", "enplaned_passengers_000", "rpm_millions", "asm_millions"]].copy()
pan["trip_factor"] = pan["enplaned_passengers_000"] / pan["pax"]
pan["trip_factor_yoy"] = pan["trip_factor"].pct_change(4) * 100
pan["haul"] = pan["rpm_millions"] / pan["pax"] * 1000
pan["lf"] = pan["rpm_millions"] / pan["asm_millions"] * 100
pan["pax_yoy"] = pan["pax"].pct_change(4) * 100
t100_q = t100.groupby(t100.index.asfreq("Q")).agg(seg=("segment_passengers", "sum"),
                                                  nmon=("segment_passengers", "size"))
pan = pan.join(t100_q)
pan["uplift"] = pan["enplaned_passengers_000"] * 1000 / pan["seg"]
pan.loc[pan["nmon"] != 3, "uplift"] = np.nan
pan = pan.join(tsa_q.rename("tsa"))
pan["tsa_yoy"] = pan["tsa"].pct_change(4) * 100

# --- BLS airfare CPI (Oct 2025 blank -> interpolated) and EIA jet fuel spot -------
cpi = pd.read_csv(DATA / "bls_airline_fares_cpi_CUUR0000SETG01_2018-01_2026-09.csv",
                  parse_dates=["observation_date"]).set_index("observation_date")["CUUR0000SETG01"]
cpi = cpi.interpolate()
fuel = pd.read_csv(DATA / "eia_jet_fuel_gulf_coast_daily_DJFUELUSGULF_2019-01-01_2026-09-30.csv",
                   parse_dates=["observation_date"]).set_index("observation_date")["DJFUELUSGULF"]
fuel = fuel.dropna()

q = sw[["fare", "pax", "pax_rev", "op_rev", "fuel_per_gallon_usd", "fuel_gallons_millions"]].copy()
q = q.reindex(pd.period_range("2019Q1", TARGET, freq="Q"))
q["cpi"] = cpi.groupby(cpi.index.to_period("Q")).mean()
q["spot"] = fuel.groupby(fuel.index.to_period("Q")).mean()
q["fuel_px"] = q["fuel_per_gallon_usd"]
q["gal_per_pax"] = q["fuel_gallons_millions"] / q["pax"] * 1000
q["premium_spot"] = q["fuel_px"] - q["spot"]
for c in ["fare", "cpi"]:
    q[c + "_yoy"] = np.log(q[c] / q[c].shift(4))
    q[c + "_qoq"] = np.log(q[c] / q[c].shift(1))
say("TSA, T-100, BLS CPI and EIA spot loaded with the roles' cleaning decisions:")
say("  TSA: no day imputed; T-100 share = segment pax / TSA; CPI Oct 2025 interpolated;")
say("  EIA holiday blanks dropped; Q2 2026 passenger revenue +$285M (ex-breakage).")


# =============================================================================
# 2. THE METHODS, RE-IMPLEMENTED
# Every function forecasts quarter t from what was public before t's print:
# TSA and EIA through the end of t, BLS CPI through month 3 of t (released
# ~2 weeks after quarter-end, before Southwest reports), T-100 through month 1
# of t (BTS runs ~3 months late), Southwest's own figures through t-1.
# =============================================================================
head("2. METHODS RE-IMPLEMENTED FROM EACH ROLE'S WRITE-UP")

def month(t, k):
    """k-th month (0, 1, 2) of quarter t."""
    return pd.Period(f"{t.year}-{3 * (t.quarter - 1) + 1 + k:02d}", freq="M")

# ---------------------------------------------------------------- Traffic
def trip_factor_hat(t):
    """Traffic's blend of E1 (carry last YoY step) and E2 (seasonal step from t-1)."""
    tf = pan["trip_factor"]
    g = pan["trip_factor_yoy"].get(t - 1, np.nan)
    e1 = tf[t - 4] * (1 + (0.0 if np.isnan(g) else g) / 100)
    sr = [tf[pd.Period(f"{y}Q{t.quarter}", "Q")] / tf[pd.Period(f"{y}Q{t.quarter}", "Q") - 1]
          for y in range(t.year - 4, t.year)
          if pd.Period(f"{y}Q{t.quarter}", "Q") - 1 in tf.index
          and pd.Period(f"{y}Q{t.quarter}", "Q") in tf.index]
    e2 = tf[t - 1] * np.mean(sr)
    return (e1 + e2) / 2

def m1_tsa_chain(t):
    """TSA x share x uplift / trip factor. Month 1 from T-100, months 2-3 nowcast."""
    sh = mon["share_yoy"].dropna()
    gs = sh[sh.index <= month(t, 0)].iloc[-6:].mean()
    uy = (pan["uplift"] / pan["uplift"].shift(4)).dropna()
    up = pan.loc[t - 4, "uplift"] * uy[uy.index < t].iloc[-4:].mean()
    seg = 0.0
    for k in range(3):
        mp = month(t, k)
        if k == 0 and mp in t100.index:
            seg += mon.loc[mp, "seg"]
        else:
            seg += tsa_m[mp] * mon.loc[mp - 12, "share"] * (1 + gs / 100)
    return seg * up / trip_factor_hat(t) / 1000

def asm_proxy(t):
    """Stand-in for ASM guidance in the backtest: last year's ASMs scaled by the
    YoY change in T-100 domestic ASMs for month 1 of t -- the only capacity
    signal on file at forecast time. Historical guidance is not in the packet."""
    m = month(t, 0)
    return pan.loc[t - 4, "asm_millions"] * mon.loc[m, "t100_asm"] / mon.loc[m - 12, "t100_asm"]

def m2_capacity(t, asm):
    """ASM x load factor / haul. LF = last year + mean of the last two YoY LF steps;
    haul = last quarter x the average seasonal step over the four prior years."""
    lf = pan["lf"]
    lf_hat = lf[t - 4] + np.mean([lf[t - 2] - lf[t - 6], lf[t - 1] - lf[t - 5]])
    hs = [pan.loc[pd.Period(f"{y}Q{t.quarter}", "Q"), "haul"] /
          pan.loc[pd.Period(f"{y}Q{t.quarter}", "Q") - 1, "haul"]
          for y in range(t.year - 4, t.year)
          if pd.Period(f"{y}Q{t.quarter}", "Q") - 1 in pan.index]
    haul_hat = pan.loc[t - 1, "haul"] * np.mean(hs)
    return asm * (lf_hat / 100) * 1000 / haul_hat

def m3_naive_ols(t, start=pd.Period("2022Q1", "Q"), min_n=4):
    """revpax YoY ~ a + b * TSA YoY, refitted each quarter on start..t-1 only.
    Traffic fitted it once, in-sample, on 2022Q1-2026Q2 (R2 0.98)."""
    d = pan.loc[start:t - 1, ["pax_yoy", "tsa_yoy"]].dropna()
    if len(d) < min_n:
        return np.nan
    X = np.column_stack([np.ones(len(d)), d["tsa_yoy"].values])
    a, b = np.linalg.lstsq(X, d["pax_yoy"].values, rcond=None)[0]
    return pan.loc[t - 4, "pax"] * (1 + (a + b * pan.loc[t, "tsa_yoy"]) / 100)

# ---------------------------------------------------------------- Price
NORMAL_YEARS = [2019, 2022, 2023, 2024, 2025, 2026]     # Price skips 2020-21

def p1_industry_anchor(t):
    cpi_g = np.log(q.loc[t, "cpi"] / q.loc[t - 4, "cpi"])
    prem = q.loc[t - 1, "fare_yoy"] - q.loc[t - 1, "cpi_yoy"]
    return q.loc[t - 4, "fare"] * np.exp(cpi_g + prem)

def p2_seasonal_step(t):
    d = q.loc[:t - 1]
    d = d[d.index.year.isin(NORMAL_YEARS)].dropna(subset=["fare_qoq", "cpi_qoq"])
    d = d[d.index > pd.Period("2019Q1", "Q")]
    X = np.column_stack([(d.index.quarter == k).astype(float) for k in [1, 2, 3, 4]]
                        + [d["cpi_qoq"].values])
    coef = np.linalg.lstsq(X, d["fare_qoq"].values, rcond=None)[0]
    return q.loc[t - 1, "fare"] * np.exp(coef[t.quarter - 1] + coef[4] * q.loc[t, "cpi_qoq"])

def p3_fuel_passthrough(t):
    fuel_t = q.loc[t, "spot"] + q.loc[t - 4:t - 1, "premium_spot"].mean()
    gpp = q.loc[t - 4, "gal_per_pax"] * q.loc[t - 1, "gal_per_pax"] / q.loc[t - 5, "gal_per_pax"]
    d_fuel = (fuel_t - q.loc[t - 4, "fuel_px"]) * gpp
    d_fuel_prev = (q.loc[t - 1, "fuel_px"] - q.loc[t - 5, "fuel_px"]) * q.loc[t - 1, "gal_per_pax"]
    nonfuel_prev = (q.loc[t - 1, "fare"] - q.loc[t - 5, "fare"]) - d_fuel_prev
    return q.loc[t - 4, "fare"] + d_fuel + nonfuel_prev

def m4_naive_regression(t, min_n=3):
    d = q.loc[pd.Period("2022Q2", "Q"):t - 1].dropna(subset=["fare_yoy", "cpi_yoy"])
    if len(d) < min_n:
        return np.nan
    X = np.column_stack([np.ones(len(d)), d["cpi_yoy"].values])
    a, b = np.linalg.lstsq(X, d["fare_yoy"].values, rcond=None)[0]
    return q.loc[t - 4, "fare"] * np.exp(a + b * q.loc[t, "cpi_yoy"])

# ---------------------------------------------------------------- baselines
def b0(s, t):
    return s[t - 4]

def b1(s, t):
    return s[t - 4] * s[t - 1] / s[t - 5]

say("Traffic: M1 TSA chain, M2 capacity identity (ASM from a T-100 proxy, and an")
say("         'oracle' run on actual ASMs), M3 naive OLS refitted each quarter.")
say("Price:   P1 industry anchor, P2 seasonal step, P3 fuel pass-through, M4 naive")
say("         regression. Baselines B0 (same quarter last year), B1 (B0 x last YoY).")


# =============================================================================
# 3. RUN EVERYTHING, 2022Q1 - 2026Q2
# =============================================================================
head("3. BACKTEST 2022Q1 - 2026Q2")

quarters = list(pd.period_range(BT_START, BT_END, freq="Q"))
rows = []
for t in quarters:
    r = {"quarter": t, "era": era_of(t),
         "pax_actual": pan.loc[t, "pax"],
         "fare_actual": q.loc[t, "fare"],
         "fare_actual_reported": sw.loc[t, "fare_reported"],
         "rev_actual": q.loc[t, "pax_rev"]}
    r["M1"] = m1_tsa_chain(t)
    r["M2"] = m2_capacity(t, asm_proxy(t))
    r["M2_oracle"] = m2_capacity(t, pan.loc[t, "asm_millions"])
    r["T_BLEND"] = TRAFFIC_W1 * r["M1"] + (1 - TRAFFIC_W1) * r["M2"]
    r["M3"] = m3_naive_ols(t)
    r["pax_B0"], r["pax_B1"] = b0(pan["pax"], t), b1(pan["pax"], t)
    r["P1"], r["P2"], r["P3"] = p1_industry_anchor(t), p2_seasonal_step(t), p3_fuel_passthrough(t)
    r["M4"] = m4_naive_regression(t)
    r["fare_B0"], r["fare_B1"] = b0(q["fare"], t), b1(q["fare"], t)
    rows.append(r)
bt = pd.DataFrame(rows).set_index("quarter")

# --- Price blends --------------------------------------------------------------
# (a) as delivered: weights fitted on the 2025-26 errors, then applied to those
#     same quarters -- in-sample by construction, which Price says openly.
# (b) EQUAL: no fitted weights at all, so fully out-of-sample.
# (c) OOS: Price's rule (inverse MSE within the era, shrunk 50% to equal), but
#     using only errors from quarters strictly before t. Equal weights until two
#     errors exist in the era.
P = ["P1", "P2", "P3"]
w_delivered = {m: PRICE_FC["w_" + m] for m in P}
bt["P_BLEND_insample"] = sum(w_delivered[m] * bt[m] for m in P)
bt["P_BLEND_equal"] = bt[P].mean(axis=1)
oos, oos_w = [], {}
for t in bt.index:
    prior = bt.loc[[p for p in bt.index if p < t and era_of(p) == era_of(t)]]
    if len(prior) >= 2:
        mse = {m: ((prior[m] / prior["fare_actual"] - 1) ** 2).mean() for m in P}
        inv = {m: 1 / mse[m] for m in P}
        w = {m: PRICE_SHRINK * inv[m] / sum(inv.values()) + (1 - PRICE_SHRINK) / 3 for m in P}
    else:
        w = {m: 1 / 3 for m in P}
    oos_w[t] = w
    oos.append(sum(w[m] * bt.loc[t, m] for m in P))
bt["P_BLEND_oos"] = oos

# the team's product: passenger revenue = passengers x fare ($M)
bt["REV_team"] = bt["T_BLEND"] * bt["P_BLEND_oos"] / 1000
bt["REV_M1xPoos"] = bt["M1"] * bt["P_BLEND_oos"] / 1000
bt["rev_B0"] = [b0(q["pax_rev"], t) for t in bt.index]
bt["rev_B1"] = [b1(q["pax_rev"], t) for t in bt.index]

PAX = ["M1", "M2", "M2_oracle", "T_BLEND", "M3", "pax_B0", "pax_B1"]
FARE = ["P1", "P2", "P3", "P_BLEND_insample", "P_BLEND_equal", "P_BLEND_oos", "M4",
        "fare_B0", "fare_B1"]
REV = ["REV_team", "REV_M1xPoos", "rev_B0", "rev_B1"]
for c in PAX:
    bt[c + "_err"] = (bt[c] / bt["pax_actual"] - 1) * 100
for c in FARE:
    bt[c + "_err"] = (bt[c] / bt["fare_actual"] - 1) * 100
for c in REV:
    bt[c + "_err"] = (bt[c] / bt["rev_actual"] - 1) * 100

say("Revenue passengers, % error (forecast / actual - 1):")
say(bt[[c + "_err" for c in PAX]].round(2).to_string())
say("\nAverage fare, % error (vs ex-breakage fare in 2026Q2, as both roles forecast):")
say(bt[[c + "_err" for c in FARE]].round(2).to_string())
say("\nPassenger revenue ($M), % error:")
say(bt[[c + "_err" for c in REV]].round(2).to_string())


# =============================================================================
# 4. REPRODUCTION AUDIT -- does the independent re-implementation match?
# =============================================================================
head("4. REPRODUCTION AUDIT AGAINST EACH ROLE'S COMMITTED BACKTEST")

tr = pd.read_csv(ROOT / "Traffic/outputs/backtest.csv", index_col="quarter")
pr = pd.read_csv(ROOT / "Price/outputs/backtest.csv", index_col="quarter")
audit = []
for col, src, ours in [("M1", tr, "M1"), ("B0", tr, "pax_B0"), ("B1", tr, "pax_B1")]:
    d = (bt[ours].rename(str) - src[col]).dropna()
    audit.append(dict(role="Traffic", series=col, quarters=f"{d.index[0]}..{d.index[-1]}",
                      n=len(d), max_abs_diff=d.abs().max(), unit="000 pax"))
for col, ours in [("P1", "P1"), ("P2", "P2"), ("P3", "P3"), ("M4", "M4"),
                  ("B0", "fare_B0"), ("B1", "fare_B1"), ("BLEND", "P_BLEND_insample")]:
    d = (bt[ours].rename(str) - pr[col]).dropna()
    audit.append(dict(role="Price", series=col, quarters=f"{d.index[0]}..{d.index[-1]}",
                      n=len(d), max_abs_diff=d.abs().max(), unit="$"))
audit = pd.DataFrame(audit)
say(audit.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
ok = bool((audit["max_abs_diff"] < 0.01).all())
say(f"\nAll series reproduce to within 0.01 of the committed values: {ok}")
say("(Price's blend differs by up to the rounding of its 3-decimal weights.)" if not ok else
    "Both roles' backtests are reproducible from their write-ups alone.")


# =============================================================================
# 5. THE BACKTEST TABLE BY PERIOD -- the Evaluation deliverable
# =============================================================================
head("5. BACKTEST TABLE BY PERIOD")

PERIODS = [
    ("2022-2024 (pre fee change)", lambda p: p < CURRENT_ERA),
    ("  of which 2022 (COVID base)", lambda p: p < pd.Period("2023Q1", "Q")),
    ("  of which 2023-2024", lambda p: pd.Period("2023Q1", "Q") <= p < CURRENT_ERA),
    ("2025-2026 (fee + model change)", lambda p: p >= CURRENT_ERA),
    ("full sample 2022Q1-2026Q2", lambda p: True),
]

def summarise(cols, b1_col):
    out = []
    for name, sel in PERIODS:
        g = bt.loc[[p for p in bt.index if sel(p)]]
        for c in cols:
            e = g[c + "_err"].dropna()
            if e.empty:
                continue
            e_b1 = g.loc[e.index, b1_col + "_err"]
            out.append(dict(period=name, method=c, n=len(e), MAPE=e.abs().mean(),
                            bias=e.mean(), RMSE=np.sqrt((e ** 2).mean()),
                            sd=e.std(ddof=1) if len(e) > 1 else np.nan,
                            beats_B1=f"{int((e.abs() < e_b1.abs()).sum())}/{len(e)}"))
    return pd.DataFrame(out)

by_pax = summarise(PAX, "pax_B1")
by_fare = summarise(FARE, "fare_B1")
by_rev = summarise(REV, "rev_B1")

def mape_grid(df, cols):
    g = df.pivot(index="period", columns="method", values="MAPE")
    return g.reindex(index=[p for p, _ in PERIODS], columns=cols)

say("MAPE (%) -- REVENUE PASSENGERS")
say(mape_grid(by_pax, PAX).round(2).to_string())
say("\nMAPE (%) -- AVERAGE FARE")
say(mape_grid(by_fare, FARE).round(2).to_string())
say("\nMAPE (%) -- PASSENGER REVENUE (the product)")
say(mape_grid(by_rev, REV).round(2).to_string())

cur = bt.loc[CURRENT_ERA:]
say("\nCurrent era, quarters each method beats B1 (|err| smaller):")
for c in ["M1", "T_BLEND", "M3", "P2", "P3", "P_BLEND_oos", "P_BLEND_equal", "REV_team"]:
    b1c = "pax_B1" if c in PAX else "fare_B1" if c in FARE else "rev_B1"
    wins = int((cur[c + "_err"].abs() < cur[b1c + "_err"].abs()).sum())
    say(f"  {c:16s} {wins}/{len(cur)}")


# =============================================================================
# 6. IS ANY EDGE OVER B1 REAL? Diebold-Mariano with the small-sample correction
# =============================================================================
head("6. IS THE EDGE OVER BASELINE B1 STATISTICALLY DISTINGUISHABLE?")

def dm_hln(e_model, e_base):
    """Diebold-Mariano on squared errors, h=1, Harvey-Leybourne-Newbold small-sample
    correction, t(n-1) reference. Negative stat = model better. Two-sided p."""
    d = (e_model ** 2 - e_base ** 2).dropna()
    n = len(d)
    if n < 3 or d.std(ddof=1) == 0:
        return np.nan, np.nan, n
    dm = d.mean() / np.sqrt(d.var(ddof=0) / n)
    dm *= np.sqrt((n - 1) / n)                 # HLN correction for h = 1
    return dm, 2 * stats.t.sf(abs(dm), df=n - 1), n

dm_rows = []
for period, sel in [("2022-2024", lambda p: p < CURRENT_ERA),
                    ("2023-2024", lambda p: pd.Period("2023Q1", "Q") <= p < CURRENT_ERA),
                    ("2025-2026", lambda p: p >= CURRENT_ERA),
                    ("full", lambda p: True)]:
    g = bt.loc[[p for p in bt.index if sel(p)]]
    for m, base in [("M1", "pax_B1"), ("T_BLEND", "pax_B1"), ("P2", "fare_B1"),
                    ("P3", "fare_B1"), ("P_BLEND_oos", "fare_B1"), ("REV_team", "rev_B1")]:
        s, pv, n = dm_hln(g[m + "_err"], g[base + "_err"])
        dm_rows.append(dict(period=period, model=m, vs=base, n=n, dm_stat=s, p_value=pv))
dm_tab = pd.DataFrame(dm_rows)
say(dm_tab.round(3).to_string(index=False))
say("\nNegative = the model's squared errors are smaller than B1's. With n = 6 in the")
say("current era, nothing short of a very large and consistent edge reaches p < 0.10.")


# =============================================================================
# 7. INTERVAL CALIBRATION -- do the 80% intervals cover 80%?
# =============================================================================
head("7. INTERVAL CALIBRATION")

# (a) Apply each role's DELIVERED half-width (as % of its point) to the errors its
#     method actually made. A calibrated 80% band covers ~80% of them.
t_hw = (TRAFFIC_FC["hi80"] - TRAFFIC_FC["lo80"]) / 2 / TRAFFIC_FC["point"] * 100
p_hw = (PRICE_FC["hi80"] - PRICE_FC["lo80"]) / 2 / PRICE_FC["point"] * 100
cal_rows = []
for name, col, hw in [("Traffic (blend)", "T_BLEND", t_hw), ("Traffic (M1)", "M1", t_hw),
                      ("Price (OOS blend)", "P_BLEND_oos", p_hw),
                      ("Price (in-sample blend)", "P_BLEND_insample", p_hw)]:
    for period, sel in [("2023-2024", lambda p: pd.Period("2023Q1", "Q") <= p < CURRENT_ERA),
                        ("2025-2026", lambda p: p >= CURRENT_ERA)]:
        e = bt.loc[[p for p in bt.index if sel(p)], col + "_err"]
        cal_rows.append(dict(check="delivered half-width", series=name, period=period,
                             half_width_pct=hw, n=len(e),
                             covered=int((e.abs() <= hw).sum()),
                             coverage=(e.abs() <= hw).mean()))

# (b) The two roles turn the same "Student-t, 5 df" into different widths.
#     Traffic rescales the t to have the backtest sd   -> 80% half-width 1.14 sd.
#     Price uses the backtest sd as the t's scale       -> 80% half-width 1.48 sd.
#     Test both rules out of sample: half-width = k x sd of the six errors the
#     method made in the quarters before t (known at forecast time).
k_traffic = stats.t.ppf(0.9, 5) * np.sqrt(3 / 5)
k_price = stats.t.ppf(0.9, 5)
k_normal = stats.norm.ppf(0.9)
for name, col in [("Traffic M1", "M1"), ("Traffic blend", "T_BLEND"),
                  ("Price OOS blend", "P_BLEND_oos"), ("Product", "REV_team")]:
    e = bt[col + "_err"]
    sd_trail = e.shift(1).rolling(6).std()
    for rule, k in [("t5 rescaled to sd (Traffic)", k_traffic),
                    ("normal", k_normal), ("t5 with sd as scale (Price)", k_price)]:
        for period, sel in [("2023Q3-2024Q4", lambda p: p < CURRENT_ERA),
                            ("2025-2026", lambda p: p >= CURRENT_ERA)]:
            idx = [p for p in bt.index if sel(p) and not np.isnan(sd_trail[p])]
            cov = (e[idx].abs() <= k * sd_trail[idx])
            cal_rows.append(dict(check=f"rolling 6q sd, {rule}", series=name, period=period,
                                 half_width_pct=float((k * sd_trail[idx]).mean()), n=len(idx),
                                 covered=int(cov.sum()), coverage=cov.mean()))
# (c) A harmonised rule for both halves: the error sd over every post-COVID
#     quarter (2023Q1-2026Q2, n = 14), Student-t with n-1 df rescaled to that sd.
#     Excludes 2022's COVID-base quarters; keeps both regimes, because the
#     current era's six quarters are the calmest M1 has had and a band sized on
#     them alone assumes that luck continues.
POST_COVID = pd.Period("2023Q1", "Q")
harm_rows = []
for name, col, fc_point in [("Traffic M1", "M1", TRAFFIC_FC["point"]),
                            ("Traffic blend", "T_BLEND", TRAFFIC_FC["point"]),
                            ("Price OOS blend", "P_BLEND_oos", PRICE_FC["point"]),
                            ("Product", "REV_team", np.nan)]:
    e = bt.loc[POST_COVID:, col + "_err"]
    n = len(e)
    k = stats.t.ppf(0.9, n - 1) * np.sqrt((n - 3) / (n - 1))
    hw = k * e.std(ddof=1)
    harm_rows.append(dict(series=name, n=n, sd_pct=e.std(ddof=1), k=k, half_width_pct=hw,
                          coverage_post_covid=(e.abs() <= hw).mean(),
                          lo80=fc_point * (1 - hw / 100), hi80=fc_point * (1 + hw / 100)))
harm = pd.DataFrame(harm_rows)

cal = pd.DataFrame(cal_rows)
say("(a) Each role's delivered half-width applied to its own backtest errors:")
say(cal[cal["check"] == "delivered half-width"].drop(columns="check")
    .round(3).to_string(index=False))
say(f"\n    Traffic's interval is +/-{t_hw:.2f}%; Price's is +/-{p_hw:.2f}%.")
say("\n(b) Rolling rule: half-width = k x sd of the previous six errors (vintage-legal):")
say(cal[cal["check"] != "delivered half-width"].round(3).to_string(index=False))
say(f"\n    k = {k_traffic:.3f} (Traffic's rescaled t5), {k_normal:.3f} (normal), "
    f"{k_price:.3f} (Price's unscaled t5).")
say("    The roles describe the same distribution and implement it differently; Price's")
say(f"    convention makes its band {k_price / k_traffic - 1:.0%} wider than Traffic's would be at the same sd.")
post = bt.loc[POST_COVID:]
say(f"\n    Over all 14 post-COVID quarters, Traffic's +/-{t_hw:.2f}% covers "
    f"{(post['M1_err'].abs() <= t_hw).mean():.0%} of M1's errors and Price's +/-{p_hw:.2f}% covers "
    f"{(post['P_BLEND_oos_err'].abs() <= p_hw).mean():.0%} of the blend's.")
sd6 = bt["M1_err"].rolling(6).std().loc[POST_COVID + 5:]     # windows wholly post-COVID
say(f"    Traffic's band is sized on M1's calmest six-quarter stretch (rolling sd "
    f"{sd6.min():.2f}-{sd6.max():.2f}%")
say("    across post-COVID windows; the latest is the minimum). Price's uses the wider t.")
say("    One band is too narrow and the other too wide.")
say("\n(c) Harmonised rule for both halves: sd over 2023Q1-2026Q2 (n=14), t(13) rescaled:")
say(harm.round(3).to_string(index=False))


# =============================================================================
# 8. HOW THE TWO HALVES' ERRORS COMBINE -- input for Integration's product interval
# =============================================================================
head("8. ERROR CORRELATION BETWEEN THE TWO HALVES")

corr_rows = []
for period, sel in [("2023-2024", lambda p: pd.Period("2023Q1", "Q") <= p < CURRENT_ERA),
                    ("2025-2026", lambda p: p >= CURRENT_ERA),
                    ("2023Q1-2026Q2", lambda p: p >= pd.Period("2023Q1", "Q"))]:
    g = bt.loc[[p for p in bt.index if sel(p)]]
    for tcol, pcol in [("M1", "P_BLEND_oos"), ("T_BLEND", "P_BLEND_oos")]:
        x, y = g[tcol + "_err"], g[pcol + "_err"]
        r = x.corr(y)
        # Fisher-z 80% band on r, to show how little n = 6 pins it down
        se = 1 / np.sqrt(max(len(x) - 3, 1))
        lo_r, hi_r = np.tanh(np.arctanh(r) + np.array([-1, 1]) * stats.norm.ppf(0.9) * se)
        corr_rows.append(dict(period=period, traffic=tcol, price=pcol, n=len(x), rho=r,
                              rho_lo80=lo_r, rho_hi80=hi_r,
                              sd_pax=x.std(ddof=1), sd_fare=y.std(ddof=1),
                              sd_product=g["REV_team_err"].std(ddof=1)))
corr = pd.DataFrame(corr_rows)
say(corr.round(3).to_string(index=False))
c_cur = corr.query("period == '2025-2026' and traffic == 'M1'").iloc[0]
c_all = corr.query("period == '2023Q1-2026Q2' and traffic == 'M1'").iloc[0]
say(f"\nThe halves share no input (TSA/T-100 vs BLS/EIA), yet their errors are NEGATIVELY")
say(f"correlated: rho {c_all['rho']:+.2f} over 2023Q1-2026Q2, {c_cur['rho']:+.2f} in the current era.")
say("That is mechanical, not a coincidence. Southwest's fare is passenger revenue /")
say("revenue passengers, and the fare methods never see the passenger count. When the")
say("count comes in below forecast (Traffic over-forecasts), the same revenue is spread")
say("over fewer passengers and the fare comes in above forecast (Price under-forecasts).")
say("The 2026 trip-factor shift is exactly this: fewer revenue passengers, higher fare.")
indep = np.sqrt(c_all["sd_pax"] ** 2 + c_all["sd_fare"] ** 2)
say(f"\nConsequence for the product: errors that offset make it MORE accurate than the")
say(f"halves imply. Post-COVID, independence would give a product sd of {indep:.2f}%;")
say(f"the realised product sd was {c_all['sd_product']:.2f}%. Integration should not combine the")
say(f"halves as independent. Recommended rho = {c_all['rho']:+.1f} (the 14-quarter estimate, the more")
say("conservative of the two), with rho = 0 shown as the cautious bound.")

# Traffic imposed rho = 0.7 between its own M1 and M2 errors. Check it.
say("\nTraffic's own assumption, M1/M2 error correlation rho = 0.7:")
for period, sel in [("2023-2024", lambda p: POST_COVID <= p < CURRENT_ERA),
                    ("2025-2026", lambda p: p >= CURRENT_ERA),
                    ("2023Q1-2026Q2", lambda p: p >= POST_COVID)]:
    g = bt.loc[[p for p in bt.index if sel(p)]]
    say(f"  {period:14s} M1 vs M2 (T-100 ASM proxy) {g['M1_err'].corr(g['M2_err']):+.2f}   "
        f"M1 vs M2 (actual ASM) {g['M1_err'].corr(g['M2_oracle_err']):+.2f}")
say("  Realised: +0.2 to +0.6 before 2025, about zero since. 0.7 sits at or above every")
say("  window, so that part of Traffic's interval is conservative. The backtest-sd part")
say("  (section 7) is not, and it is the larger effect: the two do not cancel.")


# =============================================================================
# 9. BASELINES FOR Q3 2026 -- and what each role's forecast looks like against them
# =============================================================================
head("9. BASELINES FOR Q3 2026")

fare_rep = sw["fare_reported"]
rev_rep = sw["pax_rev_reported"]
base = pd.DataFrame([
    dict(target="revenue passengers (000s)", basis="reported",
         B0=b0(pan["pax"], TARGET), B1=b1(pan["pax"], TARGET),
         team=TRAFFIC_FC["point"], team_lo80=TRAFFIC_FC["lo80"], team_hi80=TRAFFIC_FC["hi80"]),
    dict(target="average fare ($)", basis="reported Q2 (packet's B1)",
         B0=b0(fare_rep, TARGET), B1=b1(fare_rep, TARGET),
         team=PRICE_FC["point"], team_lo80=PRICE_FC["lo80"], team_hi80=PRICE_FC["hi80"]),
    dict(target="average fare ($)", basis="ex-breakage Q2",
         B0=b0(q["fare"], TARGET), B1=b1(q["fare"], TARGET),
         team=PRICE_FC["point"], team_lo80=PRICE_FC["lo80"], team_hi80=PRICE_FC["hi80"]),
    dict(target="passenger revenue ($M)", basis="reported Q2",
         B0=b0(rev_rep, TARGET), B1=b1(rev_rep, TARGET),
         team=TRAFFIC_FC["point"] * PRICE_FC["point"] / 1000, team_lo80=np.nan, team_hi80=np.nan),
    dict(target="passenger revenue ($M)", basis="ex-breakage Q2",
         B0=b0(q["pax_rev"], TARGET), B1=b1(q["pax_rev"], TARGET),
         team=TRAFFIC_FC["point"] * PRICE_FC["point"] / 1000, team_lo80=np.nan, team_hi80=np.nan),
])
base["team_vs_B0_pct"] = (base["team"] / base["B0"] - 1) * 100
base["team_vs_B1_pct"] = (base["team"] / base["B1"] - 1) * 100
say(base.round(2).to_string(index=False))
say("\nB1 on the fare is $8 apart depending on the Q2 basis. The packet's $220.67 uses")
say("the reported Q2 fare, which carries the $285M one-off. Scored as 'beat B1', the")
say("team's fare looks 4% better than a naive forecast on the packet's basis and")
say("0.2% better on the ex-breakage basis. Only the second is a fair comparison.")

# Scoring basis: the methods forecast the underlying fare. If the print carries a
# one-off, the score moves with it. 2026Q2 shows the size of that effect.
t2 = pd.Period("2026Q2", "Q")
say(f"\nScoring basis check, 2026Q2 Price OOS blend ${bt.loc[t2, 'P_BLEND_oos']:.2f}:")
say(f"  vs ex-breakage ${bt.loc[t2, 'fare_actual']:.2f}: {bt.loc[t2, 'P_BLEND_oos_err']:+.2f}%   "
    f"vs reported ${bt.loc[t2, 'fare_actual_reported']:.2f}: "
    f"{(bt.loc[t2, 'P_BLEND_oos'] / bt.loc[t2, 'fare_actual_reported'] - 1) * 100:+.2f}%")
say("  A one-off of that size in Q3 would double the fare error on its own.")

# what the extra, never-blended Q3 2026 methods say
m2_q3_proxy = m2_capacity(TARGET, pan.loc[TARGET - 4, "asm_millions"]
                          * mon.loc[month(TARGET, 0), "t100_asm"] / mon.loc[month(TARGET, 0) - 12, "t100_asm"])
m2_q3_guided = m2_capacity(TARGET, pan.loc[TARGET - 4, "asm_millions"] * (1 + ASM_GUIDE_MID_PCT / 100))
pan.loc[TARGET, "tsa_yoy"] = (tsa_q[TARGET] / tsa_q[TARGET - 4] - 1) * 100
say(f"\nQ3 2026 cross-checks from this re-implementation:")
say(f"  M1 TSA chain                                {m1_tsa_chain(TARGET):9,.0f}k  (Traffic: {TRAFFIC_FC['M1']:,.0f}k)")
say(f"  M2 at guided ASM midpoint ({ASM_GUIDE_MID_PCT:+.1f}%)          {m2_q3_guided:9,.0f}k  (Traffic: {TRAFFIC_FC['M2']:,.0f}k)")
say(f"  M2 at July T-100 ASM YoY "
    f"({(mon.loc[month(TARGET, 0), 't100_asm'] / mon.loc[month(TARGET, 0) - 12, 't100_asm'] - 1) * 100:+.2f}%)"
    f"          {m2_q3_proxy:9,.0f}k")
say(f"  M3 naive OLS, refitted on 2022Q1-2026Q2     {m3_naive_ols(TARGET):9,.0f}k  (Traffic: {TRAFFIC_FC['M3_benchmark']:,.0f}k)")
say(f"  P1 / P2 / P3   ${p1_industry_anchor(TARGET):.2f} / ${p2_seasonal_step(TARGET):.2f} / "
    f"${p3_fuel_passthrough(TARGET):.2f}  (Price: ${PRICE_FC['P1']:.2f} / ${PRICE_FC['P2']:.2f} / ${PRICE_FC['P3']:.2f})")
say(f"  M4 naive regression                         ${m4_naive_regression(TARGET):.2f}")
w_q3 = {}
prior = bt.loc[CURRENT_ERA:]
mse = {m: ((prior[m] / prior["fare_actual"] - 1) ** 2).mean() for m in P}
inv = {m: 1 / mse[m] for m in P}
w_q3 = {m: PRICE_SHRINK * inv[m] / sum(inv.values()) + (1 - PRICE_SHRINK) / 3 for m in P}
say(f"  Price blend weights for Q3 (all six current-era errors, no look-ahead for Q3 itself): "
    + ", ".join(f"{m} {w_q3[m]:.3f}" for m in P))


# =============================================================================
# 10. SAVE
# =============================================================================
out_q = bt.copy()
out_q.index = out_q.index.astype(str)
out_q.round(3).to_csv(OUT / "backtest_quarterly.csv")
pd.concat([by_pax.assign(target="revenue_passengers"),
           by_fare.assign(target="average_fare"),
           by_rev.assign(target="passenger_revenue")])[
    ["target", "period", "method", "n", "MAPE", "bias", "RMSE", "sd", "beats_B1"]
].round(3).to_csv(OUT / "backtest_by_period.csv", index=False)
dm_tab.round(4).to_csv(OUT / "dm_tests.csv", index=False)
cal.round(4).to_csv(OUT / "interval_calibration.csv", index=False)
harm.round(4).to_csv(OUT / "interval_recommendation.csv", index=False)
corr.round(4).to_csv(OUT / "error_correlation.csv", index=False)
base.round(2).to_csv(OUT / "baselines_q3_2026.csv", index=False)
audit.round(6).to_csv(OUT / "reproduction_audit.csv", index=False)
pd.DataFrame(oos_w).T.rename_axis("quarter").rename(index=str).round(3) \
    .to_csv(OUT / "price_oos_blend_weights.csv")

# --- charts -------------------------------------------------------------------
fig, ax = plt.subplots(2, 2, figsize=(14, 9))
x = [str(p) for p in bt.index]
split = x.index(str(CURRENT_ERA)) - 0.5

a = ax[0, 0]
for c, st, col in [("M1", "-", "#1f3b73"), ("T_BLEND", "-", "#2a9d8f"),
                   ("pax_B0", "--", "#999999"), ("pax_B1", "--", "#d1495b")]:
    a.plot(x, bt[c + "_err"], st, marker="o", ms=4, color=col, label=c)
a.axhline(0, color="k", lw=.8); a.axvline(split, color="grey", ls=":")
a.set_ylim(-25, 30); a.set_title("Revenue passengers: backtest error (%)")
a.tick_params(axis="x", rotation=60, labelsize=8); a.legend(fontsize=8)

a = ax[0, 1]
for c, st, col in [("P2", "-", "#1f3b73"), ("P3", "-", "#e9a13b"), ("P_BLEND_oos", "-", "#2a9d8f"),
                   ("fare_B0", "--", "#999999"), ("fare_B1", "--", "#d1495b")]:
    a.plot(x, bt[c + "_err"], st, marker="o", ms=4, color=col, label=c)
a.axhline(0, color="k", lw=.8); a.axvline(split, color="grey", ls=":")
a.set_ylim(-25, 30); a.set_title("Average fare: backtest error (%)")
a.tick_params(axis="x", rotation=60, labelsize=8); a.legend(fontsize=8)

a = ax[1, 0]
g = mape_grid(by_rev, REV).loc[["  of which 2023-2024", "2025-2026 (fee + model change)"]]
g.index = ["2023-2024", "2025-2026"]
g.T.plot.bar(ax=a, color=["#9fb3d1", "#1f3b73"], rot=0)
a.set_title("Passenger revenue (the product): MAPE % by period"); a.set_ylabel("MAPE %")
a.legend(fontsize=8)

a = ax[1, 1]
c3 = bt.loc[pd.Period("2023Q1", "Q"):]
colors = ["#d1495b" if p >= CURRENT_ERA else "#9fb3d1" for p in c3.index]
a.scatter(c3["M1_err"], c3["P_BLEND_oos_err"], c=colors, s=50)
for p, r in c3.iterrows():
    a.annotate(str(p), (r["M1_err"], r["P_BLEND_oos_err"]), fontsize=7, xytext=(3, 3),
               textcoords="offset points")
a.axhline(0, color="k", lw=.6); a.axvline(0, color="k", lw=.6)
a.set_xlabel("Traffic M1 error %"); a.set_ylabel("Price OOS blend error %")
a.set_title("Do the two halves miss together? (red = 2025-26)")
plt.tight_layout(); plt.savefig(OUT / "evaluation_diagnostics.png", dpi=130)

(OUT / "run_log.txt").write_text("\n".join(log_lines) + "\n")
say(f"\nwrote {len(list(OUT.iterdir()))} files to {OUT}")
