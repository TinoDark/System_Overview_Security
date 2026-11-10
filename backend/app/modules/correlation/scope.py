"""Correlation key construction; keys are tenant-scoped by their callers."""


def event_scope(event_data: dict) -> set[str]:
    asset = event_data.get("asset") or {}
    values = {f"asset:{asset[k]}" for k in ("asset_id", "hostname", "ip_address") if asset.get(k)}
    if not values:
        values = {f"indicator:{i['type']}:{i['value']}" for i in event_data.get("indicators", [])}
    return values


def matches_scope(left: set[str], right: set[str]) -> bool:
    return bool(left.intersection(right))
