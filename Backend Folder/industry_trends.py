"""
Real, cited data on industry-level demand outlook, growth/decline, and AI
adoption.

Unlike the modeled financial-statement section (naics_sectors.py), every
number in this module is a real, published, government-sourced statistic:

- Employment growth 2024-2034: U.S. Bureau of Labor Statistics, Employment
  Projections news release, Aug. 28, 2025.
  https://www.bls.gov/news.release/ecopro.nr0.htm
  (BLS content is a U.S. government work and is in the public domain.)

- Real output (demand-side) growth 2024-2034: same BLS Employment
  Projections release, "Employment and output by industry" table (Table
  2.11) and "Industries with the fastest growing output" table (Table 2.7).
  Output is measured in billions of chained 2017 dollars -- it's the
  production/demand-side complement to the employment figures above, and
  can grow faster or slower than employment depending on productivity
  change (e.g. retail trade output is projected to grow while retail
  employment shrinks, because automation lets fewer workers produce more
  sales volume).
  https://www.bls.gov/emp/tables/industry-employment-and-output.htm
  https://www.bls.gov/emp/tables/industries-fast-grow-output.htm

- AI adoption rates: U.S. Census Bureau, Business Trends and Outlook Survey
  (BTOS), "AI Use at U.S. Businesses" (America Counts story), May 26, 2026,
  and the BTOS AI Supplement data dashboard.
  https://www.census.gov/library/stories/2026/05/ai-use-businesses.html
  https://www.census.gov/hfp/btos/data

Neither BLS nor Census expose these specific figures through a simple,
stable queryable API, so this is a periodically-refreshed curated snapshot
rather than a live call, unlike the revenue/employment data in
census_client.py. Update AS_OF and the figures below when new releases come
out (BLS Employment Projections: roughly every 2 years; Census BTOS AI
data: ongoing, published every couple of weeks).

Where a sector doesn't have a separately published figure, that field is
None and the caller/frontend should fall back to the national baseline,
clearly labeled as a fallback rather than a sector-specific measurement.
Where BLS only publishes output data for a piece of a sector (e.g. private
education, or a handful of health care sub-industries) rather than the
whole 2-digit sector, that's noted in the text rather than presented as if
it were the full-sector figure.
"""

AS_OF = (
    "Snapshot as of July 2026. Employment and output growth figures are "
    "from BLS Employment Projections 2024-2034 (released Aug. 28, 2025). "
    "AI adoption figures are from Census BTOS data through May 2026."
)

SOURCE_GROWTH = "U.S. Bureau of Labor Statistics, Employment Projections 2024-34"
SOURCE_GROWTH_URL = "https://www.bls.gov/news.release/ecopro.nr0.htm"
SOURCE_OUTPUT = "U.S. Bureau of Labor Statistics, Employment and Output by Industry, 2024-34"
SOURCE_OUTPUT_URL = "https://www.bls.gov/emp/tables/industry-employment-and-output.htm"
SOURCE_AI = "U.S. Census Bureau, Business Trends and Outlook Survey (BTOS)"
SOURCE_AI_URL = "https://www.census.gov/library/stories/2026/05/ai-use-businesses.html"

NATIONAL_BASELINE = {
    "employment_growth_2024_2034_pct": 3.1,
    "growth_note": (
        "U.S. total employment is projected to grow 3.1% (5.2 million jobs) "
        "from 2024 to 2034 -- slower than the 13.0% growth recorded over "
        "the prior decade (2014-2024)."
    ),
    "output_growth_2024_2034_pct": 1.9,
    "output_growth_note": (
        "U.S. total real output (GDP, in constant dollars) is projected to "
        "grow 1.9% per year from 2024 to 2034 -- this is the demand-side "
        "complement to the employment figure above. A sector can show "
        "rising demand (output) alongside flat or falling employment if "
        "productivity is improving faster than demand is growing."
    ),
    "ai_current_use_pct": 19.8,
    "ai_expected_use_pct": 21.5,
    "ai_note": (
        "Nationally, AI usage among businesses ran 17-20% between December "
        "2025 and May 2026, with 20-23% of businesses expecting to use AI "
        "in some business function within the next six months."
    ),
}

