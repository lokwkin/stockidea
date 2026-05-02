from datetime import datetime, timedelta


def next_monday(date: datetime) -> datetime:
    # Get the weekday (Monday = 0, Sunday = 6)
    days_ahead = date.weekday()

    if days_ahead == 0:  # If it's already Monday, return next week's Monday
        return date + timedelta(days=7)
    else:  # Calculate days until next Monday
        days_until_monday = 7 - days_ahead
        return date + timedelta(days=days_until_monday)


def previous_friday(date: datetime) -> datetime:
    """Return the most recent Friday strictly before `date`.

    Used to derive the sell date for a holding period whose next-rebalance Monday
    is `date`: the position holds Mon-open through last-Fri-close, with the
    weekend gap before the next rebalance.
    """
    # Friday = 4. Days back to the previous Friday.
    # If date is a Friday, treat it as 7 days back (we want strictly before).
    days_back = (date.weekday() - 4) % 7
    if days_back == 0:
        days_back = 7
    return date - timedelta(days=days_back)
