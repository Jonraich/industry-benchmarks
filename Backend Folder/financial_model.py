"""
Builds the full benchmark report: real Census figures for revenue, firm
counts, employment and payroll, plus a MODELED income statement, balance
sheet, and ratio set derived from a sector-typical margin/structure profile
(see naics_sectors.py).

Every number that is not sourced directly from a Census field is tagged
"modeled" in the output payload so the frontend can label it clearly.
"""
from naics_sectors import get_profile

HISTORY_YEARS = 5


def _pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round(numerator / denominator, 4)


def build_income_statement(revenue: float, profile: dict) -> dict:
    cogs = revenue * profile["cogs_pct"]
    gross_profit = revenue - cogs

    officer_comp = revenue * profile["officer_comp_pct"]
    wages = revenue * profile["wages_pct"]
    benefits = revenue * profile["benefits_pct"]
    rent = revenue * profile["rent_pct"]
    other_opex = revenue * profile["other_opex_pct"]
    da = revenue * profile["da_pct"]
    total_opex = officer_comp + wages + benefits + rent + other_opex + da

    operating_income = gross_profit - total_opex

    interest_income = revenue * profile["interest_income_pct"]
    interest_expense = revenue * profile["interest_expense_pct"]
    other_income = revenue * profile["other_income_pct"]
    net_other = interest_income - interest_expense + other_income

    pretax_profit = operating_income + net_other

    ebitda = operating_income + da
    sde = ebitda + officer_comp  # standard small-business valuation definition

    return {
        "revenue": revenue,
        "cost_of_sales": cogs,
        "gross_profit": gross_profit,
        "opex": {
            "officers_compensation": officer_comp,
            "salary_and_wages": wages,
            "benefits_and_pensions": benefits,
            "rent": rent,
            "other_expenses": other_opex,
            "depreciation_and_amortization": da,
            "total": total_opex,
        },
        "operating_income": operating_income,
        "other": {
            "interest_income": interest_income,
            "interest_expense": interest_expense,
            "other_income": other_income,
            "net": net_other,
        },
        "pretax_net_profit": pretax_profit,
        "ebitda": ebitda,
        "sde": sde,
    }


def build_balance_sheet(revenue: float, profile: dict, capital_intensity: float) -> dict:
    """capital_intensity = total_assets / revenue (modeled or derived)."""
    total_assets = revenue * capital_intensity

    cash = total_assets * profile["cash_pct"]
    receivables = total_assets * profile["receivables_pct"]
    inventory = total_assets * profile["inventory_pct"]
    other_ca = total_assets * profile["other_ca_pct"]
    total_ca = cash + receivables + inventory + other_ca

    gross_fixed = total_assets * profile["gross_fixed_pct"]
    accum_dep = total_assets * profile["accum_dep_pct"]
    net_fixed = gross_fixed - accum_dep
    other_nca = total_assets * profile["other_nca_pct"]

    computed_total = total_ca + net_fixed + other_nca
    # normalize so components sum exactly to total_assets
    scale = total_assets / computed_total if computed_total else 1

    ap = total_assets * profile["ap_pct"] * scale
    notes_payable = total_assets * profile["notes_payable_pct"] * scale
    other_cl = total_assets * profile["other_cl_pct"] * scale
    total_cl = ap + notes_payable + other_cl

    lt_liab = total_assets * profile["lt_liab_pct"] * scale
    total_liab = total_cl + lt_liab
    equity = total_assets - total_liab

    return {
        "total_assets": total_assets,
        "current_assets": {
            "cash": cash * scale, "receivables": receivables * scale,
            "inventory": inventory * scale, "other": other_ca * scale,
            "total": total_ca * scale,
        },
        "fixed_assets": {
            "gross": gross_fixed * scale, "accumulated_depreciation": accum_dep * scale,
            "net": net_fixed * scale,
        },
        "other_non_current_assets": other_nca * scale,
        "current_liabilities": {
            "accounts_payable": ap, "notes_payable": notes_payable,
            "other": other_cl, "total": total_cl,
        },
        "long_term_liabilities": lt_liab,
        "total_liabilities": total_liab,
        "equity": equity,
    }


