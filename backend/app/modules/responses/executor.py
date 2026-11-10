"""Simulation-only executor; intentionally has no network or system-control dependencies."""


def simulate_containment() -> dict:
    return {
        "outcome": "simulated",
        "verified": True,
        "message": "Simulation completed; no external system was contacted or changed",
    }
