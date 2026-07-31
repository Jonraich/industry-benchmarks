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
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
)

ACCENT = colors.HexColor("#0f7a63")
ACCENT_DARK = colors.HexColor("#0a5a49")
INK = colors.HexColor("#12212b")
SUB = colors.HexColor("#5b6b74")
LINE = colors.HexColor("#dfe6ea")
WARN_BG = colors.HexColor("#fff6e5")


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
        name="ReportTitle", fontSize=19, textColor=ACCENT_DARK,
        fontName="Helvetica-Bold", spaceAfter=4, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="SubTitle", fontSize=9.5, textColor=SUB, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="H2", fontSize=13.5, textColor=INK, fontName="Helvetica-Bold",
        spaceBefore=18, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="H3", fontSize=10.5, textColor=SUB, fontName="Helvetica-Bold",
        spaceBefore=12, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="H4", fontSize=9.5, textColor=INK, fontName="Helvetica-Bold",
        spaceBefore=8, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Body", fontSize=9.3, textColor=INK, leading=13.5, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Caption", fontSize=8.2, textColor=SUB, leading=11.5, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="DisclaimerHeading", fontSize=11, textColor=colors.HexColor("#5c4a12"),
        fontName="Helvetica-Bold", spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="DisclaimerBody", fontSize=8.5, textColor=colors.HexColor("#5c4a12"),
        leading=12, spaceAfter=6,
    ))
    return styles


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------

