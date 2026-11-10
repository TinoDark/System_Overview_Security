from app.modules.detection.scoring import score_correlated


def test_score_is_bounded_and_explainable():
    severity, score, factors = score_correlated(
        ["medium", "medium", "high", "critical", "critical"]
    )
    assert severity == "critical"
    assert score == 100
    assert factors[0]["code"] == "severity_critical"
    assert factors[1]["contribution"] == 20
    assert all(factor["explanation"] for factor in factors)
