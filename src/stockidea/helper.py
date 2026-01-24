from datetime import datetime, timedelta


def next_monday(date: datetime) -> datetime:
    # Get the weekday (Monday = 0, Sunday = 6)
    days_ahead = date.weekday()

    if days_ahead == 0:  # If it's already Monday, return next week's Monday
        return date + timedelta(days=7)
    else:  # Calculate days until next Monday
        days_until_monday = 7 - days_ahead
        return date + timedelta(days=days_until_monday)