# Keyed by 2-digit NAICS sector prefix (same convention as naics_sectors.py).
SECTOR_TRENDS = {
    "21": {  # Mining, Quarrying, and Oil & Gas Extraction
        "employment_growth_2024_2034_pct": -1.6,
        "growth_note": (
            "Projected to decline 1.6% from 2024-2034, driven in part by "
            "productivity gains from automation and robotics (e.g. drones) "
            "used in extraction."
        ),
        "output_growth_2024_2034_pct": 1.2,
        "output_growth_note": (
            "Real output (production value) is still projected to grow "
            "1.2% per year through 2034 even as employment falls -- demand "
            "for what the sector produces is rising, it just takes fewer "
            "workers to produce it."
        ),
        "ai_current_use_pct": None,
        "ai_expected_use_pct": None,
        "ai_note": None,
    },
    "31": {  # Manufacturing
        "employment_growth_2024_2034_pct": 0.0,
        "growth_note": (
            "Manufacturing employment is projected to be essentially flat "
            "(0.0% from 2024-2034), with growth in some subsectors (food, "
            "computer/electronics) offset by declines in others (apparel, "
            "textiles, printing)."
        ),
        "output_growth_2024_2034_pct": 1.3,
        "output_growth_note": (
            "Real output is projected to grow 1.3% per year through 2034 "
            "despite flat headcount -- production is expected to grow "
            "through automation and productivity gains rather than more "
            "workers."
        ),
        "ai_current_use_pct": None,
        "ai_expected_use_pct": None,
        "ai_note": (
            "Census separately tracks AI adoption for Manufacturing in its "
            "sector breakdown; a specific current rate wasn't published in "
            "the most recent summary available."
        ),
    },
    "44": {  # Retail Trade
        "employment_growth_2024_2034_pct": -1.2,
        "growth_note": (
            "Projected to lose more jobs than any other sector (-1.2% from "
            "2024-2034) as automation, consolidation, and e-commerce "
            "continue to reduce demand for retail sales occupations."
        ),
        "output_growth_2024_2034_pct": 2.4,
        "output_growth_note": (
            "Despite the projected job losses, real output (sales volume "
            "in constant dollars) is projected to grow 2.4% per year "
            "through 2034 -- consumer demand for retail goods is still "
            "rising, it's just being met with fewer workers per dollar of "
            "sales as automation and e-commerce raise productivity."
        ),
        "ai_current_use_pct": 14.0,
        "ai_expected_use_pct": 17.0,
        "ai_note": (
            "Below-average AI adoption: about 14% of Retail Trade firms "
            "reported current use versus the 19.8% national rate, though "
            "AI integration in sales and customer service is cited as a "
            "factor in the sector's projected employment decline."
        ),
    },
    "48": {  # Transportation & Warehousing
        "employment_growth_2024_2034_pct": 3.0,
        "growth_note": (
            "Projected to grow 3.0% from 2024-2034, close to the "
            "economy-wide average, supported by continued growth in "
            "e-commerce parcel and delivery volume."
        ),
        "output_growth_2024_2034_pct": 2.2,
        "output_growth_note": (
            "Real output (freight and delivery volume, in constant "
            "dollars) is projected to grow 2.2% per year through 2034, "
            "tracking closely with the sector's employment growth."
        ),
        "ai_current_use_pct": None,
        "ai_expected_use_pct": None,
        "ai_note": None,
    },
    "51": {  # Information
        "employment_growth_2024_2034_pct": 6.5,
        "growth_note": (
            "Projected to grow 6.5% from 2024-2034, among the fastest of "
            "any sector -- demand for AI-based systems, data processing, "
            "and software development is a primary driver."
        ),
        "output_growth_2024_2034_pct": 3.3,
        "output_growth_note": (
            "Real output is projected to grow 3.3% per year through 2034, "
            "among the fastest of any sector -- software publishing alone "
            "(+5.0%/yr) is one of the single fastest-growing industries in "
            "the entire economy by output."
        ),
        "ai_current_use_pct": 39.7,
        "ai_expected_use_pct": 42.0,
        "ai_note": (
            "The highest AI adoption of any sector Census tracks: 39.7% of "
            "Information-sector firms reported using AI in the two weeks "
            "before the survey, roughly double the national rate."
        ),
    },
    "52": {  # Finance & Insurance
        "employment_growth_2024_2034_pct": 3.4,
        "growth_note": (
            "Employment is projected to grow 3.4% from 2024-2034, close to "
            "the economy-wide average."
        ),
        "output_growth_2024_2034_pct": 2.0,
        "output_growth_note": (
            "Real output for finance and insurance is projected to grow "
            "2.0% per year through 2034."
        ),
        "ai_current_use_pct": 33.9,
        "ai_expected_use_pct": 39.0,
        "ai_note": (
            "The second-highest AI adoption of any sector Census tracks: "
            "33.9% of firms reported current use, well above the 19.8% "
            "national rate."
        ),
    },
    "54": {  # Professional, Scientific & Technical Services
        "employment_growth_2024_2034_pct": 7.5,
        "growth_note": (
            "Projected to grow 7.5% from 2024-2034 -- demand for AI "
            "development, data analysis, research, and associated "
            "consulting services is a primary driver."
        ),
        "output_growth_2024_2034_pct": 2.3,
        "output_growth_note": (
            "Real output is projected to grow 2.3% per year through 2034 "
            "-- notably slower than the sector's 7.5% employment growth, "
            "meaning much of the added headcount goes toward "
            "labor-intensive service delivery rather than a proportional "
            "rise in output per worker. Computer systems design specifically "
            "is one of the fastest-growing industries in the economy by "
            "output (+3.2%/yr)."
        ),
        "ai_current_use_pct": None,
        "ai_expected_use_pct": None,
        "ai_note": (
            "Census separately tracks AI adoption for this sector; a "
            "specific current rate wasn't published in the most recent "
            "summary available, though the sector's growth is explicitly "
            "tied to AI-related demand."
        ),
    },
    "61": {  # Educational Services
        "employment_growth_2024_2034_pct": 0.1,
        "growth_note": (
            "Total educational services employment (public and private "
            "combined) is projected to be essentially flat (+0.1% from "
            "2024-2034); the private-education subset is projected to grow "
            "faster, at +1.9%."
        ),
        "output_growth_2024_2034_pct": 1.4,
        "output_growth_note": (
            "BLS doesn't publish a combined real-output figure across "
            "public and private education (public-sector output isn't "
            "measured in dollar terms the same way). For the private "
            "education subset specifically, real output is projected to "
            "grow 1.4% per year through 2034."
        ),
        "ai_current_use_pct": None,
        "ai_expected_use_pct": None,
        "ai_note": (
            "Census separately tracks AI adoption for this sector; a "
            "specific current rate wasn't published in the most recent "
            "summary available."
        ),
    },
    "62": {  # Health Care & Social Assistance
        "employment_growth_2024_2034_pct": 8.4,
        "growth_note": (
            "Projected to be the fastest-growing sector in the economy "
            "(+8.4% from 2024-2034), driven primarily by an aging "
            "population and rising chronic-disease prevalence -- a "
            "demographic driver rather than an AI-related one."
        ),
        "output_growth_2024_2034_pct": None,
        "output_growth_note": (
            "BLS doesn't publish a single combined real-output figure for "
            "the health care and social assistance sector, but several of "
            "its sub-industries are among the fastest-growing in the "
            "entire economy by output through 2034: individual and family "
            "services (+4.0%/yr), home health care services (+3.9%/yr), "
            "offices of other health practitioners (+3.6%/yr), outpatient "
            "care centers (+3.5%/yr), and offices of physicians (+3.3%/yr)."
        ),
        "ai_current_use_pct": None,
        "ai_expected_use_pct": None,
        "ai_note": None,
    },
}

