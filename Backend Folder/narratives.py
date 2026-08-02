"""
Auto-generates the short trend sentences shown under each 5-year metric
(e.g. "Revenue grew moderately from $X to $Y from 2020 to 2024"). This is
plain arithmetic + rule-based wording applied to numbers this tool already
computed -- it doesn't add any new data, just describes the modeled trend
in words instead of only a table. Original wording; not copied from any
third-party report template.
"""


def _magnitude_word(pct_change: float) -> str:
    m = abs(pct_change)
    if m < 0.03:
        return "held roughly steady"
    if m < 0.10:
        return "shifted modestly"
    if m < 0.25:
        return "moved notably"
    return "shifted sharply"


def _direction_word(pct_change: float) -> str:
    if pct_change > 0.005:
        return "up"
    if pct_change < -0.005:
        return "down"
    return "flat"


def describe_series(metric_label: str, series_by_year: dict, unit: str = "dollar") -> dict:
    """series_by_year: {year: numeric_value}. unit: 'dollar' or 'pct'."""
    years = sorted(series_by_year)
    if not years:
        return None
    first_year, last_year = years[0], years[-1]
    first_val, last_val = series_by_year[first_year], series_by_year[last_year]
    pct_change = ((last_val - first_val) / first_val) if first_val else 0.0

    if unit == "pct":
        fmt = lambda v: f"{v * 100:.1f}%"
    else:
        fmt = lambda v: f"${v:,.0f}"

    sentence = (
        f"{metric_label} {_magnitude_word(pct_change)} over {first_year}-{last_year}, "
        f"moving {_direction_word(pct_change)} from {fmt(first_val)} to {fmt(last_val)} "
        f"({pct_change * 100:+.1f}%)."
    )

    return {
        "first_year": first_year,
        "last_year": last_year,
        "first_value": first_val,
        "last_value": last_val,
        "pct_change": round(pct_change * 100, 1),
        "sentence": sentence,
    }


def describe_state_vs_national(metric_label: str, state_value: float, national_value: float) -> str:
    if not national_value:
        return f"No national comparison is available for {metric_label.lower()} for this industry."
    gap_pct = (state_value - national_value) / national_value
    if abs(gap_pct) < 0.03:
        return f"{metric_label} in this state is roughly in line with the national figure."
    direction = "above" if gap_pct > 0 else "below"
    return (
        f"{metric_label} in this state is {abs(gap_pct) * 100:.1f}% {direction} "
        f"the national figure of ${national_value:,.0f}."
    )


def _money_compact(v):
    if v is None:
        return "—"
    abs_v = abs(v)
    if abs_v >= 1e9:
        return f"${v / 1e9:.1f}B"
    if abs_v >= 1e6:
        return f"${v / 1e6:.1f}M"
    if abs_v >= 1e3:
        return f"${v / 1e3:.0f}K"
    return f"${v:,.0f}"


# Generic, defensible AI-opportunity framing for each major modeled cost
# line -- kept broad rather than industry-specific, since the underlying
# assumption (which cost line is largest) already comes from this
# industry's real modeled cost structure, not a guess.
_COST_LEVER_LABELS = {
    "cost_of_sales": (
        "the cost of goods and materials sold",
        "AI-assisted demand forecasting, supplier negotiation, and inventory "
        "optimization to reduce material costs and stockouts",
    ),
    "wages_benefits": (
        "labor (wages and benefits)",
        "AI-driven scheduling, workforce forecasting, and task automation to "
        "reduce overtime and improve staffing efficiency",
    ),
    "other_opex": (
        "other operating expenses",
        "AI-powered inventory management, dynamic pricing, and "
        "customer-service automation (chatbots and self-service tools) to "
        "streamline day-to-day operations",
    ),
}


def build_five_year_outlook(sector_label: str, naics_label: str, state_name: str,
                             income_stmt: dict, trends: dict, projection: dict) -> str:
    """Composes a short, data-grounded 5-year outlook paragraph from figures
    this tool already computes -- real BLS/Census growth and AI-adoption
    rates (industry_trends.py), the calculated revenue projection, and this
    industry's own modeled cost structure (financial_model.py). It doesn't
    introduce any new data source; it just narrates numbers already in the
    report, plus a generic (not fabricated) AI-opportunity framing pointed
    at whichever modeled cost line is largest for this sector."""
    nat = (trends or {}).get("national") or {}
    sec = (trends or {}).get("sector") or {}
    has_sector = bool((trends or {}).get("sector_has_data"))

    def _pick(key):
        if has_sector and sec.get(key) is not None:
            return sec[key]
        return nat.get(key)

    emp_growth = _pick("employment_growth_2024_2034_pct")
    demand_growth = _pick("output_growth_2024_2034_pct")
    ai_current = _pick("ai_current_use_pct")
    ai_expected = _pick("ai_expected_use_pct")

    sentences = []

    growth_bits = []
    if emp_growth is not None:
        growth_bits.append(f"employment projected to grow {emp_growth:+.1f}%")
    if demand_growth is not None:
        growth_bits.append(f"real demand (output) up {demand_growth:+.1f}%")
    if growth_bits:
        sentences.append(
            f"Looking out over the 2024–2034 window, the outlook for "
            f"{naics_label or 'this industry'} is {' and '.join(growth_bits)} "
            f"nationally—a modestly expansionary backdrop for operators in "
            f"{state_name}."
        )

    if projection and projection.get("projected_revenue"):
        sentences.append(
            f"Extending this tool's modeled revenue estimate forward at that "
            f"pace points to roughly {_money_compact(projection['projected_revenue'])} "
            f"in average per-firm revenue by {projection['target_year']}—a "
            f"directional calculation, not a forecast guarantee."
        )

    if ai_current is not None:
        infancy = (
            f"AI adoption is still in its infancy in this space: only "
            f"{ai_current:.1f}% of businesses report using it in any function today"
        )
        if ai_expected is not None:
            infancy += f", with {ai_expected:.1f}% expecting to adopt it within six months"
        infancy += "."
        sentences.append(infancy)

    revenue = (income_stmt or {}).get("revenue") or 0
    if revenue:
        opex = income_stmt.get("opex", {})
        candidates = {
            "cost_of_sales": income_stmt.get("cost_of_sales") or 0,
            "wages_benefits": (opex.get("salary_and_wages") or 0) + (opex.get("benefits_and_pensions") or 0),
            "other_opex": opex.get("other_expenses") or 0,
        }
        top_key = max(candidates, key=candidates.get)
        top_pct = candidates[top_key] / revenue * 100
        top_label, ai_use_case = _COST_LEVER_LABELS[top_key]
        sentences.append(
            f"For a {(sector_label or 'business').lower()}-type operation, {top_label} is the "
            f"largest lever on profitability here, running roughly {top_pct:.0f}% of revenue in "
            f"this tool's modeled structure—{ai_use_case} is where early AI adoption is most "
            f"likely to move the needle, before broader adoption narrows the competitive edge it "
            f"offers today."
        )

    return " ".join(sentences)
