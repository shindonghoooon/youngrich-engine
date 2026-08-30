import json
from pathlib import Path

from engine.models import AnalysisSnapshot
from engine.scoring import weighted_quant_score, quant_grade


def main():
    path = Path("data/examples/STRL.example.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    snapshot = AnalysisSnapshot.model_validate(data)

    score = weighted_quant_score(snapshot.metrics)
    grade = quant_grade(score)

    print(f"{snapshot.ticker} | {snapshot.case.value}")
    print(f"Quant Score: {score:.3f}")
    print(f"Quant Grade: {grade.value}")


if __name__ == "__main__":
    main()
