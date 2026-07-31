"""Assembles the final JSON report payload served to the frontend."""
from datetime import datetime

import census_client
import industry_trends
import narratives
from naics_sectors import get_profile
from states import STATE_NAMES
import financial_model as fm

METRIC_LABELS = {
    "revenue": "Revenue",
    "sde": "SDE (Cash Flow)",
    "ebitda": "EBITDA",
    "gross_profit": "Gross Profit",
    "pretax_net_profit": "Pre-Tax Net Profit",
}


def _build_industry_description(naics_code: str, naics_label: str, sector_label: str) -> str:
    label = naics_label or f"NAICS {naics_code}"
    return (
        f"This report covers businesses classified under NAICS {naics_code} "
        f"({label}) as reported to the U.S. Census Bureau. For the modeled "
        f"financial detail (income statement, balance sheet, and ratios), "
        f"this tool applies typical operating characteristics for the "
        f'broader "{sector_label}" sector, since Census does not publish '
        f"detailed profit-and-loss or balance-sheet data at the individual "
        f"industry level."
    )


def build_report(naics_code: str, state_abbr: str, api_key: str = None) -> dict:
    profile = get_profile(naics_code)

    econ_state = census_client.fetch_economic_census(naics_code, state_abbr, api_key)
    econ_national = census_client.fetch_economic_census_national(naics_code, api_key)
    cbp_latest = census_client.fetch_cbp(naics_code, state_abbr, api_key=api_key)
    cbp_national = census_client.fetch_cbp_national(naics_code, api_key=api_key)

    if not econ_state or not econ_state.get("revenue_thousands"):
        return {
            "error": (
                f"No 2022 Economic Census revenue data was published for NAICS "
                f"{naics_code} in {STATE_NAMES.get(state_abbr.upper(), state_abbr)}. "
                "This happens for small/rare industry-state combinations where the "
                "Census Bureau suppresses data to protect firm confidentiality. "
                "Try a broader NAICS code (fewer digits) or a larger state."
            )
        }

    state_revenue_total = econ_state["revenue_thousands"] * 1000
    state_firms = econ_state.get("firms") or econ_state["establishments"] or 1
    state_employment_2022 = econ_state["employment"]
    state_employment_latest = (cbp_latest or {}).get("employment") or state_employment_2022

    # Census publishes aggregate totals (revenue, firm count), not a median --
    # this is a true AVERAGE (mean) revenue per firm, not a median.
    average_revenue_per_firm = state_revenue_total / state_firms

    # Scale 2022 revenue forward to the latest CBP year using payroll growth,
    # a modeled assumption (documented to the user).
    growth_factor = 1.0
    if cbp_latest and econ_state.get("annual_payroll_thousands") and cbp_latest.get("annual_payroll_thousands"):
        old_payroll = econ_state["annual_payroll_thousands"]
        new_payroll = cbp_latest["annual_payroll_thousands"]
        if old_payroll:
            growth_factor = new_payroll / old_payroll
            growth_factor = max(min(growth_factor, 1.5), 0.7)  # sanity clamp

    latest_average_revenue = average_revenue_per_firm * growth_factor
    latest_year = cbp_latest["year"] if cbp_latest else econ_state["year"]

    capital_intensity_assumption = 1 / (1 - profile["inventory_pct"]) * 0.30 \
        if profile["inventory_pct"] else 0.27

    income_statement = fm.build_income_statement(latest_average_revenue, profile)
    balance_sheet = fm.build_balance_sheet(latest_average_revenue, profile, capital_intensity_assumption)
    ratios = fm.build_ratios(income_statement, balance_sheet)

    implied_annual_growth = fm.implied_growth_rate(state_employment_latest, state_employment_2022)
    income_statement_history, balance_sheet_history, ratios_history = fm.build_history(
        latest_average_revenue, implied_annual_growth, profile,
        capital_intensity_assumption, end_year=latest_year,
    )

    size_classes = fm.build_size_class_estimates(latest_average_revenue, profile)
    size_class_history = fm.build_size_class_history(
        latest_average_revenue, profile, implied_annual_growth, end_year=latest_year,
    )
    firm_distribution = fm.build_firm_distribution(state_firms)
    capital_intensity_by_size = fm.build_capital_intensity_by_size(capital_intensity_assumption)

    total_sde = round(state_firms * income_statement["sde"])
    total_net_income = round(state_firms * income_statement["pretax_net_profit"])

    # --- National comparison (real Census revenue, scaled/modeled the same
    # way as the state figures so the two are methodologically consistent) ---
    national_average_revenue = None
    national_firms = None
    if econ_national and econ_national.get("revenue_thousands"):
        national_firms = econ_national.get("firms") or econ_national.get("establishments")
        if national_firms:
            national_average_revenue = (econ_national["revenue_thousands"] * 1000) / national_firms

    national_growth_factor = 1.0
    if cbp_national and econ_national and econ_national.get("annual_payroll_thousands") and cbp_national.get("annual_payroll_thousands"):
        old_p = econ_national["annual_payroll_thousands"]
        new_p = cbp_national["annual_payroll_thousands"]
        if old_p:
            national_growth_factor = new_p / old_p
            national_growth_factor = max(min(national_growth_factor, 1.5), 0.7)

    latest_national_average_revenue = (
        national_average_revenue * national_growth_factor if national_average_revenue else None
    )

    national_income_statement = None
    national_income_statement_history = {}
    if latest_national_average_revenue:
        national_income_statement = fm.build_income_statement(latest_national_average_revenue, profile)
        national_employment_2022 = econ_national.get("employment") if econ_national else None
        national_employment_latest = (cbp_national or {}).get("employment") or national_employment_2022
        implied_annual_growth_national = fm.implied_growth_rate(
            national_employment_latest, national_employment_2022
        )
        national_income_statement_history, _, _ = fm.build_history(
            latest_national_average_revenue, implied_annual_growth_national, profile,
            capital_intensity_assumption, end_year=latest_year,
        )

    # --- Per-metric state trend + state-vs-national narrative sentences ---
    metric_trends = {}
    for key, label in METRIC_LABELS.items():
        state_series = {year: stmt[key] for year, stmt in income_statement_history.items()}
        national_series = (
            {year: stmt[key] for year, stmt in national_income_statement_history.items()}
            if national_income_statement_history else {}
        )
        metric_trends[key] = {
            "label": label,
            "state_history": state_series,
            "national_history": national_series,
            "state_trend": narratives.describe_series(label, state_series),
            "vs_national_note": narratives.describe_state_vs_national(
                label, income_statement[key],
                national_income_statement[key] if national_income_statement else None,
            ),
        }

    industry_description = _build_industry_description(
        naics_code, econ_state.get("naics_label"), profile["label"]
    )

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "methodology_note": (
            "Firm counts, total revenue, employment, and payroll for the selected "
            "state and industry are sourced directly from the U.S. Census Bureau "
            "(2022 Economic Census and County Business Patterns). Income statement "
            "detail, balance sheet structure, SDE/EBITDA, and financial ratios are "
            "MODELED using industry-typical margin and capital-structure assumptions "
            "for this NAICS sector -- they are reasonable estimates, not measured "
            "figures, and should be treated as directional benchmarks."
        ),
        "industry": {
            "naics_code": naics_code,
            "naics_label": econ_state.get("naics_label"),
            "sector_profile_used": profile["label"],
        },
        "industry_description": industry_description,
        "geography": {
            "state": state_abbr.upper(),
            "state_name": STATE_NAMES.get(state_abbr.upper(), state_abbr),
        },
        "data_sources": {
            "economic_census_year": econ_state["year"],
            "cbp_year": latest_year,
            "revenue_scaling_assumption": (
                f"2022 Economic Census revenue scaled to {latest_year} using "
                f"{round((growth_factor - 1) * 100, 1)}% payroll growth (CBP)."
            ),
        },
        "industry_at_a_glance": {
            "total_firms": state_firms,
            "total_revenue": state_revenue_total,
            "total_employment": state_employment_2022,
            "total_payroll": (econ_state.get("annual_payroll_thousands") or 0) * 1000,
            "total_sde": total_sde,
            "total_net_income": total_net_income,
            "average_revenue_per_firm": round(latest_average_revenue),
            "national_average_revenue_per_firm": round(latest_national_average_revenue) if latest_national_average_revenue else None,
            "firm_distribution": firm_distribution,
        },
        "income_statement_latest": income_statement,
        "income_statement_history": income_statement_history,
        "balance_sheet": balance_sheet,
        "balance_sheet_history": balance_sheet_history,
        "financial_ratios": ratios,
        "ratios_history": ratios_history,
        "size_class_estimates": size_classes,
        "size_class_history": size_class_history,
        "capital_intensity_by_size": capital_intensity_by_size,
        "metric_trends": metric_trends,
        "national_income_statement_latest": national_income_statement,
        "implied_annual_growth_pct": round(implied_annual_growth * 100, 2),
        "industry_trends": industry_trends.get_trend(naics_code),
        "revenue_projection": industry_trends.project_revenue(
            latest_average_revenue, latest_year, naics_code
        ),
    }
