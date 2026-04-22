from __future__ import annotations

from datetime import datetime


def format_bytes(value: int | float | None) -> str:
    if value is None or value <= 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    number = f"{size:.2f}".rstrip("0").rstrip(".")
    return f"{number} {units[unit_index]}"


def format_speed(value: int | float | None) -> str:
    if value is None or value <= 0:
        return "-"
    return f"{format_bytes(value)}/s"


def format_progress(completed: int | None, total: int | None) -> float:
    if not completed or not total or total <= 0:
        return 0.0
    return min(100.0, max(0.0, (completed / total) * 100.0))


def format_datetime(value: str | None) -> str:
    if not value:
        return "-"

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")
