"""
Real, cited data on industry-level employment outlook and AI adoption.

Unlike the modeled financial-statement section (naics_sectors.py), every
number in this module is a real, published, government-sourced statistic:

- Employment growth 2024-2034: U.S. Bureau of Labor Statistics, Employment
  Projections news release, Aug. 28, 2025.
  https://www.bls.gov/news.release/ecopro.nr0.htm
  (BLS content is a U.S. government work and is in the public domain.)

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
"""

AS_OF = (
    "Snapshot as of July 2026. Employment growth figures are from BLS "
    "Employment Projections 2024-2034 (released Aug. 28, 2025). AI adoption "
    "figures are from Census BTOS data through May 2026."
)

SOURCE_GROWTH = "U.S. Bureau of Labor Statistics, Employment Projections 2024-34"
SOURCE_GROWTH_URL = "https://www.bls.gov/news.release/ecopro.nr0.htm"
SOURCE_AI = "U.S. Census Bureau, Business Trends and Outlook Survey (BTOS)"
SOURCE_AI_URL = "https://www.census.gov/library/stories/2026/05/ai-use-businesses.html"

NATIONAL_BASELINE = {
    "employment_growth_2024_2034_pct": 3.1,
    "growth_note": (
        "U.S. total employment is projected to grow 3.1% (5.2 million jobs) "
        "from 2024 to 2034 -- slower than the 13.0% growth recorded over "
        "the prior decade (2014-2024)."
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
        "ai_current_use_pct": None,
        "ai_expected_use_pct": None,
        "ai_note": None,
    },
    "31": {  # Manufacturing
        "employment_growth_2024_2034_pct": None,
        "growth_note": None,
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
        "ai_current_use_pct": 39.7,
        "ai_expected_use_pct": 42.0,
        "ai_note": (
            "The highest AI adoption of any sector Census tracks: 39.7% of "
            "Information-sector firms reported using AI in the two weeks "
            "before the survey, roughly double the national rate."
        ),
    },
    "52": {  # Finance & Insurance
        "employment_growth_2024_2034_pct": None,
        "growth_note": None,
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
        "employment_growth_2024_2034_pct": None,
        "growth_note": None,
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
            "ai_adoption": {"label": SOURCE_AI, "url": SOURCE_AI_URL},
        },
        "national": NATIONAL_BASELINE,
        "sector": sector,
        "sector_has_data": sector is not None,
    }
