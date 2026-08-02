"""
Builds a print-friendly, multi-page PDF version of the industry benchmark
report, directly from the same JSON-shaped data dict produced by
report_builder.build_report() -- so the PDF numbers always match the web
report exactly.

Uses reportlab (pure Python, no external system binaries like wkhtmltopdf
or Pango/Cairo) so it installs cleanly on Render's standard Python
buildpack with nothing extra needed.

The layout mirrors the web report's sections but is restyled for print
(clean tables, no interactive chart -- the Revenue & SDE trend is shown as
a table instead of a line chart, since rendering a chart image would pull
in a heavier dependency like matplotlib for a report that is otherwise
pure reportlab).
"""
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)
from reportlab.platypus.flowables import HRFlowable

ACCENT = colors.HexColor("#0f7a63")
ACCENT_DARK = colors.HexColor("#0a5a49")
ACCENT_TINT = colors.HexColor("#eaf5f1")
CARD_TINT = colors.HexColor("#f3f9f7")
ZEBRA = colors.HexColor("#f7faf9")
INK = colors.HexColor("#12212b")
SUB = colors.HexColor("#5b6b74")
LINE = colors.HexColor("#dfe6ea")
WARN_BG = colors.HexColor("#fff6e5")
WARN_BORDER = colors.HexColor("#f0d998")
WARN_TEXT = colors.HexColor("#5c4a12")

PAGE_W, PAGE_H = letter
MARGIN = 0.65 * inch
CONTENT_WIDTH = PAGE_W - 2 * MARGIN


# ---------------------------------------------------------------------------
# Formatting helpers (mirror frontend/index.html's money()/num()/pct())
# ---------------------------------------------------------------------------

def money(v, decimals=0):
    if v is None:
        return "—"
    return f"${v:,.{decimals}f}"


def money_compact(v):
    if v is None:
        return "—"
    abs_v = abs(v)
    sign = "-" if v < 0 else ""
    if abs_v >= 1e9:
        d = 0 if abs_v >= 1e11 else 1
        return f"{sign}${abs_v / 1e9:.{d}f}B"
    if abs_v >= 1e6:
        d = 0 if abs_v >= 1e8 else 1
        return f"{sign}${abs_v / 1e6:.{d}f}M"
    if abs_v >= 1e3:
        d = 0 if abs_v >= 1e5 else 1
        return f"{sign}${abs_v / 1e3:.{d}f}K"
    return money(v)


def num(v):
    if v is None:
        return "—"
    return f"{v:,.0f}"


def pct(v):
    if v is None:
        return "—"
    return f"{v * 100:.1f}%"


def pct_of(v, base):
    if not base:
        return "—"
    return pct(v / base if v is not None else None)


def num2(v):
    if v is None:
        return "—"
    return f"{v:.2f}"


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", fontSize=20, leading=25, textColor=ACCENT_DARK,
        fontName="Helvetica-Bold", spaceAfter=6, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="SubTitle", fontSize=9.5, leading=13, textColor=SUB, spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="H2", fontSize=14, leading=17, textColor=ACCENT_DARK, fontName="Helvetica-Bold",
        spaceBefore=20, spaceAfter=2, keepWithNext=1,
    ))
    styles.add(ParagraphStyle(
        name="H3", fontSize=10.5, textColor=INK, fontName="Helvetica-Bold",
        spaceBefore=14, spaceAfter=5, keepWithNext=1,
    ))
    styles.add(ParagraphStyle(
        name="H4", fontSize=9.5, textColor=INK, fontName="Helvetica-Bold",
        spaceBefore=10, spaceAfter=4, keepWithNext=1,
    ))
    styles.add(ParagraphStyle(
        name="Body", fontSize=9.3, textColor=INK, leading=13.5, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Caption", fontSize=8.2, textColor=SUB, leading=11.5, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="DisclaimerHeading", fontSize=12, leading=15, textColor=ACCENT_DARK,
        fontName="Helvetica-Bold", spaceBefore=20, spaceAfter=8, keepWithNext=1,
    ))
    styles.add(ParagraphStyle(
        name="DisclaimerBody", fontSize=8.5, textColor=WARN_TEXT,
        leading=12.5, spaceAfter=7,
    ))
    return styles


# ---------------------------------------------------------------------------
# Table / card builders
# ---------------------------------------------------------------------------

_CELL_STYLE_CACHE = {}


