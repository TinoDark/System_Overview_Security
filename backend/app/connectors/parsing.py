import re
from datetime import UTC, datetime
from typing import Any


def parse_utc(value: str | float) -> datetime:
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        return datetime.fromtimestamp(float(value), tz=UTC)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if re.search(r"[+-]\d{4}$", text):
        text = text[:-2] + ":" + text[-2:]
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def wazuh_severity(level: int) -> str:
    if level >= 15:
        return "critical"
    if level >= 12:
        return "high"
    if level >= 7:
        return "medium"
    if level >= 4:
        return "low"
    return "info"


def suricata_severity(level: int) -> str:
    return {1: "critical", 2: "high", 3: "medium"}.get(level, "low")


def bounded_raw(raw: dict[str, Any], drop: tuple[str, ...] = ()) -> dict[str, Any]:
    return {key: value for key, value in raw.items() if key not in drop}
