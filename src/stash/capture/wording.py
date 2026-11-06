from datetime import date

LINE_LIMIT = 300


def short_day(day: date) -> str:
    return f"{day:%a %b} {day.day}"


def counted(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"