def _cell_style(align="LEFT", bold=False, color=INK, size=7.8):
    """Small Paragraph styles for table cells, cached by (align, bold,
    color, size). Using Paragraph objects (instead of raw strings) is
    what makes cell text actually WRAP inside its column -- plain
    strings in a reportlab Table never wrap, they just overflow past the
    cell edge and overlap whatever is next to them."""
    key = (align, bold, color, size)
    if key not in _CELL_STYLE_CACHE:
        _CELL_STYLE_CACHE[key] = ParagraphStyle(
            name=f"cell-{len(_CELL_STYLE_CACHE)}",
            fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size, leading=size * 1.35, textColor=color,
            alignment=TA_RIGHT if align == "RIGHT" else TA_LEFT,
        )
    return _CELL_STYLE_CACHE[key]


def _cell(value, align="LEFT", bold=False, color=INK, size=7.8):
    return Paragraph(str(value), _cell_style(align, bold, color, size))


def _kv_table(rows, value_width=1.8 * inch):
    """Two-column label/value table (used for At-a-Glance and Ratios).
    Always spans the full content width and is left-aligned, so it lines
    up flush with the surrounding headings and paragraphs."""
    label_width = CONTENT_WIDTH - value_width
    data = [
        [_cell(label, "LEFT", size=9), _cell(value, "RIGHT", size=9)]
        for label, value in rows
    ]
    t = Table(data, colWidths=[label_width, value_width])
    t.hAlign = "LEFT"
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, ZEBRA]),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
    ]))
    return t


def _grid_table(header, rows, bold_rows=None, first_col_width=2.3 * inch, left_align_cols=None):
    """Header row + data rows, used for multi-column (year-by-year or
    size-class) tables. Always spans the full content width, is left-
    aligned, and gives the header row a tinted accent background so it
    reads as a distinct table header rather than a plain top line.
    bold_rows is a set of row indices (0-based, into `rows`) to bold as
    subtotal-style rows. If first_col_width is None, all columns share
    the width evenly (used when there's no separate "label" column).
    left_align_cols (0-based column indices) defaults to just the first
    column -- pass e.g. {0, 2} for a table with a descriptive text
    column later on (like a "Basis"/"Notes" column) so it left-aligns
    and wraps instead of being forced right like a number column."""
    bold_rows = bold_rows or set()
    left_align_cols = {0} if left_align_cols is None else left_align_cols
    n_cols = len(header)
    if first_col_width is None:
        col_widths = [CONTENT_WIDTH / n_cols] * n_cols
    else:
        other_width = (CONTENT_WIDTH - first_col_width) / (n_cols - 1) if n_cols > 1 else 0
        col_widths = [first_col_width] + [other_width] * (n_cols - 1)

    def _row(values, bold, color):
        return [
            _cell(v, "LEFT" if i in left_align_cols else "RIGHT", bold=bold, color=color)
            for i, v in enumerate(values)
        ]

    data = [_row(header, True, ACCENT_DARK)]
    for idx, row in enumerate(rows):
        data.append(_row(row, idx in bold_rows, INK))

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.hAlign = "LEFT"
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT_TINT),
        ("LINEBELOW", (0, 0), (-1, 0), 1, ACCENT_DARK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
    ]
    for idx in bold_rows:
        row = idx + 1  # +1 to account for header row
        style.append(("LINEABOVE", (0, row), (-1, row), 0.6, SUB))
    t.setStyle(TableStyle(style))
    return t


def _card(flowables, bg_color, border_color=None, pad=12):
    """Wraps one or more flowables in a full-width tinted/bordered box, to
    echo the web report's card-based visual language (used for the intro
    description, the calculated-projection callout, and the disclosures)."""
    if not isinstance(flowables, list):
        flowables = [flowables]
    t = Table([[flowables]], colWidths=[CONTENT_WIDTH])
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("LEFTPADDING", (0, 0), (-1, -1), pad),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if border_color:
        style.append(("BOX", (0, 0), (-1, -1), 0.75, border_color))
    t.setStyle(TableStyle(style))
    t.hAlign = "LEFT"
    return t


