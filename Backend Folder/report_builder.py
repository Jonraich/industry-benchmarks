"""Assembles the final JSON report payload served to the frontend."""
from datetime import datetime

import census_client
from naics_sectors import get_profile
from states import STATE_NAMES
import financial_model as fm


def build_report(naics_code: str, state_abbr: str, api_key: str = None) -> dict:
    profile = get_profile(naics_code)

    econ_state = census_client.fetch_economic_census(naics_code, state_abbr, api_key)
    econ_national = census_client.fetch_economic_census_national(naics_code, api_key)
    cbp_latest = census_client.fetch_cbp(naics_code, state_abbr, api_key=api_key)

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

    income_statement = fm.build_income_statement(latest_average_revenue, profile)
    history, implied_growth = fm.build_history(
        latest_average_revenue,
        state_employment_latest,
        state_employment_2022,
        profile,
        end_year=latest_year,
    )

    capital_intensity_assumption = 1 / (1 - profile["inventory_pct"]) * 0.30 \
        if profile["inventory_pct"] else 0.27
    balance_sheet = fm.build_balance_sheet(latest_average_revenue, profile, capital_intensity_assumption)
    ratios = fm.build_ratios(income_statement, balance_sheet)

    size_classes = fm.build_size_class_estimates(latest_average_revenue, profile)

    national_average_revenue = None
    if econ_national and econ_national.get("revenue_thousands"):
        national_firms = econ_national.get("firms") or econ_national.get("establishments")
        if national_firms:
            national_average_revenue = (econ_national["revenue_thousands"] * 1000) / national_firms

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
            "average_revenue_per_firm": round(latest_average_revenue),
            "national_average_revenue_per_firm": round(national_average_revenue) if national_average_revenue else None,
        },
        "income_statement_latest": income_statement,
        "income_statement_history": history,
        "balance_sheet": balance_sheet,
        "financial_ratios": ratios,
        "size_class_estimates": size_classes,
        "implied_annual_growth_pct": round(implied_growth * 100, 2),
    }
