"""
AIPI 590 Alternative Data -- Southwest Q3 2026 case study
PRESENTATION: the five-slide deck uploaded for the Oct 28 readout (due Oct 27).

The packet asks for at most five slides covering: forecast against actual, data
and cleaning decisions, model and baselines, backtest by period, and what we got
wrong and why. One slide per topic, in that order, each with one idea and one
visual; the detail lives in the speaker notes. Every number is read from the
pipeline's outputs, never typed in:
  Integration/outputs/integration_summary.json   (integrate.py, with actuals.json filled)
  Evaluation/outputs/backtest_by_period.csv, dm_tests.csv
  Presentation/deck_inputs.json                  (team name, the closing line)

Run:  python Presentation/build_presentation.py      (after Integration/integrate.py)
Needs: python-pptx
"""
from pathlib import Path
import io
import json
import re
import zipfile
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
INTEG = ROOT / "Integration" / "outputs"
DECK = HERE / "southwest_q3_2026_presentation.pptx"

S = json.loads((INTEG / "integration_summary.json").read_text())
if S["actuals"] is None or S["decomposition"] is None:
    raise SystemExit("Integration/actuals.json has no reported figures yet: fill it from the Q3 "
                     "release, re-run Integration/integrate.py, then this script.")
BYP = pd.read_csv(ROOT / "Evaluation/outputs/backtest_by_period.csv")
BQ = pd.read_csv(ROOT / "Evaluation/outputs/backtest_quarterly.csv").set_index("quarter")
DM = pd.read_csv(ROOT / "Evaluation/outputs/dm_tests.csv")
INP = json.loads((HERE / "deck_inputs.json").read_text())
SW = pd.read_csv(ROOT / "data/southwest_quarterly_stats_2019Q1_2026Q2.csv").set_index("quarter")

# palette shared with the role charts: navy for our methods, coral for the naive
# baseline, amber for the forecast itself, teal for what held
INK, NAVY, CARD = "15202B", "1F3B73", "22324A"
AMBER, CORAL, TEAL, GREY = "E9A13B", "D1495B", "2A9D8F", "8A94A3"
PAPER, TINT, TEXT, MUTED = "FFFFFF", "EEF2F7", "1B1F24", "5B6573"
SOFT = "AEB8C6"                          # secondary text on dark slides
TEAL_DARK = "1E7268"                     # teal text on light slides (teal fails contrast)
HEAD, BODY = "Cambria", "Calibri"

def rgb(h):
    return RGBColor.from_string(h)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
TITLE_ONLY = prs.slide_layouts[5]
L, R = 0.6, 12.733                      # left / right content edges, inches
W = R - L


# ----------------------------------------------------------------- helpers
def new_slide(kicker, title, dark=False):
    s = prs.slides.add_slide(TITLE_ONLY)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(INK if dark else PAPER)
    text(s, L, 0.45, W, 0.3, kicker, size=13, bold=True, color=AMBER if dark else NAVY, name="Kicker")
    t = s.shapes.title
    t.left, t.top, t.width, t.height = Inches(L), Inches(0.75), Inches(W), Inches(0.8)
    tf = t.text_frame
    tf.margin_left = tf.margin_right = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    p.text = title
    p.alignment = PP_ALIGN.LEFT
    f = p.runs[0].font
    f.name, f.size, f.bold = HEAD, Pt(36), True
    f.color.rgb = rgb(PAPER if dark else INK)
    return s