def _section_heading(story, styles, text):
    story.append(Paragraph(text, styles["H2"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT,
                             spaceBefore=0, spaceAfter=10, hAlign="LEFT"))


# ---------------------------------------------------------------------------
# Page chrome: footer with page numbers (+ a thin accent bar on page 1)
# ---------------------------------------------------------------------------

def _make_canvas_class(footer_left_text):
    class _NumberedCanvas(pdfcanvas.Canvas):
        def __init__(self, *args, **kwargs):
            pdfcanvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_chrome(total)
                pdfcanvas.Canvas.showPage(self)
            pdfcanvas.Canvas.save(self)

        def _draw_chrome(self, total):
            self.saveState()
            if self._pageNumber == 1:
                self.setFillColor(ACCENT)
                self.rect(0, PAGE_H - 5, PAGE_W, 5, fill=1, stroke=0)
            self.setStrokeColor(LINE)
            self.setLineWidth(0.6)
            self.line(MARGIN, 0.52 * inch, PAGE_W - MARGIN, 0.52 * inch)
            self.setFont("Helvetica", 7.5)
            self.setFillColor(SUB)
            self.drawString(MARGIN, 0.34 * inch, footer_left_text)
            self.drawRightString(PAGE_W - MARGIN, 0.34 * inch, f"Page {self._pageNumber} of {total}")
            self.restoreState()

    return _NumberedCanvas


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    industry = data["industry"]
    geo = data["geography"]
    doc_title = f"{industry.get('naics_label', 'Industry')} — {geo['state_name']} Benchmark Report"
    footer_text = f"{industry.get('naics_label', 'Industry')} - {geo['state_name']} - Industry Financial Benchmarks"

    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.6 * inch, bottomMargin=0.75 * inch,
        title=doc_title,
    )
    styles = _styles()
    story = []

    g = data["industry_at_a_glance"]
    is_ = data["income_statement_latest"]
    ns = data.get("national_income_statement_latest")
    bs = data["balance_sheet"]
    ratios_history = data["ratios_history"]
    sources = data["data_sources"]
    years_sorted = sorted(ratios_history.keys())
    first_year, last_year = years_sorted[0], years_sorted[-1]

    # ---- Header -----------------------------------------------------
    story.append(Paragraph(industry.get("naics_label", "Industry"), styles["ReportTitle"]))
    story.append(Paragraph(
        f"{geo['state_name']} &middot; NAICS {industry['naics_code']} &middot; "
        f"Modeled with the &ldquo;{industry['sector_profile_used']}&rdquo; sector profile &middot; "
        f"Generated {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
        styles["SubTitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT,
                             spaceBefore=0, spaceAfter=12, hAlign="LEFT"))
    if data.get("industry_description"):
        story.append(_card(Paragraph(data["industry_description"], styles["Body"]),
                            bg_color=CARD_TINT, border_color=LINE))
        story.append(Spacer(1, 10))

    # ---- At a Glance --------------------------------------------------
    _section_heading(story, styles, "At a Glance")
    story.append(Paragraph("Average per firm", styles["H3"]))
    avg_rows = [
        [f"Est. average revenue / firm, {geo['state_name']} ({sources['cbp_year']})",
         money_compact(g["average_revenue_per_firm"])],
        ["National average revenue / firm", money_compact(g.get("national_average_revenue_per_firm"))],
    ]
    if is_ and is_.get("sde") is not None:
        avg_rows.append([f"Est. average SDE / firm, {geo['state_name']}", money_compact(is_["sde"])])
    if ns and ns.get("sde") is not None:
        avg_rows.append(["National average SDE / firm", money_compact(ns["sde"])])
    story.append(_kv_table(avg_rows))

    story.append(Paragraph("Industry totals", styles["H3"]))
    totals_rows = [
        ["Firms (2022 Economic Census)", num(g["total_firms"])],
        ["Total industry revenue", money_compact(g["total_revenue"])],
        ["Total employment", num(g["total_employment"])],
        ["Total annual payroll", money_compact(g["total_payroll"])],
        ["Total SDE, all firms", money_compact(g["total_sde"])],
        ["Total net income, all firms", money_compact(g["total_net_income"])],
    ]
    story.append(_kv_table(totals_rows))

    dist = g.get("firm_distribution") or {}
    if dist:
        story.append(Paragraph("Firms Distribution by Sales Class", styles["H3"]))
        rows = [[label, num(v["count"]), f"{v['pct']:.1f}%"] for label, v in dist.items()]
        rows.append(["Total", num(g["total_firms"]), "100.0%"])
        story.append(_grid_table(["Sales Class", "Firms", "% of Total"], rows, bold_rows={len(rows) - 1},
                                  first_col_width=3.2 * inch))

    # ---- Industry Trends & AI Outlook ---------------------------------
    trends = data.get("industry_trends")
    projection = data.get("revenue_projection")
    if trends:
        story.append(Spacer(1, 6))
        _section_heading(story, styles, "Industry Trends & AI Outlook (government data)")
        nat = trends["national"]
        sec = trends.get("sector") or {}
        has_sector = trends.get("sector_has_data")

        def _pick(key, note_key, fallback_tag):
            if has_sector and sec.get(key) is not None:
                return sec[key], sec.get(note_key), "Sector-specific"
            return nat.get(key), nat.get(note_key), fallback_tag

        growth_val, growth_note, growth_tag = _pick(
            "employment_growth_2024_2034_pct", "growth_note",
            "National average (sector-specific figure not published)")
        demand_val, demand_note, demand_tag = _pick(
            "output_growth_2024_2034_pct", "output_growth_note",
            "National average (sector-specific figure not published)")
        ai_current = sec.get("ai_current_use_pct") if has_sector else None
        ai_expected = sec.get("ai_expected_use_pct") if has_sector else None
        ai_note = sec.get("ai_note") if has_sector else None
        ai_tag = "Sector-specific"
        if ai_current is None:
            ai_current, ai_expected, ai_note = nat.get("ai_current_use_pct"), nat.get("ai_expected_use_pct"), nat.get("ai_note")
            ai_tag = "National average (sector-specific figure not published)"

        trend_rows = [
            ["Projected employment growth, 2024–2034", f"{growth_val:+.1f}%" if growth_val is not None else "—", growth_tag],
            ["Projected demand growth (real output), 2024–2034", f"{demand_val:+.1f}%" if demand_val is not None else "—", demand_tag],
            ["Businesses currently using AI", f"{ai_current:.1f}%" if ai_current is not None else "—", ai_tag],
            ["Businesses expecting to use AI within 6 months", f"{ai_expected:.1f}%" if ai_expected is not None else "—", ""],
        ]
        story.append(_grid_table(["Metric", "Value", "Basis"], trend_rows, first_col_width=2.5 * inch,
                                  left_align_cols={0, 2}))
        for note in (growth_note, demand_note, ai_note):
            if note:
                story.append(Paragraph(note, styles["Caption"]))

        if projection and projection.get("projected_revenue"):
            story.append(Spacer(1, 4))
            story.append(_card(Paragraph(
                f"<b>Calculated projection:</b> {money(projection['projected_revenue'])} by {projection['target_year']} "
                f"&mdash; projected average revenue per firm, growing this industry's estimated "
                f"{money(projection['base_revenue'])} ({projection['base_year']}) forward at "
                f"{projection['annual_growth_rate_pct_used']}%/year, the {projection['growth_rate_basis']} "
                f"for real demand growth. This isn't a Census/BLS figure &mdash; it's calculated by this tool "
                f"and should be treated as directional, not a forecast guarantee.",
                styles["Body"],
            ), bg_color=ACCENT_TINT, border_color=ACCENT))
            story.append(Spacer(1, 6))
        if trends.get("as_of"):
            story.append(Paragraph(trends["as_of"], styles["Caption"]))

    # ---- Revenue & SDE 5-Year trend (table instead of chart) ----------
    is_history = data.get("income_statement_history") or {}
    if is_history:
        story.append(Paragraph("Revenue & SDE Trend, 5-Year", styles["H3"]))
        years = sorted(is_history.keys())
        rev_row = ["Revenue"] + [money(is_history[y]["revenue"]) for y in years]
        sde_row = ["SDE"] + [money(is_history[y]["sde"]) for y in years]
        ebitda_row = ["EBITDA"] + [money(is_history[y]["ebitda"]) for y in years]
        story.append(_grid_table(["Metric"] + [str(y) for y in years], [rev_row, sde_row, ebitda_row],
                                  first_col_width=1.3 * inch))
        story.append(Paragraph(
            "5-year series modeled from the latest average-revenue estimate using observed "
            "employment growth. Not measured year-by-year data.", styles["Caption"],
        ))

    # ---- State vs. National Benchmarks ---------------------------------
    metric_trends = data.get("metric_trends") or {}
    if metric_trends:
        story.append(Paragraph("State vs. National Benchmarks, 5-Year", styles["H3"]))
        order = ["revenue", "sde", "ebitda", "gross_profit", "pretax_net_profit"]
        for key in order:
            mt = metric_trends.get(key)
            if not mt:
                continue
            years = sorted(mt["state_history"].keys())
            has_national = any(y in mt.get("national_history", {}) for y in years)
            story.append(Paragraph(mt["label"], styles["H4"]))
            rows = [["State"] + [money(mt["state_history"][y]) for y in years]]
            if has_national:
                rows.append(["United States"] + [money(mt["national_history"].get(y)) for y in years])
            story.append(_grid_table(["Year"] + [str(y) for y in years], rows, first_col_width=1.3 * inch))
            if mt.get("state_trend") and mt["state_trend"].get("sentence"):
                story.append(Paragraph(mt["state_trend"]["sentence"], styles["Caption"]))
            if mt.get("vs_national_note"):
                story.append(Paragraph(mt["vs_national_note"], styles["Caption"]))

    # ---- Income Statement (latest year) --------------------------------
    _section_heading(story, styles, "Income Statement")
    story.append(Paragraph(f"% of average revenue, latest year ({sources['cbp_year']})", styles["Caption"]))
    rev = is_["revenue"]
    is_rows = [
        ("Business Revenue", rev, True),
        ("Cost of Sales", is_["cost_of_sales"], False),
        ("Gross Profit", is_["gross_profit"], True),
        ("Officers Compensation", is_["opex"]["officers_compensation"], False),
        ("Salary & Wages", is_["opex"]["salary_and_wages"], False),
        ("Benefits & Pensions", is_["opex"]["benefits_and_pensions"], False),
        ("Rent", is_["opex"]["rent"], False),
        ("Other Expenses", is_["opex"]["other_expenses"], False),
        ("Depreciation & Amortization", is_["opex"]["depreciation_and_amortization"], False),
        ("Total Operating Expenses", is_["opex"]["total"], True),
        ("Operating Income", is_["operating_income"], True),
        ("Interest Income", is_["other"]["interest_income"], False),
        ("Interest Expense", is_["other"]["interest_expense"], False),
        ("Other Income", is_["other"]["other_income"], False),
        ("EBITDA", is_["ebitda"], True),
        ("SDE (Cash Flow)", is_["sde"], True),
        ("Pre-Tax Net Profit", is_["pretax_net_profit"], True),
    ]
    grid_rows = [[label, money(val), pct_of(val, rev)] for label, val, _ in is_rows]
    bold_idx = {i for i, (_, _, b) in enumerate(is_rows) if b}
    story.append(_grid_table(["Line Item", "Amount", "% of Revenue"], grid_rows, bold_rows=bold_idx,
                              first_col_width=2.6 * inch))

    # ---- Balance Sheet (latest year) ------------------------------------
    story.append(Spacer(1, 6))
    _section_heading(story, styles, "Balance Sheet")
    story.append(Paragraph("% of total assets, latest year", styles["Caption"]))
    ta = bs["total_assets"]
    bs_rows = [
        ("Cash", bs["current_assets"]["cash"], False),
        ("Receivables", bs["current_assets"]["receivables"], False),
        ("Inventory", bs["current_assets"]["inventory"], False),
        ("Other Current Assets", bs["current_assets"]["other"], False),
        ("Total Current Assets", bs["current_assets"]["total"], True),
        ("Net Fixed Assets", bs["fixed_assets"]["net"], False),
        ("Other Non-Current Assets", bs["other_non_current_assets"], False),
        ("Total Assets", ta, True),
        ("Accounts Payable", bs["current_liabilities"]["accounts_payable"], False),
        ("Notes Payable", bs["current_liabilities"]["notes_payable"], False),
        ("Other Current Liabilities", bs["current_liabilities"]["other"], False),
        ("Total Current Liabilities", bs["current_liabilities"]["total"], True),
        ("Long-Term Liabilities", bs["long_term_liabilities"], False),
        ("Total Liabilities", bs["total_liabilities"], True),
        ("Equity", bs["equity"], True),
    ]
    grid_rows = [[label, money(val), pct_of(val, ta)] for label, val, _ in bs_rows]
    bold_idx = {i for i, (_, _, b) in enumerate(bs_rows) if b}
    story.append(_grid_table(["Line Item", "Amount", "% of Assets"], grid_rows, bold_rows=bold_idx,
                              first_col_width=2.6 * inch))

    # ---- Income Statement, 5-Year --------------------------------------
    if is_history:
        story.append(Spacer(1, 6))
        _section_heading(story, styles, "Income Statement, 5-Year")
        years = sorted(is_history.keys())
        rows_def = [
            ("Business Revenue", lambda y: is_history[y]["revenue"], True),
            ("Cost of Sales", lambda y: is_history[y]["cost_of_sales"], False),
            ("Gross Profit", lambda y: is_history[y]["gross_profit"], True),
            ("Officers Compensation", lambda y: is_history[y]["opex"]["officers_compensation"], False),
            ("Salary & Wages", lambda y: is_history[y]["opex"]["salary_and_wages"], False),
            ("Benefits & Pensions", lambda y: is_history[y]["opex"]["benefits_and_pensions"], False),
            ("Rent", lambda y: is_history[y]["opex"]["rent"], False),
            ("Other Expenses", lambda y: is_history[y]["opex"]["other_expenses"], False),
            ("Depreciation & Amortization", lambda y: is_history[y]["opex"]["depreciation_and_amortization"], False),
            ("Total Operating Expenses", lambda y: is_history[y]["opex"]["total"], True),
            ("Operating Income", lambda y: is_history[y]["operating_income"], True),
            ("EBITDA", lambda y: is_history[y]["ebitda"], True),
            ("SDE (Cash Flow)", lambda y: is_history[y]["sde"], True),
            ("Pre-Tax Net Profit", lambda y: is_history[y]["pretax_net_profit"], True),
        ]
        grid_rows = [[label] + [money(fn(y)) for y in years] for label, fn, _ in rows_def]
        bold_idx = {i for i, (_, _, b) in enumerate(rows_def) if b}
        story.append(_grid_table(["Line item"] + [str(y) for y in years], grid_rows, bold_rows=bold_idx,
                                  first_col_width=2.0 * inch))

    # ---- Balance Sheet, 5-Year ------------------------------------------
    bs_history = data.get("balance_sheet_history") or {}
    if bs_history:
        story.append(Spacer(1, 6))
        _section_heading(story, styles, "Balance Sheet, 5-Year")
        years = sorted(bs_history.keys())
        rows_def = [
            ("Total Assets", lambda y: bs_history[y]["total_assets"], True),
            ("Cash", lambda y: bs_history[y]["current_assets"]["cash"], False),
            ("Receivables", lambda y: bs_history[y]["current_assets"]["receivables"], False),
            ("Inventory", lambda y: bs_history[y]["current_assets"]["inventory"], False),
            ("Other Current Assets", lambda y: bs_history[y]["current_assets"]["other"], False),
            ("Total Current Assets", lambda y: bs_history[y]["current_assets"]["total"], True),
            ("Net Fixed Assets", lambda y: bs_history[y]["fixed_assets"]["net"], False),
            ("Other Non-Current Assets", lambda y: bs_history[y]["other_non_current_assets"], False),
            ("Accounts Payable", lambda y: bs_history[y]["current_liabilities"]["accounts_payable"], False),
            ("Notes Payable", lambda y: bs_history[y]["current_liabilities"]["notes_payable"], False),
            ("Other Current Liabilities", lambda y: bs_history[y]["current_liabilities"]["other"], False),
            ("Total Current Liabilities", lambda y: bs_history[y]["current_liabilities"]["total"], True),
            ("Long-Term Liabilities", lambda y: bs_history[y]["long_term_liabilities"], False),
            ("Total Liabilities", lambda y: bs_history[y]["total_liabilities"], True),
            ("Equity", lambda y: bs_history[y]["equity"], True),
        ]
        grid_rows = [[label] + [money(fn(y)) for y in years] for label, fn, _ in rows_def]
        bold_idx = {i for i, (_, _, b) in enumerate(rows_def) if b}
        story.append(_grid_table(["Line item"] + [str(y) for y in years], grid_rows, bold_rows=bold_idx,
                                  first_col_width=2.0 * inch))

    # ---- Financial Ratios (merged latest-year + NWC trend) --------------
    story.append(Spacer(1, 6))
    _section_heading(story, styles, "Financial Ratios")
    story.append(Paragraph(
        f"Latest year ({sources['cbp_year']}). This tool applies one fixed sector-typical cost and "
        f"balance-sheet structure across all 5 modeled years, so margin, liquidity, and turnover "
        f"ratios stay constant by construction &mdash; only Net Working Capital (a dollar-scale "
        f"figure) genuinely moves as revenue grows, shown below with its change since {first_year}.",
        styles["Caption"],
    ))

    def _ratio_section(title, rows):
        story.append(Paragraph(title, styles["H3"]))
        table_rows = []
        for label, getter, fmt in rows:
            values = [getter(y) for y in years_sorted]
            is_constant = len(values) > 1 and all(v == values[0] for v in values)
            latest = values[-1]
            value_str = fmt(latest)
            if not is_constant:
                first_v = values[0]
                chg = (latest - first_v) / first_v if first_v else 0
                sign = "+" if chg >= 0 else ""
                value_str = f"{value_str}  ({sign}{chg * 100:.1f}% since {first_year})"
            table_rows.append([label, value_str])
        story.append(_kv_table(table_rows, value_width=3.0 * inch))

    r = ratios_history
    _ratio_section("Cash Flow & Solvency", [
        ("Current Ratio", lambda y: r[y]["current_ratio"], num2),
        ("Quick Ratio", lambda y: r[y]["quick_ratio"], num2),
        ("Days Payable", lambda y: r[y]["days_payable"], lambda v: v if v is not None else "—"),
        ("Net Working Capital", lambda y: r[y]["net_working_capital"], money),
    ])
    _ratio_section("Profitability", [
        ("EBITDA / Revenue", lambda y: r[y]["ebitda_margin_pct"], pct),
        ("Pre-Tax Return on Assets", lambda y: r[y]["pretax_return_on_assets_pct"], pct),
        ("Pre-Tax Return on Net Worth", lambda y: r[y]["pretax_return_on_net_worth_pct"], pct),
        ("Gross Margin", lambda y: r[y]["gross_margin_pct"], pct),
    ])
    _ratio_section("Efficiency", [
        ("Assets / Revenue (Capital Intensity)", lambda y: r[y]["assets_to_revenue"], num2),
        ("Fixed Asset Turnover", lambda y: r[y]["fixed_asset_turnover"], num2),
        ("Receivables Turnover", lambda y: r[y]["receivables_turnover"], num2),
        ("Total Asset Turnover", lambda y: r[y]["total_asset_turnover"], num2),
        ("Days Working Capital", lambda y: r[y]["days_working_capital"], lambda v: v if v is not None else "—"),
    ])

    # ---- By Revenue Size Class -------------------------------------------
    size_classes = data.get("size_class_estimates") or {}
    if size_classes:
        story.append(Spacer(1, 6))
        _section_heading(story, styles, "By Revenue Size Class")
        story.append(Paragraph("Estimated SDE and EBITDA by size class, scaled from the sector profile.", styles["Caption"]))
        labels = list(size_classes.keys())
        metric_rows = [
            ["Revenue"] + [money(size_classes[l]["revenue"]) for l in labels],
            ["Gross Profit"] + [money(size_classes[l]["gross_profit"]) for l in labels],
            ["EBITDA"] + [money(size_classes[l]["ebitda"]) for l in labels],
            ["SDE"] + [money(size_classes[l]["sde"]) for l in labels],
        ]
        story.append(_grid_table(["Metric"] + labels, metric_rows, first_col_width=1.8 * inch))

    # ---- By Revenue Size Class, 5-Year ------------------------------------
    size_history = data.get("size_class_history") or {}
    if size_history:
        story.append(Spacer(1, 6))
        _section_heading(story, styles, "By Revenue Size Class, 5-Year")
        class_labels = list(size_history.keys())
        years = sorted(size_history[class_labels[0]].keys())
        story.append(Paragraph(
            f"Same modeled growth trend applied within each size class, using this industry's "
            f"observed employment growth rate ({data.get('implied_annual_growth_pct')}%/year) "
            f"&mdash; the rightmost column shows the total change over the 5-year window.",
            styles["Caption"],
        ))
        for key, label in [("revenue", "Revenue"), ("sde", "SDE (Cash Flow)"), ("ebitda", "EBITDA"),
                           ("gross_profit", "Gross Profit"), ("pretax_net_profit", "Pre-Tax Net Profit")]:
            story.append(Paragraph(label, styles["H4"]))
            rows = []
            for cls in class_labels:
                first_v = size_history[cls][years[0]][key]
                last_v = size_history[cls][years[-1]][key]
                chg = (last_v - first_v) / first_v if first_v else 0
                sign = "+" if chg >= 0 else ""
                row = [cls] + [money(size_history[cls][y][key]) for y in years] + [f"{sign}{chg * 100:.1f}%"]
                rows.append(row)
            story.append(_grid_table(["Sales Class"] + [str(y) for y in years] + [f"{years[0]}–{years[-1]}"], rows,
                                      first_col_width=1.5 * inch))

    # ---- Capital Intensity Analysis ---------------------------------------
    cap_intensity = data.get("capital_intensity_by_size") or {}
    if cap_intensity:
        story.append(Spacer(1, 6))
        _section_heading(story, styles, "Capital Intensity Analysis")
        story.append(Paragraph(
            "Capital intensity measures how many dollars of assets it takes to generate a dollar "
            "of revenue (Total Assets ÷ Revenue) — a rough gauge of how “asset-heavy” "
            "a business model is. A ratio of 0.30 means $0.30 of assets are needed to generate $1.00 "
            "of revenue.", styles["Body"],
        ))
        labels = list(cap_intensity.keys())
        story.append(_grid_table(labels, [[f"{cap_intensity[l]:.2f}" for l in labels]], first_col_width=None,
                                  left_align_cols=set()))
        story.append(Paragraph(
            "This tool applies one modeled capital-structure profile per sector. Unlike revenue and "
            "SDE, which are anchored to a real, measured employment/payroll growth rate, there isn't a "
            "comparably grounded way to vary capital intensity by year, so it's shown as a current "
            "estimate by size class rather than a fabricated historical trend.", styles["Caption"],
        ))

        story.append(Paragraph("Reading the ranges", styles["H3"]))
        range_rows = [
            ["Below 0.25", "Light on physical assets — typically service-driven businesses with room to scale without heavy capital spending."],
            ["0.25 – 0.35", "A mix of service and physical operations — some equipment or inventory, but not asset-dominated."],
            ["0.35 – 0.45", "Meaningful equipment or working-capital needs — more established, less nimble to scale quickly."],
            ["Above 0.45", "Asset-heavy — significant infrastructure and higher barriers for a new entrant."],
        ]
        story.append(_grid_table(["Range", "General characteristics"], range_rows, first_col_width=1.3 * inch,
                                  left_align_cols={0, 1}))

        story.append(Paragraph("Why it matters, by audience", styles["H3"]))
        audience_rows = [
            ["Buyers", "A higher ratio usually means more capital tied up in the business before it starts generating a return."],
            ["Investors", "Lower-intensity, asset-light models tend to scale more easily and often command different valuation multiples."],
            ["Lenders", "Higher-intensity businesses typically carry more collateral, but asset quality and liquidity matter just as much as quantity."],
            ["Advisors", "Capital intensity is one input among many — it should inform the valuation approach, not dictate it on its own."],
        ]
        story.append(_grid_table(["Audience", "Why it matters"], audience_rows, first_col_width=1.3 * inch,
                                  left_align_cols={0, 1}))

    # ---- Glossary -----------------------------------------------------------
    # Plain-English definitions for the report's key financial/industry terms.
    # Mirrors the hover-bubble definitions shown on the web report -- a PDF
    # can't support hover, so this appears as a reference table instead of
    # the old per-value "Modeled — footnote 1" marker system.
    story.append(Spacer(1, 10))
    _section_heading(story, styles, "Glossary")
    story.append(Paragraph(
        "Plain-English definitions for the financial and industry terms used throughout this report.",
        styles["Caption"],
    ))
    glossary_rows = [
        ("NAICS", "North American Industry Classification System — the standard code the U.S. Census Bureau and other federal agencies use to classify businesses by industry."),
        ("SDE", "Seller's Discretionary Earnings — total cash flow available to a single owner-operator, including officer compensation, before taxes and financing costs. The standard cash-flow measure used to value small businesses."),
        ("EBITDA", "Earnings Before Interest, Taxes, Depreciation, and Amortization — operating profit before financing costs and non-cash accounting charges."),
        ("Gross Profit / Margin", "Revenue minus the direct cost of goods or services sold; margin expresses this as a percentage of revenue."),
        ("Officers Compensation", "Compensation paid to the business owner(s)/officers. Counted as an expense here but added back into SDE, since it represents owner pay rather than a market-rate employee cost."),
        ("Operating Income", "Gross profit minus all operating expenses (excluding interest and other non-operating items) — profit from core business operations."),
        ("Pre-Tax Net Profit", "Operating income plus or minus interest and other non-operating income or expense, before income taxes."),
        ("Net Working Capital", "Current assets minus current liabilities — the short-term cash cushion available to fund day-to-day operations."),
        ("Current Ratio", "Current assets divided by current liabilities. Above 1.0 generally means short-term obligations are covered by short-term assets."),
        ("Quick Ratio", "Like the current ratio, but excludes inventory (the least liquid current asset) — a stricter test of short-term liquidity."),
        ("Days Payable", "Average number of days it takes the business to pay its suppliers, based on accounts payable and cost of sales."),
        ("Pre-Tax Return on Assets", "Pre-tax profit divided by total assets — how efficiently the business turns its asset base into profit."),
        ("Pre-Tax Return on Net Worth", "Pre-tax profit divided by equity (net worth) — the pre-tax return generated on the owners' invested capital."),
        ("Capital Intensity", "Total assets divided by revenue — a rough measure of how many dollars of assets it takes to generate a dollar of sales. Higher means a more asset-heavy business model."),
        ("Fixed Asset Turnover", "Revenue divided by net fixed assets — how efficiently the business generates sales from its property, plant, and equipment."),
        ("Receivables Turnover", "Revenue divided by accounts receivable. A higher number means the business collects from customers faster."),
        ("Total Asset Turnover", "Revenue divided by total assets — how efficiently the whole asset base is used to generate sales."),
        ("Days Working Capital", "Net working capital expressed in days of revenue — roughly how many days of sales the working capital could cover."),
    ]
    story.append(_grid_table(["Term", "Definition"], glossary_rows, first_col_width=1.7 * inch,
                              left_align_cols={0, 1}))

    # ---- Methodology & Disclosures -----------------------------------------
    story.append(Spacer(1, 10))
    story.append(Paragraph("Methodology & Disclosures", styles["DisclaimerHeading"]))
    disclaimer_paras = []
    if data.get("methodology_note"):
        disclaimer_paras.append(Paragraph(data["methodology_note"], styles["DisclaimerBody"]))
    extra = f"{sources.get('revenue_scaling_assumption', '')} Implied annual growth used for the trend line: {data.get('implied_annual_growth_pct')}%."
    disclaimer_paras.append(Paragraph(extra, styles["DisclaimerBody"]))
    disclaimer_paras.append(Paragraph(
        "This report is generated independently from public U.S. Census Bureau data and general "
        "industry-typical financial assumptions. It is not affiliated with, endorsed by, or derived "
        "from any third-party proprietary benchmark provider. Figures are estimates for general "
        "informational purposes only and should not be used as the sole basis for a valuation, "
        "lending, or investment decision.", styles["DisclaimerBody"],
    ))
    story.append(_card(disclaimer_paras, bg_color=WARN_BG, border_color=WARN_BORDER))

    doc.build(story, canvasmaker=_make_canvas_class(footer_text))
    return buf.getvalue()
