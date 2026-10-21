"""
AIPI 590 Alternative Data -- Southwest Q3 2026 case study
INTEGRATION ROLE: combine the Traffic and Price forecasts, run the passenger
revenue check against guidance, produce the numbers for the forecast form,
and (after Oct 21) score the locked forecast against the print.

Inputs, all already in the repo:
  Traffic/outputs/forecast.csv          passenger point
  Price/outputs/forecast.csv            fare point
  Evaluation/outputs/*.csv              harmonised intervals, error correlation, baselines
  data/southwest_quarterly_stats_*.csv  for the guidance arithmetic
  Integration/actuals.json              the reported Q3 figures -- all null until the print

The form numbers never read actuals.json, so filling it in after the print
cannot move the locked forecast. It only switches on the scorecard (section 7).

Run:  python Integration/integrate.py
Then: python Integration/build_deck.py   (reads this script's outputs)
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)

TARGET = pd.Period("2026Q3", "Q")
BREAKAGE_Q2_2026 = 285                 # $M, added back (Traffic §8, Price §6)
RASM_GUIDE_PCT = (17.5, 19.5)          # Q3 2026 RASM YoY, Q2 2026 release
ASM_GUIDE_PCT = (-1.0, 0.0)            # Q3 2026 ASM YoY
RHO = -0.4                             # passenger/fare error correlation, Evaluation E9
N_DRAWS = 400_000
RNG = np.random.default_rng(20261021)

# Kalshi "Southwest Airlines average passenger fare in Q3" (KXLUV-26OCTFARE), the
# packet's market benchmark. Read from the public market page on Oct 20 2026 at
# about 9:30pm ET, before the form closes. Benchmark only: it does not enter the
# forecast. P(fare above threshold), as displayed under "Chance".
KALSHI = {"retrieved": "2026-10-20 ~21:30 ET",
          "url": "https://kalshi.com/markets/kxluv/southwest-airlines-kpi/kxluv-26octfare",
          "p_above": {225: 0.77, 230: 0.50, 235: 0.19}}

log_lines = []
def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log_lines.append(s)

def head(t):
    say("\n" + "=" * 78)
    say(t)
    say("=" * 78)


# =============================================================================
# 1. THE TWO HANDOFFS, AND EVALUATION'S VERDICT ON THEIR INTERVALS
# =============================================================================
head("1. COMBINE THE TWO FORECASTS")

tf = pd.read_csv(ROOT / "Traffic/outputs/forecast.csv").iloc[0]
pf = pd.read_csv(ROOT / "Price/outputs/forecast.csv").iloc[0]
rec = pd.read_csv(ROOT / "Evaluation/outputs/interval_recommendation.csv").set_index("series")
corr = pd.read_csv(ROOT / "Evaluation/outputs/error_correlation.csv")
base = pd.read_csv(ROOT / "Evaluation/outputs/baselines_q3_2026.csv")

pax_pt, fare_pt = float(tf["point"]), float(pf["point"])
# Points are the roles' own. Intervals follow Evaluation's harmonised rule (E3/E8):
# the delivered bands covered 50% (Traffic) and 93% (Price) of post-COVID quarters,
# because they were built on different samples and different t conventions.
pax_sd, fare_sd = rec.loc["Traffic M1", "sd_pct"], rec.loc["Price OOS blend", "sd_pct"]
pax_lo, pax_hi = rec.loc["Traffic M1", ["lo80", "hi80"]]
fare_lo, fare_hi = rec.loc["Price OOS blend", ["lo80", "hi80"]]
n_bt = int(rec.loc["Traffic M1", "n"])

say(f"Revenue passengers  point {pax_pt:,.0f}k   80% {pax_lo:,.0f} - {pax_hi:,.0f}"
    f"   (Traffic delivered {tf['lo80']:,.0f} - {tf['hi80']:,.0f})")
say(f"Average fare        point ${fare_pt:.2f}   80% ${fare_lo:.2f} - ${fare_hi:.2f}"
    f"   (Price delivered ${pf['lo80']:.2f} - ${pf['hi80']:.2f})")
say("Points are the roles' own. Intervals are Evaluation's harmonised 80% rule: error sd")
say(f"over the {n_bt} post-COVID backtest quarters, Student-t on {n_bt - 1} df rescaled to that sd.")
say(f"  passengers sd {pax_sd:.2f}%  ->  +/-{rec.loc['Traffic M1', 'half_width_pct']:.2f}%")
say(f"  fare       sd {fare_sd:.2f}%  ->  +/-{rec.loc['Price OOS blend', 'half_width_pct']:.2f}%")


# =============================================================================
# 2. THE PRODUCT -- passenger revenue, with an interval that respects how the
#    halves' errors move together
# =============================================================================
head("2. PASSENGER REVENUE = PASSENGERS x FARE")

def product_draws(sd_p, sd_f, rho, df=n_bt - 1, n=N_DRAWS):
    """Bivariate Student-t errors (shared chi-square), each rescaled to its sd."""
    cov = np.array([[1, rho], [rho, 1]])
    z = RNG.multivariate_normal([0, 0], cov, size=n)
    w = np.sqrt(RNG.chisquare(df, n) / df)
    e = z / w[:, None] * np.sqrt((df - 2) / df)
    pax = pax_pt * (1 + sd_p / 100 * e[:, 0])
    fare = fare_pt * (1 + sd_f / 100 * e[:, 1])
    return pax * fare / 1000                       # $M

rev_pt = pax_pt * fare_pt / 1000
draws = product_draws(pax_sd, fare_sd, RHO)
rev_lo, rev_hi = np.percentile(draws, [10, 90])
say(f"Point: {pax_pt:,.0f}k x ${fare_pt:.2f} = ${rev_pt:,.0f}M")
say(f"80% interval (rho = {RHO:+.1f}): ${rev_lo:,.0f}M - ${rev_hi:,.0f}M   "
    f"(+/-{(rev_hi - rev_lo) / 2 / rev_pt * 100:.1f}%)")

sens = []
for label, sp, sf, r in [
        (f"harmonised, rho {RHO:+.1f} [CHOSEN]", pax_sd, fare_sd, RHO),
        ("harmonised, rho 0 (independent)", pax_sd, fare_sd, 0.0),
        ("harmonised, rho -0.76 (current era only)", pax_sd, fare_sd, -0.76),
        ("roles' delivered widths, rho 0", None, None, 0.0)]:
    if sp is None:   # back out the sd each role's own band implies under this rule
        k = stats.t.ppf(0.9, n_bt - 1) * np.sqrt((n_bt - 3) / (n_bt - 1))
        sp = (tf["hi80"] - tf["lo80"]) / 2 / pax_pt * 100 / k
        sf = (pf["hi80"] - pf["lo80"]) / 2 / fare_pt * 100 / k
    d = product_draws(sp, sf, r)
    lo, hi = np.percentile(d, [10, 90])
    sens.append(dict(variant=label, lo80=lo, hi80=hi, half_width_pct=(hi - lo) / 2 / rev_pt * 100))
sens = pd.DataFrame(sens)
say("\nProduct interval sensitivity:")
say(sens.round(1).to_string(index=False))
prod_bt = rec.loc["Product", "half_width_pct"]
say(f"Cross-check: the product's own backtest errors (n={n_bt}) give +/-{prod_bt:.1f}%,"
    f" consistent with rho {RHO:+.1f}")
say("and tighter than independence. The offset is mechanical: the fare is revenue /")
say("passengers, so a passenger shortfall shows up as a fare overshoot (Evaluation E4/E9).")


# =============================================================================
# 3. THE GUIDANCE CHECK
# =============================================================================
head("3. CHECK AGAINST GUIDANCE")

sw = pd.read_csv(DATA / "southwest_quarterly_stats_2019Q1_2026Q2.csv")
sw.index = pd.PeriodIndex(sw["quarter"], freq="Q")
pr = sw["passenger_revenue_musd"].astype(float).copy()
orv = sw["operating_revenue_musd"].astype(float).copy()
pr_x, orv_x = pr.copy(), orv.copy()
pr_x["2026Q2"] += BREAKAGE_Q2_2026
orv_x["2026Q2"] += BREAKAGE_Q2_2026
ly = TARGET - 4

rasm_ly, asm_ly = sw.loc[ly, "rasm_cents"], sw.loc[ly, "asm_millions"]
asm_band = [asm_ly * (1 + g / 100) for g in ASM_GUIDE_PCT]
rasm_band = [rasm_ly * (1 + g / 100) for g in RASM_GUIDE_PCT]
oprev_band = [rasm_band[0] * asm_band[0] / 100, rasm_band[1] * asm_band[1] / 100]
say(f"Q3 2025 RASM {rasm_ly:.2f}c x (1 + {RASM_GUIDE_PCT[0]}..{RASM_GUIDE_PCT[1]}%) = "
    f"{rasm_band[0]:.2f}-{rasm_band[1]:.2f}c")
say(f"Q3 2025 ASMs {asm_ly:,.0f}M x (1 {ASM_GUIDE_PCT[0]:+.0f}..{ASM_GUIDE_PCT[1]:+.0f}%) = "
    f"{asm_band[0]:,.0f}-{asm_band[1]:,.0f}M")
say(f"Operating revenue implied by guidance: ${oprev_band[0]:,.0f}M - ${oprev_band[1]:,.0f}M")

# Passenger share of operating revenue. The packet uses a flat 92% (a Q2 number);
# Q3 runs seasonally lower, so also carry Q3 2025's share forward by Q2's YoY move.
share_q2 = pr_x["2026Q2"] / orv_x["2026Q2"]
share_seasonal = (pr[ly] / orv[ly]) * share_q2 / (pr["2025Q2"] / orv["2025Q2"])
bands = {"packet, 92% share": [x * 0.92 for x in oprev_band],
         f"seasonal, {share_seasonal:.2%} share": [x * share_seasonal for x in oprev_band]}
chk = []
for name, (lo, hi) in bands.items():
    chk.append(dict(band=name, lo=lo, hi=hi, team=rev_pt, inside=lo <= rev_pt <= hi,
                    position_in_band=(rev_pt - lo) / (hi - lo),
                    p_inside=((draws >= lo) & (draws <= hi)).mean(),
                    fare_implied_lo=lo / pax_pt * 1000, fare_implied_hi=hi / pax_pt * 1000,
                    pax_implied_lo=lo / fare_pt * 1000, pax_implied_hi=hi / fare_pt * 1000))
chk = pd.DataFrame(chk)
say("")
say(chk.round(3).to_string(index=False))
say(f"\nThe team's ${rev_pt:,.0f}M is INSIDE both bands. Read backwards: at our passenger count")
say(f"the band needs a fare of ${chk.loc[1, 'fare_implied_lo']:.2f}-${chk.loc[1, 'fare_implied_hi']:.2f} "
    f"(seasonal); at our fare it needs {chk.loc[1, 'pax_implied_lo']:,.0f}-{chk.loc[1, 'pax_implied_hi']:,.0f}k passengers.")
say(f"Only {chk.loc[1, 'p_inside']:.0%} of our product distribution falls inside the seasonal band:")
say("the guidance band is much narrower than our uncertainty about the product.")

asm_mid = np.mean(asm_band)
for name, sh in [("92%", 0.92), ("seasonal", share_seasonal)]:
    rasm_impl = rev_pt / sh / asm_mid * 100
    say(f"Implied RASM at {name} share and mid-guide ASMs: {rasm_impl:.2f}c, "
        f"{(rasm_impl / rasm_ly - 1) * 100:+.1f}% YoY (guide +{RASM_GUIDE_PCT[0]}% to +{RASM_GUIDE_PCT[1]}%)")


# =============================================================================
# 4. WHAT THE SPLIT TELLS YOU THAT THE BAND DOES NOT
# =============================================================================
head("4. THE SPLIT: WHERE THE BASELINES LAND AGAINST THE BAND")

seas_lo, seas_hi = bands[list(bands)[1]]
flat_lo, flat_hi = bands[list(bands)[0]]
pts = pd.DataFrame([
    dict(name="Team", pax=pax_pt, fare=fare_pt),
    dict(name="B0 same quarter last year", pax=base.iloc[0]["B0"], fare=base.iloc[1]["B0"]),
    dict(name="B1 packet (reported Q2 basis)", pax=base.iloc[0]["B1"], fare=base.iloc[1]["B1"]),
    dict(name="B1 ex-breakage Q2 basis", pax=base.iloc[0]["B1"], fare=base.iloc[2]["B1"]),
])
pts["revenue"] = pts["pax"] * pts["fare"] / 1000
pts["vs_seasonal_band"] = np.where(pts["revenue"] < seas_lo, "below",
                                   np.where(pts["revenue"] > seas_hi, "above", "inside"))
pts["vs_92pct_band"] = np.where(pts["revenue"] < flat_lo, "below",
                                np.where(pts["revenue"] > flat_hi, "above", "inside"))
say(pts.round(2).to_string(index=False))
pax_ly = base.iloc[0]["B0"]
flat_fares = [x / pax_ly * 1000 for x in (seas_lo, seas_hi)]
ours_fares = [x / pax_pt * 1000 for x in (seas_lo, seas_hi)]
say("\nNeither naive forecast lands in the band. B1 on the packet's basis is BELOW it")
say("(it carries the $285M one-off into the fare); B1 rebuilt ex-breakage is ABOVE it")
say("(it carries Q2's passenger decline but not the slower Q3 fare growth management")
say(f"guided to). The band admits flat passengers at ${flat_fares[0]:.0f}-{flat_fares[1]:.0f} or "
    f"{(pax_pt / pax_ly - 1) * 100:.1f}% passengers at ${ours_fares[0]:.0f}-{ours_fares[1]:.0f}:")
say("a volume story and a yield story. Our split says it is the yield story, and it says")
say("which half to blame if the print misses: the passenger count has the evidence")
say("behind it (Evaluation E1), the fare does not.")


# =============================================================================
# 5. THE MARKET'S VIEW -- Kalshi, benchmark only
# =============================================================================
head("5. MARKET BENCHMARK: KALSHI Q3 FARE CONTRACTS")

k = np.array(sorted(KALSHI["p_above"]))
p = np.array([KALSHI["p_above"][x] for x in k])
zq = stats.norm.ppf(1 - p)                       # threshold = mu + sigma * z
sigma_k, mu_k = np.polyfit(zq, k, 1)
kal_lo, kal_hi = mu_k + np.array([-1, 1]) * stats.norm.ppf(0.9) * sigma_k
say(f"Retrieved {KALSHI['retrieved']} from {KALSHI['url']}")
for x in k:
    say(f"  P(fare > ${x}) = {KALSHI['p_above'][x]:.0%}")
say(f"Normal fitted to the three prices: median ${mu_k:.2f}, sd ${sigma_k:.2f}, "
    f"80% ${kal_lo:.2f} - ${kal_hi:.2f}")
say(f"Ours: ${fare_pt:.2f}, 80% ${fare_lo:.2f} - ${fare_hi:.2f}.")
p_ours_above = {x: 1 - stats.t.cdf((x / fare_pt - 1) * 100 / (fare_sd * np.sqrt((n_bt - 3) / (n_bt - 1))),
                                   n_bt - 1) for x in k}
say("Our implied P(fare > threshold): "
    + ", ".join(f"${x}: {p_ours_above[x]:.0%}" for x in k))
say("The market and the model agree on the centre to within a dollar. The market is")
say(f"{(fare_hi - fare_lo) / (kal_hi - kal_lo):.1f}x more confident. Our band is sized on what our method's backtest")
say("errors were, and a one-off item in the print (Evaluation E7) is a real tail the")
say("market may be under-pricing.")


# =============================================================================
# 6. THE FORM
# =============================================================================
head("6. FORECAST FORM -- one submission per team, closes Oct 21 12:00 noon ET")

form = {
    "revenue_passengers_000": {"point": round(pax_pt), "lo80": round(pax_lo), "hi80": round(pax_hi)},
    "avg_passenger_fare_usd": {"point": round(fare_pt, 2), "lo80": round(fare_lo, 2),
                               "hi80": round(fare_hi, 2)},
    "implied_passenger_revenue_musd": {"point": round(rev_pt), "lo80": round(rev_lo),
                                       "hi80": round(rev_hi)},
    "share_price_oct22_close_usd": None,
}
say(f"  Revenue passengers (000s)      {form['revenue_passengers_000']['point']:,}   "
    f"80%: {form['revenue_passengers_000']['lo80']:,} - {form['revenue_passengers_000']['hi80']:,}")
say(f"  Average passenger fare ($)     {form['avg_passenger_fare_usd']['point']:.2f}   "
    f"80%: {form['avg_passenger_fare_usd']['lo80']:.2f} - {form['avg_passenger_fare_usd']['hi80']:.2f}")
say(f"  Implied passenger revenue ($M) {form['implied_passenger_revenue_musd']['point']:,}   "
    f"80%: {form['implied_passenger_revenue_musd']['lo80']:,} - {form['implied_passenger_revenue_musd']['hi80']:,}")
say("  Share price, Oct 22 close      not submitted (optional) -- see README §6")


# =============================================================================
# 7. SCORECARD -- only once actuals.json carries the reported figures
# =============================================================================
head("7. SCORECARD AGAINST THE PRINT")

act = json.loads((HERE / "actuals.json").read_text())
have = act.get("revenue_passengers_000") is not None and act.get("avg_passenger_fare_usd") is not None
score = pd.DataFrame()
decomp = {}
if not have:
    say("actuals.json has no reported figures yet (Southwest reports Oct 21 after the close).")
    say("Fill it from the Q3 2026 release and re-run this script and build_deck.py.")
else:
    a_pax, a_fare = float(act["revenue_passengers_000"]), float(act["avg_passenger_fare_usd"])
    a_rev = act.get("passenger_revenue_musd") or a_pax * a_fare / 1000
    rows = []
    for target, actual, team, lo, hi, b0, b1p, b1x, mkt in [
            ("revenue passengers (000s)", a_pax, pax_pt, pax_lo, pax_hi,
             base.iloc[0]["B0"], base.iloc[0]["B1"], base.iloc[0]["B1"], np.nan),
            ("average fare ($)", a_fare, fare_pt, fare_lo, fare_hi,
             base.iloc[1]["B0"], base.iloc[1]["B1"], base.iloc[2]["B1"], mu_k),
            ("passenger revenue ($M)", a_rev, rev_pt, rev_lo, rev_hi,
             base.iloc[3]["B0"], base.iloc[3]["B1"], base.iloc[4]["B1"], np.nan)]:
        rows.append(dict(target=target, actual=actual, team=team,
                         team_err_pct=(team / actual - 1) * 100,
                         in_80=lo <= actual <= hi,
                         B0_err_pct=(b0 / actual - 1) * 100,
                         B1_packet_err_pct=(b1p / actual - 1) * 100,
                         B1_exbreakage_err_pct=(b1x / actual - 1) * 100,
                         kalshi_err_pct=(mkt / actual - 1) * 100))
    score = pd.DataFrame(rows)
    say(score.round(2).to_string(index=False))
    say(f"\nPassenger revenue vs the guidance bands: "
        + ", ".join(f"{n}: {'inside' if lo <= a_rev <= hi else ('below' if a_rev < lo else 'above')}"
                    for n, (lo, hi) in bands.items()))

    # Why the passenger count missed: Traffic's identity, revpax = enplaned / trip
    # factor, splits the log error exactly into a boardings miss and a trip-factor miss.
    if act.get("enplaned_passengers_000") is not None:
        a_enp = float(act["enplaned_passengers_000"])
        tf_hat = float(tf["trip_factor"])
        f_enp = pax_pt * tf_hat
        a_tf = a_enp / a_pax
        decomp = {"enplaned_forecast": f_enp, "enplaned_actual": a_enp,
                  "trip_factor_forecast": tf_hat, "trip_factor_actual": a_tf,
                  "total_log_err_pct": np.log(pax_pt / a_pax) * 100,
                  "boardings_log_err_pct": np.log(f_enp / a_enp) * 100,
                  "trip_factor_log_err_pct": -np.log(tf_hat / a_tf) * 100}
        say(f"\nPassenger miss decomposed (log %): total {decomp['total_log_err_pct']:+.2f} = "
            f"boardings {decomp['boardings_log_err_pct']:+.2f} (TSA/T-100 chain) "
            f"+ trip factor {decomp['trip_factor_log_err_pct']:+.2f} (the accounting bridge)")
        say(f"  enplaned forecast {f_enp:,.0f}k vs actual {a_enp:,.0f}k; "
            f"trip factor {tf_hat:.4f} vs actual {a_tf:.4f}")
    say(f"\nProduct log error {np.log(rev_pt / a_rev) * 100:+.2f}% = passengers "
        f"{np.log(pax_pt / a_pax) * 100:+.2f} + fare {np.log(fare_pt / a_fare) * 100:+.2f}"
        + (f" + revenue/(pax x fare) gap {np.log(a_pax * a_fare / 1000 / a_rev) * 100:+.2f}"
           if act.get("passenger_revenue_musd") else ""))


# =============================================================================
# 8. SAVE -- everything build_deck.py needs
# =============================================================================
summary = {
    "form": form,
    "pax": {"point": pax_pt, "lo80": pax_lo, "hi80": pax_hi, "sd_pct": pax_sd,
            "delivered_lo80": float(tf["lo80"]), "delivered_hi80": float(tf["hi80"]),
            "yoy_pct": float(tf["yoy_pct"]), "trip_factor": float(tf["trip_factor"]),
            "M1": float(tf["M1"]), "M2": float(tf["M2"]), "M3": float(tf["M3_benchmark"])},
    "fare": {"point": fare_pt, "lo80": fare_lo, "hi80": fare_hi, "sd_pct": fare_sd,
             "delivered_lo80": float(pf["lo80"]), "delivered_hi80": float(pf["hi80"]),
             "yoy_pct": float(pf["yoy_pct"]),
             "P1": float(pf["P1"]), "P2": float(pf["P2"]), "P3": float(pf["P3"])},
    "revenue": {"point": rev_pt, "lo80": rev_lo, "hi80": rev_hi, "rho": RHO},
    "guidance": {"oprev_lo": oprev_band[0], "oprev_hi": oprev_band[1],
                 "share_seasonal": share_seasonal,
                 "band_92_lo": flat_lo, "band_92_hi": flat_hi,
                 "band_seasonal_lo": seas_lo, "band_seasonal_hi": seas_hi,
                 "p_inside_seasonal": float(chk.loc[1, "p_inside"])},
    "baselines": pts.to_dict(orient="records"),
    "kalshi": {**{k_: v for k_, v in KALSHI.items() if k_ != "p_above"},
               "p_above": {str(x): v for x, v in KALSHI["p_above"].items()},
               "median": mu_k, "sd": sigma_k, "lo80": kal_lo, "hi80": kal_hi},
    "actuals": act if have else None,
    "decomposition": decomp or None,
}
(OUT / "integration_summary.json").write_text(json.dumps(summary, indent=2, default=float))
chk.round(4).to_csv(OUT / "guidance_check.csv", index=False)
sens.round(2).to_csv(OUT / "product_interval_sensitivity.csv", index=False)
pts.round(2).to_csv(OUT / "split_vs_band.csv", index=False)
if have:
    score.round(3).to_csv(OUT / "scorecard.csv", index=False)
else:
    (OUT / "scorecard.csv").unlink(missing_ok=True)     # never leave a stale scorecard

form_md = f"""# Forecast form — Southwest Q3 2026 (one submission per team)

