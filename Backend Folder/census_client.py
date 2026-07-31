"""
Thin client around the Census Bureau Data API.

Two real datasets back this tool:

1. Economic Census - Basic (``ecnbasic``), most recent full run = 2022.
   This is the only Census series with actual REVENUE (RCPTOT) by NAICS
   code and state. It runs every 5 years (years ending in 2 and 7).

2. County Business Patterns (``cbp``), published annually.
   No revenue, but gives current-year establishment counts, employment,
   and annual payroll -- used to (a) show the latest available snapshot
   and (b) scale the 2022 Economic Census revenue figure forward to the
   latest CBP year using payroll growth as a proxy (an assumption, clearly
   labeled as such by the caller).

A free Census API key is required: https://api.census.gov/data/key_signup.html
"""
import os
import requests

from states import STATE_FIPS

CENSUS_BASE = "https://api.census.gov/data"
ECON_CENSUS_YEAR = 2022   # most recent Economic Census with revenue data
CBP_YEAR = 2023           # most recent County Business Patterns release


class CensusAPIError(RuntimeError):
    pass


def _get_key(api_key: str = None) -> str:
    key = api_key or os.environ.get("CENSUS_API_KEY")
    if not key:
        raise CensusAPIError(
            "No Census API key provided. Set CENSUS_API_KEY or pass ?key= "
            "on the request. Get a free key at "
            "https://api.census.gov/data/key_signup.html"
        )
    return key


def _request(url: str, params: dict):
    resp = requests.get(url, params=params, timeout=20)
    if resp.status_code == 204:
        # Census returns "204 No Content" (rather than a 200 with an empty
        # array) for some NAICS + geography combinations where the data is
        # suppressed or simply doesn't exist at that granularity. Treat this
        # the same as "no rows found" rather than raising an error.
        return []
    if resp.status_code != 200:
        raise CensusAPIError(f"Census API error {resp.status_code}: {resp.text[:300]}")
    if not resp.text.strip():
        return []
    data = resp.json()
    header, *rows = data
    return [dict(zip(header, row)) for row in rows]


def fetch_economic_census(naics_code: str, state_abbr: str, api_key: str = None):
    """Real revenue/establishment/employment figures for a NAICS code + state,
    from the most recent Economic Census (2022)."""
    key = _get_key(api_key)
    state_fips = STATE_FIPS.get(state_abbr.upper())
    if not state_fips:
        raise CensusAPIError(f"Unknown state abbreviation: {state_abbr}")

    url = f"{CENSUS_BASE}/{ECON_CENSUS_YEAR}/ecnbasic"
    params = {
        # 2022 Economic Census uses 2022-vintage NAICS variable names.
        "get": "NAICS2022_LABEL,NAME,FIRM,ESTAB,RCPTOT,EMP,PAYANN",
        "for": f"state:{state_fips}",
        "NAICS2022": naics_code,
        "key": key,
    }
    rows = _request(url, params)
    if not rows:
        return None
    row = rows[0]
    return {
        "year": ECON_CENSUS_YEAR,
        "naics_label": row.get("NAICS2022_LABEL"),
        "state_name": row.get("NAME"),
        "firms": _safe_int(row.get("FIRM")),
        "establishments": _safe_int(row.get("ESTAB")),
        "revenue_thousands": _safe_int(row.get("RCPTOT")),
        "employment": _safe_int(row.get("EMP")),
        "annual_payroll_thousands": _safe_int(row.get("PAYANN")),
    }


def fetch_economic_census_national(naics_code: str, api_key: str = None):
    """Same as above but for the whole United States (used for state-vs-national)."""
    key = _get_key(api_key)
    url = f"{CENSUS_BASE}/{ECON_CENSUS_YEAR}/ecnbasic"
    params = {
        "get": "NAICS2022_LABEL,NAME,FIRM,ESTAB,RCPTOT,EMP,PAYANN",
        "for": "us:*",
        "NAICS2022": naics_code,
        "key": key,
    }
    rows = _request(url, params)
    if not rows:
        return None
    row = rows[0]
    return {
        "year": ECON_CENSUS_YEAR,
        "firms": _safe_int(row.get("FIRM")),
        "establishments": _safe_int(row.get("ESTAB")),
        "revenue_thousands": _safe_int(row.get("RCPTOT")),
        "employment": _safe_int(row.get("EMP")),
        "annual_payroll_thousands": _safe_int(row.get("PAYANN")),
    }


def fetch_cbp(naics_code: str, state_abbr: str, year: int = CBP_YEAR, api_key: str = None):
    """Latest-year establishment/employment/payroll snapshot (no revenue)."""
    key = _get_key(api_key)
    state_fips = STATE_FIPS.get(state_abbr.upper())
    if not state_fips:
        raise CensusAPIError(f"Unknown state abbreviation: {state_abbr}")

    url = f"{CENSUS_BASE}/{year}/cbp"
    params = {
        "get": "ESTAB,EMP,PAYANN,NAICS2017_LABEL",
        "for": f"state:{state_fips}",
        "NAICS2017": naics_code,
        "key": key,
    }
    rows = _request(url, params)
    if not rows:
        return None
    row = rows[0]
    return {
        "year": year,
        "establishments": _safe_int(row.get("ESTAB")),
        "employment": _safe_int(row.get("EMP")),
        "annual_payroll_thousands": _safe_int(row.get("PAYANN")),
    }


def _safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