def _kv_table(rows, value_width=1.6 * inch):
    """Two-column label/value table (used for At-a-Glance and Ratios)."""
    t = Table(rows, colWidths=[None, value_width])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _grid_table(header, rows, bold_rows=None, first_col_width=2.3 * inch):
    """Header row + data rows, used for multi-column (year-by-year or
    size-class) tables. bold_rows is a set of row indices (0-based, into
    `rows`) to bold/underline as subtotal-style rows."""
    bold_rows = bold_rows or set()
    data = [header] + rows
    n_cols = len(header)
    col_widths = [first_col_width] + [None] * (n_cols - 1)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 7.6),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), SUB),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for idx in bold_rows:
        row = idx + 1  # +1 to account for header row
        style.append(("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    return t


def _section_heading(story, styles, text):
    story.append(Paragraph(text, styles["H2"]))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    industry = data["industry"]
    geo = data["geography"]
    doc_title = f"{industry.get('naics_label', 'Industry')} — {geo['state_name']} Benchmark Report"

    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.65 * inch, rightMargin=0.65 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
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
    if data.get("industry_description"):
        story.append(Paragraph(data["industry_description"], styles["Body"]))

    # ---- At a Glance --------------------------------------------------
    _section_heading(story, styles, "At a Glance")
    story.append(Paragraph("Average per firm", styles["H3"]))
    avg_rows = [
        [f"Est. average revenue / firm, {geo['state_name']} ({sources['cbp_year']})",
         money_compact(g["average_revenue_per_firm"])],
        ["National average revenue / firm", money_compact(g.get("national_average_revenue_per_firm"))],
    ]
    if is_ and is_.get("sde") is not None:
        avg_rows.append([f"Est. average SDE / firm, {geo['state_name']} (modeled)", money_compact(is_["sde"])])
    if ns and ns.get("sde") is not None:
        avg_rows.append(["National average SDE / firm (modeled)", money_compact(ns["sde"])])
    story.append(_kv_table(avg_rows))

    story.append(Paragraph("Industry totals", styles["H3"]))
    totals_rows = [
        ["Firms (2022 Economic Census)", num(g["total_firms"])],
        ["Total industry revenue", money_compact(g["total_revenue"])],
        ["Total employment", num(g["total_employment"])],
        ["Total annual payroll", money_compact(g["total_payroll"])],
        ["Total SDE, all firms (modeled)", money_compact(g["total_sde"])],
        ["Total net income, all firms (modeled)", money_compact(g["total_net_income"])],
    ]
    story.append(_kv_table(totals_rows))

    dist = g.get("firm_distribution") or {}
    if dist:
        story.append(Paragraph("Firms Distribution by Sales Class (modeled)", styles["H3"]))
        rows = [[label, num(v["count"]), f"{v['pct']:.1f}%"] for label, v in dist.items()]
        rows.append(["Total", num(g["total_firms"]), "100.0%"])
        story.append(_grid_table(["Sales Class", "Firms", "% of Total"], rows, bold_rows={len(rows) - 1}))

    # ---- Industry Trends & AI Outlook ---------------------------------
    trends = data.get("industry_trends")
    projection = data.get("revenue_projection")
    if trends:
        story.append(PageBreak())
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
        story.append(_grid_table(["Metric", "Value", "Basis"], trend_rows, first_col_width=3.1 * inch))
        for note in (growth_note, demand_note, ai_note):
            if note:
                story.append(Paragraph(note, styles["Caption"]))

        if projection and projection.get("projected_revenue"):
            story.append(Paragraph(
                f"<b>Calculated projection:</b> {money(projection['projected_revenue'])} by {projection['target_year']} "
                f"&mdash; projected average revenue per firm, growing this industry's estimated "
                f"{money(projection['base_revenue'])} ({projection['base_year']}) forward at "
                f"{projection['annual_growth_rate_pct_used']}%/year, the {projection['growth_rate_basis']} "
                f"for real demand growth. This isn't a Census/BLS figure &mdash; it's calculated by this tool "
                f"and should be treated as directional, not a forecast guarantee.",
                styles["Body"],
            ))
        if trends.get("as_of"):
            story.append(Paragraph(trends["as_of"], styles["Caption"]))

    # ---- Revenue & SDE 5-Year trend (table instead of chart) ----------
    is_history = data.get("income_statement_history") or {}
    if is_history:
        story.append(Paragraph("Revenue & SDE Trend, 5-Year (modeled)", styles["H3"]))
        years = sorted(is_history.keys())
        rev_row = ["Revenue"] + [money(is_history[y]["revenue"]) for y in years]
        sde_row = ["SDE"] + [money(is_history[y]["sde"]) for y in years]
        ebitda_row = ["EBITDA"] + [money(is_history[y]["ebitda"]) for y in years]
        story.append(_grid_table(["Metric"] + [str(y) for y in years], [rev_row, sde_row, ebitda_row]))
        story.append(Paragraph(
            "5-year series modeled from the latest average-revenue estimate using observed "
            "employment growth. Not measured year-by-year data.", styles["Caption"],
        ))

    # ---- State vs. National Benchmarks ---------------------------------
    metric_trends = data.get("metric_trends") or {}
    if metric_trends:
        story.append(Paragraph("State vs. National Benchmarks, 5-Year (modeled)", styles["H3"]))
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
            story.append(_grid_table(["Year"] + [str(y) for y in years], rows))
            if mt.get("state_trend") and mt["state_trend"].get("sentence"):
                story.append(Paragraph(mt["state_trend"]["sentence"], styles["Caption"]))
            if mt.get("vs_national_note"):
                story.append(Paragraph(mt["vs_national_note"], styles["Caption"]))

    # ---- Income Statement (latest year) --------------------------------
    story.append(PageBreak())
    _section_heading(story, styles, "Income Statement (modeled)")
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
    story.append(_grid_table(["Line Item", "Amount", "% of Revenue"], grid_rows, bold_rows=bold_idx))

    # ---- Balance Sheet (latest year) ------------------------------------
    story.append(Paragraph("Balance Sheet (modeled)", styles["H2"]))
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
    story.append(_grid_table(["Line Item", "Amount", "% of Assets"], grid_rows, bold_rows=bold_idx))

    # ---- Income Statement, 5-Year --------------------------------------
    if is_history:
        story.append(PageBreak())
        _section_heading(story, styles, "Income Statement, 5-Year (modeled)")
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
        story.append(_grid_table(["Line item"] + [str(y) for y in years], grid_rows, bold_rows=bold_idx))

    # ---- Balance Sheet, 5-Year ------------------------------------------
    bs_history = data.get("balance_sheet_history") or {}
    if bs_history:
        story.append(Paragraph("Balance Sheet, 5-Year (modeled)", styles["H2"]))
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
        story.append(_grid_table(["Line item"] + [str(y) for y in years], grid_rows, bold_rows=bold_idx))

    # ---- Financial Ratios (merged latest-year + NWC trend) --------------
    story.append(PageBreak())
    _section_heading(story, styles, "Financial Ratios (modeled)")
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
        story.append(_kv_table(table_rows, value_width=2.6 * inch))

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
        story.append(PageBreak())
        _section_heading(story, styles, "By Revenue Size Class (modeled)")
        story.append(Paragraph("Estimated SDE and EBITDA by size class, scaled from the sector profile.", styles["Caption"]))
        labels = list(size_classes.keys())
        metric_rows = [
            ["Revenue"] + [money(size_classes[l]["revenue"]) for l in labels],
            ["Gross Profit"] + [money(size_classes[l]["gross_profit"]) for l in labels],
            ["EBITDA"] + [money(size_classes[l]["ebitda"]) for l in labels],
            ["SDE"] + [money(size_classes[l]["sde"]) for l in labels],
        ]
        story.append(_grid_table(["Metric"] + labels, metric_rows))

    # ---- By Revenue Size Class, 5-Year ------------------------------------
    size_history = data.get("size_class_history") or {}
    if size_history:
        story.append(Paragraph("By Revenue Size Class, 5-Year (modeled)", styles["H2"]))
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
            story.append(_grid_table(["Sales Class"] + [str(y) for y in years] + [f"{years[0]}–{years[-1]}"], rows))

    # ---- Capital Intensity Analysis ---------------------------------------
    cap_intensity = data.get("capital_intensity_by_size") or {}
    if cap_intensity:
        story.append(PageBreak())
        _section_heading(story, styles, "Capital Intensity Analysis (modeled)")
        story.append(Paragraph(
            "Capital intensity measures how many dollars of assets it takes to generate a dollar "
            "of revenue (Total Assets ÷ Revenue) — a rough gauge of how “asset-heavy” "
            "a business model is. A ratio of 0.30 means $0.30 of assets are needed to generate $1.00 "
            "of revenue.", styles["Body"],
        ))
        labels = list(cap_intensity.keys())
        story.append(_grid_table(labels, [[f"{cap_intensity[l]:.2f}" for l in labels]], first_col_width=None))
        story.append(Paragraph(
            "This tool applies one modeled capital-structure profile per sector. Unlike revenue and "
            "SDE, which are anchored to a real, measured employment/payroll growth rate, there isn't a "
            "comparably grounded way to vary capital intensity by year, so it's shown as a current "
            "estimate by size class rather than a fabricated historical trend.", styles["Caption"],
        ))

    # ---- Methodology & Disclosures -----------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("Methodology & Disclosures", styles["DisclaimerHeading"]))
    if data.get("methodology_note"):
        story.append(Paragraph(data["methodology_note"], styles["DisclaimerBody"]))
    extra = f"{sources.get('revenue_scaling_assumption', '')} Implied annual growth used for the trend line: {data.get('implied_annual_growth_pct')}%."
    story.append(Paragraph(extra, styles["DisclaimerBody"]))
    story.append(Paragraph(
        "This report is generated independently from public U.S. Census Bureau data and general "
        "industry-typical financial assumptions. It is not affiliated with, endorsed by, or derived "
        "from any third-party proprietary benchmark provider. Figures are estimates for general "
        "informational purposes only and should not be used as the sole basis for a valuation, "
        "lending, or investment decision.", styles["DisclaimerBody"],
    ))

    doc.build(story)
    return buf.getvalue()