Generated by `Integration/integrate.py`. **Closes Oct 21 2026, 12:00 noon ET.**

| Field | Point | 80% interval |
|---|---|---|
| Revenue passengers carried (000s) | **{form['revenue_passengers_000']['point']:,}** | {form['revenue_passengers_000']['lo80']:,} – {form['revenue_passengers_000']['hi80']:,} |
| Average passenger fare ($) | **{form['avg_passenger_fare_usd']['point']:.2f}** | {form['avg_passenger_fare_usd']['lo80']:.2f} – {form['avg_passenger_fare_usd']['hi80']:.2f} |
| Implied passenger revenue ($M) | **{form['implied_passenger_revenue_musd']['point']:,}** | {form['implied_passenger_revenue_musd']['lo80']:,} – {form['implied_passenger_revenue_musd']['hi80']:,} |
| Share price, Oct 22 close (optional) | not submitted | — |

Guidance check: implied passenger revenue is inside the guided band on both the packet's 92% share
(${flat_lo:,.0f}M – ${flat_hi:,.0f}M) and the seasonal {share_seasonal:.2%} share
(${seas_lo:,.0f}M – ${seas_hi:,.0f}M).
"""
(OUT / "form.md").write_text(form_md)

(OUT / "run_log.txt").write_text("\n".join(log_lines) + "\n")
say(f"\nwrote {len(list(OUT.iterdir()))} files to {OUT}")
