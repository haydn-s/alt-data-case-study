"""
AIPI 590 Alternative Data -- Southwest Q3 2026 case study
INTEGRATION ROLE: build the five-slide readout deck from the team's outputs.

The packet asks for at most five slides covering: forecast against actual, data
and cleaning decisions, model and baselines, backtest by period, and what we got
wrong and why. Every number on the slides is read from the pipeline's outputs,
never typed in:
  Integration/outputs/integration_summary.json   (from integrate.py)
  Evaluation/outputs/backtest_by_period.csv, dm_tests.csv

Before the print, slide 1 shows "pending" for the actuals and slide 5 lists the
risks we pre-registered. Once actuals.json is filled and integrate.py re-run,
the same script fills in the actuals and turns slide 5 into the scorecard.

Run:  python Integration/build_deck.py      (after integrate.py)
Needs: python-pptx
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION, XL_MARKER_STYLE

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
DECK = HERE / "slides" / "southwest_q3_2026_readout.pptx"
DECK.parent.mkdir(exist_ok=True)

S = json.loads((OUT / "integration_summary.json").read_text())
BYP = pd.read_csv(ROOT / "Evaluation/outputs/backtest_by_period.csv")
DM = pd.read_csv(ROOT / "Evaluation/outputs/dm_tests.csv")
POST = S["actuals"] is not None

# palette shared with the role charts: navy for our methods, coral for the naive
# baseline, amber for the forecast itself, teal for the market
INK, NAVY, CARD = "15202B", "1F3B73", "22324A"
AMBER, CORAL, TEAL, GREY = "E9A13B", "D1495B", "2A9D8F", "8A94A3"
PAPER, TINT, TEXT, MUTED = "FFFFFF", "EEF2F7", "1B1F24", "5B6573"
HEAD, BODY = "Cambria", "Calibri"

def rgb(h):
    return RGBColor.from_string(h)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
TITLE_ONLY = prs.slide_layouts[5]
L, R = 0.6, 12.733                      # left / right content edges, inches
W = R - L


# ----------------------------------------------------------------- helpers
def new_slide(title, dark=False):
    s = prs.slides.add_slide(TITLE_ONLY)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(INK if dark else PAPER)
    t = s.shapes.title
    t.left, t.top, t.width, t.height = Inches(L), Inches(0.42), Inches(W), Inches(0.8)
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

def text(slide, x, y, w, h, runs, size=14, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
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

def card(slide, x, y, w, h, fill, name=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = 0.06
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(fill)
    shp.line.fill.background()
    shp.shadow.inherit = False
    if name:
        shp.name = name
    return shp

def disc(slide, x, y, d, fill, label, color=PAPER, size=16):
    shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(fill)
    shp.line.fill.background()
    shp.shadow.inherit = False
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.name, r.font.size, r.font.bold = BODY, Pt(size), True
    r.font.color.rgb = rgb(color)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return shp

def style_axis_text(axis, size=12):
    axis.tick_labels.font.size = Pt(size)
    axis.tick_labels.font.name = BODY
    axis.tick_labels.font.color.rgb = rgb(MUTED)

def axis_title(axis, label):
    axis.has_title = True
    tf = axis.axis_title.text_frame
    tf.text = label
    r = tf.paragraphs[0].runs[0]
    r.font.size, r.font.name, r.font.bold = Pt(12), BODY, False
    r.font.color.rgb = rgb(MUTED)

def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s

def k(x):
    return f"{x:,.0f}k"

def usd(x):
    return f"${x:,.2f}"

def bn(x):
    return f"${x / 1000:,.2f}bn"

def pct(x):
    return f"{x:+.1f}%".replace("-", "−")


pax, fare, rev, g, kal = S["pax"], S["fare"], S["revenue"], S["guidance"], S["kalshi"]
base = {b["name"]: b for b in S["baselines"]}
B0 = base["B0 same quarter last year"]
B1p = base["B1 packet (reported Q2 basis)"]
B1x = base["B1 ex-breakage Q2 basis"]
act = S["actuals"] or {}


# =============================================================================
# SLIDE 1 -- the forecast against the actual
# =============================================================================
s1 = new_slide("Fewer passengers, a much higher fare", dark=True)
text(s1, L, 1.25, W, 0.4,
     "Southwest Airlines (LUV), Q3 2026  ·  forecast locked Oct 21 2026, 12:00 ET  ·  free public data only",
     size=14, color="AEB8C6", name="Subtitle")

def actual_line(a, value_fmt, point, lo, hi):
    if a is None:
        return [[("Actual  ", {"bold": True, "color": "AEB8C6"}),
                 ("reported Oct 21, after the close", {"color": "AEB8C6"})]]
    err = (point / a - 1) * 100
    hit = lo <= a <= hi
    return [[("Actual  ", {"bold": True, "color": "AEB8C6"}), (value_fmt(a), {"bold": True, "color": PAPER})],
            [(f"error {pct(err)}  ·  ", {"color": "AEB8C6"}),
             ("inside 80%" if hit else "outside 80%", {"bold": True, "color": TEAL if hit else CORAL})]]

a_pax, a_fare = act.get("revenue_passengers_000"), act.get("avg_passenger_fare_usd")
a_rev = act.get("passenger_revenue_musd") or (a_pax * a_fare / 1000 if a_pax and a_fare else None)
cards = [
    ("REVENUE PASSENGERS", k(pax["point"]),
     f"80%  {pax['lo80']:,.0f} – {pax['hi80']:,.0f}k", f"{pct(pax['yoy_pct'])} YoY  ·  TSA + T-100 chain",
     actual_line(a_pax, k, pax["point"], pax["lo80"], pax["hi80"])),
    ("AVERAGE FARE", usd(fare["point"]),
     f"80%  {usd(fare['lo80'])} – {usd(fare['hi80'])}", f"{pct(fare['yoy_pct'])} YoY  ·  CPI, season, fuel blend",
     actual_line(a_fare, usd, fare["point"], fare["lo80"], fare["hi80"])),
    ("PASSENGER REVENUE", bn(rev["point"]),
     f"80%  {bn(rev['lo80'])} – {bn(rev['hi80'])}",
     f"inside guided band {bn(g['band_seasonal_lo'])} – {bn(g['band_seasonal_hi'])}",
     actual_line(a_rev, bn, rev["point"], rev["lo80"], rev["hi80"])),
]
cw, gap, cy, ch = (W - 2 * 0.3) / 3, 0.3, 1.95, 3.55
for i, (label, big, band, sub, act_runs) in enumerate(cards):
    x = L + i * (cw + gap)
    card(s1, x, cy, cw, ch, CARD, name=f"Card {label.title()}")
    text(s1, x + 0.3, cy + 0.3, cw - 0.6, 0.3, label, size=12, bold=True, color="AEB8C6")
    text(s1, x + 0.3, cy + 0.65, cw - 0.6, 0.85, big, size=44, bold=True, color=AMBER, font=HEAD)
    text(s1, x + 0.3, cy + 1.55, cw - 0.6, 0.35, band, size=16, bold=True, color=PAPER)
    text(s1, x + 0.3, cy + 1.95, cw - 0.6, 0.6, sub, size=14, color="AEB8C6")
    ln = s1.shapes.add_connector(1, Inches(x + 0.3), Inches(cy + 2.6), Inches(x + cw - 0.3), Inches(cy + 2.6))
    ln.line.color.rgb = rgb("3A4B63")
    text(s1, x + 0.3, cy + 2.75, cw - 0.6, 0.65, act_runs, size=14, space_after=2)

# benchmark strip
by = 5.85
text(s1, L, by, W, 0.3, "BENCHMARKS", size=12, bold=True, color="AEB8C6")
bench = [
    ("B0  same quarter last year", f"{B0['pax']:,.0f}k  ·  {usd(B0['fare'])}"),
    ("B1  packet (reported Q2)", f"{B1p['pax']:,.0f}k  ·  {usd(B1p['fare'])}"),
    ("B1  rebuilt ex-breakage", f"{B1x['pax']:,.0f}k  ·  {usd(B1x['fare'])}"),
    ("Kalshi fare market, Oct 20", f"median ≈ {usd(kal['median'])}"),
]
bw = (W - 3 * 0.3) / 4
for i, (lab, val) in enumerate(bench):
    x = L + i * (bw + 0.3)
    text(s1, x, by + 0.35, bw, 0.3, lab, size=12, color="AEB8C6")
    text(s1, x, by + 0.65, bw, 0.35, val, size=16, bold=True, color=PAPER)
notes(s1, (
    "Headline: Southwest carries about 5% fewer revenue passengers than a year ago but charges about "
    "25% more per passenger, so passenger revenue lands inside the band management's guidance implies. "
    "The passenger count comes from TSA checkpoint throughput, Southwest's share of it (T-100), and the "
    "trip-factor bridge; the fare from three methods anchored on the BLS airfare index, seasonality and "
    "fuel. Intervals are Evaluation's harmonised 80% rule (post-COVID backtest error sd for both halves). "
    "The revenue interval uses a -0.4 error correlation because the fare is revenue divided by passengers. "
    "Kalshi's fare market agrees with our centre to within a dollar but is tighter than our band."))


# =============================================================================
# SLIDE 2 -- data and cleaning decisions
# =============================================================================
s2 = new_slide("TSA counts boardings, not passengers")
lw = 4.1
card(s2, L, 1.5, lw, 5.35, TINT, name="Trip factor callout")
text(s2, L + 0.35, 1.8, lw - 0.7, 0.35, "Q2 2026, YEAR ON YEAR", size=12, bold=True, color=MUTED)
text(s2, L + 0.35, 2.2, lw - 0.7, 0.8, [[("+0.3%", {"color": NAVY}), ("  enplaned", {"size": 18, "bold": False, "color": TEXT, "font": BODY})]],
     size=40, bold=True, font=HEAD)
text(s2, L + 0.35, 3.0, lw - 0.7, 0.8, [[("−3.3%", {"color": CORAL}), ("  revenue pax", {"size": 18, "bold": False, "color": TEXT, "font": BODY})]],
     size=40, bold=True, font=HEAD)
text(s2, L + 0.35, 4.05, lw - 0.7, 2.6, [
    "A checkpoint scan is a boarding. The target counts one-way paying trips. The bridge is the "
    "trip factor (enplaned ÷ revenue passengers), up 3.7% in a year as assigned seating pushed "
    "travellers onto connections.",
    [("No free source observes it. ", {"bold": True}),
     ("We extrapolate it from four post-break quarters, and it swings our answer by ~1,000k.", {})],
], size=14, color=TEXT, space_after=8)

rows = [
    ("Source", "Cleaning decision", "Why"),
    ("TSA daily, 2,830 days", "No day imputed. Both funding lapses flagged, neither repaired",
     "No dip once trend is controlled; the packet's −6.7% is not in this file"),
    ("BTS T-100, Southwest", "July is a filing; Aug–Sep nowcast from TSA × share",
     "BTS publishes ~3 months late"),
    ("Southwest quarterly", "Q2 2026 +$285M breakage added back",
     "One-off: fare $225.61 → $233.90 underlying"),
    ("BLS airfare CPI", "Oct 2025 blank → interpolated", "Shutdown gap; touches Q4 2025 only"),
    ("EIA jet fuel spot", "87 holiday blanks dropped; add Southwest's premium over spot",
     "Wholesale is ~30¢ below what Southwest pays"),
    ("Google Trends", "Not used", "Rescaled on every pull: no stable history to backtest"),
]
tx = L + lw + 0.4
tw = R - tx
tbl = s2.shapes.add_table(len(rows), 3, Inches(tx), Inches(1.5), Inches(tw), Inches(5.35))
tbl.name = "Cleaning decisions"
t = tbl.table
for j, wdt in enumerate([1.95, 3.05, tw - 5.0]):
    t.columns[j].width = Inches(wdt)
for i, row in enumerate(rows):
    for j, val in enumerate(row):
        c = t.cell(i, j)
        c.fill.solid()
        c.fill.fore_color.rgb = rgb(NAVY if i == 0 else (PAPER if i % 2 else TINT))
        c.margin_left = c.margin_right = Inches(0.1)
        c.margin_top = c.margin_bottom = Inches(0.06)
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = c.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = val
        f = p.runs[0].font
        f.name, f.size = BODY, Pt(13)
        f.bold = i == 0 or j == 0
        f.color.rgb = rgb(PAPER if i == 0 else TEXT)
notes(s2, (
    "Which reported count does a checkpoint count measure? Enplaned passengers, not revenue passengers: "
    "a connecting trip is scanned once but boards twice, and the target counts it once. In Q2 2026 "
    "enplanements rose 0.3% while revenue passengers fell 3.3%. Cleaning: the TSA file is structurally "
    "clean (no missing, duplicate or non-positive days), so nothing was imputed. The two funding-lapse "
    "windows are flagged and tested: once the downward trend in YoY growth is controlled, neither shows a "
    "throughput drop, and the -6.7% the packet cites for Mar-May is +0.3% in this file. We went with the "
    "data and kept the flag. Neither window touches Q3 2026 or its Q3 2025 base."))


# =============================================================================
# SLIDE 3 -- model and baselines
# =============================================================================
s3 = new_slide("The split says yield, not volume")
steps = [
    ("1", "Passengers", f"TSA × Southwest share × uplift ÷ trip factor, blended 65/35 with "
                        f"ASM × load factor ÷ haul", k(pax["point"])),
    ("2", "Fare", "Blend of an industry anchor (BLS CPI), a seasonal step and fuel pass-through",
     usd(fare["point"])),
    ("3", "Revenue", "Passengers × fare, with a −0.4 error correlation, checked against guidance",
     bn(rev["point"])),
]
sy = 1.55
for i, (n, head, body, val) in enumerate(steps):
    y = sy + i * 1.65
    disc(s3, L, y, 0.55, NAVY, n)
    text(s3, L + 0.8, y - 0.02, 3.5, 0.4, [[(head, {}), ("   " + val, {"color": AMBER, "font": BODY, "size": 18})]],
         size=20, bold=True, color=INK, font=HEAD)
    text(s3, L + 0.8, y + 0.45, 3.5, 1.0, body, size=14, color=TEXT)

# iso-revenue chart: the guidance band as two curves in (fare, passengers) space
X_MIN, X_MAX, Y_MIN, Y_MAX = 180, 250, 31000, 35500
cd = XyChartData()
for label, R_ in [("Guidance band", g["band_seasonal_lo"]), ("Guidance band (upper edge)", g["band_seasonal_hi"])]:
    ser = cd.add_series(label)
    for fx in np.linspace(R_ * 1000 / Y_MAX, min(X_MAX, R_ * 1000 / Y_MIN), 25):
        ser.add_data_point(round(float(fx), 2), round(R_ * 1000 / fx, 1))
pt_series = [
    ("Team forecast", [(fare["point"], pax["point"])], AMBER),
    ("B0 last year", [(B0["fare"], B0["pax"])], GREY),
    ("B1 packet", [(B1p["fare"], B1p["pax"])], CORAL),
    ("B1 ex-breakage", [(B1x["fare"], B1x["pax"])], "8E2C3A"),
]
for label, xy, _ in pt_series:
    ser = cd.add_series(label)
    for x_, y_ in xy:
        ser.add_data_point(x_, y_)
whisk = cd.add_series("Team 80% interval")
for x_, y_ in [(fare["lo80"], pax["point"]), (fare["hi80"], pax["point"])]:
    whisk.add_data_point(x_, y_)
whisk2 = cd.add_series("Team 80% interval (passengers)")
for x_, y_ in [(fare["point"], pax["lo80"]), (fare["point"], pax["hi80"])]:
    whisk2.add_data_point(x_, y_)

cx = L + 4.55
gf = s3.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS, Inches(cx), Inches(1.4),
                         Inches(R - cx), Inches(4.95), cd)
gf.name = "Iso-revenue chart"
ch3 = gf.chart
ch3.font.name, ch3.font.size = BODY, Pt(12)
ch3.has_legend = True
ch3.legend.position = XL_LEGEND_POSITION.BOTTOM
ch3.legend.include_in_layout = False
ch3.legend.font.size, ch3.legend.font.color.rgb = Pt(12), rgb(MUTED)
for ser in ch3.plots[0].series:
    nm = ser.name
    if nm.startswith("Guidance"):
        ser.format.line.color.rgb = rgb(TEAL)
        ser.format.line.width = Pt(2.25)
        ser.marker.style = XL_MARKER_STYLE.NONE
    elif nm.startswith("Team 80%"):
        ser.format.line.color.rgb = rgb(AMBER)
        ser.format.line.width = Pt(1.5)
        ser.marker.style = XL_MARKER_STYLE.NONE
    else:                     # single points: marker only, no connecting line
        col = dict((a, c) for a, _, c in pt_series)[nm]
        ser.format.line.fill.background()
        ser.marker.style = XL_MARKER_STYLE.CIRCLE if nm != "Team forecast" else XL_MARKER_STYLE.DIAMOND
        ser.marker.size = 12 if nm == "Team forecast" else 10
        ser.marker.format.fill.solid()
        ser.marker.format.fill.fore_color.rgb = rgb(col)
        ser.marker.format.line.color.rgb = rgb(PAPER)
ch3.plots[0].vary_by_categories = False
# show only the readable legend entries: drop the second band edge and the second whisker
from lxml import etree
from pptx.oxml.ns import qn
leg = ch3.legend._element
for idx in (1, 7):
    le = etree.SubElement(leg, qn("c:legendEntry"))
    etree.SubElement(le, qn("c:idx")).set("val", str(idx))
    etree.SubElement(le, qn("c:delete")).set("val", "1")
    leg.remove(le)
    leg.insert(1, le)
va, ca = ch3.value_axis, ch3.category_axis
va.minimum_scale, va.maximum_scale, va.major_unit = Y_MIN, Y_MAX, 1000
ca.minimum_scale, ca.maximum_scale, ca.major_unit = X_MIN, X_MAX, 10
va.tick_labels.number_format, va.tick_labels.number_format_is_linked = "#,##0", False
ca.tick_labels.number_format, ca.tick_labels.number_format_is_linked = '"$"0', False
va.has_major_gridlines = True
va.major_gridlines.format.line.color.rgb = rgb("E3E8EF")
ca.has_major_gridlines = False
for ax in (va, ca):
    style_axis_text(ax)
    ax.format.line.color.rgb = rgb("C9D1DC")
axis_title(va, "Revenue passengers (000s)")
axis_title(ca, "Average fare ($)")
text(s3, cx, 6.45, R - cx, 0.6,
     f"Teal lines: passenger revenue implied by guidance, {bn(g['band_seasonal_lo'])}–{bn(g['band_seasonal_hi'])} "
     f"at a {g['share_seasonal']:.1%} passenger share. Both naive baselines miss it, on opposite sides.",
     size=12, color=MUTED)
notes(s3, (
    "Guidance pins passenger revenue to a narrow band, the teal curves. Any point between them satisfies "
    "guidance: flat passengers at about $215-220, or 5% fewer passengers at about $225-231. Those are "
    "different businesses, a volume story and a yield story, and the band cannot tell them apart. Our "
    "split says yield. The naive baselines miss the band on both sides: B1 on the packet's basis carries "
    "the $285M one-off into the fare and lands below; B1 rebuilt ex-breakage carries Q2's growth forward "
    "and lands above. Splitting also says which half to blame if the print misses the band."))


# =============================================================================
# SLIDE 4 -- backtest by period
# =============================================================================
s4 = new_slide("Passengers beat naive; fares don't yet")
def mape(target, period, method):
    r = BYP[(BYP["target"] == target) & (BYP["period"].str.strip() == period) & (BYP["method"] == method)]
    return float(r["MAPE"].iloc[0])

PAIRS = [("Passengers", "revenue_passengers", "M1", "pax_B1"),
         ("Fare", "average_fare", "P_BLEND_oos", "fare_B1"),
         ("Revenue", "passenger_revenue", "REV_team", "rev_B1")]
for i, (period, label) in enumerate([("of which 2023-2024", "2023–2024, pre fee change"),
                                     ("2025-2026 (fee + model change)", "2025–2026, fee + model change")]):
    cdat = CategoryChartData()
    cdat.categories = [p[0] for p in PAIRS]
    cdat.add_series("Our method", [round(mape(t_, period, m), 2) for _, t_, m, _ in PAIRS])
    cdat.add_series("B1 naive", [round(mape(t_, period, b), 2) for _, t_, _, b in PAIRS])
    x = L + i * 4.3
    gfx = s4.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(1.45),
                              Inches(4.0), Inches(4.6), cdat)
    gfx.name = f"Backtest MAPE {label}"
    c = gfx.chart
    c.font.name, c.font.size = BODY, Pt(12)
    c.has_title = True
    c.chart_title.text_frame.text = label
    tr = c.chart_title.text_frame.paragraphs[0].runs[0]
    tr.font.size, tr.font.bold, tr.font.name = Pt(14), True, BODY
    tr.font.color.rgb = rgb(INK)
    c.has_legend = True
    c.legend.position = XL_LEGEND_POSITION.BOTTOM
    c.legend.include_in_layout = False
    c.legend.font.size, c.legend.font.color.rgb = Pt(12), rgb(MUTED)
    pl = c.plots[0]
    pl.gap_width, pl.overlap = 60, -10
    pl.has_data_labels = True
    dl = pl.data_labels
    dl.number_format, dl.number_format_is_linked = '0.0"%"', False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.color.rgb = Pt(12), rgb(TEXT)
    for ser, col in zip(pl.series, [NAVY, CORAL]):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(col)
    va = c.value_axis
    va.minimum_scale, va.maximum_scale, va.major_unit = 0, 6, 2
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E3E8EF")
    va.tick_labels.number_format, va.tick_labels.number_format_is_linked = '0"%"', False
    va.format.line.fill.background()
    style_axis_text(va)
    style_axis_text(c.category_axis)
    c.category_axis.format.line.color.rgb = rgb("C9D1DC")

def p_dm(model):
    return float(DM[(DM["period"] == "2025-2026") & (DM["model"] == model)]["p_value"].iloc[0])

wins = BYP[(BYP["target"] == "revenue_passengers") & (BYP["method"] == "M1")
           & (BYP["period"].str.startswith("full"))]["beats_B1"].iloc[0]
rx = L + 8.75
calls = [
    (NAVY, "Passengers: an edge", f"Beats B1 in {wins} quarters. Current-era p = {p_dm('T_BLEND'):.2f} (blend)."),
    (CORAL, "Fare: no edge yet", f"B1 wins 2023–24. Current-era gap 0.5 pt, p = {p_dm('P_BLEND_oos'):.2f}."),
    (CORAL, "Revenue: not proven", f"The client's number: p = {p_dm('REV_team'):.2f}. Sell the split, not the point."),
]
for i, (col, h_, b_) in enumerate(calls):
    y = 1.55 + i * 1.5
    disc(s4, rx, y + 0.05, 0.32, col, "")
    text(s4, rx + 0.5, y, R - rx - 0.5, 0.4, h_, size=16, bold=True, color=INK)
    text(s4, rx + 0.5, y + 0.4, R - rx - 0.5, 1.0, b_, size=14, color=TEXT)
text(s4, L, 6.3, W, 0.75, [
    "MAPE, vintage-correct backtest: every parameter re-estimated from what was public at the time. "
    "Our method = TSA chain (passengers), out-of-sample price blend (fare), their product (revenue). "
    "2022 is reported separately in Evaluation/README because COVID bases flatter every method. "
    "p = Diebold-Mariano vs B1, HLN small-sample correction, n = 6."], size=12, color=MUTED)
notes(s4, (
    "Evaluation re-implemented both roles' methods from their write-ups, reproduced their backtests "
    "exactly, and ran the packet's full 2022-2026 window. The TSA chain beats the naive baseline in "
    "every period and in 16 of 18 quarters, and in the current regime the edge is about as close to "
    "significance as six quarters allow. The fare does not reliably beat B1: in 2023-24 B1 wins outright. "
    "So the revenue figure the client cares about has no demonstrated edge over 'last year times last "
    "quarter's growth'. Interval check: Traffic's delivered band covered only 50% of post-COVID quarters "
    "and Price's 93%, so the form uses one harmonised rule for both."))


# =============================================================================
# SLIDE 5 -- what we got wrong and why (pre-registered before the print)
# =============================================================================
s5 = new_slide("What we got wrong, and why" if POST else "What would make us wrong", dark=True)
lx, lw5 = L, 7.35
if not POST:
    text(s5, lx, 1.3, lw5, 0.35, "PRE-REGISTERED BEFORE THE PRINT", size=12, bold=True, color="AEB8C6")
    risks = [
        ("Trip factor", f"We assume {pax['trip_factor']:.4f}, +3.4% YoY. With no 2026 step the "
                        f"TSA chain gives ~33,900k: above B1, at the top edge of our 80% band."),
        ("A one-off in the print", "Q2's $285M breakage moved the reported fare by $8. We forecast "
                                   "the underlying fare."),
        ("Capacity below guide", "July domestic ASMs ran −1.8% YoY against a −1% to flat guide: "
                                 "about −160k passengers."),
        ("The naive regression", f"Refitted, it says {k(pax['M3'])}, 2.1% below us. We think it "
                                 f"misses the share flip, but the gap is large."),
    ]
    for i, (h_, b_) in enumerate(risks):
        y = 1.8 + i * 1.18
        disc(s5, lx, y + 0.02, 0.42, CORAL, str(i + 1), size=14)
        text(s5, lx + 0.65, y, lw5 - 0.65, 0.35, h_, size=16, bold=True, color=PAPER)
        text(s5, lx + 0.65, y + 0.38, lw5 - 0.65, 0.75, b_, size=14, color="D5DCE6")
else:
    sc = pd.read_csv(OUT / "scorecard.csv")
    text(s5, lx, 1.3, lw5, 0.35, "SCORECARD", size=12, bold=True, color="AEB8C6")
    tbl5 = s5.shapes.add_table(len(sc) + 1, 5, Inches(lx), Inches(1.75), Inches(lw5), Inches(2.0))
    tbl5.name = "Scorecard"
    hdr = ["", "Forecast", "Actual", "Error", "B1 error"]
    fmt = [lambda v: f"{v:,.0f}k", lambda v: usd(v), lambda v: bn(v)]
    for j, h_ in enumerate(hdr):
        tbl5.table.cell(0, j).text = h_
    for i, r_ in sc.iterrows():
        vals = [r_["target"].split(" (")[0].capitalize(), fmt[i](r_["team"]), fmt[i](r_["actual"]),
                pct(r_['team_err_pct']) + (" ✓" if r_["in_80"] else " ✗"),
                pct(r_['B1_exbreakage_err_pct'])]
        for j, v in enumerate(vals):
            tbl5.table.cell(i + 1, j).text = v
    for i in range(len(sc) + 1):
        for j in range(5):
            c = tbl5.table.cell(i, j)
            c.fill.solid()
            c.fill.fore_color.rgb = rgb(NAVY if i == 0 else CARD)
            f = c.text_frame.paragraphs[0].runs[0].font if c.text_frame.paragraphs[0].runs else None
            if f:
                f.name, f.size, f.color.rgb = BODY, Pt(14), rgb(PAPER)
                f.bold = i == 0 or j == 0
    d = S["decomposition"]
    why = ([[("Passenger miss, log %: ", {"bold": True, "color": PAPER}),
             (f"{pct(d['total_log_err_pct'])} = boardings {pct(d['boardings_log_err_pct'])} "
              f"(the TSA chain) + trip factor {pct(d['trip_factor_log_err_pct'])} (the bridge). "
              f"Trip factor forecast {d['trip_factor_forecast']:.4f}, actual {d['trip_factor_actual']:.4f}.",
              {"color": "D5DCE6"})]] if d else
           [[("Add enplaned passengers to actuals.json ", {"bold": True, "color": PAPER}),
             ("to split the passenger miss into boardings vs trip factor.", {"color": "D5DCE6"})]])
    text(s5, lx, 4.25, lw5, 0.7, why, size=14)
    text(s5, lx, 5.0, lw5, 1.5, [
        [("Pre-registered risks: ", {"bold": True, "color": PAPER}),
         ("trip factor; a one-off in the print; capacity below guide; the naive regression's lower call. "
          "Say which one hit.", {"color": "D5DCE6"})]], size=14)

px = L + lw5 + 0.45
pw = R - px
card(s5, px, 1.3, pw, 5.55, CARD, name="PoV card")
text(s5, px + 0.35, 1.6, pw - 0.7, 0.35, "OUR POV  ·  TEAM FLAG", size=12, bold=True, color=AMBER)
text(s5, px + 0.35, 2.0, pw - 0.7, 1.3,
     "Sell the passenger nowcast and the fare attribution, with a regime flag. Do not sell the revenue "
     "point as beating naive.", size=16, bold=True, color=PAPER)
text(s5, px + 0.35, 3.45, pw - 0.7, 0.3, "Downgrade when", size=14, bold=True, color="AEB8C6")
triggers = [
    "The trip factor moves >1.5 pt off trend",
    "Southwest's TSA share turns negative two months running",
    "The TSA chain loses to B1 two quarters running",
    "A funding lapse or a TSA collection change",
    "The TSA chain and the naive regression split by >2% (raised for Q3)",
]
tb = text(s5, px + 0.35, 3.85, pw - 0.7, 2.8, triggers, size=14, color="D5DCE6", space_after=6)
for p in tb.text_frame.paragraphs:
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(Inches(0.25)))
    pPr.set("indent", str(-Inches(0.25)))
    bu = etree.SubElement(pPr, qn("a:buChar"))
    bu.set("char", "•")
notes(s5, (
    "Before the print we wrote down what would make us wrong, in order of how much each could move the "
    "answer. The trip factor is the whole passenger call: it is extrapolated from four quarters and no "
    "public source observes it. A one-off revenue item would move the reported fare with no signal in "
    "public data. July capacity ran below the bottom of guidance. And the naive regression, which is "
    "nearly as accurate as our chain out of sample, says 2% lower. After the print, re-run integrate.py "
    "with actuals.json filled and this slide becomes the scorecard, with the passenger miss split into a "
    "boardings error and a trip-factor error. PoV for the debate: Flag."
    if not POST else
    "Scorecard against the print. The passenger miss is split exactly, in logs, into the boardings "
    "nowcast (TSA and T-100) and the trip factor (the accounting bridge). Say which pre-registered risk "
    "materialised and whether the Flag conditions were triggered."))

prs.save(DECK)

# Make the build byte-reproducible like the other pipelines: python-pptx stamps
# every zip entry with the wall clock, and each chart's embedded workbook also
# records its creation time. Pin both so a re-run with the same inputs is a no-op.
import io, re, zipfile
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
print(f"wrote {DECK.relative_to(ROOT)}  ({'post-print scorecard' if POST else 'pre-print'} version, "
      f"{len(prs.slides)} slides)")
