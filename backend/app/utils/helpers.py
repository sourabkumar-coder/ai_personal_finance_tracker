from datetime import date
import calendar


def format_currency(amount: float, currency: str = "INR") -> str:
    """Format a numeric amount as a readable currency string."""
    return f"{currency} {amount:,.2f}"


def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage safely handling zero total."""
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 2)


def get_current_month_range(year: int = None, month: int = None):
    """Return start date and end date for a given or current month."""
    today = date.today()
    target_year = year or today.year
    target_month = month or today.month

    start_date = date(target_year, target_month, 1)
    last_day = calendar.monthrange(target_year, target_month)[1]
    end_date = date(target_year, target_month, last_day)

    return start_date, end_date
