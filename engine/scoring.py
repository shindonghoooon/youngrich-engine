from __future__ import annotations

from engine.models import Grade, MetricResult

GRADE_SCORE = {
    Grade.A: 4.0,
    Grade.B: 3.0,
    Grade.C: 2.0,
    Grade.D: 1.0,
    Grade.X: 0.0,
}


def weighted_quant_score(metrics: list[MetricResult]) -> float:
    total_weight = sum(m.weight for m in metrics)
    if round(total_weight, 6) != 1.0:
        raise ValueError(f"Metric weights must sum to 1.0, got {total_weight:.6f}")
    if any(m.grade is None for m in metrics):
        raise ValueError("All metrics must be graded before calculating a Quant score")

    return round(sum(GRADE_SCORE[m.grade] * m.weight for m in metrics), 3)


def quant_grade(score: float) -> Grade:
    if score >= 3.50:
        return Grade.A
    if score >= 3.00:
        return Grade.B
    if score >= 2.40:
        return Grade.C
    if score >= 1.80:
        return Grade.D
    return Grade.X
