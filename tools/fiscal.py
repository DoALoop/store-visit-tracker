"""
Walmart Fiscal Week Helper Functions
"""

from datetime import date, timedelta


def get_fiscal_week_number(week_start_date):
    """Calculate fiscal week number (Week 1 starts January 31st)"""
    year = week_start_date.year

    fiscal_year_start = date(year, 1, 31)
    if week_start_date < fiscal_year_start:
        fiscal_year_start = date(year - 1, 1, 31)

    # Find the first Saturday on or after Jan 31
    days_to_saturday = (5 - fiscal_year_start.weekday()) % 7
    first_saturday = fiscal_year_start + timedelta(days=days_to_saturday)

    days_since_start = (week_start_date - first_saturday).days
    week_number = (days_since_start // 7) + 1

    return week_number


def get_monday_from_fiscal_week(week_number, year=None):
    """Convert a fiscal week number to the Monday of that week"""
    if year is None:
        year = date.today().year

    fiscal_year_start = date(year, 1, 31)
    today = date.today()

    # Handle high week numbers before Jan 31 (previous fiscal year)
    if today < fiscal_year_start and week_number > 40:
        fiscal_year_start = date(year - 1, 1, 31)

    # Calculate the Saturday that starts this fiscal week
    days_to_saturday = (5 - fiscal_year_start.weekday()) % 7
    first_saturday = fiscal_year_start + timedelta(days=days_to_saturday)

    # Get the Saturday for the requested week
    target_saturday = first_saturday + timedelta(weeks=week_number - 1)

    # Return the Monday of that week (Saturday + 2 days)
    target_monday = target_saturday + timedelta(days=2)

    return target_monday
