from engine.cases.profitable_growth import grade_cash_conversion, reinvestment_intensity
from engine.models import CaseType, Grade, MetricResult
from engine.router import RouterInput, route_case
from engine.scoring import weighted_quant_score, quant_grade


def test_weighted_score():
    metrics = [
        MetricResult(name="a", grade=Grade.A, weight=0.5),
        MetricResult(name="b", grade=Grade.B, weight=0.5),
    ]
    assert weighted_quant_score(metrics) == 3.5
    assert quant_grade(3.5) == Grade.A


def test_cash_conversion_uses_cfo_to_net_income():
    assert grade_cash_conversion(300, 250) == Grade.A
    assert grade_cash_conversion(210, 250) == Grade.B
    assert grade_cash_conversion(150, 250) == Grade.C
    assert grade_cash_conversion(100, 250) == Grade.D
    assert grade_cash_conversion(99, 250) == Grade.X
    assert grade_cash_conversion(100, 0) == Grade.X


def test_capex_is_a_tag_not_a_cash_grade_input():
    grade = grade_cash_conversion(300, 250)
    assert reinvestment_intensity(330, 300) == "very_high"
    assert grade == Grade.A


def test_cyclical_routing_precedes_profitable_growth():
    result = route_case(RouterInput(profitable=True, structurally_cyclical=True))
    assert result == CaseType.CYCLICAL


def test_quality_compounder_routing_does_not_require_a_loss():
    result = route_case(RouterInput(profitable=True, high_roic_long_duration=True))
    assert result == CaseType.QUALITY_COMPOUNDER
