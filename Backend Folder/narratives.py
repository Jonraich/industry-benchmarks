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