def build_ratios(income_stmt: dict, balance_sheet: dict) -> dict:
    ca = balance_sheet["current_assets"]["total"]
    cl = balance_sheet["current_liabilities"]["total"]
    inventory = balance_sheet["current_assets"]["inventory"]
    receivables = balance_sheet["current_assets"]["receivables"]
    ap = balance_sheet["current_liabilities"]["accounts_payable"]
    total_assets = balance_sheet["total_assets"]
    equity = balance_sheet["equity"]
    net_fixed = balance_sheet["fixed_assets"]["net"]
    revenue = income_stmt["revenue"]
    cogs = income_stmt["cost_of_sales"]

    current_ratio = _pct(ca, cl) if cl else None
    quick_ratio = _pct(ca - inventory, cl) if cl else None
    days_payable = round((ap / cogs) * 365, 1) if cogs else None
    net_working_capital = ca - cl

    ebitda_margin = _pct(income_stmt["ebitda"], revenue)
    pretax_roa = _pct(income_stmt["pretax_net_profit"], total_assets)
    pretax_ronw = _pct(income_stmt["pretax_net_profit"], equity) if equity else None
    gross_margin = _pct(income_stmt["gross_profit"], revenue)

    assets_to_revenue = _pct(total_assets, revenue)
    fixed_asset_turnover = _pct(revenue, net_fixed) if net_fixed else None
    receivables_turnover = _pct(revenue, receivables) if receivables else None
    total_asset_turnover = _pct(revenue, total_assets)
    days_working_capital = round((net_working_capital / revenue) * 365, 1) if revenue else None

    return {
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "days_payable": days_payable,
        "net_working_capital": net_working_capital,
        "ebitda_margin_pct": ebitda_margin,
        "pretax_return_on_assets_pct": pretax_roa,
        "pretax_return_on_net_worth_pct": pretax_ronw,
        "gross_margin_pct": gross_margin,
        "assets_to_revenue": assets_to_revenue,
        "fixed_asset_turnover": fixed_asset_turnover,
        "receivables_turnover": receivables_turnover,
        "total_asset_turnover": total_asset_turnover,
        "days_working_capital": days_working_capital,
        "capital_intensity": assets_to_revenue,
    }


def implied_growth_rate(latest_employment: float, cbp_employment_prior: float) -> float:
    """Shared growth-rate estimator used for both state and national modeled
    trends: derives an annual growth rate from the real 4-year change in CBP
    employment (a genuine, measured signal), clamped to a sane range, with a
    conservative flat-ish default when the employment data isn't available."""
    if cbp_employment_prior and latest_employment and cbp_employment_prior > 0:
        rate = (latest_employment / cbp_employment_prior) ** (1 / 4) - 1
        return max(min(rate, 0.08), -0.05)
    return 0.015  # conservative default assumption


def build_history(latest_revenue: float, implied_annual_growth: float, profile: dict,
                   capital_intensity: float, years: int = HISTORY_YEARS, end_year: int = 2024):
    """
    Builds a HISTORY_YEARS-long series ending at `latest_revenue`, with a
    matching income statement, balance sheet, and ratio set for each year.
    Prior years are modeled by applying `implied_annual_growth` (see
    implied_growth_rate() above) backward from the latest year. This is
    explicitly a MODELED trend, not measured history -- Census's revenue
    figure (Economic Census) only exists for census years.
    """
    income_statement_history = {}
    balance_sheet_history = {}
    ratios_history = {}
    for i in range(years):
        year = end_year - (years - 1 - i)
        periods_back = years - 1 - i
        revenue = latest_revenue / ((1 + implied_annual_growth) ** periods_back)
        income_stmt = build_income_statement(revenue, profile)
        bs = build_balance_sheet(revenue, profile, capital_intensity)
        ratios = build_ratios(income_stmt, bs)
        income_statement_history[year] = income_stmt
        balance_sheet_history[year] = bs
        ratios_history[year] = ratios
    return income_statement_history, balance_sheet_history, ratios_history


