"""
NAICS sector -> financial profile mapping.

Census data (Economic Census / County Business Patterns / SUSB) gives us real,
government-sourced figures for: number of firms, total revenue (receipts),
employment, and annual payroll, broken out by NAICS code and state.

Census does NOT publish income-statement detail (cost of sales, officer
compensation, EBITDA, SDE), balance-sheet structure, or financial ratios for
individual industries. Those sections of this tool are MODELED using
typical/representative margin and balance-sheet structures for each broad
NAICS sector. The assumptions below are informed by widely-cited public
benchmarking sources (e.g., NYU Stern/Damodaran industry margin data, IRS
Statistics of Income corporate financial ratios, and general small-business
valuation practice for SDE) -- not from any proprietary/licensed dataset.
They are reasonable industry-typical estimates, not measured facts, and the
tool labels them as such everywhere they appear.

All percentages are expressed as a fraction of revenue (income statement) or
a fraction of total assets (balance sheet), matching the convention used in
common financial benchmark reports.
"""

# Fallback profile used when a NAICS code's 2-digit sector isn't in the table.
DEFAULT_PROFILE = {
    "label": "All Industries (general)",
    "cogs_pct": 0.55,
    "officer_comp_pct": 0.05,
    "wages_pct": 0.14,
    "benefits_pct": 0.02,
    "rent_pct": 0.04,
    "other_opex_pct": 0.12,
    "da_pct": 0.02,
    "interest_expense_pct": 0.01,
    "interest_income_pct": 0.001,
    "other_income_pct": 0.01,
    # Balance sheet, as % of total assets
    "cash_pct": 0.12,
    "receivables_pct": 0.10,
    "inventory_pct": 0.15,
    "other_ca_pct": 0.03,
    "gross_fixed_pct": 0.35,
    "accum_dep_pct": 0.18,
    "other_nca_pct": 0.44,
    "ap_pct": 0.08,
    "notes_payable_pct": 0.05,
    "other_cl_pct": 0.05,
    "lt_liab_pct": 0.15,
}