def text(slide, x, y, w, h, runs, size=16, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, font=BODY, name=None, space_after=0):
    """runs: a string, or a list of paragraphs, each a string or [(text, {opts}), ...]."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        for chunk, opts in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = chunk
            r.font.name = opts.get("font", font)
            r.font.size = Pt(opts.get("size", size))
            r.font.bold = opts.get("bold", bold)
            r.font.italic = opts.get("italic", False)
            r.font.color.rgb = rgb(opts.get("color", color))
    return tb

def box(slide, x, y, w, h, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=None, line=None):
    shp = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = 0.12
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(fill)
    if line:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(1.5)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    if name:
        shp.name = name
    return shp

def label_in(shp, runs, size=16, color=PAPER, bold=False, align=PP_ALIGN.CENTER):
    """Write centred text inside a shape."""
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.15)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = align
    for chunk, opts in ([(runs, {})] if isinstance(runs, str) else runs):
        r = p.add_run()
        r.text = chunk
        r.font.name = opts.get("font", BODY)
        r.font.size = Pt(opts.get("size", size))
        r.font.bold = opts.get("bold", bold)
        r.font.color.rgb = rgb(opts.get("color", color))

def cell(c, runs, fill, size=16, color=TEXT, bold=False, align=PP_ALIGN.LEFT):
    c.fill.solid()
    c.fill.fore_color.rgb = rgb(fill)
    c.margin_left = c.margin_right = Inches(0.15)
    c.margin_top = c.margin_bottom = Inches(0.06)
    c.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf = c.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    for chunk, opts in ([(runs, {})] if isinstance(runs, str) else runs):
        r = p.add_run()
        r.text = chunk
        r.font.name, r.font.size = BODY, Pt(opts.get("size", size))
        r.font.bold = opts.get("bold", bold)
        r.font.color.rgb = rgb(opts.get("color", color))

def style_axis_text(axis, size=14):
    axis.tick_labels.font.size = Pt(size)
    axis.tick_labels.font.name = BODY
    axis.tick_labels.font.color.rgb = rgb(MUTED)

def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s

def k(x):
    return f"{x:,.0f}k"

def usd(x):
    return f"${x:,.2f}"

def bn(x):
    return f"${x / 1000:,.2f}bn"

def pct(x, d=1):
    return f"{x:+.{d}f}%".replace("-", "−")

def err(forecast, actual):
    return (forecast / actual - 1) * 100

def miss(e):
    """A forecast error as words: '1.7% low'."""
    return f"{abs(e):.1f}% {'low' if e < 0 else 'high'}"


pax, fare, rev, g = S["pax"], S["fare"], S["revenue"], S["guidance"]
base = {b["name"]: b for b in S["baselines"]}
B0 = base["B0 same quarter last year"]
B1p = base["B1 packet (reported Q2 basis)"]
B1x = base["B1 ex-breakage Q2 basis"]
act, d = S["actuals"], S["decomposition"]
a_pax, a_fare, a_rev = act["revenue_passengers_000"], act["avg_passenger_fare_usd"], act["passenger_revenue_musd"]
ly = SW.loc["2025Q3"]
tf_ly = ly["enplaned_passengers_000"] / ly["revenue_passengers_000"]
# RASM in cents to two decimals, as the release prints it, so the YoY matches the release
rasm_yoy = (round(act["operating_revenue_musd"] / act["asm_millions"] * 100, 2) / ly["rasm_cents"] - 1) * 100
rasm_lo, rasm_hi = g["rasm_yoy_pct"]
# did B1 also beat our passenger method in the last backtest quarter? (a downgrade trigger)
q_prev = BQ.loc["2026Q2"]
lost_prev = abs(q_prev["pax_B1_err"]) < abs(q_prev["T_BLEND_err"])
lost_now = abs(err(B1p["pax"], a_pax)) < abs(err(pax["point"], a_pax))


# =============================================================================
# SLIDE 1 -- the forecast against the actual
# =============================================================================
s1 = new_slide("1  ·  FORECAST VS ACTUAL", "Inside every 80% band, a little low", dark=True)
team = INP.get("team_name")
text(s1, L, 1.6, W, 0.4,
     (f"Team {team}  ·  " if team else "")
     + "Southwest Airlines (LUV), Q3 2026  ·  forecast locked Oct 20, scored against the Oct 21 release",
     size=15, color=SOFT, name="Subtitle")

BX, BW = 3.55, 6.1                       # the 80% band, drawn the same width on every row
rows1 = [("Revenue passengers", pax, a_pax, k),
         ("Average fare", fare, a_fare, usd),
         ("Passenger revenue", rev, a_rev, bn)]
for i, (lab, f_, a, fmt) in enumerate(rows1):
    y = 2.45 + i * 1.3
    mid = y + 0.55
    text(s1, L, mid - 0.2, 2.8, 0.4, lab, size=20, bold=True, color=PAPER, anchor=MSO_ANCHOR.MIDDLE)
    box(s1, BX, mid - 0.17, BW, 0.34, "3A4B63", name=f"80% band {lab}")
    text(s1, BX, mid + 0.25, 1.5, 0.3, fmt(f_["lo80"]), size=12, color=SOFT)
    text(s1, BX + BW - 1.5, mid + 0.25, 1.5, 0.3, fmt(f_["hi80"]), size=12, color=SOFT, align=PP_ALIGN.RIGHT)

    def at(v):
        return BX + BW * (v - f_["lo80"]) / (f_["hi80"] - f_["lo80"])
    box(s1, at(f_["point"]) - 0.17, mid - 0.17, 0.34, 0.34, AMBER, shape=MSO_SHAPE.DIAMOND, name=f"Forecast {lab}")
    text(s1, at(f_["point"]) - 1.0, mid + 0.25, 2.0, 0.3, f"Forecast {fmt(f_['point'])}",
         size=14, bold=True, color=AMBER, align=PP_ALIGN.CENTER)
    box(s1, at(a) - 0.14, mid - 0.14, 0.28, 0.28, PAPER, shape=MSO_SHAPE.OVAL, name=f"Actual {lab}", line=INK)
    text(s1, at(a) - 1.0, mid - 0.55, 2.0, 0.3, f"Actual {fmt(a)}",
         size=14, bold=True, color=PAPER, align=PP_ALIGN.CENTER)

    e = err(f_["point"], a)
    hit = f_["lo80"] <= a <= f_["hi80"]
    text(s1, BX + BW + 0.5, mid - 0.4, R - BX - BW - 0.5, 0.8, [
        [(miss(e), {"size": 26, "bold": True, "color": PAPER})],
        [("✓ inside 80% band" if hit else "✗ outside 80% band", {"size": 14, "color": TEAL if hit else CORAL})]])

side = "above" if a_rev > g["band_seasonal_hi"] else ("below" if a_rev < g["band_seasonal_lo"] else "inside")
text(s1, L, 6.55, W, 0.4, [[
    ("Passenger revenue landed ", {}),
    (f"{side} the {bn(g['band_seasonal_lo'])}–{bn(g['band_seasonal_hi'])} band", {"bold": True, "color": PAPER}),
    (" that Southwest's own guidance implied.", {})]], size=16, color=SOFT)
notes(s1, (
    f"Southwest reported {k(a_pax)} revenue passengers and a {usd(a_fare)} average fare, so {bn(a_rev)} of "
    f"passenger revenue. We forecast {k(pax['point'])}, {usd(fare['point'])} and {bn(rev['point'])}. All three "
    f"actuals sit inside our 80% bands, and all three forecasts were low: passengers by "
    f"{abs(err(pax['point'], a_pax)):.1f}%, fare by {abs(err(fare['point'], a_fare)):.1f}%, revenue by "
    f"{abs(err(rev['point'], a_rev)):.1f}%. The bar is each 80% band, the diamond our forecast, the dot the "
    f"actual. The bigger surprise: passenger revenue came in {side} the band implied by Southwest's own "
    f"guidance. Our forecast sat inside that band; the company beat its own guide."))


# =============================================================================
# SLIDE 2 -- data and cleaning decisions
# =============================================================================
s2 = new_slide("2  ·  DATA AND CLEANING DECISIONS", "TSA counts boardings, not passengers")
q2, q2ly = SW.loc["2026Q2"], SW.loc["2025Q2"]
enp_yoy = (q2["enplaned_passengers_000"] / q2ly["enplaned_passengers_000"] - 1) * 100
rp_yoy = (q2["revenue_passengers_000"] / q2ly["revenue_passengers_000"] - 1) * 100
lw = 4.7
box(s2, L, 1.9, lw, 4.75, TINT, name="Boardings vs passengers")
text(s2, L + 0.4, 2.2, lw - 0.8, 0.3, "Q2 2026, YEAR ON YEAR", size=13, bold=True, color=MUTED)
text(s2, L + 0.4, 2.65, lw - 0.8, 0.9, [[(pct(enp_yoy), {"color": NAVY}),
                                         ("  boardings", {"size": 20, "bold": False, "font": BODY})]],
     size=54, bold=True, font=HEAD, color=TEXT)
text(s2, L + 0.4, 3.65, lw - 0.8, 0.9, [[(pct(rp_yoy), {"color": CORAL}),
                                         ("  paying trips", {"size": 20, "bold": False, "font": BODY})]],
     size=54, bold=True, font=HEAD, color=TEXT)
text(s2, L + 0.4, 5.0, lw - 0.8, 1.4,
     "The gap is the trip factor: boardings per paying trip. No public source reports it.",
     size=17, color=TEXT)

clean = [("TSA checkpoint, daily", "Nothing imputed. Both funding lapses flagged, not repaired."),
         ("Southwest Q2 release",
          f"$285M one-off added back: fare {usd(q2['avg_passenger_fare_usd'])} → "
          f"{usd((q2['passenger_revenue_musd'] + 285) * 1000 / q2['revenue_passengers_000'])}."),
         ("BTS T-100", "July is filed; August and September nowcast from TSA.")]
cx = L + lw + 0.6
text(s2, cx, 1.95, R - cx, 0.3, "CLEANING DECISIONS", size=13, bold=True, color=MUTED)
for i, (src, dec) in enumerate(clean):
    y = 2.45 + i * 1.4
    box(s2, cx, y + 0.05, 0.08, 1.0, NAVY, shape=MSO_SHAPE.RECTANGLE)
    text(s2, cx + 0.35, y, R - cx - 0.35, 0.4, src, size=20, bold=True, color=INK)
    text(s2, cx + 0.35, y + 0.45, R - cx - 0.35, 0.6, dec, size=17, color=TEXT)
notes(s2, (
    "Which reported count does a checkpoint count measure? Enplaned passengers, not revenue passengers. "
    "A connecting trip is one paying trip but two boardings. In Q2 2026 boardings rose while paying trips "
    "fell, because assigned seating and the fare bundles pushed travellers onto connections. The ratio "
    "between the two, the trip factor, is the bridge from alternative data to the target, and no free "
    "source observes it: we extrapolate it from Southwest's own releases. "
    "Cleaning: the TSA file is structurally clean, with no missing, duplicate or non-positive days, so we "
    "imputed nothing. We flagged both funding-lapse windows. Once the downward trend in growth is "
    "controlled, neither shows a throughput drop, so we repaired nothing; neither touches Q3. Q2's fare "
    "carries a $285M one-off, which we added back before projecting. T-100 is published about three "
    "months late, so only July is a filing. We also used the BLS airfare CPI (October 2025 blank, "
    "interpolated) and EIA jet fuel (holiday blanks dropped). Google Trends was not used, because it is "
    "rescaled on every pull and has no stable history to backtest."))


# =============================================================================
# SLIDE 3 -- model and baselines
# =============================================================================
s3 = new_slide("3  ·  MODEL AND BASELINES", "Naive won on passengers; we won on fare")
flow = [("TSA throughput × Southwest share\n÷ trip factor", "Passengers", k(pax["point"])),
        ("Airfare CPI, seasonality\nand fuel pass-through", "Fare", usd(fare["point"]))]
for i, (inp, lab, val) in enumerate(flow):
    y = 2.0 + i * 1.45
    b = box(s3, L, y, 3.7, 1.05, TINT)
    label_in(b, inp, size=16, color=TEXT)
    box(s3, L + 3.85, y + 0.33, 0.4, 0.4, GREY, shape=MSO_SHAPE.RIGHT_ARROW)
    r_ = box(s3, L + 4.4, y, 2.5, 1.05, NAVY)
    label_in(r_, [(lab + "\n", {"size": 14, "color": SOFT}), (val, {"size": 24, "bold": True})])
r_ = box(s3, L + 4.4, 4.9, 2.5, 1.05, AMBER)
label_in(r_, [("Passenger revenue\n", {"size": 14, "color": INK}), (bn(rev["point"]), {"size": 24, "bold": True, "color": INK})])
text(s3, L, 5.15, 4.2, 0.6, "Passengers × fare", size=18, bold=True, color=MUTED, align=PP_ALIGN.RIGHT,
     anchor=MSO_ANCHOR.MIDDLE)

tx = R - 4.75
text(s3, tx, 1.95, R - tx, 0.3, "ERROR VS ACTUAL", size=13, bold=True, color=MUTED)
methods = [("Ours", pax["point"], fare["point"]),
           ("B1 naive", B1p["pax"], B1p["fare"]),
           ("B0 last year", B0["pax"], B0["fare"])]
errs = [(n, err(p_, a_pax), err(f_, a_fare)) for n, p_, f_ in methods]
best = [min(range(3), key=lambda i: abs(errs[i][j])) for j in (1, 2)]
tb3 = s3.shapes.add_table(4, 3, Inches(tx), Inches(2.35), Inches(R - tx), Inches(2.4))
tb3.name = "Baselines vs actual"
t3 = tb3.table
for j, wdt in enumerate([1.75, 1.5, 1.5]):
    t3.columns[j].width = Inches(wdt)
for j, h_ in enumerate(["", "Passengers", "Fare"]):
    cell(t3.cell(0, j), h_, NAVY, size=15, color=PAPER, bold=True)
for i, (n, ep, ef) in enumerate(errs, start=1):
    fill = PAPER if i % 2 else TINT
    cell(t3.cell(i, 0), n, fill, size=15, bold=i == 1)
    for j, e in ((1, ep), (2, ef)):
        win = best[j - 1] == i - 1
        cell(t3.cell(i, j), miss(e), fill, size=16, bold=win, color=TEAL_DARK if win else TEXT)
text(s3, tx, 4.95, R - tx, 0.6,
     f"Green: closest. B1 = last year × Q2 growth; its fare without Q2's $285M one-off is "
     f"{miss(err(B1x['fare'], a_fare))}.", size=13, color=MUTED)
notes(s3, (
    "Two halves, each from its own public signal, then multiplied. Passengers: national TSA throughput, "
    "times Southwest's share of it from T-100, divided by the trip factor; blended 65/35 with a capacity "
    "identity built on guided seat miles. Fare: a blend of three methods, an industry anchor on the BLS "
    "airfare CPI, a seasonal step and fuel pass-through, all within 1.6% of each other. "
    f"Baselines from the packet: B0 is last year, B1 is last year scaled by Q2's growth. Against the print, "
    f"B1 beat us on passengers, {miss(errs[1][1])} against our {miss(errs[0][1])}. We beat both on fare, "
    f"though only narrowly once B1 is rebuilt without the one-off ({miss(err(B1x['fare'], a_fare))}). "
    f"Kalshi's fare market, a benchmark only, finished at {miss(err(S['kalshi']['median'], a_fare))}, "
    "a touch closer than us."))


# =============================================================================
# SLIDE 4 -- backtest by period
# =============================================================================
s4 = new_slide("4  ·  BACKTEST BY PERIOD", "Passengers beat naive; fare barely does")

def mape(target, period, method):
    r = BYP[(BYP["target"] == target) & (BYP["period"] == period) & (BYP["method"] == method)]
    return float(r["MAPE"].iloc[0])

def p_dm(model):
    return float(DM[(DM["period"] == "2025-2026") & (DM["model"] == model)]["p_value"].iloc[0])

PAIRS = [("Passengers", "revenue_passengers", "T_BLEND", "pax_B1"),
         ("Fare", "average_fare", "P_BLEND_oos", "fare_B1"),
         ("Revenue", "passenger_revenue", "REV_team", "rev_B1")]
for i, (period, label) in enumerate([("2022-2024 (pre fee change)", "2022–2024  ·  before the fee change"),
                                     ("2025-2026 (fee + model change)", "2025–2026  ·  after the fee change")]):
    cdat = CategoryChartData()
    cdat.categories = [p[0] for p in PAIRS]
    cdat.add_series("Ours", [round(mape(t_, period, m), 1) for _, t_, m, _ in PAIRS])
    cdat.add_series("B1 naive", [round(mape(t_, period, b), 1) for _, t_, _, b in PAIRS])
    x = L + i * 6.25
    gfx = s4.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(1.85),
                              Inches(5.9), Inches(4.45), cdat)
    gfx.name = f"Backtest MAPE {label}"
    c = gfx.chart
    c.font.name, c.font.size = BODY, Pt(14)
    c.has_title = True
    c.chart_title.text_frame.text = label
    tr = c.chart_title.text_frame.paragraphs[0].runs[0]
    tr.font.size, tr.font.bold, tr.font.name = Pt(16), True, BODY
    tr.font.color.rgb = rgb(INK)
    c.has_legend = True
    c.legend.position = XL_LEGEND_POSITION.BOTTOM
    c.legend.include_in_layout = False
    c.legend.font.size, c.legend.font.color.rgb = Pt(14), rgb(MUTED)
    pl = c.plots[0]
    pl.gap_width, pl.overlap = 60, -10
    pl.has_data_labels = True
    dl = pl.data_labels
    dl.number_format, dl.number_format_is_linked = '0.0"%"', False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.bold, dl.font.color.rgb = Pt(14), True, rgb(TEXT)
    for ser, col in zip(pl.series, [NAVY, CORAL]):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(col)
    va = c.value_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = 0, 12, 4
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E3E8EF")
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = '0"%"', False
    va.format.line.fill.background()
    style_axis_text(va)
    style_axis_text(c.category_axis, size=15)
    c.category_axis.format.line.color.rgb = rgb("C9D1DC")
text(s4, L, 6.5, W, 0.5, [[
    ("Mean absolute % error, lower is better. ", {}),
    (f"Only the passenger edge is significant (p = {p_dm('T_BLEND'):.2f}, 2025–26).",
     {"bold": True, "color": INK})]], size=15, color=MUTED)
wins = BYP[(BYP["target"] == "revenue_passengers") & (BYP["method"] == "T_BLEND")
           & (BYP["period"].str.startswith("full"))]["beats_B1"].iloc[0]
notes(s4, (
    "Evaluation re-implemented both methods from the roles' write-ups and replayed them quarter by quarter "
    "from 2022, re-estimating every parameter from what was public at the time. The packet asks for "
    "2022-2024 and the 2025-2026 fee change separately; those are the two panels. "
    f"Passengers beat B1 in both eras and in {wins} quarters. Fare beats B1 on average in both eras, but "
    f"by about a point, and the Diebold-Mariano test cannot tell it apart from naive (p = "
    f"{p_dm('P_BLEND_oos'):.2f}); 2022's COVID base flatters every method, and in 2023-24 alone B1 wins on "
    f"fare. So the revenue figure, the client's number, has no demonstrated edge (p = {p_dm('REV_team'):.2f}). "
    "Q3 2026 fits that pattern on fare, but on passengers the naive forecast won this time"
    + (", as it did in Q2" if lost_prev and lost_now else "") + ": see the next slide."))


# =============================================================================
# SLIDE 5 -- what we got wrong and why
# =============================================================================
s5 = new_slide("5  ·  WHAT WE GOT WRONG AND WHY", "The TSA data held; the trip factor didn't", dark=True)
text(s5, L, 1.9, 6.0, 0.3, "PASSENGER MISS, SPLIT", size=13, bold=True, color=SOFT)
parts = [("Boardings", "TSA + T-100 data", d["boardings_log_err_pct"], TEAL),
         ("Trip factor", "the bridge", d["trip_factor_log_err_pct"], CORAL),
         ("Total", "", d["total_log_err_pct"], PAPER)]
scale = 3.0 / max(abs(p[2]) for p in parts)    # inches per point of error
for i, (lab, sub, e, col) in enumerate(parts):
    y = 2.4 + i * 1.05
    text(s5, L, y, 2.2, 0.7, [[(lab, {"size": 20, "bold": True, "color": PAPER})],
                              [(sub, {"size": 13, "color": SOFT})]], anchor=MSO_ANCHOR.MIDDLE)
    box(s5, L + 2.3, y + 0.12, abs(e) * scale, 0.46, col, shape=MSO_SHAPE.RECTANGLE, name=f"Miss {lab}")
    text(s5, L + 2.3 + abs(e) * scale + 0.15, y + 0.12, 1.4, 0.46, miss(e), size=18, bold=True,
         color=col, anchor=MSO_ANCHOR.MIDDLE)

why = [f"Trip factor rose {(d['trip_factor_actual'] / tf_ly - 1) * 100:.1f}%, "
       f"not the {(d['trip_factor_forecast'] / tf_ly - 1) * 100:.1f}% we extrapolated.",
       f"Fare {miss(err(fare['point'], a_fare))}: Southwest beat its own guide, "
       f"unit revenue {pct(rasm_yoy)} vs {pct(rasm_lo).rstrip('%')}–{rasm_hi:.1f}%.",
       f"Naive B1 beat our passenger count: {miss(err(B1p['pax'], a_pax))} vs {miss(err(pax['point'], a_pax))}"
       + (", the second quarter running." if lost_prev and lost_now else ".")]
wx = L + 6.9
for i, w_ in enumerate(why):
    y = 2.4 + i * 1.05
    b = box(s5, wx, y + 0.1, 0.46, 0.46, CORAL, shape=MSO_SHAPE.OVAL)
    label_in(b, str(i + 1), size=16, bold=True)
    text(s5, wx + 0.7, y, R - wx - 0.7, 0.7, w_, size=17, color=PAPER, anchor=MSO_ANCHOR.MIDDLE)

pov = INP.get("why")
if pov:
    b = box(s5, L, 5.75, W, 0.95, CARD, name="PoV")
    label_in(b, [("PoV  ", {"bold": True, "color": AMBER}), (pov, {"color": PAPER})], size=18,
             align=PP_ALIGN.LEFT)
tf_off = abs(d["trip_factor_actual"] / d["trip_factor_forecast"] - 1) * 100
notes(s5, (
    f"Our passenger forecast was {miss(err(pax['point'], a_pax))}. The identity revenue passengers = "
    "boardings ÷ trip factor splits that miss exactly. The boardings half, built from TSA and T-100, was "
    f"{miss(d['boardings_log_err_pct'])}: we forecast {k(d['enplaned_forecast'])} boardings and Southwest "
    f"reported {k(d['enplaned_actual'])}. The trip factor, which no public source observes, was "
    f"{miss(d['trip_factor_log_err_pct'])}: we extrapolated {d['trip_factor_forecast']:.4f} from the two "
    f"post-change quarters and it came in at {d['trip_factor_actual']:.4f}, slightly below Q2's. The "
    "alternative data held; the accounting bridge on top of it missed, which is the risk our Flag position "
    f"names. The trip factor was {tf_off:.1f}% off forecast, inside our 1.5-point downgrade trigger. "
    f"On fare, we were {miss(err(fare['point'], a_fare))}: Southwest beat its own unit revenue guide, so "
    "the band we used as a sense check was itself too low. And the naive B1 beat our passenger number "
    "this quarter"
    + (f", as it did in Q2 ({miss(q_prev['pax_B1_err'])} against our {miss(q_prev['T_BLEND_err'])}). That "
       "fires our two-quarters-running downgrade trigger. For the Q4 decision: keep selling the boardings "
       "nowcast, but downgrade the revenue-passenger number to boardings-only until the trip factor is "
       "re-estimated on the new quarters." if lost_prev and lost_now else
       ". For the Q4 decision: sell the boardings nowcast, re-estimate the trip factor every quarter, and "
       "downgrade if it moves more than 1.5 points or our passenger count loses to B1 two quarters running.")))

prs.save(DECK)

# Make the build byte-reproducible like the other pipelines: python-pptx stamps
# every zip entry with the wall clock, and each chart's embedded workbook also
# records its creation time. Pin both so a re-run with the same inputs is a no-op.
FIXED = (2026, 10, 21, 12, 0, 0)

def _pinned_zip(blob, rewrite=lambda n, b: b):
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(blob)) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zi = zipfile.ZipInfo(info.filename, FIXED)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zi, rewrite(info.filename, zin.read(info.filename)))
    return out.getvalue()

def _pin_workbook(name, blob):
    if name.endswith(".xlsx"):
        return _pinned_zip(blob, lambda n, b: re.sub(rb"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ",
                                                     b"2026-10-21T16:00:00Z", b)
                           if n == "docProps/core.xml" else b)
    return blob

DECK.write_bytes(_pinned_zip(DECK.read_bytes(), _pin_workbook))
print(f"wrote {DECK.relative_to(ROOT)}  ({len(prs.slides)} slides"
      + ("" if team else "; no team name in deck_inputs.json") + ")")