_ALIASES = {  # mirrors naics_sectors.py's sector aliasing
    "32": "31", "33": "31",
    "45": "44",
    "49": "48",
}


def get_trend(naics_code: str) -> dict:
    prefix = (naics_code or "")[:2]
    prefix = _ALIASES.get(prefix, prefix)
    sector = SECTOR_TRENDS.get(prefix)
    return {
        "as_of": AS_OF,
        "sources": {
            "employment_growth": {"label": SOURCE_GROWTH, "url": SOURCE_GROWTH_URL},
            "output_growth": {"label": SOURCE_OUTPUT, "url": SOURCE_OUTPUT_URL},
            "ai_adoption": {"label": SOURCE_AI, "url": SOURCE_AI_URL},
        },
        "national": NATIONAL_BASELINE,
        "sector": sector,
        "sector_has_data": sector is not None,
    }


PROJECTION_TARGET_YEAR = 2034


def project_revenue(latest_revenue: float, latest_year: int, naics_code: str) -> dict:
    """Calculated projection (NOT a government figure): applies the real,
    published BLS demand-side (output) growth rate for this industry to the
    Census-derived average-revenue estimate, to show roughly where that
    revenue figure would land by 2034 if it grows in line with the
    industry's overall demand trend.

    This combines two real, cited inputs (Census revenue + BLS output
    growth) into one derived number -- it is a calculation performed by
    this tool, not a statistic published by Census or BLS, and is labeled
    as such wherever it's displayed.
    """
    prefix = (naics_code or "")[:2]
    prefix = _ALIASES.get(prefix, prefix)
    sector = SECTOR_TRENDS.get(prefix)

    if sector and sector.get("output_growth_2024_2034_pct") is not None:
        rate_pct = sector["output_growth_2024_2034_pct"]
        basis = "sector-specific BLS output growth rate"
    else:
        rate_pct = NATIONAL_BASELINE["output_growth_2024_2034_pct"]
        basis = "national-average BLS output growth rate (sector-specific figure not published)"

    years = max(PROJECTION_TARGET_YEAR - latest_year, 0)
    projected_revenue = latest_revenue * ((1 + rate_pct / 100) ** years) if latest_revenue else None

    return {
        "base_year": latest_year,
        "target_year": PROJECTION_TARGET_YEAR,
        "years_projected": years,
        "annual_growth_rate_pct_used": rate_pct,
        "growth_rate_basis": basis,
        "base_revenue": latest_revenue,
        "projected_revenue": round(projected_revenue) if projected_revenue is not None else None,
    }
