"""Deterministic, explainable MVP risk scoring."""

SEVERITY_SCORE = {"info": 5, "low": 15, "medium": 35, "high": 60, "critical": 80}
SEVERITY_ORDER = {name: index for index, name in enumerate(SEVERITY_SCORE)}


def score_correlated(severities: list[str]) -> tuple[str, int, list[dict]]:
    if not severities:
        raise ValueError("at least one event severity is required")
    top = max(severities, key=lambda value: SEVERITY_ORDER[value])
    count = len(severities)
    score = min(100, SEVERITY_SCORE[top] + max(0, count - 1) * 10)
    factors = [
        {
            "code": f"severity_{top}",
            "contribution": SEVERITY_SCORE[top],
            "explanation": f"Highest correlated severity: {top}",
        },
        {
            "code": "correlated_events",
            "contribution": min(100 - SEVERITY_SCORE[top], (count - 1) * 10),
            "explanation": f"{count} distinct event(s) correlated in a 15-minute window",
        },
    ]
    return top, score, factors