# Shared revenue multipliers for the <$1M / $1M-$5M / $5M-$25M size-class
# breakdown shown in typical benchmark reports. Census's size-class data
# (SUSB) is bucketed by EMPLOYEE count, not revenue, so this maps the
# industry's typical revenue distribution using modeled multipliers around
# the state average. Modeled -- used for both the current-year table and
# the 5-year size-class history below, so both stay internally consistent.
SIZE_CLASS_REVENUE_MULTIPLIERS = {
    "<$1M": lambda avg: min(avg * 0.35, 900_000),
    "$1M - $5M": lambda avg: max(avg * 0.95, 1_200_000),
    "$5M - $25M": lambda avg: max(avg * 4.2, 6_000_000),
}

# Modeled share of firms falling into each size class, used only to turn a
# real total-firm count into an estimated distribution (Census does not
# publish firm counts by REVENUE size class at the NAICS+state level -- SUSB
# breaks firms out by employee count instead). This is a general small-
# business distribution assumption, not sector-specific, and is labeled
# "Modeled" wherever it's shown.
SIZE_CLASS_FIRM_SHARE = {
    "<$1M": 0.60,
    "$1M - $5M": 0.32,
    "$5M - $25M": 0.08,
}


def build_size_class_estimates(average_revenue: float, profile: dict):
    return {
        label: build_income_statement(fn(average_revenue), profile)
        for label, fn in SIZE_CLASS_REVENUE_MULTIPLIERS.items()
    }


def build_size_class_history(average_revenue: float, profile: dict, implied_annual_growth: float,
                              years: int = HISTORY_YEARS, end_year: int = 2024):
    """5-year modeled income-statement history for each size class, using the
    same implied growth rate as the overall state trend so the size-class
    lines and the state-level line stay consistent with each other."""
    result = {}
    for label, fn in SIZE_CLASS_REVENUE_MULTIPLIERS.items():
        latest_class_revenue = fn(average_revenue)
        yearly = {}
        for i in range(years):
            year = end_year - (years - 1 - i)
            periods_back = years - 1 - i
            revenue = latest_class_revenue / ((1 + implied_annual_growth) ** periods_back)
            yearly[year] = build_income_statement(revenue, profile)
        result[label] = yearly
    return result


def build_firm_distribution(total_firms: int):
    """Modeled count + percentage of firms in each size class. The last
    bucket absorbs any rounding remainder so the counts always sum exactly
    to total_firms."""
    labels = list(SIZE_CLASS_FIRM_SHARE.keys())
    dist = {}
    running_total = 0
    for label in labels[:-1]:
        share = SIZE_CLASS_FIRM_SHARE[label]
        count = round(total_firms * share)
        running_total += count
        dist[label] = {"count": count, "pct": round(share * 100, 1)}
    last_label = labels[-1]
    last_count = max(total_firms - running_total, 0)
    dist[last_label] = {
        "count": last_count,
        "pct": round((last_count / total_firms) * 100, 1) if total_firms else 0.0,
    }
    return dist


def build_capital_intensity_by_size(capital_intensity_base: float):
    """Modeled variation of capital intensity (assets/revenue) by size
    class. Larger firms in most retail/service industries carry somewhat
    more fixed infrastructure relative to revenue than very small firms, so
    this applies a modest upward slope around the sector's base capital-
    intensity assumption. Shown as a single current estimate rather than a
    5-year table: unlike revenue/SDE/EBITDA (which we can model a trend for
    using real employment growth), we don't have a comparably grounded way
    to vary a capital-structure ratio year over year, so we don't fabricate
    one."""
    return {
        "<$1M": round(capital_intensity_base * 0.85, 3),
        "$1M - $5M": round(capital_intensity_base * 1.0, 3),
        "$5M - $25M": round(capital_intensity_base * 1.25, 3),
        "All Sizes": round(capital_intensity_base, 3),
    }