# Keyed by 2-digit NAICS sector prefix.
SECTOR_PROFILES = {
    "23": {  # Construction
        "label": "Construction",
        "cogs_pct": 0.72, "officer_comp_pct": 0.04, "wages_pct": 0.09,
        "benefits_pct": 0.015, "rent_pct": 0.015, "other_opex_pct": 0.06,
        "da_pct": 0.015, "interest_expense_pct": 0.008, "interest_income_pct": 0.001,
        "other_income_pct": 0.008,
        "cash_pct": 0.14, "receivables_pct": 0.22, "inventory_pct": 0.06,
        "other_ca_pct": 0.04, "gross_fixed_pct": 0.28, "accum_dep_pct": 0.14,
        "other_nca_pct": 0.40, "ap_pct": 0.14, "notes_payable_pct": 0.05,
        "other_cl_pct": 0.08, "lt_liab_pct": 0.14,
    },
    "31": {  # Manufacturing (31-33)
        "label": "Manufacturing",
        "cogs_pct": 0.65, "officer_comp_pct": 0.035, "wages_pct": 0.12,
        "benefits_pct": 0.02, "rent_pct": 0.015, "other_opex_pct": 0.07,
        "da_pct": 0.025, "interest_expense_pct": 0.01, "interest_income_pct": 0.001,
        "other_income_pct": 0.008,
        "cash_pct": 0.10, "receivables_pct": 0.16, "inventory_pct": 0.22,
        "other_ca_pct": 0.03, "gross_fixed_pct": 0.38, "accum_dep_pct": 0.20,
        "other_nca_pct": 0.31, "ap_pct": 0.09, "notes_payable_pct": 0.05,
        "other_cl_pct": 0.06, "lt_liab_pct": 0.18,
    },
    "42": {  # Wholesale Trade
        "label": "Wholesale Trade",
        "cogs_pct": 0.78, "officer_comp_pct": 0.03, "wages_pct": 0.08,
        "benefits_pct": 0.012, "rent_pct": 0.012, "other_opex_pct": 0.055,
        "da_pct": 0.01, "interest_expense_pct": 0.008, "interest_income_pct": 0.001,
        "other_income_pct": 0.008,
        "cash_pct": 0.10, "receivables_pct": 0.20, "inventory_pct": 0.24,
        "other_ca_pct": 0.03, "gross_fixed_pct": 0.20, "accum_dep_pct": 0.10,
        "other_nca_pct": 0.33, "ap_pct": 0.13, "notes_payable_pct": 0.04,
        "other_cl_pct": 0.06, "lt_liab_pct": 0.12,
    },
    "44": {  # Retail Trade (44-45) -- matches the sample "Clothing and Clothing
             # Accessories Retailers" example
        "label": "Retail Trade",
        "cogs_pct": 0.59, "officer_comp_pct": 0.045, "wages_pct": 0.12,
        "benefits_pct": 0.01, "rent_pct": 0.045, "other_opex_pct": 0.13,
        "da_pct": 0.01, "interest_expense_pct": 0.01, "interest_income_pct": 0.001,
        "other_income_pct": 0.012,
        "cash_pct": 0.05, "receivables_pct": 0.04, "inventory_pct": 0.15,
        "other_ca_pct": 0.02, "gross_fixed_pct": 0.12, "accum_dep_pct": 0.07,
        "other_nca_pct": 0.71, "ap_pct": 0.06, "notes_payable_pct": 0.02,
        "other_cl_pct": 0.03, "lt_liab_pct": 0.06,
    },
    "48": {  # Transportation & Warehousing (48-49)
        "label": "Transportation & Warehousing",
        "cogs_pct": 0.62, "officer_comp_pct": 0.035, "wages_pct": 0.14,
        "benefits_pct": 0.02, "rent_pct": 0.02, "other_opex_pct": 0.08,
        "da_pct": 0.035, "interest_expense_pct": 0.012, "interest_income_pct": 0.001,
        "other_income_pct": 0.008,
        "cash_pct": 0.09, "receivables_pct": 0.16, "inventory_pct": 0.04,
        "other_ca_pct": 0.03, "gross_fixed_pct": 0.48, "accum_dep_pct": 0.25,
        "other_nca_pct": 0.29, "ap_pct": 0.08, "notes_payable_pct": 0.06,
        "other_cl_pct": 0.05, "lt_liab_pct": 0.20,
    },
    "51": {  # Information
        "label": "Information",
        "cogs_pct": 0.40, "officer_comp_pct": 0.06, "wages_pct": 0.18,
        "benefits_pct": 0.025, "rent_pct": 0.03, "other_opex_pct": 0.15,
        "da_pct": 0.035, "interest_expense_pct": 0.008, "interest_income_pct": 0.002,
        "other_income_pct": 0.01,
        "cash_pct": 0.22, "receivables_pct": 0.14, "inventory_pct": 0.02,
        "other_ca_pct": 0.04, "gross_fixed_pct": 0.30, "accum_dep_pct": 0.16,
        "other_nca_pct": 0.44, "ap_pct": 0.07, "notes_payable_pct": 0.03,
        "other_cl_pct": 0.06, "lt_liab_pct": 0.16,
    },
    "52": {  # Finance & Insurance
        "label": "Finance & Insurance",
        "cogs_pct": 0.30, "officer_comp_pct": 0.06, "wages_pct": 0.20,
        "benefits_pct": 0.03, "rent_pct": 0.03, "other_opex_pct": 0.16,
        "da_pct": 0.015, "interest_expense_pct": 0.015, "interest_income_pct": 0.01,
        "other_income_pct": 0.015,
        "cash_pct": 0.25, "receivables_pct": 0.18, "inventory_pct": 0.0,
        "other_ca_pct": 0.05, "gross_fixed_pct": 0.14, "accum_dep_pct": 0.07,
        "other_nca_pct": 0.45, "ap_pct": 0.05, "notes_payable_pct": 0.03,
        "other_cl_pct": 0.07, "lt_liab_pct": 0.14,
    },
    "53": {  # Real Estate & Rental/Leasing
        "label": "Real Estate & Rental/Leasing",
        "cogs_pct": 0.35, "officer_comp_pct": 0.04, "wages_pct": 0.10,
        "benefits_pct": 0.015, "rent_pct": 0.02, "other_opex_pct": 0.14,
        "da_pct": 0.06, "interest_expense_pct": 0.03, "interest_income_pct": 0.001,
        "other_income_pct": 0.012,
        "cash_pct": 0.08, "receivables_pct": 0.06, "inventory_pct": 0.01,
        "other_ca_pct": 0.02, "gross_fixed_pct": 0.62, "accum_dep_pct": 0.22,
        "other_nca_pct": 0.43, "ap_pct": 0.04, "notes_payable_pct": 0.08,
        "other_cl_pct": 0.04, "lt_liab_pct": 0.32,
    },
    "54": {  # Professional, Scientific & Technical Services
        "label": "Professional, Scientific & Technical Services",
        "cogs_pct": 0.32, "officer_comp_pct": 0.08, "wages_pct": 0.22,
        "benefits_pct": 0.03, "rent_pct": 0.035, "other_opex_pct": 0.14,
        "da_pct": 0.015, "interest_expense_pct": 0.006, "interest_income_pct": 0.002,
        "other_income_pct": 0.01,
        "cash_pct": 0.20, "receivables_pct": 0.28, "inventory_pct": 0.0,
        "other_ca_pct": 0.05, "gross_fixed_pct": 0.14, "accum_dep_pct": 0.08,
        "other_nca_pct": 0.41, "ap_pct": 0.08, "notes_payable_pct": 0.02,
        "other_cl_pct": 0.07, "lt_liab_pct": 0.10,
    },
    "56": {  # Administrative & Support Services
        "label": "Administrative & Support Services",
        "cogs_pct": 0.45, "officer_comp_pct": 0.05, "wages_pct": 0.20,
        "benefits_pct": 0.025, "rent_pct": 0.025, "other_opex_pct": 0.12,
        "da_pct": 0.015, "interest_expense_pct": 0.008, "interest_income_pct": 0.001,
        "other_income_pct": 0.008,
        "cash_pct": 0.14, "receivables_pct": 0.22, "inventory_pct": 0.02,
        "other_ca_pct": 0.03, "gross_fixed_pct": 0.20, "accum_dep_pct": 0.11,
        "other_nca_pct": 0.50, "ap_pct": 0.09, "notes_payable_pct": 0.03,
        "other_cl_pct": 0.06, "lt_liab_pct": 0.12,
    },
    "61": {  # Educational Services
        "label": "Educational Services",
        "cogs_pct": 0.30, "officer_comp_pct": 0.06, "wages_pct": 0.28,
        "benefits_pct": 0.04, "rent_pct": 0.04, "other_opex_pct": 0.13,
        "da_pct": 0.02, "interest_expense_pct": 0.008, "interest_income_pct": 0.002,
        "other_income_pct": 0.01,
        "cash_pct": 0.20, "receivables_pct": 0.12, "inventory_pct": 0.01,
        "other_ca_pct": 0.03, "gross_fixed_pct": 0.34, "accum_dep_pct": 0.16,
        "other_nca_pct": 0.46, "ap_pct": 0.06, "notes_payable_pct": 0.03,
        "other_cl_pct": 0.06, "lt_liab_pct": 0.14,
    },
    "62": {  # Health Care & Social Assistance
        "label": "Health Care & Social Assistance",
        "cogs_pct": 0.42, "officer_comp_pct": 0.07, "wages_pct": 0.24,
        "benefits_pct": 0.035, "rent_pct": 0.03, "other_opex_pct": 0.10,
        "da_pct": 0.02, "interest_expense_pct": 0.009, "interest_income_pct": 0.001,
        "other_income_pct": 0.01,
        "cash_pct": 0.15, "receivables_pct": 0.22, "inventory_pct": 0.05,
        "other_ca_pct": 0.03, "gross_fixed_pct": 0.26, "accum_dep_pct": 0.13,
        "other_nca_pct": 0.49, "ap_pct": 0.07, "notes_payable_pct": 0.03,
        "other_cl_pct": 0.06, "lt_liab_pct": 0.14,
    },
    "71": {  # Arts, Entertainment & Recreation
        "label": "Arts, Entertainment & Recreation",
        "cogs_pct": 0.45, "officer_comp_pct": 0.05, "wages_pct": 0.16,
        "benefits_pct": 0.015, "rent_pct": 0.04, "other_opex_pct": 0.13,
        "da_pct": 0.03, "interest_expense_pct": 0.012, "interest_income_pct": 0.001,
        "other_income_pct": 0.012,
        "cash_pct": 0.10, "receivables_pct": 0.06, "inventory_pct": 0.06,
        "other_ca_pct": 0.03, "gross_fixed_pct": 0.48, "accum_dep_pct": 0.24,
        "other_nca_pct": 0.31, "ap_pct": 0.07, "notes_payable_pct": 0.04,
        "other_cl_pct": 0.05, "lt_liab_pct": 0.18,
    },
    "72": {  # Accommodation & Food Services
        "label": "Accommodation & Food Services",
        "cogs_pct": 0.33, "officer_comp_pct": 0.05, "wages_pct": 0.26,
        "benefits_pct": 0.02, "rent_pct": 0.06, "other_opex_pct": 0.14,
        "da_pct": 0.025, "interest_expense_pct": 0.012, "interest_income_pct": 0.001,
        "other_income_pct": 0.01,
        "cash_pct": 0.09, "receivables_pct": 0.03, "inventory_pct": 0.06,
        "other_ca_pct": 0.02, "gross_fixed_pct": 0.52, "accum_dep_pct": 0.27,
        "other_nca_pct": 0.35, "ap_pct": 0.08, "notes_payable_pct": 0.05,
        "other_cl_pct": 0.05, "lt_liab_pct": 0.19,
    },
    "81": {  # Other Services (except Public Administration)
        "label": "Other Services",
        "cogs_pct": 0.42, "officer_comp_pct": 0.06, "wages_pct": 0.16,
        "benefits_pct": 0.015, "rent_pct": 0.035, "other_opex_pct": 0.12,
        "da_pct": 0.015, "interest_expense_pct": 0.009, "interest_income_pct": 0.001,
        "other_income_pct": 0.012,
        "cash_pct": 0.13, "receivables_pct": 0.10, "inventory_pct": 0.08,
        "other_ca_pct": 0.03, "gross_fixed_pct": 0.28, "accum_dep_pct": 0.14,
        "other_nca_pct": 0.48, "ap_pct": 0.07, "notes_payable_pct": 0.03,
        "other_cl_pct": 0.05, "lt_liab_pct": 0.13,
    },
}

# Aliases so 2-digit prefixes that share a sector (31-33, 44-45, 48-49) all resolve.
_ALIASES = {
    "32": "31", "33": "31",
    "45": "44",
    "49": "48",
}


def get_profile(naics_code: str) -> dict:
    """Return the financial modeling profile for a NAICS code, using the
    2-digit sector prefix, with aliasing for split ranges (31-33, 44-45, 48-49)."""
    prefix = (naics_code or "")[:2]
    prefix = _ALIASES.get(prefix, prefix)
    return SECTOR_PROFILES.get(prefix, DEFAULT_PROFILE)
