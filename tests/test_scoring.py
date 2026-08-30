from engine.models import Grade, MetricResult
from engine.scoring import weighted_quant_score, quant_grade


def test_weighted_score():
    metrics = [
        MetricResult(name="a", grade=Grade.A, weight=0.5),
        MetricResult(name="b", grade=Grade.B, weight=0.5),
    ]
    assert weighted_quant_score(metrics) == 3.5
    assert quant_grade(3.5) == Grade.A
